"""Bot earnings service implementation.

Fully async service managing bot earnings tracking, attribution syncing,
payout requests, and earnings reporting. All dependencies arrive via
``__init__`` injection.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from src.core.types.game import MatchId, PlayerId
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

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.bot_earnings.protocols import (
        AdServiceProtocol,
        AttributionEntryRepositoryProtocol,
        DailyEarningsRepositoryProtocol,
        EarningsLedgerRepositoryProtocol,
        PayoutRequestRepositoryProtocol,
        PlayerServiceProtocol,
    )


_MAX_PAGE_LIMIT = 100
_LIFETIME_START_DATE = date(2020, 1, 1)  # Fallback start for LIFETIME period queries


class BotEarningsService:
    """Concrete implementation of ``BotEarningsServiceProtocol``."""

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        ads_service: AdServiceProtocol,
        earnings_ledger_repository: EarningsLedgerRepositoryProtocol,
        attribution_entry_repository: AttributionEntryRepositoryProtocol,
        payout_request_repository: PayoutRequestRepositoryProtocol,
        daily_earnings_repository: DailyEarningsRepositoryProtocol,
        data_ctx: DataContextProtocol | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._player_service = player_service
        self._ads_service = ads_service
        self._ledger_repo = earnings_ledger_repository
        self._attribution_repo = attribution_entry_repository
        self._payout_repo = payout_request_repository
        self._daily_repo = daily_earnings_repository
        self._data_ctx = data_ctx

        # Read config values
        self._min_payout: int = config.get(
            "bot_earnings.minimum_payout_cents",
            1000,
        )
        self._attribution_share: float = config.get(
            "bot_earnings.attribution_share_percent",
            30.0,
        )
        self._sync_lookback: int = config.get(
            "bot_earnings.sync_lookback_days",
            7,
        )
        self._max_date_range: int = config.get(
            "bot_earnings.max_date_range_days",
            90,
        )
        self._hold_hours: int = config.get(
            "bot_earnings.payout_hold_hours",
            72,
        )
        self._sync_batch_size: int = config.get(
            "bot_earnings.sync_batch_size",
            100,
        )

    # === Earnings queries ===

    async def get_earnings_balance(
        self,
        bot_player_id: PlayerId,
    ) -> EarningsBalance:
        """Get the current earnings balance for a bot."""
        await self._validate_bot(bot_player_id)

        ledger = await self._ledger_repo.find_by_bot_id(bot_player_id)
        if ledger is None:
            # EC-1: Bot with no activity returns zero balance
            self._logger.debug(
                "Balance queried for bot with no ledger",
                bot_player_id=str(bot_player_id),
                available_cents=0,
            )
            return EarningsBalance(
                bot_player_id=bot_player_id,
                total_earned_cents=0,
                total_paid_out_cents=0,
                pending_payout_cents=0,
                available_balance_cents=0,
                last_attribution_at=None,
                last_sync_at=None,
            )

        available = (
            ledger.total_earned_cents
            - ledger.total_paid_out_cents
            - ledger.pending_payout_cents
        )

        self._logger.debug(
            "Balance queried",
            bot_player_id=str(bot_player_id),
            available_cents=available,
        )

        return EarningsBalance(
            bot_player_id=bot_player_id,
            total_earned_cents=ledger.total_earned_cents,
            total_paid_out_cents=ledger.total_paid_out_cents,
            pending_payout_cents=ledger.pending_payout_cents,
            available_balance_cents=available,
            last_attribution_at=ledger.last_attribution_at,
            last_sync_at=ledger.last_sync_at,
        )

    async def get_earnings_summary(
        self,
        bot_player_id: PlayerId,
        period: EarningsPeriod = EarningsPeriod.LIFETIME,
    ) -> EarningsSummary:
        """Get earnings summary for a bot over a time period."""
        await self._validate_bot(bot_player_id)

        today = date.today()
        period_start, period_end = self._compute_period_range(period, today)

        summary = await self._attribution_repo.get_period_summary(
            bot_player_id,
            period_start,
            period_end,
        )

        days_in_period = max(1, (period_end - period_start).days + 1)
        total_cents = getattr(summary, "total_cents", 0) or 0
        avg_daily = total_cents // days_in_period

        # Get daily breakdown to find top earning day
        daily_records = await self._attribution_repo.get_daily_summary(
            bot_player_id,
            period_start,
            period_end,
        )

        top_day: date | None = None
        top_day_cents = 0
        for record in daily_records:
            rec_cents = getattr(record, "total_cents", 0) or 0
            if rec_cents > top_day_cents:
                top_day_cents = rec_cents
                top_day = record.date

        return EarningsSummary(
            bot_player_id=bot_player_id,
            period=period,
            period_start=period_start,
            period_end=period_end,
            total_attributions=getattr(summary, "total_attributions", 0) or 0,
            total_matches=getattr(summary, "total_matches", 0) or 0,
            total_impressions=getattr(summary, "total_impressions", 0) or 0,
            earnings_cents=total_cents,
            average_daily_cents=avg_daily,
            top_earning_day=top_day,
            top_earning_day_cents=top_day_cents,
        )

    async def get_attribution_entries(
        self,
        bot_player_id: PlayerId,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[AttributionEntry]:
        """Get individual attribution entries (audit trail) for a bot."""
        await self._validate_bot(bot_player_id)
        self._validate_pagination(limit, offset)

        if start_date is not None and end_date is not None:
            self._validate_date_range(start_date, end_date)

        records, total = await self._attribution_repo.find_by_bot(
            bot_player_id,
            start_date,
            end_date,
            limit,
            offset,
        )

        items = [self._build_attribution_entry(r) for r in records]
        return PaginatedResult(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_daily_earnings(
        self,
        bot_player_id: PlayerId,
        start_date: date,
        end_date: date,
    ) -> list[DailyEarnings]:
        """Get daily breakdown of earnings for a bot."""
        await self._validate_bot(bot_player_id)
        self._validate_date_range(start_date, end_date)

        records = await self._daily_repo.find_range(
            bot_player_id,
            start_date,
            end_date,
        )

        return [
            DailyEarnings(
                date=r.earnings_date,
                attributions=r.attributions_count,
                matches=r.matches_count,
                impressions=r.impressions_count,
                earnings_cents=r.earnings_cents,
            )
            for r in records
        ]

    # === Sync operations ===

    async def sync_attributions(
        self,
        bot_player_id: PlayerId,
    ) -> AttributionSyncResult:
        """Sync attributed revenue from ads module into earnings ledger."""
        sync_start = datetime.now(timezone.utc)
        errors: list[str] = []

        # 1. Validate bot
        player = await self._player_service.get_player(bot_player_id)
        if not getattr(player, "is_bot", False):
            raise self._errors.validation(
                "Player is not a bot",
                code="VALIDATION_PLAYER_NOT_BOT",
                player_id=str(bot_player_id),
            )

        # 2. Get or create ledger entry
        ledger = await self._ledger_repo.find_by_bot_id(bot_player_id)
        if ledger is None:
            owner_id = self._extract_owner_id(player)
            ledger = await self._ledger_repo.create(
                EarningsLedgerCreate(
                    bot_player_id=bot_player_id,
                    owner_player_id=owner_id,
                )
            )

        # 3. Determine sync window
        today = date.today()
        sync_start_date = today - timedelta(days=self._sync_lookback)
        sync_end_date = today

        if ledger.last_sync_at is not None:
            last_sync_date = ledger.last_sync_at.date() - timedelta(days=1)
            if last_sync_date > sync_start_date:
                sync_start_date = last_sync_date

        # 4. Fetch attributions from ads module
        try:
            attribution_report = await self._ads_service.get_bot_ad_attributions(
                bot_player_id=bot_player_id,
                start_date=sync_start_date,
                end_date=sync_end_date,
            )
        except Exception as e:
            self._logger.error(
                "Ads service error during sync",
                bot_player_id=str(bot_player_id),
                error=str(e),
            )
            raise self._errors.internal(
                "Ads service error",
                code="INTERNAL_ADS_SERVICE_ERROR",
                operation="get_bot_ad_attributions",
                error=str(e),
            )

        # 5. Process daily breakdown from ads module
        new_entries: list[AttributionEntryCreate] = []
        new_total_cents = 0
        daily_updates: dict[date, DailyEarningsUpsert] = {}

        for daily in getattr(attribution_report, "daily_breakdown", []):
            daily_date = daily.date
            attributed_cents = getattr(daily, "attributed_cents", 0) or 0
            impressions = getattr(daily, "impressions", 0) or 0
            matches = getattr(daily, "matches", 0) or 0
            est_revenue = getattr(daily, "estimated_revenue_cents", 0) or 0

            if impressions > 0 and attributed_cents > 0:
                # Create an aggregated attribution entry per day
                entry = AttributionEntryCreate(
                    bot_player_id=bot_player_id,
                    match_id=PlayerId(bot_player_id),  # Aggregate marker
                    ad_impression_id=self._generate_impression_id(
                        bot_player_id,
                        daily_date,
                    ),
                    opponent_player_id=bot_player_id,  # Aggregate marker
                    estimated_impression_revenue_cents=est_revenue,
                    attribution_share_percent=self._attribution_share,
                    attributed_cents=attributed_cents,
                    attribution_date=daily_date,
                )

                # Check for duplicate
                existing = await self._attribution_repo.find_by_impression_id(
                    entry.ad_impression_id,
                )
                if existing is None:
                    new_entries.append(entry)
                    new_total_cents += attributed_cents

                    daily_updates[daily_date] = DailyEarningsUpsert(
                        bot_player_id=bot_player_id,
                        earnings_date=daily_date,
                        attributions_count=impressions,
                        matches_count=matches,
                        impressions_count=impressions,
                        earnings_cents=attributed_cents,
                    )

        # 6. Persist new entries
        if new_entries:
            await self._attribution_repo.create_batch(new_entries)
            await self._ledger_repo.increment_earned(bot_player_id, new_total_cents)

            # Update daily summaries
            for upsert_data in daily_updates.values():
                await self._daily_repo.upsert(upsert_data)

        # 7. Update ledger sync timestamp
        now = datetime.now(timezone.utc)
        update_fields = EarningsLedgerUpdate(last_sync_at=now)
        if new_entries:
            update_fields.last_attribution_at = now
        await self._ledger_repo.update(bot_player_id, update_fields)

        sync_end = datetime.now(timezone.utc)

        self._logger.info(
            "Attribution sync complete",
            bot_player_id=str(bot_player_id),
            new_count=len(new_entries),
            new_cents=new_total_cents,
        )

        return AttributionSyncResult(
            bot_player_id=bot_player_id,
            new_attributions=len(new_entries),
            new_earnings_cents=new_total_cents,
            sync_start=sync_start,
            sync_end=sync_end,
            errors=errors,
        )

    async def sync_all_attributions(self) -> BulkSyncResult:
        """Background job: sync attributions for all bots with recent activity."""
        sync_start = datetime.now(timezone.utc)
        since = sync_start - timedelta(days=self._sync_lookback)
        errors: list[tuple[PlayerId, str]] = []
        total_new = 0
        total_cents = 0
        bots_synced = 0

        ledgers = await self._ledger_repo.find_bots_needing_sync(
            since,
            limit=self._sync_batch_size,
        )

        for ledger in ledgers:
            bot_id = PlayerId(ledger.bot_player_id)
            try:
                result = await self.sync_attributions(bot_id)
                total_new += result.new_attributions
                total_cents += result.new_earnings_cents
                bots_synced += 1
            except Exception as e:
                self._logger.error(
                    "Sync error for bot",
                    bot_player_id=str(bot_id),
                    error=str(e),
                )
                errors.append((bot_id, str(e)))

        sync_end = datetime.now(timezone.utc)

        self._logger.info(
            "Bulk sync complete",
            bots_synced=bots_synced,
            total_new_cents=total_cents,
        )

        return BulkSyncResult(
            bots_synced=bots_synced,
            total_new_attributions=total_new,
            total_new_earnings_cents=total_cents,
            errors=errors,
            sync_start=sync_start,
            sync_end=sync_end,
        )

    # === Payout operations ===

    async def request_payout(
        self,
        bot_player_id: PlayerId,
        requesting_owner_id: PlayerId,
    ) -> PayoutRequest:
        """Submit a payout request for a bot's earnings."""
        # 1. Validate bot
        player = await self._player_service.get_player(bot_player_id)
        if not getattr(player, "is_bot", False):
            raise self._errors.validation(
                "Player is not a bot",
                code="VALIDATION_PLAYER_NOT_BOT",
                player_id=str(bot_player_id),
            )

        # Get ledger
        ledger = await self._ledger_repo.find_by_bot_id(bot_player_id)
        if ledger is None:
            raise self._errors.validation(
                "Bot has no earnings",
                code="VALIDATION_INSUFFICIENT_BALANCE",
                available_cents=0,
                requested_cents=0,
            )

        # Verify ownership
        if ledger.owner_player_id != requesting_owner_id:
            raise self._errors.forbidden(
                "Not authorized to request payout for this bot",
                code="FORBIDDEN_NOT_BOT_OWNER",
                bot_player_id=str(bot_player_id),
                requester_id=str(requesting_owner_id),
            )

        # 2. Check no pending payout
        existing_pending = await self._payout_repo.find_pending_by_bot(
            bot_player_id,
        )
        if existing_pending is not None:
            raise self._errors.conflict(
                "Bot already has a pending payout request",
                code="CONFLICT_PENDING_PAYOUT_EXISTS",
                bot_player_id=str(bot_player_id),
                existing_request_id=str(existing_pending.id),
            )

        # 3. Calculate available balance
        available = (
            ledger.total_earned_cents
            - ledger.total_paid_out_cents
            - ledger.pending_payout_cents
        )

        if available < self._min_payout:
            raise self._errors.validation(
                "Balance below minimum payout threshold",
                code="VALIDATION_BELOW_PAYOUT_THRESHOLD",
                available_cents=available,
                minimum_cents=self._min_payout,
            )

        # 4. Create payout request
        hold_until = datetime.now(timezone.utc) + timedelta(hours=self._hold_hours)

        payout = await self._payout_repo.create(
            PayoutRequestCreate(
                bot_player_id=bot_player_id,
                owner_player_id=requesting_owner_id,
                amount_cents=available,
                status=PayoutStatus.PENDING.value,
                hold_until=hold_until,
            )
        )

        # 5. Update ledger
        await self._ledger_repo.increment_pending(bot_player_id, available)

        self._logger.info(
            "Payout requested",
            bot_player_id=str(bot_player_id),
            owner_id=str(requesting_owner_id),
            amount_cents=available,
        )

        return self._build_payout_request(payout)

    async def get_payout_requests(
        self,
        bot_player_id: PlayerId,
        status: PayoutStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[PayoutRequest]:
        """Get payout request history for a bot."""
        await self._validate_bot(bot_player_id)
        self._validate_pagination(limit, offset)

        status_str = status.value if status else None
        records, total = await self._payout_repo.find_by_bot(
            bot_player_id,
            status_str,
            limit,
            offset,
        )

        items = [self._build_payout_request(r) for r in records]
        return PaginatedResult(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_payout_request(
        self,
        payout_request_id: PayoutRequestId,
    ) -> PayoutRequest:
        """Get a specific payout request by ID."""
        record = await self._payout_repo.find_by_id(payout_request_id)
        if record is None:
            raise self._errors.not_found(
                "Payout request not found",
                code="NOT_FOUND_PAYOUT_REQUEST",
                payout_request_id=str(payout_request_id),
            )
        return self._build_payout_request(record)

    async def cancel_payout_request(
        self,
        payout_request_id: PayoutRequestId,
        requesting_owner_id: PlayerId,
    ) -> PayoutRequest:
        """Cancel a pending payout request."""
        record = await self._payout_repo.find_by_id(payout_request_id)
        if record is None:
            raise self._errors.not_found(
                "Payout request not found",
                code="NOT_FOUND_PAYOUT_REQUEST",
                payout_request_id=str(payout_request_id),
            )

        if record.status != PayoutStatus.PENDING.value:
            raise self._errors.conflict(
                "Payout request is not pending",
                code="CONFLICT_PAYOUT_NOT_PENDING",
                payout_request_id=str(payout_request_id),
                current_status=record.status,
            )

        # Verify ownership
        if record.owner_player_id != requesting_owner_id:
            raise self._errors.forbidden(
                "Not authorized to cancel this payout request",
                code="FORBIDDEN_NOT_BOT_OWNER",
                bot_player_id=str(record.bot_player_id),
                requester_id=str(requesting_owner_id),
            )

        # Update request status
        updated = await self._payout_repo.update(
            payout_request_id,
            PayoutRequestUpdate(status=PayoutStatus.CANCELLED.value),
        )

        # Return funds to available balance
        await self._ledger_repo.cancel_pending(
            record.bot_player_id,
            record.amount_cents,
        )

        self._logger.info(
            "Payout cancelled",
            payout_request_id=str(payout_request_id),
            owner_id=str(requesting_owner_id),
        )

        return self._build_payout_request(updated)

    async def process_payout(
        self,
        payout_request_id: PayoutRequestId,
        processor_id: PlayerId,
        external_reference: str | None = None,
    ) -> PayoutRequest:
        """Admin method: marks a payout request as processed."""
        await self._validate_admin(processor_id, "process_payout")

        record = await self._payout_repo.find_by_id(payout_request_id)
        if record is None:
            raise self._errors.not_found(
                "Payout request not found",
                code="NOT_FOUND_PAYOUT_REQUEST",
                payout_request_id=str(payout_request_id),
            )

        if record.status != PayoutStatus.PENDING.value:
            raise self._errors.conflict(
                "Payout request is not pending",
                code="CONFLICT_PAYOUT_NOT_PENDING",
                payout_request_id=str(payout_request_id),
                current_status=record.status,
            )

        if external_reference and len(external_reference) > 255:
            raise self._errors.validation(
                "External reference too long",
                code="VALIDATION_INVALID_INPUT",
                field="external_reference",
                max_length=255,
            )

        now = datetime.now(timezone.utc)
        updated = await self._payout_repo.update(
            payout_request_id,
            PayoutRequestUpdate(
                status=PayoutStatus.COMPLETED.value,
                processed_at=now,
                processed_by=processor_id,
                external_reference=external_reference,
            ),
        )

        # Move from pending to paid out
        await self._ledger_repo.complete_payout(
            record.bot_player_id,
            record.amount_cents,
        )

        self._logger.info(
            "Payout processed",
            payout_request_id=str(payout_request_id),
            processor_id=str(processor_id),
            amount_cents=record.amount_cents,
        )

        return self._build_payout_request(updated)

    async def reject_payout(
        self,
        payout_request_id: PayoutRequestId,
        processor_id: PlayerId,
        reason: str,
    ) -> PayoutRequest:
        """Admin method: rejects a payout request."""
        await self._validate_admin(processor_id, "reject_payout")

        if not reason or len(reason) > 500:
            raise self._errors.validation(
                "Rejection reason is required and must not exceed 500 characters",
                code="VALIDATION_INVALID_INPUT",
                field="reason",
                max_length=500,
            )

        record = await self._payout_repo.find_by_id(payout_request_id)
        if record is None:
            raise self._errors.not_found(
                "Payout request not found",
                code="NOT_FOUND_PAYOUT_REQUEST",
                payout_request_id=str(payout_request_id),
            )

        if record.status != PayoutStatus.PENDING.value:
            raise self._errors.conflict(
                "Payout request is not pending",
                code="CONFLICT_PAYOUT_NOT_PENDING",
                payout_request_id=str(payout_request_id),
                current_status=record.status,
            )

        now = datetime.now(timezone.utc)
        updated = await self._payout_repo.update(
            payout_request_id,
            PayoutRequestUpdate(
                status=PayoutStatus.REJECTED.value,
                processed_at=now,
                processed_by=processor_id,
                rejection_reason=reason,
            ),
        )

        # Return funds to available balance
        await self._ledger_repo.cancel_pending(
            record.bot_player_id,
            record.amount_cents,
        )

        self._logger.warn(
            "Payout rejected",
            payout_request_id=str(payout_request_id),
            processor_id=str(processor_id),
            reason=reason,
        )

        return self._build_payout_request(updated)

    async def get_pending_payouts(
        self,
        past_hold_only: bool = False,
    ) -> list[PayoutRequest]:
        """List pending payout requests, optionally filtered to those past hold.

        Wraps the payout repository call so CLI commands do not access
        repositories directly.
        """
        if past_hold_only:
            now = datetime.now(timezone.utc)
            records = await self._payout_repo.find_pending_past_hold(now)
        else:
            # Use a far-future date to get ALL pending (regardless of hold)
            records = await self._payout_repo.find_pending_past_hold(
                datetime(2099, 1, 1, tzinfo=timezone.utc),
            )

        self._logger.debug(
            "Pending payouts listed",
            count=len(records),
            past_hold_only=past_hold_only,
        )
        return [self._build_payout_request(r) for r in records]

    async def get_bot_owner(
        self,
        bot_player_id: PlayerId,
    ) -> PlayerId:
        """Get the owner of a bot for authorization checks."""
        player = await self._player_service.get_player(bot_player_id)
        if not getattr(player, "is_bot", False):
            raise self._errors.validation(
                "Player is not a bot",
                code="VALIDATION_PLAYER_NOT_BOT",
                player_id=str(bot_player_id),
            )

        ledger = await self._ledger_repo.find_by_bot_id(bot_player_id)
        if ledger is not None:
            return PlayerId(ledger.owner_player_id)

        # Fall back to extracting owner from player object
        return self._extract_owner_id(player)

    # === Private helpers ===

    async def _validate_admin(self, processor_id: PlayerId, operation: str) -> None:
        """Validate that the processor has admin privileges.

        Uses ``getattr(player, 'is_admin', False)`` on the player object.
        If the player module does not expose an ``is_admin`` attribute yet,
        this check is a no-op (all processors are allowed).  A future
        iteration should add ``is_admin`` to the player model and the
        ``PlayerServiceProtocol`` to enforce this properly.
        """
        player = await self._player_service.get_player(processor_id)
        is_admin = getattr(player, "is_admin", None)
        # Only enforce when the player model actually exposes the attribute
        if is_admin is not None and not is_admin:
            raise self._errors.forbidden(
                "Admin privileges required for this operation",
                code="FORBIDDEN_NOT_ADMIN",
                operation=operation,
                requester_id=str(processor_id),
            )

    async def _validate_bot(self, bot_player_id: PlayerId) -> Any:
        """Validate that the player exists and is a bot. Returns player."""
        player = await self._player_service.get_player(bot_player_id)
        if not getattr(player, "is_bot", False):
            raise self._errors.validation(
                "Player is not a bot",
                code="VALIDATION_PLAYER_NOT_BOT",
                player_id=str(bot_player_id),
            )
        return player

    def _validate_pagination(self, limit: int, offset: int) -> None:
        """Validate pagination parameters."""
        if limit < 1 or limit > _MAX_PAGE_LIMIT:
            raise self._errors.validation(
                f"Limit must be between 1 and {_MAX_PAGE_LIMIT}",
                code="VALIDATION_INVALID_INPUT",
                field="limit",
                value=limit,
            )
        if offset < 0:
            raise self._errors.validation(
                "Offset must be non-negative",
                code="VALIDATION_INVALID_INPUT",
                field="offset",
                value=offset,
            )

    def _validate_date_range(self, start_date: date, end_date: date) -> None:
        """Validate date range parameters."""
        if end_date < start_date:
            raise self._errors.validation(
                "End date must be on or after start date",
                code="VALIDATION_INVALID_INPUT",
                start_date=str(start_date),
                end_date=str(end_date),
                reason="end_date before start_date",
            )

        days = (end_date - start_date).days
        if days > self._max_date_range:
            raise self._errors.validation(
                f"Date range exceeds maximum of {self._max_date_range} days",
                code="VALIDATION_DATE_RANGE_TOO_LARGE",
                days_requested=days,
                max_days=self._max_date_range,
            )

    def _compute_period_range(
        self,
        period: EarningsPeriod,
        reference: date,
    ) -> tuple[date, date]:
        """Compute start/end dates for a given period relative to reference."""
        end = reference
        if period == EarningsPeriod.DAY:
            start = end
        elif period == EarningsPeriod.WEEK:
            start = end - timedelta(days=6)
        elif period == EarningsPeriod.MONTH:
            start = end - timedelta(days=29)
        elif period == EarningsPeriod.QUARTER:
            start = end - timedelta(days=89)
        elif period == EarningsPeriod.YEAR:
            start = end - timedelta(days=364)
        else:  # LIFETIME
            start = _LIFETIME_START_DATE
        return start, end

    @staticmethod
    def _extract_owner_id(player: Any) -> PlayerId:
        """Extract the owner_player_id from a player object."""
        owner = getattr(player, "owner_player_id", None)
        if owner is not None:
            return PlayerId(owner)
        # Fallback: bot is its own owner record holder
        return PlayerId(player.id)

    @staticmethod
    def _generate_impression_id(
        bot_player_id: PlayerId,
        daily_date: date,
    ) -> PlayerId:
        """Generate a deterministic UUID for deduplication of daily aggregates.

        Uses UUID v5 (SHA-1 based) with bot_player_id and date as namespace.
        """
        import uuid as _uuid

        namespace = _uuid.UUID(str(bot_player_id))
        name = f"daily-{daily_date.isoformat()}"
        return PlayerId(_uuid.uuid5(namespace, name))

    @staticmethod
    def _build_payout_request(record: Any) -> PayoutRequest:
        """Convert a repository record to a PayoutRequest domain object."""
        return PayoutRequest(
            id=PayoutRequestId(record.id),
            bot_player_id=PlayerId(record.bot_player_id),
            owner_player_id=PlayerId(record.owner_player_id),
            amount_cents=record.amount_cents,
            status=PayoutStatus(record.status),
            requested_at=record.requested_at,
            processed_at=getattr(record, "processed_at", None),
            processed_by=(
                PlayerId(record.processed_by)
                if getattr(record, "processed_by", None)
                else None
            ),
            external_reference=getattr(record, "external_reference", None),
            rejection_reason=getattr(record, "rejection_reason", None),
            notes=getattr(record, "notes", None),
        )

    @staticmethod
    def _build_attribution_entry(record: Any) -> AttributionEntry:
        """Convert a repository record to an AttributionEntry domain object."""
        return AttributionEntry(
            id=AttributionEntryId(record.id),
            bot_player_id=PlayerId(record.bot_player_id),
            match_id=MatchId(record.match_id),
            ad_impression_id=AdImpressionId(record.ad_impression_id),
            opponent_player_id=PlayerId(record.opponent_player_id),
            estimated_impression_revenue_cents=record.estimated_impression_revenue_cents,
            attribution_share_percent=float(record.attribution_share_percent),
            attributed_cents=record.attributed_cents,
            recorded_at=record.recorded_at,
            attribution_date=record.attribution_date,
        )
