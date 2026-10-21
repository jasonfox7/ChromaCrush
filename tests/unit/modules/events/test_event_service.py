"""Comprehensive unit tests for EventService.

Tests all 15 public methods plus error paths and private helper behavior
(via public API): create_event, get_event, list_events, get_active_events,
join_event, leave_event, record_event_match, get_leaderboard,
get_player_rank, get_player_events, get_event_participant, finalize_event,
cancel_event, update_event, process_scheduled_events.

Uses pytest + pytest-asyncio with AsyncMock/MagicMock dependencies.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.core.errors import AppError
from src.core.types.game import EventId, MatchId, PlayerId
from src.modules.events.dto import (
    EventCreate,
    EventDbUpdate,
    EventMatchCreate,
    EventUpdate,
    PaginatedResult,
    ParticipantCreate,
    ParticipantUpdate,
)
from src.modules.events.service import EventService
from src.modules.events.types import (
    Event,
    EventFinalizationResult,
    EventLeaderboard,
    EventParticipant,
    EventStatus,
    EventSummary,
    EventType,
    LeaderboardEntry,
    MatchEventStats,
    PlayerEventRank,
    PlayerEventSummary,
    ScheduledEventResult,
    ScoringType,
)
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ============================================================================
# Helpers
# ============================================================================

NOW = datetime.now(timezone.utc)
HOUR_AGO = NOW - timedelta(hours=1)
HOUR_LATER = NOW + timedelta(hours=1)
DAY_AGO = NOW - timedelta(days=1)
DAY_LATER = NOW + timedelta(days=1)


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


def make_player_stats(total_matches: int = 50) -> MagicMock:
    """Create a mock PlayerStats-like object."""
    s = MagicMock()
    s.total_matches = total_matches
    return s


def make_energy_info(current_hearts: int = 5, max_hearts: int = 5) -> MagicMock:
    """Create a mock EnergyInfo-like object."""
    e = MagicMock()
    e.current_hearts = current_hearts
    e.max_hearts = max_hearts
    return e


def make_event_record(
    event_id: UUID | None = None,
    name: str = "Test Event",
    description: str = "A test event",
    event_type: str = "weekly",
    status: str = "active",
    scoring_type: str = "total_score",
    entry_requirements: dict | None = None,
    reward_tiers: list | None = None,
    rules: dict | None = None,
    max_participants: int | None = None,
    participant_count: int = 0,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    activated_at: datetime | None = None,
    finalized_at: datetime | None = None,
    cancelled_at: datetime | None = None,
    cancellation_reason: str | None = None,
    created_at: datetime | None = None,
    created_by: UUID | None = None,
) -> MagicMock:
    """Create a mock event ORM record."""
    record = MagicMock()
    record.id = event_id or uuid4()
    record.name = name
    record.description = description
    record.event_type = event_type
    record.status = status
    record.scoring_type = scoring_type
    record.entry_requirements = entry_requirements or {}
    record.reward_tiers = reward_tiers or []
    record.rules = rules or {}
    record.max_participants = max_participants
    record.participant_count = participant_count
    record.start_at = start_at or HOUR_AGO
    record.end_at = end_at or DAY_LATER
    record.activated_at = activated_at
    record.finalized_at = finalized_at
    record.cancelled_at = cancelled_at
    record.cancellation_reason = cancellation_reason
    record.created_at = created_at or HOUR_AGO
    record.created_by = created_by
    return record


def make_participant_record(
    event_id: UUID | None = None,
    player_id: UUID | None = None,
    joined_at: datetime | None = None,
    left_at: datetime | None = None,
    total_score: int = 0,
    matches_played: int = 0,
    best_match_score: int = 0,
    current_rank: int | None = None,
    rewards_claimed: bool = False,
    reward_tier: str | None = None,
    last_match_at: datetime | None = None,
) -> MagicMock:
    """Create a mock participant ORM record."""
    record = MagicMock()
    record.event_id = event_id or uuid4()
    record.player_id = player_id or uuid4()
    record.joined_at = joined_at or NOW
    record.left_at = left_at
    record.total_score = total_score
    record.matches_played = matches_played
    record.best_match_score = best_match_score
    record.current_rank = current_rank
    record.rewards_claimed = rewards_claimed
    record.reward_tier = reward_tier
    record.last_match_at = last_match_at
    record.updated_at = NOW
    return record


def make_match_event_stats(
    chain_count: int = 3,
    gems_cleared: int = 20,
    special_gems_activated: int = 1,
    match_duration_seconds: int = 120,
) -> MatchEventStats:
    """Create MatchEventStats for testing."""
    return MatchEventStats(
        chain_count=chain_count,
        gems_cleared=gems_cleared,
        special_gems_activated=special_gems_activated,
        match_duration_seconds=match_duration_seconds,
    )


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def mock_config() -> MockConfigService:
    return MockConfigService(
        {
            "events.flash_duration_hours": 4,
            "events.weekly_duration_days": 7,
            "events.seasonal_duration_days": 28,
            "events.entry_energy_cost": 0,
            "events.match_energy_cost": 1,
            "events.max_participants_flash": 10000,
            "events.max_participants_weekly": 50000,
            "events.max_participants_seasonal": 0,
            "events.leaderboard_cache_ttl_seconds": 30,
            "events.auto_finalize_delay_minutes": 15,
            "events.min_matches_for_rewards": 3,
            "events.allow_leave_after_match": False,
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
    ctx = MagicMock()
    ctx.redis = AsyncMock()
    return ctx


@pytest.fixture()
def mock_vault_service() -> AsyncMock:
    svc = AsyncMock()
    svc.add_artifact.return_value = MagicMock()
    return svc


@pytest.fixture()
def mock_energy_service() -> AsyncMock:
    svc = AsyncMock()
    svc.get_energy.return_value = make_energy_info(5, 5)
    svc.consume_heart.return_value = MagicMock()
    svc.grant_bonus_hearts.return_value = MagicMock()
    svc.refund_heart.return_value = MagicMock()
    return svc


@pytest.fixture()
def mock_match_service() -> AsyncMock:
    svc = AsyncMock()
    svc.get_match.return_value = MagicMock()
    return svc


@pytest.fixture()
def mock_player_service() -> AsyncMock:
    svc = AsyncMock()
    svc.get_player.side_effect = lambda pid: make_player(pid, f"user_{str(pid)[:8]}")
    svc.get_stats.return_value = make_player_stats(50)
    svc.get_elo.return_value = 1200
    svc.update_elo.return_value = MagicMock()
    return svc


@pytest.fixture()
def mock_event_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.create.return_value = make_event_record()
    repo.find_by_id.return_value = None
    repo.update.return_value = make_event_record()
    repo.find_by_status.return_value = ([], 0)
    repo.find_active.return_value = []
    repo.find_scheduled_to_start.return_value = []
    repo.find_active_to_end.return_value = []
    repo.find_ended_to_finalize.return_value = []
    repo.increment_participant_count.return_value = 1
    repo.decrement_participant_count.return_value = 0
    return repo


@pytest.fixture()
def mock_participant_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.create.return_value = make_participant_record()
    repo.find_by_event_and_player.return_value = None
    repo.update.return_value = make_participant_record()
    repo.find_by_event.return_value = ([], 0)
    repo.find_by_player.return_value = ([], 0)
    repo.find_ranked_by_event.return_value = []
    repo.count_by_event.return_value = 0
    repo.bulk_update_ranks.return_value = 0
    repo.find_eligible_for_rewards.return_value = []
    repo.create_event_match.return_value = MagicMock()
    return repo


@pytest.fixture()
def mock_leaderboard_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.update_score.return_value = None
    repo.get_rank.return_value = 1
    repo.get_score.return_value = 100
    repo.get_top.return_value = []
    repo.get_total_count.return_value = 0
    repo.get_percentile.return_value = 99.0
    repo.remove_player.return_value = None
    repo.clear_leaderboard.return_value = None
    repo.sync_to_database.return_value = 0
    return repo


@pytest.fixture()
def event_service(
    mock_config: MockConfigService,
    mock_logger: MockLogService,
    mock_errors: MockErrorService,
    mock_data_ctx: MagicMock,
    mock_vault_service: AsyncMock,
    mock_energy_service: AsyncMock,
    mock_match_service: AsyncMock,
    mock_player_service: AsyncMock,
    mock_event_repo: AsyncMock,
    mock_participant_repo: AsyncMock,
    mock_leaderboard_repo: AsyncMock,
) -> EventService:
    return EventService(
        config=mock_config,
        logger=mock_logger,
        errors=mock_errors,
        data_ctx=mock_data_ctx,
        vault_service=mock_vault_service,
        energy_service=mock_energy_service,
        match_service=mock_match_service,
        player_service=mock_player_service,
        event_repository=mock_event_repo,
        event_participant_repository=mock_participant_repo,
        event_leaderboard_repository=mock_leaderboard_repo,
    )


# ============================================================================
# create_event tests
# ============================================================================


class TestCreateEvent:
    """Tests for EventService.create_event."""

    @pytest.mark.asyncio
    async def test_create_event_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Happy path: create event returns Event domain object."""
        data = EventCreate(
            name="Weekly Showdown",
            description="A weekly event",
            event_type="weekly",
            scoring_type="total_score",
            start_at=HOUR_LATER,
            end_at=DAY_LATER,
            entry_requirements={},
            reward_tiers=[],
            rules={},
        )
        record = make_event_record(name="Weekly Showdown")
        mock_event_repo.create.return_value = record

        result = await event_service.create_event(data)

        assert isinstance(result, Event)
        assert result.name == "Weekly Showdown"
        mock_event_repo.create.assert_awaited_once_with(data)

    @pytest.mark.asyncio
    async def test_create_event_name_too_short(
        self,
        event_service: EventService,
    ) -> None:
        """Event name < 3 chars raises VALIDATION_INVALID_INPUT."""
        data = EventCreate(
            name="AB",
            description="desc",
            event_type="weekly",
            scoring_type="total_score",
            start_at=HOUR_LATER,
            end_at=DAY_LATER,
            entry_requirements={},
            reward_tiers=[],
            rules={},
        )

        with pytest.raises(AppError) as exc_info:
            await event_service.create_event(data)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_create_event_name_too_long(
        self,
        event_service: EventService,
    ) -> None:
        """Event name > 100 chars raises VALIDATION_INVALID_INPUT."""
        data = EventCreate(
            name="A" * 101,
            description="desc",
            event_type="weekly",
            scoring_type="total_score",
            start_at=HOUR_LATER,
            end_at=DAY_LATER,
            entry_requirements={},
            reward_tiers=[],
            rules={},
        )

        with pytest.raises(AppError) as exc_info:
            await event_service.create_event(data)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_create_event_end_before_start(
        self,
        event_service: EventService,
    ) -> None:
        """end_at before start_at raises VALIDATION_INVALID_INPUT."""
        data = EventCreate(
            name="Bad Event",
            description="desc",
            event_type="weekly",
            scoring_type="total_score",
            start_at=DAY_LATER,
            end_at=HOUR_LATER,
            entry_requirements={},
            reward_tiers=[],
            rules={},
        )

        with pytest.raises(AppError) as exc_info:
            await event_service.create_event(data)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_create_event_empty_name(
        self,
        event_service: EventService,
    ) -> None:
        """Empty event name raises VALIDATION_INVALID_INPUT."""
        data = EventCreate(
            name="",
            description="desc",
            event_type="weekly",
            scoring_type="total_score",
            start_at=HOUR_LATER,
            end_at=DAY_LATER,
            entry_requirements={},
            reward_tiers=[],
            rules={},
        )

        with pytest.raises(AppError) as exc_info:
            await event_service.create_event(data)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ============================================================================
