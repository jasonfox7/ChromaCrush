"""Repository protocol for player card data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.player_card_repository``.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class PlayerCardRepositoryProtocol(Protocol):
    """Async repository interface for player card persistence."""

    async def find_by_id(self, card_instance_id: UUID) -> Any | None:
        """Find a player card by UUID.

        Returns:
            A record-like object with id, player_id, card_id, position,
            acquired_at, source, source_id, level fields, or None.
        """
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """Find cards owned by a player, ordered by position.

        Returns:
            Tuple of (items, total_count).
        """
        ...

    async def find_equipped(self, player_id: UUID) -> list[Any]:
        """Find equipped cards (positions 1-3) for a player.

        Returns:
            List of records sorted by position.
        """
        ...

    async def count_by_player(self, player_id: UUID) -> int:
        """Count total cards owned by a player."""
        ...

    async def find_max_position(self, player_id: UUID) -> int:
        """Get the highest position value for a player's cards.

        Returns 0 if the player has no cards.
        """
        ...

    async def create(
        self,
        player_id: UUID,
        card_id: int,
        position: int,
        source: str,
        source_id: str | None = None,
    ) -> Any:
        """Create a new player card record.

        Returns:
            The created record.
        """
        ...

    async def update_position(
        self,
        card_instance_id: UUID,
        new_position: int,
    ) -> Any:
        """Update the position of a card.

        Returns:
            The updated record.
        """
        ...

    async def delete(self, card_instance_id: UUID) -> None:
        """Delete a player card record."""
        ...

    async def delete_multiple(self, card_instance_ids: list[UUID]) -> None:
        """Delete multiple player card records."""
        ...
