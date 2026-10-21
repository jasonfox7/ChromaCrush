"""SQLAlchemy implementation of ad impression repository."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select

from src.data.models.ad_impression import AdImpressionModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.dto import AdImpressionCreate


class SQLAlchemyAdImpressionRepository:
    """Concrete ad impression repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def create(self, data: AdImpressionCreate) -> AdImpressionModel:
        model = AdImpressionModel(
            player_id=data.player_id,
            ad_request_id=data.ad_request_id,
            ad_type=data.ad_type,
            trigger=data.trigger,
            placement=data.placement,
            viewed=data.viewed,
            view_duration_ms=data.view_duration_ms,
            completed=data.completed,
            match_id=data.match_id,
            event_id=data.event_id,
            opponent_id=data.opponent_id,
            attributed_to=data.attributed_to,
            attribution_share_percent=data.attribution_share_percent,
            estimated_revenue_cents=data.estimated_revenue_cents,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def find_by_id(self, impression_id: UUID) -> AdImpressionModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(AdImpressionModel).where(
                AdImpressionModel.id == impression_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def find_by_request_id(self, ad_request_id: UUID) -> AdImpressionModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(AdImpressionModel).where(
                AdImpressionModel.ad_request_id == ad_request_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def find_by_player(
        self,
        player_id: UUID,
        ad_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AdImpressionModel], int]:
        async with self._data_ctx.session() as session:
            base = select(AdImpressionModel).where(
                AdImpressionModel.player_id == player_id
            )
            if ad_type is not None:
                base = base.where(AdImpressionModel.ad_type == ad_type)
            count_stmt = select(func.count()).select_from(base.subquery())
            total = (await session.execute(count_stmt)).scalar_one()
            stmt = (
                base.order_by(AdImpressionModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all()), total

    async def find_by_match(self, match_id: UUID) -> list[AdImpressionModel]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(AdImpressionModel)
                .where(
                    AdImpressionModel.match_id == match_id,
                )
                .order_by(AdImpressionModel.created_at.asc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_player_stats(
        self,
        player_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Any:
        async with self._data_ctx.session() as session:
            base = select(
                func.count().label("total_impressions"),
                func.count()
                .filter(AdImpressionModel.ad_type == "interstitial")
                .label("interstitial_count"),
                func.count()
                .filter(AdImpressionModel.ad_type == "rewarded")
                .label("rewarded_video_count"),
                func.count()
                .filter(AdImpressionModel.ad_type == "banner")
                .label("banner_impression_count"),
                func.coalesce(func.avg(AdImpressionModel.view_duration_ms), 0).label(
                    "average_view_duration_ms"
                ),
                func.max(AdImpressionModel.created_at).label("last_ad_at"),
            ).where(AdImpressionModel.player_id == player_id)
            if start_date is not None:
                base = base.where(AdImpressionModel.recorded_date >= start_date)
            if end_date is not None:
                base = base.where(AdImpressionModel.recorded_date <= end_date)
            result = await session.execute(base)
            return result.one()

    async def get_bot_attributions(
        self, bot_player_id: UUID, start_date: date, end_date: date
    ) -> Any:
        async with self._data_ctx.session() as session:
            stmt = select(
                func.count(func.distinct(AdImpressionModel.match_id)).label(
                    "total_matches"
                ),
                func.count(AdImpressionModel.match_id).label(
                    "matches_with_impressions"
                ),
                func.count().label("total_attributed_impressions"),
                func.coalesce(
                    func.sum(AdImpressionModel.estimated_revenue_cents), 0
                ).label("estimated_revenue_cents"),
                func.coalesce(
                    func.sum(
                        AdImpressionModel.estimated_revenue_cents
                        * AdImpressionModel.attribution_share_percent
                        / 100
                    ),
                    0,
                ).label("attributed_revenue_cents"),
            ).where(
                AdImpressionModel.attributed_to == bot_player_id,
                AdImpressionModel.recorded_date >= start_date,
                AdImpressionModel.recorded_date <= end_date,
            )
            result = await session.execute(stmt)
            return result.one()

    async def get_daily_attributions(
        self, bot_player_id: UUID, start_date: date, end_date: date
    ) -> list[Any]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(
                    AdImpressionModel.recorded_date.label("date"),
                    func.count(func.distinct(AdImpressionModel.match_id)).label(
                        "matches"
                    ),
                    func.count().label("impressions"),
                    func.coalesce(
                        func.sum(AdImpressionModel.estimated_revenue_cents), 0
                    ).label("estimated_revenue_cents"),
                    func.coalesce(
                        func.sum(
                            AdImpressionModel.estimated_revenue_cents
                            * AdImpressionModel.attribution_share_percent
                            / 100
                        ),
                        0,
                    ).label("attributed_cents"),
                )
                .where(
                    AdImpressionModel.attributed_to == bot_player_id,
                    AdImpressionModel.recorded_date >= start_date,
                    AdImpressionModel.recorded_date <= end_date,
                )
                .group_by(AdImpressionModel.recorded_date)
                .order_by(AdImpressionModel.recorded_date.asc())
            )
            result = await session.execute(stmt)
            return list(result.all())
