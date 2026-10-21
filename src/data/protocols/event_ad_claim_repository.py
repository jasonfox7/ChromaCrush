"""Protocol interface for event ad claim repository."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class EventAdClaimRepositoryProtocol(Protocol):
    """Repository interface for event ad claims (PostgreSQL)."""

    async def create(self, data: Any) -> Any: ...
    async def count_claims(
        self, event_id: UUID, opportunity_id: str, player_id: UUID
    ) -> int: ...
    async def find_last_claim(
        self, event_id: UUID, opportunity_id: str, player_id: UUID
    ) -> Any | None: ...
