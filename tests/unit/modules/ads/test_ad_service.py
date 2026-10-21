"""Comprehensive unit tests for AdService.

Tests all 16 public methods plus error paths:
check_ad_free_status, can_show_ad, request_interstitial,
record_interstitial_impression, request_rewarded_video,
complete_rewarded_video, record_banner_impression,
get_player_ad_stats, get_ad_impressions, get_match_ad_attribution,
get_bot_ad_attributions, grant_ad_free_status, revoke_ad_free_status,
get_event_ad_opportunities, claim_event_ad_reward.

Uses pytest + pytest-asyncio with AsyncMock/MagicMock dependencies.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.core.errors import AppError
from src.core.types.game import EventId, MatchId, PlayerId
from src.modules.ads.dto import PaginatedResult
from src.modules.ads.service import AdRepositoryBundle, AdService
from src.modules.ads.types import (
    AdEligibility,
    AdFreeReason,
    AdFreeStatus,
    AdImpression,
    AdProviderResponse,
    AdRequestId,
    AdRequestStatus,
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
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ============================================================================
# Helpers
# ============================================================================

NOW = datetime.now(timezone.utc)
HOUR_AGO = NOW - timedelta(hours=1)
FIVE_MIN_LATER = NOW + timedelta(minutes=5)


def _pid() -> PlayerId:
    return PlayerId(uuid4())


def _mid() -> MatchId:
    return MatchId(uuid4())


def _eid() -> EventId:
    return EventId(uuid4())


def _arid() -> AdRequestId:
    return AdRequestId(uuid4())


def make_player(player_id: PlayerId | None = None, is_bot: bool = False) -> MagicMock:
    """Create a mock Player-like object."""
    p = MagicMock()
    p.id = player_id or _pid()
    p.username = "testplayer"
    p.is_bot = is_bot
    return p


def make_ad_request(
    request_id: UUID | None = None,
    player_id: UUID | None = None,
    ad_type: str = "interstitial",
    status: str = "pending",
    trigger: str | None = "match_end",
    reward_type: str | None = None,
    reward_value: int | None = None,
    match_id: UUID | None = None,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> MagicMock:
    """Create a mock AdRequest-like object."""
    ar = MagicMock()
    ar.id = request_id or uuid4()
    ar.player_id = player_id or uuid4()
    ar.ad_type = ad_type
    ar.status = status
    ar.trigger = trigger
    ar.reward_type = reward_type
    ar.reward_value = reward_value
    ar.match_id = match_id
    ar.created_at = created_at or NOW
    ar.expires_at = expires_at or FIVE_MIN_LATER
    ar.completed_at = completed_at
    return ar


def make_impression(
    imp_id: UUID | None = None,
    player_id: UUID | None = None,
    ad_type: str = "interstitial",
    viewed: bool = True,
    view_duration_ms: int = 5000,
    trigger: str = "match_end",
    ad_request_id: UUID | None = None,
    match_id: UUID | None = None,
    event_id: UUID | None = None,
    attributed_to: UUID | None = None,
    estimated_revenue_cents: int | None = 0,
    completed: bool = False,
) -> MagicMock:
    """Create a mock AdImpression-like record."""
    r = MagicMock()
    r.id = imp_id or uuid4()
    r.player_id = player_id or uuid4()
    r.ad_type = ad_type
    r.viewed = viewed
    r.view_duration_ms = view_duration_ms
    r.trigger = trigger
    r.ad_request_id = ad_request_id
    r.match_id = match_id
    r.event_id = event_id
    r.attributed_to = attributed_to
    r.estimated_revenue_cents = estimated_revenue_cents
    r.completed = completed
    r.created_at = NOW
    return r


def make_ad_free_record(
    player_id: UUID | None = None,
    is_ad_free: bool = True,
    reason: str = "purchase",
    granted_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> MagicMock:
    """Create a mock AdFreeStatus record."""
    r = MagicMock()
    r.player_id = player_id or uuid4()
    r.is_ad_free = is_ad_free
    r.reason = reason
    r.granted_at = granted_at or NOW
    r.expires_at = expires_at
    r.revoked_at = None
    r.revoke_reason = None
    return r


def make_opportunity(
    opp_id: str = "watch_bonus",
    event_id: UUID | None = None,
    ad_type: str = "rewarded",
    reward_type: str = "bonus_points",
    reward_value: int = 100,
    times_available_per_player: int = 3,
    cooldown_minutes: int | None = 60,
    description: str = "Watch ad for bonus",
) -> MagicMock:
    """Create a mock EventAdOpportunity record."""
    o = MagicMock()
    o.id = opp_id
    o.event_id = event_id or uuid4()
    o.ad_type = ad_type
    o.reward_type = reward_type
    o.reward_value = reward_value
    o.times_available_per_player = times_available_per_player
    o.cooldown_minutes = cooldown_minutes
    o.description = description
    o.created_at = NOW
    return o


def make_claim(
    claimed_at: datetime | None = None,
) -> MagicMock:
    """Create a mock EventAdClaim record."""
    c = MagicMock()
    c.claimed_at = claimed_at or NOW
    return c


def make_provider_response(available: bool = True) -> AdProviderResponse:
    return AdProviderResponse(
        success=True, ad_available=available, ad_data={"provider": "mock"}
    )


def build_service(
    config_overrides: dict | None = None,
    player_service: AsyncMock | None = None,
    events_service: AsyncMock | None = None,
    req_repo: AsyncMock | None = None,
    imp_repo: AsyncMock | None = None,
    free_repo: AsyncMock | None = None,
    rew_repo: AsyncMock | None = None,
    opp_repo: AsyncMock | None = None,
    claim_repo: AsyncMock | None = None,
    ad_provider: AsyncMock | None = None,
) -> tuple[AdService, dict[str, AsyncMock]]:
    """Build AdService with injected mocks. Returns (service, mocks_dict)."""
    config = MockConfigService(config_overrides or {})
    logger = MockLogService()
    errors = MockErrorService(logger)

    ps = player_service or AsyncMock()
    if player_service is None:
        ps.get_player = AsyncMock(return_value=make_player())

    es = events_service or AsyncMock()
    if events_service is None:
        es.get_event = AsyncMock(return_value=MagicMock())
        es.get_event_participant = AsyncMock(return_value=MagicMock())

    rr = req_repo or AsyncMock()
    ir = imp_repo or AsyncMock()
    fr = free_repo or AsyncMock()
    wr = rew_repo or AsyncMock()
    op = opp_repo or AsyncMock()
    cr = claim_repo or AsyncMock()
    ap = ad_provider or AsyncMock()

    # Set default return values for free_repo
    if free_repo is None:
        fr.find_by_player = AsyncMock(return_value=None)

    # Set default return value for ad provider
    if ad_provider is None:
        ap.request_interstitial = AsyncMock(return_value=make_provider_response())
        ap.request_rewarded_video = AsyncMock(return_value=make_provider_response())

    repos = AdRepositoryBundle(
        ad_request=rr,
        ad_impression=ir,
        ad_free_status=fr,
        ad_reward=wr,
        event_opportunity=op,
        event_claim=cr,
    )

    svc = AdService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=ps,
        events_service=es,
        repos=repos,
        ad_provider=ap,
    )

    mocks = {
        "config": config,
        "logger": logger,
        "errors": errors,
        "player_service": ps,
        "events_service": es,
        "req_repo": rr,
        "imp_repo": ir,
        "free_repo": fr,
        "rew_repo": wr,
        "opp_repo": op,
        "claim_repo": cr,
        "ad_provider": ap,
    }
    return svc, mocks


# ============================================================================
# check_ad_free_status
# ============================================================================


@pytest.mark.asyncio
async def test_check_ad_free_status_not_ad_free() -> None:
    """Player with no ad-free record returns is_ad_free=False."""
    svc, m = build_service()
    pid = _pid()
    result = await svc.check_ad_free_status(pid)
    assert result.is_ad_free is False
    m["player_service"].get_player.assert_awaited_once_with(pid)


@pytest.mark.asyncio
async def test_check_ad_free_status_active() -> None:
    """Player with active ad-free record returns is_ad_free=True."""
    pid = _pid()
    rec = make_ad_free_record(player_id=pid, is_ad_free=True)
    free_repo = AsyncMock()
    free_repo.find_by_player = AsyncMock(return_value=rec)
    svc, m = build_service(free_repo=free_repo)
    result = await svc.check_ad_free_status(pid)
    assert result.is_ad_free is True
    assert result.reason == AdFreeReason.PURCHASE


@pytest.mark.asyncio
async def test_check_ad_free_status_expired() -> None:
    """Ad-free with past expires_at returns is_ad_free=False."""
    pid = _pid()
    rec = make_ad_free_record(
        player_id=pid,
        is_ad_free=True,
        expires_at=NOW - timedelta(days=1),
    )
    free_repo = AsyncMock()
    free_repo.find_by_player = AsyncMock(return_value=rec)
    svc, _ = build_service(free_repo=free_repo)
    result = await svc.check_ad_free_status(pid)
    assert result.is_ad_free is False


# ============================================================================
# can_show_ad
# ============================================================================


@pytest.mark.asyncio
async def test_can_show_ad_eligible() -> None:
    """Non-ad-free player with no recent request is eligible."""
    req_repo = AsyncMock()
    req_repo.find_last_by_type = AsyncMock(return_value=None)
    svc, _ = build_service(req_repo=req_repo)
    result = await svc.can_show_ad(_pid(), AdType.INTERSTITIAL)
    assert result.can_show is True


@pytest.mark.asyncio
async def test_can_show_ad_ad_free_player() -> None:
    """Ad-free player is not eligible."""
    pid = _pid()
    rec = make_ad_free_record(player_id=pid, is_ad_free=True)
    free_repo = AsyncMock()
    free_repo.find_by_player = AsyncMock(return_value=rec)
    svc, _ = build_service(free_repo=free_repo)
    result = await svc.can_show_ad(pid, AdType.INTERSTITIAL)
    assert result.can_show is False
    assert "ad-free" in result.reason.lower()


@pytest.mark.asyncio
async def test_can_show_ad_cooldown_active() -> None:
    """Player with recent request is on cooldown."""
    pid = _pid()
    last = make_ad_request(player_id=pid, created_at=NOW - timedelta(seconds=30))
    req_repo = AsyncMock()
    req_repo.find_last_by_type = AsyncMock(return_value=last)
    svc, _ = build_service(req_repo=req_repo)
    result = await svc.can_show_ad(pid, AdType.INTERSTITIAL)
    assert result.can_show is False
    assert result.cooldown_remaining_seconds is not None
    assert result.cooldown_remaining_seconds > 0


# ============================================================================
# grant_ad_free_status
# ============================================================================


@pytest.mark.asyncio
async def test_grant_ad_free_status_success() -> None:
    """Granting ad-free status returns correct result."""
    pid = _pid()
    rec = make_ad_free_record(player_id=pid, is_ad_free=True, reason="purchase")
    free_repo = AsyncMock()
    free_repo.upsert = AsyncMock(return_value=rec)
    free_repo.find_by_player = AsyncMock(return_value=None)
    svc, _ = build_service(free_repo=free_repo)
    result = await svc.grant_ad_free_status(pid, AdFreeReason.PURCHASE)
    assert result.is_ad_free is True
    free_repo.upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_grant_ad_free_status_with_duration() -> None:
    """Granting ad-free with duration sets expires_at."""
    pid = _pid()
    rec = make_ad_free_record(
        player_id=pid,
        is_ad_free=True,
        expires_at=NOW + timedelta(days=7),
    )
    free_repo = AsyncMock()
    free_repo.upsert = AsyncMock(return_value=rec)
    free_repo.find_by_player = AsyncMock(return_value=None)
    svc, _ = build_service(free_repo=free_repo)
    result = await svc.grant_ad_free_status(
        pid, AdFreeReason.PROMOTION, duration_days=7
    )
    assert result.is_ad_free is True
    call_args = free_repo.upsert.call_args[0][0]
    assert call_args.expires_at is not None


@pytest.mark.asyncio
async def test_grant_ad_free_invalid_duration() -> None:
    """Negative duration raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.grant_ad_free_status(_pid(), AdFreeReason.PURCHASE, duration_days=-1)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ============================================================================
