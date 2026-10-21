"""SQLAlchemy implementation of ad request repository."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, update as sa_update

from src.data.models.ad_request import AdRequestModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.dto import AdRequestCreate, AdRequestUpdate


class SQLAlchemyAdRequestRepository:
    """Concrete ad request repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def create(self, data: AdRequestCreate) -> AdRequestModel:
        model = AdRequestModel(
            player_id=data.player_id,
            ad_type=data.ad_type,
            ad_unit_id=data.ad_unit_id,
            trigger=data.trigger,
            reward_type=data.reward_type,
            reward_value=data.reward_value,
            match_id=data.match_id,
            event_id=data.event_id,
            status=data.status,
            expires_at=data.expires_at,
            provider_response=data.provider_response,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def find_by_id(self, request_id: UUID) -> AdRequestModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(AdRequestModel).where(AdRequestModel.id == request_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update(
        self, request_id: UUID, changes: AdRequestUpdate
    ) -> AdRequestModel:
        async with self._data_ctx.session() as session:
            stmt = select(AdRequestModel).where(AdRequestModel.id == request_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Ad request not found",
                    code="NOT_FOUND_AD_REQUEST",
                    ad_request_id=str(request_id),
                )
            if changes.status is not None:
                model.status = changes.status
            if changes.completed_at is not None:
                model.completed_at = changes.completed_at
            await session.flush()
        return model

    async def find_pending_by_player(self, player_id: UUID) -> list[AdRequestModel]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(AdRequestModel)
                .where(
                    AdRequestModel.player_id == player_id,
                    AdRequestModel.status == "pending",
                )
                .order_by(AdRequestModel.created_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def find_last_by_type(
        self, player_id: UUID, ad_type: str
    ) -> AdRequestModel | None:
        async with self._data_ctx.session() as session:
            stmt = (
                select(AdRequestModel)
                .where(
                    AdRequestModel.player_id == player_id,
                    AdRequestModel.ad_type == ad_type,
                )
                .order_by(AdRequestModel.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def expire_old_requests(self, before: datetime) -> int:
        async with self._data_ctx.session() as session:
            stmt = (
                sa_update(AdRequestModel)
                .where(
                    AdRequestModel.status == "pending",
                    AdRequestModel.expires_at < before,
                )
                .values(status="expired")
            )
            result = await session.execute(stmt)
            return result.rowcount
