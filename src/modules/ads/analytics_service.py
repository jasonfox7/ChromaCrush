"""Ad analytics service.

Read-only analytics: player stats, impression history, match attribution,
bot attribution reports.
Internal module — not exported from ``__init__.py``.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from src.core.types.game import MatchId, PlayerId
from src.modules.ads._helpers import (
    build_bot_report,
    build_impression,
    build_match_attribution,
    build_player_stats,
    stats_date_range,
)
from src.modules.ads.dto import PaginatedResult
from src.modules.ads.types import (
    AdImpression,
    AdType,
    BotAdAttributionReport,
    MatchAdAttribution,
    PlayerAdStats,
    StatsPeriod,
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.protocols import (
        AdImpressionRepositoryProtocol,
        PlayerServiceProtocol,
    )


class AdAnalyticsService:
    """Read-only ad analytics queries."""

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        imp_repo: AdImpressionRepositoryProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._players = player_service
        self._imp_repo = imp_repo
        self._bot_share: float = config.get("ads.bot_attribution_share_percent", 30.0)

    async def get_player_ad_stats(
        self, player_id: PlayerId, period: StatsPeriod = StatsPeriod.LIFETIME
    ) -> PlayerAdStats:
        await self._players.get_player(player_id)
        s, e = stats_date_range(period)
        rec = await self._imp_repo.get_player_stats(player_id, s, e)
        return build_player_stats(rec, player_id, period)

    async def get_ad_impressions(
        self,
        player_id: PlayerId,
        ad_type: AdType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[AdImpression]:
        await self._players.get_player(player_id)
        if limit < 1 or limit > 100:
            raise self._errors.validation(
                "Limit must be between 1 and 100",
                code="VALIDATION_INVALID_INPUT",
                field="limit",
            )
        ts = ad_type.value if ad_type else None
        recs, total = await self._imp_repo.find_by_player(player_id, ts, limit, offset)
        return PaginatedResult(
            items=[build_impression(r) for r in recs],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_match_ad_attribution(self, match_id: MatchId) -> MatchAdAttribution:
        recs = await self._imp_repo.find_by_match(match_id)
        imps = [build_impression(r) for r in recs]
        return build_match_attribution(match_id, imps, self._bot_share)

    async def get_bot_ad_attributions(
        self, bot_player_id: PlayerId, start_date: date, end_date: date
    ) -> BotAdAttributionReport:
        p = await self._players.get_player(bot_player_id)
        if not getattr(p, "is_bot", False):
            raise self._errors.validation(
                "Player is not a bot",
                code="VALIDATION_PLAYER_NOT_BOT",
                player_id=str(bot_player_id),
            )
        if end_date < start_date:
            raise self._errors.validation(
                "end_date must be >= start_date",
                code="VALIDATION_INVALID_INPUT",
                start_date=str(start_date),
                end_date=str(end_date),
            )
        agg = await self._imp_repo.get_bot_attributions(
            bot_player_id, start_date, end_date
        )
        daily = await self._imp_repo.get_daily_attributions(
            bot_player_id, start_date, end_date
        )
        return build_bot_report(
            bot_player_id, start_date, end_date, agg, daily, self._bot_share
        )
