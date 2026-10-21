"""Match/game state types for ChromaCrush.

Defines the match lifecycle states, per-player match state, and full match state.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from src.core.types.board import BoardState
from src.core.types.game import MatchId, Move, PlayerId


class MatchType(Enum):
    """Match types with different rule sets."""

    STANDARD = "standard"
    COMPETITIVE = "competitive"
    CASUAL = "casual"
    TUTORIAL = "tutorial"


class MatchStatus(Enum):
    """Lifecycle status of a versus match."""

    PENDING = "pending"  # Waiting for opponent
    IN_PROGRESS = "in_progress"  # Active gameplay
    COMPLETED = "completed"  # Finished
    ABANDONED = "abandoned"  # Player disconnected/forfeited


@dataclass
class PlayerMatchState:
    """A single player's state within a match."""

    player_id: PlayerId
    score: int = 0
    moves_made: list[Move] = field(default_factory=list)
    moves_remaining: int = 20


@dataclass
class MatchState:
    """Complete state of a versus match.

    Both players share the same board and seed.
    """

    match_id: MatchId
    board_seed: int
    board: BoardState
    status: MatchStatus
    player1: PlayerMatchState
    player2: PlayerMatchState
    current_player_id: PlayerId | None  # None if match not started
    winner_id: PlayerId | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
