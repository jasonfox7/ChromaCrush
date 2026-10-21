"""Match module protocols — typing.Protocol interfaces.

Defines ``MatchServiceProtocol`` for dependent modules and presentation layer,
plus repository protocols for data access and minimal dependency protocols.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.core.types.board import BoardState
from src.core.types.game import MatchId, Move, PlayerId
from src.modules.match.dto import MatchCreate, MatchUpdate, MoveCreate, PaginatedResult
from src.modules.match.types import (
    MatchState,
    MatchSummary,
    MatchType,
    MoveRecord,
    MoveSubmissionResult,
    PlayerBoardState,
)


class MatchServiceProtocol(Protocol):
    """Public interface for the match module.

    All methods are ``async def`` because they involve database operations
    and cross-module coordination. Consumed by presentation layer and other
    modules via ``__init__`` injection.
    """

    async def create_match(
        self,
        player1_id: PlayerId,
        player2_id: PlayerId,
        board_seed: int | None = None,
        match_type: MatchType = MatchType.STANDARD,
    ) -> MatchState:
        """Create a new versus match.

        Generates a shared board seed, creates initial boards for both players,
        and persists the match record.

        Args:
            player1_id: First player.
            player2_id: Second player.
            board_seed: Optional seed for board generation (random if None).
            match_type: Rule set variant (default: STANDARD).

        Returns:
            Initial MatchState with PENDING status.

        Raises:
            VALIDATION_INVALID_INPUT: If player1_id == player2_id.
            NOT_FOUND_PLAYER: If either player doesn't exist.
        """
        ...

    async def submit_move(
        self,
        match_id: MatchId,
        player_id: PlayerId,
        move: Move,
    ) -> MoveSubmissionResult:
        """Submit a move for a player in an active match.

        Processes the move, updates board state, calculates score, handles
        special gems, persists move record, and checks for match completion.

        Args:
            match_id: The match.
            player_id: Who is making the move.
            move: The swap to perform.

        Returns:
            MoveSubmissionResult with updated match state and move details.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
            VALIDATION_INVALID_INPUT: If player not in match or out of moves.
            CONFLICT_MATCH_COMPLETED: If match already finished.
            VALIDATION_INVALID_GEM_SWAP: If move is invalid.
        """
        ...

    async def get_match(
        self,
        match_id: MatchId,
    ) -> MatchState:
        """Get current state of a match.

        Args:
            match_id: The match to retrieve.

        Returns:
            Current MatchState.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
        """
        ...

    async def get_player_board(
        self,
        match_id: MatchId,
        player_id: PlayerId,
    ) -> PlayerBoardState:
        """Get a player's current board state and progress.

        Args:
            match_id: The match.
            player_id: The player.

        Returns:
            PlayerBoardState with current board and move counts.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
            VALIDATION_INVALID_INPUT: If player not in match.
        """
        ...

    async def get_active_matches(
        self,
        player_id: PlayerId,
    ) -> list[MatchState]:
        """Get all active matches for a player.

        Returns matches with status PENDING or IN_PROGRESS.

        Args:
            player_id: The player.

        Returns:
            List of active MatchState objects.
        """
        ...

    async def get_match_history(
        self,
        player_id: PlayerId,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResult[MatchSummary]:
        """Get match history for a player.

        Args:
            player_id: The player.
            limit: Maximum results (1-100, default 20).
            offset: Pagination offset.

        Returns:
            PaginatedResult containing MatchSummary objects.
        """
        ...

    async def get_move_history(
        self,
        match_id: MatchId,
        player_id: PlayerId | None = None,
    ) -> list[MoveRecord]:
        """Get move history for a match, optionally filtered by player.

        Args:
            match_id: The match.
            player_id: If provided, return only moves by this player.

        Returns:
            List of MoveRecord objects in chronological order.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
        """
        ...

    async def activate_mega(
        self,
        match_id: MatchId,
        player_id: PlayerId,
        slot_index: int,
        source: str | None = None,
    ) -> MoveSubmissionResult:
        """Activate a banked mega gem or shuffle.

        Consumes one item from the player's inventory, places the mega
        gem on the board, fires it, cascades, and scores -- all without
        consuming a move. Slot 4 triggers a board shuffle instead.

        Args:
            match_id: The match.
            player_id: Who is activating.
            slot_index: 0-3 for mega gems, 4 for shuffle.
            source: Optional source tag (e.g. ``"void_instability"``).

        Returns:
            MoveSubmissionResult with updated state and cascade details.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
            FORBIDDEN_NOT_MATCH_PARTICIPANT: If player not in match.
            INSUFFICIENT_MEGA_GEMS: If slot is empty.
        """
        ...

    async def forfeit_match(
        self,
        match_id: MatchId,
        player_id: PlayerId,
    ) -> MatchState:
        """Forfeit a match, marking the opponent as winner.

        Args:
            match_id: The match.
            player_id: Who is forfeiting.

        Returns:
            Updated MatchState with COMPLETED status.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
            VALIDATION_INVALID_INPUT: If player not in match.
            CONFLICT_MATCH_COMPLETED: If match already finished.
        """
        ...

    async def abandon_stale_matches(self) -> int:
        """Abandon matches that have exceeded their timeout.

        Returns:
            Number of matches abandoned.
        """
        ...


class MatchRepositoryProtocol(Protocol):
    """Repository interface for match data access.

    All methods are ``async def``. Returns ORM models (MatchModel).
    """

    async def create(self, data: MatchCreate) -> Any:
        """Create a new match record.

        Args:
            data: Match creation data.

        Returns:
            MatchModel ORM instance.
        """
        ...

    async def find_by_id(self, match_id: UUID) -> Any | None:
        """Find match by ID.

        Args:
            match_id: Match identifier.

        Returns:
            MatchModel or None if not found.
        """
        ...

    async def update(self, match_id: UUID, changes: MatchUpdate) -> Any:
        """Update match record.

        Only updates fields that are not None in changes.

        Args:
            match_id: Match to update.
            changes: Fields to update.

        Returns:
            Updated MatchModel.

        Raises:
            ValueError: If match not found.
        """
        ...

    async def find_active_by_player(self, player_id: UUID) -> list[Any]:
        """Find all active matches for a player.

        Returns matches with status PENDING or IN_PROGRESS.

        Args:
            player_id: Player identifier.

        Returns:
            List of MatchModel objects.
        """
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """Find matches for a player with pagination.

        Args:
            player_id: Player identifier.
            status: Filter by status (optional).
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            Tuple of (list of MatchModel, total count).
        """
        ...

    async def find_stale_matches(self, cutoff: datetime) -> list[Any]:
        """Find matches that have timed out.

        Args:
            cutoff: Matches with timeout_at before this time.

        Returns:
            List of MatchModel objects.
        """
        ...

    async def bulk_abandon(self, match_ids: list[UUID]) -> int:
        """Mark multiple matches as ABANDONED atomically.

        Args:
            match_ids: Matches to abandon.

        Returns:
            Number of matches updated.
        """
        ...

    async def cleanup_match_data(self, match_id: UUID) -> None:
        """NULL out board states and raid data for a completed match.

        Args:
            match_id: The match to clean up.
        """
        ...


class MatchMoveRepositoryProtocol(Protocol):
    """Repository interface for match move data access.

    All methods are ``async def``. Returns ORM models (MatchMoveModel).
    """

    async def create(self, data: MoveCreate) -> Any:
        """Create a new move record.

        Args:
            data: Move creation data.

        Returns:
            MatchMoveModel ORM instance.
        """
        ...

    async def find_by_match(
        self,
        match_id: UUID,
        player_id: UUID | None = None,
    ) -> list[Any]:
        """Find all moves for a match, optionally filtered by player.

        Args:
            match_id: Match identifier.
            player_id: If provided, return only this player's moves.

        Returns:
            List of MatchMoveModel objects in chronological order.
        """
        ...

    async def count_by_player(self, match_id: UUID, player_id: UUID) -> int:
        """Count moves made by a player in a match.

        Args:
            match_id: Match identifier.
            player_id: Player identifier.

        Returns:
            Number of moves made.
        """
        ...

    async def delete_by_match_id(self, match_id: UUID) -> int:
        """Delete all move records for a match.

        Args:
            match_id: Match whose moves should be deleted.

        Returns:
            Number of records deleted.
        """
        ...


# Minimal dependency protocols for sync services


class BoardServiceProtocol(Protocol):
    """Minimal board service interface required by match module.

    Only synchronous methods used by match service.
    """

    def process_move(
        self,
        board: BoardState,
        move: Move,
        seed: int,
        modifiers: object | None = None,
    ) -> Any:
        """Process a move and return MoveProcessingResult.

        Args:
            board: Current board state.
            move: Move to process.
            seed: Random seed for deterministic gem spawning.
            modifiers: Optional CardModifierEngine for card effects.

        Returns:
            MoveProcessingResult from src.modules.board.types.
        """
        ...

    def process_mega_activation(
        self,
        board: BoardState,
        mega_value: int,
        seed: int,
        modifiers: object | None = None,
    ) -> Any:
        """Process a mega gem activation and return MoveProcessingResult.

        Places a mega gem at a random position, fires it, and runs cascades.

        Args:
            board: Current board state.
            mega_value: Mega gem value to place (14, 24, 34, or 44).
            seed: RNG seed for determinism.
            modifiers: Optional CardModifierEngine for card effects.

        Returns:
            MoveProcessingResult from src.modules.board.types.
        """
        ...

    def shuffle_board(self, board: BoardState, seed: int) -> BoardState:
        """Shuffle the board preserving gem counts and specials.

        Args:
            board: The board state to shuffle.
            seed: RNG seed for deterministic shuffling.

        Returns:
            A new BoardState with shuffled gem positions.
        """
        ...

    def has_valid_moves(self, board: BoardState) -> bool:
        """Check if board has any valid moves remaining.

        Args:
            board: Board state to check.

        Returns:
            True if at least one valid move exists.
        """
        ...


class ScoringServiceProtocol(Protocol):
    """Minimal scoring service interface required by match module."""

    def calculate_move_score(self, move_result: Any) -> Any:
        """Calculate score for a processed move.

        Args:
            move_result: MoveProcessingResult from board service.

        Returns:
            MoveScore from src.modules.scoring.types.
        """
        ...
