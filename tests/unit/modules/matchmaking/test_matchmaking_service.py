"""Comprehensive unit tests for MatchmakingService.

Tests all 7 public methods plus private helper behavior (via public API):
join_queue, leave_queue, get_queue_status, find_match, process_queue,
cleanup_stale_entries, get_queue_stats, and the internal helpers
_maybe_expand_elo_range, _try_create_match, _re_add_to_queue,
_calculate_queue_position, _estimate_wait_time (tested through public API).

Uses pytest + pytest-asyncio with AsyncMock/MagicMock dependencies.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.core.errors import AppError
from src.core.types.game import MatchId, PlayerId
from src.core.types.player import Player, PlayerType
from src.modules.matchmaking.service import MatchmakingService
from src.modules.matchmaking.types import (
    MatchmakingResult,
    MatchmakingStatus,
    PoolType,
    QueueEntry,
    QueueEntryData,
    QueueStats,
    QueueStatus,
)
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ============================================================================
# Helpers
# ============================================================================


def make_player_id() -> PlayerId:
    """Create a random PlayerId."""
    return PlayerId(uuid4())


def make_match_id() -> MatchId:
    """Create a random MatchId."""
    return MatchId(uuid4())


def make_player(
    player_id: PlayerId | None = None,
    username: str = "player",
    player_type: PlayerType = PlayerType.HUMAN,
    elo_rating: int = 1000,
) -> Player:
    """Create a Player dataclass for testing."""
    return Player(
        id=player_id or make_player_id(),
        username=username,
        player_type=player_type,
        elo_rating=elo_rating,
    )


def make_queue_entry_data(
    player_id: PlayerId | None = None,
    elo_rating: int = 1000,
    pool_type: PoolType = PoolType.MIXED,
    joined_at: datetime | None = None,
    last_expansion_at: datetime | None = None,
    current_min_elo: int = 950,
    current_max_elo: int = 1050,
) -> QueueEntryData:
    """Create a QueueEntryData for testing."""
    now = joined_at or datetime.now(timezone.utc)
    return QueueEntryData(
        player_id=player_id or make_player_id(),
        elo_rating=elo_rating,
        pool_type=pool_type,
        joined_at=now,
        last_expansion_at=last_expansion_at or now,
        current_min_elo=current_min_elo,
        current_max_elo=current_max_elo,
    )


def make_match_state(
    match_id: MatchId | None = None,
    player1_id: PlayerId | None = None,
    player2_id: PlayerId | None = None,
) -> MagicMock:
    """Create a mock MatchState for testing."""
    state = MagicMock()
    state.match_id = match_id or make_match_id()
    state.player1_id = player1_id or make_player_id()
    state.player2_id = player2_id or make_player_id()
    state.status = "pending"
    return state


def make_config(overrides: dict | None = None) -> MockConfigService:
    """Create a MockConfigService with matchmaking defaults."""
    base = {
        "matchmaking.initial_elo_range": 50,
        "matchmaking.elo_range_expansion": 50,
        "matchmaking.elo_range_expansion_interval_seconds": 30,
        "matchmaking.max_elo_range": 500,
        "matchmaking.queue_timeout_seconds": 300,
        "matchmaking.min_wait_before_expansion": 10,
    }
    if overrides:
        base.update(overrides)
    return MockConfigService(base)


def make_service(
    config: MockConfigService | None = None,
    logger: MockLogService | None = None,
    errors: MockErrorService | None = None,
    match_service: AsyncMock | None = None,
    player_service: AsyncMock | None = None,
    queue_repo: AsyncMock | None = None,
) -> MatchmakingService:
    """Create a MatchmakingService with mocked dependencies."""
    _logger = logger or MockLogService()
    _errors = errors or MockErrorService(_logger)
    return MatchmakingService(
        config=config or make_config(),
        logger=_logger,
        errors=_errors,
        match_service=match_service or AsyncMock(),
        player_service=player_service or AsyncMock(),
        matchmaking_queue_repository=queue_repo or AsyncMock(),
    )


# ============================================================================
# join_queue tests
# ============================================================================


class TestJoinQueue:
    """Tests for MatchmakingService.join_queue."""

    @pytest.mark.asyncio
    async def test_join_queue_success(self) -> None:
        """Successfully join the matchmaking queue."""
        player_id = make_player_id()
        player = make_player(player_id=player_id, username="alice", elo_rating=1050)
        entry_data = make_queue_entry_data(
            player_id=player_id,
            elo_rating=1050,
            current_min_elo=1000,
            current_max_elo=1100,
        )

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player
        player_svc.get_elo.return_value = 1050

        match_svc = AsyncMock()
        match_svc.get_active_matches.return_value = []

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = False
        queue_repo.add_to_queue.return_value = entry_data
        queue_repo.get_all_queued_players.return_value = [entry_data]
        queue_repo.get_queue_count.return_value = 1

        svc = make_service(
            player_service=player_svc,
            match_service=match_svc,
            queue_repo=queue_repo,
        )

        result = await svc.join_queue(player_id, PoolType.MIXED)

        assert isinstance(result, QueueEntry)
        assert result.player_id == player_id
        assert result.player_username == "alice"
        assert result.elo_rating == 1050
        assert result.pool_type == PoolType.MIXED
        assert result.position_in_queue == 1
        queue_repo.add_to_queue.assert_called_once()

    @pytest.mark.asyncio
    async def test_join_queue_default_pool(self) -> None:
        """Join with default pool type (MIXED)."""
        player_id = make_player_id()
        player = make_player(player_id=player_id)
        entry_data = make_queue_entry_data(player_id=player_id)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player
        player_svc.get_elo.return_value = 1000

        match_svc = AsyncMock()
        match_svc.get_active_matches.return_value = []

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = False
        queue_repo.add_to_queue.return_value = entry_data
        queue_repo.get_all_queued_players.return_value = [entry_data]
        queue_repo.get_queue_count.return_value = 1

        svc = make_service(
            player_service=player_svc,
            match_service=match_svc,
            queue_repo=queue_repo,
        )

        result = await svc.join_queue(player_id)
        assert result.pool_type == PoolType.MIXED

    @pytest.mark.asyncio
    async def test_join_queue_human_pool(self) -> None:
        """Human player joins human-only pool successfully."""
        player_id = make_player_id()
        player = make_player(player_id=player_id, player_type=PlayerType.HUMAN)
        entry_data = make_queue_entry_data(
            player_id=player_id, pool_type=PoolType.HUMAN
        )

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player
        player_svc.get_elo.return_value = 1000

        match_svc = AsyncMock()
        match_svc.get_active_matches.return_value = []

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = False
        queue_repo.add_to_queue.return_value = entry_data
        queue_repo.get_all_queued_players.return_value = [entry_data]
        queue_repo.get_queue_count.return_value = 1

        svc = make_service(
            player_service=player_svc,
            match_service=match_svc,
            queue_repo=queue_repo,
        )

        result = await svc.join_queue(player_id, PoolType.HUMAN)
        assert result.pool_type == PoolType.HUMAN

    @pytest.mark.asyncio
    async def test_join_queue_bot_in_human_pool_forbidden(self) -> None:
        """Bot player rejected from human-only pool."""
        player_id = make_player_id()
        player = make_player(player_id=player_id, player_type=PlayerType.BOT)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player

        svc = make_service(player_service=player_svc)

        with pytest.raises(AppError) as exc_info:
            await svc.join_queue(player_id, PoolType.HUMAN)

        assert exc_info.value.code == "FORBIDDEN_POOL_RESTRICTED"

    @pytest.mark.asyncio
    async def test_join_queue_human_in_bot_pool_forbidden(self) -> None:
        """Human player rejected from bot-only pool."""
        player_id = make_player_id()
        player = make_player(player_id=player_id, player_type=PlayerType.HUMAN)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player

        svc = make_service(player_service=player_svc)

        with pytest.raises(AppError) as exc_info:
            await svc.join_queue(player_id, PoolType.BOT)

        assert exc_info.value.code == "FORBIDDEN_POOL_RESTRICTED"

    @pytest.mark.asyncio
    async def test_join_queue_bot_in_bot_pool_success(self) -> None:
        """Bot player joins bot-only pool successfully."""
        player_id = make_player_id()
        player = make_player(player_id=player_id, player_type=PlayerType.BOT)
        entry_data = make_queue_entry_data(player_id=player_id, pool_type=PoolType.BOT)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player
        player_svc.get_elo.return_value = 1000

        match_svc = AsyncMock()
        match_svc.get_active_matches.return_value = []

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = False
        queue_repo.add_to_queue.return_value = entry_data
        queue_repo.get_all_queued_players.return_value = [entry_data]
        queue_repo.get_queue_count.return_value = 1

        svc = make_service(
            player_service=player_svc,
            match_service=match_svc,
            queue_repo=queue_repo,
        )

        result = await svc.join_queue(player_id, PoolType.BOT)
        assert result.pool_type == PoolType.BOT

    @pytest.mark.asyncio
    async def test_join_queue_already_in_queue(self) -> None:
        """Player already in queue raises conflict."""
        player_id = make_player_id()
        player = make_player(player_id=player_id)
        existing = make_queue_entry_data(player_id=player_id)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = True
        queue_repo.get_player_queue_state.return_value = existing

        svc = make_service(player_service=player_svc, queue_repo=queue_repo)

        with pytest.raises(AppError) as exc_info:
            await svc.join_queue(player_id)

        assert exc_info.value.code == "CONFLICT_ALREADY_IN_QUEUE"

    @pytest.mark.asyncio
    async def test_join_queue_player_in_active_match(self) -> None:
        """Player in active match raises conflict."""
        player_id = make_player_id()
        player = make_player(player_id=player_id)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player

        match_svc = AsyncMock()
        active_match = make_match_state()
        match_svc.get_active_matches.return_value = [active_match]

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = False

        svc = make_service(
            player_service=player_svc,
            match_service=match_svc,
            queue_repo=queue_repo,
        )

        with pytest.raises(AppError) as exc_info:
            await svc.join_queue(player_id)

        assert exc_info.value.code == "CONFLICT_PLAYER_IN_MATCH"

    @pytest.mark.asyncio
    async def test_join_queue_player_not_found(self) -> None:
        """Non-existent player raises NOT_FOUND."""
        player_id = make_player_id()

        player_svc = AsyncMock()
        player_svc.get_player.side_effect = AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
            http_status=404,
        )

        svc = make_service(player_service=player_svc)

        with pytest.raises(AppError) as exc_info:
            await svc.join_queue(player_id)

        assert exc_info.value.code == "NOT_FOUND_PLAYER"

    @pytest.mark.asyncio
    async def test_join_queue_bot_in_mixed_pool_success(self) -> None:
        """Bot player can join mixed pool."""
        player_id = make_player_id()
        player = make_player(player_id=player_id, player_type=PlayerType.BOT)
        entry_data = make_queue_entry_data(
            player_id=player_id, pool_type=PoolType.MIXED
        )

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player
        player_svc.get_elo.return_value = 1000

        match_svc = AsyncMock()
        match_svc.get_active_matches.return_value = []

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = False
        queue_repo.add_to_queue.return_value = entry_data
        queue_repo.get_all_queued_players.return_value = [entry_data]
        queue_repo.get_queue_count.return_value = 1

        svc = make_service(
            player_service=player_svc,
            match_service=match_svc,
            queue_repo=queue_repo,
        )

        result = await svc.join_queue(player_id, PoolType.MIXED)
        assert result.pool_type == PoolType.MIXED

    @pytest.mark.asyncio
    async def test_join_queue_logs_event(self) -> None:
        """Joining queue logs the correct event."""
        player_id = make_player_id()
        player = make_player(player_id=player_id, username="alice")
        entry_data = make_queue_entry_data(player_id=player_id)
        logger = MockLogService()

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player
        player_svc.get_elo.return_value = 1000

        match_svc = AsyncMock()
        match_svc.get_active_matches.return_value = []

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = False
        queue_repo.add_to_queue.return_value = entry_data
        queue_repo.get_all_queued_players.return_value = [entry_data]
        queue_repo.get_queue_count.return_value = 1

        svc = make_service(
            logger=logger,
            player_service=player_svc,
            match_service=match_svc,
            queue_repo=queue_repo,
        )

        await svc.join_queue(player_id)
        logger.assert_logged("INFO", "Player joined matchmaking queue")


# ============================================================================
# leave_queue tests
# ============================================================================


class TestLeaveQueue:
    """Tests for MatchmakingService.leave_queue."""

    @pytest.mark.asyncio
    async def test_leave_queue_success(self) -> None:
        """Successfully leave the queue."""
        player_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.remove_from_queue.return_value = True

        svc = make_service(queue_repo=queue_repo)

        result = await svc.leave_queue(player_id)
        assert result is True
        queue_repo.remove_from_queue.assert_called_once_with(player_id)

    @pytest.mark.asyncio
    async def test_leave_queue_not_in_queue(self) -> None:
        """Leaving when not in queue returns False."""
        player_id = make_player_id()

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = None
        queue_repo.remove_from_queue.return_value = False

        svc = make_service(queue_repo=queue_repo)

        result = await svc.leave_queue(player_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_leave_queue_logs_event(self) -> None:
        """Leaving queue logs the correct event."""
        player_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)
        logger = MockLogService()

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.remove_from_queue.return_value = True

        svc = make_service(logger=logger, queue_repo=queue_repo)

        await svc.leave_queue(player_id)
        logger.assert_logged("INFO", "Player left matchmaking queue")

    @pytest.mark.asyncio
    async def test_leave_queue_no_log_when_not_in_queue(self) -> None:
        """No log event when player was not in queue."""
        player_id = make_player_id()
        logger = MockLogService()

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = None
        queue_repo.remove_from_queue.return_value = False

        svc = make_service(logger=logger, queue_repo=queue_repo)

        await svc.leave_queue(player_id)
        assert not any(
            "Player left matchmaking queue" in e["message"]
            for e in logger.entries
            if e["level"] == "INFO"
        )


# ============================================================================
# get_queue_status tests
# ============================================================================


class TestGetQueueStatus:
    """Tests for MatchmakingService.get_queue_status."""

    @pytest.mark.asyncio
    async def test_get_queue_status_in_queue(self) -> None:
        """Get status when player is in queue."""
        player_id = make_player_id()
        entry_data = make_queue_entry_data(
            player_id=player_id,
            elo_rating=1050,
            current_min_elo=1000,
            current_max_elo=1100,
        )

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = [
            (make_player_id(), 1020),
            (make_player_id(), 1080),
        ]
        queue_repo.get_all_queued_players.return_value = [entry_data]
        queue_repo.get_queue_count.return_value = 3

        svc = make_service(queue_repo=queue_repo)

        result = await svc.get_queue_status(player_id)

        assert result is not None
        assert isinstance(result, QueueStatus)
        assert result.player_id == player_id
        assert result.elo_rating == 1050
        assert result.potential_opponents == 2
        assert result.position_in_queue == 1

    @pytest.mark.asyncio
    async def test_get_queue_status_not_in_queue(self) -> None:
        """Get status returns None when player not in queue."""
        player_id = make_player_id()

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = None

        svc = make_service(queue_repo=queue_repo)

        result = await svc.get_queue_status(player_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_queue_status_wait_time(self) -> None:
        """Wait time is calculated correctly."""
        player_id = make_player_id()
        joined = datetime.now(timezone.utc) - timedelta(seconds=45)
        entry_data = make_queue_entry_data(
            player_id=player_id,
            joined_at=joined,
            last_expansion_at=joined,
        )

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = []
        queue_repo.get_all_queued_players.return_value = [entry_data]
        queue_repo.get_queue_count.return_value = 1

        svc = make_service(queue_repo=queue_repo)

        result = await svc.get_queue_status(player_id)
        assert result is not None
        assert result.wait_time_seconds >= 44  # Allow 1s tolerance


# ============================================================================
# find_match tests
# ============================================================================


class TestFindMatch:
    """Tests for MatchmakingService.find_match."""

    @pytest.mark.asyncio
    async def test_find_match_success(self) -> None:
        """Successfully find and create a match."""
        player_id = make_player_id()
        opponent_id = make_player_id()
        match_id = make_match_id()

        entry_data = make_queue_entry_data(
            player_id=player_id,
            elo_rating=1000,
            current_min_elo=950,
            current_max_elo=1050,
        )

        match_state = make_match_state(match_id=match_id)

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = [(opponent_id, 1020)]
        queue_repo.atomic_remove_pair.return_value = True

        match_svc = AsyncMock()
        match_svc.create_match.return_value = match_state

        svc = make_service(match_service=match_svc, queue_repo=queue_repo)

        result = await svc.find_match(player_id)

        assert result.status == MatchmakingStatus.MATCHED
        assert result.player_id == player_id
        assert result.opponent_id == opponent_id
        assert result.match_id == match_id
        assert result.elo_difference == 20
        assert result.message == "Match found!"

    @pytest.mark.asyncio
    async def test_find_match_not_in_queue(self) -> None:
        """Finding match when not in queue raises validation error."""
        player_id = make_player_id()

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = None

        svc = make_service(queue_repo=queue_repo)

        with pytest.raises(AppError) as exc_info:
            await svc.find_match(player_id)

        assert exc_info.value.code == "VALIDATION_NOT_IN_QUEUE"

    @pytest.mark.asyncio
    async def test_find_match_timeout(self) -> None:
        """Player who has timed out gets EXPIRED status."""
        player_id = make_player_id()
        old_time = datetime.now(timezone.utc) - timedelta(seconds=400)
        entry_data = make_queue_entry_data(
            player_id=player_id,
            joined_at=old_time,
            last_expansion_at=old_time,
        )

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.remove_from_queue.return_value = True

        svc = make_service(queue_repo=queue_repo)

        result = await svc.find_match(player_id)

        assert result.status == MatchmakingStatus.EXPIRED
        assert result.wait_time_seconds >= 399
        queue_repo.remove_from_queue.assert_called_once_with(player_id)

    @pytest.mark.asyncio
    async def test_find_match_no_opponents(self) -> None:
        """No opponents in range returns SEARCHING."""
        player_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = []

        svc = make_service(queue_repo=queue_repo)

        result = await svc.find_match(player_id)

        assert result.status == MatchmakingStatus.SEARCHING
        assert result.message == "Searching for opponent"

    @pytest.mark.asyncio
    async def test_find_match_opponent_taken(self) -> None:
        """When all opponents are taken, returns SEARCHING."""
        player_id = make_player_id()
        opponent_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = [(opponent_id, 1000)]
        queue_repo.atomic_remove_pair.return_value = False

        svc = make_service(queue_repo=queue_repo)

        result = await svc.find_match(player_id)

        assert result.status == MatchmakingStatus.SEARCHING
        assert result.message == "Opponent selection in progress"

    @pytest.mark.asyncio
    async def test_find_match_tries_multiple_opponents(self) -> None:
        """Tries next opponent when first is taken."""
        player_id = make_player_id()
        opp1_id = make_player_id()
        opp2_id = make_player_id()
        match_id = make_match_id()
        entry_data = make_queue_entry_data(player_id=player_id)
        match_state = make_match_state(match_id=match_id)

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = [
            (opp1_id, 1000),
            (opp2_id, 1020),
        ]
        # First opponent taken, second available
        queue_repo.atomic_remove_pair.side_effect = [False, True]

        match_svc = AsyncMock()
        match_svc.create_match.return_value = match_state

        svc = make_service(match_service=match_svc, queue_repo=queue_repo)

        result = await svc.find_match(player_id)

        assert result.status == MatchmakingStatus.MATCHED
        assert result.opponent_id == opp2_id

    @pytest.mark.asyncio
    async def test_find_match_creation_fails_compensates(self) -> None:
        """Match creation failure re-adds players and raises INTERNAL error."""
        player_id = make_player_id()
        opponent_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = [(opponent_id, 1000)]
        queue_repo.atomic_remove_pair.return_value = True
        queue_repo.add_to_queue.return_value = entry_data  # For re-add

        match_svc = AsyncMock()
        match_svc.create_match.side_effect = AppError(
            code="INTERNAL_UNEXPECTED",
            message="DB error",
            http_status=500,
        )

        svc = make_service(match_service=match_svc, queue_repo=queue_repo)

        with pytest.raises(AppError) as exc_info:
            await svc.find_match(player_id)

        assert exc_info.value.code == "INTERNAL_MATCHMAKING_ERROR"
        # Verify re-add was called twice (once per player)
        assert queue_repo.add_to_queue.call_count == 2

    @pytest.mark.asyncio
    async def test_find_match_logs_match_found(self) -> None:
        """Successful match logs the match found event."""
        player_id = make_player_id()
        opponent_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)
        match_state = make_match_state()
        logger = MockLogService()

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = [(opponent_id, 1000)]
        queue_repo.atomic_remove_pair.return_value = True

        match_svc = AsyncMock()
        match_svc.create_match.return_value = match_state

        svc = make_service(
            logger=logger, match_service=match_svc, queue_repo=queue_repo
        )

        await svc.find_match(player_id)
        logger.assert_logged("INFO", "Match found")

    @pytest.mark.asyncio
    async def test_find_match_logs_timeout(self) -> None:
        """Timeout logs the queue timeout event."""
        player_id = make_player_id()
        old_time = datetime.now(timezone.utc) - timedelta(seconds=400)
        entry_data = make_queue_entry_data(
            player_id=player_id,
            joined_at=old_time,
            last_expansion_at=old_time,
        )
        logger = MockLogService()

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.remove_from_queue.return_value = True

        svc = make_service(logger=logger, queue_repo=queue_repo)

        await svc.find_match(player_id)
        logger.assert_logged("INFO", "Player queue timeout")


# ============================================================================
# process_queue tests
# ============================================================================


class TestProcessQueue:
    """Tests for MatchmakingService.process_queue."""

    @pytest.mark.asyncio
    async def test_process_queue_empty(self) -> None:
        """Processing empty queue returns empty list."""
        queue_repo = AsyncMock()
        queue_repo.get_all_queued_players.return_value = []

        svc = make_service(queue_repo=queue_repo)

        results = await svc.process_queue(PoolType.MIXED)
        assert results == []

    @pytest.mark.asyncio
    async def test_process_queue_single_player(self) -> None:
        """Single player cannot be matched."""
        player_id = make_player_id()
        entry = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        queue_repo.get_all_queued_players.return_value = [entry]
        queue_repo.get_player_queue_state.return_value = entry
        queue_repo.find_opponents_in_range.return_value = []

        svc = make_service(queue_repo=queue_repo)

        results = await svc.process_queue(PoolType.MIXED)
        assert results == []

    @pytest.mark.asyncio
    async def test_process_queue_two_players_matched(self) -> None:
        """Two compatible players are matched."""
        p1_id = make_player_id()
        p2_id = make_player_id()
        match_id = make_match_id()

        entry1 = make_queue_entry_data(player_id=p1_id, elo_rating=1000)
        entry2 = make_queue_entry_data(player_id=p2_id, elo_rating=1020)

        queue_repo = AsyncMock()
        queue_repo.get_all_queued_players.return_value = [entry1, entry2]
        queue_repo.get_player_queue_state.side_effect = lambda pid: (
            entry1 if pid == p1_id else entry2
        )
        queue_repo.find_opponents_in_range.return_value = [(p2_id, 1020)]
        queue_repo.atomic_remove_pair.return_value = True

        match_state = make_match_state(match_id=match_id)
        match_svc = AsyncMock()
        match_svc.create_match.return_value = match_state

        svc = make_service(match_service=match_svc, queue_repo=queue_repo)

        results = await svc.process_queue(PoolType.MIXED)
        assert len(results) == 1
        assert results[0].status == MatchmakingStatus.MATCHED

    @pytest.mark.asyncio
    async def test_process_queue_four_players_two_matches(self) -> None:
        """Four players produce two matches."""
        p1_id = make_player_id()
        p2_id = make_player_id()
        p3_id = make_player_id()
        p4_id = make_player_id()

        entry1 = make_queue_entry_data(player_id=p1_id, elo_rating=1000)
        entry2 = make_queue_entry_data(player_id=p2_id, elo_rating=1010)
        entry3 = make_queue_entry_data(player_id=p3_id, elo_rating=1020)
        entry4 = make_queue_entry_data(player_id=p4_id, elo_rating=1030)

        queue_repo = AsyncMock()
        queue_repo.get_all_queued_players.return_value = [
            entry1,
            entry2,
            entry3,
            entry4,
        ]

        def get_state(pid):
            for e in [entry1, entry2, entry3, entry4]:
                if e.player_id == pid:
                    return e
            return None

        queue_repo.get_player_queue_state.side_effect = get_state

        # Each player finds the next as opponent
        call_count = [0]

        def find_opponents(pool_type, min_elo, max_elo, exclude_player_id, limit=10):
            call_count[0] += 1
            if exclude_player_id == p1_id:
                return [(p2_id, 1010)]
            elif exclude_player_id == p3_id:
                return [(p4_id, 1030)]
            return []

        queue_repo.find_opponents_in_range.side_effect = find_opponents
        queue_repo.atomic_remove_pair.return_value = True

        match_svc = AsyncMock()
        match_svc.create_match.return_value = make_match_state()

        svc = make_service(match_service=match_svc, queue_repo=queue_repo)

        results = await svc.process_queue(PoolType.MIXED)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_process_queue_skips_already_matched(self) -> None:
        """Already-matched players are skipped in processing."""
        p1_id = make_player_id()
        p2_id = make_player_id()
        p3_id = make_player_id()

        entry1 = make_queue_entry_data(player_id=p1_id, elo_rating=1000)
        entry2 = make_queue_entry_data(player_id=p2_id, elo_rating=1010)
        entry3 = make_queue_entry_data(player_id=p3_id, elo_rating=1020)

        queue_repo = AsyncMock()
        queue_repo.get_all_queued_players.return_value = [entry1, entry2, entry3]

        def get_state(pid):
            for e in [entry1, entry2, entry3]:
                if e.player_id == pid:
                    return e
            return None

        queue_repo.get_player_queue_state.side_effect = get_state

        # p1 matches with p2, p3 finds no remaining opponents
        def find_opponents(pool_type, min_elo, max_elo, exclude_player_id, limit=10):
            if exclude_player_id == p1_id:
                return [(p2_id, 1010), (p3_id, 1020)]
            return []

        queue_repo.find_opponents_in_range.side_effect = find_opponents
        queue_repo.atomic_remove_pair.return_value = True

        match_svc = AsyncMock()
        match_svc.create_match.return_value = make_match_state()

        svc = make_service(match_service=match_svc, queue_repo=queue_repo)

        results = await svc.process_queue(PoolType.MIXED)
        # Only 1 match: p1-p2. p3 has no unmatched opponent remaining
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_process_queue_logs_summary(self) -> None:
        """Queue processing logs summary."""
        logger = MockLogService()
        queue_repo = AsyncMock()
        queue_repo.get_all_queued_players.return_value = []

        svc = make_service(logger=logger, queue_repo=queue_repo)

        await svc.process_queue(PoolType.MIXED)
        logger.assert_logged("DEBUG", "Queue processed")


# ============================================================================
# cleanup_stale_entries tests
# ============================================================================


class TestCleanupStaleEntries:
    """Tests for MatchmakingService.cleanup_stale_entries."""

    @pytest.mark.asyncio
    async def test_cleanup_no_stale_entries(self) -> None:
        """No stale entries returns 0."""
        queue_repo = AsyncMock()
        queue_repo.remove_stale_entries.return_value = 0

        svc = make_service(queue_repo=queue_repo)

        result = await svc.cleanup_stale_entries()
        assert result == 0

    @pytest.mark.asyncio
    async def test_cleanup_removes_stale_entries(self) -> None:
        """Stale entries are removed and count returned."""
        queue_repo = AsyncMock()
        queue_repo.remove_stale_entries.return_value = 5

        svc = make_service(queue_repo=queue_repo)

        result = await svc.cleanup_stale_entries()
        assert result == 5

    @pytest.mark.asyncio
    async def test_cleanup_logs_when_entries_removed(self) -> None:
        """Logs cleanup when entries are removed."""
        logger = MockLogService()
        queue_repo = AsyncMock()
        queue_repo.remove_stale_entries.return_value = 3

        svc = make_service(logger=logger, queue_repo=queue_repo)

        await svc.cleanup_stale_entries()
        logger.assert_logged("INFO", "Stale entries cleaned up")

    @pytest.mark.asyncio
    async def test_cleanup_no_log_when_zero(self) -> None:
        """No log when no entries removed."""
        logger = MockLogService()
        queue_repo = AsyncMock()
        queue_repo.remove_stale_entries.return_value = 0

        svc = make_service(logger=logger, queue_repo=queue_repo)

        await svc.cleanup_stale_entries()
        assert not any(
            "Stale entries cleaned up" in e["message"]
            for e in logger.entries
            if e["level"] == "INFO"
        )

    @pytest.mark.asyncio
    async def test_cleanup_uses_correct_cutoff(self) -> None:
        """Cutoff time uses queue_timeout_seconds config."""
        config = make_config({"matchmaking.queue_timeout_seconds": 120})
        queue_repo = AsyncMock()
        queue_repo.remove_stale_entries.return_value = 0

        svc = make_service(config=config, queue_repo=queue_repo)

        await svc.cleanup_stale_entries()

        call_args = queue_repo.remove_stale_entries.call_args
        cutoff = call_args[0][0] if call_args[0] else call_args[1].get("cutoff_time")
        now = datetime.now(timezone.utc)
        expected_cutoff = now - timedelta(seconds=120)
        # Allow 2 second tolerance
        assert abs((cutoff - expected_cutoff).total_seconds()) < 2


# ============================================================================
# get_queue_stats tests
# ============================================================================


class TestGetQueueStats:
    """Tests for MatchmakingService.get_queue_stats."""

    @pytest.mark.asyncio
    async def test_get_stats_specific_pool(self) -> None:
        """Get stats for a specific pool."""
        queue_repo = AsyncMock()
        queue_repo.get_queue_count.return_value = 10
        queue_repo.get_players_by_elo_bucket.return_value = {
            "900-1000": 3,
            "1000-1100": 7,
        }
        queue_repo.get_all_queued_players.return_value = []

        svc = make_service(queue_repo=queue_repo)

        result = await svc.get_queue_stats(PoolType.MIXED)

        assert isinstance(result, QueueStats)
        assert result.pool_type == PoolType.MIXED
        assert result.total_players == 10
        assert result.players_by_elo_bucket == {"900-1000": 3, "1000-1100": 7}

    @pytest.mark.asyncio
    async def test_get_stats_all_pools(self) -> None:
        """Get aggregate stats across all pools."""
        queue_repo = AsyncMock()
        queue_repo.get_queue_count.return_value = 5
        queue_repo.get_players_by_elo_bucket.return_value = {}
        queue_repo.get_all_queued_players.return_value = []

        svc = make_service(queue_repo=queue_repo)

        result = await svc.get_queue_stats(None)

        assert result.pool_type is None
        # 5 per pool * 3 pools = 15
        assert result.total_players == 15

    @pytest.mark.asyncio
    async def test_get_stats_empty_queue(self) -> None:
        """Empty queue returns zero stats."""
        queue_repo = AsyncMock()
        queue_repo.get_queue_count.return_value = 0
        queue_repo.get_players_by_elo_bucket.return_value = {}
        queue_repo.get_all_queued_players.return_value = []

        svc = make_service(queue_repo=queue_repo)

        result = await svc.get_queue_stats(PoolType.MIXED)

        assert result.total_players == 0
        assert result.average_wait_seconds == 0.0
        assert result.longest_wait_seconds == 0

    @pytest.mark.asyncio
    async def test_get_stats_calculates_wait_times(self) -> None:
        """Wait time statistics are calculated correctly."""
        p1_id = make_player_id()
        p2_id = make_player_id()

        now = datetime.now(timezone.utc)
        entry1 = make_queue_entry_data(
            player_id=p1_id,
            joined_at=now - timedelta(seconds=60),
            last_expansion_at=now - timedelta(seconds=60),
        )
        entry2 = make_queue_entry_data(
            player_id=p2_id,
            joined_at=now - timedelta(seconds=30),
            last_expansion_at=now - timedelta(seconds=30),
        )

        queue_repo = AsyncMock()
        queue_repo.get_queue_count.return_value = 2
        queue_repo.get_players_by_elo_bucket.return_value = {}
        queue_repo.get_all_queued_players.return_value = [entry1, entry2]

        svc = make_service(queue_repo=queue_repo)

        result = await svc.get_queue_stats(PoolType.MIXED)

        # Average should be around 45 seconds
        assert 43 <= result.average_wait_seconds <= 62
        # Longest should be around 60 seconds
        assert result.longest_wait_seconds >= 58


# ============================================================================
# ELO range expansion tests (via find_match)
# ============================================================================


class TestEloRangeExpansion:
    """Tests for _maybe_expand_elo_range (tested via find_match)."""

    @pytest.mark.asyncio
    async def test_no_expansion_before_min_wait(self) -> None:
        """No expansion when wait time is below min_wait_before_expansion."""
        player_id = make_player_id()
        now = datetime.now(timezone.utc)
        entry_data = make_queue_entry_data(
            player_id=player_id,
            joined_at=now - timedelta(seconds=5),
            last_expansion_at=now - timedelta(seconds=5),
        )

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = []

        svc = make_service(queue_repo=queue_repo)

        await svc.find_match(player_id)
        queue_repo.update_elo_range.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_expansion_before_interval(self) -> None:
        """No expansion when interval since last expansion hasn't passed."""
        player_id = make_player_id()
        now = datetime.now(timezone.utc)
        entry_data = make_queue_entry_data(
            player_id=player_id,
            joined_at=now - timedelta(seconds=20),
            last_expansion_at=now - timedelta(seconds=5),
        )

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = []

        config = make_config({"matchmaking.elo_range_expansion_interval_seconds": 30})
        svc = make_service(config=config, queue_repo=queue_repo)

        await svc.find_match(player_id)
        queue_repo.update_elo_range.assert_not_called()

    @pytest.mark.asyncio
    async def test_expansion_triggered(self) -> None:
        """ELO range is expanded when conditions are met."""
        player_id = make_player_id()
        now = datetime.now(timezone.utc)
        entry_data = make_queue_entry_data(
            player_id=player_id,
            elo_rating=1000,
            joined_at=now - timedelta(seconds=60),
            last_expansion_at=now - timedelta(seconds=40),
            current_min_elo=950,
            current_max_elo=1050,
        )

        # After expansion, return updated entry
        expanded_entry = make_queue_entry_data(
            player_id=player_id,
            elo_rating=1000,
            joined_at=now - timedelta(seconds=60),
            last_expansion_at=now,
            current_min_elo=900,
            current_max_elo=1100,
        )

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.side_effect = [entry_data, expanded_entry]
        queue_repo.find_opponents_in_range.return_value = []

        config = make_config({"matchmaking.elo_range_expansion_interval_seconds": 30})
        svc = make_service(config=config, queue_repo=queue_repo)

        await svc.find_match(player_id)
        queue_repo.update_elo_range.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_expansion_at_max_range(self) -> None:
        """No expansion when already at max range."""
        player_id = make_player_id()
        now = datetime.now(timezone.utc)
        entry_data = make_queue_entry_data(
            player_id=player_id,
            elo_rating=1000,
            joined_at=now - timedelta(seconds=600),
            last_expansion_at=now - timedelta(seconds=60),
            current_min_elo=500,
            current_max_elo=1500,
        )

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = []

        svc = make_service(queue_repo=queue_repo)

        await svc.find_match(player_id)
        queue_repo.update_elo_range.assert_not_called()

    @pytest.mark.asyncio
    async def test_expansion_logs_debug(self) -> None:
        """ELO range expansion logs a debug event."""
        player_id = make_player_id()
        now = datetime.now(timezone.utc)
        entry_data = make_queue_entry_data(
            player_id=player_id,
            elo_rating=1000,
            joined_at=now - timedelta(seconds=60),
            last_expansion_at=now - timedelta(seconds=40),
            current_min_elo=950,
            current_max_elo=1050,
        )
        expanded_entry = make_queue_entry_data(
            player_id=player_id,
            elo_rating=1000,
            joined_at=now - timedelta(seconds=60),
            last_expansion_at=now,
            current_min_elo=900,
            current_max_elo=1100,
        )
        logger = MockLogService()

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.side_effect = [entry_data, expanded_entry]
        queue_repo.find_opponents_in_range.return_value = []

        config = make_config({"matchmaking.elo_range_expansion_interval_seconds": 30})
        svc = make_service(config=config, logger=logger, queue_repo=queue_repo)

        await svc.find_match(player_id)
        logger.assert_logged("DEBUG", "ELO range expanded")


