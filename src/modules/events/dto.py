"""Data Transfer Objects for the events module.

Pure data carriers used by repositories and the service layer.
No database or business logic awareness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.core.types.game import EventId, MatchId, PlayerId
from src.core.types.pagination import PaginatedResult as PaginatedResult  # noqa: F401


@dataclass
class EventCreate:
    """Data required to create a new event."""

    name: str
    description: str
    event_type: str
    scoring_type: str
    start_at: datetime
    end_at: datetime
    entry_requirements: dict  # JSONB-serialisable
    reward_tiers: list[dict]  # JSONB-serialisable
    rules: dict  # JSONB-serialisable
    max_participants: int | None = None
    created_by: UUID | None = None


@dataclass
class EventUpdate:
    """Fields that callers can update on an event (service-level DTO)."""

    name: str | None = None
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    entry_requirements: dict | None = None
    reward_tiers: list[dict] | None = None
    rules: dict | None = None
    max_participants: int | None = None


@dataclass
class EventDbUpdate:
    """Fields written to the database (internal repo-level DTO).

    Includes status transitions and timestamps not exposed to callers.
    """

    name: str | None = None
    description: str | None = None
    status: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    entry_requirements: dict | None = None
    reward_tiers: list[dict] | None = None
    rules: dict | None = None
    max_participants: int | None = None
    activated_at: datetime | None = None
    finalized_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None


@dataclass
class ParticipantCreate:
    """Data required to create a participant record."""

    event_id: UUID
    player_id: UUID


@dataclass
class ParticipantUpdate:
    """Fields that can be updated on a participant record."""

    total_score: int | None = None
    matches_played: int | None = None
    best_match_score: int | None = None
    current_rank: int | None = None
    rewards_claimed: bool | None = None
    reward_tier: str | None = None
    last_match_at: datetime | None = None
    left_at: datetime | None = None


@dataclass
class EventMatchCreate:
    """Data required to record an event match."""

    event_id: UUID
    player_id: UUID
    match_id: UUID
    score: int
    chain_count: int = 0
    gems_cleared: int = 0
    special_gems_activated: int = 0
