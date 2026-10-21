"""SQLAlchemy implementation of CampaignAttemptRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, update as sa_update

from src.data.models.campaign_attempt import CampaignAttemptModel
from src.data.protocols.campaign_attempt_repository import CampaignAttemptRecord

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


class SQLAlchemyCampaignAttemptRepository:
    """Concrete campaign attempt repository backed by PostgreSQL.

    Satisfies ``CampaignAttemptRepositoryProtocol``. Created in the
    composition root and injected into the campaign service.
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

    async def create(
        self,
        player_id: UUID,
        level_number: int,
        board_seed: int,
        board_state: dict,
        moves_remaining: int,
        obstacles_remaining: int,
    ) -> CampaignAttemptRecord:
        """Create a new campaign attempt."""
        self._logger.debug(
            "Creating campaign attempt",
            player_id=str(player_id),
            level_number=level_number,
        )

        model = CampaignAttemptModel(
            player_id=player_id,
            level_number=level_number,
            board_seed=board_seed,
            board_state=board_state,
            moves_remaining=moves_remaining,
            obstacles_remaining=obstacles_remaining,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            record = self._to_record(model)

        self._logger.debug(
            "Campaign attempt created",
            attempt_id=str(record.id),
            player_id=str(player_id),
        )
        return record

    async def find_by_id(self, attempt_id: UUID) -> CampaignAttemptRecord | None:
        """Find an attempt by its UUID."""
        async with self._data_ctx.session() as session:
            stmt = select(CampaignAttemptModel).where(
                CampaignAttemptModel.id == attempt_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None
            return self._to_record(model)

    async def find_active_by_player(
        self, player_id: UUID
    ) -> CampaignAttemptRecord | None:
        """Find the player's current in-progress attempt."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(CampaignAttemptModel)
                .where(CampaignAttemptModel.player_id == player_id)
                .where(CampaignAttemptModel.status == "in_progress")
                .order_by(CampaignAttemptModel.started_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None
            return self._to_record(model)

    async def update(
        self,
        attempt_id: UUID,
        *,
        board_state: dict | None = None,
        moves_remaining: int | None = None,
        obstacles_remaining: int | None = None,
        status: str | None = None,
        score: int | None = None,
    ) -> CampaignAttemptRecord:
        """Update fields on an existing attempt."""
        async with self._data_ctx.session() as session:
            stmt = select(CampaignAttemptModel).where(
                CampaignAttemptModel.id == attempt_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Campaign attempt not found: {attempt_id}",
                    code="NOT_FOUND_CAMPAIGN_ATTEMPT",
                    attempt_id=str(attempt_id),
                )

            if board_state is not None:
                model.board_state = board_state
            if moves_remaining is not None:
                model.moves_remaining = moves_remaining
            if obstacles_remaining is not None:
                model.obstacles_remaining = obstacles_remaining
            if status is not None:
                model.status = status
                if status in ("won", "lost", "abandoned"):
                    model.completed_at = datetime.now(timezone.utc)
            if score is not None:
                model.score = score

            await session.flush()
            record = self._to_record(model)

        return record

    async def find_stale_attempts(self, cutoff: datetime) -> list[UUID]:
        """Find in-progress attempts started before *cutoff*.

        Args:
            cutoff: Attempts with ``started_at`` before this are stale.

        Returns:
            List of stale attempt UUIDs.
        """
        async with self._data_ctx.session() as session:
            stmt = (
                select(CampaignAttemptModel.id)
                .where(CampaignAttemptModel.status == "in_progress")
                .where(CampaignAttemptModel.started_at < cutoff)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def bulk_abandon(self, attempt_ids: list[UUID]) -> int:
        """Mark multiple attempts as abandoned.

        Args:
            attempt_ids: Attempt UUIDs to abandon.

        Returns:
            Number of rows updated.
        """
        if not attempt_ids:
            return 0

        async with self._data_ctx.session() as session:
            stmt = (
                sa_update(CampaignAttemptModel)
                .where(CampaignAttemptModel.id.in_(attempt_ids))
                .values(
                    status="abandoned",
                    completed_at=datetime.now(timezone.utc),
                )
            )
            result = await session.execute(stmt)
            return result.rowcount or 0

    @staticmethod
    def _to_record(model: CampaignAttemptModel) -> CampaignAttemptRecord:
        """Convert an ORM model to a lightweight record."""
        return CampaignAttemptRecord(
            id=model.id,
            player_id=model.player_id,
            level_number=model.level_number,
            board_seed=model.board_seed,
            board_state=model.board_state,
            moves_remaining=model.moves_remaining,
            obstacles_remaining=model.obstacles_remaining,
            status=model.status,
            score=model.score,
        )