# ============================================================================
# Configuration tests
# ============================================================================


class TestConfiguration:
    """Tests for configuration key handling."""

    @pytest.mark.asyncio
    async def test_custom_initial_elo_range(self) -> None:
        """Custom initial_elo_range is used."""
        player_id = make_player_id()
        player = make_player(player_id=player_id, elo_rating=1000)
        entry_data = make_queue_entry_data(player_id=player_id)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player
        player_svc.get_elo.return_value = 1000

        match_svc = AsyncMock()
        match_svc.get_active_matches.return_value = []

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = False
        queue_repo.add_to_queue.return_value = entry_data
        queue_repo.get_all_queued_players.return_value = [entry_data]
        queue_repo.get_queue_count.return_value = 1

        config = make_config({"matchmaking.initial_elo_range": 100})
        svc = make_service(
            config=config,
            player_service=player_svc,
            match_service=match_svc,
            queue_repo=queue_repo,
        )

        await svc.join_queue(player_id)
        # Verify add_to_queue was called with initial_elo_range=100
        call_kwargs = queue_repo.add_to_queue.call_args
        assert (
            call_kwargs[1]["initial_elo_range"] == 100
            or call_kwargs.kwargs.get("initial_elo_range") == 100
        )

    @pytest.mark.asyncio
    async def test_custom_timeout(self) -> None:
        """Custom queue_timeout_seconds is used."""
        player_id = make_player_id()
        # Set joined_at to 65 seconds ago, with timeout of 60
        old_time = datetime.now(timezone.utc) - timedelta(seconds=65)
        entry_data = make_queue_entry_data(
            player_id=player_id,
            joined_at=old_time,
            last_expansion_at=old_time,
        )

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.remove_from_queue.return_value = True

        config = make_config({"matchmaking.queue_timeout_seconds": 60})
        svc = make_service(config=config, queue_repo=queue_repo)

        result = await svc.find_match(player_id)
        assert result.status == MatchmakingStatus.EXPIRED


