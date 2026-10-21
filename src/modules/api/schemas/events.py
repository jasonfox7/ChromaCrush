"""Event-related Pydantic v2 schemas for API request/response models.

Defines response models for events, participants, leaderboards,
and player event status.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Query schemas
# ---------------------------------------------------------------------------


class EventListQuery(BaseModel):
    """Query parameters for listing events."""

    status: str | None = Field(default=None, description="Filter by event status.")
    event_type: str | None = Field(default=None, description="Filter by event type.")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results.")
    offset: int = Field(default=0, ge=0, description="Pagination offset.")


class LeaderboardQuery(BaseModel):
    """Query parameters for leaderboard pagination."""

    limit: int = Field(default=100, ge=1, le=500, description="Maximum entries.")
    offset: int = Field(default=0, ge=0, description="Pagination offset.")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class EventResponse(BaseModel):
    """Full event details."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    name: str
    event_type: str
    status: str
    start_time: str
    end_time: str
    max_participants: int | None
    current_participants: int
    description: str | None = None


class EventParticipantResponse(BaseModel):
    """Player participation details for an event."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    player_id: str
    score: int
    rank: int | None
    matches_played: int
    joined_at: str


class LeaderboardEntryResponse(BaseModel):
    """Single entry on an event leaderboard."""

    model_config = ConfigDict(frozen=True)

    rank: int
    player_id: str
    username: str
    score: int
    matches_played: int


class EventLeaderboardResponse(BaseModel):
    """Full event leaderboard response."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    entries: list[LeaderboardEntryResponse]
    total_participants: int
    player_rank: int | None = None


class PlayerEventStatusResponse(BaseModel):
    """Player's current status within an event."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    player_id: str
    score: int
    rank: int | None
    matches_played: int
    is_active: bool
