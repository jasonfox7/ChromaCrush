"""Unit tests for events route handlers (/api/v1/events/*).

Self-contained test file -- creates its own FastAPI app, mock services,
and test client.  No shared conftest dependency.

Covers:
- GET  /events                    -- success with list
- GET  /events/{event_id}         -- success, not found
- POST /events/{event_id}/join    -- success, already joined, at capacity
- GET  /events/{event_id}/leaderboard -- success
- GET  /events/{event_id}/status  -- success, not participant
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


class _EventType(Enum):
    TOURNAMENT = "tournament"
    CHALLENGE = "challenge"


class _EventStatus(Enum):
    ACTIVE = "active"
    UPCOMING = "upcoming"
    COMPLETED = "completed"


@dataclass
class _Event:
    id: UUID = field(default_factory=uuid4)
    name: str = "Weekly Tournament"
    event_type: _EventType = _EventType.TOURNAMENT
    status: _EventStatus = _EventStatus.ACTIVE
    start_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=7)
    )
    max_participants: int | None = 100
    participant_count: int = 42
    description: str = "Weekly tournament event"


@dataclass
class _EventParticipant:
    event_id: UUID = field(default_factory=uuid4)
    player_id: UUID = field(default_factory=uuid4)
    total_score: int = 1500
    current_rank: int | None = 5
    matches_played: int = 3
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class _LeaderboardEntry:
    rank: int = 1
    player_id: UUID = field(default_factory=uuid4)
    player_username: str = "top_player"
    score: int = 5000
    matches_played: int = 10


@dataclass
class _EventLeaderboard:
    event_id: UUID = field(default_factory=uuid4)
    entries: list[_LeaderboardEntry] = field(default_factory=list)
    total_participants: int = 50


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
    event_service: AsyncMock | None = None,
    auth_type: str = "jwt",
    player_id: str = _PLAYER_ID,
) -> FastAPI:
    from src.modules.api.routes.events import router

    app = FastAPI()
    app.add_middleware(_TestAuthMiddleware, player_id=player_id, auth_type=auth_type)

    app.state.config = MagicMock()
    app.state.config.get = MagicMock(return_value=True)
    app.state.logger = MagicMock()
    app.state.errors = _create_mock_error_service()
    app.state.response_adapter = ResponseAdapter()
    app.state.bot_hint_generator = BotHintGenerator()

    if event_service is not None:
        app.state.event_service = event_service

    register_error_handlers(app)
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListEvents:
    """GET /api/v1/events"""

    def test_success_with_list(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_active_events.return_value = [_Event(), _Event(name="Challenge")]

        app = _create_test_app(event_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/events")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["events"]) == 2
        assert data["events"][0]["name"] == "Weekly Tournament"
        assert data["events"][0]["status"] == "active"
        assert data["events"][0]["current_participants"] == 42


class TestGetEvent:
    """GET /api/v1/events/{event_id}"""

    def test_success(self) -> None:
        event_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.get_event.return_value = _Event(id=event_id)

        app = _create_test_app(event_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/events/{event_id}")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["event_id"] == str(event_id)
        assert data["event_type"] == "tournament"

    def test_not_found(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_event.side_effect = AppError(
            code="NOT_FOUND_EVENT",
            message="Event not found",
            http_status=404,
        )

        app = _create_test_app(event_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/events/{uuid4()}")

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND_EVENT"


class TestJoinEvent:
    """POST /api/v1/events/{event_id}/join"""

    def test_success(self) -> None:
        event_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.join_event.return_value = _EventParticipant(
            event_id=event_id,
            player_id=UUID(_PLAYER_ID),
        )

        app = _create_test_app(event_service=mock_svc)
        client = TestClient(app)
        resp = client.post(f"/api/v1/events/{event_id}/join")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["event_id"] == str(event_id)
        assert data["player_id"] == _PLAYER_ID

    def test_already_joined(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.join_event.side_effect = AppError(
            code="CONFLICT_ALREADY_JOINED",
            message="Already joined this event",
            http_status=409,
        )

        app = _create_test_app(event_service=mock_svc)
        client = TestClient(app)
        resp = client.post(f"/api/v1/events/{uuid4()}/join")

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONFLICT_ALREADY_JOINED"

    def test_at_capacity(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.join_event.side_effect = AppError(
            code="CONFLICT_EVENT_FULL",
            message="Event is at capacity",
            http_status=409,
        )

        app = _create_test_app(event_service=mock_svc)
        client = TestClient(app)
        resp = client.post(f"/api/v1/events/{uuid4()}/join")

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONFLICT_EVENT_FULL"


class TestGetLeaderboard:
    """GET /api/v1/events/{event_id}/leaderboard"""

    def test_success(self) -> None:
        event_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.get_leaderboard.return_value = _EventLeaderboard(
            event_id=event_id,
            entries=[
                _LeaderboardEntry(rank=1, player_username="first", score=5000),
                _LeaderboardEntry(rank=2, player_username="second", score=4000),
            ],
            total_participants=50,
        )
        mock_svc.get_event_participant.return_value = _EventParticipant(
            event_id=event_id,
            player_id=UUID(_PLAYER_ID),
            current_rank=10,
        )

        app = _create_test_app(event_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/events/{event_id}/leaderboard")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["event_id"] == str(event_id)
        assert len(data["entries"]) == 2
        assert data["entries"][0]["rank"] == 1
        assert data["total_participants"] == 50
        assert data["player_rank"] == 10


class TestGetPlayerEventStatus:
    """GET /api/v1/events/{event_id}/status"""

    def test_success(self) -> None:
        event_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.get_event_participant.return_value = _EventParticipant(
            event_id=event_id,
            player_id=UUID(_PLAYER_ID),
            total_score=1500,
            current_rank=5,
            matches_played=3,
        )
        from src.modules.events.types import EventStatus as RealEventStatus

        mock_svc.get_event.return_value = _Event(
            id=event_id,
            status=RealEventStatus.ACTIVE,
        )

        app = _create_test_app(event_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/events/{event_id}/status")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["score"] == 1500
        assert data["rank"] == 5
        assert data["matches_played"] == 3
        assert data["is_active"] is True

    def test_not_participant(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_event_participant.side_effect = AppError(
            code="NOT_FOUND_PARTICIPANT",
            message="Not a participant in this event",
            http_status=404,
        )

        app = _create_test_app(event_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/events/{uuid4()}/status")

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND_PARTICIPANT"
