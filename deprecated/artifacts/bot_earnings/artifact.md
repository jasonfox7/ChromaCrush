# Module Artifact: bot_earnings

## Header
- **Author:** Scout Agent (bot_earnings)
- **Date:** 2026-02-05
- **Version:** 1.0
- **Status:** Final
- **Dependencies:** `ads` (Wave 7), `player` (Wave 1)
- **Dependents:** `api` (exposes earnings endpoints)

---

## Purpose

The **bot_earnings** module tracks revenue share for bots based on ad impressions they help generate. When a human plays against a bot and subsequently views an ad, a portion of the estimated ad revenue is attributed to the bot. This module aggregates these attributions into an earnings ledger and allows bot owners to:

1. **View Cumulative Earnings** - Track total revenue share earned by their bots
2. **Query Attribution History** - Audit trail of individual attribution entries
3. **Request Payouts** - Submit payout requests when balance exceeds threshold
4. **Access Earnings Reports** - Daily, weekly, monthly breakdowns of earnings

**Initial Scope:** This implementation tracks earnings and payout requests only. Actual payout fulfillment is manual. Automated payout integration (e.g., Stripe Connect, PayPal) is deferred to a future phase.

This module is **asynchronous** - all public methods involving database operations are `async def`.

---

## Public Interface

### Class: `BotEarningsService`

The bot_earnings module exposes a single service class that receives dependencies via `__init__` injection.

```python
class BotEarningsService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        data_ctx: DataContextProtocol,
        player_service: PlayerServiceProtocol,
        ads_service: AdServiceProtocol,
        earnings_ledger_repository: EarningsLedgerRepositoryProtocol,
        attribution_entry_repository: AttributionEntryRepositoryProtocol,
        payout_request_repository: PayoutRequestRepositoryProtocol,
    ) -> None:
        ...
```

---

### Inputs

#### `get_earnings_balance(bot_player_id: PlayerId) -> EarningsBalance`

Gets the current earnings balance for a bot.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `bot_player_id` | `PlayerId` | The bot player | Must exist, must be bot |

---

#### `get_earnings_summary(bot_player_id: PlayerId, period: EarningsPeriod = EarningsPeriod.LIFETIME) -> EarningsSummary`

Gets earnings summary for a bot over a time period.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `bot_player_id` | `PlayerId` | The bot player | Must exist, must be bot |
| `period` | `EarningsPeriod` | Time period for summary | Valid enum |

---

#### `get_attribution_entries(bot_player_id: PlayerId, start_date: date | None = None, end_date: date | None = None, limit: int = 50, offset: int = 0) -> PaginatedResult[AttributionEntry]`

Gets individual attribution entries (audit trail) for a bot.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `bot_player_id` | `PlayerId` | The bot player | Must exist, must be bot |
| `start_date` | `date \| None` | Start of date range | Valid date if provided |
| `end_date` | `date \| None` | End of date range | Must be >= start_date if both provided |
| `limit` | `int` | Max results | 1-100 |
| `offset` | `int` | Pagination offset | >= 0 |

---

#### `get_daily_earnings(bot_player_id: PlayerId, start_date: date, end_date: date) -> list[DailyEarnings]`

Gets daily breakdown of earnings for a bot.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `bot_player_id` | `PlayerId` | The bot player | Must exist, must be bot |
| `start_date` | `date` | Start of date range | Valid date |
| `end_date` | `date` | End of date range | Must be >= start_date, max 90 days range |

---

#### `sync_attributions(bot_player_id: PlayerId) -> AttributionSyncResult`

Syncs attributed revenue from ads module into the earnings ledger.

This method pulls new attributions from `ads.get_bot_ad_attributions()` that haven't been recorded yet, creates attribution entries, and updates the earnings balance.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `bot_player_id` | `PlayerId` | The bot player | Must exist, must be bot |

---

#### `sync_all_attributions() -> BulkSyncResult`

Background job method: syncs attributions for all bots with recent activity.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| (none) | - | - | - |

---

#### `request_payout(bot_player_id: PlayerId, requesting_owner_id: PlayerId) -> PayoutRequest`

Submits a payout request for a bot's earnings.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `bot_player_id` | `PlayerId` | The bot whose earnings to pay out | Must exist, must be bot |
| `requesting_owner_id` | `PlayerId` | The owner requesting payout | Must be bot's owner |

---

#### `get_payout_requests(bot_player_id: PlayerId, status: PayoutStatus | None = None, limit: int = 50, offset: int = 0) -> PaginatedResult[PayoutRequest]`

Gets payout request history for a bot.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `bot_player_id` | `PlayerId` | The bot player | Must exist, must be bot |
| `status` | `PayoutStatus \| None` | Filter by status | Valid enum if provided |
| `limit` | `int` | Max results | 1-100 |
| `offset` | `int` | Pagination offset | >= 0 |

---

#### `get_payout_request(payout_request_id: PayoutRequestId) -> PayoutRequest`

Gets a specific payout request by ID.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `payout_request_id` | `PayoutRequestId` | The payout request | Must exist |