# revoke_ad_free_status
# ============================================================================


@pytest.mark.asyncio
async def test_revoke_ad_free_status_success() -> None:
    """Revoking active ad-free succeeds."""
    pid = _pid()
    rec = make_ad_free_record(player_id=pid, is_ad_free=True)
    free_repo = AsyncMock()
    free_repo.find_by_player = AsyncMock(return_value=rec)
    free_repo.revoke = AsyncMock(return_value=rec)
    svc, _ = build_service(free_repo=free_repo)
    await svc.revoke_ad_free_status(pid, "Refund processed")
    free_repo.revoke.assert_awaited_once_with(pid, "Refund processed")


@pytest.mark.asyncio
async def test_revoke_ad_free_status_not_active() -> None:
    """Revoking when not ad-free raises not_found."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.revoke_ad_free_status(_pid(), "No reason")
    assert exc_info.value.code == "NOT_FOUND_PLAYER"


@pytest.mark.asyncio
async def test_revoke_ad_free_reason_too_long() -> None:
    """Reason over 500 chars raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.revoke_ad_free_status(_pid(), "x" * 501)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ============================================================================
# request_interstitial
# ============================================================================


@pytest.mark.asyncio
async def test_request_interstitial_success() -> None:
    """Successful interstitial request returns result with request ID."""
    pid = _pid()
    req_repo = AsyncMock()
    req_repo.find_last_by_type = AsyncMock(return_value=None)
    req_rec = make_ad_request(player_id=pid)
    req_repo.create = AsyncMock(return_value=req_rec)

    svc, _ = build_service(req_repo=req_repo)
    result = await svc.request_interstitial(pid, InterstitialTrigger.MATCH_END)
    assert isinstance(result, InterstitialAdResult)
    assert result.should_show is True
    assert result.ad_request_id is not None
    req_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_interstitial_ad_free_blocked() -> None:
    """Ad-free player cannot request interstitial."""
    pid = _pid()
    rec = make_ad_free_record(player_id=pid, is_ad_free=True)
    free_repo = AsyncMock()
    free_repo.find_by_player = AsyncMock(return_value=rec)
    svc, _ = build_service(free_repo=free_repo)
    with pytest.raises(AppError) as exc_info:
        await svc.request_interstitial(pid, InterstitialTrigger.MATCH_END)
    assert exc_info.value.code == "FORBIDDEN_PLAYER_AD_FREE"


