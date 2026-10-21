"""SQLAlchemy implementation of attribution entry repository."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select

from src.data.models.bot_attribution_entry import BotAttributionEntryModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.bot_earnings.dto import AttributionEntryCreate


class SQLAlchemyAttributionEntryRepository:
    """Concrete attribution entry repository backed by PostgreSQL."""

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
        data: AttributionEntryCreate,
    ) -> BotAttributionEntryModel:
        model = BotAttributionEntryModel(
            bot_player_id=data.bot_player_id,
            match_id=data.match_id,
            ad_impression_id=data.ad_impression_id,
            opponent_player_id=data.opponent_player_id,
            estimated_impression_revenue_cents=data.estimated_impression_revenue_cents,
            attribution_share_percent=data.attribution_share_percent,
            attributed_cents=data.attributed_cents,
            attribution_date=data.attribution_date,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def create_batch(
        self,
        entries: list[AttributionEntryCreate],
    ) -> list[BotAttributionEntryModel]:
        models = []
        async with self._data_ctx.session() as session:
            for data in entries:
                model = BotAttributionEntryModel(
                    bot_player_id=data.bot_player_id,
                    match_id=data.match_id,
                    ad_impression_id=data.ad_impression_id,
                    opponent_player_id=data.opponent_player_id,
                    estimated_impression_revenue_cents=data.estimated_impression_revenue_cents,
                    attribution_share_percent=data.attribution_share_percent,
                    attributed_cents=data.attributed_cents,
                    attribution_date=data.attribution_date,
                )
                session.add(model)
                models.append(model)
            await session.flush()
        return models

    async def find_by_impression_id(
        self,
        ad_impression_id: UUID,
    ) -> BotAttributionEntryModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(BotAttributionEntryModel).where(
                BotAttributionEntryModel.ad_impression_id == ad_impression_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def find_by_bot(
        self,
        bot_player_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BotAttributionEntryModel], int]:
        async with self._data_ctx.session() as session:
            base = select(BotAttributionEntryModel).where(
                BotAttributionEntryModel.bot_player_id == bot_player_id,
            )
            if start_date is not None:
                base = base.where(
                    BotAttributionEntryModel.attribution_date >= start_date,
                )
            if end_date is not None:
                base = base.where(
                    BotAttributionEntryModel.attribution_date <= end_date,
                )
            count_stmt = select(func.count()).select_from(base.subquery())
            total = (await session.execute(count_stmt)).scalar_one()
            stmt = (
                base.order_by(BotAttributionEntryModel.recorded_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all()), total

    async def get_daily_summary(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[Any]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(
                    BotAttributionEntryModel.attribution_date.label("date"),
                    func.count().label("total_attributions"),
                    func.count(
                        func.distinct(BotAttributionEntryModel.match_id),
                    ).label("total_matches"),
                    func.count().label("total_impressions"),
                    func.coalesce(
                        func.sum(BotAttributionEntryModel.attributed_cents),
                        0,
                    ).label("total_cents"),
                )
                .where(
                    BotAttributionEntryModel.bot_player_id == bot_player_id,
                    BotAttributionEntryModel.attribution_date >= start_date,
                    BotAttributionEntryModel.attribution_date <= end_date,
                )
                .group_by(BotAttributionEntryModel.attribution_date)
                .order_by(BotAttributionEntryModel.attribution_date.asc())
            )
            result = await session.execute(stmt)
            return list(result.all())

    async def get_period_summary(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Any:
        async with self._data_ctx.session() as session:
            stmt = select(
                func.count().label("total_attributions"),
                func.count(
                    func.distinct(BotAttributionEntryModel.match_id),
                ).label("total_matches"),
                func.count().label("total_impressions"),
                func.coalesce(
                    func.sum(BotAttributionEntryModel.attributed_cents),
                    0,
                ).label("total_cents"),
            ).where(
                BotAttributionEntryModel.bot_player_id == bot_player_id,
                BotAttributionEntryModel.attribution_date >= start_date,
                BotAttributionEntryModel.attribution_date <= end_date,
            )
            result = await session.execute(stmt)
            return result.one()

    async def get_last_recorded_for_bot(
        self,
        bot_player_id: UUID,
    ) -> BotAttributionEntryModel | None:
        async with self._data_ctx.session() as session:
            stmt = (
                select(BotAttributionEntryModel)
                .where(
                    BotAttributionEntryModel.bot_player_id == bot_player_id,
                )
                .order_by(BotAttributionEntryModel.recorded_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
