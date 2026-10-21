"""SQLAlchemy implementation of PlayerCardRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update

from src.data.models.player_card import PlayerCardModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


@dataclass
class PlayerCardRecord:
    """Lightweight record returned by the repository.

    The service layer maps this to PlayerCard DTOs.
    """

    id: UUID
    player_id: UUID
    card_id: int
    position: int
    acquired_at: datetime
    source: str
    source_id: str | None
    level: int
    created_at: datetime


class SQLAlchemyPlayerCardRepository:
    """Concrete player card repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``PlayerCardRepositoryProtocol``.
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

    async def find_by_id(self, card_instance_id: UUID) -> PlayerCardRecord | None:
        """Find a player card by UUID."""
        self._logger.debug(
            "Finding player card by id", card_instance_id=str(card_instance_id)
        )

        async with self._data_ctx.session() as session:
            stmt = select(PlayerCardModel).where(PlayerCardModel.id == card_instance_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_record(model)

    async def find_by_player(
        self,
        player_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PlayerCardRecord], int]:
        """Find cards by owner, ordered by position. Returns (items, total)."""
        self._logger.debug(
            "Finding cards by player",
            player_id=str(player_id),
        )

        async with self._data_ctx.session() as session:
            base = select(PlayerCardModel).where(PlayerCardModel.player_id == player_id)

            # Count
            count_stmt = select(func.count()).select_from(base.subquery())
            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            # Data
            data_stmt = (
                base.order_by(PlayerCardModel.position).limit(limit).offset(offset)
            )
            data_result = await session.execute(data_stmt)
            models = data_result.scalars().all()

            items = [self._to_record(m) for m in models]

        return items, total

    async def find_equipped(self, player_id: UUID) -> list[PlayerCardRecord]:
        """Find equipped cards (positions 1-3) for a player."""
        self._logger.debug(
            "Finding equipped cards",
            player_id=str(player_id),
        )

        async with self._data_ctx.session() as session:
            stmt = (
                select(PlayerCardModel)
                .where(PlayerCardModel.player_id == player_id)
                .where(PlayerCardModel.position <= 3)
                .order_by(PlayerCardModel.position)
            )
            result = await session.execute(stmt)
            models = result.scalars().all()

            return [self._to_record(m) for m in models]

    async def count_by_player(self, player_id: UUID) -> int:
        """Count total cards owned by a player."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(func.count())
                .select_from(PlayerCardModel)
                .where(PlayerCardModel.player_id == player_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one()

    async def find_max_position(self, player_id: UUID) -> int:
        """Get the highest position value for a player's cards."""
        async with self._data_ctx.session() as session:
            stmt = select(func.max(PlayerCardModel.position)).where(
                PlayerCardModel.player_id == player_id
            )
            result = await session.execute(stmt)
            max_pos = result.scalar_one_or_none()
            return max_pos if max_pos is not None else 0

    async def create(
        self,
        player_id: UUID,
        card_id: int,
        position: int,
        source: str,
        source_id: str | None = None,
    ) -> PlayerCardRecord:
        """Create a new player card record."""
        self._logger.debug(
            "Creating player card",
            player_id=str(player_id),
            card_id=card_id,
            position=position,
            source=source,
        )

        model = PlayerCardModel(
            player_id=player_id,
            card_id=card_id,
            position=position,
            source=source,
            source_id=source_id,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            record = self._to_record(model)

        self._logger.debug("Player card created", card_instance_id=str(record.id))
        return record

    async def update_position(
        self,
        card_instance_id: UUID,
        new_position: int,
    ) -> PlayerCardRecord:
        """Update the position of a card."""
        self._logger.debug(
            "Updating card position",
            card_instance_id=str(card_instance_id),
            new_position=new_position,
        )

        async with self._data_ctx.session() as session:
            stmt = select(PlayerCardModel).where(PlayerCardModel.id == card_instance_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Player card not found: {card_instance_id}",
                    code="NOT_FOUND_PLAYER_CARD",
                    card_instance_id=str(card_instance_id),
                )

            model.position = new_position
            await session.flush()
            record = self._to_record(model)

        return record

    async def delete(self, card_instance_id: UUID) -> None:
        """Delete a player card record."""
        self._logger.debug(
            "Deleting player card", card_instance_id=str(card_instance_id)
        )

        async with self._data_ctx.session() as session:
            stmt = select(PlayerCardModel).where(PlayerCardModel.id == card_instance_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Player card not found: {card_instance_id}",
                    code="NOT_FOUND_PLAYER_CARD",
                    card_instance_id=str(card_instance_id),
                )

            await session.delete(model)

        self._logger.debug(
            "Player card deleted", card_instance_id=str(card_instance_id)
        )

    async def delete_multiple(self, card_instance_ids: list[UUID]) -> None:
        """Delete multiple player card records."""
        if not card_instance_ids:
            return

        self._logger.debug(
            "Deleting multiple player cards",
            count=len(card_instance_ids),
        )

        async with self._data_ctx.session() as session:
            stmt = sa_delete(PlayerCardModel).where(
                PlayerCardModel.id.in_(card_instance_ids)
            )
            await session.execute(stmt)

        self._logger.debug(
            "Multiple player cards deleted",
            count=len(card_instance_ids),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_record(model: PlayerCardModel) -> PlayerCardRecord:
        """Convert an ORM model to a lightweight record."""
        return PlayerCardRecord(
            id=model.id,
            player_id=model.player_id,
            card_id=model.card_id,
            position=model.position,
            acquired_at=model.acquired_at,
            source=model.source,
            source_id=model.source_id,
            level=model.level,
            created_at=model.created_at,
        )