@pytest.mark.asyncio
async def test_request_interstitial_cooldown() -> None:
    """Request during cooldown raises rate_limited error."""
    pid = _pid()
    last = make_ad_request(player_id=pid, created_at=NOW - timedelta(seconds=10))
    req_repo = AsyncMock()
    req_repo.find_last_by_type = AsyncMock(return_value=last)
    svc, _ = build_service(req_repo=req_repo)
    with pytest.raises(AppError) as exc_info:
        await svc.request_interstitial(pid, InterstitialTrigger.MATCH_END)
    assert exc_info.value.code == "RATE_LIMIT_AD_COOLDOWN"


# ============================================================================
# record_interstitial_impression
# ============================================================================


@pytest.mark.asyncio
async def test_record_interstitial_impression_success() -> None:
    """Recording a viewed interstitial creates impression and updates request."""
    pid = _pid()
    rid = _arid()
    ar = make_ad_request(request_id=rid, player_id=pid, status="pending")
    imp_rec = make_impression(player_id=pid, ad_request_id=rid, viewed=True)

    req_repo = AsyncMock()
    req_repo.find_by_id = AsyncMock(return_value=ar)
    req_repo.update = AsyncMock(return_value=ar)
    imp_repo = AsyncMock()
    imp_repo.create = AsyncMock(return_value=imp_rec)
    free_repo = AsyncMock()
    free_repo.find_by_player = AsyncMock(return_value=None)

    svc, _ = build_service(req_repo=req_repo, imp_repo=imp_repo, free_repo=free_repo)
    result = await svc.record_interstitial_impression(rid, True, 5000)
    assert isinstance(result, AdImpression)
    assert result.viewed is True
    imp_repo.create.assert_awaited_once()
    req_repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_interstitial_not_found() -> None:
    """Recording with invalid request ID raises not_found."""
    req_repo = AsyncMock()
    req_repo.find_by_id = AsyncMock(return_value=None)
    svc, _ = build_service(req_repo=req_repo)
    with pytest.raises(AppError) as exc_info:
        await svc.record_interstitial_impression(_arid(), True, 5000)
    assert exc_info.value.code == "NOT_FOUND_AD_REQUEST"


