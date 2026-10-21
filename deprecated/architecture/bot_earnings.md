# Module Architecture Report: bot_earnings

**Module:** bot_earnings
**Build Wave:** 8 (Terminal Node)
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The bot_earnings module tracks and manages revenue sharing for bot players in ChromaCrush. It maintains a running earnings ledger with atomic balance updates, syncs ad attribution data from the ads module on a periodic pull basis, manages the full payout request lifecycle (owner-initiated, admin-processed with hold periods), and provides daily earnings breakdowns for reporting. The module uses deduplication via deterministic UUID v5-based impression IDs and aggregates attribution entries at the daily level rather than per-impression. All 13 public service methods are **asynchronous** (`async def`) because they involve database operations and cross-module coordination. The module is a terminal node in the dependency graph with no downstream dependents.

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get_earnings_balance` | `(bot_player_id) -> EarningsBalance` | Get current earnings balance |
| `get_earnings_summary` | `(bot_player_id, start_date?, end_date?) -> EarningsSummary` | Earnings summary for date range |
| `get_attribution_entries` | `(bot_player_id, start_date?, end_date?, limit?, offset?) -> PaginatedResult[AttributionEntry]` | Paginated attribution entries |
| `get_daily_earnings` | `(bot_player_id, start_date?, end_date?) -> list[DailyEarnings]` | Daily earnings breakdown |
| `sync_attributions` | `(bot_player_id) -> AttributionSyncResult` | Pull new attributions from ads module |
| `sync_all_attributions` | `() -> BulkSyncResult` | Bulk sync for all bots |
| `request_payout` | `(bot_player_id, owner_player_id) -> PayoutRequest` | Initiate payout request |
| `get_payout_requests` | `(bot_player_id, status?, limit?, offset?) -> PaginatedResult[PayoutRequest]` | List payout requests |
| `get_payout_request` | `(payout_request_id) -> PayoutRequest` | Get single payout request |
| `cancel_payout_request` | `(payout_request_id, player_id) -> PayoutRequest` | Cancel pending payout |
| `process_payout` | `(payout_request_id, processor_id, external_ref?) -> PayoutRequest` | Admin: mark payout as processed |
| `reject_payout` | `(payout_request_id, processor_id, reason) -> PayoutRequest` | Admin: reject payout request |
| `get_bot_owner` | `(bot_player_id) -> PlayerId` | Get bot's owner player ID |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Bot earnings configuration (thresholds, share %, batch size) |
| `logger` | `LoggerProtocol` | Structured diagnostic logging |
| `errors` | `ErrorServiceProtocol` | Create typed errors |
| `data_ctx` | `DataContextProtocol` | Session management |
| `player_service` | `PlayerServiceProtocol` | Player existence and bot status verification |
| `ads_service` | `AdServiceProtocol` | Pull bot ad attribution data for sync |
| `earnings_ledger_repository` | `EarningsLedgerRepositoryProtocol` | Running balance tracking |
| `attribution_entry_repository` | `AttributionEntryRepositoryProtocol` | Attribution entry persistence |
| `payout_request_repository` | `PayoutRequestRepositoryProtocol` | Payout request lifecycle |
| `daily_earnings_repository` | `DailyEarningsRepositoryProtocol` | Daily earnings summaries |

---

## 4. Data Owned

| Table | Description |
|-------|-------------|
| `bot_earnings_ledger` | Running balance per bot (bot_player_id UUID as PK, atomic updates) |
| `bot_attribution_entries` | Attribution records (daily aggregates with deduplication) |
| `bot_payout_requests` | Payout request lifecycle (pending, processed, rejected, cancelled) |
| `bot_earnings_daily` | Daily earnings summary (composite PK: bot_player_id + earnings_date) |

Read-only access to `ad_impressions` (via ads service) and `players` (via player service).

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `bot_earnings.minimum_payout_cents` | int | 1000 | Minimum balance for payout ($10) |
| `bot_earnings.attribution_share_percent` | float | 30.0 | Bot share of impression revenue |
| `bot_earnings.sync_lookback_days` | int | 7 | Days to look back during sync |
| `bot_earnings.max_date_range_days` | int | 90 | Max days for date range queries |
| `bot_earnings.payout_hold_hours` | int | 72 | Hours to hold new payouts for review |
| `bot_earnings.sync_batch_size` | int | 100 | Bots per batch in bulk sync |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_INVALID_INPUT` | 400 | Invalid date range, non-bot player |
| `VALIDATION_INSUFFICIENT_BALANCE` | 400 | Payout exceeds available balance |
| `VALIDATION_BELOW_PAYOUT_THRESHOLD` | 400 | Balance below minimum payout |
| `VALIDATION_DATE_RANGE_TOO_LARGE` | 400 | Query date range exceeds maximum |
| `NOT_FOUND_PLAYER` | 404 | Player does not exist (via player_service) |
| `NOT_FOUND_PAYOUT_REQUEST` | 404 | Payout request not found |
| `FORBIDDEN_NOT_BOT` | 403 | Non-bot player attempting bot operation |
| `FORBIDDEN_NOT_BOT_OWNER` | 403 | Non-owner requesting bot payout |
| `CONFLICT_PENDING_PAYOUT_EXISTS` | 409 | Bot already has pending payout |
| `CONFLICT_PAYOUT_NOT_PENDING` | 409 | Process/cancel non-pending payout |
| `CONFLICT_SYNC_IN_PROGRESS` | 409 | Concurrent sync attempt |
| `INTERNAL_ADS_SERVICE_ERROR` | 500 | Ads module call failed during sync |

---

## 7. Cross-Module Interactions

**Called by:**
- `api` -- exposes bot earnings endpoints

**Calls:**
- `ads` -- pulls bot ad attribution data via `get_bot_ad_attributions`
- `player` -- player existence and bot status verification

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `EarningsPeriod` | `src/modules/bot_earnings/types.py` | Enum for date range presets |
| `PayoutStatus` | `src/modules/bot_earnings/types.py` | Enum: PENDING, PROCESSED, REJECTED, CANCELLED |
| `EarningsBalance` | `src/modules/bot_earnings/types.py` | Current balance with lifetime totals |
| `EarningsSummary` | `src/modules/bot_earnings/types.py` | Summary with period totals and breakdowns |
| `AttributionEntry` | `src/modules/bot_earnings/types.py` | Individual attribution record |
| `DailyEarnings` | `src/modules/bot_earnings/types.py` | Daily earnings aggregate |
| `AttributionSyncResult` | `src/modules/bot_earnings/types.py` | Result of attribution sync operation |
| `PayoutRequest` | `src/modules/bot_earnings/types.py` | Payout request with lifecycle status |
