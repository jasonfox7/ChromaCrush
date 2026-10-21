"""SQLAlchemy implementation of event participant repository protocol."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy import update as sa_update

from src.data.models.event import EventModel
from src.data.models.event_match import EventMatchRecordModel
from src.data.models.event_participant import EventParticipantModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.events.dto import (
        EventMatchCreate,
        ParticipantCreate,
        ParticipantUpdate,
    )


class SQLAlchemyEventParticipantRepository:
    """Concrete event participant repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def create(self, data: ParticipantCreate) -> EventParticipantModel:
        """Add participant to event."""
        model = EventParticipantModel(
            event_id=data.event_id,
            player_id=data.player_id,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model

    async def find_by_event_and_player(
        self,
        event_id: UUID,
        player_id: UUID,
    ) -> EventParticipantModel | None:
        """Find specific participant."""
        async with self._data_ctx.session() as session:
            stmt = select(EventParticipantModel).where(
                and_(
                    EventParticipantModel.event_id == event_id,
                    EventParticipantModel.player_id == player_id,
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update(
        self,
        event_id: UUID,
        player_id: UUID,
        changes: ParticipantUpdate,
    ) -> EventParticipantModel:
        """Update participant record."""
        async with self._data_ctx.session() as session:
            stmt = select(EventParticipantModel).where(
                and_(
                    EventParticipantModel.event_id == event_id,
                    EventParticipantModel.player_id == player_id,
                )
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    "Participant not found",
                    code="FORBIDDEN_NOT_EVENT_PARTICIPANT",
                    event_id=str(event_id),
                    player_id=str(player_id),
                )

            for f in dataclasses.fields(changes):
                value = getattr(changes, f.name)
                if value is not None and hasattr(model, f.name):
                    setattr(model, f.name, value)

            await session.flush()
        return model

    async def find_by_event(
        self,
        event_id: UUID,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[EventParticipantModel], int]:
        """Find participants in an event."""
        async with self._data_ctx.session() as session:
            conditions = [EventParticipantModel.event_id == event_id]
            if active_only:
                conditions.append(EventParticipantModel.left_at.is_(None))

            count_stmt = (
                select(func.count())
                .select_from(EventParticipantModel)
                .where(and_(*conditions))
            )
            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            data_stmt = (
                select(EventParticipantModel)
                .where(and_(*conditions))
                .order_by(EventParticipantModel.total_score.desc())
                .limit(limit)
                .offset(offset)
            )
            data_result = await session.execute(data_stmt)
            models = data_result.scalars().all()
        return list(models), total

    async def find_by_player(
        self,
        player_id: UUID,
        include_past: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[EventParticipantModel], int]:
        """Find events a player is/was in (joined to events table)."""
        async with self._data_ctx.session() as session:
            conditions = [EventParticipantModel.player_id == player_id]
            if not include_past:
                conditions.append(EventParticipantModel.left_at.is_(None))

            count_stmt = (
                select(func.count())
                .select_from(EventParticipantModel)
                .where(and_(*conditions))
            )
            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            data_stmt = (
                select(EventParticipantModel)
                .where(and_(*conditions))
                .order_by(EventParticipantModel.joined_at.desc())
                .limit(limit)
                .offset(offset)
            )
            data_result = await session.execute(data_stmt)
            models = data_result.scalars().all()
        return list(models), total

    async def find_ranked_by_event(
        self,
        event_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EventParticipantModel]:
        """Find participants ordered by score (for DB fallback)."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(EventParticipantModel)
                .where(
                    and_(
                        EventParticipantModel.event_id == event_id,
                        EventParticipantModel.left_at.is_(None),
                    )
                )
                .order_by(EventParticipantModel.total_score.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
        return list(models)

    async def count_by_event(self, event_id: UUID, active_only: bool = True) -> int:
        """Count participants in an event."""
        async with self._data_ctx.session() as session:
            conditions = [EventParticipantModel.event_id == event_id]
            if active_only:
                conditions.append(EventParticipantModel.left_at.is_(None))

            stmt = (
                select(func.count())
                .select_from(EventParticipantModel)
                .where(and_(*conditions))
            )
            result = await session.execute(stmt)
            return result.scalar_one()

    async def bulk_update_ranks(
        self,
        event_id: UUID,
        ranks: list[tuple[UUID, int]],
    ) -> int:
        """Bulk update ranks from leaderboard. Returns count updated."""
        if not ranks:
            return 0

        updated = 0
        async with self._data_ctx.session() as session:
            for player_id, rank in ranks:
                stmt = (
                    sa_update(EventParticipantModel)
                    .where(
                        and_(
                            EventParticipantModel.event_id == event_id,
                            EventParticipantModel.player_id == player_id,
                        )
                    )
                    .values(current_rank=rank)
                )
                result = await session.execute(stmt)
                updated += result.rowcount or 0
        return updated

    async def find_eligible_for_rewards(
        self,
        event_id: UUID,
        min_matches: int,
    ) -> list[EventParticipantModel]:
        """Find participants who qualify for rewards."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(EventParticipantModel)
                .where(
                    and_(
                        EventParticipantModel.event_id == event_id,
                        EventParticipantModel.left_at.is_(None),
                        EventParticipantModel.matches_played >= min_matches,
                    )
                )
                .order_by(EventParticipantModel.current_rank.asc())
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
        return list(models)

    async def create_event_match(self, data: EventMatchCreate) -> EventMatchRecordModel:
        """Record a match entry for an event."""
        model = EventMatchRecordModel(
            event_id=data.event_id,
            player_id=data.player_id,
            match_id=data.match_id,
            score=data.score,
            chain_count=data.chain_count,
            gems_cleared=data.gems_cleared,
            special_gems_activated=data.special_gems_activated,
        )
        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
        return model