@pytest.mark.asyncio
async def test_record_interstitial_already_recorded() -> None:
    """Recording on already-completed request raises conflict."""
    ar = make_ad_request(status="shown")
    req_repo = AsyncMock()
    req_repo.find_by_id = AsyncMock(return_value=ar)
    svc, _ = build_service(req_repo=req_repo)
    with pytest.raises(AppError) as exc_info:
        await svc.record_interstitial_impression(AdRequestId(ar.id), True, 5000)
    assert exc_info.value.code == "CONFLICT_AD_ALREADY_RECORDED"


@pytest.mark.asyncio
async def test_record_interstitial_expired() -> None:
    """Recording on expired request raises conflict."""
    ar = make_ad_request(
        status="pending",
        expires_at=NOW - timedelta(minutes=1),
    )
    req_repo = AsyncMock()
    req_repo.find_by_id = AsyncMock(return_value=ar)
    req_repo.update = AsyncMock(return_value=ar)
    svc, _ = build_service(req_repo=req_repo)
    with pytest.raises(AppError) as exc_info:
        await svc.record_interstitial_impression(AdRequestId(ar.id), True, 5000)
    assert exc_info.value.code == "CONFLICT_AD_REQUEST_EXPIRED"


# ============================================================================
# request_rewarded_video
# ============================================================================


