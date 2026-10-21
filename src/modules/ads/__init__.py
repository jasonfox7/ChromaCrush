"""Ads module for ChromaCrush.

NOTE: This module is a stub from original agentic code generation and is
not yet integrated into the game. The current compensation model is leaning
toward purchaseable gold rather than ad-supported revenue. This module will
need architectural review if/when ads are implemented.

Manages advertisement integration: interstitial ads, rewarded videos,
banner ads, ad-free status, impression tracking, bot revenue attribution,
and event ad opportunities. This module is fully async.

Exports:
    AdService: Concrete service implementation.
    AdServiceProtocol: Protocol interface for dependency injection.
    AdRepositoryBundle: Groups all ad repositories for injection.
"""

from src.modules.ads.dto import (
    AdFreeStatusUpsert,
    AdImpressionCreate,
    AdRequestCreate,
    AdRequestUpdate,
    AdRewardCreate,
    EventAdClaimCreate,
    EventAdOpportunityCreate,
    PaginatedResult,
)
from src.modules.ads.protocols import AdServiceProtocol
from src.modules.ads.service import AdRepositoryBundle, AdService
from src.modules.ads.types import (
    AdContext,
    AdEligibility,
    AdFreeReason,
    AdFreeStatus,
    AdImpression,
    AdImpressionId,
    AdProviderResponse,
    AdRequestId,
    AdRequestStatus,
    AdType,
    BannerPlacement,
    BotAdAttributionReport,
    DailyAttribution,
    EventAdOpportunity,
    EventAdRewardResult,
    InterstitialAdResult,
    InterstitialTrigger,
    MatchAdAttribution,
    PlayerAdStats,
    RewardedAdType,
    RewardedVideoRequest,
    RewardedVideoResult,
    StatsPeriod,
)

__all__ = [
    "AdContext",
    "AdEligibility",
    "AdFreeReason",
    "AdFreeStatus",
    "AdFreeStatusUpsert",
    "AdImpression",
    "AdImpressionCreate",
    "AdImpressionId",
    "AdProviderResponse",
    "AdRepositoryBundle",
    "AdRequestCreate",
    "AdRequestId",
    "AdRequestStatus",
    "AdRequestUpdate",
    "AdRewardCreate",
    "AdService",
    "AdServiceProtocol",
    "AdType",
    "BannerPlacement",
    "BotAdAttributionReport",
    "DailyAttribution",
    "EventAdClaimCreate",
    "EventAdOpportunity",
    "EventAdOpportunityCreate",
    "EventAdRewardResult",
    "InterstitialAdResult",
    "InterstitialTrigger",
    "MatchAdAttribution",
    "PaginatedResult",
    "PlayerAdStats",
    "RewardedAdType",
    "RewardedVideoRequest",
    "RewardedVideoResult",
    "StatsPeriod",
]
