"""Private helper functions for the ads service.

Extracted to keep service.py under the 500-line hard limit.
These functions are not part of the public API.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Protocol, runtime_checkable

from src.core.types.game import EventId, MatchId, PlayerId
from src.modules.ads.dto import AdRequestUpdate
from src.modules.ads.types import (
    AdFreeReason,
    AdFreeStatus,
    AdImpression,
    AdImpressionId,
    AdProviderResponse,
    AdRequestId,
    AdRequestStatus,
    AdType,
    BotAdAttributionReport,
    DailyAttribution,
    EventAdOpportunity,
    MatchAdAttribution,
    PlayerAdStats,
    StatsPeriod,
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.protocols import (
        AdFreeStatusRepositoryProtocol,
        AdRequestRepositoryProtocol,
    )

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_REWARDED_CPM_MULTIPLIER = 1.5
_BANNER_CPM_MULTIPLIER = 0.3
_CPM_DIVISOR = 1000  # CPM = cost per mille (1000 impressions)
_WEEK_DAYS = 7
_MONTH_DAYS = 30

# ---------------------------------------------------------------------------
# Record protocols for type safety (replaces ``Any`` on helper parameters)
# ---------------------------------------------------------------------------


@runtime_checkable
class AdFreeStatusRecord(Protocol):
    """Shape of an ad-free status ORM record."""

    player_id: Any
    is_ad_free: bool
    reason: str | None
    granted_at: datetime | None
    expires_at: datetime | None


@runtime_checkable
class ImpressionRecord(Protocol):
    """Shape of an ad impression ORM record."""

    id: Any
    player_id: Any
    ad_type: str
    ad_request_id: Any | None
    viewed: bool
    view_duration_ms: int
    trigger: str
    match_id: Any | None
    event_id: Any | None
    attributed_to: Any | None
    estimated_revenue_cents: int | None
    created_at: datetime


@runtime_checkable
class PlayerStatsRecord(Protocol):
    """Shape of a player ad-stats aggregate record."""

    total_impressions: int
    interstitial_count: int
    rewarded_video_count: int
    banner_impression_count: int
    total_rewards_earned: int
    average_view_duration_ms: int
    last_ad_at: datetime | None


@runtime_checkable
class DailyAttributionRecord(Protocol):
    """Shape of a daily attribution aggregate record."""

    date: date
    matches: int
    impressions: int
    estimated_revenue_cents: int
    attributed_cents: int


@runtime_checkable
class EventOpportunityRecord(Protocol):
    """Shape of an event ad opportunity ORM record."""

    id: str
    ad_type: str
    reward_type: str
    reward_value: int
    description: str | None
    times_available_per_player: int
    cooldown_minutes: int | None


@runtime_checkable
class AdRequestRecord(Protocol):
    """Shape of an ad request ORM record used by service helpers."""

    id: Any
    player_id: Any
    ad_type: str
    status: str
    trigger: str | None
    match_id: Any | None
    reward_type: str | None
    reward_value: int | None
    expires_at: datetime
    completed_at: datetime | None
    created_at: datetime


@runtime_checkable
class BotAggregateRecord(Protocol):
    """Shape of bot attribution aggregate record."""

    total_matches: int
    matches_with_impressions: int
    total_attributed_impressions: int
    estimated_revenue_cents: int
    attributed_revenue_cents: int


def build_ad_free_status(
    record: AdFreeStatusRecord | None, player_id: PlayerId
) -> AdFreeStatus:
    """Convert an ad-free status record to domain object."""
    if record is None:
        return AdFreeStatus(player_id=PlayerId(player_id), is_ad_free=False)
    now = datetime.now(timezone.utc)
    is_expired = record.expires_at is not None and record.expires_at < now
    is_active = record.is_ad_free and not is_expired
    reason = None
    if record.reason:
        try:
            reason = AdFreeReason(record.reason)
        except ValueError:
            reason = None
    return AdFreeStatus(
        player_id=PlayerId(record.player_id),
        is_ad_free=is_active,
        reason=reason,
        granted_at=record.granted_at,
        expires_at=record.expires_at,
        is_permanent=record.expires_at is None and is_active,
    )


def build_impression(record: ImpressionRecord) -> AdImpression:
    """Convert an impression record to domain object."""
    return AdImpression(
        id=AdImpressionId(record.id),
        player_id=PlayerId(record.player_id),
        ad_type=AdType(record.ad_type),
        ad_request_id=(
            AdRequestId(record.ad_request_id) if record.ad_request_id else None
        ),
        viewed=record.viewed,
        view_duration_ms=record.view_duration_ms,
        trigger=record.trigger,
        match_id=MatchId(record.match_id) if record.match_id else None,
        event_id=EventId(record.event_id) if record.event_id else None,
        attributed_to=PlayerId(record.attributed_to) if record.attributed_to else None,
        estimated_revenue_cents=record.estimated_revenue_cents,
        created_at=record.created_at,
    )


def calc_revenue(ad_type: AdType, viewed: bool, cpm_cents: int) -> int:
    """Calculate estimated revenue in cents for an impression."""
    if not viewed:
        return 0
    effective = cpm_cents
    if ad_type == AdType.REWARDED:
        effective = int(cpm_cents * _REWARDED_CPM_MULTIPLIER)
    elif ad_type == AdType.BANNER:
        effective = int(cpm_cents * _BANNER_CPM_MULTIPLIER)
    return effective // _CPM_DIVISOR


def stats_date_range(period: StatsPeriod) -> tuple[date | None, date | None]:
    """Get start/end dates for a stats period."""
    if period == StatsPeriod.LIFETIME:
        return None, None
    today = datetime.now(timezone.utc).date()
    if period == StatsPeriod.DAY:
        return today, today
    if period == StatsPeriod.WEEK:
        return today - timedelta(days=_WEEK_DAYS), today
    if period == StatsPeriod.MONTH:
        return today - timedelta(days=_MONTH_DAYS), today
    return None, None


def build_player_stats(
    record: PlayerStatsRecord, pid: PlayerId, period: StatsPeriod
) -> PlayerAdStats:
    """Convert a stats record to domain object."""
    return PlayerAdStats(
        player_id=PlayerId(pid),
        period=period,
        total_impressions=getattr(record, "total_impressions", 0),
        interstitial_count=getattr(record, "interstitial_count", 0),
        rewarded_video_count=getattr(record, "rewarded_video_count", 0),
        banner_impression_count=getattr(record, "banner_impression_count", 0),
        total_rewards_earned=getattr(record, "total_rewards_earned", 0),
        average_view_duration_ms=getattr(record, "average_view_duration_ms", 0),
        last_ad_at=getattr(record, "last_ad_at", None),
    )


def build_daily_attr(record: DailyAttributionRecord) -> DailyAttribution:
    """Convert a daily attribution record to domain object."""
    return DailyAttribution(
        date=record.date,
        matches=getattr(record, "matches", 0),
        impressions=getattr(record, "impressions", 0),
        estimated_revenue_cents=getattr(record, "estimated_revenue_cents", 0),
        attributed_cents=getattr(record, "attributed_cents", 0),
    )


def build_event_opp(
    record: EventOpportunityRecord,
    event_id: EventId,
    claimed: int,
    avail: bool,
    next_at: datetime | None,
) -> EventAdOpportunity:
    """Convert event ad opportunity record to domain object."""
    return EventAdOpportunity(
        opportunity_id=record.id,
        event_id=EventId(event_id),
        ad_type=AdType(record.ad_type),
        reward_type=record.reward_type,
        reward_value=record.reward_value,
        description=record.description or "",
        times_available=record.times_available_per_player,
        times_claimed=claimed,
        cooldown_minutes=record.cooldown_minutes,
        available=avail,
        next_available_at=next_at,
    )


def build_match_attribution(
    match_id: MatchId,
    impressions: list[AdImpression],
    share: float,
) -> MatchAdAttribution:
    """Build MatchAdAttribution from impression list."""
    from uuid import UUID

    total_rev = sum(i.estimated_revenue_cents or 0 for i in impressions)
    bot_rev = sum(
        int((i.estimated_revenue_cents or 0) * share / 100)
        for i in impressions
        if i.attributed_to is not None
    )
    nil = PlayerId(UUID(int=0))
    p1 = impressions[0].player_id if impressions else nil
    p2 = (
        impressions[0].attributed_to
        if impressions and impressions[0].attributed_to
        else nil
    )
    return MatchAdAttribution(
        match_id=match_id,
        player1_id=p1,
        player2_id=p2,
        player1_is_bot=False,
        player2_is_bot=p2 != nil,
        impressions=impressions,
        total_impressions=len(impressions),
        estimated_revenue_cents=total_rev,
        bot_attribution_cents=bot_rev,
    )


def build_bot_report(
    pid: PlayerId,
    start: date,
    end: date,
    agg: BotAggregateRecord,
    daily_recs: list[DailyAttributionRecord],
    share: float,
) -> BotAdAttributionReport:
    """Build BotAdAttributionReport from aggregates."""
    daily = [build_daily_attr(r) for r in daily_recs]
    return BotAdAttributionReport(
        bot_player_id=pid,
        start_date=start,
        end_date=end,
        total_matches=getattr(agg, "total_matches", 0),
        matches_with_impressions=getattr(agg, "matches_with_impressions", 0),
        total_attributed_impressions=getattr(agg, "total_attributed_impressions", 0),
        estimated_revenue_cents=getattr(agg, "estimated_revenue_cents", 0),
        attributed_revenue_cents=getattr(agg, "attributed_revenue_cents", 0),
        attribution_share_percent=share,
        daily_breakdown=daily,
    )


# ---------------------------------------------------------------------------
# Shared guard / utility functions (used by multiple managers)
# ---------------------------------------------------------------------------


def cooldown_seconds(ad_type: AdType, cd_inter: int, cd_reward: int) -> int:
    """Return cooldown seconds for the given ad type."""
    if ad_type == AdType.INTERSTITIAL:
        return cd_inter
    if ad_type == AdType.REWARDED:
        return cd_reward
    return 0


async def guard_ad_free(
    player_id: PlayerId,
    free_repo: AdFreeStatusRepositoryProtocol,
    errors: ErrorServiceProtocol,
) -> None:
    """Raise FORBIDDEN if the player has ad-free status."""
    rec = await free_repo.find_by_player(player_id)
    st = build_ad_free_status(rec, player_id)
    if st.is_ad_free:
        raise errors.forbidden(
            "Player has ad-free status",
            code="FORBIDDEN_PLAYER_AD_FREE",
            player_id=str(player_id),
            reason=st.reason.value if st.reason else None,
        )


async def guard_cooldown(
    player_id: PlayerId,
    ad_type: AdType,
    cd_inter: int,
    cd_reward: int,
    req_repo: AdRequestRepositoryProtocol,
    errors: ErrorServiceProtocol,
) -> None:
    """Raise RATE_LIMITED if the player is on cooldown for this ad type."""
    cd = cooldown_seconds(ad_type, cd_inter, cd_reward)
    if cd <= 0:
        return
    last = await req_repo.find_last_by_type(player_id, ad_type.value)
    if last is None:
        return
    elapsed = (datetime.now(timezone.utc) - last.created_at).total_seconds()
    if elapsed < cd:
        raise errors.rate_limited(
            f"{ad_type.value} ad on cooldown",
            retry_after=int(cd - elapsed),
            code="RATE_LIMIT_AD_COOLDOWN",
            ad_type=ad_type.value,
        )


async def valid_request(
    rid: AdRequestId,
    req_repo: AdRequestRepositoryProtocol,
    errors: ErrorServiceProtocol,
) -> AdRequestRecord:
    """Fetch and validate an ad request by ID. Raises on not-found/conflict/expired."""
    ar = await req_repo.find_by_id(rid)
    if ar is None:
        raise errors.not_found(
            "Ad request not found",
            code="NOT_FOUND_AD_REQUEST",
            ad_request_id=str(rid),
        )
    if ar.status != AdRequestStatus.PENDING.value:
        raise errors.conflict(
            "Ad request already recorded",
            code="CONFLICT_AD_ALREADY_RECORDED",
            ad_request_id=str(rid),
            recorded_at=ar.completed_at.isoformat() if ar.completed_at else None,
        )
    if datetime.now(timezone.utc) > ar.expires_at:
        await req_repo.update(
            rid, AdRequestUpdate(status=AdRequestStatus.EXPIRED.value)
        )
        raise errors.conflict(
            "Ad request expired",
            code="CONFLICT_AD_REQUEST_EXPIRED",
            ad_request_id=str(rid),
            expired_at=ar.expires_at.isoformat(),
        )
    return ar


async def provider_call(
    fn: Callable[[str, str], Awaitable[AdProviderResponse]],
    unit: str,
    player_id: PlayerId,
    config: ConfigProtocol,
    logger: LoggerProtocol,
    errors: ErrorServiceProtocol,
) -> AdProviderResponse:
    """Call an ad provider function with error wrapping."""
    try:
        return await fn(unit, str(player_id))
    except Exception as exc:
        prov = config.get("ads.provider_name", "mock")
        logger.error(
            "Ad provider error",
            provider=prov,
            operation=fn.__name__,
            error=str(exc),
        )
        raise errors.internal(
            "Ad provider error",
            code="INTERNAL_AD_PROVIDER_ERROR",
            provider=prov,
            error=str(exc),
        ) from exc
