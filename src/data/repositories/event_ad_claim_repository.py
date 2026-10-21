"""SQLAlchemy implementation of event ad claim repository."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select

from src.data.models.event_ad_claim import EventAdClaimModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.dto import EventAdClaimCreate


class SQLAlchemyEventAdClaimRepository:
    """Concrete event ad claim repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def create(self, data: EventAdClaimCreate) -> EventAdClaimModel:
        model = EventAdClaimModel(
            event_id=data.event_id,
            opportunity_id=data.opportunity_id,
            player_id=data.player_id,
            impression_id=data.impression_id,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def count_claims(
        self, event_id: UUID, opportunity_id: str, player_id: UUID
    ) -> int:
        async with self._data_ctx.session() as session:
            stmt = (
                select(func.count())
                .select_from(EventAdClaimModel)
                .where(
                    EventAdClaimModel.event_id == event_id,
                    EventAdClaimModel.opportunity_id == opportunity_id,
                    EventAdClaimModel.player_id == player_id,
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one()

    async def find_last_claim(
        self,
        event_id: UUID,
        opportunity_id: str,
        player_id: UUID,
    ) -> EventAdClaimModel | None:
        async with self._data_ctx.session() as session:
            stmt = (
                select(EventAdClaimModel)
                .where(
                    EventAdClaimModel.event_id == event_id,
                    EventAdClaimModel.opportunity_id == opportunity_id,
                    EventAdClaimModel.player_id == player_id,
                )
                .order_by(EventAdClaimModel.claimed_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
