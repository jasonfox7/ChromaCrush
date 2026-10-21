"""SQLAlchemy implementation of RaidLogRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, or_, select

from src.data.models.raid_log import RaidLogModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


@dataclass
class RaidLogRecord:
    """Lightweight record returned by the repository."""

    id: UUID
    attacker_id: UUID
    defender_id: UUID
    success: bool
    artifact_id: UUID | None
    artifact_type_id: str | None
    timestamp: datetime


class SQLAlchemyRaidLogRepository:
    """Concrete raid log repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``RaidLogRepositoryProtocol``.
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

    async def create(
        self,
        attacker_id: UUID,
        defender_id: UUID,
        success: bool,
        artifact_id: UUID | None = None,
        artifact_type_id: str | None = None,
    ) -> RaidLogRecord:
        """Create a new raid log entry."""
        self._logger.debug(
            "Creating raid log",
            attacker_id=str(attacker_id),
            defender_id=str(defender_id),
            success=success,
        )

        model = RaidLogModel(
            attacker_id=attacker_id,
            defender_id=defender_id,
            success=success,
            artifact_id=artifact_id,
            artifact_type_id=artifact_type_id,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            record = self._to_record(model)

        self._logger.debug("Raid log created", raid_id=str(record.id))
        return record

    async def find_by_player(
        self,
        player_id: UUID,
        as_attacker: bool = True,
        as_defender: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RaidLogRecord], int]:
        """Find raid logs involving a player. Returns (items, total)."""
        self._logger.debug(
            "Finding raid logs for player",
            player_id=str(player_id),
            as_attacker=as_attacker,
            as_defender=as_defender,
        )

        async with self._data_ctx.session() as session:
            # Build filter conditions
            conditions = []
            if as_attacker:
                conditions.append(RaidLogModel.attacker_id == player_id)
            if as_defender:
                conditions.append(RaidLogModel.defender_id == player_id)

            if not conditions:
                return [], 0

            where_clause = or_(*conditions) if len(conditions) > 1 else conditions[0]

            # Count
            count_stmt = (
                select(func.count()).select_from(RaidLogModel).where(where_clause)
            )
            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            # Data
            data_stmt = (
                select(RaidLogModel)
                .where(where_clause)
                .order_by(RaidLogModel.timestamp.desc())
                .limit(limit)
                .offset(offset)
            )
            data_result = await session.execute(data_stmt)
            models = data_result.scalars().all()

            items = [self._to_record(m) for m in models]

        return items, total

    async def find_last_raid_between(
        self,
        attacker_id: UUID,
        defender_id: UUID,
    ) -> RaidLogRecord | None:
        """Find the most recent raid from attacker to defender."""
        self._logger.debug(
            "Finding last raid between players",
            attacker_id=str(attacker_id),
            defender_id=str(defender_id),
        )

        async with self._data_ctx.session() as session:
            stmt = (
                select(RaidLogModel)
                .where(RaidLogModel.attacker_id == attacker_id)
                .where(RaidLogModel.defender_id == defender_id)
                .order_by(RaidLogModel.timestamp.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_record(model)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_record(model: RaidLogModel) -> RaidLogRecord:
        """Convert an ORM model to a lightweight record."""
        return RaidLogRecord(
            id=model.id,
            attacker_id=model.attacker_id,
            defender_id=model.defender_id,
            success=model.success,
            artifact_id=model.artifact_id,
            artifact_type_id=model.artifact_type_id,
            timestamp=model.timestamp,
        )
