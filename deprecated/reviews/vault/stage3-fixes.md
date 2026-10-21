# Stage 3 — P1-P3 Compliance Report: vault

**Reviewer:** Karen Agent
**Date:** 2026-02-07
**Module:** vault
**Files reviewed:**
- `src/modules/vault/service.py` (1019 lines)
- `src/modules/vault/protocols.py`
- `src/modules/vault/dto.py`
- `src/modules/vault/raid_engine.py`
- `src/modules/vault/collection.py`
- `src/modules/vault/__init__.py`
- `tests/unit/modules/vault/test_vault_service.py`
- `tests/unit/modules/vault/test_raid_engine.py`
- `tests/unit/modules/vault/test_collection.py`
- `src/cli/commands/vault_commands.py`

---

## P1 Findings (Framework Rule Violations)

### P1-01: No Direct Service Instantiation
**PASS** — No matches for prohibited patterns. All core services arrive via `__init__` injection. TYPE_CHECKING imports of protocol types are used correctly.

### P1-02: No Direct Environment Access
**PASS** — No `os.environ`, `os.getenv`, or `import os` found in module source.

### P1-03: No Bare Raises
**PASS** — All errors raised through `self._errors.validation(...)`, `self._errors.not_found(...)`, `self._errors.conflict(...)`, `self._errors.forbidden(...)`, or `self._errors.internal(...)`. No bare exception raises.

### P1-04: No UI/Rendering Logic in Modules
**PASS** — No click, rich, print, sys.stdout/stderr, flask, or fastapi imports in `src/modules/vault/`. Module returns dataclasses only.

### P1-05: No Raw Data Access in Business Logic
**PASS** — All data access goes through injected repository protocol interfaces. The `delete()` and `update()` calls in service.py are repository method invocations, not raw SQL.

### P1-06: Async Matches Artifact Spec
**PASS** — All public protocol methods in `protocols.py` are `async def`. The service implementation matches. No `asyncio.run()` or `asyncio.create_task()` in module code. No hidden async patterns.

**Note:** The artifact specifies `check_set_complete` as a public async method (artifact section 2.1), but it is NOT implemented in `service.py` or `protocols.py`. This is a P0 interface gap that should have been caught in Stage 2. Not flagging here since P0 is out of scope for Stage 3.

### P1-07: CLI Exercises Same Code Paths
**PASS** — All CLI commands in `vault_commands.py` call VaultService methods. No direct repository calls or business logic duplication in CLI commands. The `_build_vault_service` function instantiates repositories and wires the service, which is the expected composition-root-like pattern for CLI bridges.

---

## P2 Findings (Data/Config Compliance)

### P2-01: Config Keys Match Registered Namespaces

**FLAG (non-blocking)** — Vault uses `vault.*` config namespace (7 keys: `vault.shield_duration_hours`, `vault.raid_cooldown_hours`, `vault.raid_energy_cost`, `vault.raid_success_base_chance`, `vault.empty_vault_protection`, `vault.legendary_steal_chance_modifier`, `vault.max_artifacts_per_player`). The `vault` namespace is NOT listed in the configuration.md registered namespaces table. The artifact declares these keys, so this is an Orchestrator escalation item to add the `vault` namespace to configuration.md. **Not a code fix.**

### P2-02: Repository Pattern Followed
**PASS** — Service receives 4 repository protocols via `__init__`. All data access flows through `self._vault_artifact_repo`, `self._vault_shield_repo`, `self._artifact_definition_repo`, `self._raid_log_repo`. Service never imports SQLAlchemy or Redis.

### P2-03: Data Ownership Respected
**PASS** — Vault writes only to its owned tables (vault_artifacts, vault_shields, artifact_definitions, raid_logs). Player data is read through `PlayerServiceProtocol`.

### P2-04: Transactions at Service Layer

[P2-04] [service.py:all] Artifact specifies DataContext injection for transaction management, but VaultService does not receive or use DataContext. All operations rely on individual repository calls without explicit transaction boundaries. -> Inject DataContext via `__init__` and wrap multi-step operations (especially `attempt_raid` which does raid log creation + artifact transfer) in `async with self._data_ctx.session()` blocks.

