"""Unit tests for ads route handlers (/api/v1/ads/*).

Self-contained test file -- creates its own FastAPI app, mock services,
and test client.  No shared conftest dependency.

Covers:
- GET  /ads/status                 -- ad-free, not ad-free
- POST /ads/interstitial/request   -- success (JWT), forbidden (API key)
- POST /ads/interstitial/complete  -- success
- POST /ads/rewarded/request       -- success (JWT), forbidden (API key)
- POST /ads/rewarded/complete      -- success, not completed
- GET  /ads/bot/attributions       -- success (API key), forbidden (JWT)
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
# Fake domain types used by the ads routes
# ---------------------------------------------------------------------------


class _AdFreeReason(Enum):
    PURCHASED = "purchased"
    SUBSCRIPTION = "subscription"


@dataclass
class _AdFreeStatus:
    is_ad_free: bool = False
    reason: _AdFreeReason | None = None
    expires_at: datetime | None = None


@dataclass
class _InterstitialResult:
    ad_request_id: UUID = field(default_factory=uuid4)
    should_show: bool = True
    ad_unit_id: str | None = "interstitial_001"


@dataclass
class _ImpressionRecord:
    id: UUID = field(default_factory=uuid4)
    viewed: bool = True
    view_duration_ms: int = 5000


class _RewardType(Enum):
    BONUS_HEART = "bonus_heart"
    EXTRA_HEARTS = "extra_hearts"
    EVENT_POINTS = "event_points"


@dataclass
class _RewardedVideoResult:
    ad_request_id: UUID = field(default_factory=uuid4)
    ad_unit_id: str | None = "rewarded_001"
    reward_type: _RewardType | None = _RewardType.BONUS_HEART
    reward_value: int = 1


@dataclass
class _RewardedCompleteResult:
    reward_granted: bool = True
    reward_type: _RewardType | None = _RewardType.BONUS_HEART
    reward_value: int | None = 1


@dataclass
class _DailyBreakdown:
    date: date = field(default_factory=date.today)
    matches: int = 5
    impressions: int = 10
    estimated_revenue_cents: int = 50
    attributed_cents: int = 25


@dataclass
class _BotAttributionResult:
    bot_player_id: UUID = field(default_factory=uuid4)
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)
    total_attributed_impressions: int = 100
    attributed_revenue_cents: int = 500
    daily_breakdown: list[_DailyBreakdown] = field(
        default_factory=lambda: [_DailyBreakdown()]
    )


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
    ad_service: AsyncMock | None = None,
    auth_type: str = "jwt",
    player_id: str = _PLAYER_ID,
) -> FastAPI:
    from src.modules.api.routes.ads import router

    app = FastAPI()
    app.add_middleware(_TestAuthMiddleware, player_id=player_id, auth_type=auth_type)

    app.state.config = MagicMock()
    app.state.config.get = MagicMock(return_value=True)
    app.state.logger = MagicMock()
    app.state.errors = _create_mock_error_service()
    app.state.response_adapter = ResponseAdapter()
    app.state.bot_hint_generator = BotHintGenerator()

    if ad_service is not None:
        app.state.ad_service = ad_service

    register_error_handlers(app)
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetAdFreeStatus:
    """GET /api/v1/ads/status"""

    def test_ad_free(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.check_ad_free_status.return_value = _AdFreeStatus(
            is_ad_free=True,
            reason=_AdFreeReason.PURCHASED,
            expires_at=None,
        )

        app = _create_test_app(ad_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/ads/status")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_ad_free"] is True
        assert data["reason"] == "purchased"

    def test_not_ad_free(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.check_ad_free_status.return_value = _AdFreeStatus(
            is_ad_free=False,
            reason=None,
            expires_at=None,
        )

        app = _create_test_app(ad_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/ads/status")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_ad_free"] is False
        assert data["reason"] is None


class TestRequestInterstitial:
    """POST /api/v1/ads/interstitial/request"""

    def test_success_jwt(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.request_interstitial.return_value = _InterstitialResult()

        app = _create_test_app(ad_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/ads/interstitial/request",
            json={"trigger": "match_end"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["should_show"] is True
        assert data["ad_unit_id"] == "interstitial_001"
        assert data["ad_request_id"] is not None

    def test_forbidden_api_key(self) -> None:
        mock_svc = AsyncMock()

        app = _create_test_app(ad_service=mock_svc, auth_type="api_key")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/ads/interstitial/request",
            json={"trigger": "match_end"},
        )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN_BOT_NOT_ALLOWED"


class TestCompleteInterstitial:
    """POST /api/v1/ads/interstitial/complete"""

    def test_success(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.record_interstitial_impression.return_value = _ImpressionRecord()

        app = _create_test_app(ad_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/ads/interstitial/complete",
            json={
                "ad_request_id": str(uuid4()),
                "viewed": True,
                "duration_ms": 5000,
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["viewed"] is True
        assert data["duration_ms"] == 5000
        assert data["impression_id"] is not None


class TestRequestRewardedVideo:
    """POST /api/v1/ads/rewarded/request"""

    def test_success_jwt(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.request_rewarded_video.return_value = _RewardedVideoResult()

        app = _create_test_app(ad_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/ads/rewarded/request",
            json={"reward_type": "bonus_heart"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["ad_request_id"] is not None
        assert data["ad_unit_id"] == "rewarded_001"
        assert data["reward_preview"]["reward_type"] == "bonus_heart"
        assert data["reward_preview"]["reward_value"] == 1

    def test_forbidden_api_key(self) -> None:
        mock_svc = AsyncMock()

        app = _create_test_app(ad_service=mock_svc, auth_type="api_key")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/ads/rewarded/request",
            json={"reward_type": "bonus_heart"},
        )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN_BOT_NOT_ALLOWED"


class TestCompleteRewardedVideo:
    """POST /api/v1/ads/rewarded/complete"""

    def test_success(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.complete_rewarded_video.return_value = _RewardedCompleteResult(
            reward_granted=True,
            reward_type=_RewardType.BONUS_HEART,
            reward_value=1,
        )

        app = _create_test_app(ad_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/ads/rewarded/complete",
            json={
                "ad_request_id": str(uuid4()),
                "completed": True,
                "watched_duration_ms": 30000,
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["reward_granted"] is True
        assert data["reward_type"] == "bonus_heart"
        assert data["reward_amount"] == 1

    def test_not_completed(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.complete_rewarded_video.return_value = _RewardedCompleteResult(
            reward_granted=False,
            reward_type=None,
            reward_value=None,
        )

        app = _create_test_app(ad_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/ads/rewarded/complete",
            json={
                "ad_request_id": str(uuid4()),
                "completed": False,
                "watched_duration_ms": 5000,
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["reward_granted"] is False
        assert data["reward_type"] is None
        assert data["reward_amount"] is None


class TestGetBotAttributions:
    """GET /api/v1/ads/bot/attributions"""

    def test_success_api_key(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_bot_ad_attributions.return_value = _BotAttributionResult()

        app = _create_test_app(ad_service=mock_svc, auth_type="api_key")
        client = TestClient(app)
        resp = client.get(
            "/api/v1/ads/bot/attributions",
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_impressions"] == 100
        assert data["total_revenue_cents"] == 500
        assert len(data["daily_breakdown"]) == 1

    def test_forbidden_jwt(self) -> None:
        mock_svc = AsyncMock()

        app = _create_test_app(ad_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.get(
            "/api/v1/ads/bot/attributions",
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN_NOT_BOT"
