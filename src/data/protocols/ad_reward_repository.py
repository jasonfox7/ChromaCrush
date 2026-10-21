"""Protocol interface for ad reward repository."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class AdRewardRepositoryProtocol(Protocol):
    """Repository interface for ad rewards (PostgreSQL)."""

    async def create(self, data: Any) -> Any: ...
    async def find_by_request_id(self, ad_request_id: UUID) -> Any | None: ...
