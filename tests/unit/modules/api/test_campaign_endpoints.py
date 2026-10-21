"""Unit tests for campaign API endpoints.

Tests the campaign router endpoints with mocked campaign_service.
Uses a self-contained test app fixture to avoid modifying the shared conftest.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import numpy as np
import pytest
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from src.core.types.board import BoardState
from src.data.protocols.campaign_attempt_repository import CampaignAttemptRecord
from src.modules.api.adapters.response import ResponseAdapter
from src.modules.api.middleware.error_handler import register_error_handlers
from src.modules.api.routes.campaign import router as campaign_router
from src.modules.board._constants import OBSTACLE_COLOR
from src.modules.board.types import MoveProcessingResult
from src.core.types.game import Move, Position


# ------------------------------------------------------------------
# Constants and Auth Middleware
# ------------------------------------------------------------------

TEST_PLAYER_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
TEST_CORRELATION_ID = "cc_campaign_test_001"


class _TestAuthMiddleware(BaseHTTPMiddleware):
    """Injects auth state for route tests."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request.state.player_id = TEST_PLAYER_ID
        request.state.auth_type = "jwt"
        request.state.correlation_id = TEST_CORRELATION_ID
        return await call_next(request)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_attempt(
    attempt_id=None,
    player_id=None,
    level_number: int = 1,
    moves_remaining: int = 20,
    obstacles_remaining: int = 4,
    status: str = "in_progress",
) -> CampaignAttemptRecord:
    """Create a CampaignAttemptRecord for testing."""
    return CampaignAttemptRecord(
        id=attempt_id or uuid4(),
        player_id=player_id or UUID(TEST_PLAYER_ID),
        level_number=level_number,
        board_seed=42,
        board_state={
            "cells": [[1] * 8 for _ in range(8)],
            "functions": [[0] * 8 for _ in range(8)],
        },
        moves_remaining=moves_remaining,
        obstacles_remaining=obstacles_remaining,
        status=status,
        score=0,
    )


def _make_board() -> BoardState:
    """Create a simple 8x8 BoardState."""
    grid = np.ones((8, 8), dtype=np.int8)
    func = np.zeros((8, 8), dtype=np.int8)
    return BoardState(grid=grid, func_grid=func)


def _make_move_result(valid: bool = True) -> MoveProcessingResult:
    """Create a MoveProcessingResult for move endpoint testing."""
    board = _make_board()
    move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
    return MoveProcessingResult(
        initial_board=board,
        final_board=board,
        move=move,
        was_valid_match=valid,
        cascades=[],
        total_matches=1 if valid else 0,
        total_gems_cleared=3 if valid else 0,
        chain_count=1 if valid else 0,
        special_gems_created=[],
    )


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def mock_campaign_service() -> AsyncMock:
    """Mock campaign service with default returns."""
    svc = AsyncMock()

    # get_level_definition is sync (no await in routes) — use MagicMock.
    svc.get_level_definition = MagicMock(return_value={
        "level": 1,
        "moves": 30,
        "gem_colors": 6,
        "objective": "Clear all obstacles",
        "obstacles": [{"row": 0, "col": 0, "func": 0}],
        "is_checkpoint": False,
        "heart_cost": 0,
    })

    # max_level is accessed as an attribute (no await) — set directly.
    svc.max_level = 3

    # get_player_progress.
    svc.get_player_progress.return_value = {
        "campaign_level": 1,
        "max_level": 3,
        "active_attempt_id": None,
    }

    # start_attempt.
    attempt = _make_attempt()
    board = _make_board()
    svc.start_attempt.return_value = (attempt, board)

    # submit_move.
    move_result = _make_move_result(valid=True)
    svc.submit_move.return_value = {
        "move_result": move_result,
        "obstacles_remaining": 3,
        "moves_remaining": 19,
        "status": "in_progress",
        "obstacle_events": [],
        "score_gained": 50,
    }

    # abandon_attempt.
    svc.abandon_attempt.return_value = _make_attempt(status="abandoned")

    # _campaign_repo for get_attempt endpoint.
    svc._campaign_repo = AsyncMock()
    svc._campaign_repo.find_by_id.return_value = _make_attempt()

    return svc


@pytest.fixture
def mock_errors() -> MagicMock:
    """Mock error service."""
    from tests.mocks.services import MockLogService, MockErrorService

    logger = MockLogService()
    return MockErrorService(logger)


@pytest.fixture
def campaign_app(
    mock_campaign_service: AsyncMock,
    mock_errors: MagicMock,
) -> FastAPI:
    """Create a test FastAPI app with campaign router."""
    app = FastAPI()

    app.state.campaign_service = mock_campaign_service
    app.state.errors = mock_errors
    app.state.response_adapter = ResponseAdapter()

    app.add_middleware(_TestAuthMiddleware)
    register_error_handlers(app)
    app.include_router(campaign_router)

    return app


@pytest.fixture
def client(campaign_app: FastAPI) -> TestClient:
    """Test client for campaign endpoints."""
    return TestClient(campaign_app, raise_server_exceptions=False)


# ==================================================================
# GET /api/v1/campaign/levels
# ==================================================================