# ============================================================================
# Queue position and wait estimation tests
# ============================================================================


class TestQueuePositionAndEstimation:
    """Tests for _calculate_queue_position and _estimate_wait_time."""

    @pytest.mark.asyncio
    async def test_position_first_in_queue(self) -> None:
        """First player has position 1."""
        player_id = make_player_id()
        entry = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        queue_repo.get_all_queued_players.return_value = [entry]
        queue_repo.get_queue_count.return_value = 1

        svc = make_service(queue_repo=queue_repo)

        position = await svc._calculate_queue_position(player_id, PoolType.MIXED)
        assert position == 1

    @pytest.mark.asyncio
    async def test_position_third_in_queue(self) -> None:
        """Third player has position 3."""
        p1_id = make_player_id()
        p2_id = make_player_id()
        p3_id = make_player_id()

        entries = [
            make_queue_entry_data(player_id=p1_id),
            make_queue_entry_data(player_id=p2_id),
            make_queue_entry_data(player_id=p3_id),
        ]

        queue_repo = AsyncMock()
        queue_repo.get_all_queued_players.return_value = entries

        svc = make_service(queue_repo=queue_repo)

        position = await svc._calculate_queue_position(p3_id, PoolType.MIXED)
        assert position == 3

    @pytest.mark.asyncio
    async def test_estimate_none_for_empty_queue(self) -> None:
        """Estimate is None when queue has 0 or 1 player."""
        queue_repo = AsyncMock()
        queue_repo.get_queue_count.return_value = 1

        svc = make_service(queue_repo=queue_repo)

        estimate = await svc._estimate_wait_time(1000, PoolType.MIXED)
        assert estimate is None

    @pytest.mark.asyncio
    async def test_estimate_returns_int_for_populated_queue(self) -> None:
        """Estimate is an integer for populated queue."""
        queue_repo = AsyncMock()
        queue_repo.get_queue_count.return_value = 10

        svc = make_service(queue_repo=queue_repo)

        estimate = await svc._estimate_wait_time(1000, PoolType.MIXED)
        assert estimate is not None
        assert isinstance(estimate, int)
        assert estimate >= 5