---

#### `cancel_payout_request(payout_request_id: PayoutRequestId, requesting_owner_id: PlayerId) -> PayoutRequest`

Cancels a pending payout request.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `payout_request_id` | `PayoutRequestId` | The request to cancel | Must exist, must be pending |
| `requesting_owner_id` | `PlayerId` | The owner canceling | Must be bot's owner |

---

#### `process_payout(payout_request_id: PayoutRequestId, processor_id: PlayerId, external_reference: str | None = None) -> PayoutRequest`

Admin method: marks a payout request as processed (manual fulfillment).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `payout_request_id` | `PayoutRequestId` | The request to process | Must exist, must be pending |
| `processor_id` | `PlayerId` | Admin processing the payout | Must be admin |
| `external_reference` | `str \| None` | External payment reference | Max 255 chars |

---

#### `reject_payout(payout_request_id: PayoutRequestId, processor_id: PlayerId, reason: str) -> PayoutRequest`

Admin method: rejects a payout request.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `payout_request_id` | `PayoutRequestId` | The request to reject | Must exist, must be pending |
| `processor_id` | `PlayerId` | Admin rejecting | Must be admin |
| `reason` | `str` | Rejection reason | Max 500 chars, required |

---

#### `get_bot_owner(bot_player_id: PlayerId) -> PlayerId`

Gets the owner of a bot for authorization checks.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `bot_player_id` | `PlayerId` | The bot player | Must exist, must be bot |

---

### Outputs

#### `EarningsBalance`

```python
@dataclass
class EarningsBalance:
    """Current earnings balance for a bot."""
    bot_player_id: PlayerId
    total_earned_cents: int          # Lifetime total
    total_paid_out_cents: int        # Lifetime payouts completed
    pending_payout_cents: int        # In pending payout requests
    available_balance_cents: int     # Earned - paid out - pending
    last_attribution_at: datetime | None
    last_sync_at: datetime | None
```

---

#### `EarningsSummary`

```python
@dataclass
class EarningsSummary:
    """Earnings summary for a time period."""
    bot_player_id: PlayerId
    period: EarningsPeriod
    period_start: date
    period_end: date
    total_attributions: int          # Number of attribution entries
    total_matches: int               # Matches that generated attributions
    total_impressions: int           # Ad impressions attributed
    earnings_cents: int              # Total earnings in period
    average_daily_cents: int         # Average daily earnings
    top_earning_day: date | None     # Best day in period
    top_earning_day_cents: int       # Earnings on best day
```

---

#### `AttributionEntry`

```python
@dataclass
class AttributionEntry:
    """Individual attribution record (audit trail)."""
    id: AttributionEntryId
    bot_player_id: PlayerId
    match_id: MatchId
    ad_impression_id: AdImpressionId
    opponent_player_id: PlayerId     # Human who saw the ad
    estimated_impression_revenue_cents: int
    attribution_share_percent: float
    attributed_cents: int            # The bot's share
    recorded_at: datetime
    attribution_date: date           # Date the impression occurred
```

---

#### `DailyEarnings`

```python
@dataclass
class DailyEarnings:
    """Earnings breakdown for a single day."""
    date: date
    attributions: int
    matches: int
    impressions: int
    earnings_cents: int
```

---

#### `AttributionSyncResult`

```python
@dataclass
class AttributionSyncResult:
    """Result of syncing attributions from ads module."""
    bot_player_id: PlayerId
    new_attributions: int            # Number of new entries created
    new_earnings_cents: int          # Total new earnings synced
    sync_start: datetime
    sync_end: datetime
    errors: list[str]                # Any errors during sync
```

---

#### `BulkSyncResult`

```python
@dataclass
class BulkSyncResult:
    """Result of bulk sync for all bots."""
    bots_synced: int
    total_new_attributions: int
    total_new_earnings_cents: int
    errors: list[tuple[PlayerId, str]]  # (bot_id, error_message)
    sync_start: datetime
    sync_end: datetime
```

---

#### `PayoutRequest`

```python
@dataclass
class PayoutRequest:
    """A payout request from a bot owner."""
    id: PayoutRequestId
    bot_player_id: PlayerId
    owner_player_id: PlayerId        # Who requested the payout
    amount_cents: int                # Amount requested
    status: PayoutStatus             # pending, processing, completed, rejected, cancelled
    requested_at: datetime
    processed_at: datetime | None
    processed_by: PlayerId | None    # Admin who processed
    external_reference: str | None   # External payment reference (e.g., PayPal transaction ID)
    rejection_reason: str | None
    notes: str | None                # Admin notes
```

---

### Error Cases

