"""Event scoring sub-service.

Handles recording match results against events, scoring calculation,
and bonus condition evaluation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.core.types.game import EventId, MatchId, PlayerId
from src.modules.events._data_mapper import build_participant, parse_rules
from src.modules.events.dto import EventMatchCreate, ParticipantUpdate
from src.modules.events.types import (
    BonusCondition,
    EventParticipant,
    EventStatus,
    MatchEventStats,
    ScoringType,
)

if TYPE_CHECKING:
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.events.protocols import (
        EventLeaderboardRepositoryProtocol,
        EventParticipantRepositoryProtocol,
        EventRepositoryProtocol,
        PlayerServiceProtocol,
    )


class EventScoringService:
    """Records match results against events and calculates scores."""

    def __init__(
        self,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        event_repo: EventRepositoryProtocol,
        participant_repo: EventParticipantRepositoryProtocol,
        leaderboard_repo: EventLeaderboardRepositoryProtocol,
        player_service: PlayerServiceProtocol,
    ) -> None:
        self._logger = logger
        self._errors = errors
        self._event_repo = event_repo
        self._participant_repo = participant_repo
        self._leaderboard_repo = leaderboard_repo
        self._player_service = player_service

    async def record_event_match(
        self,
        event_id: EventId,
        player_id: PlayerId,
        match_id: MatchId,
        score: int,
        match_stats: MatchEventStats,
    ) -> EventParticipant:
        """Record a match played as part of an event."""
        # 1. Validate event
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

        # 2. Validate participant
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

        # 3. Parse rules and check match limits
        rules = parse_rules(record.rules)

        if rules.max_matches_per_player is not None:
            if participant.matches_played >= rules.max_matches_per_player:
                raise self._errors.conflict(
                    "Maximum matches reached for this event",
                    code="CONFLICT_EVENT_NOT_ACTIVE",
                    event_id=str(event_id),
                    current_status="max_matches_reached",
                )

        # 4. Apply scoring multiplier and bonus conditions
        event_score = int(score * rules.scoring_multiplier)

        if rules.bonus_conditions:
            for bonus in rules.bonus_conditions:
                if self._check_bonus_condition(bonus, match_stats):
                    event_score += bonus.bonus_points

        # 5. Calculate new totals based on scoring type
        scoring_type = ScoringType(record.scoring_type)
        new_total = self._calculate_new_score(
            scoring_type,
            participant.total_score,
            participant.matches_played,
            event_score,
        )

        # 6. Update participant record
        now = datetime.now(timezone.utc)
        updated = await self._participant_repo.update(
            event_id,
            player_id,
            ParticipantUpdate(
                total_score=new_total,
                matches_played=participant.matches_played + 1,
                best_match_score=max(participant.best_match_score, event_score),
                last_match_at=now,
            ),
        )

        # Record the match entry
        await self._participant_repo.create_event_match(
            EventMatchCreate(
                event_id=event_id,
                player_id=player_id,
                match_id=match_id,
                score=event_score,
                chain_count=match_stats.chain_count,
                gems_cleared=match_stats.gems_cleared,
                special_gems_activated=match_stats.special_gems_activated,
            ),
        )

        # 7. Update leaderboard
        await self._leaderboard_repo.update_score(event_id, player_id, new_total)

        # 8. Get new rank
        new_rank = await self._leaderboard_repo.get_rank(event_id, player_id)

        if participant.current_rank != new_rank:
            self._logger.debug(
                "Leaderboard position changed",
                event_id=str(event_id),
                player_id=str(player_id),
                old_rank=participant.current_rank,
                new_rank=new_rank,
            )

        self._logger.debug(
            "Match recorded",
            event_id=str(event_id),
            player_id=str(player_id),
            match_id=str(match_id),
            score=event_score,
        )

        player = await self._player_service.get_player(player_id)
        return build_participant(updated, player.username, record, rank=new_rank)

    @staticmethod
    def _check_bonus_condition(
        bonus: BonusCondition,
        stats: MatchEventStats,
    ) -> bool:
        """Check if a bonus condition is met."""
        if bonus.condition_type == "chain_length":
            return stats.chain_count >= bonus.threshold
        if bonus.condition_type == "special_gems":
            return stats.special_gems_activated >= bonus.threshold
        if bonus.condition_type == "time_bonus":
            return stats.match_duration_seconds <= bonus.threshold
        return False

    @staticmethod
    def _calculate_new_score(
        scoring_type: ScoringType,
        current_total: int,
        matches_played: int,
        new_score: int,
    ) -> int:
        """Calculate new total based on scoring type."""
        if scoring_type == ScoringType.TOTAL_SCORE:
            return current_total + new_score
        elif scoring_type == ScoringType.BEST_MATCH:
            return max(current_total, new_score)
        elif scoring_type == ScoringType.MATCHES_PLAYED:
            return matches_played + 1
        elif scoring_type == ScoringType.AVERAGE_SCORE:
            # Store total; average calculated on display
            return current_total + new_score
        else:
            return current_total + new_score
