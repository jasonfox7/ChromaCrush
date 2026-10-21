"""Events module protocols -- typing.Protocol interfaces."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.core.types.game import EventId, MatchId, PlayerId
from src.modules.events.dto import (
    EventCreate,
    EventDbUpdate,
    EventMatchCreate,
    EventUpdate,
    PaginatedResult,
    ParticipantCreate,
    ParticipantUpdate,
)
from src.modules.events.types import (
    Event,
    EventFinalizationResult,
    EventLeaderboard,
    EventParticipant,
    EventStatus,
    EventSummary,
    EventType,
    MatchEventStats,
    PlayerEventRank,
    PlayerEventSummary,
    ScheduledEventResult,
)


class EventServiceProtocol(Protocol):
    """Public interface for the events module."""

    async def create_event(self, event_data: EventCreate) -> Event: ...
    async def get_event(self, event_id: EventId) -> Event: ...
    async def list_events(
        self,
        status: EventStatus | None = None,
        event_type: EventType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResult[EventSummary]: ...
    async def get_active_events(self) -> list[Event]: ...
    async def join_event(
        self, event_id: EventId, player_id: PlayerId
    ) -> EventParticipant: ...
    async def leave_event(self, event_id: EventId, player_id: PlayerId) -> None: ...
    async def record_event_match(
        self,
        event_id: EventId,
        player_id: PlayerId,
        match_id: MatchId,
        score: int,
        match_stats: MatchEventStats,
    ) -> EventParticipant: ...
    async def get_leaderboard(
        self, event_id: EventId, limit: int = 100, offset: int = 0
    ) -> EventLeaderboard: ...
    async def get_player_rank(
        self, event_id: EventId, player_id: PlayerId
    ) -> PlayerEventRank: ...
    async def get_player_events(
        self,
        player_id: PlayerId,
        include_past: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResult[PlayerEventSummary]: ...
    async def get_event_participant(
        self, event_id: EventId, player_id: PlayerId
    ) -> EventParticipant: ...
    async def finalize_event(self, event_id: EventId) -> EventFinalizationResult: ...
    async def cancel_event(self, event_id: EventId, reason: str) -> Event: ...
    async def update_event(self, event_id: EventId, updates: EventUpdate) -> Event: ...
    async def process_scheduled_events(self) -> ScheduledEventResult: ...


class EventRepositoryProtocol(Protocol):
    """Repository interface for event data (PostgreSQL)."""

    async def create(self, data: EventCreate) -> Any: ...
    async def find_by_id(self, event_id: UUID) -> Any | None: ...
    async def update(self, event_id: UUID, changes: EventDbUpdate) -> Any: ...
    async def find_by_status(
        self,
        status: str | None = None,
        event_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Any], int]: ...
    async def find_active(self) -> list[Any]: ...
    async def find_scheduled_to_start(self, before: datetime) -> list[Any]: ...
    async def find_active_to_end(self, before: datetime) -> list[Any]: ...
    async def find_ended_to_finalize(self, before: datetime) -> list[Any]: ...
    async def increment_participant_count(self, event_id: UUID) -> int: ...
    async def decrement_participant_count(self, event_id: UUID) -> int: ...


class EventParticipantRepositoryProtocol(Protocol):
    """Repository interface for event participants (PostgreSQL)."""

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


class EventLeaderboardRepositoryProtocol(Protocol):
    """Repository interface for event leaderboards (Redis-backed)."""

    async def update_score(
        self, event_id: UUID, player_id: UUID, score: int
    ) -> None: ...
    async def get_rank(self, event_id: UUID, player_id: UUID) -> int | None: ...
    async def get_score(self, event_id: UUID, player_id: UUID) -> int | None: ...
    async def get_top(
        self, event_id: UUID, limit: int, offset: int = 0
    ) -> list[tuple[str, int]]: ...
    async def get_total_count(self, event_id: UUID) -> int: ...
    async def get_percentile(self, event_id: UUID, player_id: UUID) -> float | None: ...
    async def remove_player(self, event_id: UUID, player_id: UUID) -> None: ...
    async def clear_leaderboard(self, event_id: UUID) -> None: ...
    async def sync_to_database(
        self, event_id: UUID, participant_repo: EventParticipantRepositoryProtocol
    ) -> int: ...


class MatchServiceProtocol(Protocol):
    """Subset of match service used by events module."""

    async def get_match(self, match_id: MatchId) -> Any: ...


class PlayerServiceProtocol(Protocol):
    """Subset of player service used by events module."""

    async def get_player(self, player_id: PlayerId) -> Any: ...
    async def get_stats(self, player_id: PlayerId) -> Any: ...
    async def get_elo(self, player_id: PlayerId) -> int: ...
    async def update_elo(self, player_id: PlayerId, new_rating: int) -> Any: ...


class EnergyServiceProtocol(Protocol):
    """Subset of energy service used by events module."""

    async def get_energy(self, player_id: PlayerId) -> Any: ...
    async def consume_heart(self, player_id: PlayerId, amount: int = 1) -> Any: ...
    async def grant_bonus_hearts(
        self,
        player_id: PlayerId,
        amount: int,
        source: Any,
        idempotency_key: str | None = None,
    ) -> Any: ...
    async def refund_heart(
        self, player_id: PlayerId, amount: int = 1, reason: str = "match_cancelled"
    ) -> Any: ...


class VaultServiceProtocol(Protocol):
    """Subset of vault service used by events module."""

    async def add_artifact(
        self,
        player_id: PlayerId,
        artifact_type_id: str,
        source: str,
        source_id: str | None = None,
    ) -> Any: ...
