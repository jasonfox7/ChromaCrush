"""SQLAlchemy implementation of purchase intent repository."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, update as sa_update

from src.data.models.purchase_intent import PurchaseIntentModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.payments.dto import PurchaseIntentCreate, PurchaseIntentUpdate


class SQLAlchemyPurchaseIntentRepository:
    """Concrete purchase intent repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def create(self, data: PurchaseIntentCreate) -> PurchaseIntentModel:
        model = PurchaseIntentModel(
            player_id=data.player_id,
            product_id=data.product_id,
            status=data.status,
            expires_at=data.expires_at,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def find_by_id(self, intent_id: UUID) -> PurchaseIntentModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(PurchaseIntentModel).where(
                PurchaseIntentModel.id == intent_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update(
        self,
        intent_id: UUID,
        changes: PurchaseIntentUpdate,
    ) -> PurchaseIntentModel:
        async with self._data_ctx.session() as session:
            stmt = select(PurchaseIntentModel).where(
                PurchaseIntentModel.id == intent_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Purchase intent not found",
                    code="NOT_FOUND_PURCHASE_INTENT",
                    intent_id=str(intent_id),
                )
            if changes.status is not None:
                model.status = changes.status
            if changes.completed_at is not None:
                model.completed_at = changes.completed_at
            await session.flush()
        return model

    async def find_pending_by_player(
        self,
        player_id: UUID,
    ) -> list[PurchaseIntentModel]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(PurchaseIntentModel)
                .where(
                    PurchaseIntentModel.player_id == player_id,
                    PurchaseIntentModel.status == "pending",
                )
                .order_by(PurchaseIntentModel.created_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def expire_old_intents(self, before: datetime) -> int:
        async with self._data_ctx.session() as session:
            stmt = (
                sa_update(PurchaseIntentModel)
                .where(
                    PurchaseIntentModel.status == "pending",
                    PurchaseIntentModel.expires_at < before,
                )
                .values(status="expired")
            )
            result = await session.execute(stmt)
            return result.rowcount
