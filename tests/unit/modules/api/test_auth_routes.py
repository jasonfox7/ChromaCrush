"""Unit tests for auth route handlers.

Tests all eight auth endpoints using the test client with mock services
injected via app.state. Authentication state is simulated by the
TestAuthMiddleware in conftest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from starlette.testclient import TestClient

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.core.types.player import Player, PlayerType

from tests.unit.modules.api.conftest import TEST_PLAYER_ID

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------


def _make_player(
    player_id: UUID | None = None,
    username: str = "testuser",
    player_type: PlayerType = PlayerType.HUMAN,
) -> Player:
    """Create a Player entity for mock return values."""
    return Player(
        id=PlayerId(player_id or UUID(TEST_PLAYER_ID)),
        username=username,
        player_type=player_type,
        elo_rating=1000,
        created_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


@dataclass
class FakeAuthResult:
    """Mimics the AuthResult DTO returned by auth_service.authenticate."""

    access_token: str = "jwt-access-token-123"
    refresh_token: str = "jwt-refresh-token-456"
    token_type: str = "Bearer"
    expires_in: int = 3600


@dataclass
class FakeApiKeyResult:
    """Mimics the result from auth_service.create_api_key."""

    raw_key: str = "cc_generated_key_abc123"
    key_info: Any = None

    def __post_init__(self) -> None:
        if self.key_info is None:
            self.key_info = FakeKeyInfo()


@dataclass
class FakeKeyInfo:
    """Mimics ApiKeyInfo returned inside FakeApiKeyResult."""

    key_id: UUID = field(default_factory=uuid4)
    player_id: UUID = field(default_factory=lambda: UUID(TEST_PLAYER_ID))
    prefix: str = "cc_gene"
    created_at: datetime = field(
        default_factory=lambda: datetime(2026, 1, 20, 12, 0, 0, tzinfo=timezone.utc),
    )
    revoked: bool = False


# ---------------------------------------------------------------------------
# Auth Route Tests
# ---------------------------------------------------------------------------


class TestRegisterRoute:
    """Tests for POST /api/v1/auth/register."""

    def test_register_success(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Successful registration returns player info and tokens."""
        mock_player_service.create_player.return_value = _make_player(
            username="newuser"
        )
        mock_auth_service.authenticate.return_value = FakeAuthResult()

        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "password": "SecurePass123",
                "email": "new@example.com",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["player"]["username"] == "newuser"
        assert data["data"]["auth"]["access_token"] == "jwt-access-token-123"
        assert data["data"]["auth"]["token_type"] == "Bearer"

    def test_register_short_username_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Username shorter than 3 chars fails Pydantic validation."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "ab",
                "password": "SecurePass123",
            },
        )

        assert resp.status_code == 422

    def test_register_short_password_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Password shorter than 8 chars fails Pydantic validation."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "validuser",
                "password": "short",
            },
        )

        assert resp.status_code == 422

    def test_register_invalid_username_chars_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Username with special chars fails Pydantic pattern validation."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "invalid user!",
                "password": "SecurePass123",
            },
        )

        assert resp.status_code == 422

    def test_register_conflict_returns_error(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Duplicate username from player service raises error through handler."""
        mock_player_service.create_player.side_effect = AppError(
            code="CONFLICT_USERNAME_EXISTS",
            message="Username already taken",
            http_status=409,
        )

        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "existing",
                "password": "SecurePass123",
            },
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONFLICT_USERNAME_EXISTS"


class TestLoginRoute:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Valid credentials return JWT tokens."""
        mock_auth_service.authenticate.return_value = FakeAuthResult()

        resp = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "ValidPass123",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["access_token"] == "jwt-access-token-123"
        assert data["data"]["refresh_token"] == "jwt-refresh-token-456"
        assert data["data"]["token_type"] == "Bearer"
        assert data["data"]["expires_in"] == 3600

    def test_login_invalid_credentials(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Invalid credentials from auth service return error."""
        mock_auth_service.authenticate.side_effect = AppError(
            code="AUTH_INVALID_CREDENTIALS",
            message="Invalid credentials",
            http_status=401,
        )

        resp = client.post(
            "/api/v1/auth/login",
            json={
                "username": "wrong",
                "password": "WrongPass123",
            },
        )

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    def test_login_missing_fields_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Missing required fields fail Pydantic validation."""
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
            },
        )

        assert resp.status_code == 422


