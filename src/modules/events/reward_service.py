"""Event reward sub-service.

Handles granting rewards to players during event finalization,
including artifact, energy, and ELO bonus reward types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.types.game import EventId, PlayerId
from src.modules.energy.dto import BonusSource
from src.modules.events._data_mapper import parse_reward_tiers
from src.modules.events.leaderboard_service import LeaderboardService
from src.modules.events.types import RewardItem, RewardTier

if TYPE_CHECKING:
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.events.protocols import (
        EnergyServiceProtocol,
        PlayerServiceProtocol,
        VaultServiceProtocol,
    )


class RewardService:
    """Grants rewards to event participants."""

    def __init__(
        self,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        vault_service: VaultServiceProtocol,
        energy_service: EnergyServiceProtocol,
        player_service: PlayerServiceProtocol,
    ) -> None:
        self._logger = logger
        self._errors = errors
        self._vault_service = vault_service
        self._energy_service = energy_service
        self._player_service = player_service

    def determine_reward_tier(
        self,
        rank: int | None,
        total_participants: int,
        tiers: list[RewardTier],
    ) -> RewardTier | None:
        """Determine which reward tier a participant qualifies for."""
        return LeaderboardService._determine_reward_tier(
            rank,
            total_participants,
            tiers,
        )

    async def grant_reward(
        self,
        player_id: PlayerId,
        reward: RewardItem,
        event_id: EventId,
    ) -> None:
        """Grant a single reward to a player."""
        if reward.reward_type == "artifact":
            for _ in range(reward.quantity):
                await self._vault_service.add_artifact(
                    player_id=player_id,
                    artifact_type_id=str(reward.value),
                    source="event_reward",
                    source_id=str(event_id),
                )
        elif reward.reward_type == "energy":
            await self._energy_service.grant_bonus_hearts(
                player_id=player_id,
                amount=int(reward.value) * reward.quantity,
                source=BonusSource.EVENT_REWARD,
                idempotency_key=f"event:{event_id}:player:{player_id}:energy",
            )
        elif reward.reward_type == "elo_bonus":
            current_elo = await self._player_service.get_elo(player_id)
            await self._player_service.update_elo(
                player_id,
                current_elo + int(reward.value),
            )
