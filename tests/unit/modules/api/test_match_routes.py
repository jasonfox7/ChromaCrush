"""Unit tests for match route handlers (/api/v1/matches/*).

Self-contained test file -- creates its own FastAPI app, mock services,
and test client.  No shared conftest dependency.

Covers:
- GET  /matches/active        -- success, empty list
- GET  /matches/{id}          -- success, not found
- GET  /matches/{id}/state    -- success (JWT, no bot hints), success (API key, with bot hints)
- GET  /matches/{id}/board    -- success, not found
- POST /matches/{id}/move     -- success, validation error
- POST /matches/{id}/forfeit  -- success, already completed
- GET  /matches/history       -- success with pagination
- GET  /matches/{id}/moves    -- success
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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
# Fake domain types used by the match route helpers
# ---------------------------------------------------------------------------


class _MatchStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FORFEITED = "forfeited"


class _MatchType(Enum):
    RANKED = "ranked"
    CASUAL = "casual"


@dataclass
class _PlayerMatchState:
    player_id: UUID
    player_username: str = "player"
    is_bot: bool = False
    score: int = 0
    moves_made: int = 0
    moves_remaining: int = 10
    current_board: Any = None


@dataclass
class _MatchState:
    match_id: UUID
    status: _MatchStatus = _MatchStatus.IN_PROGRESS
    match_type: _MatchType = _MatchType.RANKED
    player1: _PlayerMatchState = field(
        default_factory=lambda: _PlayerMatchState(
            player_id=UUID("00000000-0000-0000-0000-000000000001")
        )
    )
    player2: _PlayerMatchState = field(
        default_factory=lambda: _PlayerMatchState(
            player_id=UUID("00000000-0000-0000-0000-000000000002")
        )
    )
    raid_data: dict | None = None
    reward_data: dict | None = None
    winner_id: UUID | None = None

    def get_player_state(self, player_id: Any) -> _PlayerMatchState | None:
        if str(self.player1.player_id) == str(player_id):
            return self.player1
        if str(self.player2.player_id) == str(player_id):
            return self.player2
        return None


@dataclass
class _MatchSummary:
    match_id: UUID
    status: _MatchStatus = _MatchStatus.COMPLETED
    match_type: _MatchType = _MatchType.RANKED
    opponent_id: UUID = field(default_factory=uuid4)
    opponent_username: str = "opponent"
    player_score: int = 500
    opponent_score: int = 400
    won: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class _PaginatedResult:
    items: list[Any] = field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0
    has_more: bool = False


@dataclass
class _Position:
    row: int = 0
    col: int = 0


@dataclass
class _Move:
    from_pos: _Position = field(default_factory=_Position)
    to_pos: _Position = field(default_factory=lambda: _Position(row=0, col=1))


@dataclass
class _MoveRecord:
    move_number: int = 1
    player_id: UUID = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000001")
    )
    move: _Move = field(default_factory=_Move)
    score_earned: int = 100
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class _FakeBoard:
    width: int = 8

    def to_list(self) -> list[list[int]]:
        return [[1] * self.width for _ in range(self.width)]

    @property
    def grid(self) -> "_FakeGrid":
        return _FakeGrid(self.width)

    @property
    def func_grid(self) -> "_FakeGrid":
        return _FakeGrid(self.width, fill=0)


class _FakeGrid:
    def __init__(self, size: int, fill: int = 1) -> None:
        self._data = [[fill] * size for _ in range(size)]

    def tolist(self) -> list[list[int]]:
        return self._data


@dataclass
class _PlayerBoardState:
    board: _FakeBoard = field(default_factory=_FakeBoard)
    moves_made: int = 2
    moves_remaining: int = 8
    score: int = 200
    has_valid_moves: bool = True


@dataclass
class _MoveResult:
    was_valid_match: bool = True
    total_matches: int = 1
    chain_count: int = 0
    special_gems_created: list[Any] = field(default_factory=list)
    final_board: _FakeBoard | None = field(default_factory=_FakeBoard)
    cascades: list[Any] = field(default_factory=list)


@dataclass
class _RewardResult:
    awarded: bool = False
    cards: list[Any] = field(default_factory=list)
    tier: str = ""


@dataclass
class _MoveSubmissionResult:
    move_result: _MoveResult = field(default_factory=_MoveResult)
    match_state: _MatchState = field(
        default_factory=lambda: _MatchState(match_id=uuid4())
    )
    match_completed: bool = False
    points_earned: int = 100
    moves_remaining: int = 9
    move_number: int = 1
    player_finished: bool = False
    raid_result: object = None
    reward_result: _RewardResult | None = None


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

_PLAYER_ID = "00000000-0000-0000-0000-000000000001"


class _TestAuthMiddleware(BaseHTTPMiddleware):
    """Injects authenticated player context into request.state."""

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
    """Create a mock error service that produces real AppError instances."""
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
    match_service: AsyncMock | None = None,
    auth_type: str = "jwt",
    player_id: str = _PLAYER_ID,
) -> FastAPI:
    from src.modules.api.routes.matches import router

    app = FastAPI()
    app.add_middleware(_TestAuthMiddleware, player_id=player_id, auth_type=auth_type)

    app.state.config = MagicMock()
    app.state.config.get = MagicMock(return_value=True)
    app.state.logger = MagicMock()
    app.state.errors = _create_mock_error_service()
    app.state.response_adapter = ResponseAdapter()
    app.state.bot_hint_generator = BotHintGenerator()

    if match_service is not None:
        app.state.match_service = match_service

    register_error_handlers(app)
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetActiveMatches:
    """GET /api/v1/matches/active"""

    def test_success_returns_list(self) -> None:
        mock_svc = AsyncMock()
        match_state = _MatchState(
            match_id=uuid4(),
            player1=_PlayerMatchState(player_id=UUID(_PLAYER_ID), player_username="me"),
            player2=_PlayerMatchState(player_id=uuid4(), player_username="opp"),
        )
        mock_svc.get_active_matches.return_value = [match_state]

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/matches/active")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]["matches"]) == 1
        assert data["data"]["matches"][0]["status"] == "in_progress"

    def test_empty_list(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_active_matches.return_value = []

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/matches/active")

        assert resp.status_code == 200
        assert resp.json()["data"]["matches"] == []


class TestGetMatch:
    """GET /api/v1/matches/{match_id}"""

    def test_success(self) -> None:
        match_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.get_match.return_value = _MatchState(
            match_id=match_id,
            player1=_PlayerMatchState(player_id=UUID(_PLAYER_ID)),
            player2=_PlayerMatchState(player_id=uuid4()),
        )

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/matches/{match_id}")

        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["data"]["match_id"] == str(match_id)

    def test_not_found(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_match.side_effect = AppError(
            code="NOT_FOUND_MATCH",
            message="Match not found",
            http_status=404,
        )

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/matches/{uuid4()}")

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND_MATCH"


class TestGetMatchState:
    """GET /api/v1/matches/{match_id}/state"""

    def _make_match_state(self, match_id: UUID) -> _MatchState:
        return _MatchState(
            match_id=match_id,
            player1=_PlayerMatchState(
                player_id=UUID(_PLAYER_ID),
                player_username="me",
                score=100,
                current_board=_FakeBoard(),
            ),
            player2=_PlayerMatchState(
                player_id=uuid4(),
                player_username="opp",
                score=50,
            ),
        )

    def test_jwt_no_bot_hints(self) -> None:
        match_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.get_match.return_value = self._make_match_state(match_id)

        app = _create_test_app(match_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.get(f"/api/v1/matches/{match_id}/state")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["bot_hints"] is None

    def test_api_key_with_bot_hints(self) -> None:
        match_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.get_match.return_value = self._make_match_state(match_id)

        app = _create_test_app(match_service=mock_svc, auth_type="api_key")
        client = TestClient(app)
        resp = client.get(f"/api/v1/matches/{match_id}/state")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["bot_hints"] is not None
        assert "board_analysis" in data["bot_hints"]
        assert "strategic_context" in data["bot_hints"]
        assert "best_moves" in data["bot_hints"]


class TestGetBoard:
    """GET /api/v1/matches/{match_id}/board"""

    def test_success(self) -> None:
        match_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.get_player_board.return_value = _PlayerBoardState()

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/matches/{match_id}/board")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["size"] == 8
        assert data["moves_made"] == 2
        assert data["moves_remaining"] == 8
        assert data["score"] == 200
        assert data["has_valid_moves"] is True
        assert isinstance(data["cells"], list)

    def test_not_found(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_player_board.side_effect = AppError(
            code="NOT_FOUND_MATCH",
            message="Match not found",
            http_status=404,
        )

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/matches/{uuid4()}/board")

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND_MATCH"


class TestSubmitMove:
    """POST /api/v1/matches/{match_id}/move"""

    def test_success_valid_move(self) -> None:
        match_id = uuid4()
        mock_svc = AsyncMock()

        submission_result = _MoveSubmissionResult()
        submission_result.match_state = _MatchState(
            match_id=match_id,
            player1=_PlayerMatchState(
                player_id=UUID(_PLAYER_ID),
                score=100,
                moves_made=1,
            ),
            player2=_PlayerMatchState(player_id=uuid4()),
        )
        mock_svc.submit_move.return_value = submission_result

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.post(
            f"/api/v1/matches/{match_id}/move",
            json={
                "from_row": 0,
                "from_col": 0,
                "to_row": 0,
                "to_col": 1,
                "timestamp_ms": 1000,
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["valid"] is True
        assert data["score_gained"] == 100
        assert data["match_completed"] is False
        assert data["move_number"] == 1

    def test_validation_error_non_adjacent(self) -> None:
        """The MoveRequest schema validates adjacency -- non-adjacent positions
        produce a 422 Unprocessable Entity from FastAPI's request validation."""
        mock_svc = AsyncMock()

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.post(
            f"/api/v1/matches/{uuid4()}/move",
            json={
                "from_row": 0,
                "from_col": 0,
                "to_row": 5,
                "to_col": 5,
                "timestamp_ms": 1000,
            },
        )

        assert resp.status_code == 422


