"""Repository protocol for match data access.

Modules depend on these protocol interfaces; the concrete SQLAlchemy
implementations live in ``src.data.repositories.match_repository``.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from src.data.models.match import MatchModel
    from src.data.models.match_move import MatchMoveModel
    from src.modules.match.dto import MatchCreate, MatchUpdate, MoveCreate


class MatchRepositoryProtocol(Protocol):
    """Async repository interface for match persistence.

    All methods are ``async`` and work with ``MatchModel`` ORM instances or DTOs.
    The implementation manages its own session lifecycle through the injected
    ``DataContextProtocol``.
    """

    async def create(self, data: MatchCreate) -> MatchModel:
        """Create a new match.

        Args:
            data: MatchCreate DTO with match initialization data.

        Returns:
            The newly created ``MatchModel`` ORM instance.
        """
        ...

    async def find_by_id(self, match_id: UUID) -> MatchModel | None:
        """Find a match by its UUID.

        Args:
            match_id: The match's unique identifier.

        Returns:
            The ``MatchModel`` ORM instance, or ``None`` if not found.
        """
        ...

    async def update(self, match_id: UUID, changes: MatchUpdate) -> MatchModel:
        """Update an existing match's attributes.

        Args:
            match_id: The match's unique identifier.
            changes: MatchUpdate DTO with fields to update.

        Returns:
            The updated ``MatchModel`` ORM instance.

        Raises:
            AppError (NOT_FOUND_RESOURCE): If the match does not exist.
        """
        ...

    async def find_active_by_player(self, player_id: UUID) -> list[MatchModel]:
        """Find all active matches for a player.

        Returns matches where status is 'pending' or 'in_progress' and
        the player is either player1 or player2.

        Args:
            player_id: The player's unique identifier.

        Returns:
            List of active ``MatchModel`` instances (may be empty).
        """
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[MatchModel], int]:
        """Find matches involving a player with optional status filter and pagination.

        Args:
            player_id: The player's unique identifier.
            status: Optional status filter (e.g., "completed", "abandoned").
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            Tuple of (items, total_count).
        """
        ...

    async def find_stale_matches(self, cutoff: datetime) -> list[MatchModel]:
        """Find matches that are in-progress but have exceeded their timeout deadline.

        Args:
            cutoff: Timestamp threshold -- matches with timeout_at < cutoff are stale.

        Returns:
            List of stale ``MatchModel`` instances.
        """
        ...

    async def bulk_abandon(self, match_ids: list[UUID]) -> int:
        """Mark multiple matches as abandoned.

        Updates the status to 'abandoned' for all provided match IDs.

        Args:
            match_ids: List of match UUIDs to abandon.

        Returns:
            Number of matches updated.
        """
        ...


class MatchMoveRepositoryProtocol(Protocol):
    """Async repository interface for match move persistence.

    All methods are ``async`` and work with ``MatchMoveModel`` ORM instances or DTOs.
    """

    async def create(self, data: MoveCreate) -> MatchMoveModel:
        """Record a new move in a match.

        Args:
            data: MoveCreate DTO with move details.

        Returns:
            The newly created ``MatchMoveModel`` ORM instance.
        """
        ...

    async def find_by_match(
        self,
        match_id: UUID,
        player_id: UUID | None = None,
    ) -> list[MatchMoveModel]:
        """Find all moves for a match, optionally filtered by player.

        Results are ordered by move_number ascending.

        Args:
            match_id: The match's unique identifier.
            player_id: Optional player filter -- if provided, only return moves by this player.

        Returns:
            List of ``MatchMoveModel`` instances (may be empty).
        """
        ...

    async def count_by_player(self, match_id: UUID, player_id: UUID) -> int:
        """Count the number of moves a player has made in a match.

        Args:
            match_id: The match's unique identifier.
            player_id: The player's unique identifier.

        Returns:
            Move count for the player in this match.
        """
        ...