---

## P3 Findings (Best Practices / Testing)

### P3-01: Service File Length

[P3-01] [service.py:1-1019] Service file is 1019 lines, exceeding the 500-line hard limit. -> Extract raid logic into a separate `raid_service.py` or internal helper module. Shield operations and collection tracking could also be extracted into focused helper classes.

### P3-02: Function Length

[P3-02] [service.py:612-820] `attempt_raid` is approximately 208 lines, far exceeding the 50-line limit. -> Break into smaller methods: `_validate_raid_preconditions`, `_select_and_steal_artifact`, `_create_raid_result`.

[P3-02] [service.py:822-917] `can_raid` is approximately 95 lines, exceeding the 50-line limit. -> Extract eligibility checks into smaller private methods.

[P3-02] [service.py:249-313] `get_vault_summary` is approximately 64 lines, exceeding the 50-line limit. -> Extract set completion scanning into a helper.

### P3-03: Constructor Parameters
**PASS** — `__init__` has 8 parameters (self excluded). Artifact specifies 8 dependencies. Within acceptable range per checklist note.

### P3-04: No Magic Numbers

[P3-04] [service.py:215] `limit > 100` — validation bound should be a named constant. -> Define `MAX_PAGE_LIMIT = 100` or read from config.

### P3-05: Tests Use Injected Mocks

[P3-05] [test_vault_service.py:11,971-973,996-998] Tests import `from unittest.mock import patch` and use `with patch("src.modules.vault.service.calculate_raid_success", return_value=...)` to control raid outcomes. This patches a module-level import inside the service, violating the injected-mocks testing standard. -> Refactor `calculate_raid_success` to be injectable (e.g., pass as a dependency or make `attempt_raid` accept an optional RNG/strategy parameter) so tests can control behavior through injection rather than patching.

[P3-05] [test_raid_engine.py:12,47-89] Tests use `with patch("src.modules.vault.raid_engine.random.random", ...)` to control random outcomes. This is borderline acceptable for pure-function testing of `calculate_raid_success` since `random.random` is a stdlib global. However, it still violates the letter of P3-05. -> Consider making `calculate_raid_success` accept an optional `rng` parameter (similar to `select_raid_target_artifact` which already does this correctly).

### P3-06: Test Naming Conventions
**PASS** — All test files follow `test_*.py`, classes follow `Test*`, methods follow `test_*_*` pattern. Fixtures use snake_case.

### P3-07: Error Path Tests Exist

[P3-07] [tests/unit/modules/vault/] Missing test for `FORBIDDEN_INSUFFICIENT_ENERGY` error path (raid energy cost check). The artifact specifies this error but the service does not implement energy consumption (no energy module dependency injected). -> This is an implementation gap, not just a test gap. The service needs energy consumption logic per the artifact, and a test to cover it.

**Covered error paths:** VALIDATION_INVALID_INPUT (artifact type, limit, self-raid, duration), NOT_FOUND_PLAYER, NOT_FOUND_ARTIFACT, FORBIDDEN_VAULT_PROTECTED, CONFLICT_SHIELD_ALREADY_ACTIVE, CONFLICT_RAID_COOLDOWN. All tested.

### P3-08: Async Tests Properly Structured
**PASS** — All async test methods use `async def test_*` with `@pytest.mark.asyncio`. Service calls are properly awaited. No `asyncio.run()` in tests.

### P3-09: Type Hints on Service Methods
**PASS** — All public methods have parameter and return type hints.

---

## Summary

| Priority | Count | Details |
|----------|-------|---------|
| P1       | 0     | All framework rules pass |
| P2       | 1     | Missing DataContext injection for transaction management |
| P3       | 7     | File length (1), function length (3), magic number (1), test patching (2) |

**Note:** The `vault` config namespace needs to be added to configuration.md by the Orchestrator (non-blocking escalation).