class TestListLevels:
    """Tests for GET /api/v1/campaign/levels."""

    def test_list_levels_success(
        self,
        client: TestClient,
        mock_campaign_service: AsyncMock,
    ) -> None:
        """Lists all levels with unlock status."""
        resp = client.get("/api/v1/campaign/levels")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "levels" in data
        assert "campaign_level" in data
        assert data["campaign_level"] == 1

    def test_list_levels_includes_level_metadata(
        self,
        client: TestClient,
        mock_campaign_service: AsyncMock,
    ) -> None:
        """Each level includes moves, objective, checkpoint info."""
        resp = client.get("/api/v1/campaign/levels")

        data = resp.json()["data"]
        levels = data["levels"]
        assert len(levels) > 0
        level = levels[0]
        assert "level" in level
        assert "moves" in level
        assert "objective" in level
        assert "is_checkpoint" in level
        assert "unlocked" in level


# ==================================================================
# GET /api/v1/campaign/levels/{level_number}
# ==================================================================


class TestGetLevel:
    """Tests for GET /api/v1/campaign/levels/{level_number}."""

    def test_get_level_success(
        self,
        client: TestClient,
    ) -> None:
        """Returns level definition."""
        resp = client.get("/api/v1/campaign/levels/1")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["level"] == 1
        assert data["moves"] == 30
        assert "obstacles" in data


# ==================================================================
# GET /api/v1/campaign/progress
# ==================================================================


class TestGetProgress:
    """Tests for GET /api/v1/campaign/progress."""

    def test_progress_success(
        self,
        client: TestClient,
    ) -> None:
        """Returns player campaign progress."""
        resp = client.get("/api/v1/campaign/progress")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["campaign_level"] == 1
        assert data["active_attempt_id"] is None


# ==================================================================
# POST /api/v1/campaign/attempts
# ==================================================================


class TestStartAttempt:
    """Tests for POST /api/v1/campaign/attempts."""

    def test_start_attempt_success(
        self,
        client: TestClient,
    ) -> None:
        """Starting an attempt returns attempt_id and board."""
        resp = client.post(
            "/api/v1/campaign/attempts",
            json={"level_number": 1},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "attempt_id" in data
        assert "board" in data
        assert "cells" in data["board"]
        assert "functions" in data["board"]
        assert data["status"] == "in_progress"


# ==================================================================
# GET /api/v1/campaign/attempts/{attempt_id}
# ==================================================================


class TestGetAttempt:
    """Tests for GET /api/v1/campaign/attempts/{attempt_id}."""

    def test_get_attempt_success(
        self,
        client: TestClient,
        mock_campaign_service: AsyncMock,
    ) -> None:
        """Returns attempt state."""
        attempt = _make_attempt()
        mock_campaign_service._campaign_repo.find_by_id.return_value = attempt

        resp = client.get(f"/api/v1/campaign/attempts/{attempt.id}")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["attempt_id"] == str(attempt.id)
        assert data["moves_remaining"] == 20
        assert data["obstacles_remaining"] == 4
        assert data["status"] == "in_progress"

    def test_get_attempt_not_found(
        self,
        client: TestClient,
        mock_campaign_service: AsyncMock,
    ) -> None:
        """Non-existent attempt returns 404."""
        mock_campaign_service._campaign_repo.find_by_id.return_value = None

        resp = client.get(f"/api/v1/campaign/attempts/{uuid4()}")

        assert resp.status_code == 404

    def test_get_attempt_wrong_player(
        self,
        client: TestClient,
        mock_campaign_service: AsyncMock,
    ) -> None:
        """Attempt owned by another player returns 403."""
        other_player = uuid4()
        attempt = _make_attempt(player_id=other_player)
        mock_campaign_service._campaign_repo.find_by_id.return_value = attempt

        resp = client.get(f"/api/v1/campaign/attempts/{attempt.id}")

        assert resp.status_code == 403


# ==================================================================
# POST /api/v1/campaign/attempts/{attempt_id}/move
# ==================================================================


class TestSubmitMove:
    """Tests for POST /api/v1/campaign/attempts/{attempt_id}/move."""

    def test_submit_move_success(
        self,
        client: TestClient,
    ) -> None:
        """Valid move returns new board state and status."""
        attempt_id = uuid4()
        resp = client.post(
            f"/api/v1/campaign/attempts/{attempt_id}/move",
            json={
                "from_row": 3,
                "from_col": 3,
                "to_row": 3,
                "to_col": 4,
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["valid"] is True
        assert "new_board" in data
        assert "cascade_steps" in data
        assert "obstacles_remaining" in data
        assert "moves_remaining" in data
        assert "status" in data
        assert "obstacle_events" in data

    def test_submit_move_response_structure(
        self,
        client: TestClient,
    ) -> None:
        """Move response contains all expected fields."""
        attempt_id = uuid4()
        resp = client.post(
            f"/api/v1/campaign/attempts/{attempt_id}/move",
            json={
                "from_row": 0,
                "from_col": 0,
                "to_row": 0,
                "to_col": 1,
            },
        )

        data = resp.json()["data"]
        assert isinstance(data["cascade_steps"], list)
        assert isinstance(data["applied_modifiers"], list)
        assert isinstance(data["obstacle_events"], list)
        assert isinstance(data["obstacles_remaining"], int)
        assert isinstance(data["moves_remaining"], int)


# ==================================================================
# POST /api/v1/campaign/attempts/{attempt_id}/abandon
# ==================================================================


class TestAbandonAttempt:
    """Tests for POST /api/v1/campaign/attempts/{attempt_id}/abandon."""

    def test_abandon_success(
        self,
        client: TestClient,
    ) -> None:
        """Abandoning an attempt returns updated status."""
        attempt_id = uuid4()
        resp = client.post(
            f"/api/v1/campaign/attempts/{attempt_id}/abandon",
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "abandoned"
        assert "attempt_id" in data
