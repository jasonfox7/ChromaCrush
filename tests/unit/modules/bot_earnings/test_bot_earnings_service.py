"""Comprehensive unit tests for BotEarningsService.

Tests all 13 public methods plus error paths:
get_earnings_balance, get_earnings_summary, get_attribution_entries,
get_daily_earnings, sync_attributions, sync_all_attributions,
request_payout, get_payout_requests, get_payout_request,
cancel_payout_request, process_payout, reject_payout, get_bot_owner.

Uses pytest + pytest-asyncio with AsyncMock/MagicMock dependencies.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.modules.bot_earnings.dto import PaginatedResult
from src.modules.bot_earnings.service import BotEarningsService
from src.modules.bot_earnings.types import (
    AttributionEntry,
    AttributionSyncResult,
    BulkSyncResult,
    DailyEarnings,
    EarningsBalance,
    EarningsPeriod,
    EarningsSummary,
    PayoutRequest,
    PayoutRequestId,
    PayoutStatus,
)
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ============================================================================
# Helpers
# ============================================================================

NOW = datetime.now(timezone.utc)
HOUR_AGO = NOW - timedelta(hours=1)


def _pid() -> PlayerId:
    return PlayerId(uuid4())


def _prid() -> PayoutRequestId:
    return PayoutRequestId(uuid4())


def make_player(
    player_id: PlayerId | None = None,
    is_bot: bool = False,
    owner_player_id: UUID | None = None,
) -> MagicMock:
    """Create a mock Player-like object."""
    p = MagicMock()
    p.id = player_id or _pid()
    p.username = "testbot"
    p.is_bot = is_bot
    p.owner_player_id = owner_player_id
    return p


def make_ledger(
    bot_player_id: UUID | None = None,
    owner_player_id: UUID | None = None,
    total_earned_cents: int = 5000,
    total_paid_out_cents: int = 1000,
    pending_payout_cents: int = 0,
    last_attribution_at: datetime | None = None,
    last_sync_at: datetime | None = None,
) -> MagicMock:
    """Create a mock ledger record."""
    r = MagicMock()
    r.bot_player_id = bot_player_id or uuid4()
    r.owner_player_id = owner_player_id or uuid4()
    r.total_earned_cents = total_earned_cents
    r.total_paid_out_cents = total_paid_out_cents
    r.pending_payout_cents = pending_payout_cents
    r.last_attribution_at = last_attribution_at
    r.last_sync_at = last_sync_at
    return r


def make_payout_record(
    payout_id: UUID | None = None,
    bot_player_id: UUID | None = None,
    owner_player_id: UUID | None = None,
    amount_cents: int = 4000,
    status: str = "pending",
    requested_at: datetime | None = None,
    processed_at: datetime | None = None,
    processed_by: UUID | None = None,
    external_reference: str | None = None,
    rejection_reason: str | None = None,
    notes: str | None = None,
    hold_until: datetime | None = None,
) -> MagicMock:
    """Create a mock payout request record."""
    r = MagicMock()
    r.id = payout_id or uuid4()
    r.bot_player_id = bot_player_id or uuid4()
    r.owner_player_id = owner_player_id or uuid4()
    r.amount_cents = amount_cents
    r.status = status
    r.requested_at = requested_at or NOW
    r.processed_at = processed_at
    r.processed_by = processed_by
    r.external_reference = external_reference
    r.rejection_reason = rejection_reason
    r.notes = notes
    r.hold_until = hold_until
    return r


def make_attribution_record(
    entry_id: UUID | None = None,
    bot_player_id: UUID | None = None,
    match_id: UUID | None = None,
    ad_impression_id: UUID | None = None,
    opponent_player_id: UUID | None = None,
    estimated_impression_revenue_cents: int = 100,
    attribution_share_percent: float = 30.0,
    attributed_cents: int = 30,
    attribution_date: date | None = None,
    recorded_at: datetime | None = None,
) -> MagicMock:
    """Create a mock attribution entry record."""
    r = MagicMock()
    r.id = entry_id or uuid4()
    r.bot_player_id = bot_player_id or uuid4()
    r.match_id = match_id or uuid4()
    r.ad_impression_id = ad_impression_id or uuid4()
    r.opponent_player_id = opponent_player_id or uuid4()
    r.estimated_impression_revenue_cents = estimated_impression_revenue_cents
    r.attribution_share_percent = attribution_share_percent
    r.attributed_cents = attributed_cents
    r.attribution_date = attribution_date or date.today()
    r.recorded_at = recorded_at or NOW
    return r


def make_daily_record(
    earnings_date: date | None = None,
    attributions_count: int = 10,
    matches_count: int = 8,
    impressions_count: int = 10,
    earnings_cents: int = 300,
) -> MagicMock:
    """Create a mock daily earnings record."""
    r = MagicMock()
    r.earnings_date = earnings_date or date.today()
    r.attributions_count = attributions_count
    r.matches_count = matches_count
    r.impressions_count = impressions_count
    r.earnings_cents = earnings_cents
    return r


def make_period_summary(
    total_attributions: int = 50,
    total_matches: int = 40,
    total_impressions: int = 50,
    total_cents: int = 1500,
) -> MagicMock:
    """Create a mock period summary record."""
    r = MagicMock()
    r.total_attributions = total_attributions
    r.total_matches = total_matches
    r.total_impressions = total_impressions
    r.total_cents = total_cents
    return r


def make_daily_summary_row(
    day: date,
    total_attributions: int = 5,
    total_matches: int = 4,
    total_impressions: int = 5,
    total_cents: int = 150,
) -> MagicMock:
    """Create a mock daily summary row from aggregate query."""
    r = MagicMock()
    r.date = day
    r.total_attributions = total_attributions
    r.total_matches = total_matches
    r.total_impressions = total_impressions
    r.total_cents = total_cents
    return r


def make_ads_report(
    bot_player_id: UUID | None = None,
    daily_breakdown: list | None = None,
) -> MagicMock:
    """Create a mock ads attribution report."""
    r = MagicMock()
    r.bot_player_id = bot_player_id or uuid4()
    r.start_date = date.today() - timedelta(days=7)
    r.end_date = date.today()
    r.total_matches = 10
    r.matches_with_impressions = 8
    r.total_attributed_impressions = 8
    r.estimated_revenue_cents = 1600
    r.attributed_revenue_cents = 480
    r.attribution_share_percent = 30.0
    r.daily_breakdown = daily_breakdown or []
    return r


def make_daily_attribution(
    day: date,
    matches: int = 5,
    impressions: int = 5,
    estimated_revenue_cents: int = 100,
    attributed_cents: int = 30,
) -> MagicMock:
    """Create a mock DailyAttribution from ads module."""
    d = MagicMock()
    d.date = day
    d.matches = matches
    d.impressions = impressions
    d.estimated_revenue_cents = estimated_revenue_cents
    d.attributed_cents = attributed_cents
    return d


def build_service(
    config_overrides: dict | None = None,
    player_service: AsyncMock | None = None,
    ads_service: AsyncMock | None = None,
    ledger_repo: AsyncMock | None = None,
    attribution_repo: AsyncMock | None = None,
    payout_repo: AsyncMock | None = None,
    daily_repo: AsyncMock | None = None,
) -> tuple[BotEarningsService, dict[str, AsyncMock]]:
    """Build BotEarningsService with injected mocks. Returns (service, mocks_dict)."""
    config = MockConfigService(config_overrides or {})
    logger = MockLogService()
    errors = MockErrorService(logger)

    ps = player_service or AsyncMock()
    if player_service is None:
        ps.get_player = AsyncMock(return_value=make_player(is_bot=True))

    ads = ads_service or AsyncMock()
    if ads_service is None:
        ads.get_bot_ad_attributions = AsyncMock(return_value=make_ads_report())

    lr = ledger_repo or AsyncMock()
    ar = attribution_repo or AsyncMock()
    pr = payout_repo or AsyncMock()
    dr = daily_repo or AsyncMock()

    # Default returns for repos
    if ledger_repo is None:
        lr.find_by_bot_id = AsyncMock(return_value=make_ledger())
        lr.create = AsyncMock(return_value=make_ledger())
        lr.update = AsyncMock(return_value=make_ledger())
        lr.increment_earned = AsyncMock(return_value=make_ledger())
        lr.increment_pending = AsyncMock(return_value=make_ledger())
        lr.complete_payout = AsyncMock(return_value=make_ledger())
        lr.cancel_pending = AsyncMock(return_value=make_ledger())
        lr.find_bots_needing_sync = AsyncMock(return_value=[])

    if attribution_repo is None:
        ar.find_by_bot = AsyncMock(return_value=([], 0))
        ar.find_by_impression_id = AsyncMock(return_value=None)
        ar.create_batch = AsyncMock(return_value=[])
        ar.get_period_summary = AsyncMock(return_value=make_period_summary())
        ar.get_daily_summary = AsyncMock(return_value=[])
        ar.get_last_recorded_for_bot = AsyncMock(return_value=None)

    if payout_repo is None:
        pr.find_pending_by_bot = AsyncMock(return_value=None)
        pr.find_by_id = AsyncMock(return_value=None)
        pr.create = AsyncMock(return_value=make_payout_record())
        pr.update = AsyncMock(return_value=make_payout_record())
        pr.find_by_bot = AsyncMock(return_value=([], 0))

    if daily_repo is None:
        dr.find_range = AsyncMock(return_value=[])
        dr.upsert = AsyncMock(return_value=make_daily_record())

    svc = BotEarningsService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=ps,
        ads_service=ads,
        earnings_ledger_repository=lr,
        attribution_entry_repository=ar,
        payout_request_repository=pr,
        daily_earnings_repository=dr,
    )

    mocks = {
        "config": config,
        "logger": logger,
        "errors": errors,
        "player_service": ps,
        "ads_service": ads,
        "ledger_repo": lr,
        "attribution_repo": ar,
        "payout_repo": pr,
        "daily_repo": dr,
    }
    return svc, mocks


# ============================================================================
# get_earnings_balance
# ============================================================================


@pytest.mark.asyncio
async def test_get_earnings_balance_success() -> None:
    """Bot with ledger returns correct balance."""
    bot_id = _pid()
    owner_id = _pid()
    ledger = make_ledger(
        bot_player_id=bot_id,
        owner_player_id=owner_id,
        total_earned_cents=5000,
        total_paid_out_cents=1000,
        pending_payout_cents=500,
    )
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=ledger)

    svc, _ = build_service(ledger_repo=lr)
    result = await svc.get_earnings_balance(bot_id)
    assert isinstance(result, EarningsBalance)
    assert result.total_earned_cents == 5000
    assert result.total_paid_out_cents == 1000
    assert result.pending_payout_cents == 500
    assert result.available_balance_cents == 3500


@pytest.mark.asyncio
async def test_get_earnings_balance_no_ledger() -> None:
    """Bot with no ledger returns zero balance (EC-1)."""
    bot_id = _pid()
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=None)

    svc, _ = build_service(ledger_repo=lr)
    result = await svc.get_earnings_balance(bot_id)
    assert result.total_earned_cents == 0
    assert result.available_balance_cents == 0


@pytest.mark.asyncio
async def test_get_earnings_balance_not_bot() -> None:
    """Non-bot player raises VALIDATION_PLAYER_NOT_BOT."""
    pid = _pid()
    player = make_player(player_id=pid, is_bot=False)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    svc, _ = build_service(player_service=ps)
    with pytest.raises(AppError) as exc_info:
        await svc.get_earnings_balance(pid)
    assert exc_info.value.code == "VALIDATION_PLAYER_NOT_BOT"


# ============================================================================
# get_earnings_summary
# ============================================================================


@pytest.mark.asyncio
async def test_get_earnings_summary_success() -> None:
    """Returns earnings summary for a period."""
    bot_id = _pid()
    summary = make_period_summary(
        total_attributions=50,
        total_matches=40,
        total_impressions=50,
        total_cents=1500,
    )
    daily_row = make_daily_summary_row(date.today(), total_cents=300)

    ar = AsyncMock()
    ar.get_period_summary = AsyncMock(return_value=summary)
    ar.get_daily_summary = AsyncMock(return_value=[daily_row])

    svc, _ = build_service(attribution_repo=ar)
    result = await svc.get_earnings_summary(bot_id, EarningsPeriod.MONTH)
    assert isinstance(result, EarningsSummary)
    assert result.total_attributions == 50
    assert result.earnings_cents == 1500
    assert result.top_earning_day == date.today()
    assert result.top_earning_day_cents == 300


@pytest.mark.asyncio
async def test_get_earnings_summary_not_bot() -> None:
    """Non-bot player raises error."""
    pid = _pid()
    player = make_player(player_id=pid, is_bot=False)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    svc, _ = build_service(player_service=ps)
    with pytest.raises(AppError) as exc_info:
        await svc.get_earnings_summary(pid)
    assert exc_info.value.code == "VALIDATION_PLAYER_NOT_BOT"


# ============================================================================
# get_attribution_entries
# ============================================================================


@pytest.mark.asyncio
async def test_get_attribution_entries_success() -> None:
    """Returns paginated attribution entries."""
    bot_id = _pid()
    records = [make_attribution_record(bot_player_id=bot_id) for _ in range(3)]
    ar = AsyncMock()
    ar.find_by_bot = AsyncMock(return_value=(records, 3))
    ar.get_period_summary = AsyncMock(return_value=make_period_summary())
    ar.get_daily_summary = AsyncMock(return_value=[])

    svc, _ = build_service(attribution_repo=ar)
    result = await svc.get_attribution_entries(bot_id)
    assert isinstance(result, PaginatedResult)
    assert len(result.items) == 3
    assert result.total == 3
    assert all(isinstance(a, AttributionEntry) for a in result.items)


@pytest.mark.asyncio
async def test_get_attribution_entries_invalid_limit() -> None:
    """Limit > 100 raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.get_attribution_entries(_pid(), limit=200)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


