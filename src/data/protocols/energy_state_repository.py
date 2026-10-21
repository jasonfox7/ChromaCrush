"""Repository protocol for energy state data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.energy_state_repository``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from src.core.types.player import EnergyState


class EnergyStateRepositoryProtocol(Protocol):
    """Async repository interface for energy state persistence.

    All methods are ``async`` and work with the domain ``EnergyState`` type.
    The implementation manages its own session lifecycle through the
    injected ``DataContextProtocol``.
    """

    async def find_by_player_id(self, player_id: UUID) -> EnergyState | None:
        """Find energy state by player UUID.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The ``EnergyState`` domain object, or ``None`` if not found.
        """
        ...

    async def create(
        self,
        player_id: UUID,
        hearts: int,
        max_hearts: int,
    ) -> EnergyState:
        """Create a new energy state record.

        Args:
            player_id: The player's unique identifier.
            hearts: Initial hearts count.
            max_hearts: Maximum hearts capacity.

        Returns:
            The newly created ``EnergyState`` domain object.
        """
        ...

    async def update(self, player_id: UUID, **changes: object) -> EnergyState:
        """Update an existing player's energy state.

        Args:
            player_id: The player's unique identifier.
            **changes: Keyword arguments of field names and new values.

        Returns:
            The updated ``EnergyState`` domain object.

        Raises:
            AppError (NOT_FOUND_PLAYER): If the energy state does not exist.
        """
        ...
