"""Event lifecycle sub-service.

Handles CRUD operations for events: create, get, list, update, cancel,
and active event retrieval.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.core.types.game import EventId, PlayerId
from src.modules.events._data_mapper import (
    parse_requirements,
    record_to_event,
    record_to_summary,
)
from src.modules.events.dto import (
    EventCreate,
    EventDbUpdate,
    EventUpdate,
    PaginatedResult,
)
from src.modules.events.types import (
    Event,
    EventStatus,
    EventSummary,
    EventType,
)

if TYPE_CHECKING:
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.events.protocols import (
        EnergyServiceProtocol,
        EventLeaderboardRepositoryProtocol,
        EventParticipantRepositoryProtocol,
        EventRepositoryProtocol,
    )

_MIN_EVENT_NAME_LENGTH = 3
_MAX_EVENT_NAME_LENGTH = 100
_MAX_LIST_LIMIT = 100
_MAX_REASON_LENGTH = 500


class EventLifecycleService:
    """Manages event CRUD and status transitions."""

    def __init__(
        self,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        energy_service: EnergyServiceProtocol,
        event_repo: EventRepositoryProtocol,
        participant_repo: EventParticipantRepositoryProtocol,
        leaderboard_repo: EventLeaderboardRepositoryProtocol,
    ) -> None:
        self._logger = logger
        self._errors = errors
        self._energy_service = energy_service
        self._event_repo = event_repo
        self._participant_repo = participant_repo
        self._leaderboard_repo = leaderboard_repo

    async def create_event(self, event_data: EventCreate) -> Event:
        """Create a new event (admin operation)."""
        # Validate inputs
        if not event_data.name or len(event_data.name) < _MIN_EVENT_NAME_LENGTH:
            raise self._errors.validation(
                f"Event name must be at least {_MIN_EVENT_NAME_LENGTH} characters",
                code="VALIDATION_INVALID_INPUT",
                field="name",
                reason="too_short",
            )
        if len(event_data.name) > _MAX_EVENT_NAME_LENGTH:
            raise self._errors.validation(
                f"Event name must be at most {_MAX_EVENT_NAME_LENGTH} characters",
                code="VALIDATION_INVALID_INPUT",
                field="name",
                reason="too_long",
            )
        if event_data.start_at >= event_data.end_at:
            raise self._errors.validation(
                "Event end_at must be after start_at",
                code="VALIDATION_INVALID_INPUT",
                field="end_at",
                reason="must_be_after_start_at",
            )

        record = await self._event_repo.create(event_data)
        event = record_to_event(record)

        self._logger.info(
            "Event created",
            event_id=str(event.id),
            event_type=event_data.event_type,
            start_at=str(event_data.start_at),
            end_at=str(event_data.end_at),
        )

        return event

    async def get_event(self, event_id: EventId) -> Event:
        """Retrieve event details."""
        record = await self._event_repo.find_by_id(event_id)
        if record is None:
            raise self._errors.not_found(
                "Event not found",
                code="NOT_FOUND_EVENT",
                event_id=str(event_id),
            )
        return record_to_event(record)

    async def list_events(
        self,
        status: EventStatus | None = None,
        event_type: EventType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResult[EventSummary]:
        """List events with optional filtering."""
        if limit < 1 or limit > _MAX_LIST_LIMIT:
            raise self._errors.validation(
                f"Limit must be between 1 and {_MAX_LIST_LIMIT}",
                code="VALIDATION_INVALID_INPUT",
                field="limit",
                max=_MAX_LIST_LIMIT,
            )

        status_str = status.value if status is not None else None
        type_str = event_type.value if event_type is not None else None

        records, total = await self._event_repo.find_by_status(
            status=status_str,
            event_type=type_str,
            limit=limit,
            offset=offset,
        )

        now = datetime.now(timezone.utc)
        summaries = [record_to_summary(r, now) for r in records]

        return PaginatedResult(
            items=summaries,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_active_events(self) -> list[Event]:
        """Get all currently active events."""
        records = await self._event_repo.find_active()
        return [record_to_event(r) for r in records]

    async def update_event(
        self,
        event_id: EventId,
        updates: EventUpdate,
    ) -> Event:
        """Update event details (admin operation, limited fields)."""
        record = await self._event_repo.find_by_id(event_id)
        if record is None:
            raise self._errors.not_found(
                "Event not found",
                code="NOT_FOUND_EVENT",
                event_id=str(event_id),
            )

        # Build db update from the caller update
        db_update = EventDbUpdate(
            name=updates.name,
            description=updates.description,
            start_at=updates.start_at,
            end_at=updates.end_at,
            entry_requirements=updates.entry_requirements,
            reward_tiers=updates.reward_tiers,
            rules=updates.rules,
            max_participants=updates.max_participants,
        )

        updated = await self._event_repo.update(event_id, db_update)
        return record_to_event(updated)

    async def cancel_event(self, event_id: EventId, reason: str) -> Event:
        """Cancel an event before completion (admin operation)."""
        if len(reason) > _MAX_REASON_LENGTH:
            raise self._errors.validation(
                "Cancellation reason too long",
                code="VALIDATION_INVALID_INPUT",
                field="reason",
                reason=f"max_{_MAX_REASON_LENGTH}_chars",
            )

        record = await self._event_repo.find_by_id(event_id)
        if record is None:
            raise self._errors.not_found(
                "Event not found",
                code="NOT_FOUND_EVENT",
                event_id=str(event_id),
            )

        if record.status == EventStatus.FINALIZED.value:
            raise self._errors.conflict(
                "Cannot cancel a finalized event",
                code="CONFLICT_EVENT_ALREADY_FINALIZED",
                event_id=str(event_id),
                finalized_at=(
                    record.finalized_at.isoformat() if record.finalized_at else ""
                ),
            )

        now = datetime.now(timezone.utc)
        updated = await self._event_repo.update(
            event_id,
            EventDbUpdate(
                status=EventStatus.CANCELLED.value,
                cancelled_at=now,
                cancellation_reason=reason,
            ),
        )

        # Refund energy if entry cost was charged
        requirements = parse_requirements(record.entry_requirements)
        if requirements.energy_cost > 0:
            participants, _ = await self._participant_repo.find_by_event(
                event_id,
                active_only=True,
                limit=100000,
                offset=0,
            )
            for p in participants:
                await self._energy_service.refund_heart(
                    PlayerId(p.player_id),
                    amount=requirements.energy_cost,
                    reason="event_cancelled",
                )

        # Clear leaderboard
        await self._leaderboard_repo.clear_leaderboard(event_id)

        affected = record.participant_count
        self._logger.warn(
            "Event cancelled",
            event_id=str(event_id),
            reason=reason,
            affected_participants=affected,
        )

        return record_to_event(updated)
