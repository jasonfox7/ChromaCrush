# Matchmaking Module — Stage 3 Compliance Review (P1-P3)

**Reviewer:** Karen Agent
**Date:** 2026-02-07
**Module:** matchmaking
**Source:** `src/modules/matchmaking/`, `tests/unit/modules/matchmaking/`, `src/cli/commands/matchmaking_commands.py`

---

## P1 — Framework Rules

### P1-01: No Direct Service Instantiation
- [P1] [service.py:14] `from src.core.errors import AppError` — direct import of `AppError` from `src.core.errors`. This import is used for `except AppError as e:` at line 576, which is an isinstance/catch pattern. Per the checklist, imports of `AppError` for isinstance checks are explicitly allowed. **PASS (allowed exception).**

All other protocol imports (`ConfigProtocol`, `ErrorServiceProtocol`, `LoggerProtocol`, repository protocols) are under `TYPE_CHECKING` guards. Service dependencies arrive via `__init__`.

### P1-02: No Direct Environment Access
**PASS** — No `os.environ`, `os.getenv`, or `import os` found in module source.

### P1-03: No Bare Raises
**PASS** — No bare `raise Exception()`, `raise ValueError()`, etc. found. All errors raised through `self._errors.validation()`, `self._errors.conflict()`, `self._errors.forbidden()`, and `self._errors.internal()`.

### P1-04: No UI / Rendering Logic in Modules
**PASS** — No `click`, `rich`, `print()`, or terminal formatting found in `src/modules/matchmaking/`.

### P1-05: No Raw Data Access in Business Logic
**PASS** — No `execute()`, `cursor`, `session.query`, `select()`, `from sqlalchemy`, `from redis`, or `import redis` found in `src/modules/matchmaking/`. All data access goes through the injected `MatchmakingQueueRepositoryProtocol`. Note: Redis usage is expected in the repository implementation, not in the service.

### P1-06: Async Matches Artifact Spec
**PASS** — Matchmaking is an async module. All 7 public methods (`join_queue`, `leave_queue`, `get_queue_status`, `find_match`, `process_queue`, `cleanup_stale_entries`, `get_queue_stats`) are `async def`. All private helpers are also `async def`. No hidden async patterns (`asyncio.run()`, `asyncio.create_task()`) found in module source.

### P1-07: CLI Exercises Same Code Paths
**FINDINGS:**

- [P1] [matchmaking_commands.py:127-153] Inline `_PasswordStore` class contains raw data access: `select(PlayerModel.password_hash)`, `session.execute(stmt)`, `update(PlayerModel)`. This raw SQL/ORM code is inside the CLI commands file, violating "No raw data access in CLI commands." -> Move `_PasswordStore` to `src/data/repositories/` as a proper repository class, or refactor the CLI composition to use the composition root's wiring instead of inline classes.

All CLI commands themselves (`join`, `leave`, `status`, `find`, `process`, `cleanup`, `stats`, `list_queue`) correctly call `MatchmakingService` methods through the service instance. No business logic is duplicated. The violation is specifically in the composition wiring helper, not in command logic.

---

## P2 — Data Layer & Config Compliance

### P2-01: Config Keys Match Registered Namespaces
**FINDINGS:**

The matchmaking service uses config keys that differ from the registered namespace keys in configuration.md:

| Used in Code | Registered in configuration.md | Match? |
|---|---|---|
| `matchmaking.initial_elo_range` | `matchmaking.elo_range_initial` | NO (name mismatch) |
| `matchmaking.elo_range_expansion` | `matchmaking.elo_expansion_step` | NO (name mismatch) |
| `matchmaking.elo_range_expansion_interval_seconds` | `matchmaking.elo_expansion_interval_seconds` | NO (name mismatch) |
| `matchmaking.max_elo_range` | `matchmaking.elo_range_max` | NO (name mismatch) |
| `matchmaking.queue_timeout_seconds` | `matchmaking.match_timeout_seconds` | NO (name mismatch) |
| `matchmaking.min_wait_before_expansion` | (not registered) | NO (missing) |

All six keys are declared in the artifact (section "Configuration Keys"). Per the checklist: "If the artifact declares it and configuration.md doesn't have it, that's an Orchestrator escalation item -- flag but don't block."

