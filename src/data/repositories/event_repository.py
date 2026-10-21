"""SQLAlchemy implementation of event repository protocol."""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy import update as sa_update

from src.data.models.event import EventModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.events.dto import EventCreate, EventDbUpdate


class SQLAlchemyEventRepository:
    """Concrete event repository backed by PostgreSQL via SQLAlchemy."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def create(self, data: EventCreate) -> EventModel:
        """Create a new event record."""
        self._logger.debug("Creating event", name=data.name, event_type=data.event_type)

        model = EventModel(
            name=data.name,
            description=data.description,
            event_type=data.event_type,
            scoring_type=data.scoring_type,
            start_at=data.start_at,
            end_at=data.end_at,
            entry_requirements=data.entry_requirements,
            reward_tiers=data.reward_tiers,
            rules=data.rules,
            max_participants=data.max_participants,
            created_by=data.created_by,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()

        self._logger.debug("Event created", event_id=str(model.id))
        return model

    async def find_by_id(self, event_id: UUID) -> EventModel | None:
        """Find event by ID."""
        async with self._data_ctx.session() as session:
            stmt = select(EventModel).where(EventModel.id == event_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update(self, event_id: UUID, changes: EventDbUpdate) -> EventModel:
        """Update event fields."""
        async with self._data_ctx.session() as session:
            stmt = select(EventModel).where(EventModel.id == event_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Event not found: {event_id}",
                    code="NOT_FOUND_EVENT",
                    event_id=str(event_id),
                )

            for f in dataclasses.fields(changes):
                value = getattr(changes, f.name)
                if value is not None and hasattr(model, f.name):
                    setattr(model, f.name, value)

            await session.flush()

        return model

    async def find_by_status(
        self,
        status: str | None = None,
        event_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[EventModel], int]:
        """Find events by status/type with pagination."""
        async with self._data_ctx.session() as session:
            base_filter = True  # noqa: E712
            conditions = []

            if status is not None:
                conditions.append(EventModel.status == status)
            if event_type is not None:
                conditions.append(EventModel.event_type == event_type)

            # Count query
            count_stmt = select(func.count()).select_from(EventModel)
            for cond in conditions:
                count_stmt = count_stmt.where(cond)
            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            # Data query
            data_stmt = select(EventModel)
            for cond in conditions:
                data_stmt = data_stmt.where(cond)
            data_stmt = (
                data_stmt.order_by(EventModel.start_at.desc())
                .limit(limit)
                .offset(offset)
            )
            data_result = await session.execute(data_stmt)
            models = data_result.scalars().all()

        return list(models), total

    async def find_active(self) -> list[EventModel]:
        """Find all currently active events."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(EventModel)
                .where(EventModel.status == "active")
                .order_by(EventModel.end_at.asc())
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
        return list(models)

    async def find_scheduled_to_start(self, before: datetime) -> list[EventModel]:
        """Find scheduled events whose start_at <= before."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(EventModel)
                .where(EventModel.status == "scheduled")
                .where(EventModel.start_at <= before)
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
        return list(models)

    async def find_active_to_end(self, before: datetime) -> list[EventModel]:
        """Find active events whose end_at <= before."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(EventModel)
                .where(EventModel.status == "active")
                .where(EventModel.end_at <= before)
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
        return list(models)

    async def find_ended_to_finalize(self, before: datetime) -> list[EventModel]:
        """Find ended events whose end_at <= before (ready for finalization)."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(EventModel)
                .where(EventModel.status == "ended")
                .where(EventModel.end_at <= before)
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
        return list(models)

    async def increment_participant_count(self, event_id: UUID) -> int:
        """Atomically increment participant_count and return new value."""
        async with self._data_ctx.session() as session:
            stmt = (
                sa_update(EventModel)
                .where(EventModel.id == event_id)
                .values(participant_count=EventModel.participant_count + 1)
                .returning(EventModel.participant_count)
            )
            result = await session.execute(stmt)
            new_count = result.scalar_one()
        return new_count

    async def decrement_participant_count(self, event_id: UUID) -> int:
        """Atomically decrement participant_count and return new value."""
        async with self._data_ctx.session() as session:
            stmt = (
                sa_update(EventModel)
                .where(EventModel.id == event_id)
                .values(participant_count=EventModel.participant_count - 1)
                .returning(EventModel.participant_count)
            )
            result = await session.execute(stmt)
            new_count = result.scalar_one()
        return new_count