| Condition | Error Code | Error Type | Context Fields |
|-----------|------------|------------|----------------|
| Player not found | `NOT_FOUND_PLAYER` | not_found | `player_id` |
| Player is not a bot | `VALIDATION_PLAYER_NOT_BOT` | validation | `player_id` |
| Payout request not found | `NOT_FOUND_PAYOUT_REQUEST` | not_found | `payout_request_id` |
| Insufficient balance for payout | `VALIDATION_INSUFFICIENT_BALANCE` | validation | `available_cents`, `requested_cents` |
| Balance below minimum threshold | `VALIDATION_BELOW_PAYOUT_THRESHOLD` | validation | `available_cents`, `minimum_cents` |
| Payout request not pending | `CONFLICT_PAYOUT_NOT_PENDING` | conflict | `payout_request_id`, `current_status` |
| Not bot owner | `FORBIDDEN_NOT_BOT_OWNER` | forbidden | `bot_player_id`, `requester_id` |
| Not admin | `FORBIDDEN_NOT_ADMIN` | forbidden | `operation`, `requester_id` |
| Pending payout exists | `CONFLICT_PENDING_PAYOUT_EXISTS` | conflict | `bot_player_id`, `existing_request_id` |
| Invalid date range | `VALIDATION_INVALID_INPUT` | validation | `start_date`, `end_date`, `reason` |
| Date range too large | `VALIDATION_DATE_RANGE_TOO_LARGE` | validation | `days_requested`, `max_days` |
| Sync already in progress | `CONFLICT_SYNC_IN_PROGRESS` | conflict | `bot_player_id`, `started_at` |
| Ads module error | `INTERNAL_ADS_SERVICE_ERROR` | internal | `operation`, `error` |

---

### Async Behavior

**This module is fully asynchronous.**

All public methods are `async def` because they involve:
- Database reads/writes via repositories
- Cross-module service calls to `player_service`, `ads_service`

**Async operations:**
- `get_earnings_balance` - DB read
- `get_earnings_summary` - DB read (aggregate)
- `get_attribution_entries` - DB read
- `get_daily_earnings` - DB read (aggregate)
- `sync_attributions` - DB read/write + ads service call
- `sync_all_attributions` - Batch DB read/write + ads service calls
- `request_payout` - DB write
- `get_payout_requests` - DB read
- `get_payout_request` - DB read
- `cancel_payout_request` - DB write
- `process_payout` - DB write
- `reject_payout` - DB write
- `get_bot_owner` - player service call

**Error propagation:** All errors are raised through the injected `ErrorServiceProtocol`. Ads service errors are caught and wrapped in `INTERNAL_ADS_SERVICE_ERROR`.

---

## Mandatory Service Usage

### Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `bot_earnings.minimum_payout_cents` | int | 1000 | Minimum balance to request payout ($10.00) |
| `bot_earnings.attribution_share_percent` | float | 30.0 | Bot's share of impression revenue (mirrors ads config) |
| `bot_earnings.sync_lookback_days` | int | 7 | Days to look back when syncing attributions |
| `bot_earnings.max_date_range_days` | int | 90 | Maximum days for date range queries |
| `bot_earnings.payout_hold_hours` | int | 72 | Hours to hold new payouts for fraud review |
| `bot_earnings.sync_batch_size` | int | 100 | Bots per batch in bulk sync |

---

### Logging Events

| Event | Severity | Trigger | Context |
|-------|----------|---------|---------|
| `bot_earnings.attribution_synced` | INFO | New attributions recorded | `bot_player_id`, `new_count`, `new_cents` |
| `bot_earnings.bulk_sync_complete` | INFO | Bulk sync finished | `bots_synced`, `total_new_cents` |
| `bot_earnings.payout_requested` | INFO | Payout request created | `bot_player_id`, `owner_id`, `amount_cents` |
| `bot_earnings.payout_processed` | INFO | Payout marked complete | `payout_request_id`, `processor_id`, `amount_cents` |
| `bot_earnings.payout_rejected` | WARN | Payout rejected | `payout_request_id`, `processor_id`, `reason` |
| `bot_earnings.payout_cancelled` | INFO | Payout cancelled by owner | `payout_request_id`, `owner_id` |
| `bot_earnings.balance_queried` | DEBUG | Balance retrieved | `bot_player_id`, `available_cents` |
| `bot_earnings.sync_error` | ERROR | Error during attribution sync | `bot_player_id`, `error` |
| `bot_earnings.insufficient_balance` | DEBUG | Payout blocked - low balance | `bot_player_id`, `available_cents`, `requested_cents` |
| `bot_earnings.fraud_review_hold` | DEBUG | Payout in hold period | `payout_request_id`, `hold_until` |

---

### Error Types Used

From the error taxonomy (Interface Agent guidance):

