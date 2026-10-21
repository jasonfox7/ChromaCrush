"""Event participant repository protocol (data layer)."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from src.modules.events.dto import (
    EventMatchCreate,
    ParticipantCreate,
    ParticipantUpdate,
)


class EventParticipantRepositoryProtocol(Protocol):
    """Repository interface for event participant data access."""

    async def create(self, data: ParticipantCreate) -> Any: ...
    async def find_by_event_and_player(
        self, event_id: UUID, player_id: UUID
    ) -> Any | None: ...
    async def update(
        self, event_id: UUID, player_id: UUID, changes: ParticipantUpdate
    ) -> Any: ...
    async def find_by_event(
        self,
        event_id: UUID,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Any], int]: ...
    async def find_by_player(
        self,
        player_id: UUID,
        include_past: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Any], int]: ...
    async def find_ranked_by_event(
        self, event_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Any]: ...
    async def count_by_event(self, event_id: UUID, active_only: bool = True) -> int: ...
    async def bulk_update_ranks(
        self, event_id: UUID, ranks: list[tuple[UUID, int]]
    ) -> int: ...
    async def find_eligible_for_rewards(
        self, event_id: UUID, min_matches: int
    ) -> list[Any]: ...
    async def create_event_match(self, data: EventMatchCreate) -> Any: ...
