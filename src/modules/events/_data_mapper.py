"""Pure data-mapping functions for the events module.

Converts ORM records and raw JSONB data into typed domain objects.
These functions are stateless and carry no dependencies beyond the
domain types themselves.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.types.game import EventId, PlayerId
from src.modules.events.types import (
    BonusCondition,
    EntryRequirements,
    Event,
    EventParticipant,
    EventRules,
    EventStatus,
    EventSummary,
    EventType,
    RewardItem,
    RewardTier,
    ScoringType,
)


def record_to_event(record: Any) -> Event:
    """Convert ORM record to Event domain object."""
    return Event(
        id=EventId(record.id),
        name=record.name,
        description=record.description or "",
        event_type=EventType(record.event_type),
        status=EventStatus(record.status),
        scoring_type=ScoringType(record.scoring_type),
        entry_requirements=parse_requirements(record.entry_requirements),
        reward_tiers=parse_reward_tiers(record.reward_tiers),
        rules=parse_rules(record.rules),
        max_participants=record.max_participants,
        participant_count=record.participant_count,
        start_at=record.start_at,
        end_at=record.end_at,
        activated_at=record.activated_at,
        finalized_at=record.finalized_at,
        created_at=record.created_at,
        created_by=PlayerId(record.created_by) if record.created_by else None,
    )


def record_to_summary(record: Any, now: datetime) -> EventSummary:
    """Convert ORM record to EventSummary."""
    time_remaining = None
    if record.status == EventStatus.ACTIVE.value:
        delta = record.end_at - now
        time_remaining = max(0, int(delta.total_seconds()))

    return EventSummary(
        id=EventId(record.id),
        name=record.name,
        event_type=EventType(record.event_type),
        status=EventStatus(record.status),
        participant_count=record.participant_count,
        start_at=record.start_at,
        end_at=record.end_at,
        time_remaining_seconds=time_remaining,
    )


def build_participant(
    record: Any,
    player_username: str,
    event_record: Any,
    rank: int | None = None,
) -> EventParticipant:
    """Build EventParticipant from ORM records."""
    matches_played = record.matches_played
    total_score = record.total_score
    average_score = 0.0
    if matches_played > 0:
        scoring_type = ScoringType(event_record.scoring_type)
        if scoring_type == ScoringType.AVERAGE_SCORE:
            average_score = total_score / matches_played
        else:
            average_score = total_score / matches_played

    return EventParticipant(
        event_id=EventId(record.event_id),
        player_id=PlayerId(record.player_id),
        player_username=player_username,
        joined_at=record.joined_at,
        total_score=total_score,
        matches_played=matches_played,
        best_match_score=record.best_match_score,
        average_score=average_score,
        current_rank=rank if rank is not None else record.current_rank,
        rewards_claimed=record.rewards_claimed,
        last_match_at=record.last_match_at,
    )


def parse_requirements(data: dict | None) -> EntryRequirements:
    """Parse JSONB entry_requirements into typed dataclass."""
    if not data:
        return EntryRequirements()
    return EntryRequirements(
        min_level=data.get("min_level"),
        min_elo=data.get("min_elo"),
        max_elo=data.get("max_elo"),
        energy_cost=data.get("energy_cost", 0),
        player_types=data.get("player_types"),
    )


def parse_reward_tiers(data: list | None) -> list[RewardTier]:
    """Parse JSONB reward_tiers into typed dataclass list."""
    if not data:
        return []
    tiers = []
    for item in data:
        rewards = []
        for r in item.get("rewards", []):
            rewards.append(
                RewardItem(
                    reward_type=r.get("reward_type", ""),
                    value=r.get("value", ""),
                    quantity=r.get("quantity", 1),
                )
            )
        tiers.append(
            RewardTier(
                tier_id=item.get("tier_id", ""),
                name=item.get("name", ""),
                description=item.get("description", ""),
                rank_min=item.get("rank_min"),
                rank_max=item.get("rank_max"),
                percentile_min=item.get("percentile_min"),
                percentile_max=item.get("percentile_max"),
                rewards=rewards,
            )
        )
    return tiers


def parse_rules(data: dict | None) -> EventRules:
    """Parse JSONB rules into typed dataclass."""
    if not data:
        return EventRules()
    bonus_conditions = None
    raw_bonuses = data.get("bonus_conditions")
    if raw_bonuses:
        bonus_conditions = [
            BonusCondition(
                condition_type=b.get("condition_type", ""),
                threshold=b.get("threshold", 0),
                bonus_points=b.get("bonus_points", 0),
            )
            for b in raw_bonuses
        ]
    return EventRules(
        max_matches_per_player=data.get("max_matches_per_player"),
        match_cooldown_minutes=data.get("match_cooldown_minutes", 0),
        scoring_multiplier=data.get("scoring_multiplier", 1.0),
        allowed_match_types=data.get("allowed_match_types"),
        special_board_seed=data.get("special_board_seed"),
        bonus_conditions=bonus_conditions,
    )
