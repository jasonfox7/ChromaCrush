"""Bot earnings module for ChromaCrush.

Tracks bot revenue share from ad impressions, manages attribution syncing,
earnings ledger, payout requests, and daily earnings reports.
This module is fully async -- all public service methods are ``async def``.

Exports:
    BotEarningsService: Concrete service implementation.
    BotEarningsServiceProtocol: Protocol interface for dependency injection.
"""

from src.modules.bot_earnings.dto import (
    AttributionEntryCreate,
    DailyEarningsUpsert,
    EarningsLedgerCreate,
    EarningsLedgerUpdate,
    PaginatedResult,
    PayoutRequestCreate,
    PayoutRequestUpdate,
)
from src.modules.bot_earnings.protocols import BotEarningsServiceProtocol
from src.modules.bot_earnings.service import BotEarningsService
from src.modules.bot_earnings.types import (
    AdImpressionId,
    AttributionEntry,
    AttributionEntryId,
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

__all__ = [
    "AdImpressionId",
    "AttributionEntry",
    "AttributionEntryCreate",
    "AttributionEntryId",
    "AttributionSyncResult",
    "BotEarningsService",
    "BotEarningsServiceProtocol",
    "BulkSyncResult",
    "DailyEarnings",
    "DailyEarningsUpsert",
    "EarningsBalance",
    "EarningsLedgerCreate",
    "EarningsLedgerUpdate",
    "EarningsPeriod",
    "EarningsSummary",
    "PaginatedResult",
    "PayoutRequest",
    "PayoutRequestCreate",
    "PayoutRequestId",
    "PayoutRequestUpdate",
    "PayoutStatus",
]
