"""Protocol interface for event ad opportunity repository."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class EventAdOpportunityRepositoryProtocol(Protocol):
    """Repository interface for event ad opportunities (PostgreSQL)."""

    async def find_by_event(self, event_id: UUID) -> list[Any]: ...
    async def find_by_id(self, event_id: UUID, opportunity_id: str) -> Any | None: ...
    async def create(self, data: Any) -> Any: ...