# ============================================================================
# Error propagation tests
# ============================================================================


class TestErrorPropagation:
    """Tests for proper error handling and propagation."""

    @pytest.mark.asyncio
    async def test_player_not_found_propagates(self) -> None:
        """NOT_FOUND_PLAYER from player_service propagates unchanged."""
        player_id = make_player_id()

        player_svc = AsyncMock()
        player_svc.get_player.side_effect = AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
            http_status=404,
        )

        svc = make_service(player_service=player_svc)

        with pytest.raises(AppError) as exc_info:
            await svc.join_queue(player_id)

        assert exc_info.value.code == "NOT_FOUND_PLAYER"
        assert exc_info.value.http_status == 404

    @pytest.mark.asyncio
    async def test_forbidden_error_has_context(self) -> None:
        """FORBIDDEN_POOL_RESTRICTED error includes context fields."""
        player_id = make_player_id()
        player = make_player(player_id=player_id, player_type=PlayerType.BOT)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player

        svc = make_service(player_service=player_svc)

        with pytest.raises(AppError) as exc_info:
            await svc.join_queue(player_id, PoolType.HUMAN)

        error = exc_info.value
        assert error.code == "FORBIDDEN_POOL_RESTRICTED"
        assert error.context.get("player_type") == "bot"
        assert error.context.get("pool_type") == "human"

    @pytest.mark.asyncio
    async def test_conflict_error_includes_match_id(self) -> None:
        """CONFLICT_PLAYER_IN_MATCH includes active match ID."""
        player_id = make_player_id()
        match_id = make_match_id()
        player = make_player(player_id=player_id)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player

        match_svc = AsyncMock()
        active_match = make_match_state(match_id=match_id)
        match_svc.get_active_matches.return_value = [active_match]

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = False

        svc = make_service(
            player_service=player_svc,
            match_service=match_svc,
            queue_repo=queue_repo,
        )

        with pytest.raises(AppError) as exc_info:
            await svc.join_queue(player_id)

        error = exc_info.value
        assert error.code == "CONFLICT_PLAYER_IN_MATCH"
        assert str(match_id) in error.context.get("active_match_id", "")

    @pytest.mark.asyncio
    async def test_internal_error_on_match_creation_failure(self) -> None:
        """INTERNAL_MATCHMAKING_ERROR on match creation failure includes context."""
        player_id = make_player_id()
        opponent_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = [(opponent_id, 1000)]
        queue_repo.atomic_remove_pair.return_value = True
        queue_repo.add_to_queue.return_value = entry_data

        match_svc = AsyncMock()
        match_svc.create_match.side_effect = AppError(
            code="INTERNAL_UNEXPECTED",
            message="Database error",
            http_status=500,
        )

        svc = make_service(match_service=match_svc, queue_repo=queue_repo)

        with pytest.raises(AppError) as exc_info:
            await svc.find_match(player_id)

        error = exc_info.value
        assert error.code == "INTERNAL_MATCHMAKING_ERROR"
        assert str(player_id) in error.context.get("player_id", "")
        assert str(opponent_id) in error.context.get("opponent_id", "")


