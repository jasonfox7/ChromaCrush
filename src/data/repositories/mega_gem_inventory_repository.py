"""SQLAlchemy implementation of mega gem inventory repository.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.data.models.mega_gem_inventory import MegaGemInventoryModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


@dataclass
class MegaGemInventoryRecord:
    """Lightweight record returned by the repository.

    The service layer maps this to response DTOs.
    """

    id: UUID
    player_id: UUID
    slot_index: int
    count: int


class SQLAlchemyMegaGemInventoryRepository:
    """Concrete mega gem inventory repository backed by PostgreSQL via SQLAlchemy.

    Manages per-player inventory slots for mega gems (slots 0-3)
    and shuffle tokens (slot 4).
    """

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_inventory(self, player_id: UUID) -> list[MegaGemInventoryRecord]:
        """Get all 5 inventory slots for a player, ordered by slot_index.

        Args:
            player_id: The player whose inventory to retrieve.

        Returns:
            List of MegaGemInventoryRecord ordered by slot_index.
        """
        self._logger.debug("Getting mega gem inventory", player_id=str(player_id))

        async with self._data_ctx.session() as session:
            stmt = (
                select(MegaGemInventoryModel)
                .where(MegaGemInventoryModel.player_id == player_id)
                .order_by(MegaGemInventoryModel.slot_index)
            )
            result = await session.execute(stmt)
            models = result.scalars().all()

            return [self._to_record(m) for m in models]

    async def get_slot(
        self, player_id: UUID, slot_index: int
    ) -> MegaGemInventoryRecord | None:
        """Get a single inventory slot for a player.

        Args:
            player_id: The player whose slot to retrieve.
            slot_index: The slot index (0-4).

        Returns:
            MegaGemInventoryRecord if found, None otherwise.
        """
        self._logger.debug(
            "Getting mega gem slot",
            player_id=str(player_id),
            slot_index=slot_index,
        )

        async with self._data_ctx.session() as session:
            stmt = select(MegaGemInventoryModel).where(
                MegaGemInventoryModel.player_id == player_id,
                MegaGemInventoryModel.slot_index == slot_index,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_record(model)

    async def consume_one(self, player_id: UUID, slot_index: int) -> bool:
        """Consume one mega gem from a slot.

        Atomically decrements count by 1 only if count > 0.

        Args:
            player_id: The player consuming the mega gem.
            slot_index: The slot to consume from (0-4).

        Returns:
            True if a mega gem was consumed, False if count was 0.
        """
        self._logger.debug(
            "Consuming mega gem",
            player_id=str(player_id),
            slot_index=slot_index,
        )

        async with self._data_ctx.session() as session:
            stmt = (
                update(MegaGemInventoryModel)
                .where(
                    MegaGemInventoryModel.player_id == player_id,
                    MegaGemInventoryModel.slot_index == slot_index,
                    MegaGemInventoryModel.count > 0,
                )
                .values(count=MegaGemInventoryModel.count - 1)
            )
            result = await session.execute(stmt)

            updated = result.rowcount > 0

        if updated:
            self._logger.debug(
                "Mega gem consumed",
                player_id=str(player_id),
                slot_index=slot_index,
            )
        else:
            self._logger.debug(
                "Mega gem consume failed (count was 0)",
                player_id=str(player_id),
                slot_index=slot_index,
            )

        return updated

    async def add_count(
        self, player_id: UUID, slot_index: int, amount: int
    ) -> MegaGemInventoryRecord:
        """Add mega gems to a slot, upserting the row if it doesn't exist.

        Uses PostgreSQL INSERT ... ON CONFLICT to atomically create or
        increment the slot count.

        Args:
            player_id: The player receiving mega gems.
            slot_index: The slot to add to (0-4).
            amount: Number of mega gems to add.

        Returns:
            Updated MegaGemInventoryRecord with the new count.
        """
        self._logger.debug(
            "Adding mega gems",
            player_id=str(player_id),
            slot_index=slot_index,
            amount=amount,
        )

        async with self._data_ctx.session() as session:
            insert_stmt = pg_insert(MegaGemInventoryModel).values(
                player_id=player_id,
                slot_index=slot_index,
                count=amount,
            )
            upsert_stmt = insert_stmt.on_conflict_do_update(
                constraint="uq_mega_gem_inventory_player_slot",
                set_={"count": MegaGemInventoryModel.count + amount},
            ).returning(
                MegaGemInventoryModel.id,
                MegaGemInventoryModel.player_id,
                MegaGemInventoryModel.slot_index,
                MegaGemInventoryModel.count,
            )
            result = await session.execute(upsert_stmt)
            row = result.one()

        record = MegaGemInventoryRecord(
            id=row.id,
            player_id=row.player_id,
            slot_index=row.slot_index,
            count=row.count,
        )

        self._logger.debug(
            "Mega gems added",
            player_id=str(player_id),
            slot_index=slot_index,
            new_count=record.count,
        )

        return record

    async def ensure_slots(self, player_id: UUID) -> None:
        """Ensure all 5 inventory slots exist for a player.

        Inserts rows for slots 0-4 with count=0, using ON CONFLICT DO NOTHING
        so existing rows are left untouched.

        Args:
            player_id: The player whose slots to initialize.
        """
        self._logger.debug(
            "Ensuring mega gem inventory slots", player_id=str(player_id)
        )

        async with self._data_ctx.session() as session:
            for slot in range(5):
                stmt = (
                    pg_insert(MegaGemInventoryModel)
                    .values(
                        player_id=player_id,
                        slot_index=slot,
                        count=0,
                    )
                    .on_conflict_do_nothing(
                        constraint="uq_mega_gem_inventory_player_slot",
                    )
                )
                await session.execute(stmt)

        self._logger.debug("Mega gem inventory slots ensured", player_id=str(player_id))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_record(model: MegaGemInventoryModel) -> MegaGemInventoryRecord:
        """Convert an ORM model to a lightweight record."""
        return MegaGemInventoryRecord(
            id=model.id,
            player_id=model.player_id,
            slot_index=model.slot_index,
            count=model.count,
        )