class TestRefreshTokenRoute:
    """Tests for POST /api/v1/auth/refresh."""

    def test_refresh_success(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Valid refresh token returns new token pair."""
        mock_auth_service.refresh_token.return_value = FakeAuthResult(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
        )

        resp = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "old-refresh-token",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["access_token"] == "new-access-token"
        assert data["data"]["refresh_token"] == "new-refresh-token"

    def test_refresh_invalid_token(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Invalid refresh token returns error."""
        mock_auth_service.refresh_token.side_effect = AppError(
            code="AUTH_TOKEN_INVALID",
            message="Refresh token invalid",
            http_status=401,
        )

        resp = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "invalid-token",
            },
        )

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTH_TOKEN_INVALID"

    def test_refresh_missing_token_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Missing refresh_token field returns 422."""
        resp = client.post("/api/v1/auth/refresh", json={})

        assert resp.status_code == 422


class TestLogoutRoute:
    """Tests for POST /api/v1/auth/logout."""

    def test_logout_success(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Successful logout returns acknowledgement."""
        mock_auth_service.logout.return_value = None

        resp = client.post("/api/v1/auth/logout")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "Logged out" in data["data"]["message"]

    def test_logout_player_not_found(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Logout for non-existent player returns error."""
        mock_auth_service.logout.side_effect = AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
            http_status=404,
        )

        resp = client.post("/api/v1/auth/logout")

        assert resp.status_code == 404


class TestBotRegisterRoute:
    """Tests for POST /api/v1/auth/bot/register."""

    def test_bot_register_success(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Bot registration returns player info without tokens."""
        mock_player_service.create_player.return_value = _make_player(
            username="my_bot",
            player_type=PlayerType.BOT,
        )

        resp = client.post(
            "/api/v1/auth/bot/register",
            json={
                "bot_name": "my_bot",
                "owner_contact": "owner@example.com",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["player"]["username"] == "my_bot"
        assert data["data"]["player"]["player_type"] == "bot"

    def test_bot_register_short_name_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Bot name shorter than 3 chars fails Pydantic validation."""
        resp = client.post(
            "/api/v1/auth/bot/register",
            json={
                "bot_name": "ab",
                "owner_contact": "owner@example.com",
            },
        )

        assert resp.status_code == 422


class TestCreateApiKeyRoute:
    """Tests for POST /api/v1/auth/bot/api-key."""

    def test_create_api_key_success(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Successful API key creation returns key details."""
        mock_auth_service.create_api_key.return_value = FakeApiKeyResult()

        resp = client.post(
            "/api/v1/auth/bot/api-key",
            json={
                "description": "Test key",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["api_key"] == "cc_generated_key_abc123"
        assert "key_id" in data["data"]

    def test_create_api_key_no_description(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """API key creation without description succeeds."""
        mock_auth_service.create_api_key.return_value = FakeApiKeyResult()

        resp = client.post("/api/v1/auth/bot/api-key", json={})

        assert resp.status_code == 200

    def test_create_api_key_forbidden_for_human(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Human player trying to create API key gets 403."""
        mock_auth_service.create_api_key.side_effect = AppError(
            code="FORBIDDEN_NOT_BOT",
            message="Only bots can create API keys",
            http_status=403,
        )

        resp = client.post("/api/v1/auth/bot/api-key", json={})

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN_NOT_BOT"


class TestRevokeApiKeyRoute:
    """Tests for DELETE /api/v1/auth/bot/api-key/{key_id}."""

    def test_revoke_api_key_success(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Successful key revocation returns acknowledgement."""
        key_id = str(uuid4())
        mock_auth_service.revoke_api_key.return_value = None

        resp = client.delete(f"/api/v1/auth/bot/api-key/{key_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "revoked" in data["data"]["message"].lower()

    def test_revoke_api_key_not_found(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Revoking non-existent key returns 404."""
        key_id = str(uuid4())
        mock_auth_service.revoke_api_key.side_effect = AppError(
            code="NOT_FOUND_API_KEY",
            message="API key not found",
            http_status=404,
        )

        resp = client.delete(f"/api/v1/auth/bot/api-key/{key_id}")

        assert resp.status_code == 404

    def test_revoke_api_key_not_owner(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Non-owner cannot revoke a key."""
        key_id = str(uuid4())
        mock_auth_service.revoke_api_key.side_effect = AppError(
            code="FORBIDDEN_NOT_KEY_OWNER",
            message="Not the key owner",
            http_status=403,
        )

        resp = client.delete(f"/api/v1/auth/bot/api-key/{key_id}")

        assert resp.status_code == 403


class TestListApiKeysRoute:
    """Tests for GET /api/v1/auth/bot/api-keys."""

    def test_list_api_keys_success(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Successful key listing returns key metadata."""
        key_info = FakeKeyInfo()
        mock_auth_service.list_api_keys.return_value = [key_info]

        resp = client.get("/api/v1/auth/bot/api-keys")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]["keys"]) == 1
        assert data["data"]["keys"][0]["prefix"] == "cc_gene"

    def test_list_api_keys_empty(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Player with no API keys gets empty list."""
        mock_auth_service.list_api_keys.return_value = []

        resp = client.get("/api/v1/auth/bot/api-keys")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["keys"] == []