@pytest.mark.asyncio
async def test_request_rewarded_video_success() -> None:
    """Successful rewarded video request returns result."""
    pid = _pid()
    req_repo = AsyncMock()
    req_repo.find_last_by_type = AsyncMock(return_value=None)
    req_rec = make_ad_request(player_id=pid, ad_type="rewarded")
    req_repo.create = AsyncMock(return_value=req_rec)

    svc, _ = build_service(req_repo=req_repo)
    result = await svc.request_rewarded_video(pid, RewardedAdType.BONUS_HEART)
    assert isinstance(result, RewardedVideoRequest)
    assert result.video_available is True
    assert result.reward_type == RewardedAdType.BONUS_HEART


# ============================================================================
# complete_rewarded_video
# ============================================================================


@pytest.mark.asyncio
async def test_complete_rewarded_video_granted() -> None:
    """Fully watched rewarded video grants reward."""
    pid = _pid()
    rid = _arid()
    ar = make_ad_request(
        request_id=rid,
        player_id=pid,
        status="pending",
        ad_type="rewarded",
        reward_type="bonus_heart",
        reward_value=1,
    )
    imp_rec = make_impression(
        player_id=pid,
        ad_request_id=rid,
        ad_type="rewarded",
        viewed=True,
        completed=True,
        view_duration_ms=30000,
    )

    req_repo = AsyncMock()
    req_repo.find_by_id = AsyncMock(return_value=ar)
    req_repo.update = AsyncMock(return_value=ar)
    imp_repo = AsyncMock()
    imp_repo.create = AsyncMock(return_value=imp_rec)
    rew_repo = AsyncMock()
    rew_repo.create = AsyncMock(return_value=MagicMock())

    svc, _ = build_service(req_repo=req_repo, imp_repo=imp_repo, rew_repo=rew_repo)
    result = await svc.complete_rewarded_video(
        rid, completed=True, watched_duration_ms=30000
    )
    assert isinstance(result, RewardedVideoResult)
    assert result.reward_granted is True
    assert result.reward_type == RewardedAdType.BONUS_HEART
    assert result.reward_value == 1
    rew_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_complete_rewarded_video_not_granted() -> None:
    """Partially watched rewarded video does not grant reward."""
    pid = _pid()
    rid = _arid()
    ar = make_ad_request(
        request_id=rid,
        player_id=pid,
        status="pending",
        ad_type="rewarded",
        reward_type="bonus_heart",
        reward_value=1,
    )
    imp_rec = make_impression(
        player_id=pid,
        ad_request_id=rid,
        ad_type="rewarded",
        viewed=False,
        completed=False,
        view_duration_ms=10000,
    )

    req_repo = AsyncMock()
    req_repo.find_by_id = AsyncMock(return_value=ar)
    req_repo.update = AsyncMock(return_value=ar)
    imp_repo = AsyncMock()
    imp_repo.create = AsyncMock(return_value=imp_rec)
    rew_repo = AsyncMock()

    svc, _ = build_service(req_repo=req_repo, imp_repo=imp_repo, rew_repo=rew_repo)
    result = await svc.complete_rewarded_video(
        rid, completed=False, watched_duration_ms=10000
    )
    assert result.reward_granted is False
    rew_repo.create.assert_not_awaited()


# ============================================================================
# record_banner_impression
# ============================================================================


