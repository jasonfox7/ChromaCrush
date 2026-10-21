"""Repository protocol for player data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.player_repository``.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from src.core.types.player import Player, PlayerType


class PlayerRepositoryProtocol(Protocol):
    """Async repository interface for player persistence.

    All methods are ``async`` and work with the domain ``Player`` type.
    The implementation manages its own session lifecycle through the
    injected ``DataContextProtocol``.
    """

    async def find_by_id(self, player_id: UUID) -> Player | None:
        """Find a player by their UUID.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The ``Player`` domain object, or ``None`` if not found.
        """
        ...

    async def find_by_username(self, username: str) -> Player | None:
        """Find a player by their unique username.

        Args:
            username: The player's display name.

        Returns:
            The ``Player`` domain object, or ``None`` if not found.
        """
        ...

    async def create(
        self,
        username: str,
        player_type: PlayerType,
        password_hash: str | None = None,
    ) -> Player:
        """Create a new player.

        Args:
            username: Unique display name for the player.
            player_type: ``PlayerType.HUMAN`` or ``PlayerType.BOT``.
            password_hash: Bcrypt hash of the player's password (optional for bots).

        Returns:
            The newly created ``Player`` domain object.
        """
        ...

    async def update(self, player_id: UUID, **changes: Any) -> Player:
        """Update an existing player's attributes.

        Args:
            player_id: The player's unique identifier.
            **changes: Keyword arguments of column names and new values.

        Returns:
            The updated ``Player`` domain object.

        Raises:
            AppError (NOT_FOUND_RESOURCE): If the player does not exist.
        """
        ...

    async def delete(self, player_id: UUID) -> None:
        """Delete a player by their UUID.

        Args:
            player_id: The player's unique identifier.

        Raises:
            AppError (NOT_FOUND_RESOURCE): If the player does not exist.
        """
        ...

    async def list_players(
        self,
        player_type: PlayerType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Player], int]:
        """List players with optional type filtering and pagination.

        Args:
            player_type: Filter by ``PlayerType.HUMAN`` or ``PlayerType.BOT``
                (``None`` for all).
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            Tuple of (items, total_count).
        """
        ...
