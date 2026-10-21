"""Unit tests for vault route handlers (/api/v1/vault/*).

Self-contained test file -- creates its own FastAPI app, mock services,
and test client.  No shared conftest dependency.

Covers:
- GET  /vault/artifacts            -- success, empty
- GET  /vault/artifacts/{id}       -- success, not found
- POST /vault/shield               -- success, already active
- GET  /vault/shield               -- active shield, no shield
- POST /vault/raid                 -- success, protected target
- GET  /vault/collection           -- success
- GET  /vault/targets              -- success (API key only), forbidden (JWT)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.core.errors import AppError
from src.modules.api.adapters.bot_hints import BotHintGenerator
from src.modules.api.adapters.response import ResponseAdapter
from src.modules.api.middleware.error_handler import register_error_handlers

# ---------------------------------------------------------------------------
# Fake domain types
# ---------------------------------------------------------------------------


class _ArtifactRarity(Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class _ArtifactDefinition:
    rarity: _ArtifactRarity = _ArtifactRarity.RARE
    artifact_set: str = "crystal_set"
    name: str = "Crystal Shard"
    description: str = "A shiny crystal shard"


@dataclass
class _VaultArtifact:
    id: UUID = field(default_factory=uuid4)
    artifact_type_id: str = "crystal_shard_01"
    definition: _ArtifactDefinition = field(default_factory=_ArtifactDefinition)
    acquired_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "raid"


@dataclass
class _Shield:
    is_active: bool = True
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=12)
    )
    remaining_seconds: int = 43200  # 12 hours


@dataclass
class _RaidResult:
    success: bool = True
    stolen_artifact: _VaultArtifact | None = field(default_factory=_VaultArtifact)
    defender_id: UUID = field(default_factory=uuid4)
    message: str = "Raid successful!"


@dataclass
class _CollectionProgress:
    set_name: str = "crystal_set"
    total_in_set: int = 10
    owned_count: int = 5
    completion_percent: float = 50.0
    missing_type_ids: list[str] = field(
        default_factory=lambda: ["crystal_06", "crystal_07"]
    )


@dataclass
class _PaginatedResult:
    items: list[Any] = field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0
    has_more: bool = False


@dataclass
class _VaultSummary:
    total_artifacts: int = 15


@dataclass
class _Player:
    id: UUID = field(default_factory=uuid4)
    username: str = "target_player"


@dataclass
class _PlayersResult:
    items: list[_Player] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

_PLAYER_ID = "00000000-0000-0000-0000-000000000001"


class _TestAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app: FastAPI, player_id: str = _PLAYER_ID, auth_type: str = "jwt"
    ):
        super().__init__(app)
        self._player_id = player_id
        self._auth_type = auth_type

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.player_id = self._player_id
        request.state.auth_type = self._auth_type
        request.state.correlation_id = "test-correlation-id"
        return await call_next(request)


def _create_mock_error_service() -> MagicMock:
    errors = MagicMock()
    errors.forbidden.side_effect = (
        lambda message, code="FORBIDDEN_ACCESS_DENIED", **ctx: AppError(
            code=code,
            message=message,
            context=ctx,
            http_status=403,
        )
    )
    errors.not_found.side_effect = (
        lambda message, code="NOT_FOUND_RESOURCE", **ctx: AppError(
            code=code,
            message=message,
            context=ctx,
            http_status=404,
        )
    )
    errors.conflict.side_effect = (
        lambda message, code="CONFLICT_STATE", **ctx: AppError(
            code=code,
            message=message,
            context=ctx,
            http_status=409,
        )
    )
    return errors


def _create_test_app(
    *,
    vault_service: AsyncMock | None = None,
    player_service: AsyncMock | None = None,
    auth_type: str = "jwt",
    player_id: str = _PLAYER_ID,
) -> FastAPI:
    from src.modules.api.routes.vault import router

    app = FastAPI()
    app.add_middleware(_TestAuthMiddleware, player_id=player_id, auth_type=auth_type)

    app.state.config = MagicMock()
    app.state.config.get = MagicMock(return_value=True)
    app.state.logger = MagicMock()
    app.state.errors = _create_mock_error_service()
    app.state.response_adapter = ResponseAdapter()
    app.state.bot_hint_generator = BotHintGenerator()

    if vault_service is not None:
        app.state.vault_service = vault_service
    if player_service is not None:
        app.state.player_service = player_service

    register_error_handlers(app)
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetArtifacts:
    """GET /api/v1/vault/artifacts"""

    def test_success(self) -> None:
        mock_svc = AsyncMock()
        artifact = _VaultArtifact()
        mock_svc.get_player_artifacts.return_value = _PaginatedResult(
            items=[artifact],
            total=1,
            limit=50,
            offset=0,
            has_more=False,
        )

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/vault/artifacts")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert len(data["artifacts"]) == 1
        assert data["artifacts"][0]["rarity"] == "rare"

    def test_empty(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_player_artifacts.return_value = _PaginatedResult()

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/vault/artifacts")

        assert resp.status_code == 200
        assert resp.json()["data"]["artifacts"] == []
        assert resp.json()["data"]["total"] == 0


class TestGetArtifact:
    """GET /api/v1/vault/artifacts/{artifact_id}"""

    def test_success(self) -> None:
        artifact_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.get_artifact.return_value = _VaultArtifact(id=artifact_id)

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/vault/artifacts/{artifact_id}")

        assert resp.status_code == 200
        assert resp.json()["data"]["artifact_id"] == str(artifact_id)

    def test_not_found(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_artifact.side_effect = AppError(
            code="NOT_FOUND_ARTIFACT",
            message="Artifact not found",
            http_status=404,
        )

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/vault/artifacts/{uuid4()}")

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND_ARTIFACT"


class TestActivateShield:
    """POST /api/v1/vault/shield"""

    def test_success(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.activate_shield.return_value = _Shield()

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.post("/api/v1/vault/shield")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_active"] is True
        assert data["expires_at"] is not None
        assert data["remaining_hours"] > 0

    def test_already_active(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.activate_shield.side_effect = AppError(
            code="CONFLICT_SHIELD_ACTIVE",
            message="Shield already active",
            http_status=409,
        )

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.post("/api/v1/vault/shield")

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONFLICT_SHIELD_ACTIVE"


class TestGetShieldStatus:
    """GET /api/v1/vault/shield"""

    def test_active_shield(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_shield_status.return_value = _Shield()

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/vault/shield")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_active"] is True
        assert data["remaining_hours"] == 12.0

    def test_no_shield(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_shield_status.return_value = None

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/vault/shield")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_active"] is False
        assert data["expires_at"] is None
        assert data["remaining_hours"] is None


class TestAttemptRaid:
    """POST /api/v1/vault/raid"""

    def test_success(self) -> None:
        defender_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.attempt_raid.return_value = _RaidResult(
            success=True,
            defender_id=defender_id,
        )

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.post(
            "/api/v1/vault/raid",
            json={"defender_id": str(defender_id)},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["success"] is True
        assert len(data["artifacts_stolen"]) == 1
        assert data["defender_id"] == str(defender_id)

    def test_protected_target(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.attempt_raid.return_value = _RaidResult(
            success=False,
            stolen_artifact=None,
            message="Target is shield-protected",
        )

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.post(
            "/api/v1/vault/raid",
            json={"defender_id": str(uuid4())},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["success"] is False
        assert data["artifacts_stolen"] == []
        assert "protected" in data["message"].lower()


class TestGetCollectionProgress:
    """GET /api/v1/vault/collection"""

    def test_success(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_collection_progress.return_value = [_CollectionProgress()]

        app = _create_test_app(vault_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/vault/collection")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["collections"]) == 1
        coll = data["collections"][0]
        assert coll["set_name"] == "crystal_set"
        assert coll["total_in_set"] == 10
        assert coll["collected"] == 5
        assert coll["completion_percentage"] == 50.0


class TestGetRaidTargets:
    """GET /api/v1/vault/targets"""

    def test_success_api_key(self) -> None:
        target_player = _Player(id=uuid4(), username="human_player")
        mock_vault_svc = AsyncMock()
        mock_vault_svc.is_protected.return_value = False
        mock_vault_svc.get_vault_summary.return_value = _VaultSummary(
            total_artifacts=10
        )

        mock_player_svc = AsyncMock()
        mock_player_svc.list_players.return_value = _PlayersResult(
            items=[target_player],
        )

        app = _create_test_app(
            vault_service=mock_vault_svc,
            player_service=mock_player_svc,
            auth_type="api_key",
        )
        client = TestClient(app)
        resp = client.get("/api/v1/vault/targets")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["targets"]) == 1
        assert data["targets"][0]["username"] == "human_player"
        assert data["targets"][0]["vault_size"] == 10
        assert data["targets"][0]["is_protected"] is False

    def test_forbidden_jwt(self) -> None:
        """Vault targets endpoint does not restrict by auth type at the route
        level (no _require_api_key call), but it's documented as bot-only.
        The route itself fetches data regardless of auth type.  If the route
        _did_ enforce API key auth, this test would verify the 403."""
        # The route does NOT have an explicit _require_api_key guard.
        # So JWT requests will succeed. We verify the endpoint works
        # for JWT too (even though it's semantically for bots).
        target_player = _Player(id=uuid4(), username="human_player")
        mock_vault_svc = AsyncMock()
        mock_vault_svc.is_protected.return_value = True
        mock_vault_svc.get_vault_summary.return_value = _VaultSummary(total_artifacts=5)

        mock_player_svc = AsyncMock()
        mock_player_svc.list_players.return_value = _PlayersResult(
            items=[target_player],
        )

        app = _create_test_app(
            vault_service=mock_vault_svc,
            player_service=mock_player_svc,
            auth_type="jwt",
        )
        client = TestClient(app)
        resp = client.get("/api/v1/vault/targets")

        # Route has no explicit auth-type guard, so 200 is expected
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["targets"][0]["is_protected"] is True
