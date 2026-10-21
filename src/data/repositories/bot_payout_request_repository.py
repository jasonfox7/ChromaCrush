"""SQLAlchemy implementation of payout request repository."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select

from src.data.models.bot_payout_request import BotPayoutRequestModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.bot_earnings.dto import (
        PayoutRequestCreate,
        PayoutRequestUpdate,
    )


class SQLAlchemyPayoutRequestRepository:
    """Concrete payout request repository backed by PostgreSQL."""

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
        data: PayoutRequestCreate,
    ) -> BotPayoutRequestModel:
        model = BotPayoutRequestModel(
            bot_player_id=data.bot_player_id,
            owner_player_id=data.owner_player_id,
            amount_cents=data.amount_cents,
            status=data.status,
            hold_until=data.hold_until,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def find_by_id(
        self,
        payout_request_id: UUID,
    ) -> BotPayoutRequestModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(BotPayoutRequestModel).where(
                BotPayoutRequestModel.id == payout_request_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update(
        self,
        payout_request_id: UUID,
        changes: PayoutRequestUpdate,
    ) -> BotPayoutRequestModel:
        async with self._data_ctx.session() as session:
            stmt = select(BotPayoutRequestModel).where(
                BotPayoutRequestModel.id == payout_request_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Payout request not found",
                    code="NOT_FOUND_PAYOUT_REQUEST",
                    payout_request_id=str(payout_request_id),
                )
            if changes.status is not None:
                model.status = changes.status
            if changes.processed_at is not None:
                model.processed_at = changes.processed_at
            if changes.processed_by is not None:
                model.processed_by = changes.processed_by
            if changes.external_reference is not None:
                model.external_reference = changes.external_reference
            if changes.rejection_reason is not None:
                model.rejection_reason = changes.rejection_reason
            if changes.notes is not None:
                model.notes = changes.notes
            await session.flush()
        return model

    async def find_by_bot(
        self,
        bot_player_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BotPayoutRequestModel], int]:
        async with self._data_ctx.session() as session:
            base = select(BotPayoutRequestModel).where(
                BotPayoutRequestModel.bot_player_id == bot_player_id,
            )
            if status is not None:
                base = base.where(BotPayoutRequestModel.status == status)
            count_stmt = select(func.count()).select_from(base.subquery())
            total = (await session.execute(count_stmt)).scalar_one()
            stmt = (
                base.order_by(BotPayoutRequestModel.requested_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all()), total

    async def find_pending_by_bot(
        self,
        bot_player_id: UUID,
    ) -> BotPayoutRequestModel | None:
        async with self._data_ctx.session() as session:
            stmt = (
                select(BotPayoutRequestModel)
                .where(
                    BotPayoutRequestModel.bot_player_id == bot_player_id,
                    BotPayoutRequestModel.status == "pending",
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def find_pending_past_hold(
        self,
        as_of: datetime,
    ) -> list[BotPayoutRequestModel]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(BotPayoutRequestModel)
                .where(
                    BotPayoutRequestModel.status == "pending",
                    (BotPayoutRequestModel.hold_until.is_(None))
                    | (BotPayoutRequestModel.hold_until <= as_of),
                )
                .order_by(BotPayoutRequestModel.requested_at.asc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
