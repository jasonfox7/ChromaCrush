"""Event ad opportunity service.

Handles listing event ad opportunities and claiming rewards.
Internal module — not exported from ``__init__.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.types.game import EventId, PlayerId
from src.modules.ads._helpers import build_event_opp, build_impression, calc_revenue
from src.modules.ads.dto import AdImpressionCreate, EventAdClaimCreate
from src.modules.ads.types import (
    AdType,
    EventAdOpportunity,
    EventAdRewardResult,
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.protocols import (
        AdImpressionRepositoryProtocol,
        EventAdClaimRepositoryProtocol,
        EventAdOpportunityRepositoryProtocol,
        EventServiceProtocol,
        PlayerServiceProtocol,
    )


class EventAdService:
    """Manages event ad opportunities and claims."""

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        events_service: EventServiceProtocol,
        opp_repo: EventAdOpportunityRepositoryProtocol,
        claim_repo: EventAdClaimRepositoryProtocol,
        imp_repo: AdImpressionRepositoryProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._players = player_service
        self._events = events_service
        self._opp_repo = opp_repo
        self._claim_repo = claim_repo
        self._imp_repo = imp_repo
        self._cpm: int = config.get("ads.estimated_cpm_cents", 200)

    async def get_event_ad_opportunities(
        self, player_id: PlayerId, event_id: EventId
    ) -> list[EventAdOpportunity]:
        await self._players.get_player(player_id)
        await self._events.get_event(event_id)
        await self._events.get_event_participant(event_id, player_id)
        opps = await self._opp_repo.find_by_event(event_id)
        results: list[EventAdOpportunity] = []
        for o in opps:
            c = await self._claim_repo.count_claims(event_id, o.id, player_id)
            avail = c < o.times_available_per_player
            results.append(build_event_opp(o, event_id, c, avail, None))
        return results

    async def claim_event_ad_reward(
        self,
        player_id: PlayerId,
        event_id: EventId,
        opportunity_id: str,
    ) -> EventAdRewardResult:
        await self._players.get_player(player_id)
        await self._events.get_event(event_id)
        await self._events.get_event_participant(event_id, player_id)
        opp = await self._opp_repo.find_by_id(event_id, opportunity_id)
        if opp is None:
            raise self._errors.not_found(
                "Ad opportunity not found",
                code="NOT_FOUND_AD_OPPORTUNITY",
                opportunity_id=opportunity_id,
            )
        claimed = await self._claim_repo.count_claims(
            event_id, opportunity_id, player_id
        )
        if claimed >= opp.times_available_per_player:
            raise self._errors.conflict(
                "Opportunity already fully claimed",
                code="CONFLICT_OPPORTUNITY_ALREADY_CLAIMED",
                opportunity_id=opportunity_id,
            )
        now = datetime.now(timezone.utc)
        if opp.cooldown_minutes:
            last = await self._claim_repo.find_last_claim(
                event_id, opportunity_id, player_id
            )
            if last:
                delta = (now - last.claimed_at).total_seconds()
                if delta < opp.cooldown_minutes * 60:
                    retry = max(0, int(opp.cooldown_minutes * 60 - delta))
                    raise self._errors.rate_limited(
                        "Opportunity on cooldown",
                        retry_after=retry,
                        code="RATE_LIMIT_OPPORTUNITY_COOLDOWN",
                        opportunity_id=opportunity_id,
                    )
        rev = calc_revenue(AdType(opp.ad_type), True, self._cpm)
        imp = await self._imp_repo.create(
            AdImpressionCreate(
                player_id=player_id,
                ad_type=opp.ad_type,
                trigger="event_opportunity",
                viewed=True,
                view_duration_ms=0,
                event_id=event_id,
                estimated_revenue_cents=rev,
            )
        )
        await self._claim_repo.create(
            EventAdClaimCreate(
                event_id=event_id,
                opportunity_id=opportunity_id,
                player_id=player_id,
                impression_id=imp.id,
            )
        )
        self._logger.info(
            "Event ad opportunity claimed",
            player_id=str(player_id),
            event_id=str(event_id),
            opportunity_id=opportunity_id,
        )
        return EventAdRewardResult(
            opportunity_id=opportunity_id,
            event_id=event_id,
            player_id=player_id,
            reward_type=opp.reward_type,
            reward_value=opp.reward_value,
            impression=build_impression(imp),
            claimed_at=now,
        )
