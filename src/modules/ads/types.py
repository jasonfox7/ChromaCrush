"""Ads module types -- enums and domain dataclasses.

Defines ad types, statuses, triggers, placements, and all output
dataclasses returned by the AdService public interface.

Note: ``PlayerId``, ``MatchId``, ``EventId`` are imported from
``src.core.types.game`` and are NOT redefined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, NewType
from uuid import UUID

from src.core.types.game import EventId, MatchId, PlayerId

# ---------------------------------------------------------------------------
# Opaque identifiers
# ---------------------------------------------------------------------------

AdRequestId = NewType("AdRequestId", UUID)
AdImpressionId = NewType("AdImpressionId", UUID)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AdType(Enum):
    """Types of ads that can be served."""

    INTERSTITIAL = "interstitial"
    REWARDED = "rewarded"
    BANNER = "banner"


class InterstitialTrigger(Enum):
    """What triggered an interstitial ad."""

    MATCH_END = "match_end"
    MENU_RETURN = "menu_return"
    MATCHMAKING_WAIT = "matchmaking_wait"
    EVENT_JOIN = "event_join"


class RewardedAdType(Enum):
    """Reward types for rewarded video ads."""

    BONUS_HEART = "bonus_heart"
    EXTRA_HEARTS = "extra_hearts"
    EVENT_POINTS = "event_points"
    CONTINUE_MATCH = "continue_match"
    DOUBLE_REWARDS = "double_rewards"


class BannerPlacement(Enum):
    """Screen placements for banner ads."""

    MAIN_MENU = "main_menu"
    LEADERBOARD = "leaderboard"
    PROFILE = "profile"
    SETTINGS = "settings"


class AdFreeReason(Enum):
    """Reasons why a player has ad-free status."""

    PURCHASE = "purchase"
    PROMOTION = "promotion"
    ADMIN_GRANT = "admin_grant"
    TRIAL = "trial"
    REFUND = "refund"


class AdRequestStatus(Enum):
    """Lifecycle states for an ad request."""

    PENDING = "pending"
    SHOWN = "shown"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


class StatsPeriod(Enum):
    """Time periods for ad statistics."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    LIFETIME = "lifetime"


# ---------------------------------------------------------------------------
# Supporting dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AdContext:
    """Context for ad display."""

    match_id: MatchId | None = None
    event_id: EventId | None = None
    opponent_id: PlayerId | None = None
    trigger_source: str | None = None


@dataclass
class DailyAttribution:
    """Daily breakdown of bot ad attribution."""

    date: date
    matches: int
    impressions: int
    estimated_revenue_cents: int
    attributed_cents: int


# ---------------------------------------------------------------------------
# Output domain objects
# ---------------------------------------------------------------------------


@dataclass
class AdFreeStatus:
    """Player's ad-free status."""

    player_id: PlayerId
    is_ad_free: bool
    reason: AdFreeReason | None = None
    granted_at: datetime | None = None
    expires_at: datetime | None = None
    is_permanent: bool = False


@dataclass
class AdEligibility:
    """Whether an ad can be shown to a player."""

    can_show: bool
    reason: str | None = None
    cooldown_remaining_seconds: int | None = None
    ad_request_token: str | None = None


@dataclass
class InterstitialAdResult:
    """Result of requesting an interstitial ad."""

    ad_request_id: AdRequestId
    ad_unit_id: str
    should_show: bool
    ad_data: dict[str, Any] | None
    created_at: datetime


@dataclass
class AdImpression:
    """Record of an ad being shown."""

    id: AdImpressionId
    player_id: PlayerId
    ad_type: AdType
    ad_request_id: AdRequestId | None
    viewed: bool
    view_duration_ms: int
    trigger: str
    match_id: MatchId | None = None
    event_id: EventId | None = None
    attributed_to: PlayerId | None = None
    estimated_revenue_cents: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RewardedVideoRequest:
    """Result of requesting a rewarded video."""

    ad_request_id: AdRequestId
    ad_unit_id: str
    reward_type: RewardedAdType
    reward_value: int
    video_available: bool
    ad_data: dict[str, Any] | None
    expires_at: datetime


@dataclass
class RewardedVideoResult:
    """Result of completing a rewarded video."""

    ad_request_id: AdRequestId
    completed: bool
    watched_duration_ms: int
    reward_granted: bool
    reward_type: RewardedAdType | None
    reward_value: int | None
    impression: AdImpression


@dataclass
class PlayerAdStats:
    """Ad statistics for a player."""

    player_id: PlayerId
    period: StatsPeriod
    total_impressions: int
    interstitial_count: int
    rewarded_video_count: int
    banner_impression_count: int
    total_rewards_earned: int
    average_view_duration_ms: int
    last_ad_at: datetime | None


@dataclass
class MatchAdAttribution:
    """Ad attribution data for a match."""

    match_id: MatchId
    player1_id: PlayerId
    player2_id: PlayerId
    player1_is_bot: bool
    player2_is_bot: bool
    impressions: list[AdImpression]
    total_impressions: int
    estimated_revenue_cents: int
    bot_attribution_cents: int


@dataclass
class BotAdAttributionReport:
    """Aggregated ad attribution for a bot."""

    bot_player_id: PlayerId
    start_date: date
    end_date: date
    total_matches: int
    matches_with_impressions: int
    total_attributed_impressions: int
    estimated_revenue_cents: int
    attributed_revenue_cents: int
    attribution_share_percent: float
    daily_breakdown: list[DailyAttribution]


@dataclass
class EventAdOpportunity:
    """Special ad opportunity during an event."""

    opportunity_id: str
    event_id: EventId
    ad_type: AdType
    reward_type: str
    reward_value: int
    description: str
    times_available: int
    times_claimed: int
    cooldown_minutes: int | None
    available: bool
    next_available_at: datetime | None


@dataclass
class EventAdRewardResult:
    """Result of claiming an event ad reward."""

    opportunity_id: str
    event_id: EventId
    player_id: PlayerId
    reward_type: str
    reward_value: int
    impression: AdImpression
    claimed_at: datetime


@dataclass
class AdProviderResponse:
    """Response from ad provider."""

    success: bool
    ad_available: bool
    ad_data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
