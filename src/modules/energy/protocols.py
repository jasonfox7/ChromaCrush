"""Energy service protocol.

Defines the public interface for the energy module. All methods are
``async def`` because they involve database or Redis operations.

Other modules and the presentation layer depend on this protocol
interface; the concrete ``EnergyService`` implementation lives in
``src.modules.energy.service``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from src.core.types.game import PlayerId

if TYPE_CHECKING:
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


class EnergyServiceProtocol(Protocol):
    """Public interface for the energy module."""

    # ========== Core Energy Operations ==========

    async def get_energy(
        self,
        player_id: PlayerId,
    ) -> EnergyInfo:
        """Get player's current energy state with real-time calculations.

        Calculates current hearts based on stored hearts plus any
        hearts that have regenerated since ``last_regen_at``.

        Args:
            player_id: The player to query.

        Returns:
            EnergyInfo with current hearts, max hearts, time to next
            heart, streak info, and whether full.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def consume_heart(
        self,
        player_id: PlayerId,
        amount: int = 1,
    ) -> EnergyConsumeResult:
        """Consume hearts for an action (e.g., starting a match).

        Applies pending regeneration first, then validates and
        deducts the requested amount atomically.

        Args:
            player_id: The player consuming energy.
            amount: Hearts to consume (default 1).

        Returns:
            EnergyConsumeResult with new state and consumption details.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            FORBIDDEN_INSUFFICIENT_ENERGY: If hearts < amount after regen.
            VALIDATION_INVALID_INPUT: If amount < 1.
        """
        ...

    async def can_play(
        self,
        player_id: PlayerId,
        hearts_required: int = 1,
    ) -> bool:
        """Check if player has enough hearts to play (non-consuming).

        Includes real-time regeneration calculation.

        Args:
            player_id: The player to check.
            hearts_required: Hearts needed (default 1).

        Returns:
            True if player has >= hearts_required after regen calc.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Regeneration Operations ==========

    async def apply_pending_regeneration(
        self,
        player_id: PlayerId,
    ) -> RegenResult:
        """Calculate and persist any hearts that have regenerated.

        Args:
            player_id: The player.

        Returns:
            RegenResult with hearts_added and new state.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def get_time_to_next_heart(
        self,
        player_id: PlayerId,
    ) -> TimeToHeartResult:
        """Get time remaining until next heart regenerates.

        Args:
            player_id: The player.

        Returns:
            TimeToHeartResult with seconds_remaining, next_regen_at,
            and is_full.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Streak Operations ==========

    async def record_login(
        self,
        player_id: PlayerId,
    ) -> LoginResult:
        """Record a player login for streak tracking.

        Compares last_login_date with today (UTC) and updates
        the streak accordingly. Grants bonus hearts at milestones.

        Args:
            player_id: The player logging in.

        Returns:
            LoginResult with streak info and any bonus granted.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def get_streak(
        self,
        player_id: PlayerId,
    ) -> StreakInfo:
        """Get player's current streak information.

        Args:
            player_id: The player.

        Returns:
            StreakInfo with current streak, last login, next reward.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Bonus Heart Operations ==========

    async def grant_bonus_hearts(
        self,
        player_id: PlayerId,
        amount: int,
        source: BonusSource,
        idempotency_key: str | None = None,
    ) -> BonusGrantResult:
        """Grant bonus hearts from various sources.

        Bonus hearts can exceed max_hearts up to
        ``max_hearts + bonus_overflow_limit``.

        Args:
            player_id: The player receiving bonus.
            amount: Hearts to grant.
            source: Source of bonus.
            idempotency_key: Optional key to prevent duplicate grants.

        Returns:
            BonusGrantResult with new heart count and grant status.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If amount < 1.
        """
        ...

    async def refund_heart(
        self,
        player_id: PlayerId,
        amount: int = 1,
        reason: str = "match_cancelled",
    ) -> EnergyInfo:
        """Refund hearts (e.g., match cancelled).

        Respects max_hearts cap.

        Args:
            player_id: The player to refund.
            amount: Hearts to refund.
            reason: Reason for refund (for logging).

        Returns:
            Updated EnergyInfo.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...
