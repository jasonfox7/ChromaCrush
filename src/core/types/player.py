"""Player types for ChromaCrush.

Defines the player entity, player statistics, and energy (hearts) state.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum

from src.core.types.game import PlayerId


class PlayerType(Enum):
    """Distinguishes human players from bot players."""

    HUMAN = "human"
    BOT = "bot"


@dataclass
class Player:
    """Core player entity."""

    id: PlayerId
    username: str
    player_type: PlayerType
    elo_rating: int = 1000
    campaign_level: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_bot(self) -> bool:
        return self.player_type == PlayerType.BOT


@dataclass
class PlayerStats:
    """Aggregate statistics for a player."""

    player_id: PlayerId
    total_matches: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    highest_score: int = 0
    longest_chain: int = 0
    total_gems_matched: int = 0

    @property
    def win_rate(self) -> float:
        if self.total_matches == 0:
            return 0.0
        return self.wins / self.total_matches


@dataclass
class EnergyState:
    """Player's energy (hearts) state."""

    player_id: PlayerId
    hearts: int = 7
    max_hearts: int = 7
    last_regen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    daily_streak: int = 0
    last_login_date: date | None = None
