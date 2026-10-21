"""Match module types — match state, player state, and results.

Defines the core domain types for asynchronous versus match coordination.
All types are dataclasses representing match lifecycle and player progress.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from src.core.types.board import BoardState
from src.core.types.game import GemType, MatchId, Move, PlayerId, Position
from src.core.types.match import MatchType as MatchType  # noqa: F401
from src.modules.board.types import MoveProcessingResult
from src.modules.scoring.types import MoveScore
from src.modules.special_gems.types import SpecialGemEffect


class MatchStatus(Enum):
    """Match lifecycle states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass
class PlayerMatchState:
    """Individual player's state within a match.

    Tracks score, moves, board state, and statistics for one player.
    Not frozen because it is mutated as the match progresses.
    """

    player_id: PlayerId
    player_username: str
    is_bot: bool = False
    score: int = 0
    moves_made: int = 0
    moves_remaining: int = 20
    current_board: BoardState | None = None
    longest_chain: int = 0
    special_gems_created: int = 0
    special_gems_activated: int = 0
    total_gems_cleared: int = 0
    finished_at: datetime | None = None


@dataclass
class MatchState:
    """Complete state of a versus match.

    Represents the full match state including both players, board seed,
    status, and outcome. Not frozen because player states are mutated.

    Attributes:
        match_id: Unique match identifier.
        board_seed: Seed used to generate the initial board.
        initial_board: Starting board state (same for both players).
        status: Current lifecycle status.
        match_type: Rule set variant.
        player1: First player's state.
        player2: Second player's state.
        winner_id: Winner's player ID if match completed, None if draw/pending.
        forfeit_by: Player ID if match was forfeited.
        created_at: When the match was created.
        started_at: When both players joined.
        completed_at: When the match finished.
        timeout_at: When the match will auto-abandon if incomplete.
    """

    match_id: MatchId
    board_seed: int
    initial_board: BoardState | None
    status: MatchStatus
    match_type: MatchType
    player1: PlayerMatchState
    player2: PlayerMatchState
    winner_id: PlayerId | None = None
    forfeit_by: PlayerId | None = None
    raid_data: dict | None = None
    reward_data: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    timeout_at: datetime | None = None

    def get_player_state(self, player_id: PlayerId) -> PlayerMatchState | None:
        """Get state for a specific player.

        Args:
            player_id: The player to retrieve.

        Returns:
            PlayerMatchState for the specified player, or None if
            the player is not a participant in this match.
        """
        if self.player1.player_id == player_id:
            return self.player1
        if self.player2.player_id == player_id:
            return self.player2
        return None

    def get_opponent_state(self, player_id: PlayerId) -> PlayerMatchState | None:
        """Get opponent's state for a given player.

        Args:
            player_id: The requesting player.

        Returns:
            PlayerMatchState for the opponent, or None if
            the player is not a participant in this match.
        """
        if self.player1.player_id == player_id:
            return self.player2
        if self.player2.player_id == player_id:
            return self.player1
        return None

    @property
    def both_finished(self) -> bool:
        """Return True if both players have used all moves."""
        return self.player1.moves_remaining == 0 and self.player2.moves_remaining == 0

    def is_participant(self, player_id: PlayerId) -> bool:
        """Check if a player is participating in this match."""
        return player_id in (self.player1.player_id, self.player2.player_id)


@dataclass
class CardRaidResult:
    """Result of a post-match card raid attempt.

    Created by MatchFinalizer when a winner is determined.
    """

    occurred: bool = False
    stolen_card_id: int | None = None
    stolen_card_name: str | None = None
    victim_player_id: PlayerId | None = None
    thief_player_id: PlayerId | None = None
    was_shielded: bool = False
    card_unequipped: bool = False
    blocked_by_card: bool = False
    blocked_by_card_name: str | None = None


@dataclass
class MatchRewardResult:
    """Result of post-match card reward for the winner.

    Created by MatchFinalizer when a winner is determined.
    """

    awarded: bool = False
    cards: list[dict] = field(default_factory=list)  # [{card_id, name, rarity}]
    tier: str = ""  # "1_common", "2_common", "3_common", "1_rare", "1_epic"


@dataclass
class MoveSubmissionResult:
    """Result of submitting a move in a match.

    Contains the updated match state, move processing results, scoring,
    and metadata about match progression.

    Attributes:
        match_state: Updated match state after the move.
        move_result: Board processing result from BoardService.
        score_result: Scoring breakdown from ScoringService.
        special_effects: Special gem effects that occurred.
        points_earned: Total points added to player's score.
        move_number: 1-based move number for this player.
        moves_remaining: How many moves the player has left.
        match_completed: True if the match finished with this move.
        player_finished: True if this player has no moves left.
        winner_id: Winner if match_completed, None if draw/pending.
    """

    match_state: MatchState
    move_result: MoveProcessingResult
    score_result: MoveScore
    special_effects: list[SpecialGemEffect]
    points_earned: int
    move_number: int
    moves_remaining: int
    match_completed: bool
    player_finished: bool
    winner_id: PlayerId | None = None
    raid_result: CardRaidResult | None = None
    reward_result: MatchRewardResult | None = None


@dataclass
class MatchSummary:
    """Summary of a completed or in-progress match.

    Used for match history, leaderboard displays, and profile views.
    """

    match_id: MatchId
    opponent_id: PlayerId
    opponent_username: str
    player_score: int
    opponent_score: int
    won: bool | None  # None = draw or in-progress
    status: MatchStatus
    match_type: MatchType
    created_at: datetime
    completed_at: datetime | None


@dataclass
class MoveRecord:
    """Historical record of a single move in a match.

    Stores complete move details for replay, analysis, and verification.

    Attributes:
        move_number: 1-based move index for this player.
        player_id: Who made the move.
        move: The swap that was performed.
        board_before: Board state before the move.
        board_after: Board state after all cascades.
        score_earned: Points awarded for this move.
        chain_count: Number of cascade steps.
        gems_cleared: Total gems cleared across cascades.
        special_gems_created: List of (position, gem_type) created.
        special_gems_activated: Positions of activated special gems.
        timestamp: When the move was submitted.
    """

    move_number: int
    player_id: PlayerId
    move: Move
    board_before: BoardState
    board_after: BoardState
    score_earned: int
    chain_count: int
    gems_cleared: int
    special_gems_created: list[tuple[Position, GemType]]
    special_gems_activated: list[Position]
    timestamp: datetime


@dataclass
class PlayerBoardState:
    """Current board state and progress for a player in a match.

    Used to return a player's view of their active match state.
    """

    player_id: PlayerId
    board: BoardState
    moves_made: int
    moves_remaining: int
    score: int
    has_valid_moves: bool
