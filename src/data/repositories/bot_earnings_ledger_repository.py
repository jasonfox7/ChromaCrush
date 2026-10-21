"""SQLAlchemy implementation of earnings ledger repository."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from src.data.models.bot_earnings_ledger import BotEarningsLedgerModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.bot_earnings.dto import (
        EarningsLedgerCreate,
        EarningsLedgerUpdate,
    )


class SQLAlchemyEarningsLedgerRepository:
    """Concrete earnings ledger repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def find_by_bot_id(
        self,
        bot_player_id: UUID,
    ) -> BotEarningsLedgerModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(BotEarningsLedgerModel).where(
                BotEarningsLedgerModel.bot_player_id == bot_player_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create(
        self,
        data: EarningsLedgerCreate,
    ) -> BotEarningsLedgerModel:
        model = BotEarningsLedgerModel(
            bot_player_id=data.bot_player_id,
            owner_player_id=data.owner_player_id,
            total_earned_cents=data.total_earned_cents,
            total_paid_out_cents=data.total_paid_out_cents,
            pending_payout_cents=data.pending_payout_cents,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def update(
        self,
        bot_player_id: UUID,
        changes: EarningsLedgerUpdate,
    ) -> BotEarningsLedgerModel:
        async with self._data_ctx.session() as session:
            stmt = select(BotEarningsLedgerModel).where(
                BotEarningsLedgerModel.bot_player_id == bot_player_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Earnings ledger not found",
                    code="NOT_FOUND_RESOURCE",
                    bot_player_id=str(bot_player_id),
                )
            if changes.total_earned_cents is not None:
                model.total_earned_cents = changes.total_earned_cents
            if changes.total_paid_out_cents is not None:
                model.total_paid_out_cents = changes.total_paid_out_cents
            if changes.pending_payout_cents is not None:
                model.pending_payout_cents = changes.pending_payout_cents
            if changes.last_attribution_at is not None:
                model.last_attribution_at = changes.last_attribution_at
            if changes.last_sync_at is not None:
                model.last_sync_at = changes.last_sync_at
            await session.flush()
        return model

    async def increment_earned(
        self,
        bot_player_id: UUID,
        cents: int,
    ) -> BotEarningsLedgerModel:
        async with self._data_ctx.session() as session:
            stmt = select(BotEarningsLedgerModel).where(
                BotEarningsLedgerModel.bot_player_id == bot_player_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Earnings ledger not found",
                    code="NOT_FOUND_RESOURCE",
                    bot_player_id=str(bot_player_id),
                )
            model.total_earned_cents += cents
            await session.flush()
        return model

    async def increment_pending(
        self,
        bot_player_id: UUID,
        cents: int,
    ) -> BotEarningsLedgerModel:
        async with self._data_ctx.session() as session:
            stmt = select(BotEarningsLedgerModel).where(
                BotEarningsLedgerModel.bot_player_id == bot_player_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Earnings ledger not found",
                    code="NOT_FOUND_RESOURCE",
                    bot_player_id=str(bot_player_id),
                )
            model.pending_payout_cents += cents
            await session.flush()
        return model

    async def complete_payout(
        self,
        bot_player_id: UUID,
        cents: int,
    ) -> BotEarningsLedgerModel:
        async with self._data_ctx.session() as session:
            stmt = select(BotEarningsLedgerModel).where(
                BotEarningsLedgerModel.bot_player_id == bot_player_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Earnings ledger not found",
                    code="NOT_FOUND_RESOURCE",
                    bot_player_id=str(bot_player_id),
                )
            model.pending_payout_cents -= cents
            model.total_paid_out_cents += cents
            await session.flush()
        return model

    async def cancel_pending(
        self,
        bot_player_id: UUID,
        cents: int,
    ) -> BotEarningsLedgerModel:
        async with self._data_ctx.session() as session:
            stmt = select(BotEarningsLedgerModel).where(
                BotEarningsLedgerModel.bot_player_id == bot_player_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Earnings ledger not found",
                    code="NOT_FOUND_RESOURCE",
                    bot_player_id=str(bot_player_id),
                )
            model.pending_payout_cents -= cents
            await session.flush()
        return model

    async def find_bots_needing_sync(
        self,
        since: datetime,
        limit: int = 100,
    ) -> list[BotEarningsLedgerModel]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(BotEarningsLedgerModel)
                .where(
                    (BotEarningsLedgerModel.last_sync_at.is_(None))
                    | (BotEarningsLedgerModel.last_sync_at < since)
                )
                .order_by(BotEarningsLedgerModel.last_sync_at.asc().nullsfirst())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
