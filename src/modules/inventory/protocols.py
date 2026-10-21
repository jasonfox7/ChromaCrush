"""Inventory service protocol.

Defines the public interface for the inventory module. All methods are
``async def`` because they involve database operations.

Other modules and the presentation layer depend on this protocol
interface; the concrete ``InventoryService`` implementation lives in
``src.modules.inventory.service``.
"""

from __future__ import annotations

from typing import Protocol

from src.core.types.game import PlayerId


class InventoryServiceProtocol(Protocol):
    """Public interface for the inventory module."""

    async def get_mega_counts(
        self,
        player_id: PlayerId,
    ) -> dict[int, int]:
        """Return {slot_index: count} for all 5 slots.

        Args:
            player_id: The player whose inventory to query.

        Returns:
            Dict mapping slot_index (0-4) to mega gem count.
        """
        ...

    async def consume_mega(
        self,
        player_id: PlayerId,
        slot_index: int,
    ) -> bool:
        """Consume one mega gem from a slot.

        Args:
            player_id: The player consuming the mega gem.
            slot_index: The slot to consume from (0-4).

        Returns:
            True if the mega gem was successfully consumed.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if slot_index is out of range.
            AppError: INSUFFICIENT_MEGA_GEMS if the slot count is 0.
        """
        ...

    async def grant_mega(
        self,
        player_id: PlayerId,
        slot_index: int,
        amount: int = 1,
    ) -> None:
        """Add mega gems to a slot.

        Args:
            player_id: The player receiving mega gems.
            slot_index: The slot to add to (0-4).
            amount: Number of mega gems to grant (default 1).

        Raises:
            AppError: VALIDATION_INVALID_INPUT if slot_index or amount is invalid.
        """
        ...
