"""Protocol interface for ad-free status repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


class AdFreeStatusRepositoryProtocol(Protocol):
    """Repository interface for ad-free status (PostgreSQL)."""

    async def find_by_player(self, player_id: UUID) -> Any | None: ...
    async def upsert(self, data: Any) -> Any: ...
    async def revoke(self, player_id: UUID, reason: str) -> Any: ...
    async def find_expiring(self, before: datetime) -> list[Any]: ...
