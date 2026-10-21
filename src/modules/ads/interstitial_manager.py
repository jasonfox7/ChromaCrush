"""Interstitial ad manager.

Handles requesting and recording interstitial ad impressions.
Internal module — not exported from ``__init__.py``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from src.core.types.game import MatchId, PlayerId
from src.modules.ads._helpers import (
    build_ad_free_status,
    build_impression,
    calc_revenue,
    guard_ad_free,
    guard_cooldown,
    provider_call,
    valid_request,
)
from src.modules.ads.dto import AdImpressionCreate, AdRequestCreate, AdRequestUpdate
from src.modules.ads.types import (
    AdImpression,
    AdRequestId,
    AdRequestStatus,
    AdType,
    InterstitialAdResult,
    InterstitialTrigger,
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
        PlayerServiceProtocol,
    )

_AD_REQUEST_EXPIRY_MINUTES = 5


class InterstitialManager:
    """Manages interstitial ad requests and impressions."""

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        req_repo: AdRequestRepositoryProtocol,
        imp_repo: AdImpressionRepositoryProtocol,
        free_repo: AdFreeStatusRepositoryProtocol,
        provider: AdProviderProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._players = player_service
        self._req_repo = req_repo
        self._imp_repo = imp_repo
        self._free_repo = free_repo
        self._provider = provider
        self._cd_inter: int = config.get("ads.interstitial_cooldown_seconds", 180)
        self._cd_reward: int = config.get("ads.rewarded_cooldown_seconds", 60)
        self._cpm: int = config.get("ads.estimated_cpm_cents", 200)

    async def request_interstitial(
        self,
        player_id: PlayerId,
        trigger: InterstitialTrigger,
        match_id: MatchId | None = None,
    ) -> InterstitialAdResult:
        await self._players.get_player(player_id)
        await guard_ad_free(player_id, self._free_repo, self._errors)
        await guard_cooldown(
            player_id,
            AdType.INTERSTITIAL,
            self._cd_inter,
            self._cd_reward,
            self._req_repo,
            self._errors,
        )
        unit = self._config.get("ads.interstitial_unit_id", "default_interstitial")
        resp = await provider_call(
            self._provider.request_interstitial,
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
                ad_type=AdType.INTERSTITIAL.value,
                ad_unit_id=unit,
                trigger=trigger.value,
                match_id=match_id,
                status=AdRequestStatus.PENDING.value,
                expires_at=exp,
                provider_response=resp.ad_data,
            )
        )
        self._logger.info(
            "Interstitial requested",
            player_id=str(player_id),
            trigger=trigger.value,
            match_id=str(match_id) if match_id else None,
        )
        return InterstitialAdResult(
            ad_request_id=AdRequestId(req.id),
            ad_unit_id=unit,
            should_show=resp.ad_available,
            ad_data=resp.ad_data,
            created_at=req.created_at,
        )

    async def record_interstitial_impression(
        self,
        ad_request_id: AdRequestId,
        viewed: bool,
        duration_ms: int,
    ) -> AdImpression:
        ar = await valid_request(ad_request_id, self._req_repo, self._errors)
        await self._mid_request_check(ar)
        rev = calc_revenue(AdType.INTERSTITIAL, viewed, self._cpm)
        rec = await self._imp_repo.create(
            AdImpressionCreate(
                player_id=ar.player_id,
                ad_type=AdType.INTERSTITIAL.value,
                trigger=ar.trigger or "interstitial",
                viewed=viewed,
                view_duration_ms=duration_ms,
                ad_request_id=ad_request_id,
                match_id=ar.match_id,
                estimated_revenue_cents=rev,
            )
        )
        await self._req_repo.update(
            ad_request_id,
            AdRequestUpdate(
                status=AdRequestStatus.SHOWN.value,
                completed_at=datetime.now(timezone.utc),
            ),
        )
        lvl = "info" if viewed else "debug"
        msg = "Interstitial shown" if viewed else "Interstitial skipped"
        getattr(self._logger, lvl)(
            msg,
            player_id=str(ar.player_id),
            ad_request_id=str(ad_request_id),
            duration_ms=duration_ms,
        )
        return build_impression(rec)

    async def _mid_request_check(self, ar: object) -> None:
        """Block impression if player became ad-free after the request was created."""
        rec = await self._free_repo.find_by_player(PlayerId(ar.player_id))  # type: ignore[attr-defined]
        st = build_ad_free_status(rec, PlayerId(ar.player_id))  # type: ignore[attr-defined]
        if st.is_ad_free and st.granted_at and st.granted_at > ar.created_at:  # type: ignore[attr-defined]
            raise self._errors.forbidden(
                "Player became ad-free after request",
                code="FORBIDDEN_PLAYER_AD_FREE",
                player_id=str(ar.player_id),  # type: ignore[attr-defined]
            )