- [P2] [service.py:70-87] Six config key names used in matchmaking service do not match the registered key names in configuration.md. The artifact uses different naming conventions than configuration.md. -> Orchestrator escalation: reconcile the key names between the artifact and configuration.md. Either update configuration.md to match the artifact key names, or update the code to match configuration.md.

**Non-blocking escalation item.**

### P2-02: Repository Pattern Followed
**PASS** — `service.py` receives `matchmaking_queue_repository`, `match_service`, and `player_service` via `__init__`. All data access uses injected protocol methods. No direct Redis or SQLAlchemy imports in service code.

### P2-03: Data Ownership Respected
**PASS** — Matchmaking module owns Redis-backed queue data only. Cross-module data access uses `PlayerServiceProtocol` and `MatchServiceProtocol` injected interfaces, not direct repository access.

### P2-04: Transactions at Service Layer
**PASS** — No `.commit()` or `.rollback()` calls found in module source. Redis atomicity is handled through the repository protocol's `atomic_remove_pair()` method.

---

## P3 — Best Practices & Testing

### P3-01: Service File Length
- [P3] [service.py] File is 645 lines, which exceeds the 500-line hard limit. -> Consider extracting private helpers (`_maybe_expand_elo_range`, `_try_create_match`, `_re_add_to_queue`, `_calculate_queue_position`, `_estimate_wait_time`) into a separate `helpers.py` or splitting the service into queue operations and match-finding operations.

### P3-02: Function Length
**FINDINGS:**

- [P3] [service.py:91-177] `join_queue` body is approximately 75 lines (excluding docstring). Exceeds the 50-line maximum. -> Extract validation steps (pool type check, queue check, active match check) into a private `_validate_join_queue()` helper.
- [P3] [service.py:242-336] `find_match` body is approximately 88 lines (excluding docstring). Exceeds the 50-line maximum. -> Extract timeout handling and opponent iteration into private helpers.
- [P3] [service.py:338-415] `process_queue` body is approximately 71 lines (excluding docstring). Exceeds the 50-line maximum. -> Extract the inner loop into a `_process_single_player()` helper.

### P3-03: Constructor Parameters
**PASS** — `MatchmakingService.__init__` takes 6 parameters (config, logger, errors, match_service, player_service, matchmaking_queue_repository). This matches the artifact specification and is at the maximum of 6.

### P3-04: No Magic Numbers
**FINDINGS:**

- [P3] [service.py:641] `base_wait = 30` — magic number in `_estimate_wait_time`. This should be a config value or named constant.
- [P3] [service.py:642] `reduction = math.sqrt(count - 1) * 5` — magic number `5` in wait time estimation formula. Should be a named constant.
- [P3] [service.py:643] `estimated = max(5, int(base_wait - reduction))` — magic number `5` as minimum wait floor. Should be a named constant.
- [P3] [service.py:221] `limit=100` in `find_opponents_in_range` call inside `get_queue_status` — magic number. Should be a named constant or config value.
- [P3] [service.py:297] `limit=10` in `find_opponents_in_range` call inside `find_match` — magic number. Should be a named constant.

-> Define named constants at module level (e.g., `_BASE_WAIT_ESTIMATE_SECONDS = 30`, `_MIN_WAIT_ESTIMATE_SECONDS = 5`, `_WAIT_REDUCTION_FACTOR = 5`, `_DEFAULT_OPPONENT_SEARCH_LIMIT = 10`, `_STATUS_OPPONENT_SEARCH_LIMIT = 100`).

### P3-05: Tests Use Injected Mocks
**FINDINGS:**

- [P3] [test_matchmaking_service.py:15] `from unittest.mock import AsyncMock, MagicMock, patch` — `patch` is imported but never used. This is an unused import. While `AsyncMock` and `MagicMock` are used correctly for creating mock objects that are then injected, the `patch` import suggests the developer considered (or forgot to remove) global state patching. -> Remove the unused `patch` import.

All tests actually use proper injection patterns: mock dependencies are created as `AsyncMock()` instances and passed directly to the `MatchmakingService` constructor. No `@mock.patch` or `monkeypatch.setattr` usage found. **PASS (with unused import note).**

