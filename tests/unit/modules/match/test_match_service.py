"""Comprehensive unit tests for MatchService.

Tests all 9 public methods plus private helper behavior (via public API):
create_match, submit_move, get_match, get_match_state, get_player_board,
get_active_matches, forfeit_match, get_match_history, get_move_history,
abandon_stale_matches, and _finalize_match (tested through submit_move
and forfeit_match).

Uses pytest + pytest-asyncio with AsyncMock/MagicMock dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import numpy as np
import pytest

from src.core.errors import AppError
from src.core.types.board import BoardState
from src.core.types.game import GemType, MatchId, Move, PlayerId, Position
from src.modules.board.types import MoveProcessingResult
from src.modules.board_gen.types import GeneratedBoard, GenerationMetadata
from src.modules.board_gen.types import MatchType as BoardGenMatchType
from src.modules.match.dto import PaginatedResult
from src.modules.match.service import MatchRepositoryBundle, MatchService
from src.modules.match.types import (
    MatchState,
    MatchStatus,
    MatchSummary,
    MatchType,
    MoveRecord,
    MoveSubmissionResult,
    PlayerBoardState,
    PlayerMatchState,
)
from src.modules.scoring.types import MoveScore, SpecialGemBonus
from src.modules.special_gems.types import SpecialGemEffect
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ============================================================================
# Helpers
# ============================================================================


def make_player(
    player_id: PlayerId | None = None, username: str = "player"
) -> MagicMock:
    """Create a mock Player-like object."""
    p = MagicMock()
    p.id = player_id or PlayerId(uuid4())
    p.username = username
    p.elo_rating = 1200
    p.player_type = "human"
    return p


def make_board(width: int = 8, height: int = 8) -> BoardState:
    """Create a simple BoardState with standard gems (no matches)."""
    rng = np.random.default_rng(42)
    grid = rng.integers(1, 7, size=(height, width), dtype=np.int8)
    return BoardState(grid=grid)


def make_board_list(width: int = 8, height: int = 8) -> list[list[int]]:
    """Create a JSON-serializable board list."""
    return make_board(width, height).to_list()


def make_match_record(
    match_id: UUID | None = None,
    player1_id: UUID | None = None,
    player2_id: UUID | None = None,
    status: str = "pending",
    match_type: str = "standard",
    board_seed: int = 42,
    player1_score: int = 0,
    player2_score: int = 0,
    player1_moves_made: int = 0,
    player2_moves_made: int = 0,
    player1_moves_remaining: int = 20,
    player2_moves_remaining: int = 20,
    player1_longest_chain: int = 0,
    player2_longest_chain: int = 0,
    player1_finished_at: datetime | None = None,
    player2_finished_at: datetime | None = None,
    winner_id: UUID | None = None,
    forfeit_by: UUID | None = None,
) -> MagicMock:
    """Create a mock match record (mimics MatchModel ORM object)."""
    board_list = make_board_list()
    record = MagicMock()
    record.id = match_id or uuid4()
    record.player1_id = player1_id or uuid4()
    record.player2_id = player2_id or uuid4()
    record.status = status
    record.match_type = match_type
    record.board_seed = board_seed
    record.initial_board_state = board_list
    record.player1_board_state = board_list
    record.player2_board_state = board_list
    record.player1_score = player1_score
    record.player2_score = player2_score
    record.player1_moves_made = player1_moves_made
    record.player2_moves_made = player2_moves_made
    record.player1_moves_remaining = player1_moves_remaining
    record.player2_moves_remaining = player2_moves_remaining
    record.player1_longest_chain = player1_longest_chain
    record.player2_longest_chain = player2_longest_chain
    record.player1_finished_at = player1_finished_at
    record.player2_finished_at = player2_finished_at
    record.winner_id = winner_id
    record.forfeit_by = forfeit_by
    record.timeout_at = datetime.now(timezone.utc)
    record.created_at = datetime.now(timezone.utc)
    record.started_at = None
    record.completed_at = None
    return record


def make_move_result(
    valid: bool = True,
    chain_count: int = 1,
    total_gems_cleared: int = 3,
    special_gems_created: list | None = None,
) -> MoveProcessingResult:
    """Create a MoveProcessingResult with configurable validity."""
    board = make_board()
    move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)
    return MoveProcessingResult(
        initial_board=board,
        final_board=board,
        move=move,
        was_valid_match=valid,
        cascades=[],
        total_matches=1 if valid else 0,
        total_gems_cleared=total_gems_cleared if valid else 0,
        chain_count=chain_count if valid else 0,
        special_gems_created=special_gems_created or [],
    )


def make_score_result(points: int = 100) -> MoveScore:
    """Create a MoveScore with a given total_points."""
    return MoveScore(
        total_points=points,
        cascade_scores=(),
        chain_count=1,
        total_gems_cleared=3,
        highest_chain_multiplier=1.0,
        special_gems_created=0,
        special_gems_activated=0,
    )


def make_generated_board(seed: int = 42) -> GeneratedBoard:
    """Create a GeneratedBoard for board_gen_service mock returns."""
    board = make_board()
    meta = GenerationMetadata(
        width=8,
        height=8,
        cascade_potential_target=0.5,
        cascade_potential_actual=0.45,
        near_miss_factor=0.3,
        near_miss_count=2,
        starting_specials_placed=[],
        valid_moves_count=15,
        generation_attempts=1,
        generation_time_ms=5.0,
    )
    return GeneratedBoard(board_state=board, seed=seed, generation_metadata=meta)


def make_move_record_orm(
    match_id: UUID | None = None,
    player_id: UUID | None = None,
    move_number: int = 1,
) -> MagicMock:
    """Create a mock MatchMoveModel record."""
    record = MagicMock()
    record.match_id = match_id or uuid4()
    record.player_id = player_id or uuid4()
    record.move_number = move_number
    record.from_row = 0
    record.from_col = 0
    record.to_row = 0
    record.to_col = 1
    record.client_timestamp_ms = 1000
    record.board_before = make_board_list()
    record.board_after = make_board_list()
    record.score_earned = 100
    record.chain_count = 1
    record.gems_cleared = 3
    record.special_gems_created = []
    record.special_gems_activated = []
    record.created_at = datetime.now(timezone.utc)
    return record


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def mock_config() -> MockConfigService:
    return MockConfigService(
        {
            "match.moves_per_player": 20,
            "match.timeout_hours": 72,
            "match.energy_cost": 1,
            "match.allow_concurrent": False,
            "match.max_concurrent": 1,
            "match.deadlock_reshuffle": True,
        }
    )


@pytest.fixture()
def mock_logger() -> MockLogService:
    return MockLogService()


@pytest.fixture()
def mock_errors(mock_logger: MockLogService) -> MockErrorService:
    return MockErrorService(mock_logger)


@pytest.fixture()
def mock_data_ctx() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_board_gen_service() -> MagicMock:
    svc = MagicMock()
    generated = make_generated_board()
    svc.generate_board_for_match.return_value = generated
    svc.regenerate_from_deadlock.return_value = generated
    return svc


@pytest.fixture()
def mock_board_service() -> MagicMock:
    svc = MagicMock()
    svc.process_move.return_value = make_move_result(valid=True)
    svc.has_valid_moves.return_value = True
    return svc


@pytest.fixture()
def mock_scoring_service() -> MagicMock:
    svc = MagicMock()
    svc.calculate_move_score.return_value = make_score_result(100)
    return svc


@pytest.fixture()
def mock_special_gems_service() -> MagicMock:
    svc = MagicMock()
    svc.is_special_gem.return_value = False
    svc.calculate_effect.return_value = MagicMock()
    svc.apply_effect.return_value = (make_board(), [])
    return svc


@pytest.fixture()
def mock_player_service() -> AsyncMock:
    svc = AsyncMock()
    # Default: return generic player objects.
    svc.get_player.side_effect = lambda pid: make_player(pid, f"user_{str(pid)[:8]}")
    svc.get_player_by_username.return_value = None
    svc.record_match_result.return_value = MagicMock()
    svc.calculate_elo_change.return_value = (10, -10)
    svc.get_elo.return_value = 1200
    svc.update_elo.return_value = MagicMock()
    return svc


@pytest.fixture()
def mock_auth_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_energy_service() -> AsyncMock:
    svc = AsyncMock()
    svc.can_play.return_value = True
    svc.consume_heart.return_value = MagicMock()
    return svc


@pytest.fixture()
def mock_match_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.create.return_value = make_match_record()
    repo.find_by_id.return_value = None
    repo.update.return_value = make_match_record()
    repo.find_active_by_player.return_value = []
    repo.find_by_player.return_value = ([], 0)
    repo.find_stale_matches.return_value = []
    repo.bulk_abandon.return_value = 0
    repo.cleanup_match_data.return_value = None
    return repo


@pytest.fixture()
def mock_move_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.create.return_value = MagicMock()
    repo.find_by_match.return_value = []
    repo.count_by_player.return_value = 0
    repo.delete_by_match_id.return_value = 0
    return repo


@pytest.fixture()
def match_service(
    mock_config: MockConfigService,
    mock_logger: MockLogService,
    mock_errors: MockErrorService,
    mock_data_ctx: MagicMock,
    mock_board_gen_service: MagicMock,
    mock_board_service: MagicMock,
    mock_scoring_service: MagicMock,
    mock_special_gems_service: MagicMock,
    mock_player_service: AsyncMock,
    mock_auth_service: AsyncMock,
    mock_energy_service: AsyncMock,
    mock_match_repo: AsyncMock,
    mock_move_repo: AsyncMock,
) -> MatchService:
    return MatchService(
        config=mock_config,
        logger=mock_logger,
        errors=mock_errors,
        data_ctx=mock_data_ctx,
        board_gen_service=mock_board_gen_service,
        board_service=mock_board_service,
        scoring_service=mock_scoring_service,
        special_gems_service=mock_special_gems_service,
        player_service=mock_player_service,
        auth_service=mock_auth_service,
        energy_service=mock_energy_service,
        repos=MatchRepositoryBundle(mock_match_repo, mock_move_repo),
    )


# ============================================================================
# create_match tests
# ============================================================================


class TestCreateMatch:
    """Tests for MatchService.create_match."""

    @pytest.mark.asyncio
    async def test_create_match_success(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Happy path: two distinct players with energy create a match."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())

        # Set up the repo to return a record with matching player IDs.
        record = make_match_record(
            player1_id=UUID(str(p1_id)), player2_id=UUID(str(p2_id))
        )
        mock_match_repo.create.return_value = record

        result = await match_service.create_match(p1_id, p2_id)

        assert isinstance(result, MatchState)
        assert result.status == MatchStatus.PENDING
        mock_match_repo.create.assert_awaited_once()
        mock_energy_service.consume_heart.assert_any_await(p1_id, amount=1)
        mock_energy_service.consume_heart.assert_any_await(p2_id, amount=1)

    @pytest.mark.asyncio
    async def test_create_match_same_player_raises(
        self,
        match_service: MatchService,
    ) -> None:
        """Creating a match against yourself raises VALIDATION_INVALID_INPUT."""
        pid = PlayerId(uuid4())
        with pytest.raises(AppError) as exc_info:
            await match_service.create_match(pid, pid)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_create_match_player1_not_found(
        self,
        match_service: MatchService,
        mock_player_service: AsyncMock,
        mock_errors: MockErrorService,
    ) -> None:
        """If player1 doesn't exist, get_player raises NOT_FOUND_PLAYER."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())

        err = AppError(
            code="NOT_FOUND_PLAYER", message="Player not found", http_status=404
        )
        mock_player_service.get_player.side_effect = [err, make_player(p2_id, "p2")]

        with pytest.raises(AppError) as exc_info:
            await match_service.create_match(p1_id, p2_id)
        assert exc_info.value.code == "NOT_FOUND_PLAYER"

    @pytest.mark.asyncio
    async def test_create_match_player2_not_found(
        self,
        match_service: MatchService,
        mock_player_service: AsyncMock,
    ) -> None:
        """If player2 doesn't exist, get_player raises NOT_FOUND_PLAYER."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())

        err = AppError(
            code="NOT_FOUND_PLAYER", message="Player not found", http_status=404
        )
        mock_player_service.get_player.side_effect = [
            make_player(p1_id, "p1"),
            err,
        ]

        with pytest.raises(AppError) as exc_info:
            await match_service.create_match(p1_id, p2_id)
        assert exc_info.value.code == "NOT_FOUND_PLAYER"

    @pytest.mark.asyncio
    async def test_create_match_concurrent_limit_player1(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Player1 already has an active match when concurrent is not allowed."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())

        # p1 has 1 active match, which >= max_concurrent (1).
        # Both calls happen before the check, so provide return values for both.
        mock_match_repo.find_active_by_player.side_effect = [
            [MagicMock()],  # p1 active matches
            [],  # p2 active matches (fetched but check for p1 triggers first)
        ]

        with pytest.raises(AppError) as exc_info:
            await match_service.create_match(p1_id, p2_id)
        assert exc_info.value.code == "CONFLICT_CONCURRENT_MATCH"

    @pytest.mark.asyncio
    async def test_create_match_concurrent_limit_player2(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Player2 already has an active match when concurrent is not allowed."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())

        # p1 has 0, p2 has 1 active match.
        mock_match_repo.find_active_by_player.side_effect = [
            [],  # p1 active matches: none
            [MagicMock()],  # p2 active matches: 1
        ]

        with pytest.raises(AppError) as exc_info:
            await match_service.create_match(p1_id, p2_id)
        assert exc_info.value.code == "CONFLICT_CONCURRENT_MATCH"

    @pytest.mark.asyncio
    async def test_create_match_insufficient_energy_player1(
        self,
        match_service: MatchService,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Player1 does not have enough energy to play."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())

        mock_energy_service.can_play.side_effect = [False, True]

        with pytest.raises(AppError) as exc_info:
            await match_service.create_match(p1_id, p2_id)
        assert exc_info.value.code == "FORBIDDEN_INSUFFICIENT_ENERGY"

    @pytest.mark.asyncio
    async def test_create_match_insufficient_energy_player2(
        self,
        match_service: MatchService,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Player2 does not have enough energy to play."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())

        mock_energy_service.can_play.side_effect = [True, False]

        with pytest.raises(AppError) as exc_info:
            await match_service.create_match(p1_id, p2_id)
        assert exc_info.value.code == "FORBIDDEN_INSUFFICIENT_ENERGY"

    @pytest.mark.asyncio
    async def test_create_match_custom_seed(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_board_gen_service: MagicMock,
    ) -> None:
        """A custom seed should be passed to board generation."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())

        record = make_match_record(
            player1_id=UUID(str(p1_id)), player2_id=UUID(str(p2_id))
        )
        mock_match_repo.create.return_value = record

        await match_service.create_match(p1_id, p2_id, board_seed=99999)

        call_args = mock_board_gen_service.generate_board_for_match.call_args
        assert call_args[0][0] == 99999

    @pytest.mark.asyncio
    async def test_create_match_custom_match_type(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_board_gen_service: MagicMock,
    ) -> None:
        """Match type should be mapped to board_gen MatchType correctly."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())

        record = make_match_record(
            player1_id=UUID(str(p1_id)),
            player2_id=UUID(str(p2_id)),
            match_type="competitive",
        )
        mock_match_repo.create.return_value = record

        await match_service.create_match(p1_id, p2_id, match_type=MatchType.COMPETITIVE)

        call_args = mock_board_gen_service.generate_board_for_match.call_args
        assert call_args[1]["match_type"] == BoardGenMatchType.COMPETITIVE

    @pytest.mark.asyncio
    async def test_create_match_energy_consumed(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Energy should be consumed for both players after validation passes."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())

        record = make_match_record(
            player1_id=UUID(str(p1_id)), player2_id=UUID(str(p2_id))
        )
        mock_match_repo.create.return_value = record

        await match_service.create_match(p1_id, p2_id)

        assert mock_energy_service.consume_heart.await_count == 2

    @pytest.mark.asyncio
    async def test_create_match_concurrent_allowed(
        self,
        mock_logger: MockLogService,
        mock_errors: MockErrorService,
        mock_data_ctx: MagicMock,
        mock_board_gen_service: MagicMock,
        mock_board_service: MagicMock,
        mock_scoring_service: MagicMock,
        mock_special_gems_service: MagicMock,
        mock_player_service: AsyncMock,
        mock_auth_service: AsyncMock,
        mock_energy_service: AsyncMock,
        mock_match_repo: AsyncMock,
        mock_move_repo: AsyncMock,
    ) -> None:
        """When allow_concurrent=True, concurrent check is skipped entirely."""
        config = MockConfigService(
            {
                "match.moves_per_player": 20,
                "match.timeout_hours": 72,
                "match.energy_cost": 1,
                "match.allow_concurrent": True,
                "match.max_concurrent": 1,
                "match.deadlock_reshuffle": True,
            }
        )
        svc = MatchService(
            config=config,
            logger=mock_logger,
            errors=mock_errors,
            data_ctx=mock_data_ctx,
            board_gen_service=mock_board_gen_service,
            board_service=mock_board_service,
            scoring_service=mock_scoring_service,
            special_gems_service=mock_special_gems_service,
            player_service=mock_player_service,
            auth_service=mock_auth_service,
            energy_service=mock_energy_service,
            repos=MatchRepositoryBundle(mock_match_repo, mock_move_repo),
        )

        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())
        record = make_match_record(
            player1_id=UUID(str(p1_id)), player2_id=UUID(str(p2_id))
        )
        mock_match_repo.create.return_value = record

        result = await svc.create_match(p1_id, p2_id)

        assert isinstance(result, MatchState)
        # find_active_by_player should NOT have been called.
        mock_match_repo.find_active_by_player.assert_not_awaited()


# ============================================================================
# submit_move tests
# ============================================================================


class TestSubmitMove:
    """Tests for MatchService.submit_move."""

    def _setup_submit_move(
        self,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        player1_id: UUID | None = None,
        player2_id: UUID | None = None,
        status: str = "in_progress",
        player1_moves_remaining: int = 20,
        player2_moves_remaining: int = 20,
        player1_score: int = 0,
        player2_score: int = 0,
        player1_moves_made: int = 0,
        player2_moves_made: int = 0,
        player1_longest_chain: int = 0,
        player2_longest_chain: int = 0,
        player1_finished_at: datetime | None = None,
        player2_finished_at: datetime | None = None,
    ) -> tuple[UUID, UUID, UUID]:
        """Configure mocks for a standard submit_move test, returning (match_uuid, p1_uuid, p2_uuid)."""
        match_uuid = uuid4()
        p1_uuid = player1_id or uuid4()
        p2_uuid = player2_id or uuid4()

        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status=status,
            player1_moves_remaining=player1_moves_remaining,
            player2_moves_remaining=player2_moves_remaining,
            player1_score=player1_score,
            player2_score=player2_score,
            player1_moves_made=player1_moves_made,
            player2_moves_made=player2_moves_made,
            player1_longest_chain=player1_longest_chain,
            player2_longest_chain=player2_longest_chain,
            player1_finished_at=player1_finished_at,
            player2_finished_at=player2_finished_at,
        )
        # find_by_id returns the record, update returns a slightly modified copy.
        mock_match_repo.find_by_id.return_value = record
        mock_match_repo.update.return_value = record

        return match_uuid, p1_uuid, p2_uuid

    @pytest.mark.asyncio
    async def test_submit_move_success(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_move_repo: AsyncMock,
    ) -> None:
        """Happy path: valid move submission returns MoveSubmissionResult."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
        )
        match_id = MatchId(match_uuid)
        player_id = PlayerId(p1_uuid)
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        result = await match_service.submit_move(match_id, player_id, move)

        assert isinstance(result, MoveSubmissionResult)
        assert result.points_earned >= 0
        mock_move_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_move_match_not_found(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Non-existent match raises NOT_FOUND_MATCH."""
        mock_match_repo.find_by_id.return_value = None
        match_id = MatchId(uuid4())
        player_id = PlayerId(uuid4())
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        with pytest.raises(AppError) as exc_info:
            await match_service.submit_move(match_id, player_id, move)
        assert exc_info.value.code == "NOT_FOUND_MATCH"

    @pytest.mark.asyncio
    async def test_submit_move_not_participant(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """A player not in the match raises FORBIDDEN_NOT_MATCH_PARTICIPANT."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
        )
        stranger_id = PlayerId(uuid4())
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        with pytest.raises(AppError) as exc_info:
            await match_service.submit_move(MatchId(match_uuid), stranger_id, move)
        assert exc_info.value.code == "FORBIDDEN_NOT_MATCH_PARTICIPANT"

    @pytest.mark.asyncio
    async def test_submit_move_match_completed(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Submitting a move to a completed match raises CONFLICT_MATCH_ALREADY_COMPLETED."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            status="completed",
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        with pytest.raises(AppError) as exc_info:
            await match_service.submit_move(
                MatchId(match_uuid), PlayerId(p1_uuid), move
            )
        assert exc_info.value.code == "CONFLICT_MATCH_ALREADY_COMPLETED"

    @pytest.mark.asyncio
    async def test_submit_move_match_abandoned(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Submitting a move to an abandoned match raises CONFLICT_MATCH_ALREADY_COMPLETED."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            status="abandoned",
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        with pytest.raises(AppError) as exc_info:
            await match_service.submit_move(
                MatchId(match_uuid), PlayerId(p1_uuid), move
            )
        assert exc_info.value.code == "CONFLICT_MATCH_ALREADY_COMPLETED"

    @pytest.mark.asyncio
    async def test_submit_move_no_moves_remaining(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Player with 0 moves remaining raises VALIDATION_NO_MOVES_REMAINING."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            player1_moves_remaining=0,
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        with pytest.raises(AppError) as exc_info:
            await match_service.submit_move(
                MatchId(match_uuid), PlayerId(p1_uuid), move
            )
        assert exc_info.value.code == "VALIDATION_NO_MOVES_REMAINING"

    @pytest.mark.asyncio
    async def test_submit_move_invalid_swap(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_board_service: MagicMock,
    ) -> None:
        """An invalid gem swap (no matches) raises VALIDATION_INVALID_GEM_SWAP."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
        )
        mock_board_service.process_move.return_value = make_move_result(valid=False)
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        with pytest.raises(AppError) as exc_info:
            await match_service.submit_move(
                MatchId(match_uuid), PlayerId(p1_uuid), move
            )
        assert exc_info.value.code == "VALIDATION_INVALID_GEM_SWAP"

    @pytest.mark.asyncio
    async def test_submit_move_updates_score(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_scoring_service: MagicMock,
    ) -> None:
        """Score from scoring_service is added to points_earned."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            player1_score=50,
        )
        mock_scoring_service.calculate_move_score.return_value = make_score_result(200)
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        result = await match_service.submit_move(
            MatchId(match_uuid), PlayerId(p1_uuid), move
        )

        assert result.points_earned == 200

    @pytest.mark.asyncio
    async def test_submit_move_decrements_moves(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """moves_remaining should be decremented by 1 after a valid move."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            player1_moves_remaining=15,
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        result = await match_service.submit_move(
            MatchId(match_uuid), PlayerId(p1_uuid), move
        )

        assert result.moves_remaining == 14

    @pytest.mark.asyncio
    async def test_submit_move_transitions_pending_to_in_progress(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """First move on a PENDING match transitions status to IN_PROGRESS."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            status="pending",
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        await match_service.submit_move(MatchId(match_uuid), PlayerId(p1_uuid), move)

        # Check the MatchUpdate passed to repo.update has status=in_progress.
        update_call = mock_match_repo.update.call_args
        match_update = update_call[0][1]
        assert match_update.status == MatchStatus.IN_PROGRESS.value
        assert match_update.started_at is not None

    @pytest.mark.asyncio
    async def test_submit_move_player1_finishes(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """When player1 uses their last move, player_finished=True and finished_at set."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            player1_moves_remaining=1,
            player2_moves_remaining=5,  # opponent not done yet
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        result = await match_service.submit_move(
            MatchId(match_uuid), PlayerId(p1_uuid), move
        )

        assert result.player_finished is True
        assert result.moves_remaining == 0
        assert result.match_completed is False  # opponent still has moves

    @pytest.mark.asyncio
    async def test_submit_move_player2_finishes(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """When player2 uses their last move, player_finished=True."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            player2_moves_remaining=1,
            player1_moves_remaining=5,  # opponent not done yet
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        result = await match_service.submit_move(
            MatchId(match_uuid), PlayerId(p2_uuid), move
        )

        assert result.player_finished is True
        assert result.moves_remaining == 0
        assert result.match_completed is False

    @pytest.mark.asyncio
    async def test_submit_move_both_finish_determines_winner(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_scoring_service: MagicMock,
    ) -> None:
        """When both players finish, the one with the higher score wins."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            player1_moves_remaining=1,
            player2_moves_remaining=0,  # p2 already done
            player1_score=500,
            player2_score=300,
            player2_finished_at=datetime.now(timezone.utc),
        )
        mock_scoring_service.calculate_move_score.return_value = make_score_result(100)
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        result = await match_service.submit_move(
            MatchId(match_uuid), PlayerId(p1_uuid), move
        )

        assert result.match_completed is True
        # p1 score is 500 + 100 = 600 > p2 score 300, so p1 wins.
        assert result.winner_id == PlayerId(p1_uuid)

    @pytest.mark.asyncio
    async def test_submit_move_both_finish_draw(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_scoring_service: MagicMock,
    ) -> None:
        """When both players finish with equal scores, winner_id is None (draw)."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            player1_moves_remaining=1,
            player2_moves_remaining=0,
            player1_score=200,  # after adding 100 points, p1 = 300
            player2_score=300,
            player2_finished_at=datetime.now(timezone.utc),
        )
        mock_scoring_service.calculate_move_score.return_value = make_score_result(100)
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        result = await match_service.submit_move(
            MatchId(match_uuid), PlayerId(p1_uuid), move
        )

        assert result.match_completed is True
        assert result.winner_id is None  # Draw

    @pytest.mark.asyncio
    async def test_submit_move_updates_longest_chain(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_board_service: MagicMock,
    ) -> None:
        """If chain_count > current longest_chain, longest_chain is updated."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            player1_longest_chain=2,
        )
        mock_board_service.process_move.return_value = make_move_result(
            valid=True, chain_count=5
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        await match_service.submit_move(MatchId(match_uuid), PlayerId(p1_uuid), move)

        # Check the MatchUpdate has new longest chain = max(2, 5) = 5.
        update_call = mock_match_repo.update.call_args
        match_update = update_call[0][1]
        assert match_update.player1_longest_chain == 5

    @pytest.mark.asyncio
    async def test_submit_move_persists_move_record(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_move_repo: AsyncMock,
    ) -> None:
        """A move record should be persisted via move_repo.create."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        await match_service.submit_move(MatchId(match_uuid), PlayerId(p1_uuid), move)

        mock_move_repo.create.assert_awaited_once()
        create_arg = mock_move_repo.create.call_args[0][0]
        assert create_arg.match_id == match_uuid
        assert create_arg.player_id == p1_uuid

    @pytest.mark.asyncio
    async def test_submit_move_special_gem_processing(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_board_service: MagicMock,
        mock_special_gems_service: MagicMock,
        mock_scoring_service: MagicMock,
    ) -> None:
        """Special gems created by a move persist on the board (no auto-activation)."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
        )

        # Move produces a special gem.
        move_result = make_move_result(valid=True)
        move_result.special_gems_created = [(Position(2, 3), GemType.RADIAL_BOMB)]
        mock_board_service.process_move.return_value = move_result

        mock_scoring_service.calculate_move_score.return_value = make_score_result(100)

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)
        result = await match_service.submit_move(
            MatchId(match_uuid), PlayerId(p1_uuid), move
        )

        # Special gems persist — no activation calls.
        mock_special_gems_service.calculate_effect.assert_not_called()
        mock_special_gems_service.apply_effect.assert_not_called()
        # Points = 100 (base only, no activation bonus).
        assert result.points_earned == 100
        assert len(result.special_effects) == 0

    @pytest.mark.asyncio
    async def test_submit_move_deadlock_reshuffle(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_board_service: MagicMock,
        mock_board_gen_service: MagicMock,
    ) -> None:
        """When has_valid_moves=False and moves remain, board should be reshuffled."""
        match_uuid, p1_uuid, p2_uuid = self._setup_submit_move(
            mock_match_repo,
            mock_player_service,
            player1_moves_remaining=5,
        )
        # First call to has_valid_moves returns False (deadlock), second returns True (after reshuffle).
        mock_board_service.has_valid_moves.side_effect = [False, True]
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)

        await match_service.submit_move(MatchId(match_uuid), PlayerId(p1_uuid), move)

        mock_board_gen_service.regenerate_from_deadlock.assert_called_once()


# ============================================================================
# get_match tests
# ============================================================================


class TestGetMatch:
    """Tests for MatchService.get_match."""

    @pytest.mark.asyncio
    async def test_get_match_success(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Happy path: returns a MatchState for an existing match."""
        match_uuid = uuid4()
        record = make_match_record(match_id=match_uuid)
        mock_match_repo.find_by_id.return_value = record

        result = await match_service.get_match(MatchId(match_uuid))

        assert isinstance(result, MatchState)
        assert result.match_id == MatchId(match_uuid)

    @pytest.mark.asyncio
    async def test_get_match_not_found(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Non-existent match raises NOT_FOUND_MATCH."""
        mock_match_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await match_service.get_match(MatchId(uuid4()))
        assert exc_info.value.code == "NOT_FOUND_MATCH"


# ============================================================================
# get_match_state tests
# ============================================================================


class TestGetMatchState:
    """Tests for MatchService.get_match_state."""

    @pytest.mark.asyncio
    async def test_get_match_state_success(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Returns MatchState when player is a participant."""
        p1_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(match_id=match_uuid, player1_id=p1_uuid)
        mock_match_repo.find_by_id.return_value = record

        result = await match_service.get_match_state(
            MatchId(match_uuid),
            for_player_id=PlayerId(p1_uuid),
        )

        assert isinstance(result, MatchState)

    @pytest.mark.asyncio
    async def test_get_match_state_not_participant(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Non-participant raises FORBIDDEN_NOT_MATCH_PARTICIPANT."""
        match_uuid = uuid4()
        record = make_match_record(match_id=match_uuid)
        mock_match_repo.find_by_id.return_value = record
        stranger_id = PlayerId(uuid4())

        with pytest.raises(AppError) as exc_info:
            await match_service.get_match_state(
                MatchId(match_uuid),
                for_player_id=stranger_id,
            )
        assert exc_info.value.code == "FORBIDDEN_NOT_MATCH_PARTICIPANT"


# ============================================================================
# get_player_board tests
# ============================================================================


class TestGetPlayerBoard:
    """Tests for MatchService.get_player_board."""

    @pytest.mark.asyncio
    async def test_get_player_board_player1(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_board_service: MagicMock,
    ) -> None:
        """Returns PlayerBoardState for player1."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            player1_score=150,
            player1_moves_made=5,
            player1_moves_remaining=15,
        )
        mock_match_repo.find_by_id.return_value = record

        result = await match_service.get_player_board(
            MatchId(match_uuid),
            PlayerId(p1_uuid),
        )

        assert isinstance(result, PlayerBoardState)
        assert result.player_id == PlayerId(p1_uuid)
        assert result.score == 150
        assert result.moves_made == 5
        assert result.moves_remaining == 15
        assert result.has_valid_moves is True

    @pytest.mark.asyncio
    async def test_get_player_board_player2(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_board_service: MagicMock,
    ) -> None:
        """Returns PlayerBoardState for player2."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            player2_score=300,
            player2_moves_made=10,
            player2_moves_remaining=10,
        )
        mock_match_repo.find_by_id.return_value = record

        result = await match_service.get_player_board(
            MatchId(match_uuid),
            PlayerId(p2_uuid),
        )

        assert isinstance(result, PlayerBoardState)
        assert result.player_id == PlayerId(p2_uuid)
        assert result.score == 300

    @pytest.mark.asyncio
    async def test_get_player_board_not_found(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Non-existent match raises NOT_FOUND_MATCH."""
        mock_match_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await match_service.get_player_board(MatchId(uuid4()), PlayerId(uuid4()))
        assert exc_info.value.code == "NOT_FOUND_MATCH"

    @pytest.mark.asyncio
    async def test_get_player_board_not_participant(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Non-participant raises FORBIDDEN_NOT_MATCH_PARTICIPANT."""
        match_uuid = uuid4()
        record = make_match_record(match_id=match_uuid)
        mock_match_repo.find_by_id.return_value = record

        stranger_id = PlayerId(uuid4())
        with pytest.raises(AppError) as exc_info:
            await match_service.get_player_board(MatchId(match_uuid), stranger_id)
        assert exc_info.value.code == "FORBIDDEN_NOT_MATCH_PARTICIPANT"


# ============================================================================
# get_active_matches tests
# ============================================================================


class TestGetActiveMatches:
    """Tests for MatchService.get_active_matches."""

    @pytest.mark.asyncio
    async def test_get_active_matches_success(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Returns a list of MatchState for active matches."""
        p1_uuid = uuid4()
        record1 = make_match_record(player1_id=p1_uuid)
        record2 = make_match_record(player1_id=p1_uuid)
        mock_match_repo.find_active_by_player.return_value = [record1, record2]

        result = await match_service.get_active_matches(PlayerId(p1_uuid))

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(m, MatchState) for m in result)

    @pytest.mark.asyncio
    async def test_get_active_matches_empty(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """No active matches returns empty list."""
        mock_match_repo.find_active_by_player.return_value = []

        result = await match_service.get_active_matches(PlayerId(uuid4()))

        assert result == []


# ============================================================================
# forfeit_match tests
# ============================================================================


class TestForfeitMatch:
    """Tests for MatchService.forfeit_match."""

    @pytest.mark.asyncio
    async def test_forfeit_match_player1_forfeits(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """When player1 forfeits, player2 wins."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="in_progress",
        )
        mock_match_repo.find_by_id.return_value = record
        # update returns a record reflecting the forfeit.
        updated = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="completed",
            winner_id=p2_uuid,
            forfeit_by=p1_uuid,
        )
        mock_match_repo.update.return_value = updated

        result = await match_service.forfeit_match(
            MatchId(match_uuid), PlayerId(p1_uuid)
        )

        assert isinstance(result, MatchState)
        # Check that update was called with p2 as winner.
        update_call = mock_match_repo.update.call_args
        match_update = update_call[0][1]
        assert match_update.winner_id == p2_uuid
        assert match_update.forfeit_by == p1_uuid

    @pytest.mark.asyncio
    async def test_forfeit_match_player2_forfeits(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """When player2 forfeits, player1 wins."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="in_progress",
        )
        mock_match_repo.find_by_id.return_value = record
        updated = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="completed",
            winner_id=p1_uuid,
            forfeit_by=p2_uuid,
        )
        mock_match_repo.update.return_value = updated

        result = await match_service.forfeit_match(
            MatchId(match_uuid), PlayerId(p2_uuid)
        )

        assert isinstance(result, MatchState)
        update_call = mock_match_repo.update.call_args
        match_update = update_call[0][1]
        assert match_update.winner_id == p1_uuid
        assert match_update.forfeit_by == p2_uuid

    @pytest.mark.asyncio
    async def test_forfeit_match_not_found(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Non-existent match raises NOT_FOUND_MATCH."""
        mock_match_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await match_service.forfeit_match(MatchId(uuid4()), PlayerId(uuid4()))
        assert exc_info.value.code == "NOT_FOUND_MATCH"

    @pytest.mark.asyncio
    async def test_forfeit_match_not_participant(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Non-participant raises FORBIDDEN_NOT_MATCH_PARTICIPANT."""
        match_uuid = uuid4()
        record = make_match_record(match_id=match_uuid, status="in_progress")
        mock_match_repo.find_by_id.return_value = record

        stranger_id = PlayerId(uuid4())
        with pytest.raises(AppError) as exc_info:
            await match_service.forfeit_match(MatchId(match_uuid), stranger_id)
        assert exc_info.value.code == "FORBIDDEN_NOT_MATCH_PARTICIPANT"

    @pytest.mark.asyncio
    async def test_forfeit_match_already_completed(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Already-completed match raises CONFLICT_MATCH_ALREADY_COMPLETED."""
        p1_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            status="completed",
        )
        mock_match_repo.find_by_id.return_value = record

        with pytest.raises(AppError) as exc_info:
            await match_service.forfeit_match(MatchId(match_uuid), PlayerId(p1_uuid))
        assert exc_info.value.code == "CONFLICT_MATCH_ALREADY_COMPLETED"


# ============================================================================
# get_match_history tests
# ============================================================================


class TestGetMatchHistory:
    """Tests for MatchService.get_match_history."""

    @pytest.mark.asyncio
    async def test_get_match_history_success(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Returns PaginatedResult with MatchSummary items."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()
        record = make_match_record(
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="completed",
            player1_score=500,
            player2_score=300,
            winner_id=p1_uuid,
            match_type="standard",
        )
        record.completed_at = datetime.now(timezone.utc)
        mock_match_repo.find_by_player.return_value = ([record], 1)

        result = await match_service.get_match_history(PlayerId(p1_uuid))

        assert isinstance(result, PaginatedResult)
        assert len(result.items) == 1
        assert isinstance(result.items[0], MatchSummary)
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_get_match_history_invalid_limit_too_low(
        self,
        match_service: MatchService,
    ) -> None:
        """limit < 1 raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            await match_service.get_match_history(PlayerId(uuid4()), limit=0)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_get_match_history_invalid_limit_too_high(
        self,
        match_service: MatchService,
    ) -> None:
        """limit > 100 raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            await match_service.get_match_history(PlayerId(uuid4()), limit=101)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_get_match_history_empty(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """No matches returns empty PaginatedResult."""
        mock_match_repo.find_by_player.return_value = ([], 0)

        result = await match_service.get_match_history(PlayerId(uuid4()))

        assert result.items == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_get_match_history_win_loss_draw(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Verify won field: True for win, False for loss, None for draw."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()

        # Win: p1 is winner.
        win_record = make_match_record(
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="completed",
            winner_id=p1_uuid,
            player1_score=500,
            player2_score=300,
            match_type="standard",
        )
        win_record.completed_at = datetime.now(timezone.utc)

        # Loss: p2 is winner.
        loss_record = make_match_record(
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="completed",
            winner_id=p2_uuid,
            player1_score=200,
            player2_score=400,
            match_type="standard",
        )
        loss_record.completed_at = datetime.now(timezone.utc)

        # Draw: no winner.
        draw_record = make_match_record(
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="completed",
            winner_id=None,
            player1_score=300,
            player2_score=300,
            match_type="standard",
        )
        draw_record.completed_at = datetime.now(timezone.utc)

        mock_match_repo.find_by_player.return_value = (
            [win_record, loss_record, draw_record],
            3,
        )

        result = await match_service.get_match_history(PlayerId(p1_uuid))

        assert result.items[0].won is True
        assert result.items[1].won is False
        assert result.items[2].won is None  # Draw


# ============================================================================
# get_move_history tests
# ============================================================================


class TestGetMoveHistory:
    """Tests for MatchService.get_move_history."""

    @pytest.mark.asyncio
    async def test_get_move_history_success(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_move_repo: AsyncMock,
    ) -> None:
        """Returns list of MoveRecord for an existing match."""
        match_uuid = uuid4()
        p1_uuid = uuid4()
        record = make_match_record(match_id=match_uuid)
        mock_match_repo.find_by_id.return_value = record

        move_orm = make_move_record_orm(match_id=match_uuid, player_id=p1_uuid)
        mock_move_repo.find_by_match.return_value = [move_orm]

        result = await match_service.get_move_history(MatchId(match_uuid))

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], MoveRecord)
        assert result[0].move_number == 1
        assert result[0].score_earned == 100

    @pytest.mark.asyncio
    async def test_get_move_history_not_found(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Non-existent match raises NOT_FOUND_MATCH."""
        mock_match_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await match_service.get_move_history(MatchId(uuid4()))
        assert exc_info.value.code == "NOT_FOUND_MATCH"

    @pytest.mark.asyncio
    async def test_get_move_history_filtered_by_player(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_move_repo: AsyncMock,
    ) -> None:
        """When player_id is given, it is passed through to the repository."""
        match_uuid = uuid4()
        p1_uuid = uuid4()
        record = make_match_record(match_id=match_uuid)
        mock_match_repo.find_by_id.return_value = record
        mock_move_repo.find_by_match.return_value = []

        await match_service.get_move_history(
            MatchId(match_uuid),
            player_id=PlayerId(p1_uuid),
        )

        call_kwargs = mock_move_repo.find_by_match.call_args
        assert call_kwargs[1]["player_id"] == p1_uuid


# ============================================================================
# abandon_stale_matches tests
# ============================================================================


class TestAbandonStaleMatches:
    """Tests for MatchService.abandon_stale_matches."""

    @pytest.mark.asyncio
    async def test_abandon_stale_matches_success(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Returns count of abandoned stale matches."""
        stale1 = MagicMock()
        stale1.id = uuid4()
        stale2 = MagicMock()
        stale2.id = uuid4()
        mock_match_repo.find_stale_matches.return_value = [stale1, stale2]
        mock_match_repo.bulk_abandon.return_value = 2

        result = await match_service.abandon_stale_matches()

        assert result == 2
        mock_match_repo.bulk_abandon.assert_awaited_once_with([stale1.id, stale2.id])

    @pytest.mark.asyncio
    async def test_abandon_stale_matches_none_stale(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """No stale matches returns 0 without calling bulk_abandon."""
        mock_match_repo.find_stale_matches.return_value = []

        result = await match_service.abandon_stale_matches()

        assert result == 0
        mock_match_repo.bulk_abandon.assert_not_awaited()


# ============================================================================
# _finalize_match tests (tested through submit_move and forfeit_match)
# ============================================================================


class TestFinalizeMatch:
    """Tests for _finalize_match behavior via public API."""

    @pytest.mark.asyncio
    async def test_finalize_records_match_result_for_both_players(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_scoring_service: MagicMock,
    ) -> None:
        """Both players get record_match_result called when match completes."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="in_progress",
            player1_moves_remaining=1,
            player2_moves_remaining=0,
            player1_score=500,
            player2_score=300,
            player2_finished_at=datetime.now(timezone.utc),
        )
        mock_match_repo.find_by_id.return_value = record
        mock_match_repo.update.return_value = record
        mock_scoring_service.calculate_move_score.return_value = make_score_result(100)

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)
        await match_service.submit_move(MatchId(match_uuid), PlayerId(p1_uuid), move)

        # record_match_result should have been called for both players.
        record_calls = mock_player_service.record_match_result.call_args_list
        assert len(record_calls) == 2

        # Player 1 won (600 > 300).
        p1_call = record_calls[0]
        assert p1_call[1]["player_id"] == PlayerId(p1_uuid)
        assert p1_call[1]["won"] is True
        assert p1_call[1]["is_draw"] is False

        # Player 2 lost.
        p2_call = record_calls[1]
        assert p2_call[1]["player_id"] == PlayerId(p2_uuid)
        assert p2_call[1]["won"] is False
        assert p2_call[1]["is_draw"] is False

    @pytest.mark.asyncio
    async def test_finalize_updates_elo_for_winner_and_loser(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_scoring_service: MagicMock,
    ) -> None:
        """ELO is updated for winner (increase) and loser (decrease)."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="in_progress",
            player1_moves_remaining=1,
            player2_moves_remaining=0,
            player1_score=500,
            player2_score=300,
            player2_finished_at=datetime.now(timezone.utc),
        )
        mock_match_repo.find_by_id.return_value = record
        mock_match_repo.update.return_value = record
        mock_scoring_service.calculate_move_score.return_value = make_score_result(100)
        mock_player_service.calculate_elo_change.return_value = (15, -15)
        mock_player_service.get_elo.return_value = 1200

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)
        await match_service.submit_move(MatchId(match_uuid), PlayerId(p1_uuid), move)

        # calculate_elo_change called with winner and loser.
        mock_player_service.calculate_elo_change.assert_awaited_once()
        elo_call = mock_player_service.calculate_elo_change.call_args
        assert elo_call[1]["is_draw"] is False

        # update_elo called twice: once for winner (1200+15=1215), once for loser (1200-15=1185).
        elo_update_calls = mock_player_service.update_elo.call_args_list
        assert len(elo_update_calls) == 2
        elo_values = sorted([call[0][1] for call in elo_update_calls])
        assert elo_values == [1185, 1215]

    @pytest.mark.asyncio
    async def test_finalize_updates_elo_for_draw(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_scoring_service: MagicMock,
    ) -> None:
        """On a draw, ELO changes are calculated with is_draw=True."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="in_progress",
            player1_moves_remaining=1,
            player2_moves_remaining=0,
            player1_score=200,
            player2_score=300,  # After +100 points p1=300, p2=300 -> draw
            player2_finished_at=datetime.now(timezone.utc),
        )
        mock_match_repo.find_by_id.return_value = record
        mock_match_repo.update.return_value = record
        mock_scoring_service.calculate_move_score.return_value = make_score_result(100)
        mock_player_service.calculate_elo_change.return_value = (5, -5)
        mock_player_service.get_elo.return_value = 1200

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)
        result = await match_service.submit_move(
            MatchId(match_uuid), PlayerId(p1_uuid), move
        )

        assert result.winner_id is None  # Draw
        # calculate_elo_change called with is_draw=True.
        elo_call = mock_player_service.calculate_elo_change.call_args
        assert elo_call[1]["is_draw"] is True

    @pytest.mark.asyncio
    async def test_forfeit_calls_finalize(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Forfeit also triggers _finalize_match with correct winner."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="in_progress",
            player1_score=100,
            player2_score=200,
        )
        mock_match_repo.find_by_id.return_value = record
        updated = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="completed",
            winner_id=p2_uuid,
            forfeit_by=p1_uuid,
        )
        mock_match_repo.update.return_value = updated

        await match_service.forfeit_match(MatchId(match_uuid), PlayerId(p1_uuid))

        # record_match_result called for both players.
        assert mock_player_service.record_match_result.await_count == 2
        # calculate_elo_change called.
        mock_player_service.calculate_elo_change.assert_awaited_once()
        # update_elo called for both.
        assert mock_player_service.update_elo.await_count == 2


# ============================================================================
# Additional edge-case and integration-style tests
# ============================================================================


class TestEdgeCases:
    """Additional edge-case tests for comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_submit_move_player2_completes_match_p2_wins(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_scoring_service: MagicMock,
    ) -> None:
        """Player2's last move completes the match and p2 wins by higher score."""
        p1_uuid = uuid4()
        p2_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            player2_id=p2_uuid,
            status="in_progress",
            player1_moves_remaining=0,
            player2_moves_remaining=1,
            player1_score=300,
            player2_score=500,
            player1_finished_at=datetime.now(timezone.utc),
        )
        mock_match_repo.find_by_id.return_value = record
        mock_match_repo.update.return_value = record
        mock_scoring_service.calculate_move_score.return_value = make_score_result(100)

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)
        result = await match_service.submit_move(
            MatchId(match_uuid), PlayerId(p2_uuid), move
        )

        assert result.match_completed is True
        # p2_score = 500 + 100 = 600 > p1_score = 300.
        assert result.winner_id == PlayerId(p2_uuid)

    @pytest.mark.asyncio
    async def test_submit_move_chain_not_updated_when_lower(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_board_service: MagicMock,
    ) -> None:
        """If chain_count < current longest_chain, longest_chain stays the same."""
        p1_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            status="in_progress",
            player1_longest_chain=10,
        )
        mock_match_repo.find_by_id.return_value = record
        mock_match_repo.update.return_value = record
        mock_board_service.process_move.return_value = make_move_result(
            valid=True, chain_count=3
        )

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)
        await match_service.submit_move(MatchId(match_uuid), PlayerId(p1_uuid), move)

        update_call = mock_match_repo.update.call_args
        match_update = update_call[0][1]
        assert match_update.player1_longest_chain == 10  # max(10, 3) = 10

    @pytest.mark.asyncio
    async def test_submit_move_no_deadlock_reshuffle_when_no_moves_remain(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
        mock_board_service: MagicMock,
        mock_board_gen_service: MagicMock,
    ) -> None:
        """No reshuffle when player finishes (0 moves left after this move)."""
        p1_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            status="in_progress",
            player1_moves_remaining=1,
        )
        mock_match_repo.find_by_id.return_value = record
        mock_match_repo.update.return_value = record
        # Board has no valid moves after the move.
        mock_board_service.has_valid_moves.return_value = False

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)
        await match_service.submit_move(MatchId(match_uuid), PlayerId(p1_uuid), move)

        # No reshuffle because moves_remaining - 1 = 0 (condition: (moves_remaining - 1) > 0).
        mock_board_gen_service.regenerate_from_deadlock.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_match_generates_random_seed_when_none(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_board_gen_service: MagicMock,
    ) -> None:
        """When board_seed is None, a random seed is generated."""
        p1_id = PlayerId(uuid4())
        p2_id = PlayerId(uuid4())
        record = make_match_record(
            player1_id=UUID(str(p1_id)), player2_id=UUID(str(p2_id))
        )
        mock_match_repo.create.return_value = record

        await match_service.create_match(p1_id, p2_id, board_seed=None)

        call_args = mock_board_gen_service.generate_board_for_match.call_args
        seed_used = call_args[0][0]
        # The seed should be a positive integer (63-bit random).
        assert isinstance(seed_used, int)
        assert seed_used >= 0

    @pytest.mark.asyncio
    async def test_get_match_state_without_player_validation(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """get_match_state with for_player_id=None does no participant check."""
        match_uuid = uuid4()
        record = make_match_record(match_id=match_uuid)
        mock_match_repo.find_by_id.return_value = record

        # Should succeed even though we pass no player for validation.
        result = await match_service.get_match_state(
            MatchId(match_uuid), for_player_id=None
        )

        assert isinstance(result, MatchState)

    @pytest.mark.asyncio
    async def test_get_move_history_with_special_gems(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_move_repo: AsyncMock,
    ) -> None:
        """Move records with special gems data are properly parsed."""
        match_uuid = uuid4()
        record = make_match_record(match_id=match_uuid)
        mock_match_repo.find_by_id.return_value = record

        move_orm = make_move_record_orm(match_id=match_uuid)
        move_orm.special_gems_created = [
            {"row": 2, "col": 3, "gem_type": int(GemType.RADIAL_BOMB)},
        ]
        move_orm.special_gems_activated = [
            {"row": 2, "col": 3},
        ]
        mock_move_repo.find_by_match.return_value = [move_orm]

        result = await match_service.get_move_history(MatchId(match_uuid))

        assert len(result) == 1
        assert len(result[0].special_gems_created) == 1
        pos, gem = result[0].special_gems_created[0]
        assert pos == Position(2, 3)
        assert gem == GemType.RADIAL_BOMB
        assert len(result[0].special_gems_activated) == 1
        assert result[0].special_gems_activated[0] == Position(2, 3)

    @pytest.mark.asyncio
    async def test_submit_move_move_number_increments(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """move_number is correctly computed from moves_made + 1."""
        p1_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            status="in_progress",
            player1_moves_made=7,
        )
        mock_match_repo.find_by_id.return_value = record
        mock_match_repo.update.return_value = record

        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=1000)
        result = await match_service.submit_move(
            MatchId(match_uuid), PlayerId(p1_uuid), move
        )

        assert result.move_number == 8  # 7 + 1

    @pytest.mark.asyncio
    async def test_forfeit_abandoned_match_raises(
        self,
        match_service: MatchService,
        mock_match_repo: AsyncMock,
    ) -> None:
        """Forfeiting an abandoned match raises CONFLICT_MATCH_ALREADY_COMPLETED."""
        p1_uuid = uuid4()
        match_uuid = uuid4()
        record = make_match_record(
            match_id=match_uuid,
            player1_id=p1_uuid,
            status="abandoned",
        )
        mock_match_repo.find_by_id.return_value = record

        with pytest.raises(AppError) as exc_info:
            await match_service.forfeit_match(MatchId(match_uuid), PlayerId(p1_uuid))
        assert exc_info.value.code == "CONFLICT_MATCH_ALREADY_COMPLETED"