# get_event tests
# ============================================================================


class TestGetEvent:
    """Tests for EventService.get_event."""

    @pytest.mark.asyncio
    async def test_get_event_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Happy path: returns Event domain object."""
        eid = uuid4()
        record = make_event_record(event_id=eid, name="My Event")
        mock_event_repo.find_by_id.return_value = record

        result = await event_service.get_event(EventId(eid))

        assert isinstance(result, Event)
        assert result.name == "My Event"

    @pytest.mark.asyncio
    async def test_get_event_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Non-existent event raises NOT_FOUND_EVENT."""
        mock_event_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.get_event(EventId(uuid4()))
        assert exc_info.value.code == "NOT_FOUND_EVENT"


# ============================================================================
# list_events tests
# ============================================================================


class TestListEvents:
    """Tests for EventService.list_events."""

    @pytest.mark.asyncio
    async def test_list_events_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Happy path: returns PaginatedResult of EventSummary."""
        record = make_event_record()
        mock_event_repo.find_by_status.return_value = ([record], 1)

        result = await event_service.list_events()

        assert isinstance(result, PaginatedResult)
        assert len(result.items) == 1
        assert isinstance(result.items[0], EventSummary)
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_events_empty(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """No events returns empty PaginatedResult."""
        mock_event_repo.find_by_status.return_value = ([], 0)

        result = await event_service.list_events()

        assert result.items == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_events_invalid_limit_low(
        self,
        event_service: EventService,
    ) -> None:
        """limit < 1 raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            await event_service.list_events(limit=0)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_list_events_invalid_limit_high(
        self,
        event_service: EventService,
    ) -> None:
        """limit > 100 raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            await event_service.list_events(limit=101)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_list_events_with_status_filter(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Status filter is passed correctly to repo."""
        mock_event_repo.find_by_status.return_value = ([], 0)

        await event_service.list_events(status=EventStatus.ACTIVE)

        call_kwargs = mock_event_repo.find_by_status.call_args
        assert call_kwargs[1]["status"] == "active"

    @pytest.mark.asyncio
    async def test_list_events_with_type_filter(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Event type filter is passed correctly to repo."""
        mock_event_repo.find_by_status.return_value = ([], 0)

        await event_service.list_events(event_type=EventType.FLASH)

        call_kwargs = mock_event_repo.find_by_status.call_args
        assert call_kwargs[1]["event_type"] == "flash"


# ============================================================================
# get_active_events tests
# ============================================================================


class TestGetActiveEvents:
    """Tests for EventService.get_active_events."""

    @pytest.mark.asyncio
    async def test_get_active_events_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Returns list of Event domain objects for active events."""
        record = make_event_record(status="active")
        mock_event_repo.find_active.return_value = [record]

        result = await event_service.get_active_events()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Event)

    @pytest.mark.asyncio
    async def test_get_active_events_empty(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """No active events returns empty list."""
        mock_event_repo.find_active.return_value = []

        result = await event_service.get_active_events()

        assert result == []


# ============================================================================
# join_event tests
# ============================================================================


class TestJoinEvent:
    """Tests for EventService.join_event."""

    @pytest.mark.asyncio
    async def test_join_event_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Happy path: player joins active event."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(event_id=eid, status="active")
        mock_event_repo.find_by_id.return_value = event_record

        participant_record = make_participant_record(
            event_id=eid, player_id=UUID(str(pid))
        )
        mock_participant_repo.create.return_value = participant_record

        result = await event_service.join_event(EventId(eid), pid)

        assert isinstance(result, EventParticipant)
        mock_participant_repo.create.assert_awaited_once()
        mock_leaderboard_repo.update_score.assert_awaited_once()
        mock_event_repo.increment_participant_count.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_join_event_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Non-existent event raises NOT_FOUND_EVENT."""
        mock_event_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.join_event(EventId(uuid4()), PlayerId(uuid4()))
        assert exc_info.value.code == "NOT_FOUND_EVENT"

    @pytest.mark.asyncio
    async def test_join_event_not_active(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Joining a non-active event raises CONFLICT_EVENT_NOT_ACTIVE."""
        record = make_event_record(status="scheduled")
        mock_event_repo.find_by_id.return_value = record

        with pytest.raises(AppError) as exc_info:
            await event_service.join_event(EventId(record.id), PlayerId(uuid4()))
        assert exc_info.value.code == "CONFLICT_EVENT_NOT_ACTIVE"

    @pytest.mark.asyncio
    async def test_join_event_already_participant(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
    ) -> None:
        """Already participating raises CONFLICT_ALREADY_PARTICIPANT."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(event_id=eid, status="active")
        mock_event_repo.find_by_id.return_value = event_record

        existing = make_participant_record(
            event_id=eid, player_id=UUID(str(pid)), left_at=None
        )
        mock_participant_repo.find_by_event_and_player.return_value = existing

        with pytest.raises(AppError) as exc_info:
            await event_service.join_event(EventId(eid), pid)
        assert exc_info.value.code == "CONFLICT_ALREADY_PARTICIPANT"

    @pytest.mark.asyncio
    async def test_join_event_at_capacity(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
    ) -> None:
        """Joining a full event raises CONFLICT_EVENT_AT_CAPACITY."""
        eid = uuid4()
        event_record = make_event_record(
            event_id=eid,
            status="active",
            max_participants=10,
            participant_count=10,
        )
        mock_event_repo.find_by_id.return_value = event_record

        with pytest.raises(AppError) as exc_info:
            await event_service.join_event(EventId(eid), PlayerId(uuid4()))
        assert exc_info.value.code == "CONFLICT_EVENT_AT_CAPACITY"

    @pytest.mark.asyncio
    async def test_join_event_race_condition_rollback(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_energy_service: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """When atomic increment overshoots capacity, rollback occurs."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            max_participants=5,
            participant_count=4,
        )
        mock_event_repo.find_by_id.return_value = event_record
        # Simulates race: increment returns 6 which exceeds max of 5
        mock_event_repo.increment_participant_count.return_value = 6

        with pytest.raises(AppError) as exc_info:
            await event_service.join_event(EventId(eid), pid)
        assert exc_info.value.code == "CONFLICT_EVENT_AT_CAPACITY"
        mock_event_repo.decrement_participant_count.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_join_event_with_energy_cost(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_energy_service: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Entry energy cost is consumed on join."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            entry_requirements={"energy_cost": 2},
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant_record = make_participant_record(
            event_id=eid, player_id=UUID(str(pid))
        )
        mock_participant_repo.create.return_value = participant_record

        await event_service.join_event(EventId(eid), pid)

        mock_energy_service.consume_heart.assert_awaited_once_with(pid, amount=2)

    @pytest.mark.asyncio
    async def test_join_event_insufficient_energy(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_energy_service: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Insufficient energy for entry raises FORBIDDEN_INSUFFICIENT_ENERGY."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            entry_requirements={"energy_cost": 3},
        )
        mock_event_repo.find_by_id.return_value = event_record
        mock_energy_service.get_energy.return_value = make_energy_info(current_hearts=1)

        with pytest.raises(AppError) as exc_info:
            await event_service.join_event(EventId(eid), pid)
        assert exc_info.value.code == "FORBIDDEN_INSUFFICIENT_ENERGY"

    @pytest.mark.asyncio
    async def test_join_event_min_elo_requirement(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Player below min_elo raises FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            entry_requirements={"min_elo": 1500},
        )
        mock_event_repo.find_by_id.return_value = event_record
        # Default mock player has elo_rating=1200 which is < 1500
        mock_player_service.get_player.return_value = make_player(pid, "low_elo")

        with pytest.raises(AppError) as exc_info:
            await event_service.join_event(EventId(eid), pid)
        assert exc_info.value.code == "FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET"

    @pytest.mark.asyncio
    async def test_join_event_max_elo_requirement(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Player above max_elo raises FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            entry_requirements={"max_elo": 1000},
        )
        mock_event_repo.find_by_id.return_value = event_record
        # Default mock player has elo_rating=1200 which is > 1000
        mock_player_service.get_player.return_value = make_player(pid, "high_elo")

        with pytest.raises(AppError) as exc_info:
            await event_service.join_event(EventId(eid), pid)
        assert exc_info.value.code == "FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET"


# ============================================================================
# leave_event tests
# ============================================================================


class TestLeaveEvent:
    """Tests for EventService.leave_event."""

    @pytest.mark.asyncio
    async def test_leave_event_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
    ) -> None:
        """Happy path: player leaves event."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(event_id=eid)
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            matches_played=0,
            left_at=None,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant

        await event_service.leave_event(EventId(eid), pid)

        mock_participant_repo.update.assert_awaited_once()
        mock_event_repo.decrement_participant_count.assert_awaited_once()
        mock_leaderboard_repo.remove_player.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_leave_event_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Non-existent event raises NOT_FOUND_EVENT."""
        mock_event_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.leave_event(EventId(uuid4()), PlayerId(uuid4()))
        assert exc_info.value.code == "NOT_FOUND_EVENT"

    @pytest.mark.asyncio
    async def test_leave_event_not_participant(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
    ) -> None:
        """Non-participant raises FORBIDDEN_NOT_EVENT_PARTICIPANT."""
        record = make_event_record()
        mock_event_repo.find_by_id.return_value = record
        mock_participant_repo.find_by_event_and_player.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.leave_event(EventId(record.id), PlayerId(uuid4()))
        assert exc_info.value.code == "FORBIDDEN_NOT_EVENT_PARTICIPANT"

    @pytest.mark.asyncio
    async def test_leave_event_already_left(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
    ) -> None:
        """Player who already left raises FORBIDDEN_NOT_EVENT_PARTICIPANT."""
        eid = uuid4()
        record = make_event_record(event_id=eid)
        mock_event_repo.find_by_id.return_value = record

        participant = make_participant_record(event_id=eid, left_at=NOW)
        mock_participant_repo.find_by_event_and_player.return_value = participant

        with pytest.raises(AppError) as exc_info:
            await event_service.leave_event(EventId(eid), PlayerId(uuid4()))
        assert exc_info.value.code == "FORBIDDEN_NOT_EVENT_PARTICIPANT"

    @pytest.mark.asyncio
    async def test_leave_event_after_match_forbidden(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
    ) -> None:
        """Player with matches_played > 0 and allow_leave_after_match=False."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        record = make_event_record(event_id=eid)
        mock_event_repo.find_by_id.return_value = record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            matches_played=3,
            left_at=None,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant

        with pytest.raises(AppError) as exc_info:
            await event_service.leave_event(EventId(eid), pid)
        assert exc_info.value.code == "FORBIDDEN_CANNOT_LEAVE_EVENT"

    @pytest.mark.asyncio
    async def test_leave_event_after_match_allowed_with_config(
        self,
        mock_logger: MockLogService,
        mock_errors: MockErrorService,
        mock_data_ctx: MagicMock,
        mock_vault_service: AsyncMock,
        mock_energy_service: AsyncMock,
        mock_match_service: AsyncMock,
        mock_player_service: AsyncMock,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
    ) -> None:
        """Allow leave when config allow_leave_after_match=True."""
        config = MockConfigService(
            {
                "events.flash_duration_hours": 4,
                "events.weekly_duration_days": 7,
                "events.seasonal_duration_days": 28,
                "events.entry_energy_cost": 0,
                "events.match_energy_cost": 1,
                "events.max_participants_flash": 10000,
                "events.max_participants_weekly": 50000,
                "events.max_participants_seasonal": 0,
                "events.leaderboard_cache_ttl_seconds": 30,
                "events.auto_finalize_delay_minutes": 15,
                "events.min_matches_for_rewards": 3,
                "events.allow_leave_after_match": True,
            }
        )
        svc = EventService(
            config=config,
            logger=mock_logger,
            errors=mock_errors,
            data_ctx=mock_data_ctx,
            vault_service=mock_vault_service,
            energy_service=mock_energy_service,
            match_service=mock_match_service,
            player_service=mock_player_service,
            event_repository=mock_event_repo,
            event_participant_repository=mock_participant_repo,
            event_leaderboard_repository=mock_leaderboard_repo,
        )

        eid = uuid4()
        pid = PlayerId(uuid4())
        record = make_event_record(event_id=eid)
        mock_event_repo.find_by_id.return_value = record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            matches_played=5,
            left_at=None,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant

        # Should not raise
        await svc.leave_event(EventId(eid), pid)

        mock_participant_repo.update.assert_awaited_once()


# ============================================================================
# record_event_match tests
# ============================================================================


class TestRecordEventMatch:
    """Tests for EventService.record_event_match."""

    @pytest.mark.asyncio
    async def test_record_match_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Happy path: record a match for an active event."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        mid = MatchId(uuid4())

        event_record = make_event_record(event_id=eid, status="active")
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=100,
            matches_played=2,
            best_match_score=80,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant

        updated_participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=250,
            matches_played=3,
            best_match_score=150,
        )
        mock_participant_repo.update.return_value = updated_participant

        stats = make_match_event_stats(chain_count=3, gems_cleared=20)
        result = await event_service.record_event_match(
            EventId(eid),
            pid,
            mid,
            score=150,
            match_stats=stats,
        )

        assert isinstance(result, EventParticipant)
        mock_participant_repo.create_event_match.assert_awaited_once()
        mock_leaderboard_repo.update_score.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_match_event_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Non-existent event raises NOT_FOUND_EVENT."""
        mock_event_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.record_event_match(
                EventId(uuid4()),
                PlayerId(uuid4()),
                MatchId(uuid4()),
                score=100,
                match_stats=make_match_event_stats(),
            )
        assert exc_info.value.code == "NOT_FOUND_EVENT"

    @pytest.mark.asyncio
    async def test_record_match_event_not_active(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Recording on non-active event raises CONFLICT_EVENT_NOT_ACTIVE."""
        record = make_event_record(status="ended")
        mock_event_repo.find_by_id.return_value = record

        with pytest.raises(AppError) as exc_info:
            await event_service.record_event_match(
                EventId(record.id),
                PlayerId(uuid4()),
                MatchId(uuid4()),
                score=100,
                match_stats=make_match_event_stats(),
            )
        assert exc_info.value.code == "CONFLICT_EVENT_NOT_ACTIVE"

    @pytest.mark.asyncio
    async def test_record_match_not_participant(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
    ) -> None:
        """Non-participant raises FORBIDDEN_NOT_EVENT_PARTICIPANT."""
        record = make_event_record(status="active")
        mock_event_repo.find_by_id.return_value = record
        mock_participant_repo.find_by_event_and_player.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.record_event_match(
                EventId(record.id),
                PlayerId(uuid4()),
                MatchId(uuid4()),
                score=100,
                match_stats=make_match_event_stats(),
            )
        assert exc_info.value.code == "FORBIDDEN_NOT_EVENT_PARTICIPANT"

    @pytest.mark.asyncio
    async def test_record_match_max_matches_reached(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
    ) -> None:
        """Exceeding max matches per player raises CONFLICT_EVENT_NOT_ACTIVE."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            rules={"max_matches_per_player": 5},
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            matches_played=5,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant

        with pytest.raises(AppError) as exc_info:
            await event_service.record_event_match(
                EventId(eid),
                pid,
                MatchId(uuid4()),
                score=100,
                match_stats=make_match_event_stats(),
            )
        assert exc_info.value.code == "CONFLICT_EVENT_NOT_ACTIVE"

    @pytest.mark.asyncio
    async def test_record_match_scoring_multiplier(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Scoring multiplier is applied to match score."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            rules={"scoring_multiplier": 2.0},
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=0,
            matches_played=0,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant
        mock_participant_repo.update.return_value = participant

        stats = make_match_event_stats()
        await event_service.record_event_match(
            EventId(eid),
            pid,
            MatchId(uuid4()),
            score=100,
            match_stats=stats,
        )

        # Score should be 100 * 2.0 = 200
        create_call = mock_participant_repo.create_event_match.call_args
        match_create = create_call[0][0]
        assert match_create.score == 200

    @pytest.mark.asyncio
    async def test_record_match_bonus_condition_met(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Bonus points are added when condition is met."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            rules={
                "scoring_multiplier": 1.0,
                "bonus_conditions": [
                    {
                        "condition_type": "chain_length",
                        "threshold": 5,
                        "bonus_points": 50,
                    },
                ],
            },
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=0,
            matches_played=0,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant
        mock_participant_repo.update.return_value = participant

        # chain_count=7 >= threshold=5, so bonus applies
        stats = make_match_event_stats(chain_count=7)
        await event_service.record_event_match(
            EventId(eid),
            pid,
            MatchId(uuid4()),
            score=100,
            match_stats=stats,
        )

        # Score = 100 * 1.0 + 50 bonus = 150
        create_call = mock_participant_repo.create_event_match.call_args
        assert create_call[0][0].score == 150

    @pytest.mark.asyncio
    async def test_record_match_bonus_condition_not_met(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Bonus points NOT added when condition is not met."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            rules={
                "scoring_multiplier": 1.0,
                "bonus_conditions": [
                    {
                        "condition_type": "chain_length",
                        "threshold": 10,
                        "bonus_points": 50,
                    },
                ],
            },
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=0,
            matches_played=0,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant
        mock_participant_repo.update.return_value = participant

        # chain_count=3 < threshold=10, no bonus
        stats = make_match_event_stats(chain_count=3)
        await event_service.record_event_match(
            EventId(eid),
            pid,
            MatchId(uuid4()),
            score=100,
            match_stats=stats,
        )

        create_call = mock_participant_repo.create_event_match.call_args
        assert create_call[0][0].score == 100  # No bonus

    @pytest.mark.asyncio
    async def test_record_match_best_match_scoring(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """BEST_MATCH scoring uses max(current, new)."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            scoring_type="best_match",
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=200,
            matches_played=3,  # Best was 200
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant
        mock_participant_repo.update.return_value = participant

        stats = make_match_event_stats()
        # New score is 150, which is less than current 200
        await event_service.record_event_match(
            EventId(eid),
            pid,
            MatchId(uuid4()),
            score=150,
            match_stats=stats,
        )

        update_call = mock_participant_repo.update.call_args
        update_dto = update_call[0][2]
        # Best of 200 and 150 = 200 (stays the same)
        assert update_dto.total_score == 200

    @pytest.mark.asyncio
    async def test_record_match_matches_played_scoring(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """MATCHES_PLAYED scoring increments match count."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            scoring_type="matches_played",
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=5,
            matches_played=5,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant
        mock_participant_repo.update.return_value = participant

        stats = make_match_event_stats()
        await event_service.record_event_match(
            EventId(eid),
            pid,
            MatchId(uuid4()),
            score=999,
            match_stats=stats,
        )

        update_call = mock_participant_repo.update.call_args
        update_dto = update_call[0][2]
        # MATCHES_PLAYED: total = matches_played + 1 = 6
        assert update_dto.total_score == 6


# ============================================================================
# get_leaderboard tests
# ============================================================================


class TestGetLeaderboard:
    """Tests for EventService.get_leaderboard."""

    @pytest.mark.asyncio
    async def test_get_leaderboard_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Happy path: returns EventLeaderboard with entries from Redis."""
        eid = uuid4()
        pid_str = str(uuid4())
        event_record = make_event_record(event_id=eid, participant_count=5)
        mock_event_repo.find_by_id.return_value = event_record

        mock_leaderboard_repo.get_top.return_value = [(pid_str, 500)]
        mock_leaderboard_repo.get_total_count.return_value = 5
        mock_leaderboard_repo.get_rank.return_value = 1

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(pid_str),
            matches_played=3,
            best_match_score=200,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant

        result = await event_service.get_leaderboard(EventId(eid))

        assert isinstance(result, EventLeaderboard)
        assert len(result.entries) == 1
        assert result.entries[0].score == 500
        assert result.total_participants == 5

    @pytest.mark.asyncio
    async def test_get_leaderboard_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Non-existent event raises NOT_FOUND_EVENT."""
        mock_event_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.get_leaderboard(EventId(uuid4()))
        assert exc_info.value.code == "NOT_FOUND_EVENT"

    @pytest.mark.asyncio
    async def test_get_leaderboard_invalid_limit(
        self,
        event_service: EventService,
    ) -> None:
        """limit > 500 raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            await event_service.get_leaderboard(EventId(uuid4()), limit=501)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_get_leaderboard_fallback_to_db(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Falls back to DB when Redis is empty but participants exist."""
        eid = uuid4()
        pid = uuid4()
        event_record = make_event_record(event_id=eid, participant_count=3)
        mock_event_repo.find_by_id.return_value = event_record

        # Redis returns empty
        mock_leaderboard_repo.get_top.return_value = []
        mock_leaderboard_repo.get_total_count.return_value = 0

        # DB fallback
        db_participant = make_participant_record(
            event_id=eid,
            player_id=pid,
            total_score=300,
            matches_played=5,
            best_match_score=100,
        )
        mock_participant_repo.find_ranked_by_event.return_value = [db_participant]

        result = await event_service.get_leaderboard(EventId(eid))

        assert isinstance(result, EventLeaderboard)
        assert len(result.entries) == 1
        mock_participant_repo.find_ranked_by_event.assert_awaited_once()


# ============================================================================
# get_player_rank tests
# ============================================================================


class TestGetPlayerRank:
    """Tests for EventService.get_player_rank."""

    @pytest.mark.asyncio
    async def test_get_player_rank_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
    ) -> None:
        """Happy path: returns PlayerEventRank."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(event_id=eid)
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            matches_played=5,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant
        mock_leaderboard_repo.get_rank.return_value = 3
        mock_leaderboard_repo.get_total_count.return_value = 50
        mock_leaderboard_repo.get_percentile.return_value = 94.0
        mock_leaderboard_repo.get_score.return_value = 500

        result = await event_service.get_player_rank(EventId(eid), pid)

        assert isinstance(result, PlayerEventRank)
        assert result.rank == 3
        assert result.total_participants == 50
        assert result.percentile == 94.0
        assert result.score == 500

    @pytest.mark.asyncio
    async def test_get_player_rank_event_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Non-existent event raises NOT_FOUND_EVENT."""
        mock_event_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.get_player_rank(EventId(uuid4()), PlayerId(uuid4()))
        assert exc_info.value.code == "NOT_FOUND_EVENT"

    @pytest.mark.asyncio
    async def test_get_player_rank_not_participant(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
    ) -> None:
        """Non-participant raises FORBIDDEN_NOT_EVENT_PARTICIPANT."""
        record = make_event_record()
        mock_event_repo.find_by_id.return_value = record
        mock_participant_repo.find_by_event_and_player.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.get_player_rank(EventId(record.id), PlayerId(uuid4()))
        assert exc_info.value.code == "FORBIDDEN_NOT_EVENT_PARTICIPANT"


# ============================================================================
# get_player_events tests
# ============================================================================


class TestGetPlayerEvents:
    """Tests for EventService.get_player_events."""

    @pytest.mark.asyncio
    async def test_get_player_events_success(
        self,
        event_service: EventService,
        mock_participant_repo: AsyncMock,
        mock_event_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Returns PaginatedResult of PlayerEventSummary."""
        pid = PlayerId(uuid4())
        eid = uuid4()

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=300,
            matches_played=5,
            current_rank=2,
        )
        mock_participant_repo.find_by_player.return_value = ([participant], 1)

        event_record = make_event_record(event_id=eid, name="Weekly Challenge")
        mock_event_repo.find_by_id.return_value = event_record

        result = await event_service.get_player_events(pid)

        assert isinstance(result, PaginatedResult)
        assert len(result.items) == 1
        assert isinstance(result.items[0], PlayerEventSummary)
        assert result.items[0].event_name == "Weekly Challenge"

    @pytest.mark.asyncio
    async def test_get_player_events_empty(
        self,
        event_service: EventService,
        mock_participant_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """No events returns empty PaginatedResult."""
        mock_participant_repo.find_by_player.return_value = ([], 0)

        result = await event_service.get_player_events(PlayerId(uuid4()))

        assert result.items == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_get_player_events_invalid_limit(
        self,
        event_service: EventService,
    ) -> None:
        """limit > 100 raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            await event_service.get_player_events(PlayerId(uuid4()), limit=101)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ============================================================================
# get_event_participant tests
# ============================================================================


class TestGetEventParticipant:
    """Tests for EventService.get_event_participant."""

    @pytest.mark.asyncio
    async def test_get_event_participant_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Happy path: returns EventParticipant."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(event_id=eid)
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=500,
            matches_played=10,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant

        result = await event_service.get_event_participant(EventId(eid), pid)

        assert isinstance(result, EventParticipant)
        assert result.total_score == 500

    @pytest.mark.asyncio
    async def test_get_event_participant_event_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Non-existent event raises NOT_FOUND_EVENT."""
        mock_event_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.get_event_participant(
                EventId(uuid4()), PlayerId(uuid4())
            )
        assert exc_info.value.code == "NOT_FOUND_EVENT"

    @pytest.mark.asyncio
    async def test_get_event_participant_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
    ) -> None:
        """Non-participant raises FORBIDDEN_NOT_EVENT_PARTICIPANT."""
        record = make_event_record()
        mock_event_repo.find_by_id.return_value = record
        mock_participant_repo.find_by_event_and_player.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.get_event_participant(
                EventId(record.id), PlayerId(uuid4())
            )
        assert exc_info.value.code == "FORBIDDEN_NOT_EVENT_PARTICIPANT"


# ============================================================================
# finalize_event tests
# ============================================================================


class TestFinalizeEvent:
    """Tests for EventService.finalize_event."""

    @pytest.mark.asyncio
    async def test_finalize_event_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Happy path: finalize event distributes rewards."""
        eid = uuid4()
        pid = uuid4()
        event_record = make_event_record(
            event_id=eid,
            status="ended",
            reward_tiers=[
                {
                    "tier_id": "gold",
                    "name": "Gold",
                    "description": "Top tier",
                    "rank_min": 1,
                    "rank_max": 3,
                    "rewards": [
                        {"reward_type": "energy", "value": "5", "quantity": 1},
                    ],
                },
            ],
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=pid,
            current_rank=2,
            matches_played=5,
        )
        mock_participant_repo.find_eligible_for_rewards.return_value = [participant]
        mock_leaderboard_repo.get_top.return_value = [(str(pid), 500)]

        participant_detail = make_participant_record(
            event_id=eid,
            player_id=pid,
            matches_played=5,
            best_match_score=200,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant_detail

        result = await event_service.finalize_event(EventId(eid))

        assert isinstance(result, EventFinalizationResult)
        assert result.total_participants == 1
        assert result.rewards_distributed >= 1
        mock_event_repo.update.assert_awaited()

    @pytest.mark.asyncio
    async def test_finalize_event_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Non-existent event raises NOT_FOUND_EVENT."""
        mock_event_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.finalize_event(EventId(uuid4()))
        assert exc_info.value.code == "NOT_FOUND_EVENT"

    @pytest.mark.asyncio
    async def test_finalize_event_already_finalized(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Already finalized event raises CONFLICT_EVENT_ALREADY_FINALIZED."""
        record = make_event_record(status="finalized", finalized_at=NOW)
        mock_event_repo.find_by_id.return_value = record

        with pytest.raises(AppError) as exc_info:
            await event_service.finalize_event(EventId(record.id))
        assert exc_info.value.code == "CONFLICT_EVENT_ALREADY_FINALIZED"

    @pytest.mark.asyncio
    async def test_finalize_event_wrong_status(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Scheduled event cannot be finalized."""
        record = make_event_record(status="scheduled")
        mock_event_repo.find_by_id.return_value = record

        with pytest.raises(AppError) as exc_info:
            await event_service.finalize_event(EventId(record.id))
        assert exc_info.value.code == "CONFLICT_EVENT_NOT_ACTIVE"

    @pytest.mark.asyncio
    async def test_finalize_event_no_eligible(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
    ) -> None:
        """Finalize with no eligible participants distributes 0 rewards."""
        eid = uuid4()
        record = make_event_record(event_id=eid, status="ended")
        mock_event_repo.find_by_id.return_value = record
        mock_participant_repo.find_eligible_for_rewards.return_value = []
        mock_leaderboard_repo.get_top.return_value = []

        result = await event_service.finalize_event(EventId(eid))

        assert result.rewards_distributed == 0
        assert result.total_participants == 0

    @pytest.mark.asyncio
    async def test_finalize_event_artifact_reward(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_vault_service: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Artifact rewards call vault_service.add_artifact."""
        eid = uuid4()
        pid = uuid4()
        event_record = make_event_record(
            event_id=eid,
            status="ended",
            reward_tiers=[
                {
                    "tier_id": "gold",
                    "name": "Gold",
                    "description": "Top",
                    "rank_min": 1,
                    "rank_max": 5,
                    "rewards": [
                        {
                            "reward_type": "artifact",
                            "value": "rare_gem_001",
                            "quantity": 2,
                        },
                    ],
                },
            ],
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=pid,
            current_rank=1,
            matches_played=5,
        )
        mock_participant_repo.find_eligible_for_rewards.return_value = [participant]
        mock_leaderboard_repo.get_top.return_value = [(str(pid), 500)]
        mock_participant_repo.find_by_event_and_player.return_value = participant

        await event_service.finalize_event(EventId(eid))

        # Artifact with quantity=2 should call add_artifact twice
        assert mock_vault_service.add_artifact.await_count == 2

    @pytest.mark.asyncio
    async def test_finalize_event_elo_bonus_reward(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """ELO bonus reward calls player_service.update_elo."""
        eid = uuid4()
        pid = uuid4()
        event_record = make_event_record(
            event_id=eid,
            status="ended",
            reward_tiers=[
                {
                    "tier_id": "gold",
                    "name": "Gold",
                    "description": "Top",
                    "rank_min": 1,
                    "rank_max": 5,
                    "rewards": [
                        {"reward_type": "elo_bonus", "value": "50", "quantity": 1},
                    ],
                },
            ],
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=pid,
            current_rank=1,
            matches_played=5,
        )
        mock_participant_repo.find_eligible_for_rewards.return_value = [participant]
        mock_leaderboard_repo.get_top.return_value = [(str(pid), 500)]
        mock_participant_repo.find_by_event_and_player.return_value = participant

        await event_service.finalize_event(EventId(eid))

        # get_elo returns 1200, so update_elo should be called with 1250
        mock_player_service.update_elo.assert_awaited_once()
        call_args = mock_player_service.update_elo.call_args
        assert call_args[0][1] == 1250  # 1200 + 50


# ============================================================================
# cancel_event tests
# ============================================================================


class TestCancelEvent:
    """Tests for EventService.cancel_event."""

    @pytest.mark.asyncio
    async def test_cancel_event_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
    ) -> None:
        """Happy path: cancel event returns Event."""
        eid = uuid4()
        record = make_event_record(event_id=eid, status="active")
        mock_event_repo.find_by_id.return_value = record
        updated = make_event_record(event_id=eid, status="cancelled")
        mock_event_repo.update.return_value = updated

        result = await event_service.cancel_event(EventId(eid), "testing")

        assert isinstance(result, Event)
        mock_leaderboard_repo.clear_leaderboard.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_event_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Non-existent event raises NOT_FOUND_EVENT."""
        mock_event_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.cancel_event(EventId(uuid4()), "reason")
        assert exc_info.value.code == "NOT_FOUND_EVENT"

    @pytest.mark.asyncio
    async def test_cancel_event_already_finalized(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Finalized event cannot be cancelled."""
        record = make_event_record(status="finalized", finalized_at=NOW)
        mock_event_repo.find_by_id.return_value = record

        with pytest.raises(AppError) as exc_info:
            await event_service.cancel_event(EventId(record.id), "reason")
        assert exc_info.value.code == "CONFLICT_EVENT_ALREADY_FINALIZED"

    @pytest.mark.asyncio
    async def test_cancel_event_reason_too_long(
        self,
        event_service: EventService,
    ) -> None:
        """Reason > 500 chars raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            await event_service.cancel_event(EventId(uuid4()), "x" * 501)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_cancel_event_refunds_energy(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_energy_service: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
    ) -> None:
        """Cancel refunds entry energy cost to active participants."""
        eid = uuid4()
        pid = uuid4()
        record = make_event_record(
            event_id=eid,
            status="active",
            entry_requirements={"energy_cost": 2},
            participant_count=1,
        )
        mock_event_repo.find_by_id.return_value = record
        mock_event_repo.update.return_value = make_event_record(status="cancelled")

        participant = make_participant_record(event_id=eid, player_id=pid)
        mock_participant_repo.find_by_event.return_value = ([participant], 1)

        await event_service.cancel_event(EventId(eid), "bug found")

        mock_energy_service.refund_heart.assert_awaited_once()
        refund_call = mock_energy_service.refund_heart.call_args
        assert refund_call[1]["amount"] == 2
        assert refund_call[1]["reason"] == "event_cancelled"


# ============================================================================
# update_event tests
# ============================================================================


class TestUpdateEvent:
    """Tests for EventService.update_event."""

    @pytest.mark.asyncio
    async def test_update_event_success(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Happy path: update event returns modified Event."""
        eid = uuid4()
        record = make_event_record(event_id=eid, name="Original")
        mock_event_repo.find_by_id.return_value = record

        updated_record = make_event_record(event_id=eid, name="Updated")
        mock_event_repo.update.return_value = updated_record

        updates = EventUpdate(name="Updated")
        result = await event_service.update_event(EventId(eid), updates)

        assert isinstance(result, Event)
        assert result.name == "Updated"

    @pytest.mark.asyncio
    async def test_update_event_not_found(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Non-existent event raises NOT_FOUND_EVENT."""
        mock_event_repo.find_by_id.return_value = None

        with pytest.raises(AppError) as exc_info:
            await event_service.update_event(EventId(uuid4()), EventUpdate(name="X"))
        assert exc_info.value.code == "NOT_FOUND_EVENT"


# ============================================================================
# process_scheduled_events tests
# ============================================================================


class TestProcessScheduledEvents:
    """Tests for EventService.process_scheduled_events."""

    @pytest.mark.asyncio
    async def test_process_activates_scheduled(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_data_ctx: MagicMock,
    ) -> None:
        """Scheduled events that should start get activated."""
        eid = uuid4()
        event_record = make_event_record(event_id=eid, status="scheduled")
        mock_event_repo.find_scheduled_to_start.return_value = [event_record]
        mock_event_repo.find_active_to_end.return_value = []
        mock_event_repo.find_ended_to_finalize.return_value = []

        result = await event_service.process_scheduled_events()

        assert isinstance(result, ScheduledEventResult)
        assert len(result.activated) == 1
        assert result.activated[0] == EventId(eid)
        mock_data_ctx.redis.sadd.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_deactivates_active(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_data_ctx: MagicMock,
    ) -> None:
        """Active events past end_at get deactivated."""
        eid = uuid4()
        event_record = make_event_record(event_id=eid, status="active")
        mock_event_repo.find_scheduled_to_start.return_value = []
        mock_event_repo.find_active_to_end.return_value = [event_record]
        mock_event_repo.find_ended_to_finalize.return_value = []

        result = await event_service.process_scheduled_events()

        assert len(result.deactivated) == 1
        assert result.deactivated[0] == EventId(eid)
        mock_data_ctx.redis.srem.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_finalizes_ended(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
    ) -> None:
        """Ended events past finalization delay get auto-finalized."""
        eid = uuid4()
        event_record = make_event_record(event_id=eid, status="ended")
        mock_event_repo.find_scheduled_to_start.return_value = []
        mock_event_repo.find_active_to_end.return_value = []
        mock_event_repo.find_ended_to_finalize.return_value = [event_record]

        # finalize_event needs the record when called internally
        mock_event_repo.find_by_id.return_value = event_record
        mock_participant_repo.find_eligible_for_rewards.return_value = []
        mock_leaderboard_repo.get_top.return_value = []

        result = await event_service.process_scheduled_events()

        assert len(result.finalized) == 1
        assert result.finalized[0] == EventId(eid)

    @pytest.mark.asyncio
    async def test_process_no_events(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Nothing to process returns empty lists."""
        mock_event_repo.find_scheduled_to_start.return_value = []
        mock_event_repo.find_active_to_end.return_value = []
        mock_event_repo.find_ended_to_finalize.return_value = []

        result = await event_service.process_scheduled_events()

        assert result.activated == []
        assert result.deactivated == []
        assert result.finalized == []

    @pytest.mark.asyncio
    async def test_process_activation_error_handled(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_logger: MockLogService,
    ) -> None:
        """Error during activation is caught and logged, not raised."""
        eid = uuid4()
        event_record = make_event_record(event_id=eid, status="scheduled")
        mock_event_repo.find_scheduled_to_start.return_value = [event_record]
        mock_event_repo.find_active_to_end.return_value = []
        mock_event_repo.find_ended_to_finalize.return_value = []
        # Make update raise to simulate activation error
        mock_event_repo.update.side_effect = RuntimeError("DB down")

        result = await event_service.process_scheduled_events()

        # Should not raise, but activated should be empty
        assert result.activated == []
        mock_logger.assert_logged("ERROR", "Failed to activate event")


# ============================================================================
# Edge cases and helper behavior
# ============================================================================


class TestHelperBehavior:
    """Tests for private helper behavior via public API."""

    @pytest.mark.asyncio
    async def test_record_to_event_parses_jsonb_fields(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Event domain object parses JSONB fields into typed dataclasses."""
        eid = uuid4()
        record = make_event_record(
            event_id=eid,
            entry_requirements={"min_elo": 1000, "energy_cost": 2},
            reward_tiers=[
                {
                    "tier_id": "gold",
                    "name": "Gold",
                    "description": "Top",
                    "rank_min": 1,
                    "rank_max": 3,
                    "rewards": [{"reward_type": "energy", "value": "5", "quantity": 1}],
                },
            ],
            rules={"max_matches_per_player": 10, "scoring_multiplier": 1.5},
        )
        mock_event_repo.find_by_id.return_value = record

        result = await event_service.get_event(EventId(eid))

        assert result.entry_requirements.min_elo == 1000
        assert result.entry_requirements.energy_cost == 2
        assert len(result.reward_tiers) == 1
        assert result.reward_tiers[0].tier_id == "gold"
        assert len(result.reward_tiers[0].rewards) == 1
        assert result.rules.max_matches_per_player == 10
        assert result.rules.scoring_multiplier == 1.5

    @pytest.mark.asyncio
    async def test_event_summary_time_remaining(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Active event summary includes time_remaining_seconds."""
        far_future = datetime.now(timezone.utc) + timedelta(hours=5)
        record = make_event_record(status="active", end_at=far_future)
        mock_event_repo.find_by_status.return_value = ([record], 1)

        result = await event_service.list_events()

        assert result.items[0].time_remaining_seconds is not None
        assert result.items[0].time_remaining_seconds > 0

    @pytest.mark.asyncio
    async def test_event_summary_no_time_remaining_for_scheduled(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
    ) -> None:
        """Scheduled event summary has time_remaining_seconds=None."""
        record = make_event_record(status="scheduled")
        mock_event_repo.find_by_status.return_value = ([record], 1)

        result = await event_service.list_events()

        assert result.items[0].time_remaining_seconds is None

    @pytest.mark.asyncio
    async def test_calculate_level_from_stats(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Player level calculation from total_matches: <5 -> lvl 1."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            entry_requirements={"min_level": 2},
        )
        mock_event_repo.find_by_id.return_value = event_record

        # 3 total matches -> level 1, which is < min_level 2
        mock_player_service.get_stats.return_value = make_player_stats(3)

        with pytest.raises(AppError) as exc_info:
            await event_service.join_event(EventId(eid), pid)
        assert exc_info.value.code == "FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET"

    @pytest.mark.asyncio
    async def test_participant_average_score_calculation(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """EventParticipant.average_score is correctly computed."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(event_id=eid)
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=300,
            matches_played=6,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant

        result = await event_service.get_event_participant(EventId(eid), pid)

        assert result.average_score == 50.0  # 300 / 6

    @pytest.mark.asyncio
    async def test_participant_zero_matches_average_score(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """EventParticipant with 0 matches has average_score=0.0."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(event_id=eid)
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=0,
            matches_played=0,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant

        result = await event_service.get_event_participant(EventId(eid), pid)

        assert result.average_score == 0.0

    @pytest.mark.asyncio
    async def test_special_gems_bonus_condition(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Bonus for special_gems condition type works correctly."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            rules={
                "scoring_multiplier": 1.0,
                "bonus_conditions": [
                    {
                        "condition_type": "special_gems",
                        "threshold": 3,
                        "bonus_points": 25,
                    },
                ],
            },
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=0,
            matches_played=0,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant
        mock_participant_repo.update.return_value = participant

        # special_gems_activated=5 >= threshold=3
        stats = make_match_event_stats(special_gems_activated=5)
        await event_service.record_event_match(
            EventId(eid),
            pid,
            MatchId(uuid4()),
            score=100,
            match_stats=stats,
        )

        create_call = mock_participant_repo.create_event_match.call_args
        assert create_call[0][0].score == 125  # 100 + 25 bonus

    @pytest.mark.asyncio
    async def test_time_bonus_condition(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Bonus for time_bonus condition type works correctly."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            rules={
                "scoring_multiplier": 1.0,
                "bonus_conditions": [
                    {
                        "condition_type": "time_bonus",
                        "threshold": 60,
                        "bonus_points": 100,
                    },
                ],
            },
        )
        mock_event_repo.find_by_id.return_value = event_record

        participant = make_participant_record(
            event_id=eid,
            player_id=UUID(str(pid)),
            total_score=0,
            matches_played=0,
        )
        mock_participant_repo.find_by_event_and_player.return_value = participant
        mock_participant_repo.update.return_value = participant

        # match_duration_seconds=45 <= threshold=60 -> bonus
        stats = make_match_event_stats(match_duration_seconds=45)
        await event_service.record_event_match(
            EventId(eid),
            pid,
            MatchId(uuid4()),
            score=100,
            match_stats=stats,
        )

        create_call = mock_participant_repo.create_event_match.call_args
        assert create_call[0][0].score == 200  # 100 + 100 bonus

    @pytest.mark.asyncio
    async def test_determine_reward_tier_by_percentile(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Finalization assigns correct tier by percentile range."""
        eid = uuid4()
        pid = uuid4()
        event_record = make_event_record(
            event_id=eid,
            status="ended",
            reward_tiers=[
                {
                    "tier_id": "top_10_percent",
                    "name": "Elite",
                    "description": "Top 10%",
                    "percentile_min": 90.0,
                    "percentile_max": 100.0,
                    "rewards": [
                        {"reward_type": "energy", "value": "10", "quantity": 1},
                    ],
                },
            ],
        )
        mock_event_repo.find_by_id.return_value = event_record

        # rank=1 out of 10 -> percentile = (10-1+1)/10*100 = 100%
        participant = make_participant_record(
            event_id=eid,
            player_id=pid,
            current_rank=1,
            matches_played=5,
        )
        mock_participant_repo.find_eligible_for_rewards.return_value = [participant]
        mock_leaderboard_repo.get_top.return_value = [(str(pid), 500)]
        mock_participant_repo.find_by_event_and_player.return_value = participant

        result = await event_service.finalize_event(EventId(eid))

        # Participant at rank 1/1 eligible -> percentile 100 -> in 90-100 range
        assert result.rewards_distributed >= 1
        assert "top_10_percent" in result.reward_summary

    @pytest.mark.asyncio
    async def test_player_type_requirement_filter(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_participant_repo: AsyncMock,
        mock_player_service: AsyncMock,
    ) -> None:
        """Player type requirement enforces player_types list."""
        eid = uuid4()
        pid = PlayerId(uuid4())
        event_record = make_event_record(
            event_id=eid,
            status="active",
            entry_requirements={"player_types": ["bot"]},
        )
        mock_event_repo.find_by_id.return_value = event_record
        # Default mock player has player_type="human" which is not in ["bot"]

        with pytest.raises(AppError) as exc_info:
            await event_service.join_event(EventId(eid), pid)
        assert exc_info.value.code == "FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET"

    @pytest.mark.asyncio
    async def test_logging_on_create_event(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_logger: MockLogService,
    ) -> None:
        """Creating an event logs at INFO level."""
        data = EventCreate(
            name="Log Test",
            description="desc",
            event_type="weekly",
            scoring_type="total_score",
            start_at=HOUR_LATER,
            end_at=DAY_LATER,
            entry_requirements={},
            reward_tiers=[],
            rules={},
        )
        mock_event_repo.create.return_value = make_event_record(name="Log Test")

        await event_service.create_event(data)

        mock_logger.assert_logged("INFO", "Event created")

    @pytest.mark.asyncio
    async def test_logging_on_cancel_event(
        self,
        event_service: EventService,
        mock_event_repo: AsyncMock,
        mock_leaderboard_repo: AsyncMock,
        mock_logger: MockLogService,
    ) -> None:
        """Cancelling an event logs at WARN level."""
        eid = uuid4()
        record = make_event_record(event_id=eid, status="active")
        mock_event_repo.find_by_id.return_value = record
        mock_event_repo.update.return_value = make_event_record(status="cancelled")

        await event_service.cancel_event(EventId(eid), "maintenance")

        mock_logger.assert_logged("WARN", "Event cancelled")