- `NOT_FOUND_PLAYER` - Player ID doesn't exist
- `NOT_FOUND_PAYOUT_REQUEST` - Payout request ID doesn't exist
- `VALIDATION_INVALID_INPUT` - Invalid parameters (dates, limits)
- `VALIDATION_PLAYER_NOT_BOT` - Player is not a bot
- `VALIDATION_INSUFFICIENT_BALANCE` - Not enough available balance
- `VALIDATION_BELOW_PAYOUT_THRESHOLD` - Balance below minimum payout
- `VALIDATION_DATE_RANGE_TOO_LARGE` - Requested date range exceeds max
- `FORBIDDEN_NOT_BOT_OWNER` - Requester doesn't own the bot
- `FORBIDDEN_NOT_ADMIN` - Requester lacks admin privileges
- `CONFLICT_PAYOUT_NOT_PENDING` - Payout request not in pending status
- `CONFLICT_PENDING_PAYOUT_EXISTS` - Bot already has a pending payout
- `CONFLICT_SYNC_IN_PROGRESS` - Another sync is running for this bot
- `INTERNAL_ADS_SERVICE_ERROR` - Ads module returned error
- `INTERNAL_DATABASE_ERROR` - Database operation failed

All errors created through injected `ErrorServiceProtocol`, never bare raises.

---

## Data Access

### Owned Data

The bot_earnings module owns these database tables:

#### `bot_earnings_ledger` Table

```sql
CREATE TABLE bot_earnings_ledger (
    bot_player_id UUID PRIMARY KEY REFERENCES players(id),
    owner_player_id UUID NOT NULL REFERENCES players(id),
    total_earned_cents INTEGER NOT NULL DEFAULT 0,
    total_paid_out_cents INTEGER NOT NULL DEFAULT 0,
    pending_payout_cents INTEGER NOT NULL DEFAULT 0,
    last_attribution_at TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_earned_non_negative CHECK (total_earned_cents >= 0),
    CONSTRAINT chk_paid_non_negative CHECK (total_paid_out_cents >= 0),
    CONSTRAINT chk_pending_non_negative CHECK (pending_payout_cents >= 0),
    CONSTRAINT chk_paid_le_earned CHECK (total_paid_out_cents <= total_earned_cents)
);

CREATE INDEX idx_bot_earnings_owner ON bot_earnings_ledger(owner_player_id);
CREATE INDEX idx_bot_earnings_last_sync ON bot_earnings_ledger(last_sync_at);
```

#### `bot_attribution_entries` Table

```sql
CREATE TABLE bot_attribution_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_player_id UUID NOT NULL REFERENCES players(id),
    match_id UUID NOT NULL,  -- No FK to allow historical data retention
    ad_impression_id UUID NOT NULL UNIQUE,  -- Each impression attributed once
    opponent_player_id UUID NOT NULL REFERENCES players(id),
    estimated_impression_revenue_cents INTEGER NOT NULL,
    attribution_share_percent DECIMAL(5,2) NOT NULL,
    attributed_cents INTEGER NOT NULL,
    attribution_date DATE NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_revenue_non_negative CHECK (estimated_impression_revenue_cents >= 0),
    CONSTRAINT chk_share_valid CHECK (attribution_share_percent >= 0 AND attribution_share_percent <= 100),
    CONSTRAINT chk_attributed_non_negative CHECK (attributed_cents >= 0)
);

CREATE INDEX idx_attribution_bot ON bot_attribution_entries(bot_player_id, attribution_date DESC);
CREATE INDEX idx_attribution_date ON bot_attribution_entries(attribution_date);
CREATE INDEX idx_attribution_match ON bot_attribution_entries(match_id);
CREATE INDEX idx_attribution_recorded ON bot_attribution_entries(recorded_at);
```

#### `bot_payout_requests` Table

```sql
CREATE TABLE bot_payout_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_player_id UUID NOT NULL REFERENCES players(id),
    owner_player_id UUID NOT NULL REFERENCES players(id),
    amount_cents INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, rejected, cancelled
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    hold_until TIMESTAMPTZ,  -- Fraud review hold period
    processed_at TIMESTAMPTZ,
    processed_by UUID REFERENCES players(id),
    external_reference VARCHAR(255),
    rejection_reason TEXT,
    notes TEXT,

    CONSTRAINT chk_amount_positive CHECK (amount_cents > 0),
    CONSTRAINT chk_valid_status CHECK (status IN ('pending', 'processing', 'completed', 'rejected', 'cancelled'))
);

CREATE INDEX idx_payout_bot ON bot_payout_requests(bot_player_id, requested_at DESC);
CREATE INDEX idx_payout_status ON bot_payout_requests(status) WHERE status = 'pending';
CREATE INDEX idx_payout_owner ON bot_payout_requests(owner_player_id, requested_at DESC);
CREATE INDEX idx_payout_hold ON bot_payout_requests(hold_until) WHERE status = 'pending' AND hold_until IS NOT NULL;
```

#### `bot_earnings_daily` Table (Materialized Summary)

```sql
CREATE TABLE bot_earnings_daily (
    bot_player_id UUID NOT NULL REFERENCES players(id),
    earnings_date DATE NOT NULL,
    attributions_count INTEGER NOT NULL DEFAULT 0,
    matches_count INTEGER NOT NULL DEFAULT 0,
    impressions_count INTEGER NOT NULL DEFAULT 0,
    earnings_cents INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (bot_player_id, earnings_date)
);

CREATE INDEX idx_daily_date ON bot_earnings_daily(earnings_date);
```

---

