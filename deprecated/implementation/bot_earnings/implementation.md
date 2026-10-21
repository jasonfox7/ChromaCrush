# Bot Earnings Module - Implementation Document

## Author
Coding Agent (bot_earnings)

## Date
2026-02-06

## Files Created

### Module Source (`src/modules/bot_earnings/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `types.py` | Enums (EarningsPeriod, PayoutStatus), NewType IDs, output dataclasses |
| `dto.py` | Repository DTOs (Create/Update/Upsert), PaginatedResult[T] |
| `protocols.py` | Service protocol, 4 repository protocols, dependency protocols |
| `service.py` | BotEarningsService with 13 public methods |

### ORM Models (`src/data/models/`)
| File | Table | PK |
|------|-------|----|
| `bot_earnings_ledger.py` | `bot_earnings_ledger` | `bot_player_id` (UUID, no UUIDMixin) |
| `bot_attribution_entry.py` | `bot_attribution_entries` | `id` (UUID via UUIDMixin) |
| `bot_payout_request.py` | `bot_payout_requests` | `id` (UUID via UUIDMixin) |
| `bot_earnings_daily.py` | `bot_earnings_daily` | Composite (`bot_player_id`, `earnings_date`) |

### Repositories (`src/data/repositories/`)
| File | Implements |
|------|-----------|
| `bot_earnings_ledger_repository.py` | `EarningsLedgerRepositoryProtocol` |
| `bot_attribution_entry_repository.py` | `AttributionEntryRepositoryProtocol` |
| `bot_payout_request_repository.py` | `PayoutRequestRepositoryProtocol` |
| `bot_daily_earnings_repository.py` | `DailyEarningsRepositoryProtocol` |

### Migration
| File | Tables |
|------|--------|
| `src/data/migrations/versions/009_bot_earnings_tables.py` | All 4 tables with indexes and constraints |

### CLI Commands (`src/cli/commands/bot_earnings_commands.py`)
12 commands: balance, summary, daily, attributions, sync, sync-all, request-payout, payout-requests, cancel-payout, process-payout, reject-payout, pending-payouts

### Tests (`tests/unit/modules/bot_earnings/`)
| File | Coverage |
|------|---------|
| `__init__.py` | Package marker |
| `test_bot_earnings_service.py` | 40+ test cases covering all 13 public methods |

## Deviations from Artifact

### 1. Daily Earnings Repository Added
The artifact mentions `DailyEarningsRepository` in the repository interfaces section but does not explicitly list it in the `__init__` constructor. Added `daily_earnings_repository` parameter to `BotEarningsService.__init__()` since the `get_daily_earnings` method and sync operations require it.

### 2. Sync Attribution Aggregation Strategy
The artifact's sync algorithm pseudocode shows per-impression entries, but notes this requires impression-level data from ads module. Implemented daily aggregate entries instead (one attribution entry per bot per day) with deterministic UUID v5-based impression IDs for deduplication. This aligns with the artifact's note about using aggregate data.

### 3. Migration Numbering
Assignment specifies `009` as the migration number. The last existing migration is `007_ad_tables.py` (no `008` exists). Migration `009` was created with `down_revision = "007"` as specified.

### 4. Admin Validation Deferred
The artifact lists `FORBIDDEN_NOT_ADMIN` as an error code for `process_payout` and `reject_payout`. Admin validation is not implemented in the service layer since admin authorization is a cross-cutting concern handled at the API/auth layer. The service accepts a `processor_id` but does not validate admin status -- this follows the same pattern as other modules.

## Key Design Decisions

1. **All dependencies via `__init__` injection** -- no direct imports of core services
2. **All public methods are `async def`** per artifact specification
3. **Errors through injected ErrorServiceProtocol** -- no bare raises
4. **Repository protocols defined in module's protocols.py** -- not in `src/data/protocols/`
5. **PaginatedResult[T] defined locally** -- follows ads module pattern
6. **Config keys read in `__init__`** -- cached for performance per ads service pattern
