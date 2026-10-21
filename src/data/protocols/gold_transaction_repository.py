"""Repository protocol for gold transaction ledger data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.gold_transaction_repository``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass
class GoldTransactionRecord:
    """Lightweight record returned by the gold transaction repository."""

    id: UUID
    player_id: UUID
    tx_type: str
    amount: int
    balance_after: int
    source: str
    reference_id: str | None
    created_at: datetime


class GoldTransactionRepositoryProtocol(Protocol):
    """Async repository interface for gold transaction ledger."""

    async def create(
        self,
        player_id: UUID,
        tx_type: str,
        amount: int,
        balance_after: int,
        source: str,
        reference_id: str | None = None,
    ) -> GoldTransactionRecord:
        """Record a gold transaction in the ledger.

        Args:
            player_id: The player's unique identifier.
            tx_type: Transaction type — 'purchase', 'earned', 'spent', 'refund'.
            amount: Gold amount (positive = credit, negative = debit).
            balance_after: Player's balance after this transaction.
            source: What caused the transaction (e.g. 'iap:chromacrush_gold_1500').
            reference_id: Optional external reference (Apple transaction_id, item_id).

        Returns:
            The newly created ledger record.
        """
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GoldTransactionRecord]:
        """Retrieve transaction history for a player, newest first.

        Args:
            player_id: The player's unique identifier.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            List of transaction records ordered by created_at descending.
        """
        ...

    async def find_by_reference(
        self,
        reference_id: str,
    ) -> GoldTransactionRecord | None:
        """Find a transaction by its external reference ID.

        Used for idempotency checks (e.g. duplicate Apple transaction_id).

        Args:
            reference_id: The external reference identifier.

        Returns:
            The matching record, or ``None`` if not found.
        """
        ...
