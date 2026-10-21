"""Event participation sub-service.

Handles joining/leaving events, entry requirement validation,
player event listings, and participant lookups.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.core.types.game import EventId, PlayerId
from src.modules.events._data_mapper import build_participant, parse_requirements
from src.modules.events.dto import (
    PaginatedResult,
    ParticipantCreate,
    ParticipantUpdate,
)
from src.modules.events.types import (
    EntryRequirements,
    EventParticipant,
    EventStatus,
    EventType,
    PlayerEventSummary,
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
        PlayerServiceProtocol,
    )

_MAX_LIST_LIMIT = 100
_LEVEL_THRESHOLDS = [5, 20, 50, 100]


class ParticipationService:
    """Manages player participation in events."""

    def __init__(
        self,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        energy_service: EnergyServiceProtocol,
        event_repo: EventRepositoryProtocol,
        participant_repo: EventParticipantRepositoryProtocol,
        leaderboard_repo: EventLeaderboardRepositoryProtocol,
        allow_leave_after_match: bool,
    ) -> None:
        self._logger = logger
        self._errors = errors
        self._player_service = player_service
        self._energy_service = energy_service
        self._event_repo = event_repo
        self._participant_repo = participant_repo
        self._leaderboard_repo = leaderboard_repo
        self._allow_leave_after_match = allow_leave_after_match

    async def join_event(
        self,
        event_id: EventId,
        player_id: PlayerId,
    ) -> EventParticipant:
        """Register a player for an event."""
        # 1. Load and validate event
        record = await self._event_repo.find_by_id(event_id)
        if record is None:
            raise self._errors.not_found(
                "Event not found",
                code="NOT_FOUND_EVENT",
                event_id=str(event_id),
            )

        if record.status != EventStatus.ACTIVE.value:
            raise self._errors.conflict(
                "Event is not active",
                code="CONFLICT_EVENT_NOT_ACTIVE",
                event_id=str(event_id),
                current_status=record.status,
            )

        # 2. Check if already participating
        existing = await self._participant_repo.find_by_event_and_player(
            event_id,
            player_id,
        )
        if existing is not None and existing.left_at is None:
            raise self._errors.conflict(
                "Already participating in event",
                code="CONFLICT_ALREADY_PARTICIPANT",
                event_id=str(event_id),
                player_id=str(player_id),
                joined_at=existing.joined_at.isoformat(),
            )

        # 3. Validate player exists and get info
        player = await self._player_service.get_player(player_id)

        # 4. Check entry requirements
        requirements = parse_requirements(record.entry_requirements)
        await self._check_entry_requirements(player, requirements, event_id)

        # 5. Check capacity
        if record.max_participants is not None and record.max_participants > 0:
            if record.participant_count >= record.max_participants:
                raise self._errors.conflict(
                    "Event is at capacity",
                    code="CONFLICT_EVENT_AT_CAPACITY",
                    event_id=str(event_id),
                    max_participants=record.max_participants,
                )

        # 6. Consume entry energy if required
        if requirements.energy_cost > 0:
            await self._energy_service.consume_heart(
                player_id,
                amount=requirements.energy_cost,
            )

        # 7. Create participant record + increment count
        new_count = await self._event_repo.increment_participant_count(event_id)

        if (
            record.max_participants
            and record.max_participants > 0
            and new_count > record.max_participants
        ):
            # Race condition -- roll back
            await self._event_repo.decrement_participant_count(event_id)
            if requirements.energy_cost > 0:
                await self._energy_service.refund_heart(
                    player_id,
                    amount=requirements.energy_cost,
                    reason="event_full",
                )
            raise self._errors.conflict(
                "Event is at capacity",
                code="CONFLICT_EVENT_AT_CAPACITY",
                event_id=str(event_id),
                max_participants=record.max_participants,
            )

        participant = await self._participant_repo.create(
            ParticipantCreate(event_id=event_id, player_id=player_id),
        )

        # 8. Initialize on leaderboard
        await self._leaderboard_repo.update_score(event_id, player_id, 0)

        # 9. Log and return
        self._logger.info(
            "Player joined event",
            event_id=str(event_id),
            player_id=str(player_id),
            participant_count=new_count,
        )

        return build_participant(participant, player.username, record)

    async def leave_event(
        self,
        event_id: EventId,
        player_id: PlayerId,
    ) -> None:
        """Withdraw a player from an event."""
        record = await self._event_repo.find_by_id(event_id)
        if record is None:
            raise self._errors.not_found(
                "Event not found",
                code="NOT_FOUND_EVENT",
                event_id=str(event_id),
            )

        participant = await self._participant_repo.find_by_event_and_player(
            event_id,
            player_id,
        )
        if participant is None or participant.left_at is not None:
            raise self._errors.forbidden(
                "Not a participant in this event",
                code="FORBIDDEN_NOT_EVENT_PARTICIPANT",
                event_id=str(event_id),
                player_id=str(player_id),
            )

        # Check if leaving is allowed
        if participant.matches_played > 0 and not self._allow_leave_after_match:
            raise self._errors.forbidden(
                "Cannot leave event after playing matches",
                code="FORBIDDEN_CANNOT_LEAVE_EVENT",
                event_id=str(event_id),
                reason="matches_played",
            )

        now = datetime.now(timezone.utc)
        await self._participant_repo.update(
            event_id,
            player_id,
            ParticipantUpdate(left_at=now),
        )
        await self._event_repo.decrement_participant_count(event_id)
        await self._leaderboard_repo.remove_player(event_id, player_id)

        self._logger.info(
            "Player left event",
            event_id=str(event_id),
            player_id=str(player_id),
            reason="voluntary",
        )

    async def get_event_participant(
        self,
        event_id: EventId,
        player_id: PlayerId,
    ) -> EventParticipant:
        """Get a player's participation record for an event."""
        record = await self._event_repo.find_by_id(event_id)
        if record is None:
            raise self._errors.not_found(
                "Event not found",
                code="NOT_FOUND_EVENT",
                event_id=str(event_id),
            )

        participant = await self._participant_repo.find_by_event_and_player(
            event_id,
            player_id,
        )
        if participant is None:
            raise self._errors.forbidden(
                "Not a participant in this event",
                code="FORBIDDEN_NOT_EVENT_PARTICIPANT",
                event_id=str(event_id),
                player_id=str(player_id),
            )

        player = await self._player_service.get_player(player_id)
        return build_participant(participant, player.username, record)

    async def get_player_events(
        self,
        player_id: PlayerId,
        include_past: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResult[PlayerEventSummary]:
        """Get events a player is participating in or has participated in."""
        if limit < 1 or limit > _MAX_LIST_LIMIT:
            raise self._errors.validation(
                f"Limit must be between 1 and {_MAX_LIST_LIMIT}",
                code="VALIDATION_INVALID_INPUT",
                field="limit",
                max=_MAX_LIST_LIMIT,
            )

        # Verify player exists
        await self._player_service.get_player(player_id)

        records, total = await self._participant_repo.find_by_player(
            player_id,
            include_past=include_past,
            limit=limit,
            offset=offset,
        )

        summaries = []
        for p in records:
            event_record = await self._event_repo.find_by_id(p.event_id)
            if event_record is None:
                continue
            summaries.append(
                PlayerEventSummary(
                    event_id=EventId(p.event_id),
                    event_name=event_record.name,
                    event_type=EventType(event_record.event_type),
                    event_status=EventStatus(event_record.status),
                    player_rank=p.current_rank,
                    player_score=p.total_score,
                    matches_played=p.matches_played,
                    reward_tier=p.reward_tier,
                    rewards_claimed=p.rewards_claimed,
                    joined_at=p.joined_at,
                )
            )

        return PaginatedResult(
            items=summaries,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def _check_entry_requirements(
        self,
        player: Any,
        requirements: EntryRequirements,
        event_id: EventId,
    ) -> None:
        """Check if player meets entry requirements."""
        missing: list[str] = []

        if requirements.min_level is not None:
            stats = await self._player_service.get_stats(player.id)
            player_level = self._calculate_level(stats)
            if player_level < requirements.min_level:
                missing.append(f"level {requirements.min_level} required")

        if requirements.min_elo is not None:
            if player.elo_rating < requirements.min_elo:
                missing.append(f"ELO {requirements.min_elo} required")

        if requirements.max_elo is not None:
            if player.elo_rating > requirements.max_elo:
                missing.append(f"ELO below {requirements.max_elo} required")

        if requirements.player_types is not None:
            ptype = player.player_type
            ptype_str = ptype.value if hasattr(ptype, "value") else str(ptype)
            if ptype_str not in requirements.player_types:
                missing.append(f"player type must be {requirements.player_types}")

        if requirements.energy_cost > 0:
            energy_info = await self._energy_service.get_energy(player.id)
            if energy_info.current_hearts < requirements.energy_cost:
                raise self._errors.forbidden(
                    "Insufficient energy for event entry",
                    code="FORBIDDEN_INSUFFICIENT_ENERGY",
                    required=requirements.energy_cost,
                    available=energy_info.current_hearts,
                )

        if missing:
            raise self._errors.forbidden(
                "Entry requirements not met",
                code="FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET",
                event_id=str(event_id),
                player_id=str(player.id),
                missing_requirements=missing,
            )

    @staticmethod
    def _calculate_level(stats: Any) -> int:
        """Derive player level from total matches.

        Level thresholds are defined by ``_LEVEL_THRESHOLDS``.
        """
        total = getattr(stats, "total_matches", 0)
        for level, threshold in enumerate(_LEVEL_THRESHOLDS, start=1):
            if total < threshold:
                return level
        return len(_LEVEL_THRESHOLDS) + 1
