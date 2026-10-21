# Compliance Checklist — Karen Stage 3 (P1-P3)

**Version:** 1.0
**Date:** 2026-02-06
**Author:** Orchestrator
**Purpose:** Pre-baked checklist for Stage 3 P1-P3 code review agents. Replaces reading 4,214 lines of raw guidance docs.

**Sources:** best-practices.md, configuration.md, data-layer.md, testing-standards.md, interface-contracts.md v1.6, agent instructions

---

## How To Use This Checklist

For each assigned module:
1. Read this checklist once.
2. Read ALL source files in `src/modules/[module]/`.
3. Read ALL test files in `tests/unit/modules/[module]/`.
4. Read `src/cli/commands/[module]_commands.py`.
5. Read `docs/artifacts/[module]/artifact.md` (for config keys, error codes, async spec).
6. Run every check below. Use grep patterns where provided.
7. Write findings to `docs/reviews/[module]/stage3-fixes.md`.

**Finding format:** `[P1|P2|P3] [file:line] description -> fix`

If a module has zero findings, write "No P1-P3 issues found."

**Important:** P0 interface compliance was handled in Stage 2. This checklist covers P1 (framework rules), P2 (data/config compliance), and P3 (best practices / testing).

---

# P1 — Framework Rules

These are hard violations of the framework. Must be fixed.

## P1-01: No Direct Service Instantiation

**Rule:** All dependencies arrive through `__init__`. No importing and constructing core services directly. The composition root (`src/core/composition_root.py`) is the only place services are created.

**Grep patterns (run against `src/modules/[module]/`):**
```
from src.core.config import
from src.core.logger import
from src.core.errors import
from src.core.data_context import
ConfigService(
LogService(
ErrorService(
DataContext(
```

**Allowed exceptions:**
- Imports of Protocol types: `from src.core.protocols.* import *Protocol` — OK
- Imports of type definitions: `from src.core.types.game import PlayerId` — OK
- Imports of the `AppError` class for type annotations or isinstance checks — OK
- Re-exports in `__init__.py` — OK

**Not allowed:**
- `from src.core.config import config` (importing a singleton)
- `ConfigService()` or `ConfigService.load()` inside module code
- Any direct construction of core services

## P1-02: No Direct Environment Access

**Rule:** No `os.environ`, no `os.getenv()`. All environment values flow through injected config service.

**Grep patterns (run against `src/modules/[module]/`):**
```
os.environ
os.getenv
```

**Also check for:**
```
import os
```
If `import os` is present, verify it's used only for path operations (e.g., `os.path`), NOT for environment access.

## P1-03: No Bare Raises

**Rule:** All errors flow through the injected `ErrorService` using the error taxonomy from interface-contracts.md §2. No bare `raise Exception()`, `raise ValueError()`, `raise TypeError()`, `raise RuntimeError()`.

**Grep patterns (run against `src/modules/[module]/`):**
```
raise Exception(
raise ValueError(
raise TypeError(
raise RuntimeError(
raise KeyError(
raise NotImplementedError(
```

**Allowed exceptions:**
- `raise` (bare re-raise of caught exception) — OK
- `raise self._errors.validation(...)` — OK (this is the correct pattern)
- `raise AppError(...)` — OK if constructing with proper error code
- Inside `__post_init__` validators on frozen dataclasses — OK (these are type-level, not service-level)

**Not allowed:**
- `raise ValueError("some message")` in service.py or any business logic file
- Any exception type that bypasses the error taxonomy

## P1-04: No UI / Rendering Logic in Modules

**Rule:** No DOM, no terminal formatting, no HTTP response construction in `src/modules/`. Business logic returns data. Presentation is in `src/cli/` or `src/api/`.

**Grep patterns (run against `src/modules/[module]/`):**
```
import click
from click
import rich
from rich
print(
sys.stdout
sys.stderr
import flask
import fastapi
from fastapi
JSONResponse
HTMLResponse
```

