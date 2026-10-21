"""Matchmaking module types.

Defines enums and dataclasses for the matchmaking queue system:
pool types, matchmaking status, queue entries, queue status,
matchmaking results, and queue statistics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.core.types.game import MatchId, PlayerId


class PoolType(Enum):
    """Matchmaking queue pool types."""

    HUMAN = "human"  # Human players only
    BOT = "bot"  # Bot players only
    MIXED = "mixed"  # Humans and bots together


class MatchmakingStatus(Enum):
    """Result status of a matchmaking attempt."""

    MATCHED = "matched"  # Found opponent, match created
    SEARCHING = "searching"  # Still in queue, no opponent found
    EXPIRED = "expired"  # Queue timeout exceeded
    NOT_IN_QUEUE = "not_in_queue"  # Player not in queue
    ERROR = "error"  # Match creation failed


@dataclass
class QueueEntryData:
    """Raw queue entry data from Redis."""

    player_id: PlayerId
    elo_rating: int
    pool_type: PoolType
    joined_at: datetime
    last_expansion_at: datetime
    current_min_elo: int
    current_max_elo: int


@dataclass
class QueueEntry:
    """A player's entry in the matchmaking queue."""

    player_id: PlayerId
    player_username: str
    elo_rating: int
    pool_type: PoolType
    joined_at: datetime
    current_elo_range: tuple[int, int]  # (min_elo, max_elo) being searched
    estimated_wait_seconds: int | None
    position_in_queue: int  # 1-indexed position


@dataclass
class QueueStatus:
    """Current queue status for a player."""

    player_id: PlayerId
    pool_type: PoolType
    elo_rating: int
    joined_at: datetime
    wait_time_seconds: int
    current_elo_range: tuple[int, int]
    potential_opponents: int  # Players in range
    position_in_queue: int
    estimated_wait_seconds: int | None


@dataclass
class MatchmakingResult:
    """Result of a matchmaking attempt."""

    status: MatchmakingStatus
    player_id: PlayerId
    opponent_id: PlayerId | None = None
    match_id: MatchId | None = None
    wait_time_seconds: int = 0
    elo_difference: int | None = None
    pool_type: PoolType = PoolType.MIXED
    message: str = ""


@dataclass
class QueueStats:
    """Statistics about matchmaking queues."""

    pool_type: PoolType | None
    total_players: int
    players_by_elo_bucket: dict[str, int]
    average_wait_seconds: float
    longest_wait_seconds: int
    matches_created_last_hour: int
    average_elo_difference: float
