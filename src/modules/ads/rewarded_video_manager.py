"""Rewarded video ad manager.

Handles requesting and completing rewarded video ads.
Internal module — not exported from ``__init__.py``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from src.core.types.game import PlayerId
from src.modules.ads._helpers import (
    build_impression,
    calc_revenue,
    guard_ad_free,
    guard_cooldown,
    provider_call,
    valid_request,
)
from src.modules.ads.dto import (
    AdImpressionCreate,
    AdRequestCreate,
    AdRequestUpdate,
    AdRewardCreate,
)
from src.modules.ads.types import (
    AdRequestId,
    AdRequestStatus,
    AdType,
    RewardedAdType,
    RewardedVideoRequest,
    RewardedVideoResult,
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
        PlayerServiceProtocol,
    )

_AD_REQUEST_EXPIRY_MINUTES = 5
_STANDARD_VIDEO_DURATION_MS = 30000


class RewardedVideoManager:
    """Manages rewarded video ad requests and completions."""

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        req_repo: AdRequestRepositoryProtocol,
        imp_repo: AdImpressionRepositoryProtocol,
        free_repo: AdFreeStatusRepositoryProtocol,
        rew_repo: AdRewardRepositoryProtocol,
        provider: AdProviderProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._players = player_service
        self._req_repo = req_repo
        self._imp_repo = imp_repo
        self._free_repo = free_repo
        self._rew_repo = rew_repo
        self._provider = provider
        self._cd_inter: int = config.get("ads.interstitial_cooldown_seconds", 180)
        self._cd_reward: int = config.get("ads.rewarded_cooldown_seconds", 60)
        self._rw_pct: int = config.get("ads.rewarded_min_watch_percent", 95)
        self._rw_val: int = config.get("ads.rewarded_heart_reward", 1)
        self._cpm: int = config.get("ads.estimated_cpm_cents", 200)

    async def request_rewarded_video(
        self, player_id: PlayerId, reward_type: RewardedAdType
    ) -> RewardedVideoRequest:
        await self._players.get_player(player_id)
        await guard_ad_free(player_id, self._free_repo, self._errors)
        await guard_cooldown(
            player_id,
            AdType.REWARDED,
            self._cd_inter,
            self._cd_reward,
            self._req_repo,
            self._errors,
        )
        unit = self._config.get("ads.rewarded_unit_id", "default_rewarded")
        resp = await provider_call(
            self._provider.request_rewarded_video,
            unit,
            player_id,
            self._config,
            self._logger,
            self._errors,
        )
        exp = datetime.now(timezone.utc) + timedelta(minutes=_AD_REQUEST_EXPIRY_MINUTES)
        req = await self._req_repo.create(
            AdRequestCreate(
                player_id=player_id,
                ad_type=AdType.REWARDED.value,
                ad_unit_id=unit,
                trigger="rewarded_request",
                reward_type=reward_type.value,
                reward_value=self._rw_val,
                status=AdRequestStatus.PENDING.value,
                expires_at=exp,
                provider_response=resp.ad_data,
            )
        )
        self._logger.info(
            "Rewarded video requested",
            player_id=str(player_id),
            reward_type=reward_type.value,
        )
        return RewardedVideoRequest(
            ad_request_id=AdRequestId(req.id),
            ad_unit_id=unit,
            reward_type=reward_type,
            reward_value=self._rw_val,
            video_available=resp.ad_available,
            ad_data=resp.ad_data,
            expires_at=exp,
        )

    async def complete_rewarded_video(
        self,
        ad_request_id: AdRequestId,
        completed: bool,
        watched_duration_ms: int,
    ) -> RewardedVideoResult:
        ar = await valid_request(ad_request_id, self._req_repo, self._errors)
        pct = (watched_duration_ms / _STANDARD_VIDEO_DURATION_MS) * 100
        granted = completed and pct >= self._rw_pct
        rev = calc_revenue(AdType.REWARDED, completed, self._cpm)
        rec = await self._imp_repo.create(
            AdImpressionCreate(
                player_id=ar.player_id,
                ad_type=AdType.REWARDED.value,
                trigger="rewarded_request",
                viewed=completed,
                view_duration_ms=watched_duration_ms,
                completed=completed,
                ad_request_id=ad_request_id,
                match_id=ar.match_id,
                estimated_revenue_cents=rev,
            )
        )
        rtype, rval = None, None
        if granted and ar.reward_type:
            rtype = RewardedAdType(ar.reward_type)
            rval = ar.reward_value
            await self._rew_repo.create(
                AdRewardCreate(
                    player_id=ar.player_id,
                    ad_request_id=ad_request_id,
                    impression_id=rec.id,
                    reward_type=rtype.value,
                    reward_value=rval or 0,
                )
            )
        await self._req_repo.update(
            ad_request_id,
            AdRequestUpdate(
                status=AdRequestStatus.COMPLETED.value,
                completed_at=datetime.now(timezone.utc),
            ),
        )
        if granted:
            self._logger.info(
                "Rewarded video completed",
                player_id=str(ar.player_id),
                ad_request_id=str(ad_request_id),
                reward_granted=True,
            )
        else:
            self._logger.debug(
                "Rewarded video abandoned",
                player_id=str(ar.player_id),
                ad_request_id=str(ad_request_id),
                watched_percent=int(pct),
            )
        return RewardedVideoResult(
            ad_request_id=ad_request_id,
            completed=completed,
            watched_duration_ms=watched_duration_ms,
            reward_granted=granted,
            reward_type=rtype,
            reward_value=rval,
            impression=build_impression(rec),
        )
