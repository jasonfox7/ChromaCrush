"""Bot earnings module types -- enums and domain dataclasses.

Defines earnings-related types, statuses, periods, and all output
dataclasses returned by the BotEarningsService public interface.

Note: ``PlayerId``, ``MatchId`` are imported from
``src.core.types.game`` and are NOT redefined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import NewType
from uuid import UUID

from src.core.types.game import MatchId, PlayerId

# ---------------------------------------------------------------------------
# Opaque identifiers
# ---------------------------------------------------------------------------

PayoutRequestId = NewType("PayoutRequestId", UUID)
AttributionEntryId = NewType("AttributionEntryId", UUID)
AdImpressionId = NewType("AdImpressionId", UUID)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EarningsPeriod(Enum):
    """Time periods for earnings summaries."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    LIFETIME = "lifetime"


class PayoutStatus(Enum):
    """Lifecycle states for a payout request."""

    PENDING = "pending"  # Awaiting processing
    PROCESSING = "processing"  # Being processed (reserved for future automation)
    COMPLETED = "completed"  # Successfully paid out
    REJECTED = "rejected"  # Rejected by admin
    CANCELLED = "cancelled"  # Cancelled by owner


# ---------------------------------------------------------------------------
# Output domain objects
# ---------------------------------------------------------------------------


@dataclass
class EarningsBalance:
    """Current earnings balance for a bot."""

    bot_player_id: PlayerId
    total_earned_cents: int  # Lifetime total
    total_paid_out_cents: int  # Lifetime payouts completed
    pending_payout_cents: int  # In pending payout requests
    available_balance_cents: int  # Earned - paid out - pending
    last_attribution_at: datetime | None
    last_sync_at: datetime | None


@dataclass
class EarningsSummary:
    """Earnings summary for a time period."""

    bot_player_id: PlayerId
    period: EarningsPeriod
    period_start: date
    period_end: date
    total_attributions: int  # Number of attribution entries
    total_matches: int  # Matches that generated attributions
    total_impressions: int  # Ad impressions attributed
    earnings_cents: int  # Total earnings in period
    average_daily_cents: int  # Average daily earnings
    top_earning_day: date | None  # Best day in period
    top_earning_day_cents: int  # Earnings on best day


@dataclass
class AttributionEntry:
    """Individual attribution record (audit trail)."""

    id: AttributionEntryId
    bot_player_id: PlayerId
    match_id: MatchId
    ad_impression_id: AdImpressionId
    opponent_player_id: PlayerId  # Human who saw the ad
    estimated_impression_revenue_cents: int
    attribution_share_percent: float
    attributed_cents: int  # The bot's share
    recorded_at: datetime
    attribution_date: date  # Date the impression occurred


@dataclass
class DailyEarnings:
    """Earnings breakdown for a single day."""

    date: date
    attributions: int
    matches: int
    impressions: int
    earnings_cents: int


@dataclass
class AttributionSyncResult:
    """Result of syncing attributions from ads module."""

    bot_player_id: PlayerId
    new_attributions: int  # Number of new entries created
    new_earnings_cents: int  # Total new earnings synced
    sync_start: datetime
    sync_end: datetime
    errors: list[str] = field(default_factory=list)


@dataclass
class BulkSyncResult:
    """Result of bulk sync for all bots."""

    bots_synced: int
    total_new_attributions: int
    total_new_earnings_cents: int
    errors: list[tuple[PlayerId, str]]
    sync_start: datetime
    sync_end: datetime


@dataclass
class PayoutRequest:
    """A payout request from a bot owner."""

    id: PayoutRequestId
    bot_player_id: PlayerId
    owner_player_id: PlayerId  # Who requested the payout
    amount_cents: int  # Amount requested
    status: PayoutStatus  # pending, processing, completed, rejected, cancelled
    requested_at: datetime
    processed_at: datetime | None
    processed_by: PlayerId | None  # Admin who processed
    external_reference: str | None  # External payment reference
    rejection_reason: str | None
    notes: str | None
