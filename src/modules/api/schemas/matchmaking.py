"""Matchmaking request and response schemas.

Pydantic v2 models for the ``/api/v1/matchmaking`` endpoint group.
Request schemas are mutable, response schemas are frozen.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# -- Request schemas ----------------------------------------------------------


class JoinQueueRequest(BaseModel):
    """Request to join the matchmaking queue."""

    pool_type: str = Field(
        default="mixed",
        description="Queue pool: 'human', 'bot', or 'mixed'.",
    )


class QuickMatchRequest(BaseModel):
    """Request for instant single-player match."""

    bot_player_id: str | None = Field(
        default=None,
        description="Use a specific pre-existing bot player instead of creating an ephemeral one.",
    )


# -- Response schemas ---------------------------------------------------------


class QueueEntryResponse(BaseModel):
    """Response after successfully joining the queue."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    pool_type: str
    elo_rating: int
    position: int
    estimated_wait_seconds: int | None
    joined_at: str


class QueueStatusResponse(BaseModel):
    """Current queue status for a player."""

    model_config = ConfigDict(frozen=True)

    in_queue: bool
    position: int | None = None
    pool_type: str | None = None
    estimated_wait_seconds: int | None = None
    joined_at: str | None = None


class PoolStatsResponse(BaseModel):
    """Statistics for a matchmaking pool."""

    model_config = ConfigDict(frozen=True)

    pool_type: str
    player_count: int
    average_wait_seconds: int | None
