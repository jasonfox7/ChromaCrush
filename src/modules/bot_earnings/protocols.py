"""Bot earnings module protocols -- typing.Protocol interfaces.

Defines the BotEarningsServiceProtocol (public interface), repository
protocols, and minimal dependency protocols for cross-module interactions.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID

from src.core.types.game import PlayerId
from src.modules.bot_earnings.dto import (
    AttributionEntryCreate,
    DailyEarningsUpsert,
    EarningsLedgerCreate,
    EarningsLedgerUpdate,
    PaginatedResult,
    PayoutRequestCreate,
    PayoutRequestUpdate,
)
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

# ---------------------------------------------------------------------------
# Public service protocol
# ---------------------------------------------------------------------------


class BotEarningsServiceProtocol(Protocol):
    """Public interface for the bot_earnings module."""

    async def get_earnings_balance(
        self,
        bot_player_id: PlayerId,
    ) -> EarningsBalance: ...

    async def get_earnings_summary(
        self,
        bot_player_id: PlayerId,
        period: EarningsPeriod = EarningsPeriod.LIFETIME,
    ) -> EarningsSummary: ...

    async def get_attribution_entries(
        self,
        bot_player_id: PlayerId,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[AttributionEntry]: ...

    async def get_daily_earnings(
        self,
        bot_player_id: PlayerId,
        start_date: date,
        end_date: date,
    ) -> list[DailyEarnings]: ...

    async def sync_attributions(
        self,
        bot_player_id: PlayerId,
    ) -> AttributionSyncResult: ...

    async def sync_all_attributions(self) -> BulkSyncResult: ...

    async def request_payout(
        self,
        bot_player_id: PlayerId,
        requesting_owner_id: PlayerId,
    ) -> PayoutRequest: ...

    async def get_payout_requests(
        self,
        bot_player_id: PlayerId,
        status: PayoutStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[PayoutRequest]: ...

    async def get_payout_request(
        self,
        payout_request_id: PayoutRequestId,
    ) -> PayoutRequest: ...

    async def cancel_payout_request(
        self,
        payout_request_id: PayoutRequestId,
        requesting_owner_id: PlayerId,
    ) -> PayoutRequest: ...

    async def process_payout(
        self,
        payout_request_id: PayoutRequestId,
        processor_id: PlayerId,
        external_reference: str | None = None,
    ) -> PayoutRequest: ...

    async def reject_payout(
        self,
        payout_request_id: PayoutRequestId,
        processor_id: PlayerId,
        reason: str,
    ) -> PayoutRequest: ...

    async def get_pending_payouts(
        self,
        past_hold_only: bool = False,
    ) -> list[PayoutRequest]: ...

    async def get_bot_owner(
        self,
        bot_player_id: PlayerId,
    ) -> PlayerId: ...


# ---------------------------------------------------------------------------
# Repository protocols
# ---------------------------------------------------------------------------


class EarningsLedgerRepositoryProtocol(Protocol):
    """Repository interface for earnings ledger."""

    async def find_by_bot_id(self, bot_player_id: UUID) -> Any | None: ...

    async def create(self, data: EarningsLedgerCreate) -> Any: ...

    async def update(
        self,
        bot_player_id: UUID,
        changes: EarningsLedgerUpdate,
    ) -> Any: ...

    async def increment_earned(
        self,
        bot_player_id: UUID,
        cents: int,
    ) -> Any: ...

    async def increment_pending(
        self,
        bot_player_id: UUID,
        cents: int,
    ) -> Any: ...

    async def complete_payout(
        self,
        bot_player_id: UUID,
        cents: int,
    ) -> Any: ...

    async def cancel_pending(
        self,
        bot_player_id: UUID,
        cents: int,
    ) -> Any: ...

    async def find_bots_needing_sync(
        self,
        since: datetime,
        limit: int = 100,
    ) -> list[Any]: ...


class AttributionEntryRepositoryProtocol(Protocol):
    """Repository interface for attribution entries."""

    async def create(self, data: AttributionEntryCreate) -> Any: ...

    async def create_batch(
        self,
        entries: list[AttributionEntryCreate],
    ) -> list[Any]: ...

    async def find_by_impression_id(
        self,
        ad_impression_id: UUID,
    ) -> Any | None: ...

    async def find_by_bot(
        self,
        bot_player_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]: ...

    async def get_daily_summary(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[Any]: ...

    async def get_period_summary(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Any: ...

    async def get_last_recorded_for_bot(
        self,
        bot_player_id: UUID,
    ) -> Any | None: ...


class PayoutRequestRepositoryProtocol(Protocol):
    """Repository interface for payout requests."""

    async def create(self, data: PayoutRequestCreate) -> Any: ...

    async def find_by_id(
        self,
        payout_request_id: UUID,
    ) -> Any | None: ...

    async def update(
        self,
        payout_request_id: UUID,
        changes: PayoutRequestUpdate,
    ) -> Any: ...

    async def find_by_bot(
        self,
        bot_player_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]: ...

    async def find_pending_by_bot(
        self,
        bot_player_id: UUID,
    ) -> Any | None: ...

    async def find_pending_past_hold(
        self,
        as_of: datetime,
    ) -> list[Any]: ...


class DailyEarningsRepositoryProtocol(Protocol):
    """Repository interface for daily earnings summary."""

    async def upsert(self, data: DailyEarningsUpsert) -> Any: ...

    async def find_range(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[Any]: ...


# ---------------------------------------------------------------------------
# Minimal dependency protocols (avoid circular imports)
# ---------------------------------------------------------------------------


class PlayerServiceProtocol(Protocol):
    """Subset of player service used by bot_earnings module."""

    async def get_player(self, player_id: PlayerId) -> Any: ...


class AdServiceProtocol(Protocol):
    """Subset of ads service used by bot_earnings module."""

    async def get_bot_ad_attributions(
        self,
        bot_player_id: PlayerId,
        start_date: date,
        end_date: date,
    ) -> Any: ...