# ============================================================================
# Edge case tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases documented in the artifact."""

    @pytest.mark.asyncio
    async def test_ec4_player_cannot_be_in_multiple_queues(self) -> None:
        """Player cannot be in multiple pools simultaneously (EC-4)."""
        player_id = make_player_id()
        player = make_player(player_id=player_id)
        existing = make_queue_entry_data(player_id=player_id, pool_type=PoolType.MIXED)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player

        queue_repo = AsyncMock()
        queue_repo.is_in_queue.return_value = True
        queue_repo.get_player_queue_state.return_value = existing

        svc = make_service(player_service=player_svc, queue_repo=queue_repo)

        with pytest.raises(AppError) as exc_info:
            await svc.join_queue(player_id, PoolType.HUMAN)

        assert exc_info.value.code == "CONFLICT_ALREADY_IN_QUEUE"

    @pytest.mark.asyncio
    async def test_ec6_bot_in_human_pool_rejected(self) -> None:
        """Bot cannot join human-only pool (EC-6)."""
        player_id = make_player_id()
        player = make_player(player_id=player_id, player_type=PlayerType.BOT)

        player_svc = AsyncMock()
        player_svc.get_player.return_value = player

        svc = make_service(player_service=player_svc)

        with pytest.raises(AppError) as exc_info:
            await svc.join_queue(player_id, PoolType.HUMAN)

        assert exc_info.value.code == "FORBIDDEN_POOL_RESTRICTED"

    @pytest.mark.asyncio
    async def test_ec8_empty_queue_returns_searching(self) -> None:
        """Empty queue returns SEARCHING status (EC-8)."""
        player_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = []

        svc = make_service(queue_repo=queue_repo)

        result = await svc.find_match(player_id)
        assert result.status == MatchmakingStatus.SEARCHING

    @pytest.mark.asyncio
    async def test_ec3_match_creation_fails_compensates(self) -> None:
        """Failed match creation re-adds both players (EC-3)."""
        player_id = make_player_id()
        opponent_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = [(opponent_id, 1000)]
        queue_repo.atomic_remove_pair.return_value = True
        queue_repo.add_to_queue.return_value = entry_data

        match_svc = AsyncMock()
        match_svc.create_match.side_effect = AppError(
            code="INTERNAL_UNEXPECTED",
            message="DB failure",
            http_status=500,
        )

        svc = make_service(match_service=match_svc, queue_repo=queue_repo)

        with pytest.raises(AppError):
            await svc.find_match(player_id)

        # Both players should be re-added
        assert queue_repo.add_to_queue.call_count == 2

    @pytest.mark.asyncio
    async def test_ec2_atomic_remove_handles_race(self) -> None:
        """Atomic remove pair handles race condition (EC-2)."""
        player_id = make_player_id()
        opponent_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = entry_data
        queue_repo.find_opponents_in_range.return_value = [(opponent_id, 1000)]
        queue_repo.atomic_remove_pair.return_value = False  # Race condition

        svc = make_service(queue_repo=queue_repo)

        result = await svc.find_match(player_id)
        assert result.status == MatchmakingStatus.SEARCHING

    @pytest.mark.asyncio
    async def test_leave_queue_idempotent(self) -> None:
        """Leaving queue when not in queue is a no-op."""
        player_id = make_player_id()

        queue_repo = AsyncMock()
        queue_repo.get_player_queue_state.return_value = None
        queue_repo.remove_from_queue.return_value = False

        svc = make_service(queue_repo=queue_repo)

        result = await svc.leave_queue(player_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_find_match_player_removed_between_expansion_and_search(self) -> None:
        """Handles player removed between expansion and search."""
        player_id = make_player_id()
        entry_data = make_queue_entry_data(player_id=player_id)

        queue_repo = AsyncMock()
        # First call returns entry, second (after expansion) returns None
        queue_repo.get_player_queue_state.side_effect = [entry_data, None]

        svc = make_service(queue_repo=queue_repo)

        result = await svc.find_match(player_id)
        assert result.status == MatchmakingStatus.NOT_IN_QUEUE
