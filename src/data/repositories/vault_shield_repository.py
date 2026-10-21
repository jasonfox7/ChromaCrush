"""SQLAlchemy implementation of VaultShieldRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, func, select

from src.data.models.vault_shield import VaultShieldModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


@dataclass
class VaultShieldRecord:
    """Lightweight record returned by the repository."""

    player_id: UUID
    activated_at: datetime
    expires_at: datetime
    duration_hours: int


class SQLAlchemyVaultShieldRepository:
    """Concrete vault shield repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``VaultShieldRepositoryProtocol``.
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
    # Public API
    # ------------------------------------------------------------------

    async def find_by_player(self, player_id: UUID) -> VaultShieldRecord | None:
        """Find the active shield for a player."""
        self._logger.debug("Finding shield for player", player_id=str(player_id))

        async with self._data_ctx.session() as session:
            stmt = select(VaultShieldModel).where(
                VaultShieldModel.player_id == player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_record(model)

    async def create(
        self,
        player_id: UUID,
        activated_at: datetime,
        expires_at: datetime,
        duration_hours: int,
    ) -> VaultShieldRecord:
        """Create a new shield record."""
        self._logger.debug(
            "Creating shield",
            player_id=str(player_id),
            expires_at=expires_at.isoformat(),
        )

        model = VaultShieldModel(
            player_id=player_id,
            activated_at=activated_at,
            expires_at=expires_at,
            duration_hours=duration_hours,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            record = self._to_record(model)

        self._logger.debug("Shield created", player_id=str(player_id))
        return record

    async def delete(self, player_id: UUID) -> None:
        """Delete a player's shield record."""
        self._logger.debug("Deleting shield", player_id=str(player_id))

        async with self._data_ctx.session() as session:
            stmt = select(VaultShieldModel).where(
                VaultShieldModel.player_id == player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Shield not found for player: {player_id}",
                    code="NOT_FOUND_RESOURCE",
                    player_id=str(player_id),
                )

            await session.delete(model)

        self._logger.debug("Shield deleted", player_id=str(player_id))

    async def delete_expired(self) -> int:
        """Delete all expired shields. Returns count deleted."""
        now = datetime.now(timezone.utc)
        self._logger.debug("Deleting expired shields", as_of=now.isoformat())

        async with self._data_ctx.session() as session:
            # Count first for return value
            count_stmt = (
                select(func.count())
                .select_from(VaultShieldModel)
                .where(VaultShieldModel.expires_at < now)
            )
            count_result = await session.execute(count_stmt)
            count = count_result.scalar_one()

            if count > 0:
                del_stmt = delete(VaultShieldModel).where(
                    VaultShieldModel.expires_at < now
                )
                await session.execute(del_stmt)

        self._logger.debug("Expired shields deleted", count=count)
        return count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_record(model: VaultShieldModel) -> VaultShieldRecord:
        """Convert an ORM model to a lightweight record."""
        return VaultShieldRecord(
            player_id=model.player_id,
            activated_at=model.activated_at,
            expires_at=model.expires_at,
            duration_hours=model.duration_hours,
        )
