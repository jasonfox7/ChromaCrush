"""Player service protocol.

Defines the public interface for the player module. All methods are
``async def`` because they involve database operations.

Other modules and the presentation layer depend on this protocol
interface; the concrete ``PlayerService`` implementation lives in
``src.modules.player.service``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from src.core.types.game import PlayerId
from src.core.types.player import EnergyState, Player, PlayerStats, PlayerType

if TYPE_CHECKING:
    from src.modules.player.dto import EnergyStateUpdate, PaginatedResult, PlayerUpdate


class PlayerServiceProtocol(Protocol):
    """Public interface for the player module."""

    # ========== Player Account Operations ==========

    async def create_player(
        self,
        username: str,
        player_type: PlayerType,
        password_hash: str | None = None,
        email: str | None = None,
        apple_user_id: str | None = None,
        auth_provider: str | None = None,
    ) -> Player:
        """Create a new player account.

        Args:
            username: Unique username (case-insensitive, 3-32 chars, alphanumeric + underscore).
            player_type: PlayerType.HUMAN or PlayerType.BOT.
            password_hash: Required for humans (None allowed for CLI/testing), must be None for bots.
            email: Optional email for humans, None for bots.

        Returns:
            Created Player entity.

        Raises:
            VALIDATION_INVALID_INPUT: If username format is invalid or bot has password_hash.
            CONFLICT_USERNAME_TAKEN: If username already exists (case-insensitive).
        """
        ...

    async def get_player(
        self,
        player_id: PlayerId,
    ) -> Player:
        """Get player by ID.

        Args:
            player_id: The player's unique identifier.

        Returns:
            Player entity.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist or is soft-deleted.
        """
        ...

    async def get_player_by_username(
        self,
        username: str,
    ) -> Player | None:
        """Get player by username (case-insensitive lookup).

        Args:
            username: The username to look up.

        Returns:
            Player if found and not soft-deleted, None otherwise.
        """
        ...

    async def get_player_by_apple_id(
        self,
        apple_user_id: str,
    ) -> Player | None:
        """Get player by Apple user ID.

        Args:
            apple_user_id: The Apple ``sub`` claim.

        Returns:
            Player if found, None otherwise.
        """
        ...

    async def update_player(
        self,
        player_id: PlayerId,
        updates: PlayerUpdate,
    ) -> Player:
        """Update player profile fields.

        Args:
            player_id: The player to update.
            updates: Fields to update (username, email).

        Returns:
            Updated Player entity.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If new username format is invalid.
            CONFLICT_USERNAME_TAKEN: If new username conflicts with existing.
        """
        ...

    async def soft_delete_player(
        self,
        player_id: PlayerId,
    ) -> None:
        """Soft-delete a player account.

        Sets deleted_at timestamp. Username is released by appending
        deletion timestamp suffix.

        Args:
            player_id: The player to delete.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist or already deleted.
        """
        ...

    async def list_players(
        self,
        player_type: PlayerType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[Player]:
        """List players with optional filtering.

        Args:
            player_type: Filter by human or bot (None for all).
            limit: Maximum results (1-100, default 50).
            offset: Pagination offset.

        Returns:
            PaginatedResult containing players and pagination metadata.

        Raises:
            VALIDATION_INVALID_INPUT: If limit out of range.
        """
        ...

    # ========== ELO Rating Operations ==========

    async def get_elo(
        self,
        player_id: PlayerId,
    ) -> int:
        """Get player's current ELO rating.

        Args:
            player_id: The player.

        Returns:
            Current ELO rating integer.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def update_elo(
        self,
        player_id: PlayerId,
        new_rating: int,
    ) -> Player:
        """Update player's ELO rating.

        Args:
            player_id: The player to update.
            new_rating: New ELO value (must be >= 0).

        Returns:
            Updated Player entity.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If new_rating < 0.
        """
        ...

    async def calculate_elo_change(
        self,
        winner_id: PlayerId,
        loser_id: PlayerId,
        is_draw: bool = False,
    ) -> tuple[int, int]:
        """Calculate ELO changes for a match outcome (does NOT persist).

        Args:
            winner_id: The winning player (or either player if draw).
            loser_id: The losing player (or other player if draw).
            is_draw: Whether the match was a draw.

        Returns:
            Tuple of (winner_elo_change, loser_elo_change).

        Raises:
            NOT_FOUND_PLAYER: If either player doesn't exist.
            VALIDATION_INVALID_INPUT: If both IDs are the same player.
        """
        ...

    # ========== Statistics Operations ==========

    async def get_stats(
        self,
        player_id: PlayerId,
    ) -> PlayerStats:
        """Get player statistics.

        Args:
            player_id: The player.

        Returns:
            PlayerStats aggregate.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def record_match_result(
        self,
        player_id: PlayerId,
        won: bool,
        is_draw: bool,
        score: int,
        longest_chain: int,
        gems_matched: int,
    ) -> PlayerStats:
        """Record a match result in player statistics.

        Args:
            player_id: The player.
            won: Whether player won (ignored if is_draw).
            is_draw: Whether match was a draw.
            score: Player's final score in the match.
            longest_chain: Longest cascade chain achieved.
            gems_matched: Total gems matched in the match.

        Returns:
            Updated PlayerStats.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Energy State Data Access ==========

    async def get_energy_state(
        self,
        player_id: PlayerId,
    ) -> EnergyState:
        """Get player's energy state.

        Args:
            player_id: The player.

        Returns:
            Current EnergyState.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def update_energy_state(
        self,
        player_id: PlayerId,
        energy_update: EnergyStateUpdate,
    ) -> EnergyState:
        """Update player's energy state.

        Args:
            player_id: The player.
            energy_update: Fields to update.

        Returns:
            Updated EnergyState.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If hearts < 0 or > max_hearts.
        """
        ...

    async def initialize_energy_state(
        self,
        player_id: PlayerId,
    ) -> EnergyState:
        """Initialize energy state for new player.

        Called internally during player creation. Sets up default
        energy state (max hearts, current timestamp, zero streak).

        Args:
            player_id: The newly created player.

        Returns:
            Initialized EnergyState.
        """
        ...
