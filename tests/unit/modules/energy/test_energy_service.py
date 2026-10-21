"""Unit tests for the EnergyService.

Uses mock repositories and services to test business logic without
real database or Redis connections. All tests are async using
``pytest-asyncio``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.core.types.player import EnergyState
from src.modules.energy.dto import BonusSource
from src.modules.energy.service import EnergyService
from tests.mocks.redis import MockRedis
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ---------------------------------------------------------------------------
# Mock repositories and services
# ---------------------------------------------------------------------------


class MockPlayerService:
    """In-memory mock for PlayerServiceProtocol (energy-related methods)."""

    def __init__(self, errors: MockErrorService) -> None:
        self._energy_states: dict[UUID, EnergyState] = {}
        self._errors = errors

    def seed_energy_state(self, state: EnergyState) -> None:
        """Seed an energy state for testing."""
        self._energy_states[UUID(str(state.player_id))] = state

    async def get_energy_state(self, player_id: PlayerId) -> EnergyState:
        state = self._energy_states.get(UUID(str(player_id)))
        if state is None:
            raise self._errors.not_found(
                f"Player not found: {player_id}",
                code="NOT_FOUND_PLAYER",
            )
        return state

    async def update_energy_state(
        self, player_id: PlayerId, update: object
    ) -> EnergyState:
        """Apply update to stored state.

        Note: This has max_hearts validation. The energy module
        bypasses this by using the repo directly for overflow.
        """
        state = await self.get_energy_state(player_id)
        key = UUID(str(player_id))

        # Simulate the validation that PlayerService does
        if hasattr(update, "hearts") and update.hearts is not None:
            if update.hearts > state.max_hearts:
                raise self._errors.validation(
                    "Hearts cannot exceed max",
                    code="VALIDATION_INVALID_INPUT",
                )
            if update.hearts < 0:
                raise self._errors.validation(
                    "Hearts cannot be negative",
                    code="VALIDATION_INVALID_INPUT",
                )

        # Apply changes
        for field_name in (
            "hearts",
            "last_regen_at",
            "daily_streak",
            "last_login_date",
        ):
            value = getattr(update, field_name, None)
            if value is not None:
                object.__setattr__(state, field_name, value)

        self._energy_states[key] = state
        return state


class MockEnergyRepo:
    """In-memory mock for EnergyStateRepositoryProtocol.

    Shares state with MockPlayerService to simulate the same
    underlying data store.
    """

    def __init__(self, player_service: MockPlayerService) -> None:
        self._player_service = player_service

    async def find_by_player_id(self, player_id: UUID) -> EnergyState | None:
        return self._player_service._energy_states.get(player_id)

    async def create(
        self,
        player_id: UUID,
        hearts: int,
        max_hearts: int,
    ) -> EnergyState:
        state = EnergyState(
            player_id=PlayerId(player_id),
            hearts=hearts,
            max_hearts=max_hearts,
            last_regen_at=datetime.now(timezone.utc),
        )
        self._player_service._energy_states[player_id] = state
        return state

    async def update(self, player_id: UUID, **changes: object) -> EnergyState:
        state = self._player_service._energy_states.get(player_id)
        if state is None:
            msg = f"Energy state not found: {player_id}"
            raise AppError(
                code="NOT_FOUND_PLAYER",
                message=msg,
                http_status=404,
            )

        for key, value in changes.items():
            if hasattr(state, key):
                object.__setattr__(state, key, value)

        self._player_service._energy_states[player_id] = state
        return state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config() -> MockConfigService:
    return MockConfigService(
        {
            "energy.max_hearts": 5,
            "energy.regen_interval_minutes": 30,
            "energy.bonus_overflow_limit": 3,
            "energy.streak_reward_threshold_7": 1,
            "energy.streak_reward_threshold_14": 2,
            "energy.streak_reward_threshold_30": 3,
            "energy.streak_reward_repeat_interval": 7,
        }
    )


@pytest.fixture
def mock_logger() -> MockLogService:
    return MockLogService()


@pytest.fixture
def mock_errors(mock_logger: MockLogService) -> MockErrorService:
    return MockErrorService(mock_logger)


@pytest.fixture
def mock_redis() -> MockRedis:
    return MockRedis()


@pytest.fixture
def mock_player_service(mock_errors: MockErrorService) -> MockPlayerService:
    return MockPlayerService(mock_errors)


@pytest.fixture
def mock_energy_repo(mock_player_service: MockPlayerService) -> MockEnergyRepo:
    return MockEnergyRepo(mock_player_service)


@pytest.fixture
def energy_service(
    mock_config: MockConfigService,
    mock_logger: MockLogService,
    mock_errors: MockErrorService,
    mock_player_service: MockPlayerService,
    mock_energy_repo: MockEnergyRepo,
    mock_redis: MockRedis,
) -> EnergyService:
    return EnergyService(
        config=mock_config,
        logger=mock_logger,
        errors=mock_errors,
        player_service=mock_player_service,
        energy_repo=mock_energy_repo,
        redis=mock_redis,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player_id() -> PlayerId:
    return PlayerId(uuid4())


def _seed_player(
    player_service: MockPlayerService,
    player_id: PlayerId | None = None,
    hearts: int = 5,
    max_hearts: int = 5,
    last_regen_at: datetime | None = None,
    daily_streak: int = 0,
    last_login_date: date | None = None,
) -> PlayerId:
    """Seed a player with energy state for testing."""
    if player_id is None:
        player_id = _make_player_id()
    if last_regen_at is None:
        last_regen_at = datetime.now(timezone.utc)

    state = EnergyState(
        player_id=player_id,
        hearts=hearts,
        max_hearts=max_hearts,
        last_regen_at=last_regen_at,
        daily_streak=daily_streak,
        last_login_date=last_login_date,
    )
    player_service.seed_energy_state(state)
    return player_id


# ---------------------------------------------------------------------------
# Tests -- get_energy
# ---------------------------------------------------------------------------


class TestGetEnergy:
    """Tests for ``EnergyService.get_energy``."""

    @pytest.mark.asyncio
    async def test_basic_get(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Basic energy retrieval returns correct state."""
        pid = _seed_player(mock_player_service, hearts=3)
        info = await energy_service.get_energy(pid)

        assert info.player_id == str(pid)
        assert info.current_hearts == 3
        assert info.max_hearts == 5
        assert info.is_full is False

    @pytest.mark.asyncio
    async def test_get_with_pending_regen(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """get_energy includes pending regen in calculation (without persisting)."""
        # 1 hour ago = 2 intervals, so 2 hearts should regen
        last_regen = datetime.now(timezone.utc) - timedelta(hours=1)
        pid = _seed_player(
            mock_player_service,
            hearts=2,
            last_regen_at=last_regen,
        )

        info = await energy_service.get_energy(pid)
        assert info.current_hearts == 4  # 2 stored + 2 regen

        # Verify stored state was NOT modified (lazy regen)
        stored = await mock_player_service.get_energy_state(pid)
        assert stored.hearts == 2

    @pytest.mark.asyncio
    async def test_get_at_max(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """get_energy at max hearts shows full state."""
        pid = _seed_player(mock_player_service, hearts=5)
        info = await energy_service.get_energy(pid)

        assert info.current_hearts == 5
        assert info.is_full is True
        assert info.seconds_to_next_heart is None
        assert info.next_heart_at is None

    @pytest.mark.asyncio
    async def test_get_player_not_found(
        self,
        energy_service: EnergyService,
    ) -> None:
        """get_energy for non-existent player raises NOT_FOUND_PLAYER."""
        fake_id = _make_player_id()
        with pytest.raises(AppError) as exc_info:
            await energy_service.get_energy(fake_id)
        assert exc_info.value.code == "NOT_FOUND_PLAYER"


# ---------------------------------------------------------------------------
# Tests -- consume_heart
# ---------------------------------------------------------------------------


class TestConsumeHeart:
    """Tests for ``EnergyService.consume_heart``."""

    @pytest.mark.asyncio
    async def test_consume_success(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Successful heart consumption."""
        pid = _seed_player(mock_player_service, hearts=3)
        result = await energy_service.consume_heart(pid)

        assert result.success is True
        assert result.hearts_consumed == 1
        assert result.hearts_remaining == 2
        assert result.hearts_regenerated_before_consume == 0

    @pytest.mark.asyncio
    async def test_consume_insufficient_hearts(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Consuming with insufficient hearts raises FORBIDDEN."""
        pid = _seed_player(mock_player_service, hearts=0)
        with pytest.raises(AppError) as exc_info:
            await energy_service.consume_heart(pid)
        assert exc_info.value.code == "FORBIDDEN_INSUFFICIENT_ENERGY"

    @pytest.mark.asyncio
    async def test_consume_with_regen_first(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Regen is applied before consuming, enabling consumption."""
        # 0 stored hearts but 1 hour of regen pending = 2 hearts regen
        last_regen = datetime.now(timezone.utc) - timedelta(hours=1)
        pid = _seed_player(
            mock_player_service,
            hearts=0,
            last_regen_at=last_regen,
        )

        result = await energy_service.consume_heart(pid)
        assert result.success is True
        assert result.hearts_regenerated_before_consume == 2
        assert result.hearts_remaining == 1  # 2 regen - 1 consumed

    @pytest.mark.asyncio
    async def test_consume_amount_greater_than_one(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Consuming multiple hearts at once."""
        pid = _seed_player(mock_player_service, hearts=4)
        result = await energy_service.consume_heart(pid, amount=3)

        assert result.success is True
        assert result.hearts_consumed == 3
        assert result.hearts_remaining == 1

    @pytest.mark.asyncio
    async def test_consume_invalid_amount(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Amount < 1 raises VALIDATION_INVALID_INPUT."""
        pid = _seed_player(mock_player_service, hearts=5)
        with pytest.raises(AppError) as exc_info:
            await energy_service.consume_heart(pid, amount=0)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_consume_exact_hearts(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Consuming exactly all available hearts succeeds."""
        pid = _seed_player(mock_player_service, hearts=2)
        result = await energy_service.consume_heart(pid, amount=2)

        assert result.success is True
        assert result.hearts_remaining == 0


# ---------------------------------------------------------------------------
# Tests -- can_play
# ---------------------------------------------------------------------------


class TestCanPlay:
    """Tests for ``EnergyService.can_play``."""

    @pytest.mark.asyncio
    async def test_can_play_with_energy(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Player with hearts can play."""
        pid = _seed_player(mock_player_service, hearts=3)
        assert await energy_service.can_play(pid) is True

    @pytest.mark.asyncio
    async def test_cannot_play_no_energy(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Player with 0 hearts and no pending regen cannot play."""
        pid = _seed_player(mock_player_service, hearts=0)
        assert await energy_service.can_play(pid) is False

    @pytest.mark.asyncio
    async def test_can_play_after_regen(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Player with 0 stored hearts but pending regen can play."""
        last_regen = datetime.now(timezone.utc) - timedelta(hours=1)
        pid = _seed_player(
            mock_player_service,
            hearts=0,
            last_regen_at=last_regen,
        )
        assert await energy_service.can_play(pid) is True


# ---------------------------------------------------------------------------
# Tests -- apply_pending_regeneration
# ---------------------------------------------------------------------------


class TestApplyPendingRegeneration:
    """Tests for ``EnergyService.apply_pending_regeneration``."""

    @pytest.mark.asyncio
    async def test_regen_with_pending(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Hearts are regenerated and persisted when pending."""
        last_regen = datetime.now(timezone.utc) - timedelta(hours=1)
        pid = _seed_player(
            mock_player_service,
            hearts=2,
            last_regen_at=last_regen,
        )

        result = await energy_service.apply_pending_regeneration(pid)
        assert result.hearts_added == 2
        assert result.hearts_before == 2
        assert result.hearts_after == 4

        # Verify persisted
        stored = await mock_player_service.get_energy_state(pid)
        assert stored.hearts == 4

    @pytest.mark.asyncio
    async def test_no_regen_pending(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """No regeneration when no time has passed."""
        pid = _seed_player(mock_player_service, hearts=3)
        result = await energy_service.apply_pending_regeneration(pid)

        assert result.hearts_added == 0
        assert result.hearts_before == 3
        assert result.hearts_after == 3

    @pytest.mark.asyncio
    async def test_regen_at_max(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """No regeneration when already at max."""
        last_regen = datetime.now(timezone.utc) - timedelta(hours=2)
        pid = _seed_player(
            mock_player_service,
            hearts=5,
            last_regen_at=last_regen,
        )

        result = await energy_service.apply_pending_regeneration(pid)
        assert result.hearts_added == 0
        assert result.hearts_after == 5

    @pytest.mark.asyncio
    async def test_regen_capped_at_max(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Regeneration is capped at max_hearts."""
        last_regen = datetime.now(timezone.utc) - timedelta(hours=5)
        pid = _seed_player(
            mock_player_service,
            hearts=3,
            last_regen_at=last_regen,
        )

        result = await energy_service.apply_pending_regeneration(pid)
        assert result.hearts_after == 5
        assert result.hearts_added == 2


# ---------------------------------------------------------------------------
# Tests -- get_time_to_next_heart
# ---------------------------------------------------------------------------


class TestGetTimeToNextHeart:
    """Tests for ``EnergyService.get_time_to_next_heart``."""

    @pytest.mark.asyncio
    async def test_is_full(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Full hearts returns is_full=True."""
        pid = _seed_player(mock_player_service, hearts=5)
        result = await energy_service.get_time_to_next_heart(pid)

        assert result.is_full is True
        assert result.seconds_remaining == 0
        assert result.next_regen_at is None

    @pytest.mark.asyncio
    async def test_time_remaining(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Reports correct seconds remaining."""
        pid = _seed_player(mock_player_service, hearts=3)
        result = await energy_service.get_time_to_next_heart(pid)

        assert result.is_full is False
        assert result.seconds_remaining > 0
        assert result.seconds_remaining <= 1800  # Max one interval
        assert result.next_regen_at is not None


# ---------------------------------------------------------------------------
# Tests -- record_login
# ---------------------------------------------------------------------------


class TestRecordLogin:
    """Tests for ``EnergyService.record_login``."""

    @pytest.mark.asyncio
    async def test_first_login(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """First login sets streak to 1."""
        pid = _seed_player(
            mock_player_service,
            hearts=5,
            daily_streak=0,
            last_login_date=None,
        )
        result = await energy_service.record_login(pid)

        assert result.streak_day == 1
        assert result.streak_continued is False
        assert result.streak_broken is False

    @pytest.mark.asyncio
    async def test_consecutive_day_login(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Consecutive day login increments streak."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        pid = _seed_player(
            mock_player_service,
            hearts=5,
            daily_streak=5,
            last_login_date=yesterday,
        )
        result = await energy_service.record_login(pid)

        assert result.streak_day == 6
        assert result.streak_continued is True
        assert result.streak_broken is False

    @pytest.mark.asyncio
    async def test_streak_break(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Missing a day breaks the streak."""
        two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).date()
        pid = _seed_player(
            mock_player_service,
            hearts=5,
            daily_streak=10,
            last_login_date=two_days_ago,
        )
        result = await energy_service.record_login(pid)

        assert result.streak_day == 1
        assert result.streak_continued is False
        assert result.streak_broken is True

    @pytest.mark.asyncio
    async def test_same_day_login(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Same day login is a no-op for streak."""
        today = datetime.now(timezone.utc).date()
        pid = _seed_player(
            mock_player_service,
            hearts=5,
            daily_streak=3,
            last_login_date=today,
        )
        result = await energy_service.record_login(pid)

        assert result.streak_day == 3
        assert result.streak_continued is False
        assert result.streak_broken is False
        assert result.bonus_hearts_granted == 0

    @pytest.mark.asyncio
    async def test_login_with_streak_reward(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Login that reaches day 7 grants bonus hearts."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        pid = _seed_player(
            mock_player_service,
            hearts=3,
            daily_streak=6,
            last_login_date=yesterday,
        )
        result = await energy_service.record_login(pid)

        assert result.streak_day == 7
        assert result.bonus_hearts_granted == 1  # threshold_7 = 1
        assert result.streak_continued is True

    @pytest.mark.asyncio
    async def test_login_with_day_14_reward(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Login that reaches day 14 grants 2 bonus hearts."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        pid = _seed_player(
            mock_player_service,
            hearts=3,
            daily_streak=13,
            last_login_date=yesterday,
        )
        result = await energy_service.record_login(pid)

        assert result.streak_day == 14
        assert result.bonus_hearts_granted == 2


# ---------------------------------------------------------------------------
# Tests -- get_streak
# ---------------------------------------------------------------------------


class TestGetStreak:
    """Tests for ``EnergyService.get_streak``."""

    @pytest.mark.asyncio
    async def test_basic_streak_info(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Returns correct streak information."""
        today = datetime.now(timezone.utc).date()
        pid = _seed_player(
            mock_player_service,
            daily_streak=5,
            last_login_date=today,
        )
        info = await energy_service.get_streak(pid)

        assert info.current_streak == 5
        assert info.last_login_date == today
        assert info.next_reward_threshold == 7
        assert info.days_until_reward == 2
        assert info.reward_hearts == 1  # threshold_7

    @pytest.mark.asyncio
    async def test_streak_started_at(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """streak_started_at is correctly calculated."""
        today = datetime.now(timezone.utc).date()
        pid = _seed_player(
            mock_player_service,
            daily_streak=5,
            last_login_date=today,
        )
        info = await energy_service.get_streak(pid)

        from datetime import timedelta as td

        expected_start = today - td(days=4)  # 5 day streak means started 4 days ago
        assert info.streak_started_at == expected_start


# ---------------------------------------------------------------------------
# Tests -- grant_bonus_hearts
# ---------------------------------------------------------------------------


class TestGrantBonusHearts:
    """Tests for ``EnergyService.grant_bonus_hearts``."""

    @pytest.mark.asyncio
    async def test_grant_success(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Successful bonus heart grant."""
        pid = _seed_player(mock_player_service, hearts=3)
        result = await energy_service.grant_bonus_hearts(
            pid,
            amount=2,
            source=BonusSource.AD_REWARD,
        )

        assert result.granted is True
        assert result.hearts_granted == 2
        assert result.hearts_before == 3
        assert result.hearts_after == 5
        assert result.source == BonusSource.AD_REWARD
        assert result.already_claimed is False

    @pytest.mark.asyncio
    async def test_grant_overflow(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Bonus hearts can exceed max_hearts up to overflow limit."""
        pid = _seed_player(mock_player_service, hearts=5)
        result = await energy_service.grant_bonus_hearts(
            pid,
            amount=2,
            source=BonusSource.EVENT_REWARD,
        )

        assert result.granted is True
        assert result.hearts_after == 7  # 5 + 2, within overflow limit of 8
        assert result.hearts_granted == 2

    @pytest.mark.asyncio
    async def test_grant_capped_at_overflow_limit(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Bonus hearts are capped at max_hearts + overflow_limit."""
        pid = _seed_player(mock_player_service, hearts=5)
        result = await energy_service.grant_bonus_hearts(
            pid,
            amount=10,
            source=BonusSource.COMPENSATION,
        )

        # max_hearts(5) + overflow_limit(3) = 8
        assert result.hearts_after == 8
        assert result.hearts_granted == 3

    @pytest.mark.asyncio
    async def test_grant_idempotency_new(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
        mock_redis: MockRedis,
    ) -> None:
        """First grant with idempotency key succeeds and sets Redis key."""
        pid = _seed_player(mock_player_service, hearts=3)
        result = await energy_service.grant_bonus_hearts(
            pid,
            amount=1,
            source=BonusSource.AD_REWARD,
            idempotency_key="ad-123",
        )

        assert result.granted is True
        assert result.hearts_granted == 1

        # Verify Redis key was set
        redis_key = f"chromacrush:energy:bonus:{pid}:ad-123"
        assert await mock_redis.get(redis_key) == "1"

    @pytest.mark.asyncio
    async def test_grant_idempotency_duplicate(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
        mock_redis: MockRedis,
    ) -> None:
        """Duplicate grant with same idempotency key returns already_claimed."""
        pid = _seed_player(mock_player_service, hearts=3)

        # First grant
        await energy_service.grant_bonus_hearts(
            pid,
            amount=1,
            source=BonusSource.AD_REWARD,
            idempotency_key="ad-123",
        )

        # Duplicate grant
        result = await energy_service.grant_bonus_hearts(
            pid,
            amount=1,
            source=BonusSource.AD_REWARD,
            idempotency_key="ad-123",
        )

        assert result.granted is False
        assert result.already_claimed is True
        assert result.hearts_granted == 0

    @pytest.mark.asyncio
    async def test_grant_invalid_amount(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Amount < 1 raises VALIDATION_INVALID_INPUT."""
        pid = _seed_player(mock_player_service, hearts=5)
        with pytest.raises(AppError) as exc_info:
            await energy_service.grant_bonus_hearts(
                pid,
                amount=0,
                source=BonusSource.AD_REWARD,
            )
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_grant_without_idempotency_key(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
        mock_redis: MockRedis,
    ) -> None:
        """Grant without idempotency key does not interact with Redis (no setex)."""
        pid = _seed_player(mock_player_service, hearts=3)
        result = await energy_service.grant_bonus_hearts(
            pid,
            amount=1,
            source=BonusSource.REFERRAL,
        )

        assert result.granted is True
        # No Redis calls for exists or setex
        setex_calls = [op for op in mock_redis.operations if op.method == "setex"]
        exists_calls = [op for op in mock_redis.operations if op.method == "exists"]
        assert len(setex_calls) == 0
        assert len(exists_calls) == 0


# ---------------------------------------------------------------------------
# Tests -- refund_heart
# ---------------------------------------------------------------------------


class TestRefundHeart:
    """Tests for ``EnergyService.refund_heart``."""

    @pytest.mark.asyncio
    async def test_basic_refund(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Refund adds hearts."""
        pid = _seed_player(mock_player_service, hearts=3)
        info = await energy_service.refund_heart(pid)

        assert info.current_hearts == 4

    @pytest.mark.asyncio
    async def test_refund_capped_at_max(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Refund is capped at max_hearts."""
        pid = _seed_player(mock_player_service, hearts=5)
        info = await energy_service.refund_heart(pid)

        assert info.current_hearts == 5  # Already at max

    @pytest.mark.asyncio
    async def test_refund_multiple(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Refund multiple hearts."""
        pid = _seed_player(mock_player_service, hearts=1)
        info = await energy_service.refund_heart(pid, amount=3)

        assert info.current_hearts == 4

    @pytest.mark.asyncio
    async def test_refund_capped_from_partial(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Refund that would exceed max is capped."""
        pid = _seed_player(mock_player_service, hearts=4)
        info = await energy_service.refund_heart(pid, amount=5)

        assert info.current_hearts == 5  # Capped at max

    @pytest.mark.asyncio
    async def test_refund_player_not_found(
        self,
        energy_service: EnergyService,
    ) -> None:
        """Refund for non-existent player raises NOT_FOUND_PLAYER."""
        fake_id = _make_player_id()
        with pytest.raises(AppError) as exc_info:
            await energy_service.refund_heart(fake_id)
        assert exc_info.value.code == "NOT_FOUND_PLAYER"

    @pytest.mark.asyncio
    async def test_refund_logs_reason(
        self,
        energy_service: EnergyService,
        mock_player_service: MockPlayerService,
        mock_logger: MockLogService,
    ) -> None:
        """Refund logs the reason."""
        pid = _seed_player(mock_player_service, hearts=3)
        await energy_service.refund_heart(pid, reason="opponent_disconnect")

        mock_logger.assert_logged("INFO", "Heart refunded")
