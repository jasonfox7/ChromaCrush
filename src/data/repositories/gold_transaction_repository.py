"""SQLAlchemy implementation of GoldTransactionRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from src.data.models.gold_transaction import GoldTransactionModel
from src.data.protocols.gold_transaction_repository import GoldTransactionRecord

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


class SQLAlchemyGoldTransactionRepository:
    """Concrete gold transaction repository backed by PostgreSQL.

    Satisfies ``GoldTransactionRepositoryProtocol``. Created in the
    composition root and injected into Economy and Payment services.
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

    async def create(
        self,
        player_id: UUID,
        tx_type: str,
        amount: int,
        balance_after: int,
        source: str,
        reference_id: str | None = None,
    ) -> GoldTransactionRecord:
        """Record a gold transaction in the ledger."""
        self._logger.debug(
            "Recording gold transaction",
            player_id=str(player_id),
            tx_type=tx_type,
            amount=amount,
            balance_after=balance_after,
            source=source,
        )

        model = GoldTransactionModel(
            player_id=player_id,
            tx_type=tx_type,
            amount=amount,
            balance_after=balance_after,
            source=source,
            reference_id=reference_id,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            record = self._to_record(model)

        self._logger.debug(
            "Gold transaction recorded",
            tx_id=str(record.id),
            player_id=str(player_id),
            tx_type=tx_type,
            amount=amount,
        )
        return record

    async def find_by_player(
        self,
        player_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GoldTransactionRecord]:
        """Retrieve transaction history for a player, newest first."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(GoldTransactionModel)
                .where(GoldTransactionModel.player_id == player_id)
                .order_by(GoldTransactionModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return [self._to_record(m) for m in result.scalars().all()]

    async def find_by_reference(
        self,
        reference_id: str,
    ) -> GoldTransactionRecord | None:
        """Find a transaction by its external reference ID."""
        async with self._data_ctx.session() as session:
            stmt = select(GoldTransactionModel).where(
                GoldTransactionModel.reference_id == reference_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_record(model)

    @staticmethod
    def _to_record(model: GoldTransactionModel) -> GoldTransactionRecord:
        """Convert an ORM model to a lightweight record."""
        return GoldTransactionRecord(
            id=model.id,
            player_id=model.player_id,
            tx_type=model.tx_type,
            amount=model.amount,
            balance_after=model.balance_after,
            source=model.source,
            reference_id=model.reference_id,
            created_at=model.created_at,
        )