**Also check:** No string formatting that looks like terminal output (e.g., f-strings with ANSI codes, table formatting). Module code should return dataclasses/dicts, not formatted strings.

## P1-05: No Raw Data Access in Business Logic

**Rule:** No direct SQL, no direct ORM calls in `src/modules/`. All data through injected repository protocol interfaces.

**Grep patterns (run against `src/modules/[module]/`):**
```
execute(
cursor
session.query
\.sql(
select(
insert(
update(
delete(
from sqlalchemy
import sqlalchemy
from redis
import redis
```

**Allowed exceptions:**
- Files under `src/modules/[module]/models.py` or `src/modules/[module]/repositories.py` — these ARE the data layer. Raw data access is expected there.
- Repository implementations that use SQLAlchemy internally — OK.

**Not allowed:**
- `service.py` files importing or calling SQLAlchemy, Redis, or raw SQL.

## P1-06: Async Matches Artifact Spec

**Rule:** If the artifact says a method is async, it must be `async def`. If the artifact says sync, it must NOT be `async def`.

**How to check:**
1. Read the artifact's public interface section.
2. For each method in the protocol, confirm `async def` matches artifact specification.
3. Sync modules (board, scoring, special_gems, board_gen): NO `async def` on public methods.
4. Async modules (all others): ALL public protocol methods must be `async def`.

**Also check:** No hidden async patterns:
```
asyncio.run(
asyncio.create_task(
```
These should NOT appear in module service code (fire-and-forget violation).

## P1-07: CLI Exercises Same Code Paths

**Rule:** CLI commands in `src/cli/commands/[module]_commands.py` must call the same service methods as the primary presentation layer. They must not bypass the service layer or use direct data access.

**How to check:**
1. Read the CLI commands file.
2. Each command should instantiate or receive the service and call a protocol method.
3. No direct repository calls, no direct data access in CLI commands.
4. No business logic duplicated in CLI — only service orchestration.

**Grep patterns (run against `src/cli/commands/[module]_commands.py`):**
```
Repository(
session.query
execute(
```

---

# P2 — Data Layer & Config Compliance

These are compliance issues with the data and configuration guidance.

## P2-01: Config Keys Match Registered Namespaces

**Rule:** Every config key used in module code must be from a registered namespace in configuration.md §2.

**Registered namespaces and their keys:**

| Namespace | Keys |
|-----------|------|
| `app` | name, version, environment, debug |
| `database` | host, port, name, user, password, pool_size |
| `redis` | host, port, key_prefix |
| `auth` | jwt_secret, jwt_expiry_minutes, api_key_prefix |
| `game` | board_width, board_height, gem_types, moves_per_match |
| `matchmaking` | elo_initial, elo_k_factor, queue_max_size, elo_range_initial, elo_range_max, elo_expansion_interval_seconds, elo_expansion_step, match_timeout_seconds, queue_poll_interval_ms |
| `energy` | max_hearts, regen_interval_minutes |
| `payments` | ad_free_product_id, ad_free_price_cents, ad_free_currency, intent_expiry_minutes, apple_bundle_id, apple_shared_secret, apple_verify_url, apple_sandbox_verify_url, google_package_name, google_service_account_key, webhook_apple_secret, webhook_google_secret, allow_sandbox_purchases |
| `bot_earnings` | minimum_payout_cents, attribution_share_percent, sync_lookback_days, max_date_range_days, payout_hold_hours, sync_batch_size |
| `websocket` | enabled, path, heartbeat_interval_seconds, connection_timeout_seconds, max_connections_per_player, max_message_size_bytes, rate_limit_messages_per_second |
| `logging` | level, format |
| `features` | (feature flag entries) |
| `debug` | (per-module debug flags) |

**How to check:**
1. Grep for `config.get(` and `config.require(` in module source.
2. Extract the key string argument.
3. Verify every key appears in the table above.
4. If a module uses a key NOT in the table, flag as P2 finding.

