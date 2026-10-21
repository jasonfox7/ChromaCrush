# Stage 3 — P1-P3 Compliance Report: bot_earnings

**Reviewer:** Karen Agent
**Date:** 2026-02-07
**Module:** bot_earnings
**Files reviewed:**
- `src/modules/bot_earnings/service.py` (849 lines)
- `src/modules/bot_earnings/protocols.py`
- `src/modules/bot_earnings/dto.py`
- `src/modules/bot_earnings/types.py`
- `src/modules/bot_earnings/__init__.py`
- `tests/unit/modules/bot_earnings/test_bot_earnings_service.py`
- `src/cli/commands/bot_earnings_commands.py`

---

## P1 Findings (Framework Rule Violations)

### P1-01: No Direct Service Instantiation
**PASS** — No matches for prohibited patterns. All core services arrive via `__init__` injection. TYPE_CHECKING imports of protocol types are used correctly.

### P1-02: No Direct Environment Access
**PASS** — No `os.environ`, `os.getenv`, or `import os` found in module source.

### P1-03: No Bare Raises
**PASS** — All errors raised through `self._errors.validation(...)`, `self._errors.not_found(...)`, `self._errors.conflict(...)`, `self._errors.forbidden(...)`, or `self._errors.internal(...)`. No bare exception raises.

### P1-04: No UI/Rendering Logic in Modules
**PASS** — No click, rich, print, sys.stdout/stderr, flask, or fastapi imports in `src/modules/bot_earnings/`. Module returns dataclasses only.

### P1-05: No Raw Data Access in Business Logic
**PASS** — All data access goes through injected repository protocol interfaces. No SQLAlchemy, Redis, or raw SQL in service.py.

**Note:** `service.py:807` contains `import uuid as _uuid` inside `_generate_impression_id`. This is a stdlib import for UUID generation, not a data access import, so it is acceptable. However, the inline import is unconventional; a module-level import under TYPE_CHECKING or unconditionally would be more typical.

### P1-06: Async Matches Artifact Spec
**PASS** — All public protocol methods in `protocols.py` are `async def`. The service implementation matches. No `asyncio.run()` or `asyncio.create_task()` in module code. No hidden async patterns.

### P1-07: CLI Exercises Same Code Paths

[P1-07] [bot_earnings_commands.py:530-549] The `pending_payouts` CLI command bypasses the service layer. At lines 533-536, it directly imports and instantiates `SQLAlchemyPayoutRequestRepository` and calls repository methods (`repo.find_pending_past_hold`, `repo.find_by_bot`) instead of going through `BotEarningsService`. The comment at line 532 explicitly acknowledges this: "Access the payout repo directly for this admin query". -> Add a `get_pending_payouts(past_hold_only: bool) -> list[PayoutRequest]` method to `BotEarningsService` and `BotEarningsServiceProtocol`, then call it from the CLI command instead of directly accessing the repository.

---

## P2 Findings (Data/Config Compliance)

### P2-01: Config Keys Match Registered Namespaces
**PASS** — Service uses 6 config keys, all under the `bot_earnings.*` namespace: `bot_earnings.minimum_payout_cents`, `bot_earnings.attribution_share_percent`, `bot_earnings.sync_lookback_days`, `bot_earnings.max_date_range_days`, `bot_earnings.payout_hold_hours`, `bot_earnings.sync_batch_size`. The `bot_earnings` namespace IS listed in the configuration.md registered namespaces table.

### P2-02: Repository Pattern Followed
**PASS** — Service receives 4 repository protocols via `__init__`. All data access flows through `self._ledger_repo`, `self._attribution_repo`, `self._payout_repo`, `self._daily_repo`. Service never imports SQLAlchemy or Redis.

### P2-03: Data Ownership Respected
**PASS** — Bot earnings writes only to its owned tables (bot_earnings_ledger, bot_attribution_entries, bot_payout_requests, bot_earnings_daily). Player data is read through `PlayerServiceProtocol`. Ad data is read through `AdServiceProtocol`.

### P2-04: Transactions at Service Layer

[P2-04] [service.py:all] Artifact specifies `data_ctx: DataContextProtocol` as a constructor parameter (artifact section "Public Interface", line 41), and the artifact's sync/payout algorithms explicitly use `async with self._data_ctx.session()` for transaction boundaries. However, `BotEarningsService.__init__` does NOT accept or use DataContext. Multi-step operations that require atomic consistency lack explicit transaction boundaries:
- `sync_attributions` (lines 242-373): creates attribution entries, increments ledger earned, upserts daily summaries, and updates ledger sync timestamp across multiple separate repository calls with no transaction wrapper.
- `request_payout` (lines 422-504): creates payout request and increments pending balance without a transaction.
- `cancel_payout_request` (lines 540-588): updates request status and returns funds to available balance without a transaction.
- `process_payout` (lines 590-644): updates request status and moves pending to paid out without a transaction.
- `reject_payout` (lines 646-700): updates request status and returns funds without a transaction.
-> Inject `DataContextProtocol` via `__init__` and wrap all multi-step write operations in `async with self._data_ctx.session()` blocks per the artifact specification.

---

