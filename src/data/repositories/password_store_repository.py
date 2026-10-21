"""SQLAlchemy implementation of PasswordStoreProtocol.

Provides password hash read/write access via the PlayerModel without
exposing the hash through the Player domain type. Used by the auth
service for credential verification and password changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, update

from src.data.models.player import PlayerModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol


class SQLAlchemyPasswordStoreRepository:
    """Concrete password store backed by PostgreSQL via SQLAlchemy.

    Satisfies ``PasswordStoreProtocol``. Created in the composition root
    and injected into services that need password hash access.
    """

    def __init__(self, data_ctx: DataContextProtocol) -> None:
        self._data_ctx = data_ctx

    async def get_password_hash(self, player_id: UUID) -> str | None:
        async with self._data_ctx.session() as session:
            stmt = select(PlayerModel.password_hash).where(PlayerModel.id == player_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def set_password_hash(self, player_id: UUID, password_hash: str) -> None:
        async with self._data_ctx.session() as session:
            stmt = (
                update(PlayerModel)
                .where(PlayerModel.id == player_id)
                .values(password_hash=password_hash)
            )
            await session.execute(stmt)