### P3-06: Test Naming Conventions
**PASS** — All test files follow `test_*.py` pattern. All test classes follow `Test*` pattern. All test methods follow `test_*` naming with descriptive suffixes. Helper functions use `make_*` naming pattern, which is clear and consistent.

### P3-07: Error Path Tests Exist
**FINDINGS:**

Artifact error codes coverage:

| Error Code | Test Exists? |
|---|---|
| `NOT_FOUND_PLAYER` | YES — `test_join_queue_player_not_found`, `test_player_not_found_propagates` |
| `CONFLICT_ALREADY_IN_QUEUE` | YES — `test_join_queue_already_in_queue`, `test_ec4_player_cannot_be_in_multiple_queues` |
| `CONFLICT_PLAYER_IN_MATCH` | YES — `test_join_queue_player_in_active_match`, `test_conflict_error_includes_match_id` |
| `VALIDATION_NOT_IN_QUEUE` | YES — `test_find_match_not_in_queue` |
| `VALIDATION_INVALID_INPUT` | NO — No test exercises the invalid pool type path |
| `FORBIDDEN_POOL_RESTRICTED` | YES — `test_join_queue_bot_in_human_pool_forbidden`, `test_join_queue_human_in_bot_pool_forbidden`, `test_ec6_bot_in_human_pool_rejected`, `test_forbidden_error_has_context` |
| `INTERNAL_MATCHMAKING_ERROR` | YES — `test_find_match_creation_fails_compensates`, `test_internal_error_on_match_creation_failure`, `test_ec3_match_creation_fails_compensates` |
| `INTERNAL_CACHE_ERROR` | NO — No test exercises Redis operation failure |

- [P3] [test_matchmaking_service.py] Missing error path test for `VALIDATION_INVALID_INPUT` (invalid pool type). -> Add a test that passes an invalid pool type value.
- [P3] [test_matchmaking_service.py] Missing error path test for `INTERNAL_CACHE_ERROR` (Redis operation failure). -> Add a test where a queue repository method raises an error simulating Redis failure, and verify it's wrapped in `INTERNAL_CACHE_ERROR`.

**Note:** The `INTERNAL_CACHE_ERROR` wrapping is not actually implemented in the service code — the service does not catch general Redis errors and wrap them. This may be an artifact design intent that was not implemented. Escalation may be needed.

### P3-08: Async Tests Properly Structured
**PASS** — All 47 async test methods are `async def test_*` with `@pytest.mark.asyncio` decorators. Service calls are properly `await`ed. No `asyncio.run()` in test files.

### P3-09: Type Hints on Service Methods
**PASS** — All public and private service methods have full parameter and return type annotations.

---

## Summary

| Priority | Count | Details |
|----------|-------|---------|
| P1 | 1 | Raw data access in CLI composition helper (`_PasswordStore`) |
| P2 | 6 | Non-blocking escalation: 6 config key name mismatches with configuration.md |
| P3 | 9 | File length (1), function length (3), magic numbers (5), unused import (1), missing error path tests (2) |

### P1 Findings (Must Fix)

1. **[P1-07] [matchmaking_commands.py:127-153]** Inline `_PasswordStore` class with raw `select()`, `update()`, and `session.execute()` calls inside the CLI commands file. -> Move to a proper repository in `src/data/repositories/` or use the composition root to wire this dependency.

### Escalation Items (Non-blocking)

1. **[ESCALATION] [P2-01]** Six matchmaking config key names do not match configuration.md registered keys. The artifact declares different names than what configuration.md registers. The Orchestrator should reconcile these naming differences in one place (either update configuration.md or update the artifact/code).

2. **[ESCALATION] [P3-07]** The artifact specifies `INTERNAL_CACHE_ERROR` for Redis operation failures, but the service code does not implement this wrapping. The Orchestrator should clarify whether this error wrapping should be added to the service or removed from the artifact.

### Recommendation

**Corrections needed.** The module has one P1 violation (raw data access in CLI composition) that must be addressed. The P2 config key mismatches are Orchestrator-level reconciliation items. The P3 findings (file length, function length, magic numbers, missing tests) are quality improvements that should be addressed if time permits in Stage 4.
