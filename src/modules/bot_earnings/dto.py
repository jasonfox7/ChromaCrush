"""Data Transfer Objects for the bot_earnings module.

Pure data carriers used by repositories and the service layer.
No database or business logic awareness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from src.core.types.pagination import PaginatedResult as PaginatedResult  # noqa: F401


@dataclass
class EarningsLedgerCreate:
    """Data required to create an earnings ledger entry."""

    bot_player_id: UUID
    owner_player_id: UUID
    total_earned_cents: int = 0
    total_paid_out_cents: int = 0
    pending_payout_cents: int = 0


@dataclass
class EarningsLedgerUpdate:
    """Fields that can be updated on an earnings ledger entry."""

    total_earned_cents: int | None = None
    total_paid_out_cents: int | None = None
    pending_payout_cents: int | None = None
    last_attribution_at: datetime | None = None
    last_sync_at: datetime | None = None


@dataclass
class AttributionEntryCreate:
    """Data required to create an attribution entry."""

    bot_player_id: UUID
    match_id: UUID
    ad_impression_id: UUID
    opponent_player_id: UUID
    estimated_impression_revenue_cents: int
    attribution_share_percent: float
    attributed_cents: int
    attribution_date: date


@dataclass
class PayoutRequestCreate:
    """Data required to create a payout request."""

    bot_player_id: UUID
    owner_player_id: UUID
    amount_cents: int
    status: str = "pending"
    hold_until: datetime | None = None


@dataclass
class PayoutRequestUpdate:
    """Fields that can be updated on a payout request."""

    status: str | None = None
    processed_at: datetime | None = None
    processed_by: UUID | None = None
    external_reference: str | None = None
    rejection_reason: str | None = None
    notes: str | None = None


@dataclass
class DailyEarningsUpsert:
    """Data for creating or updating a daily earnings record."""

    bot_player_id: UUID
    earnings_date: date
    attributions_count: int = 0
    matches_count: int = 0
    impressions_count: int = 0
    earnings_cents: int = 0