## P3 Findings (Best Practices / Testing)

### P3-01: Service File Length

[P3-01] [service.py:1-849] Service file is 849 lines, exceeding the 500-line hard limit. -> Extract sync logic (`sync_attributions`, `sync_all_attributions`, and related helpers) into a separate `sync_service.py` or internal helper module. Payout operations could also be extracted into a focused `payout_service.py`.

### P3-02: Function Length

[P3-02] [service.py:242-373] `sync_attributions` is approximately 131 lines, far exceeding the 50-line limit. -> Break into smaller methods: `_determine_sync_window`, `_fetch_and_filter_attributions`, `_persist_sync_results`, `_build_sync_result`.

[P3-02] [service.py:422-504] `request_payout` is approximately 82 lines, exceeding the 50-line limit. -> Extract validation into `_validate_payout_preconditions` and separate the payout creation + ledger update into `_create_payout_record`.

### P3-03: Constructor Parameters
**PASS** — `__init__` has 9 parameters (self excluded). Artifact specifies 9 dependencies (though the composition differs: artifact has `data_ctx` and no `daily_earnings_repository`, while implementation has `daily_earnings_repository` and no `data_ctx`). Within acceptable range per checklist note. The composition difference is a P2-04 issue, not a P3-03 issue.

### P3-04: No Magic Numbers

[P3-04] [service.py:787] `date(2020, 1, 1)` — hardcoded fallback date for LIFETIME period should be a named constant. -> Define `LIFETIME_START_DATE = date(2020, 1, 1)` at module level with a descriptive comment, or compute it dynamically from the earliest ledger creation date.

[P3-04] [service.py:736] `limit > 100` — pagination bound should be a named constant. -> Define `MAX_PAGE_LIMIT = 100` or read from config.

### P3-05: Tests Use Injected Mocks
**PASS** — All test dependencies are created via `AsyncMock`/`MagicMock` and injected through `BotEarningsService.__init__`. No `@mock.patch`, `with patch(...)`, or `monkeypatch.setattr` usage found in test files. The `build_service` helper function correctly demonstrates the injection pattern.

### P3-06: Test Naming Conventions
**PASS** — All test files follow `test_*.py`, all test methods follow `test_*_*` pattern with clear scenario naming. No vague test names.

### P3-07: Error Path Tests Exist

[P3-07] [tests/unit/modules/bot_earnings/] Missing test for `FORBIDDEN_NOT_ADMIN` error path. The artifact specifies this error code for `process_payout` and `reject_payout` (artifact section "Error Cases": "Not admin | FORBIDDEN_NOT_ADMIN | forbidden | operation, requester_id"). Neither `process_payout` nor `reject_payout` in `service.py` implements admin validation, and no test covers this error path. -> This is both an implementation gap and a test gap. The service needs admin role checking for `process_payout` and `reject_payout` per the artifact, and tests to cover the `FORBIDDEN_NOT_ADMIN` error path.

[P3-07] [tests/unit/modules/bot_earnings/] Missing test for `CONFLICT_SYNC_IN_PROGRESS` error path. The artifact specifies this error code (artifact section "Error Cases": "Sync already in progress | CONFLICT_SYNC_IN_PROGRESS | conflict | bot_player_id, started_at"). The service does not implement sync-in-progress detection, and no test covers this error path. -> This is both an implementation gap and a test gap. The service needs a sync lock mechanism (e.g., a sync_in_progress flag on the ledger) per the artifact, and a test to cover the `CONFLICT_SYNC_IN_PROGRESS` error path.

**Covered error paths:** VALIDATION_PLAYER_NOT_BOT, VALIDATION_INSUFFICIENT_BALANCE, VALIDATION_BELOW_PAYOUT_THRESHOLD, VALIDATION_INVALID_INPUT (limit, offset, date range, external reference, rejection reason), VALIDATION_DATE_RANGE_TOO_LARGE, NOT_FOUND_PAYOUT_REQUEST, FORBIDDEN_NOT_BOT_OWNER, CONFLICT_PAYOUT_NOT_PENDING, CONFLICT_PENDING_PAYOUT_EXISTS, INTERNAL_ADS_SERVICE_ERROR. All tested.

### P3-08: Async Tests Properly Structured
**PASS** — All async test methods use `async def test_*` with `@pytest.mark.asyncio`. Service calls are properly awaited. No `asyncio.run()` in tests.

### P3-09: Type Hints on Service Methods
**PASS** — All public methods have parameter and return type hints.

---

## Summary

| Priority | Count | Details |
|----------|-------|---------|
| P1       | 1     | CLI `pending_payouts` command bypasses service layer (direct repo access) |
| P2       | 1     | Missing DataContext injection for transaction management |
| P3       | 6     | File length (1), function length (2), magic numbers (2), missing error path tests/implementations (2) |

**Note:** The `FORBIDDEN_NOT_ADMIN` and `CONFLICT_SYNC_IN_PROGRESS` error codes from the artifact are not implemented in the service. These are both implementation gaps (not just test gaps), but they manifest here as P3-07 findings since the checklist checks for error path test coverage. The actual missing implementations are arguably P0-level interface gaps that should have been caught in Stage 2.
