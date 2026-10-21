"""Event scheduling sub-service.

Handles background activation, deactivation, and auto-finalization
of events based on their schedule. Calls back to the facade's
``finalize_event`` to avoid circular imports.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from src.core.types.game import EventId
from src.modules.events.dto import EventDbUpdate
from src.modules.events.types import EventStatus, ScheduledEventResult

if TYPE_CHECKING:
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.events.protocols import EventRepositoryProtocol


class EventSchedulingService:
    """Processes scheduled event activations, endings, and auto-finalizations."""

    def __init__(
        self,
        logger: LoggerProtocol,
        data_ctx: Any,
        event_repo: EventRepositoryProtocol,
        auto_finalize_delay: int,
        facade: Any,
    ) -> None:
        self._logger = logger
        self._data_ctx = data_ctx
        self._event_repo = event_repo
        self._auto_finalize_delay = auto_finalize_delay
        self._facade = facade

    async def process_scheduled_events(self) -> ScheduledEventResult:
        """Background operation to activate/deactivate events based on schedule."""
        now = datetime.now(timezone.utc)
        activated: list[EventId] = []
        deactivated: list[EventId] = []
        finalized: list[EventId] = []

        # 1. Activate scheduled events that should start
        to_activate = await self._event_repo.find_scheduled_to_start(before=now)
        for event in to_activate:
            try:
                await self._event_repo.update(
                    event.id,
                    EventDbUpdate(
                        status=EventStatus.ACTIVE.value,
                        activated_at=now,
                    ),
                )
                # Add to active set in Redis
                await self._data_ctx.redis.sadd(
                    "chromacrush:event:active",
                    str(event.id),
                )
                activated.append(EventId(event.id))
                self._logger.info(
                    "Scheduled event activated",
                    event_id=str(event.id),
                )
            except Exception as e:
                self._logger.error(
                    "Failed to activate event",
                    event_id=str(event.id),
                    error=str(e),
                )

        # 2. Deactivate active events that should end
        to_deactivate = await self._event_repo.find_active_to_end(before=now)
        for event in to_deactivate:
            try:
                await self._event_repo.update(
                    event.id,
                    EventDbUpdate(status=EventStatus.ENDED.value),
                )
                await self._data_ctx.redis.srem(
                    "chromacrush:event:active",
                    str(event.id),
                )
                deactivated.append(EventId(event.id))
                self._logger.info(
                    "Scheduled event ended",
                    event_id=str(event.id),
                )
            except Exception as e:
                self._logger.error(
                    "Failed to end event",
                    event_id=str(event.id),
                    error=str(e),
                )

        # 3. Auto-finalize ended events after delay
        finalize_cutoff = now - timedelta(minutes=self._auto_finalize_delay)
        to_finalize = await self._event_repo.find_ended_to_finalize(
            before=finalize_cutoff,
        )
        for event in to_finalize:
            try:
                await self._facade.finalize_event(EventId(event.id))
                finalized.append(EventId(event.id))
            except Exception as e:
                self._logger.error(
                    "Finalization failed",
                    event_id=str(event.id),
                    error=str(e),
                )

        return ScheduledEventResult(
            activated=activated,
            deactivated=deactivated,
            finalized=finalized,
            processed_at=now,
        )