### Repository Interfaces Required

```python
# src/data/protocols/bot_earnings_repositories.py
from typing import Protocol
from uuid import UUID
from datetime import date, datetime

from src.core.types.game import PlayerId, MatchId


class EarningsLedgerRepository(Protocol):
    """Repository interface for earnings ledger."""

    async def find_by_bot_id(self, bot_player_id: UUID) -> "EarningsLedgerRecord | None":
        """Find ledger entry for a bot."""
        ...

    async def create(self, data: "EarningsLedgerCreate") -> "EarningsLedgerRecord":
        """Create a new ledger entry."""
        ...

    async def update(self, bot_player_id: UUID, changes: "EarningsLedgerUpdate") -> "EarningsLedgerRecord":
        """Update ledger entry."""
        ...

    async def increment_earned(self, bot_player_id: UUID, cents: int) -> "EarningsLedgerRecord":
        """Atomically increment total_earned_cents."""
        ...

    async def increment_pending(self, bot_player_id: UUID, cents: int) -> "EarningsLedgerRecord":
        """Atomically increment pending_payout_cents."""
        ...

    async def complete_payout(self, bot_player_id: UUID, cents: int) -> "EarningsLedgerRecord":
        """Atomically move cents from pending to paid_out."""
        ...

    async def cancel_pending(self, bot_player_id: UUID, cents: int) -> "EarningsLedgerRecord":
        """Atomically decrement pending_payout_cents (for cancelled payouts)."""
        ...

    async def find_bots_needing_sync(
        self,
        since: datetime,
        limit: int = 100,
    ) -> list["EarningsLedgerRecord"]:
        """Find bots with recent activity that need sync."""
        ...


class AttributionEntryRepository(Protocol):
    """Repository interface for attribution entries."""

    async def create(self, data: "AttributionEntryCreate") -> "AttributionEntryRecord":
        """Create a new attribution entry."""
        ...

    async def create_batch(self, entries: list["AttributionEntryCreate"]) -> list["AttributionEntryRecord"]:
        """Create multiple attribution entries in one transaction."""
        ...

    async def find_by_impression_id(self, ad_impression_id: UUID) -> "AttributionEntryRecord | None":
        """Find entry by ad impression ID (to prevent duplicates)."""
        ...

    async def find_by_bot(
        self,
        bot_player_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list["AttributionEntryRecord"], int]:
        """Find entries for a bot with pagination."""
        ...

    async def get_daily_summary(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list["DailySummaryRecord"]:
        """Get aggregated daily earnings."""
        ...

    async def get_period_summary(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> "PeriodSummaryRecord":
        """Get aggregated period earnings."""
        ...

    async def get_last_recorded_for_bot(self, bot_player_id: UUID) -> "AttributionEntryRecord | None":
        """Get most recent attribution entry for a bot."""
        ...


class PayoutRequestRepository(Protocol):
    """Repository interface for payout requests."""

    async def create(self, data: "PayoutRequestCreate") -> "PayoutRequestRecord":
        """Create a new payout request."""
        ...

    async def find_by_id(self, payout_request_id: UUID) -> "PayoutRequestRecord | None":
        """Find request by ID."""
        ...

    async def update(self, payout_request_id: UUID, changes: "PayoutRequestUpdate") -> "PayoutRequestRecord":
        """Update request fields."""
        ...

    async def find_by_bot(
        self,
        bot_player_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list["PayoutRequestRecord"], int]:
        """Find requests for a bot with optional status filter."""
        ...

    async def find_pending_by_bot(self, bot_player_id: UUID) -> "PayoutRequestRecord | None":
        """Find any pending payout request for a bot."""
        ...

    async def find_pending_past_hold(self, as_of: datetime) -> list["PayoutRequestRecord"]:
        """Find pending requests past their hold period (for processing queue)."""
        ...


class DailyEarningsRepository(Protocol):
    """Repository interface for daily earnings summary."""

    async def upsert(self, data: "DailyEarningsUpsert") -> "DailyEarningsRecord":
        """Create or update daily earnings record."""
        ...

    async def find_range(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list["DailyEarningsRecord"]:
        """Find daily records in date range."""
        ...
```

---

### Data Read from Other Modules

| Data | Source Module | Access Method | Purpose |
|------|---------------|---------------|---------|
| Player entity | `player` | `PlayerServiceProtocol.get_player()` | Validate bot exists, check if is_bot |
| Bot owner info | `player` | `PlayerServiceProtocol.get_player()` + stored owner_player_id | Authorization checks |
| Bot ad attributions | `ads` | `AdServiceProtocol.get_bot_ad_attributions()` | Source data for earnings calculation |

---

### Transaction Requirements

