"""Energy service implementation.

Manages hearts/energy system including consumption, regeneration,
daily login streaks, and bonus heart grants. All public methods are
``async def`` because they involve database and/or Redis operations.

Dependencies are injected via ``__init__`` -- no direct imports of
core service implementations.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.modules.energy.dto import (
    BonusGrantResult,
    BonusSource,
    EnergyConsumeResult,
    EnergyInfo,
    LoginResult,
    RegenResult,
    StreakInfo,
    TimeToHeartResult,
)
from src.modules.energy.bonuses import (
    IDEMPOTENCY_TTL_SECONDS,
    build_idempotency_redis_key,
    calculate_bonus_hearts,
    calculate_refund_hearts,
    validate_bonus_amount,
)
from src.modules.energy.consumption import (
    calculate_hearts_after_consume,
    check_can_play,
    validate_consume_amount,
)
from src.modules.energy.regen import (
    calculate_regenerated_hearts,
    calculate_time_to_next_heart,
)
from src.modules.energy.streak import (
    calculate_next_reward_threshold,
    calculate_streak_reward,
    calculate_streak_update,
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.energy_state_repository import EnergyStateRepositoryProtocol
    from src.modules.player.protocols import PlayerServiceProtocol


class EnergyService:
    """Concrete implementation of EnergyServiceProtocol.

    Manages energy (hearts) logic: consumption, regeneration, streaks,
    and bonus grants. Data is read via the player service and written
    via the energy state repository (to bypass max_hearts validation
    when bonus overflow is needed).
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        energy_repo: EnergyStateRepositoryProtocol,
        redis: Any,  # Redis client for idempotency
        data_ctx: DataContextProtocol | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._player_service = player_service
        self._energy_repo = energy_repo
        self._redis = redis
        # Transaction boundary context for atomic operations (e.g. consume_heart).
        # TODO: wrap consume_heart regen+update in async with self._data_ctx.session()
        # once service-layer transaction orchestration pattern is established.
        self._data_ctx = data_ctx

        # Cache config values at init
        self._max_hearts: int = int(config.get("energy.max_hearts", 7))
        self._regen_interval_minutes: int = int(
            config.get("energy.regen_interval_minutes", 30),
        )
        self._regen_interval_seconds: int = self._regen_interval_minutes * 60
        self._bonus_overflow_limit: int = int(
            config.get("energy.bonus_overflow_limit", 3),
        )
        self._streak_reward_7: int = int(
            config.get("energy.streak_reward_threshold_7", 1),
        )
        self._streak_reward_14: int = int(
            config.get("energy.streak_reward_threshold_14", 2),
        )
        self._streak_reward_30: int = int(
            config.get("energy.streak_reward_threshold_30", 3),
        )
        self._streak_repeat_interval: int = int(
            config.get("energy.streak_reward_repeat_interval", 7),
        )

    # ========== Core Energy Operations ==========

    async def get_energy(
        self,
        player_id: PlayerId,
    ) -> EnergyInfo:
        """Get player's current energy state with real-time regen calculation."""
        energy_state = await self._player_service.get_energy_state(player_id)
        now = datetime.now(timezone.utc)

        # Calculate regenerated hearts (without persisting)
        hearts_to_add, effective_hearts, _ = calculate_regenerated_hearts(
            current_hearts=energy_state.hearts,
            max_hearts=energy_state.max_hearts,
            last_regen_at=energy_state.last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        # Calculate time to next heart based on effective state
        seconds_to_next = calculate_time_to_next_heart(
            current_hearts=effective_hearts,
            max_hearts=energy_state.max_hearts,
            last_regen_at=energy_state.last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        info = EnergyInfo(
            player_id=str(player_id),
            current_hearts=effective_hearts,
            max_hearts=energy_state.max_hearts,
            seconds_to_next_heart=seconds_to_next,
            next_heart_at=(
                now + timedelta(seconds=seconds_to_next)
                if seconds_to_next is not None
                else None
            ),
            is_full=effective_hearts >= energy_state.max_hearts,
            daily_streak=energy_state.daily_streak,
            last_login_date=energy_state.last_login_date,
        )

        self._logger.debug(
            "Energy state retrieved",
            player_id=str(player_id),
            current_hearts=effective_hearts,
            max_hearts=energy_state.max_hearts,
        )

        return info

    async def consume_heart(
        self,
        player_id: PlayerId,
        amount: int = 1,
    ) -> EnergyConsumeResult:
        """Consume hearts for an action. Applies regen first."""
        if not validate_consume_amount(amount):
            raise self._errors.validation(
                "Amount must be at least 1",
                code="VALIDATION_INVALID_INPUT",
                amount=amount,
            )

        # Apply pending regeneration and persist
        regen_result = await self.apply_pending_regeneration(player_id)
        effective_hearts = regen_result.hearts_after

        if not check_can_play(effective_hearts, amount):
            self._logger.warn(
                "Insufficient hearts",
                player_id=str(player_id),
                required=amount,
                available=effective_hearts,
            )
            raise self._errors.forbidden(
                "Not enough hearts",
                code="FORBIDDEN_INSUFFICIENT_ENERGY",
                required=amount,
                available=effective_hearts,
            )

        # Update hearts and reset regen timer so stale last_regen_at
        # doesn't cause phantom instant regen on the next get_energy call.
        now = datetime.now(timezone.utc)
        new_hearts = calculate_hearts_after_consume(effective_hearts, amount)
        updated_state = await self._energy_repo.update(
            UUID(str(player_id)),
            hearts=new_hearts,
            last_regen_at=now,
        )

        self._logger.info(
            "Heart consumed",
            player_id=str(player_id),
            amount=amount,
            remaining_hearts=new_hearts,
        )

        seconds_to_next = calculate_time_to_next_heart(
            current_hearts=new_hearts,
            max_hearts=updated_state.max_hearts,
            last_regen_at=updated_state.last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        energy_info = EnergyInfo(
            player_id=str(player_id),
            current_hearts=new_hearts,
            max_hearts=updated_state.max_hearts,
            seconds_to_next_heart=seconds_to_next,
            next_heart_at=(
                now + timedelta(seconds=seconds_to_next)
                if seconds_to_next is not None
                else None
            ),
            is_full=new_hearts >= updated_state.max_hearts,
            daily_streak=updated_state.daily_streak,
            last_login_date=updated_state.last_login_date,
        )

        return EnergyConsumeResult(
            success=True,
            hearts_consumed=amount,
            hearts_remaining=new_hearts,
            hearts_regenerated_before_consume=regen_result.hearts_added,
            energy_info=energy_info,
        )

    async def can_play(
        self,
        player_id: PlayerId,
        hearts_required: int = 1,
    ) -> bool:
        """Check if player has enough hearts to play (non-consuming)."""
        energy_state = await self._player_service.get_energy_state(player_id)
        now = datetime.now(timezone.utc)

        _, effective_hearts, _ = calculate_regenerated_hearts(
            current_hearts=energy_state.hearts,
            max_hearts=energy_state.max_hearts,
            last_regen_at=energy_state.last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        return check_can_play(effective_hearts, hearts_required)

    # ========== Regeneration Operations ==========

    async def apply_pending_regeneration(
        self,
        player_id: PlayerId,
    ) -> RegenResult:
        """Calculate and persist any hearts that have regenerated."""
        energy_state = await self._player_service.get_energy_state(player_id)
        now = datetime.now(timezone.utc)

        hearts_before = energy_state.hearts

        hearts_to_add, new_hearts, new_last_regen_at = calculate_regenerated_hearts(
            current_hearts=energy_state.hearts,
            max_hearts=energy_state.max_hearts,
            last_regen_at=energy_state.last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        if hearts_to_add > 0:
            updated_state = await self._energy_repo.update(
                UUID(str(player_id)),
                hearts=new_hearts,
                last_regen_at=new_last_regen_at,
            )
            self._logger.info(
                "Hearts regenerated",
                player_id=str(player_id),
                hearts_added=hearts_to_add,
                new_total=new_hearts,
            )
        else:
            updated_state = energy_state

        seconds_to_next = calculate_time_to_next_heart(
            current_hearts=new_hearts,
            max_hearts=updated_state.max_hearts,
            last_regen_at=new_last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        energy_info = EnergyInfo(
            player_id=str(player_id),
            current_hearts=new_hearts,
            max_hearts=updated_state.max_hearts,
            seconds_to_next_heart=seconds_to_next,
            next_heart_at=(
                now + timedelta(seconds=seconds_to_next)
                if seconds_to_next is not None
                else None
            ),
            is_full=new_hearts >= updated_state.max_hearts,
            daily_streak=updated_state.daily_streak,
            last_login_date=updated_state.last_login_date,
        )

        return RegenResult(
            hearts_added=hearts_to_add,
            hearts_before=hearts_before,
            hearts_after=new_hearts,
            last_regen_at=new_last_regen_at,
            energy_info=energy_info,
        )

    async def get_time_to_next_heart(
        self,
        player_id: PlayerId,
    ) -> TimeToHeartResult:
        """Get time remaining until next heart regenerates."""
        energy_state = await self._player_service.get_energy_state(player_id)
        now = datetime.now(timezone.utc)

        # Calculate effective hearts first
        _, effective_hearts, new_last_regen_at = calculate_regenerated_hearts(
            current_hearts=energy_state.hearts,
            max_hearts=energy_state.max_hearts,
            last_regen_at=energy_state.last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        seconds_to_next = calculate_time_to_next_heart(
            current_hearts=effective_hearts,
            max_hearts=energy_state.max_hearts,
            last_regen_at=new_last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        is_full = effective_hearts >= energy_state.max_hearts

        return TimeToHeartResult(
            seconds_remaining=seconds_to_next if seconds_to_next is not None else 0,
            next_regen_at=(
                now + timedelta(seconds=seconds_to_next)
                if seconds_to_next is not None
                else None
            ),
            is_full=is_full,
            current_hearts=effective_hearts,
            max_hearts=energy_state.max_hearts,
        )

    # ========== Streak Operations ==========

    async def record_login(
        self,
        player_id: PlayerId,
    ) -> LoginResult:
        """Record a player login for streak tracking."""
        # Apply regen first
        regen_result = await self.apply_pending_regeneration(player_id)

        # Re-read the (now potentially updated) state
        energy_state = await self._player_service.get_energy_state(player_id)
        today = datetime.now(timezone.utc).date()

        # Calculate streak update
        new_streak, streak_continued, streak_broken = calculate_streak_update(
            last_login_date=energy_state.last_login_date,
            current_streak=energy_state.daily_streak,
            today=today,
        )

        # Check for same-day login (no change needed)
        same_day = (
            not streak_continued
            and not streak_broken
            and energy_state.last_login_date is not None
        )

        # Calculate streak reward
        bonus_hearts = 0
        if streak_continued or (energy_state.last_login_date is None):
            bonus_hearts = calculate_streak_reward(
                streak_day=new_streak,
                threshold_7=self._streak_reward_7,
                threshold_14=self._streak_reward_14,
                threshold_30=self._streak_reward_30,
                repeat_interval=self._streak_repeat_interval,
            )

        # Persist streak + login date
        if not same_day:
            update_fields: dict[str, Any] = {
                "daily_streak": new_streak,
                "last_login_date": today,
            }

            # Grant bonus hearts if earned
            if bonus_hearts > 0:
                current_hearts = regen_result.hearts_after
                new_hearts, _ = calculate_bonus_hearts(
                    current_hearts=current_hearts,
                    amount=bonus_hearts,
                    max_hearts=self._max_hearts,
                    overflow_limit=self._bonus_overflow_limit,
                )
                update_fields["hearts"] = new_hearts

                self._logger.info(
                    "Streak bonus granted",
                    player_id=str(player_id),
                    bonus_hearts=bonus_hearts,
                    streak_day=new_streak,
                )

            await self._energy_repo.update(
                UUID(str(player_id)),
                **update_fields,
            )

        self._logger.info(
            "Login recorded",
            player_id=str(player_id),
            streak_day=new_streak,
            streak_continued=streak_continued,
            streak_broken=streak_broken,
        )

        # Calculate next reward threshold
        next_threshold, days_until = calculate_next_reward_threshold(new_streak)

        # Build energy info from current state
        now = datetime.now(timezone.utc)
        updated_state = await self._player_service.get_energy_state(player_id)

        seconds_to_next = calculate_time_to_next_heart(
            current_hearts=updated_state.hearts,
            max_hearts=updated_state.max_hearts,
            last_regen_at=updated_state.last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        energy_info = EnergyInfo(
            player_id=str(player_id),
            current_hearts=updated_state.hearts,
            max_hearts=updated_state.max_hearts,
            seconds_to_next_heart=seconds_to_next,
            next_heart_at=(
                now + timedelta(seconds=seconds_to_next)
                if seconds_to_next is not None
                else None
            ),
            is_full=updated_state.hearts >= updated_state.max_hearts,
            daily_streak=new_streak,
            last_login_date=today if not same_day else energy_state.last_login_date,
        )

        return LoginResult(
            streak_day=new_streak,
            streak_continued=streak_continued,
            streak_broken=streak_broken,
            bonus_hearts_granted=bonus_hearts if not same_day else 0,
            next_streak_reward_at=days_until,
            energy_info=energy_info,
        )

    async def get_streak(
        self,
        player_id: PlayerId,
    ) -> StreakInfo:
        """Get player's current streak information."""
        energy_state = await self._player_service.get_energy_state(player_id)

        next_threshold, days_until = calculate_next_reward_threshold(
            energy_state.daily_streak,
        )

        # Calculate reward amount at the next threshold
        reward_hearts = calculate_streak_reward(
            streak_day=next_threshold,
            threshold_7=self._streak_reward_7,
            threshold_14=self._streak_reward_14,
            threshold_30=self._streak_reward_30,
            repeat_interval=self._streak_repeat_interval,
        )

        # Calculate streak_started_at
        streak_started_at: date | None = None
        if energy_state.last_login_date is not None and energy_state.daily_streak > 0:
            streak_started_at = energy_state.last_login_date - timedelta(
                days=energy_state.daily_streak - 1,
            )

        return StreakInfo(
            current_streak=energy_state.daily_streak,
            last_login_date=energy_state.last_login_date,
            streak_started_at=streak_started_at,
            next_reward_threshold=next_threshold,
            days_until_reward=days_until,
            reward_hearts=reward_hearts,
        )

    # ========== Bonus Heart Operations ==========

    async def grant_bonus_hearts(
        self,
        player_id: PlayerId,
        amount: int,
        source: BonusSource,
        idempotency_key: str | None = None,
    ) -> BonusGrantResult:
        """Grant bonus hearts from various sources."""
        if not validate_bonus_amount(amount):
            raise self._errors.validation(
                "Amount must be at least 1",
                code="VALIDATION_INVALID_INPUT",
                amount=amount,
            )

        # Check idempotency
        redis_key: str | None = None
        if idempotency_key is not None:
            redis_key = build_idempotency_redis_key(player_id, idempotency_key)

            self._logger.debug(
                "Bonus claim attempted",
                player_id=str(player_id),
                source=source.value,
                idempotency_key=idempotency_key,
            )

            try:
                exists = await self._redis.exists(redis_key)
                if exists:
                    self._logger.warn(
                        "Duplicate bonus claim",
                        player_id=str(player_id),
                        source=source.value,
                        idempotency_key=idempotency_key,
                    )

                    # Return already_claimed result
                    energy_info = await self.get_energy(player_id)
                    return BonusGrantResult(
                        granted=False,
                        hearts_granted=0,
                        hearts_before=energy_info.current_hearts,
                        hearts_after=energy_info.current_hearts,
                        source=source,
                        already_claimed=True,
                        energy_info=energy_info,
                    )
            except Exception:
                # Redis unavailable -- fall through, accept duplicate risk
                self._logger.warn(
                    "Redis unavailable for idempotency check",
                    player_id=str(player_id),
                    source=source.value,
                )

        # Apply pending regen first
        regen_result = await self.apply_pending_regeneration(player_id)
        hearts_before = regen_result.hearts_after

        # Calculate new hearts with overflow limit
        new_hearts, actual_granted = calculate_bonus_hearts(
            current_hearts=hearts_before,
            amount=amount,
            max_hearts=self._max_hearts,
            overflow_limit=self._bonus_overflow_limit,
        )

        # Set idempotency key in Redis (24h TTL)
        if redis_key is not None:
            try:
                await self._redis.setex(redis_key, IDEMPOTENCY_TTL_SECONDS, "1")
            except Exception:
                self._logger.warn(
                    "Redis unavailable for idempotency set",
                    player_id=str(player_id),
                    source=source.value,
                )

        # Persist via energy_repo directly (bypasses player_service max_hearts check)
        await self._energy_repo.update(
            UUID(str(player_id)),
            hearts=new_hearts,
        )

        self._logger.info(
            "Bonus hearts granted",
            player_id=str(player_id),
            amount=actual_granted,
            source=source.value,
            new_total=new_hearts,
        )

        now = datetime.now(timezone.utc)
        updated_state = await self._player_service.get_energy_state(player_id)

        seconds_to_next = calculate_time_to_next_heart(
            current_hearts=new_hearts,
            max_hearts=updated_state.max_hearts,
            last_regen_at=updated_state.last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        energy_info = EnergyInfo(
            player_id=str(player_id),
            current_hearts=new_hearts,
            max_hearts=updated_state.max_hearts,
            seconds_to_next_heart=seconds_to_next,
            next_heart_at=(
                now + timedelta(seconds=seconds_to_next)
                if seconds_to_next is not None
                else None
            ),
            is_full=new_hearts >= updated_state.max_hearts,
            daily_streak=updated_state.daily_streak,
            last_login_date=updated_state.last_login_date,
        )

        return BonusGrantResult(
            granted=True,
            hearts_granted=actual_granted,
            hearts_before=hearts_before,
            hearts_after=new_hearts,
            source=source,
            already_claimed=False,
            energy_info=energy_info,
        )

    async def refund_heart(
        self,
        player_id: PlayerId,
        amount: int = 1,
        reason: str = "match_cancelled",
    ) -> EnergyInfo:
        """Refund hearts, capped at max_hearts."""
        energy_state = await self._player_service.get_energy_state(player_id)

        new_hearts = calculate_refund_hearts(
            current_hearts=energy_state.hearts,
            amount=amount,
            max_hearts=self._max_hearts,
        )
        await self._energy_repo.update(
            UUID(str(player_id)),
            hearts=new_hearts,
        )

        self._logger.info(
            "Heart refunded",
            player_id=str(player_id),
            amount=amount,
            reason=reason,
        )

        now = datetime.now(timezone.utc)
        seconds_to_next = calculate_time_to_next_heart(
            current_hearts=new_hearts,
            max_hearts=energy_state.max_hearts,
            last_regen_at=energy_state.last_regen_at,
            now=now,
            regen_interval_seconds=self._regen_interval_seconds,
        )

        return EnergyInfo(
            player_id=str(player_id),
            current_hearts=new_hearts,
            max_hearts=energy_state.max_hearts,
            seconds_to_next_heart=seconds_to_next,
            next_heart_at=(
                now + timedelta(seconds=seconds_to_next)
                if seconds_to_next is not None
                else None
            ),
            is_full=new_hearts >= energy_state.max_hearts,
            daily_streak=energy_state.daily_streak,
            last_login_date=energy_state.last_login_date,
        )
