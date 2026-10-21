"""Energy request and response schemas.

Pydantic v2 models for the ``/api/v1/energy`` endpoint group.
All response schemas are frozen (immutable).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# -- Response schemas ---------------------------------------------------------


class EnergyResponse(BaseModel):
    """Current energy (hearts) state response."""

    model_config = ConfigDict(frozen=True)

    current_hearts: int
    max_hearts: int
    seconds_to_next_heart: int | None
    next_heart_at: str | None
    is_full: bool
    daily_streak: int


class StreakResponse(BaseModel):
    """Player streak information response."""

    model_config = ConfigDict(frozen=True)

    current_streak: int
    last_login_date: str | None
    next_reward_threshold: int
    days_until_reward: int
    reward_hearts: int


class LoginStreakResponse(BaseModel):
    """Login streak recording response."""

    model_config = ConfigDict(frozen=True)

    streak_day: int
    streak_continued: bool
    streak_broken: bool
    bonus_hearts_granted: int
    energy: EnergyResponse
