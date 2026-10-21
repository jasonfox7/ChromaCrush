"""Event service facade.

Thin delegation layer that preserves the ``EventServiceProtocol`` public
interface while routing all work to focused sub-services. Each public
method is a one-line (or near-one-line) delegation except ``finalize_event``
which orchestrates across sub-services and is the callback target for
``EventSchedulingService``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from src.core.types.game import EventId, MatchId, PlayerId
from src.modules.events._data_mapper import parse_reward_tiers
from src.modules.events.dto import (
    EventCreate,
    EventDbUpdate,
    EventUpdate,
    PaginatedResult,
    ParticipantUpdate,
)
from src.modules.events.leaderboard_service import LeaderboardService
from src.modules.events.lifecycle_service import EventLifecycleService
from src.modules.events.participation_service import ParticipationService
from src.modules.events.reward_service import RewardService
from src.modules.events.scheduling_service import EventSchedulingService
from src.modules.events.scoring_service import EventScoringService
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
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.events.protocols import (
        EnergyServiceProtocol,
        EventLeaderboardRepositoryProtocol,
        EventParticipantRepositoryProtocol,
        EventRepositoryProtocol,
        MatchServiceProtocol,
        PlayerServiceProtocol,
        VaultServiceProtocol,
    )


class EventService:
    """Concrete implementation of ``EventServiceProtocol``.

    Thin facade that delegates to focused sub-services:
      - ``EventLifecycleService`` — create, get, list, update, cancel
      - ``ParticipationService`` — join, leave, participant queries
      - ``EventScoringService`` — match recording and scoring
      - ``LeaderboardService`` — leaderboard and rank queries
      - ``RewardService`` — reward tier determination and granting
      - ``EventSchedulingService`` — background activation/deactivation

    Args:
        config: Configuration service for reading settings.
        logger: Structured logging service.
        errors: Error factory service.
        data_ctx: Database session and Redis access.
        vault_service: Vault module for artifact rewards.
        energy_service: Energy module for heart operations.
        match_service: Match module for match verification.
        player_service: Player module for player lookups.
        event_repository: Repository for event records.
        event_participant_repository: Repository for participant records.
        event_leaderboard_repository: Repository for Redis leaderboards.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        data_ctx: Any,
        vault_service: VaultServiceProtocol,
        energy_service: EnergyServiceProtocol,
        match_service: MatchServiceProtocol,
        player_service: PlayerServiceProtocol,
        event_repository: EventRepositoryProtocol,
        event_participant_repository: EventParticipantRepositoryProtocol,
        event_leaderboard_repository: EventLeaderboardRepositoryProtocol,
    ) -> None:
        # Keep direct refs needed by finalize_event
        self._logger = logger
        self._errors = errors
        self._event_repo = event_repository
        self._participant_repo = event_participant_repository
        self._leaderboard_repo = event_leaderboard_repository
        self._player_service = player_service

        # Cache config needed by finalize_event
        self._min_matches_for_rewards: int = config.get(
            "events.min_matches_for_rewards", 3
        )

        # Sub-services
        self._lifecycle = EventLifecycleService(
            logger=logger,
            errors=errors,
            energy_service=energy_service,
            event_repo=event_repository,
            participant_repo=event_participant_repository,
            leaderboard_repo=event_leaderboard_repository,
        )
        self._participation = ParticipationService(
            logger=logger,
            errors=errors,
            player_service=player_service,
            energy_service=energy_service,
            event_repo=event_repository,
            participant_repo=event_participant_repository,
            leaderboard_repo=event_leaderboard_repository,
            allow_leave_after_match=config.get("events.allow_leave_after_match", False),
        )
        self._scoring = EventScoringService(
            logger=logger,
            errors=errors,
            event_repo=event_repository,
            participant_repo=event_participant_repository,
            leaderboard_repo=event_leaderboard_repository,
            player_service=player_service,
        )
        self._leaderboard = LeaderboardService(
            logger=logger,
            errors=errors,
            player_service=player_service,
            event_repo=event_repository,
            participant_repo=event_participant_repository,
            leaderboard_repo=event_leaderboard_repository,
        )
        self._rewards = RewardService(
            logger=logger,
            errors=errors,
            vault_service=vault_service,
            energy_service=energy_service,
            player_service=player_service,
        )
        self._scheduling = EventSchedulingService(
            logger=logger,
            data_ctx=data_ctx,
            event_repo=event_repository,
            auto_finalize_delay=config.get("events.auto_finalize_delay_minutes", 15),
            facade=self,
        )

    # ========== Lifecycle ==========

    async def create_event(self, event_data: EventCreate) -> Event:
        """Create a new event (admin operation)."""
        return await self._lifecycle.create_event(event_data)

    async def get_event(self, event_id: EventId) -> Event:
        """Retrieve event details."""
        return await self._lifecycle.get_event(event_id)

    async def list_events(
        self,
        status: EventStatus | None = None,
        event_type: EventType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResult[EventSummary]:
        """List events with optional filtering."""
        return await self._lifecycle.list_events(status, event_type, limit, offset)

    async def get_active_events(self) -> list[Event]:
        """Get all currently active events."""
        return await self._lifecycle.get_active_events()

    async def update_event(
        self,
        event_id: EventId,
        updates: EventUpdate,
    ) -> Event:
        """Update event details (admin operation, limited fields)."""
        return await self._lifecycle.update_event(event_id, updates)

    async def cancel_event(self, event_id: EventId, reason: str) -> Event:
        """Cancel an event before completion (admin operation)."""
        return await self._lifecycle.cancel_event(event_id, reason)

    # ========== Participation ==========

    async def join_event(
        self,
        event_id: EventId,
        player_id: PlayerId,
    ) -> EventParticipant:
        """Register a player for an event."""
        return await self._participation.join_event(event_id, player_id)

    async def leave_event(
        self,
        event_id: EventId,
        player_id: PlayerId,
    ) -> None:
        """Withdraw a player from an event."""
        return await self._participation.leave_event(event_id, player_id)

    async def get_event_participant(
        self,
        event_id: EventId,
        player_id: PlayerId,
    ) -> EventParticipant:
        """Get a player's participation record for an event."""
        return await self._participation.get_event_participant(event_id, player_id)

    async def get_player_events(
        self,
        player_id: PlayerId,
        include_past: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResult[PlayerEventSummary]:
        """Get events a player is participating in or has participated in."""
        return await self._participation.get_player_events(
            player_id,
            include_past,
            limit,
            offset,
        )

    # ========== Scoring ==========

    async def record_event_match(
        self,
        event_id: EventId,
        player_id: PlayerId,
        match_id: MatchId,
        score: int,
        match_stats: MatchEventStats,
    ) -> EventParticipant:
        """Record a match played as part of an event."""
        return await self._scoring.record_event_match(
            event_id,
            player_id,
            match_id,
            score,
            match_stats,
        )

    # ========== Leaderboard ==========

    async def get_leaderboard(
        self,
        event_id: EventId,
        limit: int = 100,
        offset: int = 0,
    ) -> EventLeaderboard:
        """Get the current leaderboard for an event."""
        return await self._leaderboard.get_leaderboard(event_id, limit, offset)

    async def get_player_rank(
        self,
        event_id: EventId,
        player_id: PlayerId,
    ) -> PlayerEventRank:
        """Get a specific player's rank in an event."""
        return await self._leaderboard.get_player_rank(event_id, player_id)

    # ========== Finalization ==========

    async def finalize_event(self, event_id: EventId) -> EventFinalizationResult:
        """End an event and distribute rewards.

        This method remains on the facade because
        ``EventSchedulingService.process_scheduled_events`` calls back to it
        via the facade reference, avoiding circular imports.
        """
        record = await self._event_repo.find_by_id(event_id)
        if record is None:
            raise self._errors.not_found(
                "Event not found",
                code="NOT_FOUND_EVENT",
                event_id=str(event_id),
            )

        if record.status == EventStatus.FINALIZED.value:
            raise self._errors.conflict(
                "Event already finalized",
                code="CONFLICT_EVENT_ALREADY_FINALIZED",
                event_id=str(event_id),
                finalized_at=(
                    record.finalized_at.isoformat() if record.finalized_at else ""
                ),
            )

        if record.status not in (EventStatus.ENDED.value, EventStatus.ACTIVE.value):
            raise self._errors.conflict(
                "Event cannot be finalized",
                code="CONFLICT_EVENT_NOT_ACTIVE",
                event_id=str(event_id),
                current_status=record.status,
            )

        # Sync leaderboard to database
        await self._leaderboard_repo.sync_to_database(
            event_id,
            self._participant_repo,
        )

        # Get eligible participants
        eligible = await self._participant_repo.find_eligible_for_rewards(
            event_id,
            self._min_matches_for_rewards,
        )

        # Parse reward tiers
        reward_tiers = parse_reward_tiers(record.reward_tiers)
        total_participants = len(eligible)

        # Assign reward tiers and distribute
        reward_summary: dict[str, int] = {}
        rewards_distributed = 0

        for participant in eligible:
            tier = self._rewards.determine_reward_tier(
                participant.current_rank,
                total_participants,
                reward_tiers,
            )

            if tier is not None:
                for reward in tier.rewards:
                    await self._rewards.grant_reward(
                        PlayerId(participant.player_id),
                        reward,
                        event_id,
                    )
                    rewards_distributed += 1

                await self._participant_repo.update(
                    event_id,
                    participant.player_id,
                    ParticipantUpdate(
                        rewards_claimed=True,
                        reward_tier=tier.tier_id,
                    ),
                )

                reward_summary[tier.tier_id] = reward_summary.get(tier.tier_id, 0) + 1

                self._logger.info(
                    "Reward granted",
                    event_id=str(event_id),
                    player_id=str(participant.player_id),
                    reward_tier=tier.tier_id,
                )

        # Update event status
        now = datetime.now(timezone.utc)
        await self._event_repo.update(
            event_id,
            EventDbUpdate(status=EventStatus.FINALIZED.value, finalized_at=now),
        )

        # Get top players
        top_entries = await self._leaderboard_repo.get_top(event_id, 10)
        top_players = []
        for i, (player_id_str, score) in enumerate(top_entries):
            pid = PlayerId(UUID(player_id_str))
            player = await self._player_service.get_player(pid)
            participant = await self._participant_repo.find_by_event_and_player(
                event_id,
                UUID(player_id_str),
            )
            top_players.append(
                LeaderboardEntry(
                    rank=i + 1,
                    player_id=pid,
                    player_username=player.username,
                    score=score,
                    matches_played=participant.matches_played if participant else 0,
                    best_match_score=participant.best_match_score if participant else 0,
                    reward_tier=participant.reward_tier if participant else None,
                )
            )

        self._logger.info(
            "Event finalized",
            event_id=str(event_id),
            total_participants=total_participants,
            rewards_distributed=rewards_distributed,
        )

        return EventFinalizationResult(
            event_id=event_id,
            total_participants=total_participants,
            rewards_distributed=rewards_distributed,
            reward_summary=reward_summary,
            top_players=top_players,
            finalized_at=now,
        )

    # ========== Scheduling ==========

    async def process_scheduled_events(self) -> ScheduledEventResult:
        """Background operation to activate/deactivate events based on schedule."""
        return await self._scheduling.process_scheduled_events()
