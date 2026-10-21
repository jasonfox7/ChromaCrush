"""SQLAlchemy implementation of ad-free status repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from src.data.models.ad_free_status import AdFreeStatusModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.dto import AdFreeStatusUpsert


class SQLAlchemyAdFreeStatusRepository:
    """Concrete ad-free status repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def find_by_player(self, player_id: UUID) -> AdFreeStatusModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(AdFreeStatusModel).where(
                AdFreeStatusModel.player_id == player_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def upsert(self, data: AdFreeStatusUpsert) -> AdFreeStatusModel:
        async with self._data_ctx.session() as session:
            stmt = select(AdFreeStatusModel).where(
                AdFreeStatusModel.player_id == data.player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                model = AdFreeStatusModel(
                    player_id=data.player_id,
                    is_ad_free=data.is_ad_free,
                    reason=data.reason,
                    granted_at=data.granted_at,
                    expires_at=data.expires_at,
                    granted_by=data.granted_by,
                )
                session.add(model)
            else:
                model.is_ad_free = data.is_ad_free
                model.reason = data.reason
                model.granted_at = data.granted_at
                model.expires_at = data.expires_at
                model.granted_by = data.granted_by
                model.revoked_at = None
                model.revoke_reason = None
            await session.flush()
        return model

    async def revoke(self, player_id: UUID, reason: str) -> AdFreeStatusModel:
        async with self._data_ctx.session() as session:
            stmt = select(AdFreeStatusModel).where(
                AdFreeStatusModel.player_id == player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise self._errors.not_found(
                    "Ad-free status not found",
                    code="NOT_FOUND_PLAYER",
                    player_id=str(player_id),
                )
            model.is_ad_free = False
            model.revoked_at = datetime.now(timezone.utc)
            model.revoke_reason = reason
            await session.flush()
        return model

    async def find_expiring(self, before: datetime) -> list[AdFreeStatusModel]:
        async with self._data_ctx.session() as session:
            stmt = select(AdFreeStatusModel).where(
                AdFreeStatusModel.is_ad_free.is_(True),
                AdFreeStatusModel.expires_at.isnot(None),
                AdFreeStatusModel.expires_at < before,
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