| Operation | Transaction Scope | Notes |
|-----------|-------------------|-------|
| `get_earnings_balance` | Read only | Simple lookup |
| `get_earnings_summary` | Read only | Aggregate query |
| `get_attribution_entries` | Read only | Paginated lookup |
| `get_daily_earnings` | Read only | Aggregate query |
| `sync_attributions` | Single transaction | Create entries + update ledger atomically |
| `sync_all_attributions` | Per-bot transactions | Each bot synced independently |
| `request_payout` | Single transaction | Create request + update ledger.pending |
| `cancel_payout_request` | Single transaction | Update request + decrement ledger.pending |
| `process_payout` | Single transaction | Update request + move pending to paid_out |
| `reject_payout` | Single transaction | Update request + decrement ledger.pending |

---

## Presentation Boundary

### Business Logic API Surface

The bot_earnings module exposes domain objects and DTOs:
- Input: `PlayerId`, `PayoutRequestId`, `EarningsPeriod`, `PayoutStatus`, dates
- Output: `EarningsBalance`, `EarningsSummary`, `AttributionEntry`, `DailyEarnings`, `AttributionSyncResult`, `BulkSyncResult`, `PayoutRequest`

All types are defined in this module (`src/modules/bot_earnings/types.py`) or imported from `src/core/types/`.

### Adapter Needs

Presentation adapters need to:
1. Convert cents to formatted currency strings (e.g., "$10.00")
2. Format dates and timestamps for display
3. Convert `EarningsBalance` to `BotEarningsBalanceResponse`
4. Convert `PayoutRequest` to `PayoutRequestResponse`
5. Filter sensitive fields (e.g., admin notes) for non-admin requests
6. Calculate percentage changes for period-over-period comparisons

### What Does NOT Belong in This Module

- No JSON serialization (adapter responsibility)
- No HTTP response construction
- No terminal formatting
- No currency formatting (cents-to-dollars is presentation concern)
- No payment processing (deferred - manual payouts for now)
- No PayPal/Stripe integration (future scope)
- No ad impression calculation (ads module responsibility)
- No player authentication (auth module responsibility)

---

## Internal Design

### Core Data Structures

```python
# src/modules/bot_earnings/types.py

from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import NewType
from uuid import UUID

from src.core.types.game import PlayerId, MatchId

PayoutRequestId = NewType("PayoutRequestId", UUID)
AttributionEntryId = NewType("AttributionEntryId", UUID)
AdImpressionId = NewType("AdImpressionId", UUID)


class EarningsPeriod(Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    LIFETIME = "lifetime"


class PayoutStatus(Enum):
    PENDING = "pending"         # Awaiting processing
    PROCESSING = "processing"   # Being processed (reserved for future automation)
    COMPLETED = "completed"     # Successfully paid out
    REJECTED = "rejected"       # Rejected by admin
    CANCELLED = "cancelled"     # Cancelled by owner
```

---

### Algorithm: Attribution Sync

```python
async def sync_attributions(
    self,
    bot_player_id: PlayerId,
) -> AttributionSyncResult:
    """
    Sync attributed revenue from ads module into earnings ledger.

    1. Validate bot exists
    2. Get last sync timestamp
    3. Fetch new attributions from ads module
    4. Filter out already-recorded impressions
    5. Create attribution entries
    6. Update earnings ledger
    7. Update daily earnings summary
    """
    sync_start = datetime.utcnow()
    errors: list[str] = []

    # 1. Validate bot
    player = await self._player_service.get_player(bot_player_id)
    if not player.is_bot:
        raise self._errors.validation(
            "Player is not a bot",
            code="VALIDATION_PLAYER_NOT_BOT",
            player_id=str(bot_player_id),
        )

    # 2. Get or create ledger entry
    ledger = await self._ledger_repo.find_by_bot_id(bot_player_id)
    if ledger is None:
        ledger = await self._ledger_repo.create(EarningsLedgerCreate(
            bot_player_id=bot_player_id,
            owner_player_id=self._get_bot_owner_id(player),  # Stored on player
        ))

    # 3. Determine sync window
    lookback_days = self._config.get("bot_earnings.sync_lookback_days", 7)
    sync_start_date = (date.today() - timedelta(days=lookback_days))
    sync_end_date = date.today()

    # If we have a last sync, use that as start (with overlap for safety)
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

    for daily in attribution_report.daily_breakdown:
        # Get individual impressions for this day
        # Note: This requires ads module to provide impression-level data
        # For now, we create aggregate entries per day

        # Check if we already have entries for this day
        # (Deduplication by ad_impression_id in batch create)

        # Create attribution entry for each impression
        # In production, iterate over impression-level data
        pass

    # Simplified: use aggregate data from ads report
    # Each day becomes one aggregated entry (or multiple per match)

    if len(new_entries) > 0:
        async with self._data_ctx.session() as session:
            # Create entries
            await self._attribution_repo.create_batch(new_entries)

            # Update ledger
            await self._ledger_repo.increment_earned(bot_player_id, new_total_cents)
            await self._ledger_repo.update(bot_player_id, EarningsLedgerUpdate(
                last_attribution_at=datetime.utcnow(),
                last_sync_at=datetime.utcnow(),
            ))

    sync_end = datetime.utcnow()

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
```

---

### Algorithm: Request Payout