@pytest.mark.asyncio
async def test_get_attribution_entries_invalid_date_range() -> None:
    """End date before start date raises error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.get_attribution_entries(
            _pid(),
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
        )
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ============================================================================
# get_daily_earnings
# ============================================================================


@pytest.mark.asyncio
async def test_get_daily_earnings_success() -> None:
    """Returns daily earnings list."""
    bot_id = _pid()
    records = [make_daily_record(earnings_date=date(2026, 1, d)) for d in range(1, 4)]
    dr = AsyncMock()
    dr.find_range = AsyncMock(return_value=records)

    svc, _ = build_service(daily_repo=dr)
    result = await svc.get_daily_earnings(
        bot_id,
        date(2026, 1, 1),
        date(2026, 1, 3),
    )
    assert len(result) == 3
    assert all(isinstance(d, DailyEarnings) for d in result)


@pytest.mark.asyncio
async def test_get_daily_earnings_date_range_too_large() -> None:
    """Date range > max raises VALIDATION_DATE_RANGE_TOO_LARGE."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.get_daily_earnings(
            _pid(),
            date(2025, 1, 1),
            date(2026, 1, 1),
        )
    assert exc_info.value.code == "VALIDATION_DATE_RANGE_TOO_LARGE"


@pytest.mark.asyncio
async def test_get_daily_earnings_end_before_start() -> None:
    """End before start raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.get_daily_earnings(
            _pid(),
            date(2026, 2, 1),
            date(2026, 1, 1),
        )
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ============================================================================
# sync_attributions
# ============================================================================


@pytest.mark.asyncio
async def test_sync_attributions_success() -> None:
    """Sync with new data creates entries and updates ledger."""
    bot_id = _pid()
    owner_id = _pid()
    player = make_player(player_id=bot_id, is_bot=True, owner_player_id=owner_id)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    ledger = make_ledger(
        bot_player_id=bot_id,
        owner_player_id=owner_id,
        last_sync_at=None,
    )
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=ledger)
    lr.create = AsyncMock(return_value=ledger)
    lr.update = AsyncMock(return_value=ledger)
    lr.increment_earned = AsyncMock(return_value=ledger)

    daily_attr = make_daily_attribution(
        day=date.today() - timedelta(days=1),
        attributed_cents=50,
        impressions=5,
    )
    ads_report = make_ads_report(
        bot_player_id=bot_id,
        daily_breakdown=[daily_attr],
    )
    ads = AsyncMock()
    ads.get_bot_ad_attributions = AsyncMock(return_value=ads_report)

    ar = AsyncMock()
    ar.find_by_impression_id = AsyncMock(return_value=None)
    ar.create_batch = AsyncMock(return_value=[])
    ar.get_period_summary = AsyncMock(return_value=make_period_summary())
    ar.get_daily_summary = AsyncMock(return_value=[])

    dr = AsyncMock()
    dr.upsert = AsyncMock(return_value=make_daily_record())

    svc, _ = build_service(
        player_service=ps,
        ads_service=ads,
        ledger_repo=lr,
        attribution_repo=ar,
        daily_repo=dr,
    )
    result = await svc.sync_attributions(bot_id)
    assert isinstance(result, AttributionSyncResult)
    assert result.new_attributions == 1
    assert result.new_earnings_cents == 50
    ar.create_batch.assert_awaited_once()
    lr.increment_earned.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_attributions_no_new_data() -> None:
    """Sync with empty report returns zero new entries."""
    bot_id = _pid()
    player = make_player(player_id=bot_id, is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    ledger = make_ledger(bot_player_id=bot_id)
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=ledger)
    lr.update = AsyncMock(return_value=ledger)

    ads = AsyncMock()
    ads.get_bot_ad_attributions = AsyncMock(
        return_value=make_ads_report(daily_breakdown=[])
    )

    ar = AsyncMock()
    ar.get_period_summary = AsyncMock(return_value=make_period_summary())
    ar.get_daily_summary = AsyncMock(return_value=[])

    svc, _ = build_service(
        player_service=ps,
        ads_service=ads,
        ledger_repo=lr,
        attribution_repo=ar,
    )
    result = await svc.sync_attributions(bot_id)
    assert result.new_attributions == 0
    assert result.new_earnings_cents == 0


@pytest.mark.asyncio
async def test_sync_attributions_not_bot() -> None:
    """Non-bot raises VALIDATION_PLAYER_NOT_BOT."""
    pid = _pid()
    player = make_player(player_id=pid, is_bot=False)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    svc, _ = build_service(player_service=ps)
    with pytest.raises(AppError) as exc_info:
        await svc.sync_attributions(pid)
    assert exc_info.value.code == "VALIDATION_PLAYER_NOT_BOT"


@pytest.mark.asyncio
async def test_sync_attributions_ads_error() -> None:
    """Ads service error raises INTERNAL_ADS_SERVICE_ERROR."""
    bot_id = _pid()
    player = make_player(player_id=bot_id, is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    ledger = make_ledger(bot_player_id=bot_id)
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=ledger)

    ads = AsyncMock()
    ads.get_bot_ad_attributions = AsyncMock(side_effect=Exception("Ads unavailable"))

    svc, _ = build_service(player_service=ps, ads_service=ads, ledger_repo=lr)
    with pytest.raises(AppError) as exc_info:
        await svc.sync_attributions(bot_id)
    assert exc_info.value.code == "INTERNAL_ADS_SERVICE_ERROR"


@pytest.mark.asyncio
async def test_sync_attributions_dedup() -> None:
    """Duplicate impressions are skipped during sync (EC-2)."""
    bot_id = _pid()
    player = make_player(player_id=bot_id, is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    ledger = make_ledger(bot_player_id=bot_id, last_sync_at=None)
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=ledger)
    lr.update = AsyncMock(return_value=ledger)

    daily_attr = make_daily_attribution(
        day=date.today(),
        attributed_cents=50,
        impressions=5,
    )
    ads = AsyncMock()
    ads.get_bot_ad_attributions = AsyncMock(
        return_value=make_ads_report(daily_breakdown=[daily_attr]),
    )

    # Simulate that the impression already exists
    ar = AsyncMock()
    ar.find_by_impression_id = AsyncMock(return_value=MagicMock())  # Already exists
    ar.create_batch = AsyncMock(return_value=[])
    ar.get_period_summary = AsyncMock(return_value=make_period_summary())
    ar.get_daily_summary = AsyncMock(return_value=[])

    svc, _ = build_service(
        player_service=ps,
        ads_service=ads,
        ledger_repo=lr,
        attribution_repo=ar,
    )
    result = await svc.sync_attributions(bot_id)
    assert result.new_attributions == 0
    ar.create_batch.assert_not_awaited()


# ============================================================================
# sync_all_attributions
# ============================================================================


@pytest.mark.asyncio
async def test_sync_all_attributions_success() -> None:
    """Bulk sync processes all bots."""
    bot1_id = uuid4()
    bot2_id = uuid4()
    ledger1 = make_ledger(bot_player_id=bot1_id, last_sync_at=None)
    ledger2 = make_ledger(bot_player_id=bot2_id, last_sync_at=None)

    lr = AsyncMock()
    lr.find_bots_needing_sync = AsyncMock(return_value=[ledger1, ledger2])
    lr.find_by_bot_id = AsyncMock(return_value=make_ledger())
    lr.update = AsyncMock(return_value=make_ledger())

    player = make_player(is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    ads = AsyncMock()
    ads.get_bot_ad_attributions = AsyncMock(return_value=make_ads_report())

    ar = AsyncMock()
    ar.get_period_summary = AsyncMock(return_value=make_period_summary())
    ar.get_daily_summary = AsyncMock(return_value=[])

    svc, _ = build_service(
        player_service=ps,
        ads_service=ads,
        ledger_repo=lr,
        attribution_repo=ar,
    )
    result = await svc.sync_all_attributions()
    assert isinstance(result, BulkSyncResult)
    assert result.bots_synced == 2
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_sync_all_attributions_partial_failure() -> None:
    """Bulk sync continues when individual bot fails."""
    bot1_id = uuid4()
    ledger1 = make_ledger(bot_player_id=bot1_id)

    lr = AsyncMock()
    lr.find_bots_needing_sync = AsyncMock(return_value=[ledger1])
    lr.find_by_bot_id = AsyncMock(return_value=make_ledger())
    lr.update = AsyncMock(return_value=make_ledger())

    # Simulate player not found for this bot
    ps = AsyncMock()
    ps.get_player = AsyncMock(
        side_effect=AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
            http_status=404,
        )
    )

    svc, _ = build_service(player_service=ps, ledger_repo=lr)
    result = await svc.sync_all_attributions()
    assert result.bots_synced == 0
    assert len(result.errors) == 1


# ============================================================================
# request_payout
# ============================================================================


@pytest.mark.asyncio
async def test_request_payout_success() -> None:
    """Successful payout request creates record and updates ledger."""
    bot_id = _pid()
    owner_id = _pid()

    player = make_player(player_id=bot_id, is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    ledger = make_ledger(
        bot_player_id=bot_id,
        owner_player_id=owner_id,
        total_earned_cents=5000,
        total_paid_out_cents=0,
        pending_payout_cents=0,
    )
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=ledger)
    lr.increment_pending = AsyncMock(return_value=ledger)

    payout_rec = make_payout_record(
        bot_player_id=bot_id,
        owner_player_id=owner_id,
        amount_cents=5000,
        status="pending",
    )
    pr = AsyncMock()
    pr.find_pending_by_bot = AsyncMock(return_value=None)
    pr.create = AsyncMock(return_value=payout_rec)

    svc, _ = build_service(
        player_service=ps,
        ledger_repo=lr,
        payout_repo=pr,
    )
    result = await svc.request_payout(bot_id, owner_id)
    assert isinstance(result, PayoutRequest)
    assert result.status == PayoutStatus.PENDING
    assert result.amount_cents == 5000
    pr.create.assert_awaited_once()
    lr.increment_pending.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_payout_not_bot() -> None:
    """Non-bot raises VALIDATION_PLAYER_NOT_BOT."""
    pid = _pid()
    player = make_player(player_id=pid, is_bot=False)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    svc, _ = build_service(player_service=ps)
    with pytest.raises(AppError) as exc_info:
        await svc.request_payout(pid, _pid())
    assert exc_info.value.code == "VALIDATION_PLAYER_NOT_BOT"


@pytest.mark.asyncio
async def test_request_payout_no_ledger() -> None:
    """Bot with no ledger raises VALIDATION_INSUFFICIENT_BALANCE."""
    bot_id = _pid()
    player = make_player(player_id=bot_id, is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=None)

    svc, _ = build_service(player_service=ps, ledger_repo=lr)
    with pytest.raises(AppError) as exc_info:
        await svc.request_payout(bot_id, _pid())
    assert exc_info.value.code == "VALIDATION_INSUFFICIENT_BALANCE"


@pytest.mark.asyncio
async def test_request_payout_not_owner() -> None:
    """Non-owner raises FORBIDDEN_NOT_BOT_OWNER."""
    bot_id = _pid()
    owner_id = _pid()
    other_id = _pid()

    player = make_player(player_id=bot_id, is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    ledger = make_ledger(
        bot_player_id=bot_id,
        owner_player_id=owner_id,
    )
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=ledger)

    svc, _ = build_service(player_service=ps, ledger_repo=lr)
    with pytest.raises(AppError) as exc_info:
        await svc.request_payout(bot_id, other_id)
    assert exc_info.value.code == "FORBIDDEN_NOT_BOT_OWNER"


@pytest.mark.asyncio
async def test_request_payout_pending_exists() -> None:
    """Second payout request raises CONFLICT_PENDING_PAYOUT_EXISTS (EC-4)."""
    bot_id = _pid()
    owner_id = _pid()

    player = make_player(player_id=bot_id, is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    ledger = make_ledger(bot_player_id=bot_id, owner_player_id=owner_id)
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=ledger)

    existing = make_payout_record(status="pending")
    pr = AsyncMock()
    pr.find_pending_by_bot = AsyncMock(return_value=existing)

    svc, _ = build_service(player_service=ps, ledger_repo=lr, payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.request_payout(bot_id, owner_id)
    assert exc_info.value.code == "CONFLICT_PENDING_PAYOUT_EXISTS"


@pytest.mark.asyncio
async def test_request_payout_below_threshold() -> None:
    """Balance below minimum raises VALIDATION_BELOW_PAYOUT_THRESHOLD (EC-3)."""
    bot_id = _pid()
    owner_id = _pid()

    player = make_player(player_id=bot_id, is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    ledger = make_ledger(
        bot_player_id=bot_id,
        owner_player_id=owner_id,
        total_earned_cents=500,  # Below default 1000
        total_paid_out_cents=0,
        pending_payout_cents=0,
    )
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=ledger)

    pr = AsyncMock()
    pr.find_pending_by_bot = AsyncMock(return_value=None)

    svc, _ = build_service(player_service=ps, ledger_repo=lr, payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.request_payout(bot_id, owner_id)
    assert exc_info.value.code == "VALIDATION_BELOW_PAYOUT_THRESHOLD"


# ============================================================================
# get_payout_requests
# ============================================================================


@pytest.mark.asyncio
async def test_get_payout_requests_success() -> None:
    """Returns paginated payout requests."""
    bot_id = _pid()
    records = [make_payout_record() for _ in range(2)]
    pr = AsyncMock()
    pr.find_by_bot = AsyncMock(return_value=(records, 2))

    svc, _ = build_service(payout_repo=pr)
    result = await svc.get_payout_requests(bot_id, PayoutStatus.PENDING)
    assert isinstance(result, PaginatedResult)
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_get_payout_requests_not_bot() -> None:
    """Non-bot raises error."""
    pid = _pid()
    player = make_player(player_id=pid, is_bot=False)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    svc, _ = build_service(player_service=ps)
    with pytest.raises(AppError) as exc_info:
        await svc.get_payout_requests(pid)
    assert exc_info.value.code == "VALIDATION_PLAYER_NOT_BOT"


# ============================================================================
# get_payout_request
# ============================================================================


@pytest.mark.asyncio
async def test_get_payout_request_success() -> None:
    """Returns payout request by ID."""
    prid = _prid()
    record = make_payout_record(payout_id=prid)
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=record)

    svc, _ = build_service(payout_repo=pr)
    result = await svc.get_payout_request(prid)
    assert isinstance(result, PayoutRequest)
    assert result.id == prid


@pytest.mark.asyncio
async def test_get_payout_request_not_found() -> None:
    """Non-existent payout raises NOT_FOUND_PAYOUT_REQUEST."""
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=None)

    svc, _ = build_service(payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.get_payout_request(_prid())
    assert exc_info.value.code == "NOT_FOUND_PAYOUT_REQUEST"


# ============================================================================
# cancel_payout_request
# ============================================================================


@pytest.mark.asyncio
async def test_cancel_payout_request_success() -> None:
    """Successfully cancels a pending payout (EC-5)."""
    prid = _prid()
    owner_id = _pid()
    bot_id = _pid()

    record = make_payout_record(
        payout_id=prid,
        bot_player_id=bot_id,
        owner_player_id=owner_id,
        status="pending",
        amount_cents=3000,
    )
    updated = make_payout_record(
        payout_id=prid,
        bot_player_id=bot_id,
        owner_player_id=owner_id,
        status="cancelled",
    )
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=record)
    pr.update = AsyncMock(return_value=updated)

    lr = AsyncMock()
    lr.cancel_pending = AsyncMock(return_value=make_ledger())

    svc, _ = build_service(payout_repo=pr, ledger_repo=lr)
    result = await svc.cancel_payout_request(prid, owner_id)
    assert result.status == PayoutStatus.CANCELLED
    lr.cancel_pending.assert_awaited_once_with(bot_id, 3000)


@pytest.mark.asyncio
async def test_cancel_payout_request_not_found() -> None:
    """Not found raises error."""
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=None)

    svc, _ = build_service(payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.cancel_payout_request(_prid(), _pid())
    assert exc_info.value.code == "NOT_FOUND_PAYOUT_REQUEST"


@pytest.mark.asyncio
async def test_cancel_payout_not_pending() -> None:
    """Non-pending payout raises CONFLICT_PAYOUT_NOT_PENDING."""
    prid = _prid()
    owner_id = _pid()
    record = make_payout_record(
        payout_id=prid,
        owner_player_id=owner_id,
        status="completed",
    )
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=record)

    svc, _ = build_service(payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.cancel_payout_request(prid, owner_id)
    assert exc_info.value.code == "CONFLICT_PAYOUT_NOT_PENDING"


@pytest.mark.asyncio
async def test_cancel_payout_not_owner() -> None:
    """Non-owner raises FORBIDDEN_NOT_BOT_OWNER."""
    prid = _prid()
    owner_id = _pid()
    other_id = _pid()
    record = make_payout_record(
        payout_id=prid,
        owner_player_id=owner_id,
        status="pending",
    )
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=record)

    svc, _ = build_service(payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.cancel_payout_request(prid, other_id)
    assert exc_info.value.code == "FORBIDDEN_NOT_BOT_OWNER"


# ============================================================================
# process_payout
# ============================================================================


@pytest.mark.asyncio
async def test_process_payout_success() -> None:
    """Successfully processes a payout."""
    prid = _prid()
    processor_id = _pid()
    bot_id = _pid()

    record = make_payout_record(
        payout_id=prid,
        bot_player_id=bot_id,
        status="pending",
        amount_cents=5000,
    )
    updated = make_payout_record(
        payout_id=prid,
        bot_player_id=bot_id,
        status="completed",
        processed_by=processor_id,
        external_reference="PP-123",
    )
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=record)
    pr.update = AsyncMock(return_value=updated)

    lr = AsyncMock()
    lr.complete_payout = AsyncMock(return_value=make_ledger())

    svc, _ = build_service(payout_repo=pr, ledger_repo=lr)
    result = await svc.process_payout(prid, processor_id, external_reference="PP-123")
    assert result.status == PayoutStatus.COMPLETED
    lr.complete_payout.assert_awaited_once_with(bot_id, 5000)


@pytest.mark.asyncio
async def test_process_payout_not_found() -> None:
    """Non-existent request raises error."""
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=None)

    svc, _ = build_service(payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.process_payout(_prid(), _pid())
    assert exc_info.value.code == "NOT_FOUND_PAYOUT_REQUEST"


@pytest.mark.asyncio
async def test_process_payout_not_pending() -> None:
    """Non-pending request raises CONFLICT_PAYOUT_NOT_PENDING."""
    prid = _prid()
    record = make_payout_record(payout_id=prid, status="completed")
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=record)

    svc, _ = build_service(payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.process_payout(prid, _pid())
    assert exc_info.value.code == "CONFLICT_PAYOUT_NOT_PENDING"


@pytest.mark.asyncio
async def test_process_payout_ref_too_long() -> None:
    """External reference > 255 chars raises validation error."""
    prid = _prid()
    record = make_payout_record(payout_id=prid, status="pending")
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=record)

    svc, _ = build_service(payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.process_payout(prid, _pid(), external_reference="x" * 256)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ============================================================================
# reject_payout
# ============================================================================


@pytest.mark.asyncio
async def test_reject_payout_success() -> None:
    """Successfully rejects a payout."""
    prid = _prid()
    processor_id = _pid()
    bot_id = _pid()

    record = make_payout_record(
        payout_id=prid,
        bot_player_id=bot_id,
        status="pending",
        amount_cents=5000,
    )
    updated = make_payout_record(
        payout_id=prid,
        bot_player_id=bot_id,
        status="rejected",
        rejection_reason="Suspicious",
    )
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=record)
    pr.update = AsyncMock(return_value=updated)

    lr = AsyncMock()
    lr.cancel_pending = AsyncMock(return_value=make_ledger())

    svc, _ = build_service(payout_repo=pr, ledger_repo=lr)
    result = await svc.reject_payout(prid, processor_id, "Suspicious")
    assert result.status == PayoutStatus.REJECTED
    lr.cancel_pending.assert_awaited_once_with(bot_id, 5000)


@pytest.mark.asyncio
async def test_reject_payout_empty_reason() -> None:
    """Empty reason raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.reject_payout(_prid(), _pid(), "")
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


