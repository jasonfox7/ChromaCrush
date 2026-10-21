"""Repository protocol for vault shield data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.vault_shield_repository``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


class VaultShieldRepositoryProtocol(Protocol):
    """Async repository interface for vault shield persistence."""

    async def find_by_player(self, player_id: UUID) -> Any | None:
        """Find the active shield for a player.

        Returns:
            A record-like object with player_id, activated_at, expires_at,
            duration_hours fields, or None.
        """
        ...

    async def create(
        self,
        player_id: UUID,
        activated_at: datetime,
        expires_at: datetime,
        duration_hours: int,
    ) -> Any:
        """Create a new shield record.

        Returns:
            The created record.
        """
        ...

    async def delete(self, player_id: UUID) -> None:
        """Delete a player's shield record."""
        ...

    async def delete_expired(self) -> int:
        """Delete all expired shields.

        Returns:
            Number of shields deleted.
        """
        ...