```python
async def request_payout(
    self,
    bot_player_id: PlayerId,
    requesting_owner_id: PlayerId,
) -> PayoutRequest:
    """
    Submit a payout request.

    1. Validate bot and ownership
    2. Check no pending payout exists
    3. Check balance >= minimum threshold
    4. Create payout request with hold period
    5. Update ledger pending_payout_cents
    """
    # 1. Validate bot
    player = await self._player_service.get_player(bot_player_id)
    if not player.is_bot:
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
    existing_pending = await self._payout_repo.find_pending_by_bot(bot_player_id)
    if existing_pending is not None:
        raise self._errors.conflict(
            "Bot already has a pending payout request",
            code="CONFLICT_PENDING_PAYOUT_EXISTS",
            bot_player_id=str(bot_player_id),
            existing_request_id=str(existing_pending.id),
        )

    # 3. Calculate available balance
    available = ledger.total_earned_cents - ledger.total_paid_out_cents - ledger.pending_payout_cents

    minimum = self._config.get("bot_earnings.minimum_payout_cents", 1000)
    if available < minimum:
        raise self._errors.validation(
            "Balance below minimum payout threshold",
            code="VALIDATION_BELOW_PAYOUT_THRESHOLD",
            available_cents=available,
            minimum_cents=minimum,
        )

    # 4. Create payout request
    hold_hours = self._config.get("bot_earnings.payout_hold_hours", 72)
    hold_until = datetime.utcnow() + timedelta(hours=hold_hours)

    async with self._data_ctx.session() as session:
        payout = await self._payout_repo.create(PayoutRequestCreate(
            bot_player_id=bot_player_id,
            owner_player_id=requesting_owner_id,
            amount_cents=available,
            status=PayoutStatus.PENDING.value,
            hold_until=hold_until,
        ))

        # 5. Update ledger
        await self._ledger_repo.increment_pending(bot_player_id, available)

    self._logger.info(
        "Payout requested",
        bot_player_id=str(bot_player_id),
        owner_id=str(requesting_owner_id),
        amount_cents=available,
    )

    return self._build_payout_request(payout)
```

---

### Fraud Prevention Considerations

1. **Hold Period:** New payout requests have a configurable hold period (default 72 hours) before they can be processed. This allows time to detect fraudulent attribution patterns.

2. **Single Pending Payout:** A bot can only have one pending payout request at a time, preventing rapid withdrawal attempts.

3. **Minimum Threshold:** Payouts require a minimum balance ($10 default), reducing processing overhead and preventing micro-withdrawals.

4. **Impression Deduplication:** Each ad impression can only be attributed once (enforced by unique constraint on `ad_impression_id`).

5. **Ownership Verification:** Only the registered owner of a bot can request payouts.

6. **Admin Review:** All payouts are manually processed by admins who can reject suspicious requests.

7. **Audit Trail:** Complete attribution history is preserved for fraud investigation.

---

## CLI Surface

### Commands

```bash
# Balance and earnings queries
chromacrush bot-earnings balance <bot-player-id>
chromacrush bot-earnings summary <bot-player-id> [--period day|week|month|quarter|year|lifetime]
chromacrush bot-earnings daily <bot-player-id> --start 2026-01-01 --end 2026-01-31
chromacrush bot-earnings attributions <bot-player-id> [--start DATE] [--end DATE] [--limit N]

# Sync operations
chromacrush bot-earnings sync <bot-player-id>
chromacrush bot-earnings sync-all [--batch-size N]

# Payout operations
chromacrush bot-earnings request-payout <bot-player-id> --owner <owner-player-id>
chromacrush bot-earnings payout-requests <bot-player-id> [--status pending|completed|rejected|cancelled]
chromacrush bot-earnings cancel-payout <payout-request-id> --owner <owner-player-id>

# Admin payout processing
chromacrush bot-earnings process-payout <payout-request-id> --processor <admin-id> [--reference "PayPal-123"]
chromacrush bot-earnings reject-payout <payout-request-id> --processor <admin-id> --reason "Suspicious activity"
chromacrush bot-earnings pending-payouts [--past-hold-only]
```

### Example Invocations