@pytest.mark.asyncio
async def test_record_banner_impression_success() -> None:
    """Banner with sufficient view time is recorded."""
    pid = _pid()
    imp_rec = make_impression(
        player_id=pid,
        ad_type="banner",
        viewed=True,
        view_duration_ms=5000,
    )
    imp_repo = AsyncMock()
    imp_repo.create = AsyncMock(return_value=imp_rec)

    svc, _ = build_service(imp_repo=imp_repo)
    result = await svc.record_banner_impression(pid, BannerPlacement.MAIN_MENU, 5000)
    assert isinstance(result, AdImpression)
    imp_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_banner_too_short() -> None:
    """Banner with view time below minimum raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.record_banner_impression(_pid(), BannerPlacement.MAIN_MENU, 500)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


@pytest.mark.asyncio
async def test_record_banner_ad_free_blocked() -> None:
    """Ad-free player cannot record banner impression."""
    pid = _pid()
    rec = make_ad_free_record(player_id=pid, is_ad_free=True)
    free_repo = AsyncMock()
    free_repo.find_by_player = AsyncMock(return_value=rec)
    svc, _ = build_service(free_repo=free_repo)
    with pytest.raises(AppError) as exc_info:
        await svc.record_banner_impression(pid, BannerPlacement.MAIN_MENU, 5000)
    assert exc_info.value.code == "FORBIDDEN_PLAYER_AD_FREE"


# ============================================================================
# get_player_ad_stats
# ============================================================================


@pytest.mark.asyncio
async def test_get_player_ad_stats_success() -> None:
    """Player stats returns aggregated data."""
    pid = _pid()
    stats_rec = MagicMock()
    stats_rec.total_impressions = 50
    stats_rec.interstitial_count = 30
    stats_rec.rewarded_video_count = 15
    stats_rec.banner_impression_count = 5
    stats_rec.total_rewards_earned = 10
    stats_rec.average_view_duration_ms = 4500
    stats_rec.last_ad_at = NOW

    imp_repo = AsyncMock()
    imp_repo.get_player_stats = AsyncMock(return_value=stats_rec)

    svc, _ = build_service(imp_repo=imp_repo)
    result = await svc.get_player_ad_stats(pid, StatsPeriod.LIFETIME)
    assert isinstance(result, PlayerAdStats)
    assert result.total_impressions == 50
    assert result.interstitial_count == 30


# ============================================================================
# get_ad_impressions
# ============================================================================


@pytest.mark.asyncio
async def test_get_ad_impressions_success() -> None:
    """Returns paginated impression list."""
    pid = _pid()
    recs = [make_impression(player_id=pid) for _ in range(3)]
    imp_repo = AsyncMock()
    imp_repo.find_by_player = AsyncMock(return_value=(recs, 3))

    svc, _ = build_service(imp_repo=imp_repo)
    result = await svc.get_ad_impressions(pid, ad_type=None, limit=50, offset=0)
    assert isinstance(result, PaginatedResult)
    assert len(result.items) == 3
    assert result.total == 3


@pytest.mark.asyncio
async def test_get_ad_impressions_invalid_limit() -> None:
    """Limit outside 1-100 range raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.get_ad_impressions(_pid(), limit=200)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ============================================================================
# get_match_ad_attribution
# ============================================================================


@pytest.mark.asyncio
async def test_get_match_ad_attribution_with_impressions() -> None:
    """Match with impressions returns attribution data."""
    mid = _mid()
    bot_id = uuid4()
    recs = [
        make_impression(attributed_to=bot_id, estimated_revenue_cents=10),
        make_impression(attributed_to=bot_id, estimated_revenue_cents=10),
    ]
    imp_repo = AsyncMock()
    imp_repo.find_by_match = AsyncMock(return_value=recs)

    svc, _ = build_service(imp_repo=imp_repo)
    result = await svc.get_match_ad_attribution(mid)
    assert isinstance(result, MatchAdAttribution)
    assert result.total_impressions == 2
    assert result.estimated_revenue_cents == 20


@pytest.mark.asyncio
async def test_get_match_ad_attribution_no_impressions() -> None:
    """Match with no impressions returns empty attribution."""
    mid = _mid()
    imp_repo = AsyncMock()
    imp_repo.find_by_match = AsyncMock(return_value=[])

    svc, _ = build_service(imp_repo=imp_repo)
    result = await svc.get_match_ad_attribution(mid)
    assert result.total_impressions == 0
    assert result.estimated_revenue_cents == 0


# ============================================================================
# get_bot_ad_attributions
# ============================================================================