**Note:** Modules may define their own config namespaces (e.g., `ads.cooldown_seconds`) if declared in their artifact. Check artifact for module-specific keys. If the artifact declares it and configuration.md doesn't have it, that's an Orchestrator escalation item — flag but don't block.

## P2-02: Repository Pattern Followed

**Rule:** Per data-layer.md §2:
- All data access flows through injected Protocol interfaces.
- Repository protocols defined in module code or `src/data/protocols/`.
- Concrete implementations in `src/data/repositories/` or module's own `repositories.py`.
- Business logic (service.py) NEVER imports SQLAlchemy, Redis, or any storage API directly.

**How to check:**
1. Service files should receive repository protocols via `__init__`.
2. Service files should call `self._repo.method()`, not raw data access.
3. Repository files may use SQLAlchemy/Redis internally — that's correct.

## P2-03: Data Ownership Respected

**Rule:** Per data-layer.md §3, modules only write to their owned tables. Cross-module data access goes through the owning module's service interface.

**Ownership matrix:**

| Module | Owns (Write) | Reads From |
|--------|-------------|------------|
| player | players, energy_states | - |
| auth | api_keys, sessions | players |
| match | matches | players, board_gen |
| vault | vault_artifacts | players, matches |
| matchmaking | matchmaking_queue (Redis) | players, matches |
| events | events, event_participants | players, vault |
| energy | energy_states (shared with player) | players |
| ads | ad_impressions, ad_requests, ad_free_status | players, matches, events |
| payments | purchases, purchase_intents, products | players, ads (ad_free_status) |
| bot_earnings | bot_earnings, attribution_entries, payout_requests | players, ads |

**How to check:** If a service imports or references another module's repository directly (not through a service protocol), flag as P2 violation.

## P2-04: Transactions at Service Layer

**Rule:** Per data-layer.md §4, transactions live at the service level, NOT inside repository methods.

**How to check:**
1. Repository methods should NOT call `session.commit()` or `session.rollback()`.
2. Service methods should use `async with self._data_ctx.session() as session:` pattern.
3. Transaction boundaries should be at service method level.

**Grep patterns (run against repository files):**
```
.commit()
.rollback()
```
These should NOT appear in repository implementations (only in DataContext or service-level code).

---

# P3 — Best Practices & Testing

Quality and maintainability checks. Lower priority but still tracked.

## P3-01: Service Files Length

**Rule:** Per best-practices.md §5:
- Python service files: soft limit 300 lines, hard limit 500 lines.

**How to check:** Count lines in `service.py` (or main service file). Flag if > 500 lines.

## P3-02: Function Length

**Rule:** Per best-practices.md §5:
- Maximum function length: 50 lines.

**How to check:** Scan service files for functions exceeding 50 lines. Flag the longest offenders.

## P3-03: Constructor Parameters

**Rule:** Per best-practices.md §5:
- Maximum constructor parameters: 6.

**How to check:** Count `__init__` parameters in service classes. Flag if > 6.

**Note:** Many async modules legitimately need 7-12 dependencies (config, logger, errors, data_ctx, repos, other services). If the artifact specifies the constructor signature, defer to the artifact. Flag only if the count is HIGHER than what the artifact specifies.

## P3-04: No Magic Numbers

**Rule:** Per best-practices.md §3.1:
- Named constants for significant values. No bare numeric literals in business logic.

**How to check:** Scan service files for numeric literals that aren't 0, 1, -1, or used in range/enumerate. Flag significant numbers (e.g., `if score > 100`, `timeout = 300`) that should be config values or named constants.

**Exception:** Test files may use magic numbers for test data — that's expected.

## P3-05: Tests Use Injected Mocks

**Rule:** Per testing-standards.md §2.4:
- No global state patching (`@mock.patch("src.core.config.config")`).
- No module-level variable mutation.
- All dependencies injected through `__init__` the same way as production code.

**Grep patterns (run against `tests/unit/modules/[module]/`):**
```
@mock.patch
@patch
mock.patch(
unittest.mock.patch
monkeypatch.setattr
```

