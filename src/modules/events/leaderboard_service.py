"""Event leaderboard sub-service.

Handles leaderboard retrieval (Redis with DB fallback), player rank
lookup, and tier progression calculation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from src.core.types.game import EventId, PlayerId
from src.modules.events._data_mapper import parse_reward_tiers
from src.modules.events.types import (
    EventLeaderboard,
    EventStatus,
    LeaderboardEntry,
    PlayerEventRank,
    RewardTier,
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

_MAX_LEADERBOARD_LIMIT = 500


class LeaderboardService:
    """Retrieves leaderboards and player ranks for events."""

    def __init__(
        self,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        event_repo: EventRepositoryProtocol,
        participant_repo: EventParticipantRepositoryProtocol,
        leaderboard_repo: EventLeaderboardRepositoryProtocol,
    ) -> None:
        self._logger = logger
        self._errors = errors
        self._player_service = player_service
        self._event_repo = event_repo
        self._participant_repo = participant_repo
        self._leaderboard_repo = leaderboard_repo

    async def get_leaderboard(
        self,
        event_id: EventId,
        limit: int = 100,
        offset: int = 0,
    ) -> EventLeaderboard:
        """Get the current leaderboard for an event."""
        if limit < 1 or limit > _MAX_LEADERBOARD_LIMIT:
            raise self._errors.validation(
                f"Limit must be between 1 and {_MAX_LEADERBOARD_LIMIT}",
                code="VALIDATION_INVALID_INPUT",
                field="limit",
                max=_MAX_LEADERBOARD_LIMIT,
            )

        record = await self._event_repo.find_by_id(event_id)
        if record is None:
            raise self._errors.not_found(
                "Event not found",
                code="NOT_FOUND_EVENT",
                event_id=str(event_id),
            )

        # Try Redis first
        top_entries = await self._leaderboard_repo.get_top(event_id, limit, offset)
        total = await self._leaderboard_repo.get_total_count(event_id)

        # Fallback to database if Redis is empty
        if not top_entries and record.participant_count > 0:
            db_entries = await self._participant_repo.find_ranked_by_event(
                event_id,
                limit,
                offset,
            )
            entries = []
            for i, p in enumerate(db_entries):
                player = await self._player_service.get_player(PlayerId(p.player_id))
                entries.append(
                    LeaderboardEntry(
                        rank=offset + i + 1,
                        player_id=PlayerId(p.player_id),
                        player_username=player.username,
                        score=p.total_score,
                        matches_played=p.matches_played,
                        best_match_score=p.best_match_score,
                        reward_tier=p.reward_tier,
                    )
                )
            total = record.participant_count
        else:
            entries = []
            for player_id_str, score in top_entries:
                pid = PlayerId(UUID(player_id_str))
                player = await self._player_service.get_player(pid)
                participant = await self._participant_repo.find_by_event_and_player(
                    event_id,
                    UUID(player_id_str),
                )
                rank = await self._leaderboard_repo.get_rank(
                    event_id, UUID(player_id_str)
                )
                entries.append(
                    LeaderboardEntry(
                        rank=rank or 0,
                        player_id=pid,
                        player_username=player.username,
                        score=score,
                        matches_played=participant.matches_played if participant else 0,
                        best_match_score=(
                            participant.best_match_score if participant else 0
                        ),
                        reward_tier=participant.reward_tier if participant else None,
                    )
                )

        now = datetime.now(timezone.utc)
        has_more = offset + len(entries) < total

        return EventLeaderboard(
            event_id=event_id,
            event_name=record.name,
            event_status=EventStatus(record.status),
            total_participants=total,
            entries=entries,
            updated_at=now,
            has_more=has_more,
        )

    async def get_player_rank(
        self,
        event_id: EventId,
        player_id: PlayerId,
    ) -> PlayerEventRank:
        """Get a specific player's rank in an event."""
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

        rank = await self._leaderboard_repo.get_rank(event_id, player_id)
        total = await self._leaderboard_repo.get_total_count(event_id)
        percentile = await self._leaderboard_repo.get_percentile(event_id, player_id)
        score = await self._leaderboard_repo.get_score(event_id, player_id)

        # Determine reward tier
        reward_tiers = parse_reward_tiers(record.reward_tiers)
        tier = self._determine_reward_tier(rank, total, reward_tiers)
        tier_name = tier.tier_id if tier else None

        # Calculate points to next tier
        points_to_next = self._calculate_points_to_next_tier(
            rank,
            total,
            reward_tiers,
            score or 0,
        )

        return PlayerEventRank(
            event_id=event_id,
            player_id=player_id,
            rank=rank or 0,
            total_participants=total,
            percentile=percentile or 0.0,
            score=score or 0,
            matches_played=participant.matches_played,
            reward_tier=tier_name,
            points_to_next_tier=points_to_next,
        )

    @staticmethod
    def _determine_reward_tier(
        rank: int | None,
        total_participants: int,
        tiers: list[RewardTier],
    ) -> RewardTier | None:
        """Determine which reward tier a participant qualifies for."""
        if rank is None or total_participants == 0:
            return None

        percentile = ((total_participants - rank + 1) / total_participants) * 100

        for tier in tiers:
            if tier.rank_min is not None and tier.rank_max is not None:
                if tier.rank_min <= rank <= tier.rank_max:
                    return tier
            elif tier.percentile_min is not None and tier.percentile_max is not None:
                if tier.percentile_min <= percentile <= tier.percentile_max:
                    return tier
            elif tier.rank_min is not None and tier.rank_max is None:
                if rank >= tier.rank_min:
                    return tier
            elif tier.percentile_min is not None and tier.percentile_max is None:
                if percentile >= tier.percentile_min:
                    return tier

        return None

    @staticmethod
    def _calculate_points_to_next_tier(
        rank: int | None,
        total: int,
        tiers: list[RewardTier],
        current_score: int,
    ) -> int | None:
        """Calculate points to next higher tier. Returns None if already top."""
        if rank is None or not tiers:
            return None
        # Simplified: return None (exact calculation would require
        # knowing score of rank boundary player)
        return None
