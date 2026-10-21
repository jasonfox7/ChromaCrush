"""Repository protocol for player statistics data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.player_stats_repository``.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.core.types.player import PlayerStats


class PlayerStatsRepositoryProtocol(Protocol):
    """Async repository interface for player statistics persistence.

    All methods are ``async`` and work with the domain ``PlayerStats`` type.
    The implementation manages its own session lifecycle through the
    injected ``DataContextProtocol``.
    """

    async def find_by_player_id(self, player_id: UUID) -> PlayerStats | None:
        """Find player statistics by player UUID.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The ``PlayerStats`` domain object, or ``None`` if not found.
        """
        ...

    async def create(self, player_id: UUID) -> PlayerStats:
        """Create a new player statistics record with default values.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The newly created ``PlayerStats`` domain object.
        """
        ...

    async def update(self, player_id: UUID, **changes: object) -> PlayerStats:
        """Update an existing player's statistics.

        Args:
            player_id: The player's unique identifier.
            **changes: Keyword arguments of field names and new values.

        Returns:
            The updated ``PlayerStats`` domain object.

        Raises:
            AppError (NOT_FOUND_PLAYER): If the player stats do not exist.
        """
        ...
