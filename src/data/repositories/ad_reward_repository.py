"""SQLAlchemy implementation of ad reward repository."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from src.data.models.ad_reward import AdRewardModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.dto import AdRewardCreate


class SQLAlchemyAdRewardRepository:
    """Concrete ad reward repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def create(self, data: AdRewardCreate) -> AdRewardModel:
        model = AdRewardModel(
            player_id=data.player_id,
            ad_request_id=data.ad_request_id,
            impression_id=data.impression_id,
            reward_type=data.reward_type,
            reward_value=data.reward_value,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def find_by_request_id(self, ad_request_id: UUID) -> AdRewardModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(AdRewardModel).where(
                AdRewardModel.ad_request_id == ad_request_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