```bash
$ chromacrush bot-earnings balance bot123
Earnings Balance for bot bot123:
  Total earned: $52.35
  Total paid out: $20.00
  Pending payout: $0.00
  Available balance: $32.35
  Last attribution: 2026-02-05 10:30:00 UTC
  Last sync: 2026-02-05 14:00:00 UTC

$ chromacrush bot-earnings summary bot123 --period month
Earnings Summary for bot bot123 (last 30 days):
  Period: 2026-01-06 to 2026-02-05
  Total attributions: 892
  Matches with impressions: 734
  Ad impressions: 892
  Earnings: $12.45
  Average daily: $0.42
  Best day: 2026-01-28 ($1.23)

$ chromacrush bot-earnings daily bot123 --start 2026-01-01 --end 2026-01-07
Daily Earnings for bot bot123:
  Date       | Attrs | Matches | Impr | Earnings
  -----------|-------|---------|------|----------
  2026-01-01 |    28 |      21 |   28 |    $0.38
  2026-01-02 |    31 |      25 |   31 |    $0.42
  2026-01-03 |    19 |      15 |   19 |    $0.25
  2026-01-04 |    42 |      38 |   42 |    $0.56
  2026-01-05 |    35 |      29 |   35 |    $0.47
  2026-01-06 |    27 |      22 |   27 |    $0.36
  2026-01-07 |    33 |      28 |   33 |    $0.44

$ chromacrush bot-earnings request-payout bot123 --owner owner456
Payout request created!
  Request ID: 550e8400-e29b-41d4-a716-446655440001
  Amount: $32.35
  Status: pending
  Hold until: 2026-02-08 14:00:00 UTC (fraud review period)

$ chromacrush bot-earnings process-payout 550e8400 --processor admin789 --reference "PP-TXN-12345"
Payout processed!
  Request ID: 550e8400-e29b-41d4-a716-446655440001
  Amount: $32.35
  Processed by: admin789
  External reference: PP-TXN-12345
```

---

## Edge Cases & Decisions

### EC-1: Bot With No Activity

**Scenario:** Bot exists but has never played any matches.

**Decision:** `get_earnings_balance` returns a balance with all values at zero. No ledger entry is created until first attribution sync.

**Rationale:** Avoid creating empty database records for inactive bots.

---

### EC-2: Duplicate Attribution Attempt

**Scenario:** Same ad impression ID synced twice (e.g., sync runs twice in quick succession).

**Decision:** Reject duplicate with unique constraint on `ad_impression_id`. Sync operation catches this and continues with other entries.

**Rationale:** Each impression must be attributed exactly once to prevent double-counting.

---

### EC-3: Payout Request While Under Minimum

**Scenario:** Bot has $8.50 balance but minimum is $10.00.

**Decision:** Return `VALIDATION_BELOW_PAYOUT_THRESHOLD` with clear message showing available vs. required.

**Rationale:** Minimum threshold reduces processing overhead and prevents micro-payouts.

---

### EC-4: Second Payout Request

**Scenario:** Owner tries to request another payout while one is pending.

**Decision:** Return `CONFLICT_PENDING_PAYOUT_EXISTS` with reference to the existing request.

**Rationale:** Single pending payout per bot simplifies accounting and fraud detection.

---

### EC-5: Cancelled Payout Re-request

**Scenario:** Owner cancels a $30 payout, then requests again for current balance ($32).

**Decision:** Allow the new request for the new balance. Cancellation returns funds to available balance.

**Rationale:** Cancellation reverses the pending hold; owner should be able to request again.

---

### EC-6: Partial Payout

**Scenario:** Owner wants to withdraw only $20 of their $50 balance.

**Decision:** Not supported in initial implementation. Payout request is always for full available balance.

**Rationale:** Simplifies implementation. Full-balance payouts reduce outstanding liability. May add partial payouts in future.

---

### EC-7: Bot Deleted After Earnings

**Scenario:** Bot player is soft-deleted but has unrequested earnings.

**Decision:** Earnings remain in ledger. Owner can still request payout for soft-deleted bots. Ledger entry retains owner_player_id.

**Rationale:** Bot deletion should not forfeit earned revenue. Owner's rights to earnings persist.

---

### EC-8: Owner Changed (Bot Transferred)

**Scenario:** Bot ownership is transferred to a new player.

**Decision:** Not supported in initial scope. If needed, admin can manually update ledger.owner_player_id.

**Rationale:** Bot transfer is a complex operation not in scope. Manual admin resolution is acceptable for edge case.

---

### EC-9: Ads Module Unavailable During Sync

**Scenario:** `ads.get_bot_ad_attributions()` times out or returns error.

**Decision:** Return `INTERNAL_ADS_SERVICE_ERROR`, log the error, and do not update any ledger data. Sync can be retried later.

**Rationale:** Partial sync with missing data would create inconsistencies. Better to fail and retry.

---

### EC-10: Attribution Amount Discrepancy

**Scenario:** Ads module's estimated revenue doesn't match what we calculated before.

**Decision:** Always use the ads module's current estimates. Attribution entries record the estimate at time of sync.

**Rationale:** Ads module is the source of truth for ad revenue. Historical entries preserve point-in-time values.

---

### EC-11: Negative Earnings Adjustment

**Scenario:** Ad provider reports a chargeback or refund after attribution was recorded.

**Decision:** Not supported in initial implementation. Negative adjustments would require admin intervention and manual ledger adjustment.

**Rationale:** Chargebacks are rare; manual handling is acceptable for initial scope.

---

## Open Questions

None. All design decisions have been resolved based on:
- Feasibility report specifications
- Interface contracts guidance
- Data layer guidance
- Ads module artifact (defines `get_bot_ad_attributions()` interface)
- Player module artifact (defines player entity with `is_bot` flag)
- Key Decision #8 in STATE.md (defines initial scope and deferral of automated payouts)

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent (bot_earnings) |
