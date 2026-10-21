"""Data Transfer Objects for the player module.

These DTOs carry structured data between the service layer and its
callers. They are not ORM models and have no database awareness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.core.types.pagination import PaginatedResult as PaginatedResult  # noqa: F401


@dataclass
class PlayerUpdate:
    """Fields that can be updated on a player profile."""

    username: str | None = None
    email: str | None = None


@dataclass
class EnergyStateUpdate:
    """Fields that can be updated on energy state."""

    hearts: int | None = None
    last_regen_at: datetime | None = None
    daily_streak: int | None = None
    last_login_date: date | None = None
