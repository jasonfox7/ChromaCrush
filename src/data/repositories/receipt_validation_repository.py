"""SQLAlchemy implementation of receipt validation repository."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from src.data.models.receipt_validation import ReceiptValidationModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.payments.dto import (
        ReceiptValidationCreate,
        ReceiptValidationUpdate,
    )


class SQLAlchemyReceiptValidationRepository:
    """Concrete receipt validation repository backed by PostgreSQL."""

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
        data: ReceiptValidationCreate,
    ) -> ReceiptValidationModel:
        model = ReceiptValidationModel(
            purchase_id=data.purchase_id,
            player_id=data.player_id,
            provider=data.provider,
            receipt_data=data.receipt_data,
            receipt_hash=data.receipt_hash,
            validation_result=data.validation_result,
            validation_response=data.validation_response,
            transaction_id=data.transaction_id,
            product_id=data.product_id,
            purchase_date=data.purchase_date,
            is_sandbox=data.is_sandbox,
            error_code=data.error_code,
            error_message=data.error_message,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def find_by_hash(
        self,
        receipt_hash: str,
    ) -> ReceiptValidationModel | None:
        async with self._data_ctx.session() as session:
            stmt = (
                select(ReceiptValidationModel)
                .where(ReceiptValidationModel.receipt_hash == receipt_hash)
                .order_by(ReceiptValidationModel.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def find_by_transaction(
        self,
        provider: str,
        transaction_id: str,
    ) -> ReceiptValidationModel | None:
        async with self._data_ctx.session() as session:
            stmt = (
                select(ReceiptValidationModel)
                .where(
                    ReceiptValidationModel.provider == provider,
                    ReceiptValidationModel.transaction_id == transaction_id,
                )
                .order_by(ReceiptValidationModel.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update(
        self,
        validation_id: UUID,
        changes: ReceiptValidationUpdate,
    ) -> ReceiptValidationModel:
        async with self._data_ctx.session() as session:
            stmt = select(ReceiptValidationModel).where(
                ReceiptValidationModel.id == validation_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Receipt validation not found",
                    code="NOT_FOUND_RECEIPT_VALIDATION",
                    validation_id=str(validation_id),
                )
            if changes.purchase_id is not None:
                model.purchase_id = changes.purchase_id
            await session.flush()
        return model
