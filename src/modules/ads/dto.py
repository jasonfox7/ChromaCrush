"""Data Transfer Objects for the ads module.

Pure data carriers used by repositories and the service layer.
No database or business logic awareness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.types.pagination import PaginatedResult as PaginatedResult  # noqa: F401


@dataclass
class AdRequestCreate:
    """Data required to create an ad request record."""

    player_id: UUID
    ad_type: str
    ad_unit_id: str | None = None
    trigger: str | None = None
    reward_type: str | None = None
    reward_value: int | None = None
    match_id: UUID | None = None
    event_id: UUID | None = None
    status: str = "pending"
    expires_at: datetime | None = None
    provider_response: dict[str, Any] | None = None


@dataclass
class AdRequestUpdate:
    """Fields that can be updated on an ad request."""

    status: str | None = None
    completed_at: datetime | None = None


@dataclass
class AdImpressionCreate:
    """Data required to create an ad impression record."""

    player_id: UUID
    ad_type: str
    trigger: str
    viewed: bool = False
    view_duration_ms: int = 0
    completed: bool = False
    ad_request_id: UUID | None = None
    placement: str | None = None
    match_id: UUID | None = None
    event_id: UUID | None = None
    opponent_id: UUID | None = None
    attributed_to: UUID | None = None
    attribution_share_percent: float | None = None
    estimated_revenue_cents: int | None = None


@dataclass
class AdFreeStatusUpsert:
    """Data for creating or updating ad-free status."""

    player_id: UUID
    is_ad_free: bool
    reason: str | None = None
    granted_at: datetime | None = None
    expires_at: datetime | None = None
    granted_by: UUID | None = None


@dataclass
class AdRewardCreate:
    """Data required to record a granted ad reward."""

    player_id: UUID
    ad_request_id: UUID
    impression_id: UUID
    reward_type: str
    reward_value: int


@dataclass
class EventAdOpportunityCreate:
    """Data required to create an event ad opportunity."""

    id: str
    event_id: UUID
    ad_type: str
    reward_type: str
    reward_value: int
    description: str | None = None
    times_available_per_player: int = 1
    cooldown_minutes: int | None = None


@dataclass
class EventAdClaimCreate:
    """Data required to record an event ad claim."""

    event_id: UUID
    opportunity_id: str
    player_id: UUID
    impression_id: UUID
