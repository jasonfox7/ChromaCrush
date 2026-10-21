"""SQLAlchemy implementation of purchase repository."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select

from src.data.models.purchase import PurchaseModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.payments.dto import PurchaseCreate, PurchaseUpdate


class SQLAlchemyPurchaseRepository:
    """Concrete purchase repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def create(self, data: PurchaseCreate) -> PurchaseModel:
        model = PurchaseModel(
            player_id=data.player_id,
            product_id=data.product_id,
            provider=data.provider,
            transaction_id=data.transaction_id,
            original_transaction_id=data.original_transaction_id,
            status=data.status,
            price_cents=data.price_cents,
            currency=data.currency,
            is_sandbox=data.is_sandbox,
            intent_id=data.intent_id,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def find_by_id(self, purchase_id: UUID) -> PurchaseModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(PurchaseModel).where(PurchaseModel.id == purchase_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def find_by_transaction(
        self,
        provider: str,
        transaction_id: str,
    ) -> PurchaseModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(PurchaseModel).where(
                PurchaseModel.provider == provider,
                PurchaseModel.transaction_id == transaction_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def find_by_player(
        self,
        player_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PurchaseModel], int]:
        async with self._data_ctx.session() as session:
            # Count total
            count_stmt = (
                select(func.count())
                .select_from(PurchaseModel)
                .where(PurchaseModel.player_id == player_id)
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            # Fetch page
            stmt = (
                select(PurchaseModel)
                .where(PurchaseModel.player_id == player_id)
                .order_by(PurchaseModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            records = list(result.scalars().all())

        return records, total

    async def find_completed_by_player(
        self,
        player_id: UUID,
        product_id: str | None = None,
    ) -> list[PurchaseModel]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(PurchaseModel)
                .where(
                    PurchaseModel.player_id == player_id,
                    PurchaseModel.status == "completed",
                )
                .order_by(PurchaseModel.created_at.desc())
            )
            if product_id is not None:
                stmt = stmt.where(PurchaseModel.product_id == product_id)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update(
        self,
        purchase_id: UUID,
        changes: PurchaseUpdate,
    ) -> PurchaseModel:
        async with self._data_ctx.session() as session:
            stmt = select(PurchaseModel).where(PurchaseModel.id == purchase_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Purchase not found",
                    code="NOT_FOUND_PURCHASE",
                    purchase_id=str(purchase_id),
                )
            if changes.status is not None:
                model.status = changes.status
            if changes.refunded_at is not None:
                model.refunded_at = changes.refunded_at
            await session.flush()
        return model