**Allowed:**
- `unittest.mock.AsyncMock` for creating mock objects that are then injected — OK
- `monkeypatch` for environment variable setup in conftest — OK if setting up test environment, not patching production code

**Not allowed:**
- `@mock.patch("src.modules.board.service.SomeGlobal")` — patching internals
- `monkeypatch.setattr(src.modules.board.service, "X", mock)` — patching module attributes

## P3-06: Test Naming Conventions

**Rule:** Per testing-standards.md §1.2:
- Test files: `test_{module}.py`
- Test classes: `Test{ClassName}`
- Test methods: `test_{method}_{scenario}_{expected}`
- Fixtures: `snake_case` descriptive
- Mock classes: `Mock{ProtocolName}`

**How to check:** Scan test files for:
1. Test methods that don't follow `test_` prefix
2. Test classes that don't follow `Test` prefix
3. Extremely vague test names (e.g., `test_it_works`, `test_basic`)

## P3-07: Error Path Tests Exist

**Rule:** Per testing-standards.md §3.1:
- Every error type defined in the artifact's error cases must have at least one test.

**How to check:**
1. Read the artifact's error cases table.
2. For each error code listed, search test files for a test that exercises that error path.
3. Flag missing error path tests.

**Note:** This is a coverage check, not a code quality check. If the error path is complex, having ONE test is acceptable.

## P3-08: Async Tests Properly Structured

**Rule:** Per testing-standards.md §4:
- Async test methods should be `async def test_...`
- Tests for async services should await service calls
- pytest-asyncio in auto mode: async tests detected automatically

**How to check:**
For async modules, verify:
1. Test methods that call async service methods are `async def`
2. Service calls are properly `await`ed
3. No `asyncio.run()` inside test methods (use pytest-asyncio)

## P3-09: Type Hints on Service Methods

**Rule:** Per best-practices.md §7:
- All function parameters and return types must have type hints.

**How to check:** Scan service methods for missing type annotations. Focus on public methods — private helper methods are lower priority.

---

# Escalation Rules

If you find a systemic issue that appears in MANY modules:
- Document it in your finding
- Prefix with `[SYSTEMIC]`
- Example: `[SYSTEMIC] [P1-03] 8 of 14 modules use raise ValueError in __post_init__ validators`

The Orchestrator will address systemic issues at the framework level rather than per-module.

---

# Config Key Quick-Reference by Module

For P2-01 checks, here are the expected config keys per module based on artifacts:

| Module | Expected Config Keys |
|--------|---------------------|
| board | `game.board_width`, `game.board_height`, `game.gem_types` |
| scoring | `game.moves_per_match` (or scoring-specific keys from artifact) |
| special_gems | (check artifact for any special gem config) |
| board_gen | `game.board_width`, `game.board_height`, `game.gem_types` |
| player | `matchmaking.elo_initial` (for default ELO) |
| auth | `auth.jwt_secret`, `auth.jwt_expiry_minutes`, `auth.api_key_prefix` |
| energy | `energy.max_hearts`, `energy.regen_interval_minutes` |
| vault | (check artifact) |
| match | `game.moves_per_match`, `game.board_width`, `game.board_height` |
| matchmaking | `matchmaking.*` (all matchmaking keys) |
| events | (check artifact) |
| ads | (check artifact for ads-specific keys) |
| payments | `payments.*` (all payments keys) |
| bot_earnings | `bot_earnings.*` (all bot_earnings keys) |

---

# Severity Reference

| Priority | Meaning | Fix When |
|----------|---------|----------|
| P1 | Framework rule violation | Stage 4 (mandatory) |
| P2 | Data/config compliance gap | Stage 4 (mandatory) |
| P3 | Best practice / quality issue | Stage 4 (if time permits) |

---

## Changelog

| Date | Version | Change |
|------|---------|--------|
| 2026-02-06 | 1.0 | Initial checklist extracted from 5 guidance docs |
