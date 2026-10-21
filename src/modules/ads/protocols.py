"""Ads module protocols -- typing.Protocol interfaces.

Defines the AdServiceProtocol (public interface), repository protocols,
ad provider abstraction, and minimal dependency protocols for cross-module
interactions.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID

from src.core.types.game import EventId, MatchId, PlayerId
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
from src.modules.ads.types import (
    AdContext,
    AdEligibility,
    AdFreeReason,
    AdFreeStatus,
    AdImpression,
    AdProviderResponse,
    AdRequestId,
    AdType,
    BannerPlacement,
    BotAdAttributionReport,
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

# ---------------------------------------------------------------------------
# Public service protocol
# ---------------------------------------------------------------------------


class AdServiceProtocol(Protocol):
    """Public interface for the ads module."""

    async def check_ad_free_status(
        self,
        player_id: PlayerId,
    ) -> AdFreeStatus: ...

    async def can_show_ad(
        self,
        player_id: PlayerId,
        ad_type: AdType,
        context: AdContext | None = None,
    ) -> AdEligibility: ...

    async def request_interstitial(
        self,
        player_id: PlayerId,
        trigger: InterstitialTrigger,
        match_id: MatchId | None = None,
    ) -> InterstitialAdResult: ...

    async def record_interstitial_impression(
        self,
        ad_request_id: AdRequestId,
        viewed: bool,
        duration_ms: int,
    ) -> AdImpression: ...

    async def request_rewarded_video(
        self,
        player_id: PlayerId,
        reward_type: RewardedAdType,
    ) -> RewardedVideoRequest: ...

    async def complete_rewarded_video(
        self,
        ad_request_id: AdRequestId,
        completed: bool,
        watched_duration_ms: int,
    ) -> RewardedVideoResult: ...

    async def record_banner_impression(
        self,
        player_id: PlayerId,
        banner_placement: BannerPlacement,
        view_duration_ms: int,
    ) -> AdImpression: ...

    async def get_player_ad_stats(
        self,
        player_id: PlayerId,
        period: StatsPeriod = StatsPeriod.LIFETIME,
    ) -> PlayerAdStats: ...

    async def get_ad_impressions(
        self,
        player_id: PlayerId,
        ad_type: AdType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[AdImpression]: ...

    async def get_match_ad_attribution(
        self,
        match_id: MatchId,
    ) -> MatchAdAttribution: ...

    async def get_bot_ad_attributions(
        self,
        bot_player_id: PlayerId,
        start_date: date,
        end_date: date,
    ) -> BotAdAttributionReport: ...

    async def grant_ad_free_status(
        self,
        player_id: PlayerId,
        reason: AdFreeReason,
        duration_days: int | None = None,
        granted_by: PlayerId | None = None,
    ) -> AdFreeStatus: ...

    async def revoke_ad_free_status(
        self,
        player_id: PlayerId,
        reason: str,
    ) -> None: ...

    async def get_event_ad_opportunities(
        self,
        player_id: PlayerId,
        event_id: EventId,
    ) -> list[EventAdOpportunity]: ...

    async def claim_event_ad_reward(
        self,
        player_id: PlayerId,
        event_id: EventId,
        opportunity_id: str,
    ) -> EventAdRewardResult: ...


# ---------------------------------------------------------------------------
# Repository protocols
# ---------------------------------------------------------------------------


class AdImpressionRepositoryProtocol(Protocol):
    """Repository interface for ad impressions."""

    async def create(self, data: AdImpressionCreate) -> Any: ...

    async def find_by_id(self, impression_id: UUID) -> Any | None: ...

    async def find_by_request_id(self, ad_request_id: UUID) -> Any | None: ...

    async def find_by_player(
        self,
        player_id: UUID,
        ad_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]: ...

    async def find_by_match(self, match_id: UUID) -> list[Any]: ...

    async def get_player_stats(
        self,
        player_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Any: ...

    async def get_bot_attributions(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Any: ...

    async def get_daily_attributions(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[Any]: ...


class AdRequestRepositoryProtocol(Protocol):
    """Repository interface for ad requests."""

    async def create(self, data: AdRequestCreate) -> Any: ...

    async def find_by_id(self, request_id: UUID) -> Any | None: ...

    async def update(
        self,
        request_id: UUID,
        changes: AdRequestUpdate,
    ) -> Any: ...

    async def find_pending_by_player(
        self,
        player_id: UUID,
    ) -> list[Any]: ...

    async def find_last_by_type(
        self,
        player_id: UUID,
        ad_type: str,
    ) -> Any | None: ...

    async def expire_old_requests(self, before: datetime) -> int: ...


class AdFreeStatusRepositoryProtocol(Protocol):
    """Repository interface for ad-free status."""

    async def find_by_player(self, player_id: UUID) -> Any | None: ...

    async def upsert(self, data: AdFreeStatusUpsert) -> Any: ...

    async def revoke(self, player_id: UUID, reason: str) -> Any: ...

    async def find_expiring(self, before: datetime) -> list[Any]: ...


class AdRewardRepositoryProtocol(Protocol):
    """Repository interface for ad rewards."""

    async def create(self, data: AdRewardCreate) -> Any: ...

    async def find_by_request_id(
        self,
        ad_request_id: UUID,
    ) -> Any | None: ...


class EventAdOpportunityRepositoryProtocol(Protocol):
    """Repository interface for event ad opportunities."""

    async def find_by_event(self, event_id: UUID) -> list[Any]: ...

    async def find_by_id(
        self,
        event_id: UUID,
        opportunity_id: str,
    ) -> Any | None: ...

    async def create(self, data: EventAdOpportunityCreate) -> Any: ...


class EventAdClaimRepositoryProtocol(Protocol):
    """Repository interface for event ad claims."""

    async def create(self, data: EventAdClaimCreate) -> Any: ...

    async def count_claims(
        self,
        event_id: UUID,
        opportunity_id: str,
        player_id: UUID,
    ) -> int: ...

    async def find_last_claim(
        self,
        event_id: UUID,
        opportunity_id: str,
        player_id: UUID,
    ) -> Any | None: ...


# ---------------------------------------------------------------------------
# Ad provider abstraction
# ---------------------------------------------------------------------------


class AdProviderProtocol(Protocol):
    """Interface for third-party ad provider SDKs."""

    async def request_interstitial(
        self,
        ad_unit_id: str,
        user_id: str,
    ) -> AdProviderResponse: ...

    async def request_rewarded_video(
        self,
        ad_unit_id: str,
        user_id: str,
    ) -> AdProviderResponse: ...

    async def verify_impression(
        self,
        ad_request_id: str,
        impression_data: dict[str, Any],
    ) -> bool: ...

    async def get_estimated_cpm(self, ad_type: str) -> int: ...


# ---------------------------------------------------------------------------
# Minimal dependency protocols (avoid circular imports)
# ---------------------------------------------------------------------------


class PlayerServiceProtocol(Protocol):
    """Subset of player service used by ads module."""

    async def get_player(self, player_id: PlayerId) -> Any: ...


class EventServiceProtocol(Protocol):
    """Subset of events service used by ads module."""

    async def get_event(self, event_id: EventId) -> Any: ...

    async def get_event_participant(
        self,
        event_id: EventId,
        player_id: PlayerId,
    ) -> Any: ...
