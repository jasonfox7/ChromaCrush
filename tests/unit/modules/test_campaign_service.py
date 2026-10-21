"""Unit tests for CampaignService.

Tests: start attempt, submit moves, obstacle counting, level completion,
checkpoint regression, heart cost enforcement, and error cases.

All dependencies are mocked — no database or network calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from src.core.errors import AppError
from src.core.types.board import BoardState
from src.core.types.game import GemType, Move, Position
from src.data.protocols.campaign_attempt_repository import CampaignAttemptRecord
from src.modules.board._constants import OBSTACLE_COLOR
from src.modules.board.types import MoveProcessingResult
from src.modules.campaign.service import CampaignService
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_player(
    player_id=None, campaign_level: int = 1, **extra
) -> MagicMock:
    """Create a mock player record."""
    p = MagicMock()
    p.id = player_id or uuid4()
    p.campaign_level = campaign_level
    for k, v in extra.items():
        setattr(p, k, v)
    return p


def _make_attempt(
    attempt_id=None,
    player_id=None,
    level_number: int = 1,
    board_seed: int = 42,
    moves_remaining: int = 20,
    obstacles_remaining: int = 4,
    status: str = "in_progress",
) -> CampaignAttemptRecord:
    """Create a CampaignAttemptRecord for testing."""
    # Build a simple 8x8 board state with a few obstacles.
    grid = np.ones((8, 8), dtype=np.int8)  # all color 1
    func = np.zeros((8, 8), dtype=np.int8)
    # Place obstacles.
    obs_positions = [(0, 0), (0, 7), (7, 0), (7, 7)]
    for r, c in obs_positions[:obstacles_remaining]:
        grid[r, c] = OBSTACLE_COLOR
        func[r, c] = 0
    board_state = {
        "cells": grid.tolist(),
        "functions": func.tolist(),
    }

    return CampaignAttemptRecord(
        id=attempt_id or uuid4(),
        player_id=player_id or uuid4(),
        level_number=level_number,
        board_seed=board_seed,
        board_state=board_state,
        moves_remaining=moves_remaining,
        obstacles_remaining=obstacles_remaining,
        status=status,
        score=0,
    )


def _make_move_result(
    valid: bool = True,
    obstacles_cleared: int = 0,
    obstacles_on_board: int = 4,
) -> MoveProcessingResult:
    """Create a MoveProcessingResult for testing."""
    grid = np.ones((8, 8), dtype=np.int8)
    func = np.zeros((8, 8), dtype=np.int8)
    # Place obstacles on the result board so obstacle counting works.
    obs_positions = [(0, 0), (0, 7), (7, 0), (7, 7)]
    for r, c in obs_positions[:obstacles_on_board]:
        grid[r, c] = OBSTACLE_COLOR
    board = BoardState(grid=grid, func_grid=func)
    move = Move(
        from_pos=Position(0, 0),
        to_pos=Position(0, 1),
        timestamp_ms=0,
    )
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
        obstacle_clearings=[Position(0, 0)] * obstacles_cleared,
        obstacle_transmutations=[],
    )


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def mock_config() -> MockConfigService:
    return MockConfigService()


@pytest.fixture
def mock_logger() -> MockLogService:
    return MockLogService()


@pytest.fixture
def mock_errors(mock_logger: MockLogService) -> MockErrorService:
    return MockErrorService(mock_logger)


@pytest.fixture
def mock_board_service() -> MagicMock:
    svc = MagicMock()
    # create_board_with_obstacles returns a board with some obstacles.
    grid = np.ones((8, 8), dtype=np.int8)
    func = np.zeros((8, 8), dtype=np.int8)
    # Put 4 obstacles in corners.
    for r, c in [(0, 0), (0, 7), (7, 0), (7, 7)]:
        grid[r, c] = OBSTACLE_COLOR
    board = BoardState(grid=grid, func_grid=func)
    svc.create_board_with_obstacles.return_value = board
    # process_move returns a valid result with no obstacle clears by default.
    svc.process_move.return_value = _make_move_result(valid=True)
    return svc


@pytest.fixture
def mock_energy_service() -> AsyncMock:
    svc = AsyncMock()
    svc.can_play.return_value = True
    svc.consume_heart.return_value = MagicMock()
    return svc


@pytest.fixture
def mock_player_repo() -> AsyncMock:
    repo = AsyncMock()
    player = _make_player(campaign_level=5)
    repo.find_by_id.return_value = player
    repo.update.return_value = player
    return repo


@pytest.fixture
def mock_campaign_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.find_active_by_player.return_value = None
    repo.create.return_value = _make_attempt()
    repo.find_by_id.return_value = _make_attempt()
    repo.update.return_value = _make_attempt(status="in_progress")
    return repo


@pytest.fixture
def campaign_service(
    mock_config: MockConfigService,
    mock_logger: MockLogService,
    mock_errors: MockErrorService,
    mock_board_service: MagicMock,
    mock_energy_service: AsyncMock,
    mock_player_repo: AsyncMock,
    mock_campaign_repo: AsyncMock,
) -> CampaignService:
    return CampaignService(
        config=mock_config,
        logger=mock_logger,
        errors=mock_errors,
        board_service=mock_board_service,
        energy_service=mock_energy_service,
        player_repo=mock_player_repo,
        campaign_repo=mock_campaign_repo,
    )


# ==================================================================
# start_attempt tests
# ==================================================================


class TestStartAttempt:
    """Tests for CampaignService.start_attempt."""

    @pytest.mark.asyncio
    async def test_start_attempt_success(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Happy path: player starts a valid level."""
        player_id = uuid4()
        attempt, board = await campaign_service.start_attempt(player_id, 1)

        mock_campaign_repo.create.assert_awaited_once()
        assert attempt is not None
        assert board is not None

    @pytest.mark.asyncio
    async def test_start_attempt_level_locked(
        self,
        campaign_service: CampaignService,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Player cannot start a level higher than their campaign_level."""
        player = _make_player(campaign_level=3)
        mock_player_repo.find_by_id.return_value = player

        with pytest.raises(AppError) as exc_info:
            await campaign_service.start_attempt(player.id, 5)
        assert exc_info.value.code == "FORBIDDEN_LEVEL_LOCKED"

    @pytest.mark.asyncio
    async def test_start_attempt_player_not_found(
        self,
        campaign_service: CampaignService,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Player not found raises NOT_FOUND_PLAYER."""
        mock_player_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await campaign_service.start_attempt(uuid4(), 1)
        assert exc_info.value.code == "NOT_FOUND_PLAYER"

    @pytest.mark.asyncio
    async def test_start_attempt_abandons_active(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Starting a new attempt abandons any existing active attempt."""
        active = _make_attempt(status="in_progress")
        mock_campaign_repo.find_active_by_player.return_value = active

        player_id = uuid4()
        await campaign_service.start_attempt(player_id, 1)

        mock_campaign_repo.update.assert_any_await(active.id, status="abandoned")

    @pytest.mark.asyncio
    async def test_start_attempt_checkpoint_deducts_heart(
        self,
        campaign_service: CampaignService,
        mock_energy_service: AsyncMock,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Checkpoint levels deduct a heart."""
        # Player must have campaign_level >= 10 to unlock level 10.
        player = _make_player(campaign_level=10)
        mock_player_repo.find_by_id.return_value = player

        campaign_service._level_loader = MagicMock()
        campaign_service._level_loader.get.return_value = {
            "level": 10,
            "moves": 25,
            "obstacles": [{"row": 0, "col": 0, "func": 0}],
            "is_checkpoint": True,
            "heart_cost": 1,
        }
        campaign_service._level_loader.max_level = 100

        await campaign_service.start_attempt(player.id, 10)

        mock_energy_service.can_play.assert_awaited_once()
        mock_energy_service.consume_heart.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_attempt_insufficient_hearts(
        self,
        campaign_service: CampaignService,
        mock_energy_service: AsyncMock,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Checkpoint level with insufficient hearts raises FORBIDDEN."""
        player = _make_player(campaign_level=10)
        mock_player_repo.find_by_id.return_value = player

        campaign_service._level_loader = MagicMock()
        campaign_service._level_loader.get.return_value = {
            "level": 10,
            "moves": 25,
            "obstacles": [{"row": 0, "col": 0, "func": 0}],
            "is_checkpoint": True,
            "heart_cost": 1,
        }
        campaign_service._level_loader.max_level = 100

        mock_energy_service.can_play.return_value = False

        with pytest.raises(AppError) as exc_info:
            await campaign_service.start_attempt(player.id, 10)
        assert exc_info.value.code == "FORBIDDEN_INSUFFICIENT_ENERGY"

    @pytest.mark.asyncio
    async def test_start_attempt_nonexistent_level(
        self,
        campaign_service: CampaignService,
    ) -> None:
        """Starting a level that doesn't exist raises NOT_FOUND."""
        campaign_service._level_loader = MagicMock()
        campaign_service._level_loader.get.return_value = None

        with pytest.raises(AppError) as exc_info:
            await campaign_service.start_attempt(uuid4(), 999)
        assert exc_info.value.code == "NOT_FOUND_CAMPAIGN_LEVEL"


# ==================================================================
# submit_move tests
# ==================================================================


class TestSubmitMove:
    """Tests for CampaignService.submit_move."""

    @pytest.mark.asyncio
    async def test_submit_move_success(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
        mock_board_service: MagicMock,
    ) -> None:
        """Happy path: valid move decrements moves_remaining."""
        attempt = _make_attempt(moves_remaining=10, obstacles_remaining=4)
        mock_campaign_repo.find_by_id.return_value = attempt

        move = Move(from_pos=Position(3, 3), to_pos=Position(3, 4), timestamp_ms=0)
        result = await campaign_service.submit_move(
            attempt.id, attempt.player_id, move
        )

        assert result["moves_remaining"] == 9
        assert result["status"] == "in_progress"
        mock_campaign_repo.update.assert_awaited()

    @pytest.mark.asyncio
    async def test_submit_move_invalid_swap_raises(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
        mock_board_service: MagicMock,
    ) -> None:
        """Invalid swap (no matches) raises VALIDATION error."""
        attempt = _make_attempt()
        mock_campaign_repo.find_by_id.return_value = attempt
        mock_board_service.process_move.return_value = _make_move_result(valid=False)

        move = Move(from_pos=Position(3, 3), to_pos=Position(3, 4), timestamp_ms=0)
        with pytest.raises(AppError) as exc_info:
            await campaign_service.submit_move(
                attempt.id, attempt.player_id, move
            )
        assert exc_info.value.code == "VALIDATION_INVALID_GEM_SWAP"

    @pytest.mark.asyncio
    async def test_submit_move_attempt_not_found(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Attempt not found raises NOT_FOUND."""
        mock_campaign_repo.find_by_id.return_value = None

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        with pytest.raises(AppError) as exc_info:
            await campaign_service.submit_move(uuid4(), uuid4(), move)
        assert exc_info.value.code == "NOT_FOUND_CAMPAIGN_ATTEMPT"

    @pytest.mark.asyncio
    async def test_submit_move_wrong_player(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Attempt owned by different player raises FORBIDDEN."""
        attempt = _make_attempt()
        mock_campaign_repo.find_by_id.return_value = attempt

        other_player = uuid4()
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        with pytest.raises(AppError) as exc_info:
            await campaign_service.submit_move(attempt.id, other_player, move)
        assert exc_info.value.code == "FORBIDDEN_NOT_OWNER"

    @pytest.mark.asyncio
    async def test_submit_move_attempt_already_finished(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Submitting to a won/lost/abandoned attempt raises CONFLICT."""
        attempt = _make_attempt(status="won")
        mock_campaign_repo.find_by_id.return_value = attempt

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        with pytest.raises(AppError) as exc_info:
            await campaign_service.submit_move(
                attempt.id, attempt.player_id, move
            )
        assert exc_info.value.code == "CONFLICT_ATTEMPT_FINISHED"


# ==================================================================
# Win / lose conditions
# ==================================================================


class TestWinLoseConditions:
    """Tests for level completion and failure logic."""

    @pytest.mark.asyncio
    async def test_all_obstacles_cleared_is_win(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
        mock_board_service: MagicMock,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Clearing all obstacles sets status to 'won'."""
        attempt = _make_attempt(
            moves_remaining=5, obstacles_remaining=1,
        )
        mock_campaign_repo.find_by_id.return_value = attempt

        # Build a result board with NO obstacles.
        grid = np.ones((8, 8), dtype=np.int8)
        func = np.zeros((8, 8), dtype=np.int8)
        result_board = BoardState(grid=grid, func_grid=func)
        move_result = _make_move_result(valid=True)
        move_result.final_board = result_board
        mock_board_service.process_move.return_value = move_result

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        result = await campaign_service.submit_move(
            attempt.id, attempt.player_id, move
        )

        assert result["status"] == "won"
        assert result["obstacles_remaining"] == 0

    @pytest.mark.asyncio
    async def test_no_moves_left_with_obstacles_is_lose(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
        mock_board_service: MagicMock,
    ) -> None:
        """Running out of moves with obstacles remaining sets status to 'lost'."""
        attempt = _make_attempt(
            moves_remaining=1, obstacles_remaining=3,
        )
        mock_campaign_repo.find_by_id.return_value = attempt

        # Result board still has obstacles.
        grid = np.ones((8, 8), dtype=np.int8)
        grid[0, 0] = OBSTACLE_COLOR
        grid[0, 7] = OBSTACLE_COLOR
        grid[7, 0] = OBSTACLE_COLOR
        func = np.zeros((8, 8), dtype=np.int8)
        result_board = BoardState(grid=grid, func_grid=func)
        move_result = _make_move_result(valid=True)
        move_result.final_board = result_board
        mock_board_service.process_move.return_value = move_result

        move = Move(from_pos=Position(3, 3), to_pos=Position(3, 4), timestamp_ms=0)
        result = await campaign_service.submit_move(
            attempt.id, attempt.player_id, move
        )

        assert result["status"] == "lost"
        assert result["moves_remaining"] == 0

    @pytest.mark.asyncio
    async def test_moves_and_obstacles_remaining_is_in_progress(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
        mock_board_service: MagicMock,
    ) -> None:
        """With moves and obstacles both remaining, status stays 'in_progress'."""
        attempt = _make_attempt(
            moves_remaining=10, obstacles_remaining=3,
        )
        mock_campaign_repo.find_by_id.return_value = attempt

        # Result board still has obstacles.
        grid = np.ones((8, 8), dtype=np.int8)
        grid[0, 0] = OBSTACLE_COLOR
        grid[0, 7] = OBSTACLE_COLOR
        func = np.zeros((8, 8), dtype=np.int8)
        result_board = BoardState(grid=grid, func_grid=func)
        move_result = _make_move_result(valid=True)
        move_result.final_board = result_board
        mock_board_service.process_move.return_value = move_result

        move = Move(from_pos=Position(3, 3), to_pos=Position(3, 4), timestamp_ms=0)
        result = await campaign_service.submit_move(
            attempt.id, attempt.player_id, move
        )

        assert result["status"] == "in_progress"
        assert result["moves_remaining"] == 9
        assert result["obstacles_remaining"] == 2


# ==================================================================
# Level progression and regression
# ==================================================================


class TestLevelProgression:
    """Tests for campaign_level advancement and checkpoint regression."""

    @pytest.mark.asyncio
    async def test_win_advances_campaign_level(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
        mock_board_service: MagicMock,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Winning the frontier level advances campaign_level."""
        player = _make_player(campaign_level=5)
        mock_player_repo.find_by_id.return_value = player

        attempt = _make_attempt(
            player_id=player.id,
            level_number=5,
            moves_remaining=5,
            obstacles_remaining=1,
        )
        mock_campaign_repo.find_by_id.return_value = attempt

        # No obstacles on result board → win.
        grid = np.ones((8, 8), dtype=np.int8)
        func = np.zeros((8, 8), dtype=np.int8)
        move_result = _make_move_result(valid=True)
        move_result.final_board = BoardState(grid=grid, func_grid=func)
        mock_board_service.process_move.return_value = move_result

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        result = await campaign_service.submit_move(
            attempt.id, player.id, move
        )

        assert result["status"] == "won"
        mock_player_repo.update.assert_awaited_with(player.id, campaign_level=6)

    @pytest.mark.asyncio
    async def test_win_replay_does_not_advance(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
        mock_board_service: MagicMock,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Replaying an earlier level (below frontier) doesn't advance."""
        player = _make_player(campaign_level=10)
        mock_player_repo.find_by_id.return_value = player

        attempt = _make_attempt(
            player_id=player.id,
            level_number=3,  # Below frontier
            moves_remaining=5,
            obstacles_remaining=1,
        )
        mock_campaign_repo.find_by_id.return_value = attempt

        grid = np.ones((8, 8), dtype=np.int8)
        func = np.zeros((8, 8), dtype=np.int8)
        move_result = _make_move_result(valid=True)
        move_result.final_board = BoardState(grid=grid, func_grid=func)
        mock_board_service.process_move.return_value = move_result

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        await campaign_service.submit_move(attempt.id, player.id, move)

        # Should NOT call update (level 3 < campaign_level 10).
        mock_player_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_checkpoint_loss_regresses_by_5(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
        mock_board_service: MagicMock,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Losing a checkpoint level regresses campaign_level by 5."""
        player = _make_player(campaign_level=20)
        mock_player_repo.find_by_id.return_value = player

        # Mock level loader to return checkpoint.
        campaign_service._level_loader = MagicMock()
        campaign_service._level_loader.get.return_value = {
            "level": 20,
            "moves": 20,
            "obstacles": [],
            "is_checkpoint": True,
            "heart_cost": 1,
        }
        campaign_service._level_loader.max_level = 100

        attempt = _make_attempt(
            player_id=player.id,
            level_number=20,
            moves_remaining=1,
            obstacles_remaining=3,
        )
        mock_campaign_repo.find_by_id.return_value = attempt

        # Still has obstacles → lose (moves = 1 → 0).
        grid = np.ones((8, 8), dtype=np.int8)
        grid[0, 0] = OBSTACLE_COLOR
        func = np.zeros((8, 8), dtype=np.int8)
        move_result = _make_move_result(valid=True)
        move_result.final_board = BoardState(grid=grid, func_grid=func)
        mock_board_service.process_move.return_value = move_result

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        result = await campaign_service.submit_move(
            attempt.id, player.id, move
        )

        assert result["status"] == "lost"
        # Regression: 20 - 5 = 15.
        mock_player_repo.update.assert_awaited_with(player.id, campaign_level=15)

    @pytest.mark.asyncio
    async def test_non_checkpoint_loss_no_regression(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
        mock_board_service: MagicMock,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Losing a non-checkpoint level does NOT regress."""
        player = _make_player(campaign_level=7)
        mock_player_repo.find_by_id.return_value = player

        # Mock level loader for non-checkpoint.
        campaign_service._level_loader = MagicMock()
        campaign_service._level_loader.get.return_value = {
            "level": 7,
            "moves": 25,
            "obstacles": [],
        }
        campaign_service._level_loader.max_level = 100

        attempt = _make_attempt(
            player_id=player.id,
            level_number=7,
            moves_remaining=1,
            obstacles_remaining=2,
        )
        mock_campaign_repo.find_by_id.return_value = attempt

        grid = np.ones((8, 8), dtype=np.int8)
        grid[0, 0] = OBSTACLE_COLOR
        func = np.zeros((8, 8), dtype=np.int8)
        move_result = _make_move_result(valid=True)
        move_result.final_board = BoardState(grid=grid, func_grid=func)
        mock_board_service.process_move.return_value = move_result

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        result = await campaign_service.submit_move(
            attempt.id, player.id, move
        )

        assert result["status"] == "lost"
        # No regression on non-checkpoint.
        mock_player_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_checkpoint_regression_floor_is_1(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
        mock_board_service: MagicMock,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Checkpoint regression cannot go below level 1."""
        player = _make_player(campaign_level=3)
        mock_player_repo.find_by_id.return_value = player

        campaign_service._level_loader = MagicMock()
        campaign_service._level_loader.get.return_value = {
            "level": 3,
            "moves": 20,
            "obstacles": [],
            "is_checkpoint": True,
            "heart_cost": 1,
        }
        campaign_service._level_loader.max_level = 100

        attempt = _make_attempt(
            player_id=player.id,
            level_number=3,
            moves_remaining=1,
            obstacles_remaining=2,
        )
        mock_campaign_repo.find_by_id.return_value = attempt

        grid = np.ones((8, 8), dtype=np.int8)
        grid[0, 0] = OBSTACLE_COLOR
        func = np.zeros((8, 8), dtype=np.int8)
        move_result = _make_move_result(valid=True)
        move_result.final_board = BoardState(grid=grid, func_grid=func)
        mock_board_service.process_move.return_value = move_result

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        await campaign_service.submit_move(attempt.id, player.id, move)

        # max(1, 3-5) = 1 — regression, but capped at 1.
        mock_player_repo.update.assert_awaited_with(player.id, campaign_level=1)


# ==================================================================
# abandon_attempt tests
# ==================================================================


class TestAbandonAttempt:
    """Tests for CampaignService.abandon_attempt."""

    @pytest.mark.asyncio
    async def test_abandon_success(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Abandoning an in-progress attempt sets status to 'abandoned'."""
        attempt = _make_attempt(status="in_progress")
        mock_campaign_repo.find_by_id.return_value = attempt
        mock_campaign_repo.update.return_value = _make_attempt(status="abandoned")

        result = await campaign_service.abandon_attempt(
            attempt.id, attempt.player_id
        )

        mock_campaign_repo.update.assert_awaited_with(attempt.id, status="abandoned")

    @pytest.mark.asyncio
    async def test_abandon_not_found(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Abandoning a non-existent attempt raises NOT_FOUND."""
        mock_campaign_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await campaign_service.abandon_attempt(uuid4(), uuid4())
        assert exc_info.value.code == "NOT_FOUND_CAMPAIGN_ATTEMPT"

    @pytest.mark.asyncio
    async def test_abandon_wrong_player(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Abandoning another player's attempt raises FORBIDDEN."""
        attempt = _make_attempt()
        mock_campaign_repo.find_by_id.return_value = attempt

        with pytest.raises(AppError) as exc_info:
            await campaign_service.abandon_attempt(attempt.id, uuid4())
        assert exc_info.value.code == "FORBIDDEN_NOT_OWNER"

    @pytest.mark.asyncio
    async def test_abandon_already_finished(
        self,
        campaign_service: CampaignService,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Abandoning a finished attempt raises CONFLICT."""
        attempt = _make_attempt(status="won")
        mock_campaign_repo.find_by_id.return_value = attempt

        with pytest.raises(AppError) as exc_info:
            await campaign_service.abandon_attempt(attempt.id, attempt.player_id)
        assert exc_info.value.code == "CONFLICT_ATTEMPT_FINISHED"


# ==================================================================
# get_player_progress tests
# ==================================================================


class TestGetPlayerProgress:
    """Tests for CampaignService.get_player_progress."""

    @pytest.mark.asyncio
    async def test_progress_with_no_active_attempt(
        self,
        campaign_service: CampaignService,
        mock_player_repo: AsyncMock,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Player progress with no active attempt."""
        player = _make_player(campaign_level=15)
        mock_player_repo.find_by_id.return_value = player
        mock_campaign_repo.find_active_by_player.return_value = None

        result = await campaign_service.get_player_progress(player.id)

        assert result["campaign_level"] == 15
        assert result["active_attempt_id"] is None

    @pytest.mark.asyncio
    async def test_progress_with_active_attempt(
        self,
        campaign_service: CampaignService,
        mock_player_repo: AsyncMock,
        mock_campaign_repo: AsyncMock,
    ) -> None:
        """Player progress with an active attempt includes attempt_id."""
        player = _make_player(campaign_level=15)
        mock_player_repo.find_by_id.return_value = player
        active = _make_attempt(player_id=player.id)
        mock_campaign_repo.find_active_by_player.return_value = active

        result = await campaign_service.get_player_progress(player.id)

        assert result["campaign_level"] == 15
        assert result["active_attempt_id"] == str(active.id)

    @pytest.mark.asyncio
    async def test_progress_player_not_found(
        self,
        campaign_service: CampaignService,
        mock_player_repo: AsyncMock,
    ) -> None:
        """Player not found raises NOT_FOUND_PLAYER."""
        mock_player_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await campaign_service.get_player_progress(uuid4())
        assert exc_info.value.code == "NOT_FOUND_PLAYER"
