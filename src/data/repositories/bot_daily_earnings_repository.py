"""SQLAlchemy implementation of daily earnings repository."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from src.data.models.bot_earnings_daily import BotEarningsDailyModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.bot_earnings.dto import DailyEarningsUpsert


class SQLAlchemyDailyEarningsRepository:
    """Concrete daily earnings repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def upsert(
        self,
        data: DailyEarningsUpsert,
    ) -> BotEarningsDailyModel:
        async with self._data_ctx.session() as session:
            stmt = select(BotEarningsDailyModel).where(
                BotEarningsDailyModel.bot_player_id == data.bot_player_id,
                BotEarningsDailyModel.earnings_date == data.earnings_date,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                model = BotEarningsDailyModel(
                    bot_player_id=data.bot_player_id,
                    earnings_date=data.earnings_date,
                    attributions_count=data.attributions_count,
                    matches_count=data.matches_count,
                    impressions_count=data.impressions_count,
                    earnings_cents=data.earnings_cents,
                )
                session.add(model)
            else:
                model.attributions_count = data.attributions_count
                model.matches_count = data.matches_count
                model.impressions_count = data.impressions_count
                model.earnings_cents = data.earnings_cents
            await session.flush()
        return model

    async def find_range(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[BotEarningsDailyModel]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(BotEarningsDailyModel)
                .where(
                    BotEarningsDailyModel.bot_player_id == bot_player_id,
                    BotEarningsDailyModel.earnings_date >= start_date,
                    BotEarningsDailyModel.earnings_date <= end_date,
                )
                .order_by(BotEarningsDailyModel.earnings_date.asc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
