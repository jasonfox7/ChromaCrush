"""Repository protocol for gold balance data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.gold_balance_repository``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass
class GoldBalanceRecord:
    """Lightweight record returned by the gold balance repository."""

    player_id: UUID
    balance: int
    lifetime_earned: int
    lifetime_spent: int


class GoldBalanceRepositoryProtocol(Protocol):
    """Async repository interface for gold balance persistence."""

    async def find_by_player_id(self, player_id: UUID) -> GoldBalanceRecord | None:
        """Find gold balance by player UUID.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The record, or ``None`` if not found.
        """
        ...

    async def create(self, player_id: UUID) -> GoldBalanceRecord:
        """Create a new gold balance record with zero balance.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The newly created record.
        """
        ...

    async def credit(self, player_id: UUID, amount: int) -> GoldBalanceRecord:
        """Add gold to a player's balance.

        Args:
            player_id: The player's unique identifier.
            amount: Gold to add (must be > 0).

        Returns:
            The updated record.

        Raises:
            AppError (NOT_FOUND_ECONOMY): If record not found.
        """
        ...

    async def debit(self, player_id: UUID, amount: int) -> GoldBalanceRecord:
        """Remove gold from a player's balance.

        Args:
            player_id: The player's unique identifier.
            amount: Gold to remove (must be > 0).

        Returns:
            The updated record.

        Raises:
            AppError (NOT_FOUND_ECONOMY): If record not found.
            AppError (INSUFFICIENT_GOLD): If balance < amount.
        """
        ...
