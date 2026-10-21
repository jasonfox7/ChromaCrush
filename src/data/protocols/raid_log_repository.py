"""Repository protocol for raid log data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.raid_log_repository``.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class RaidLogRepositoryProtocol(Protocol):
    """Async repository interface for raid history persistence."""

    async def create(
        self,
        attacker_id: UUID,
        defender_id: UUID,
        success: bool,
        artifact_id: UUID | None = None,
        artifact_type_id: str | None = None,
    ) -> Any:
        """Create a new raid log entry.

        Returns:
            The created record.
        """
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        as_attacker: bool = True,
        as_defender: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """Find raid logs involving a player.

        Args:
            player_id: The player.
            as_attacker: Include raids where player attacked.
            as_defender: Include raids where player defended.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            Tuple of (items, total_count).
        """
        ...

    async def find_last_raid_between(
        self,
        attacker_id: UUID,
        defender_id: UUID,
    ) -> Any | None:
        """Find the most recent raid from attacker to defender.

        Returns:
            A record-like object or None.
        """
        ...
