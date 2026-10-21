"""Protocol interface for ad impression repository."""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol
from uuid import UUID


class AdImpressionRepositoryProtocol(Protocol):
    """Repository interface for ad impressions (PostgreSQL)."""

    async def create(self, data: Any) -> Any: ...
    async def find_by_id(self, impression_id: UUID) -> Any | None: ...
    async def find_by_request_id(self, ad_request_id: UUID) -> Any | None: ...
    async def find_by_player(
        self,
        player_id: UUID,
        ad_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]: ...
    async def find_by_match(self, match_id: UUID) -> list[Any]: ...
    async def get_player_stats(
        self,
        player_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Any: ...
    async def get_bot_attributions(
        self, bot_player_id: UUID, start_date: date, end_date: date
    ) -> Any: ...
    async def get_daily_attributions(
        self, bot_player_id: UUID, start_date: date, end_date: date
    ) -> list[Any]: ...
