"""Events module types -- enums and domain dataclasses.

Defines event lifecycle types, scoring models, entry requirements,
reward tiers, rules, and all output dataclasses returned by the
EventService public interface.

Note: ``EventId`` is imported from ``src.core.types.game`` and is NOT
redefined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from src.core.types.game import EventId, MatchId, PlayerId


class EventType(Enum):
    """Event duration categories."""

    FLASH = "flash"  # 2-4 hours
    WEEKLY = "weekly"  # ~7 days
    SEASONAL = "seasonal"  # 2-4 weeks


class EventStatus(Enum):
    """Event lifecycle states."""

    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ENDED = "ended"
    FINALIZED = "finalized"
    CANCELLED = "cancelled"


class ScoringType(Enum):
    """How event scores are calculated from match results."""

    TOTAL_SCORE = "total_score"  # Sum of all match scores
    BEST_MATCH = "best_match"  # Highest single match score
    MATCHES_PLAYED = "matches_played"  # Number of matches (participation)
    AVERAGE_SCORE = "average_score"  # Average score per match


# ---------------------------------------------------------------------------
# Supporting dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EntryRequirements:
    """Requirements a player must meet to join an event."""

    min_level: int | None = None
    min_elo: int | None = None
    max_elo: int | None = None
    energy_cost: int = 0
    player_types: list[str] | None = None  # e.g. ['human', 'bot']


@dataclass
class RewardItem:
    """Single reward within a tier."""

    reward_type: str  # "artifact", "energy", "elo_bonus", "cosmetic"
    value: str | int  # artifact_type_id, heart count, elo points, cosmetic_id
    quantity: int = 1


@dataclass
class RewardTier:
    """Reward tier definition for rank/percentile ranges."""

    tier_id: str  # e.g. "gold", "silver", "bronze", "participation"
    name: str  # Display name
    description: str
    rank_min: int | None  # Min rank (1 = first place), None for percentile-based
    rank_max: int | None  # Max rank
    percentile_min: float | None  # Min percentile (0-100), e.g. 90 = top 10%
    percentile_max: float | None  # Max percentile
    rewards: list[RewardItem] = field(default_factory=list)


@dataclass
class BonusCondition:
    """Bonus scoring condition triggered by match stats."""

    condition_type: str  # "chain_length", "special_gems", "time_bonus"
    threshold: int
    bonus_points: int


@dataclass
class EventRules:
    """Event-specific rules and settings."""

    max_matches_per_player: int | None = None  # None = unlimited
    match_cooldown_minutes: int = 0
    scoring_multiplier: float = 1.0
    allowed_match_types: list[str] | None = None
    special_board_seed: int | None = None
    bonus_conditions: list[BonusCondition] | None = None


@dataclass
class MatchEventStats:
    """Stats from a match for event scoring."""

    chain_count: int
    gems_cleared: int
    special_gems_activated: int
    match_duration_seconds: int


# ---------------------------------------------------------------------------
# Output domain objects
# ---------------------------------------------------------------------------


@dataclass
class Event:
    """Complete event entity."""

    id: EventId
    name: str
    description: str
    event_type: EventType
    status: EventStatus
    scoring_type: ScoringType
    entry_requirements: EntryRequirements
    reward_tiers: list[RewardTier]
    rules: EventRules
    max_participants: int | None
    participant_count: int
    start_at: datetime
    end_at: datetime
    activated_at: datetime | None
    finalized_at: datetime | None
    created_at: datetime
    created_by: PlayerId | None  # Admin who created, None for system-generated


@dataclass
class EventSummary:
    """Abbreviated event info for lists."""

    id: EventId
    name: str
    event_type: EventType
    status: EventStatus
    participant_count: int
    start_at: datetime
    end_at: datetime
    time_remaining_seconds: int | None  # None if not active


@dataclass
class EventParticipant:
    """A player's participation in an event."""

    event_id: EventId
    player_id: PlayerId
    player_username: str
    joined_at: datetime
    total_score: int
    matches_played: int
    best_match_score: int
    average_score: float
    current_rank: int | None  # None if not yet ranked
    rewards_claimed: bool
    last_match_at: datetime | None


@dataclass
class LeaderboardEntry:
    """Single leaderboard entry."""

    rank: int
    player_id: PlayerId
    player_username: str
    score: int
    matches_played: int
    best_match_score: int
    reward_tier: str | None  # Which reward tier they qualify for


@dataclass
class EventLeaderboard:
    """Event leaderboard with rankings."""

    event_id: EventId
    event_name: str
    event_status: EventStatus
    total_participants: int
    entries: list[LeaderboardEntry]
    updated_at: datetime
    has_more: bool


@dataclass
class PlayerEventRank:
    """A player's rank and status in an event."""

    event_id: EventId
    player_id: PlayerId
    rank: int
    total_participants: int
    percentile: float  # e.g. 95.5 means top 4.5%
    score: int
    matches_played: int
    reward_tier: str | None
    points_to_next_tier: int | None


@dataclass
class PlayerEventSummary:
    """Summary of a player's participation in an event."""

    event_id: EventId
    event_name: str
    event_type: EventType
    event_status: EventStatus
    player_rank: int | None
    player_score: int
    matches_played: int
    reward_tier: str | None
    rewards_claimed: bool
    joined_at: datetime


@dataclass
class EventFinalizationResult:
    """Result of finalizing an event."""

    event_id: EventId
    total_participants: int
    rewards_distributed: int
    reward_summary: dict[str, int]  # tier_name -> count
    top_players: list[LeaderboardEntry]  # Top 10
    finalized_at: datetime


@dataclass
class ScheduledEventResult:
    """Result of processing scheduled events."""

    activated: list[EventId]
    deactivated: list[EventId]
    finalized: list[EventId]
    processed_at: datetime
