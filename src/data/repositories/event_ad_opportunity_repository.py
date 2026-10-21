"""SQLAlchemy implementation of event ad opportunity repository."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from src.data.models.event_ad_opportunity import EventAdOpportunityModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.dto import EventAdOpportunityCreate


class SQLAlchemyEventAdOpportunityRepository:
    """Concrete event ad opportunity repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def find_by_event(self, event_id: UUID) -> list[EventAdOpportunityModel]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(EventAdOpportunityModel)
                .where(
                    EventAdOpportunityModel.event_id == event_id,
                )
                .order_by(EventAdOpportunityModel.created_at.asc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def find_by_id(
        self, event_id: UUID, opportunity_id: str
    ) -> EventAdOpportunityModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(EventAdOpportunityModel).where(
                EventAdOpportunityModel.event_id == event_id,
                EventAdOpportunityModel.id == opportunity_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create(self, data: EventAdOpportunityCreate) -> EventAdOpportunityModel:
        model = EventAdOpportunityModel(
            id=data.id,
            event_id=data.event_id,
            ad_type=data.ad_type,
            reward_type=data.reward_type,
            reward_value=data.reward_value,
            description=data.description,
            times_available_per_player=data.times_available_per_player,
            cooldown_minutes=data.cooldown_minutes,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model
