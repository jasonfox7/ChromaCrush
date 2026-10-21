"""Inventory service -- mega gem inventory management.

Manages mega gem inventory slots for players. Each player has 5 slots:
slots 0-3 for mega gem types (encoded as mega values 14, 24, 34, 44)
and slot 4 for shuffle tokens.

Dependencies are injected via ``__init__`` -- no direct imports of
core service implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.types.game import PlayerId

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.repositories.mega_gem_inventory_repository import (
        SQLAlchemyMegaGemInventoryRepository,
    )

# Slot index -> mega value mapping.
# Slots 0-3 correspond to mega gem types, slot 4 is shuffle.
SLOT_MEGA_VALUES: dict[int, int] = {0: 11, 1: 22, 2: 33, 3: 44, 4: -1}


class InventoryService:
    """Manages mega gem inventory for players.

    Provides methods to query, consume, and grant mega gems across
    5 inventory slots per player.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        inventory_repo: SQLAlchemyMegaGemInventoryRepository,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._inventory_repo = inventory_repo

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_mega_counts(self, player_id: PlayerId) -> dict[int, int]:
        """Return {slot_index: count} for all 5 slots.

        Ensures all slots exist before querying, so new players
        automatically get initialized with zero counts.

        Args:
            player_id: The player whose inventory to query.

        Returns:
            Dict mapping slot_index (0-4) to mega gem count.
        """
        self._logger.debug("Getting mega gem counts", player_id=str(player_id))

        await self._inventory_repo.ensure_slots(player_id)
        records = await self._inventory_repo.get_inventory(player_id)

        counts = {record.slot_index: record.count for record in records}

        self._logger.debug(
            "Mega gem counts retrieved",
            player_id=str(player_id),
            counts=counts,
        )

        return counts

    async def consume_mega(self, player_id: PlayerId, slot_index: int) -> bool:
        """Consume one mega gem from a slot.

        Validates the slot index and atomically decrements the count.

        Args:
            player_id: The player consuming the mega gem.
            slot_index: The slot to consume from (0-4).

        Returns:
            True if the mega gem was successfully consumed.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if slot_index is out of range.
            AppError: INSUFFICIENT_MEGA_GEMS if the slot count is 0.
        """
        self._logger.debug(
            "Consuming mega gem",
            player_id=str(player_id),
            slot_index=slot_index,
        )

        if slot_index not in SLOT_MEGA_VALUES:
            raise self._errors.validation(
                f"Invalid slot index: {slot_index}. Must be 0-4.",
                code="VALIDATION_INVALID_INPUT",
                slot_index=slot_index,
            )

        consumed = await self._inventory_repo.consume_one(player_id, slot_index)

        if not consumed:
            raise self._errors.forbidden(
                f"Insufficient mega gems in slot {slot_index}",
                code="INSUFFICIENT_MEGA_GEMS",
                player_id=str(player_id),
                slot_index=slot_index,
            )

        self._logger.debug(
            "Mega gem consumed",
            player_id=str(player_id),
            slot_index=slot_index,
        )

        return True

    async def grant_mega(
        self, player_id: PlayerId, slot_index: int, amount: int = 1
    ) -> None:
        """Add mega gems to a slot.

        Validates the slot index and amount, then atomically increments
        the count (upserting the row if it doesn't exist).

        Args:
            player_id: The player receiving mega gems.
            slot_index: The slot to add to (0-4).
            amount: Number of mega gems to grant (default 1).

        Raises:
            AppError: VALIDATION_INVALID_INPUT if slot_index or amount is invalid.
        """
        self._logger.debug(
            "Granting mega gems",
            player_id=str(player_id),
            slot_index=slot_index,
            amount=amount,
        )

        if slot_index not in SLOT_MEGA_VALUES:
            raise self._errors.validation(
                f"Invalid slot index: {slot_index}. Must be 0-4.",
                code="VALIDATION_INVALID_INPUT",
                slot_index=slot_index,
            )

        if amount < 1:
            raise self._errors.validation(
                f"Invalid amount: {amount}. Must be >= 1.",
                code="VALIDATION_INVALID_INPUT",
                amount=amount,
            )

        await self._inventory_repo.add_count(player_id, slot_index, amount)

        self._logger.debug(
            "Mega gems granted",
            player_id=str(player_id),
            slot_index=slot_index,
            amount=amount,
        )
