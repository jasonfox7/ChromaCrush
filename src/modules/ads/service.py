"""Ad service implementation.

``AdService`` is a thin facade that delegates to domain-specific managers.
``AdRepositoryBundle`` stays here — it is imported externally.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from src.core.types.game import EventId, MatchId, PlayerId
from src.modules.ads._helpers import build_ad_free_status, cooldown_seconds
from src.modules.ads.ad_free_manager import AdFreeManager
from src.modules.ads.analytics_service import AdAnalyticsService
from src.modules.ads.banner_manager import BannerManager
from src.modules.ads.dto import PaginatedResult
from src.modules.ads.event_ad_service import EventAdService
from src.modules.ads.interstitial_manager import InterstitialManager
from src.modules.ads.rewarded_video_manager import RewardedVideoManager
from src.modules.ads.types import (
    AdContext,
    AdEligibility,
    AdFreeReason,
    AdFreeStatus,
    AdImpression,
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

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.protocols import (
        AdFreeStatusRepositoryProtocol,
        AdImpressionRepositoryProtocol,
        AdProviderProtocol,
        AdRequestRepositoryProtocol,
        AdRewardRepositoryProtocol,
        EventAdClaimRepositoryProtocol,
        EventAdOpportunityRepositoryProtocol,
        EventServiceProtocol,
        PlayerServiceProtocol,
    )


class AdRepositoryBundle:
    """Groups all ad-related repositories into a single injectable."""

    def __init__(
        self,
        ad_request: AdRequestRepositoryProtocol,
        ad_impression: AdImpressionRepositoryProtocol,
        ad_free_status: AdFreeStatusRepositoryProtocol,
        ad_reward: AdRewardRepositoryProtocol,
        event_opportunity: EventAdOpportunityRepositoryProtocol,
        event_claim: EventAdClaimRepositoryProtocol,
    ) -> None:
        self.ad_request = ad_request
        self.ad_impression = ad_impression
        self.ad_free_status = ad_free_status
        self.ad_reward = ad_reward
        self.event_opportunity = event_opportunity
        self.event_claim = event_claim


class AdService:
    """Concrete implementation of ``AdServiceProtocol``.

    Thin facade — all real work is delegated to domain managers.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        events_service: EventServiceProtocol,
        repos: AdRepositoryBundle,
        ad_provider: AdProviderProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._players = player_service
        self._req_repo = repos.ad_request
        self._free_repo = repos.ad_free_status

        # Cooldown values needed by can_show_ad (stays in facade)
        self._cd_inter: int = config.get("ads.interstitial_cooldown_seconds", 180)
        self._cd_reward: int = config.get("ads.rewarded_cooldown_seconds", 60)

        # --- Domain managers ---
        self._ad_free = AdFreeManager(
            config,
            logger,
            errors,
            player_service,
            repos.ad_free_status,
        )
        self._interstitial = InterstitialManager(
            config,
            logger,
            errors,
            player_service,
            repos.ad_request,
            repos.ad_impression,
            repos.ad_free_status,
            ad_provider,
        )
        self._rewarded = RewardedVideoManager(
            config,
            logger,
            errors,
            player_service,
            repos.ad_request,
            repos.ad_impression,
            repos.ad_free_status,
            repos.ad_reward,
            ad_provider,
        )
        self._banner = BannerManager(
            config,
            logger,
            errors,
            player_service,
            repos.ad_impression,
            repos.ad_free_status,
        )
        self._analytics = AdAnalyticsService(
            config,
            logger,
            errors,
            player_service,
            repos.ad_impression,
        )
        self._event_ads = EventAdService(
            config,
            logger,
            errors,
            player_service,
            events_service,
            repos.event_opportunity,
            repos.event_claim,
            repos.ad_impression,
        )

    # === Ad-free status (delegates to AdFreeManager) ===

    async def check_ad_free_status(self, player_id: PlayerId) -> AdFreeStatus:
        return await self._ad_free.check_ad_free_status(player_id)

    async def grant_ad_free_status(
        self,
        player_id: PlayerId,
        reason: AdFreeReason,
        duration_days: int | None = None,
        granted_by: PlayerId | None = None,
    ) -> AdFreeStatus:
        return await self._ad_free.grant_ad_free_status(
            player_id,
            reason,
            duration_days,
            granted_by,
        )

    async def revoke_ad_free_status(self, player_id: PlayerId, reason: str) -> None:
        return await self._ad_free.revoke_ad_free_status(player_id, reason)

    # === Eligibility (stays in facade — uses multiple domains) ===

    async def can_show_ad(
        self,
        player_id: PlayerId,
        ad_type: AdType,
        context: AdContext | None = None,
    ) -> AdEligibility:
        await self._players.get_player(player_id)
        st = await self.check_ad_free_status(player_id)
        if st.is_ad_free:
            return AdEligibility(can_show=False, reason="Player has ad-free status")
        cd = cooldown_seconds(ad_type, self._cd_inter, self._cd_reward)
        last = await self._req_repo.find_last_by_type(player_id, ad_type.value)
        if last is not None:
            elapsed = (datetime.now(timezone.utc) - last.created_at).total_seconds()
            if elapsed < cd:
                rem = int(cd - elapsed)
                self._logger.debug(
                    "Ad cooldown active",
                    player_id=str(player_id),
                    ad_type=ad_type.value,
                    retry_after=rem,
                )
                return AdEligibility(
                    can_show=False,
                    reason="Cooldown active",
                    cooldown_remaining_seconds=rem,
                )
        return AdEligibility(can_show=True, ad_request_token="eligible")

    # === Interstitial (delegates to InterstitialManager) ===

    async def request_interstitial(
        self,
        player_id: PlayerId,
        trigger: InterstitialTrigger,
        match_id: MatchId | None = None,
    ) -> InterstitialAdResult:
        return await self._interstitial.request_interstitial(
            player_id,
            trigger,
            match_id,
        )

    async def record_interstitial_impression(
        self,
        ad_request_id: AdRequestId,
        viewed: bool,
        duration_ms: int,
    ) -> AdImpression:
        return await self._interstitial.record_interstitial_impression(
            ad_request_id,
            viewed,
            duration_ms,
        )

    # === Rewarded video (delegates to RewardedVideoManager) ===

    async def request_rewarded_video(
        self, player_id: PlayerId, reward_type: RewardedAdType
    ) -> RewardedVideoRequest:
        return await self._rewarded.request_rewarded_video(player_id, reward_type)

    async def complete_rewarded_video(
        self,
        ad_request_id: AdRequestId,
        completed: bool,
        watched_duration_ms: int,
    ) -> RewardedVideoResult:
        return await self._rewarded.complete_rewarded_video(
            ad_request_id,
            completed,
            watched_duration_ms,
        )

    # === Banner (delegates to BannerManager) ===

    async def record_banner_impression(
        self,
        player_id: PlayerId,
        banner_placement: BannerPlacement,
        view_duration_ms: int,
    ) -> AdImpression:
        return await self._banner.record_banner_impression(
            player_id,
            banner_placement,
            view_duration_ms,
        )

    # === Stats / History (delegates to AdAnalyticsService) ===

    async def get_player_ad_stats(
        self, player_id: PlayerId, period: StatsPeriod = StatsPeriod.LIFETIME
    ) -> PlayerAdStats:
        return await self._analytics.get_player_ad_stats(player_id, period)

    async def get_ad_impressions(
        self,
        player_id: PlayerId,
        ad_type: AdType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[AdImpression]:
        return await self._analytics.get_ad_impressions(
            player_id,
            ad_type,
            limit,
            offset,
        )

    async def get_match_ad_attribution(self, match_id: MatchId) -> MatchAdAttribution:
        return await self._analytics.get_match_ad_attribution(match_id)

    async def get_bot_ad_attributions(
        self, bot_player_id: PlayerId, start_date: date, end_date: date
    ) -> BotAdAttributionReport:
        return await self._analytics.get_bot_ad_attributions(
            bot_player_id,
            start_date,
            end_date,
        )

    # === Event ad opportunities (delegates to EventAdService) ===

    async def get_event_ad_opportunities(
        self, player_id: PlayerId, event_id: EventId
    ) -> list[EventAdOpportunity]:
        return await self._event_ads.get_event_ad_opportunities(player_id, event_id)

    async def claim_event_ad_reward(
        self,
        player_id: PlayerId,
        event_id: EventId,
        opportunity_id: str,
    ) -> EventAdRewardResult:
        return await self._event_ads.claim_event_ad_reward(
            player_id,
            event_id,
            opportunity_id,
        )