@pytest.mark.asyncio
async def test_get_bot_ad_attributions_success() -> None:
    """Bot attribution report returns aggregated data."""
    pid = _pid()
    bot = make_player(player_id=pid, is_bot=True)

    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=bot)

    agg = MagicMock()
    agg.total_matches = 100
    agg.matches_with_impressions = 80
    agg.total_attributed_impressions = 80
    agg.estimated_revenue_cents = 1600
    agg.attributed_revenue_cents = 480

    daily_rec = MagicMock()
    daily_rec.date = date(2026, 1, 1)
    daily_rec.matches = 10
    daily_rec.impressions = 8
    daily_rec.estimated_revenue_cents = 16
    daily_rec.attributed_cents = 5

    imp_repo = AsyncMock()
    imp_repo.get_bot_attributions = AsyncMock(return_value=agg)
    imp_repo.get_daily_attributions = AsyncMock(return_value=[daily_rec])

    svc, _ = build_service(player_service=ps, imp_repo=imp_repo)
    result = await svc.get_bot_ad_attributions(
        pid,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )
    assert isinstance(result, BotAdAttributionReport)
    assert result.total_matches == 100
    assert len(result.daily_breakdown) == 1


@pytest.mark.asyncio
async def test_get_bot_ad_attributions_not_bot() -> None:
    """Non-bot player raises validation error."""
    pid = _pid()
    player = make_player(player_id=pid, is_bot=False)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    svc, _ = build_service(player_service=ps)
    with pytest.raises(AppError) as exc_info:
        await svc.get_bot_ad_attributions(pid, date(2026, 1, 1), date(2026, 1, 31))
    assert exc_info.value.code == "VALIDATION_PLAYER_NOT_BOT"


@pytest.mark.asyncio
async def test_get_bot_ad_attributions_invalid_dates() -> None:
    """End date before start date raises validation error."""
    pid = _pid()
    bot = make_player(player_id=pid, is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=bot)

    svc, _ = build_service(player_service=ps)
    with pytest.raises(AppError) as exc_info:
        await svc.get_bot_ad_attributions(pid, date(2026, 2, 1), date(2026, 1, 1))
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ============================================================================
# get_event_ad_opportunities
# ============================================================================


@pytest.mark.asyncio
async def test_get_event_ad_opportunities_success() -> None:
    """Returns list of opportunities with claim counts."""
    pid = _pid()
    eid = _eid()
    opp = make_opportunity(event_id=eid)

    opp_repo = AsyncMock()
    opp_repo.find_by_event = AsyncMock(return_value=[opp])
    claim_repo = AsyncMock()
    claim_repo.count_claims = AsyncMock(return_value=1)

    svc, _ = build_service(opp_repo=opp_repo, claim_repo=claim_repo)
    result = await svc.get_event_ad_opportunities(pid, eid)
    assert len(result) == 1
    assert isinstance(result[0], EventAdOpportunity)
    assert result[0].times_claimed == 1
    assert result[0].available is True  # 1 < 3


@pytest.mark.asyncio
async def test_get_event_ad_opportunities_fully_claimed() -> None:
    """Opportunity with all claims used shows available=False."""
    pid = _pid()
    eid = _eid()
    opp = make_opportunity(event_id=eid, times_available_per_player=1)

    opp_repo = AsyncMock()
    opp_repo.find_by_event = AsyncMock(return_value=[opp])
    claim_repo = AsyncMock()
    claim_repo.count_claims = AsyncMock(return_value=1)

    svc, _ = build_service(opp_repo=opp_repo, claim_repo=claim_repo)
    result = await svc.get_event_ad_opportunities(pid, eid)
    assert result[0].available is False


# ============================================================================
# claim_event_ad_reward
# ============================================================================


@pytest.mark.asyncio
async def test_claim_event_ad_reward_success() -> None:
    """Successfully claiming an event ad opportunity."""
    pid = _pid()
    eid = _eid()
    opp = make_opportunity(event_id=eid, cooldown_minutes=None)
    imp_rec = make_impression(player_id=pid, ad_type="rewarded", event_id=eid)

    opp_repo = AsyncMock()
    opp_repo.find_by_id = AsyncMock(return_value=opp)
    claim_repo = AsyncMock()
    claim_repo.count_claims = AsyncMock(return_value=0)
    claim_repo.create = AsyncMock(return_value=MagicMock())
    imp_repo = AsyncMock()
    imp_repo.create = AsyncMock(return_value=imp_rec)

    svc, _ = build_service(opp_repo=opp_repo, claim_repo=claim_repo, imp_repo=imp_repo)
    result = await svc.claim_event_ad_reward(pid, eid, "watch_bonus")
    assert isinstance(result, EventAdRewardResult)
    assert result.reward_type == opp.reward_type
    assert result.reward_value == opp.reward_value
    claim_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_claim_event_ad_reward_not_found() -> None:
    """Claiming non-existent opportunity raises not_found."""
    opp_repo = AsyncMock()
    opp_repo.find_by_id = AsyncMock(return_value=None)

    svc, _ = build_service(opp_repo=opp_repo)
    with pytest.raises(AppError) as exc_info:
        await svc.claim_event_ad_reward(_pid(), _eid(), "nonexistent")
    assert exc_info.value.code == "NOT_FOUND_AD_OPPORTUNITY"


