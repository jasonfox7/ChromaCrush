"""SQLAlchemy implementation of ApiKeyRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select, update

from src.data.models.api_key import ApiKeyModel
from src.data.protocols.api_key_repository import ApiKeyRecord

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


class SQLAlchemyApiKeyRepository:
    """Concrete API key repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``ApiKeyRepositoryProtocol``. Created in the composition root
    and injected into services that need API key data access.
    """

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    # ------------------------------------------------------------------
    # Public API (matches ApiKeyRepositoryProtocol)
    # ------------------------------------------------------------------

    async def create(
        self,
        player_id: UUID,
        key_hash: str,
        key_prefix: str,
        description: str | None = None,
    ) -> ApiKeyRecord:
        """Create a new API key record."""
        self._logger.debug(
            "Creating API key",
            player_id=str(player_id),
            key_prefix=key_prefix,
        )

        model = ApiKeyModel(
            player_id=player_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            description=description,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            record = self._to_record(model)

        self._logger.debug(
            "API key created",
            key_id=str(record.id),
            player_id=str(player_id),
        )

        return record

    async def find_by_id(self, key_id: UUID) -> ApiKeyRecord | None:
        """Find key by ID (includes revoked for audit)."""
        self._logger.debug("Finding API key by id", key_id=str(key_id))

        async with self._data_ctx.session() as session:
            stmt = select(ApiKeyModel).where(ApiKeyModel.id == key_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_record(model)

    async def find_by_prefix(self, prefix: str) -> list[ApiKeyRecord]:
        """Find keys by prefix (for lookup during validation)."""
        self._logger.debug("Finding API keys by prefix", prefix=prefix)

        async with self._data_ctx.session() as session:
            stmt = select(ApiKeyModel).where(ApiKeyModel.key_prefix == prefix)
            result = await session.execute(stmt)
            models = result.scalars().all()

            return [self._to_record(m) for m in models]

    async def find_by_player_id(
        self,
        player_id: UUID,
        include_revoked: bool = False,
    ) -> list[ApiKeyRecord]:
        """Find all keys for a player."""
        self._logger.debug(
            "Finding API keys for player",
            player_id=str(player_id),
            include_revoked=str(include_revoked),
        )

        async with self._data_ctx.session() as session:
            stmt = select(ApiKeyModel).where(ApiKeyModel.player_id == player_id)

            if not include_revoked:
                stmt = stmt.where(ApiKeyModel.revoked_at.is_(None))

            stmt = stmt.order_by(ApiKeyModel.created_at.desc())
            result = await session.execute(stmt)
            models = result.scalars().all()

            return [self._to_record(m) for m in models]

    async def update_last_used(self, key_id: UUID) -> None:
        """Update last_used_at timestamp."""
        now = datetime.now(timezone.utc)

        async with self._data_ctx.session() as session:
            stmt = (
                update(ApiKeyModel)
                .where(ApiKeyModel.id == key_id)
                .values(last_used_at=now)
            )
            await session.execute(stmt)

    async def revoke(self, key_id: UUID) -> None:
        """Revoke a key (soft delete)."""
        self._logger.debug("Revoking API key", key_id=str(key_id))
        now = datetime.now(timezone.utc)

        async with self._data_ctx.session() as session:
            stmt = (
                update(ApiKeyModel)
                .where(ApiKeyModel.id == key_id)
                .values(revoked_at=now)
            )
            await session.execute(stmt)

    async def count_active_for_player(self, player_id: UUID) -> int:
        """Count active (non-revoked) keys for a player."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(func.count())
                .select_from(ApiKeyModel)
                .where(
                    ApiKeyModel.player_id == player_id,
                    ApiKeyModel.revoked_at.is_(None),
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_record(model: ApiKeyModel) -> ApiKeyRecord:
        """Convert an ``ApiKeyModel`` ORM instance to an ``ApiKeyRecord``."""
        return ApiKeyRecord(
            id=model.id,
            player_id=model.player_id,
            key_hash=model.key_hash,
            key_prefix=model.key_prefix,
            description=model.description,
            created_at=model.created_at,
            last_used_at=model.last_used_at,
            revoked_at=model.revoked_at,
        )
