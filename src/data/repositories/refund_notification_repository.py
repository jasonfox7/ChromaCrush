"""SQLAlchemy implementation of refund notification repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from src.data.models.refund_notification import RefundNotificationModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.payments.dto import RefundNotificationCreate


class SQLAlchemyRefundNotificationRepository:
    """Concrete refund notification repository backed by PostgreSQL."""

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
        data: RefundNotificationCreate,
    ) -> RefundNotificationModel:
        model = RefundNotificationModel(
            provider=data.provider,
            transaction_id=data.transaction_id,
            original_transaction_id=data.original_transaction_id,
            notification_type=data.notification_type,
            notification_payload=data.notification_payload or {},
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def find_unprocessed(self) -> list[RefundNotificationModel]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(RefundNotificationModel)
                .where(RefundNotificationModel.processed.is_(False))
                .order_by(RefundNotificationModel.received_at.asc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def mark_processed(
        self,
        notification_id: UUID,
        result: str,
        error: str | None = None,
    ) -> RefundNotificationModel:
        async with self._data_ctx.session() as session:
            stmt = select(RefundNotificationModel).where(
                RefundNotificationModel.id == notification_id,
            )
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Refund notification not found",
                    code="NOT_FOUND_REFUND_NOTIFICATION",
                    notification_id=str(notification_id),
                )
            model.processed = True
            model.processed_at = datetime.now(timezone.utc)
            model.process_result = result
            model.process_error = error
            await session.flush()
        return model
