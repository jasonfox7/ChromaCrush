"""Player request and response schemas.

Pydantic v2 models for the ``/api/v1/players`` endpoint group.
Request schemas are mutable, response schemas are frozen.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# -- Request schemas ----------------------------------------------------------


class PlayerUpdateRequest(BaseModel):
    """Player profile update request."""

    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="New username (3-32 chars, alphanumeric + underscore).",
    )
    email: str | None = Field(
        default=None,
        description="New email address.",
    )


# -- Response schemas ---------------------------------------------------------


class PlayerProfileResponse(BaseModel):
    """Full player profile response."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    username: str
    player_type: str
    elo_rating: int
    email: str | None = None
    created_at: str


class PlayerStatsResponse(BaseModel):
    """Player statistics response."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    matches_played: int
    matches_won: int
    matches_lost: int
    matches_drawn: int
    total_score: int
    highest_score: int
    longest_chain: int
    total_gems_matched: int
    win_rate: float


class UsernameCheckResponse(BaseModel):
    """Username availability check response."""

    model_config = ConfigDict(frozen=True)

    available: bool
    valid: bool
    error: str | None = None


class LeaderboardEntry(BaseModel):
    """Single entry in the leaderboard (ELO or high score)."""

    model_config = ConfigDict(frozen=True)

    rank: int
    player_id: str
    username: str
    elo_rating: int
    highest_score: int | None = None


class LeaderboardResponse(BaseModel):
    """ELO leaderboard response with pagination metadata."""

    model_config = ConfigDict(frozen=True)

    entries: list[LeaderboardEntry]
    total: int
    limit: int
    offset: int