@pytest.mark.asyncio
async def test_reject_payout_reason_too_long() -> None:
    """Reason > 500 chars raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.reject_payout(_prid(), _pid(), "x" * 501)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


@pytest.mark.asyncio
async def test_reject_payout_not_found() -> None:
    """Non-existent request raises error."""
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=None)

    svc, _ = build_service(payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.reject_payout(_prid(), _pid(), "Bad bot")
    assert exc_info.value.code == "NOT_FOUND_PAYOUT_REQUEST"


@pytest.mark.asyncio
async def test_reject_payout_not_pending() -> None:
    """Non-pending raises conflict."""
    prid = _prid()
    record = make_payout_record(payout_id=prid, status="cancelled")
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=record)

    svc, _ = build_service(payout_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.reject_payout(prid, _pid(), "Testing")
    assert exc_info.value.code == "CONFLICT_PAYOUT_NOT_PENDING"


# ============================================================================
# get_bot_owner
# ============================================================================


@pytest.mark.asyncio
async def test_get_bot_owner_from_ledger() -> None:
    """Returns owner from ledger if it exists."""
    bot_id = _pid()
    owner_id = _pid()

    player = make_player(player_id=bot_id, is_bot=True)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    ledger = make_ledger(bot_player_id=bot_id, owner_player_id=owner_id)
    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=ledger)

    svc, _ = build_service(player_service=ps, ledger_repo=lr)
    result = await svc.get_bot_owner(bot_id)
    assert result == PlayerId(owner_id)


@pytest.mark.asyncio
async def test_get_bot_owner_no_ledger() -> None:
    """Returns owner from player if no ledger."""
    bot_id = _pid()
    owner_id = uuid4()

    player = make_player(player_id=bot_id, is_bot=True, owner_player_id=owner_id)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    lr = AsyncMock()
    lr.find_by_bot_id = AsyncMock(return_value=None)

    svc, _ = build_service(player_service=ps, ledger_repo=lr)
    result = await svc.get_bot_owner(bot_id)
    assert result == PlayerId(owner_id)


@pytest.mark.asyncio
async def test_get_bot_owner_not_bot() -> None:
    """Non-bot raises error."""
    pid = _pid()
    player = make_player(player_id=pid, is_bot=False)
    ps = AsyncMock()
    ps.get_player = AsyncMock(return_value=player)

    svc, _ = build_service(player_service=ps)
    with pytest.raises(AppError) as exc_info:
        await svc.get_bot_owner(pid)
    assert exc_info.value.code == "VALIDATION_PLAYER_NOT_BOT"


# ============================================================================
# Pagination validation
# ============================================================================


@pytest.mark.asyncio
async def test_pagination_negative_offset() -> None:
    """Negative offset raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.get_attribution_entries(_pid(), offset=-1)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


@pytest.mark.asyncio
async def test_pagination_zero_limit() -> None:
    """Zero limit raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.get_attribution_entries(_pid(), limit=0)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"
