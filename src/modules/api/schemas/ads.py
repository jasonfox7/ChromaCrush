"""Ads request and response schemas.

Pydantic v2 models for the ``/api/v1/ads`` endpoint group.
Request schemas are mutable (accept user input), response schemas
are frozen (immutable output).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# -- Request schemas ----------------------------------------------------------


class InterstitialRequest(BaseModel):
    """Request body for interstitial ad request."""

    trigger: str = Field(
        ...,
        description=(
            "What triggered the interstitial ad. "
            "One of: match_end, menu_return, matchmaking_wait, event_join."
        ),
    )
    match_id: str | None = Field(
        default=None,
        description="Optional match ID for match-related triggers.",
    )


class InterstitialCompleteRequest(BaseModel):
    """Request body for completing an interstitial ad."""

    ad_request_id: str = Field(
        ...,
        description="The ad request ID from the initial interstitial request.",
    )
    viewed: bool = Field(
        ...,
        description="Whether the ad was actually viewed by the player.",
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="Duration in milliseconds that the ad was displayed.",
    )


class RewardedVideoRequestSchema(BaseModel):
    """Request body for rewarded video ad request."""

    reward_type: str = Field(
        ...,
        description=(
            "Type of reward for the video. "
            "One of: bonus_heart, extra_hearts, event_points, "
            "continue_match, double_rewards."
        ),
    )


class RewardedVideoCompleteRequest(BaseModel):
    """Request body for completing a rewarded video ad."""

    ad_request_id: str = Field(
        ...,
        description="The ad request ID from the initial rewarded video request.",
    )
    completed: bool = Field(
        ...,
        description="Whether the video was watched to completion.",
    )
    watched_duration_ms: int = Field(
        ...,
        ge=0,
        description="Duration in milliseconds that the video was watched.",
    )


class BotAttributionQueryParams(BaseModel):
    """Query parameters for bot ad attribution endpoint."""

    start_date: str = Field(
        ...,
        description="Start date for attribution query (ISO 8601 date, e.g. 2026-01-01).",
    )
    end_date: str = Field(
        ...,
        description="End date for attribution query (ISO 8601 date, e.g. 2026-01-31).",
    )


# -- Response schemas ---------------------------------------------------------


class AdFreeStatusResponse(BaseModel):
    """Ad-free status for a player."""

    model_config = ConfigDict(frozen=True)

    is_ad_free: bool
    reason: str | None = None
    expires_at: str | None = None


class InterstitialResponse(BaseModel):
    """Response after requesting an interstitial ad."""

    model_config = ConfigDict(frozen=True)

    ad_request_id: str
    should_show: bool
    ad_unit_id: str | None = None


class InterstitialCompleteResponse(BaseModel):
    """Response after completing an interstitial impression."""

    model_config = ConfigDict(frozen=True)

    impression_id: str
    viewed: bool
    duration_ms: int


class RewardedVideoResponse(BaseModel):
    """Response after requesting a rewarded video ad."""

    model_config = ConfigDict(frozen=True)

    ad_request_id: str
    ad_unit_id: str | None = None
    reward_preview: dict | None = None


class RewardedVideoCompleteResponse(BaseModel):
    """Response after completing a rewarded video ad."""

    model_config = ConfigDict(frozen=True)

    reward_granted: bool
    reward_type: str | None = None
    reward_amount: int | None = None


class DailyBreakdownItem(BaseModel):
    """Single day in bot attribution breakdown."""

    model_config = ConfigDict(frozen=True)

    date: str
    matches: int
    impressions: int
    estimated_revenue_cents: int
    attributed_cents: int


class BotAttributionResponse(BaseModel):
    """Bot ad attribution report response."""

    model_config = ConfigDict(frozen=True)

    bot_player_id: str
    start_date: str
    end_date: str
    total_impressions: int
    total_revenue_cents: int
    daily_breakdown: list[DailyBreakdownItem]
