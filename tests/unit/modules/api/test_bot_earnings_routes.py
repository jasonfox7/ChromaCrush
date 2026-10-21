"""Unit tests for bot earnings route handlers (/api/v1/bot-earnings/*).

Self-contained test file -- creates its own FastAPI app, mock services,
and test client.  No shared conftest dependency.

Covers:
- GET  /bot-earnings/balance            -- success (API key), forbidden (JWT)
- POST /bot-earnings/sync               -- success
- POST /bot-earnings/payout/request     -- success
- GET  /bot-earnings/payout/history     -- success with pagination
- GET  /bot-earnings/attributions       -- success with pagination
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
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


class _PayoutStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class _EarningsBalance:
    bot_player_id: UUID = field(default_factory=uuid4)
    total_earned_cents: int = 5000
    pending_payout_cents: int = 1000
    available_balance_cents: int = 4000
    total_paid_out_cents: int = 0
    last_sync_at: datetime | None = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class _SyncResult:
    new_attributions: int = 10
    new_earnings_cents: int = 250
    sync_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class _PayoutRequest:
    id: UUID = field(default_factory=uuid4)
    bot_player_id: UUID = field(default_factory=uuid4)
    amount_cents: int = 4000
    status: _PayoutStatus = _PayoutStatus.PENDING
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: datetime | None = None


@dataclass
class _PaginatedResult:
    items: list[Any] = field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0
    has_more: bool = False


@dataclass
class _AttributionEntry:
    id: UUID = field(default_factory=uuid4)
    ad_impression_id: UUID = field(default_factory=uuid4)
    opponent_player_id: UUID = field(default_factory=uuid4)
    bot_player_id: UUID = field(default_factory=uuid4)
    attributed_cents: int = 25
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

_PLAYER_ID = "00000000-0000-0000-0000-000000000001"


class _TestAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app: FastAPI, player_id: str = _PLAYER_ID, auth_type: str = "api_key"
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
    errors.validation.side_effect = (
        lambda message, code="VALIDATION_INVALID_INPUT", **ctx: AppError(
            code=code,
            message=message,
            context=ctx,
            http_status=400,
        )
    )
    return errors


def _create_test_app(
    *,
    bot_earnings_service: AsyncMock | None = None,
    auth_type: str = "api_key",
    player_id: str = _PLAYER_ID,
) -> FastAPI:
    from src.modules.api.routes.bot_earnings import router

    app = FastAPI()
    app.add_middleware(_TestAuthMiddleware, player_id=player_id, auth_type=auth_type)

    app.state.config = MagicMock()
    app.state.config.get = MagicMock(return_value=True)
    app.state.logger = MagicMock()
    app.state.errors = _create_mock_error_service()
    app.state.response_adapter = ResponseAdapter()
    app.state.bot_hint_generator = BotHintGenerator()

    if bot_earnings_service is not None:
        app.state.bot_earnings_service = bot_earnings_service

    register_error_handlers(app)
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetEarningsBalance:
    """GET /api/v1/bot-earnings/balance"""

    def test_success_api_key(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_earnings_balance.return_value = _EarningsBalance()

        app = _create_test_app(bot_earnings_service=mock_svc, auth_type="api_key")
        client = TestClient(app)
        resp = client.get("/api/v1/bot-earnings/balance")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_earned_cents"] == 5000
        assert data["pending_payout_cents"] == 1000
        assert data["available_cents"] == 4000
        assert data["paid_out_cents"] == 0
        assert data["last_sync_at"] is not None

    def test_forbidden_jwt(self) -> None:
        mock_svc = AsyncMock()

        app = _create_test_app(bot_earnings_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.get("/api/v1/bot-earnings/balance")

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN_NOT_BOT"


class TestSyncAttributions:
    """POST /api/v1/bot-earnings/sync"""

    def test_success(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.sync_attributions.return_value = _SyncResult()

        app = _create_test_app(bot_earnings_service=mock_svc, auth_type="api_key")
        client = TestClient(app)
        resp = client.post("/api/v1/bot-earnings/sync")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["new_attributions"] == 10
        assert data["new_earnings_cents"] == 250
        assert data["sync_date"] is not None


class TestRequestPayout:
    """POST /api/v1/bot-earnings/payout/request"""

    def test_success(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.request_payout.return_value = _PayoutRequest()

        app = _create_test_app(bot_earnings_service=mock_svc, auth_type="api_key")
        client = TestClient(app)
        resp = client.post("/api/v1/bot-earnings/payout/request")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["amount_cents"] == 4000
        assert data["status"] == "pending"
        assert data["payout_request_id"] is not None
        assert data["requested_at"] is not None
        assert data["processed_at"] is None


class TestGetPayoutHistory:
    """GET /api/v1/bot-earnings/payout/history"""

    def test_success_with_pagination(self) -> None:
        payout1 = _PayoutRequest(status=_PayoutStatus.COMPLETED)
        payout2 = _PayoutRequest(status=_PayoutStatus.PENDING)

        mock_svc = AsyncMock()
        mock_svc.get_payout_requests.return_value = _PaginatedResult(
            items=[payout1, payout2],
            total=2,
            limit=50,
            offset=0,
        )

        app = _create_test_app(bot_earnings_service=mock_svc, auth_type="api_key")
        client = TestClient(app)
        resp = client.get("/api/v1/bot-earnings/payout/history?limit=50&offset=0")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert len(data["entries"]) == 2
        assert data["entries"][0]["status"] == "completed"
        assert data["entries"][1]["status"] == "pending"


class TestGetAttributionEntries:
    """GET /api/v1/bot-earnings/attributions"""

    def test_success_with_pagination(self) -> None:
        entry = _AttributionEntry()

        mock_svc = AsyncMock()
        mock_svc.get_attribution_entries.return_value = _PaginatedResult(
            items=[entry],
            total=1,
            limit=50,
            offset=0,
        )

        app = _create_test_app(bot_earnings_service=mock_svc, auth_type="api_key")
        client = TestClient(app)
        resp = client.get(
            "/api/v1/bot-earnings/attributions",
            params={
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "limit": 50,
                "offset": 0,
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert len(data["entries"]) == 1
        assert data["entries"][0]["attribution_id"] is not None
        assert data["entries"][0]["revenue_share_cents"] == 25
        assert data["entries"][0]["attributed_at"] is not None
