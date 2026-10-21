"""Banner ad manager.

Handles recording banner ad impressions.
Internal module — not exported from ``__init__.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.types.game import PlayerId
from src.modules.ads._helpers import build_impression, calc_revenue, guard_ad_free
from src.modules.ads.dto import AdImpressionCreate
from src.modules.ads.types import AdImpression, AdType, BannerPlacement

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.protocols import (
        AdFreeStatusRepositoryProtocol,
        AdImpressionRepositoryProtocol,
        PlayerServiceProtocol,
    )


class BannerManager:
    """Manages banner ad impressions."""

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        imp_repo: AdImpressionRepositoryProtocol,
        free_repo: AdFreeStatusRepositoryProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._players = player_service
        self._imp_repo = imp_repo
        self._free_repo = free_repo
        self._banner_min: int = config.get("ads.banner_min_view_ms", 1000)
        self._cpm: int = config.get("ads.estimated_cpm_cents", 200)

    async def record_banner_impression(
        self,
        player_id: PlayerId,
        banner_placement: BannerPlacement,
        view_duration_ms: int,
    ) -> AdImpression:
        await self._players.get_player(player_id)
        await guard_ad_free(player_id, self._free_repo, self._errors)
        if view_duration_ms < self._banner_min:
            raise self._errors.validation(
                "Banner view too short",
                code="VALIDATION_INVALID_INPUT",
                field="view_duration_ms",
                min_required=self._banner_min,
                actual=view_duration_ms,
            )
        rev = calc_revenue(AdType.BANNER, True, self._cpm)
        rec = await self._imp_repo.create(
            AdImpressionCreate(
                player_id=player_id,
                ad_type=AdType.BANNER.value,
                trigger="banner_view",
                viewed=True,
                view_duration_ms=view_duration_ms,
                placement=banner_placement.value,
                estimated_revenue_cents=rev,
            )
        )
        self._logger.debug(
            "Banner impression recorded",
            player_id=str(player_id),
            placement=banner_placement.value,
            duration_ms=view_duration_ms,
        )
        return build_impression(rec)