class TestForfeitMatch:
    """POST /api/v1/matches/{match_id}/forfeit"""

    def test_success(self) -> None:
        match_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.forfeit_match.return_value = _MatchState(
            match_id=match_id,
            status=_MatchStatus.FORFEITED,
            player1=_PlayerMatchState(player_id=UUID(_PLAYER_ID)),
            player2=_PlayerMatchState(player_id=uuid4()),
        )

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.post(f"/api/v1/matches/{match_id}/forfeit")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "forfeited"

    def test_already_completed(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.forfeit_match.side_effect = AppError(
            code="CONFLICT_MATCH_COMPLETED",
            message="Match already completed",
            http_status=409,
        )

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.post(f"/api/v1/matches/{uuid4()}/forfeit")

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONFLICT_MATCH_COMPLETED"


class TestGetMatchHistory:
    """GET /api/v1/matches/history"""

    def test_success_with_pagination(self) -> None:
        mock_svc = AsyncMock()
        summary = _MatchSummary(match_id=uuid4())
        mock_svc.get_match_history.return_value = _PaginatedResult(
            items=[summary],
            total=1,
            limit=20,
            offset=0,
            has_more=False,
        )

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.get("/api/v1/matches/history?limit=20&offset=0")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["limit"] == 20
        assert data["offset"] == 0
        assert data["has_more"] is False
        assert len(data["matches"]) == 1
        assert data["matches"][0]["won"] is True


class TestGetMoveHistory:
    """GET /api/v1/matches/{match_id}/moves"""

    def test_success(self) -> None:
        match_id = uuid4()
        mock_svc = AsyncMock()
        mock_svc.get_move_history.return_value = [
            _MoveRecord(move_number=1),
            _MoveRecord(move_number=2),
        ]

        app = _create_test_app(match_service=mock_svc)
        client = TestClient(app)
        resp = client.get(f"/api/v1/matches/{match_id}/moves")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["moves"]) == 2
        assert data["moves"][0]["move_number"] == 1
        assert data["moves"][1]["move_number"] == 2
