"""SQLAlchemy implementation of SessionRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import delete, func, select, update

from src.data.models.session import SessionModel
from src.data.protocols.session_repository import SessionRecord

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


class SQLAlchemySessionRepository:
    """Concrete session repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``SessionRepositoryProtocol``. Created in the composition root
    and injected into services that need session data access.
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
    # Public API (matches SessionRepositoryProtocol)
    # ------------------------------------------------------------------

    async def create(
        self,
        player_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        device_info: str | None = None,
        session_id: UUID | None = None,
    ) -> SessionRecord:
        """Create a new session."""
        self._logger.debug("Creating session", player_id=str(player_id))

        now = datetime.now(timezone.utc)
        kwargs: dict[str, Any] = {
            "player_id": player_id,
            "refresh_token_hash": refresh_token_hash,
            "device_info": device_info,
            "last_used_at": now,
            "expires_at": expires_at,
        }
        if session_id is not None:
            kwargs["id"] = session_id

        model = SessionModel(**kwargs)

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            record = self._to_record(model)

        self._logger.debug(
            "Session created",
            session_id=str(record.id),
            player_id=str(player_id),
        )

        return record

    async def find_by_id(self, session_id: UUID) -> SessionRecord | None:
        """Find session by ID (includes revoked for validation)."""
        self._logger.debug("Finding session by id", session_id=str(session_id))

        async with self._data_ctx.session() as session:
            stmt = select(SessionModel).where(SessionModel.id == session_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_record(model)

    async def find_by_player_id(
        self,
        player_id: UUID,
        include_revoked: bool = False,
    ) -> list[SessionRecord]:
        """Find all sessions for a player."""
        self._logger.debug(
            "Finding sessions for player",
            player_id=str(player_id),
            include_revoked=str(include_revoked),
        )

        async with self._data_ctx.session() as session:
            stmt = select(SessionModel).where(SessionModel.player_id == player_id)

            if not include_revoked:
                stmt = stmt.where(SessionModel.revoked_at.is_(None))

            stmt = stmt.order_by(SessionModel.created_at.desc())
            result = await session.execute(stmt)
            models = result.scalars().all()

            return [self._to_record(m) for m in models]

    async def update_last_used(self, session_id: UUID) -> None:
        """Update last_used_at timestamp."""
        now = datetime.now(timezone.utc)

        async with self._data_ctx.session() as session:
            stmt = (
                update(SessionModel)
                .where(SessionModel.id == session_id)
                .values(last_used_at=now)
            )
            await session.execute(stmt)

    async def revoke(self, session_id: UUID) -> None:
        """Revoke a session (soft delete)."""
        self._logger.debug("Revoking session", session_id=str(session_id))
        now = datetime.now(timezone.utc)

        async with self._data_ctx.session() as session:
            stmt = (
                update(SessionModel)
                .where(SessionModel.id == session_id)
                .values(revoked_at=now)
            )
            await session.execute(stmt)

    async def revoke_all_for_player(self, player_id: UUID) -> int:
        """Revoke all active sessions for a player. Returns count revoked."""
        self._logger.debug("Revoking all sessions for player", player_id=str(player_id))
        now = datetime.now(timezone.utc)

        async with self._data_ctx.session() as session:
            stmt = (
                update(SessionModel)
                .where(
                    SessionModel.player_id == player_id,
                    SessionModel.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            result = await session.execute(stmt)
            count = result.rowcount

        self._logger.debug(
            "Sessions revoked",
            player_id=str(player_id),
            count=count,
        )

        return count

    async def count_active_for_player(self, player_id: UUID) -> int:
        """Count active (non-revoked, non-expired) sessions."""
        now = datetime.now(timezone.utc)

        async with self._data_ctx.session() as session:
            stmt = (
                select(func.count())
                .select_from(SessionModel)
                .where(
                    SessionModel.player_id == player_id,
                    SessionModel.revoked_at.is_(None),
                    SessionModel.expires_at > now,
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one()

    async def cleanup_expired(self) -> int:
        """Delete sessions expired more than 7 days ago."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        async with self._data_ctx.session() as session:
            stmt = delete(SessionModel).where(SessionModel.expires_at < cutoff)
            result = await session.execute(stmt)
            count = result.rowcount

        self._logger.info("Expired sessions cleaned up", count=count)

        return count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_record(model: SessionModel) -> SessionRecord:
        """Convert a ``SessionModel`` ORM instance to a ``SessionRecord``."""
        return SessionRecord(
            id=model.id,
            player_id=model.player_id,
            refresh_token_hash=model.refresh_token_hash,
            device_info=model.device_info,
            created_at=model.created_at,
            last_used_at=model.last_used_at,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
        )