@pytest.mark.asyncio
async def test_claim_event_ad_reward_fully_claimed() -> None:
    """Claiming fully-used opportunity raises conflict."""
    eid = _eid()
    opp = make_opportunity(event_id=eid, times_available_per_player=1)

    opp_repo = AsyncMock()
    opp_repo.find_by_id = AsyncMock(return_value=opp)
    claim_repo = AsyncMock()
    claim_repo.count_claims = AsyncMock(return_value=1)

    svc, _ = build_service(opp_repo=opp_repo, claim_repo=claim_repo)
    with pytest.raises(AppError) as exc_info:
        await svc.claim_event_ad_reward(_pid(), eid, "watch_bonus")
    assert exc_info.value.code == "CONFLICT_OPPORTUNITY_ALREADY_CLAIMED"


@pytest.mark.asyncio
async def test_claim_event_ad_reward_cooldown() -> None:
    """Claiming during cooldown raises rate_limited."""
    eid = _eid()
    opp = make_opportunity(event_id=eid, cooldown_minutes=60)
    last = make_claim(claimed_at=NOW - timedelta(minutes=10))

    opp_repo = AsyncMock()
    opp_repo.find_by_id = AsyncMock(return_value=opp)
    claim_repo = AsyncMock()
    claim_repo.count_claims = AsyncMock(return_value=1)
    claim_repo.find_last_claim = AsyncMock(return_value=last)

    svc, _ = build_service(opp_repo=opp_repo, claim_repo=claim_repo)
    with pytest.raises(AppError) as exc_info:
        await svc.claim_event_ad_reward(_pid(), eid, "watch_bonus")
    assert exc_info.value.code == "RATE_LIMIT_OPPORTUNITY_COOLDOWN"


# ============================================================================
# Ad provider error handling
# ============================================================================


@pytest.mark.asyncio
async def test_interstitial_provider_error() -> None:
    """Ad provider error is caught and wrapped in internal error."""
    pid = _pid()
    req_repo = AsyncMock()
    req_repo.find_last_by_type = AsyncMock(return_value=None)

    ad_provider = AsyncMock()
    ad_provider.request_interstitial = AsyncMock(side_effect=Exception("Provider down"))

    svc, _ = build_service(req_repo=req_repo, ad_provider=ad_provider)
    with pytest.raises(AppError) as exc_info:
        await svc.request_interstitial(pid, InterstitialTrigger.MATCH_END)
    assert exc_info.value.code == "INTERNAL_AD_PROVIDER_ERROR"


# ============================================================================
# EC-1: Player becomes ad-free mid-request
# ============================================================================


@pytest.mark.asyncio
async def test_mid_request_ad_free_blocks_impression() -> None:
    """If player becomes ad-free after request, impression is blocked."""
    pid = _pid()
    rid = _arid()
    # Request was created an hour ago
    ar = make_ad_request(
        request_id=rid,
        player_id=pid,
        status="pending",
        created_at=NOW - timedelta(hours=1),
    )
    # Ad-free was granted 30 minutes ago (after request)
    rec = make_ad_free_record(
        player_id=pid,
        is_ad_free=True,
        granted_at=NOW - timedelta(minutes=30),
    )

    req_repo = AsyncMock()
    req_repo.find_by_id = AsyncMock(return_value=ar)
    free_repo = AsyncMock()
    free_repo.find_by_player = AsyncMock(return_value=rec)

    svc, _ = build_service(req_repo=req_repo, free_repo=free_repo)
    with pytest.raises(AppError) as exc_info:
        await svc.record_interstitial_impression(rid, True, 5000)
    assert exc_info.value.code == "FORBIDDEN_PLAYER_AD_FREE"
