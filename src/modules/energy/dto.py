"""Data Transfer Objects for the energy module.

These DTOs carry structured data between the energy service and its
callers. They are not ORM models and have no database awareness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class BonusSource(Enum):
    """Sources of bonus hearts."""

    AD_REWARD = "ad_reward"
    STREAK_BONUS = "streak_bonus"
    EVENT_REWARD = "event_reward"
    REFERRAL = "referral"
    COMPENSATION = "compensation"
    PROMOTION = "promotion"
    PURCHASE = "purchase"


@dataclass
class EnergyInfo:
    """Complete energy state with real-time calculations."""

    player_id: str
    current_hearts: int
    max_hearts: int
    seconds_to_next_heart: int | None  # None if at max
    next_heart_at: datetime | None  # None if at max
    is_full: bool
    daily_streak: int
    last_login_date: date | None


@dataclass
class EnergyConsumeResult:
    """Result of consuming hearts."""

    success: bool
    hearts_consumed: int
    hearts_remaining: int
    hearts_regenerated_before_consume: int
    energy_info: EnergyInfo


@dataclass
class RegenResult:
    """Result of applying regeneration."""

    hearts_added: int
    hearts_before: int
    hearts_after: int
    last_regen_at: datetime
    energy_info: EnergyInfo


@dataclass
class TimeToHeartResult:
    """Time until next heart regenerates."""

    seconds_remaining: int
    next_regen_at: datetime | None
    is_full: bool
    current_hearts: int
    max_hearts: int


@dataclass
class LoginResult:
    """Result of recording a login."""

    streak_day: int
    streak_continued: bool  # True if streak incremented, False if reset or same-day
    streak_broken: bool  # True if streak was reset (not just same-day)
    bonus_hearts_granted: int
    next_streak_reward_at: int  # Days until next streak reward
    energy_info: EnergyInfo


@dataclass
class StreakInfo:
    """Player's streak information."""

    current_streak: int
    last_login_date: date | None
    streak_started_at: date | None  # Calculated: last_login - streak + 1
    next_reward_threshold: int  # e.g., 7, 14, 30
    days_until_reward: int
    reward_hearts: int  # Hearts granted at next threshold


@dataclass
class BonusGrantResult:
    """Result of granting bonus hearts."""

    granted: bool
    hearts_granted: int
    hearts_before: int
    hearts_after: int
    source: BonusSource
    already_claimed: bool  # True if idempotency key was already used
    energy_info: EnergyInfo
