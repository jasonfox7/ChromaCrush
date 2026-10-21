# Energy Module -- Stage 3 Compliance Review (P1-P3)

**Module:** energy
**Reviewer:** Karen (Stage 3)
**Date:** 2026-02-07
**Checklist version:** 1.0

---

## Summary

- **P1 findings:** 0
- **P2 findings:** 2
- **P3 findings:** 5
- **Total findings:** 7

---

## P1 Findings (Framework Rules)

### P1-01: No Direct Service Instantiation -- PASS

All core services arrive via `__init__`. The `from src.core.errors import AppError` in `service.py:17` is used for `except AppError: raise` (re-raise pattern), which is an allowed exception per the checklist.

### P1-02: No Direct Environment Access -- PASS

No `os.environ`, `os.getenv`, or `import os` found in any source file.

### P1-03: No Bare Raises -- PASS

All errors flow through `self._errors.*()` factory methods. The `except AppError: raise` pattern in the artifact's error propagation section is a bare re-raise of a caught exception, which is explicitly allowed by the checklist.

### P1-04: No UI / Rendering Logic in Modules -- PASS

No click, rich, print, sys.stdout, or HTTP response logic found in `src/modules/energy/`.

### P1-05: No Raw Data Access in Business Logic -- PASS

The grep matches for `update(` in `service.py` are all calls to `self._energy_repo.update(...)`, which is the injected repository protocol interface. No SQLAlchemy, Redis, or raw SQL used in service code. Redis access is through the injected Redis client interface (`self._redis.get()`, `self._redis.exists()`, `self._redis.setex()`).

### P1-06: Async Matches Artifact Spec -- PASS

Artifact specifies all public methods as `async def`. Implementation matches exactly:
- `get_energy` -- async def
- `consume_heart` -- async def
- `can_play` -- async def
- `apply_pending_regeneration` -- async def
- `get_time_to_next_heart` -- async def
- `record_login` -- async def
- `get_streak` -- async def
- `grant_bonus_hearts` -- async def
- `refund_heart` -- async def

No hidden `asyncio.run()` or `asyncio.create_task()` in module source.

### P1-07: CLI Exercises Same Code Paths -- PASS

All CLI commands in `energy_commands.py` use `_run_async()` which builds an `EnergyService` via `_build_energy_service()` and calls the same service methods as the primary presentation layer. No direct repository calls or business logic duplication in CLI commands.

---

## P2 Findings (Data Layer & Config Compliance)

### P2-01: Config Keys Match Registered Namespaces -- PARTIAL FAIL

`[P2-01] src/modules/energy/service.py:79-92 config keys energy.bonus_overflow_limit, energy.streak_reward_threshold_7, energy.streak_reward_threshold_14, energy.streak_reward_threshold_30, energy.streak_reward_repeat_interval not in registered namespace -> fix: Orchestrator escalation to update configuration.md with artifact-declared keys`

The registered `energy` namespace (configuration.md section 2) only defines `energy.max_hearts` and `energy.regen_interval_minutes`. The additional keys are all declared in the artifact (section 3.1) but not in configuration.md. Per checklist guidance, these are Orchestrator escalation items, not blocking fixes.

### P2-02: Repository Pattern Followed -- PASS

Service receives `player_service` and `energy_repo` via `__init__`. Service calls `self._player_service.get_energy_state()` for reads and `self._energy_repo.update()` for writes. Redis operations go through the injected `self._redis` client. No raw data access in service.py.

### P2-03: Data Ownership Respected -- PASS

The energy module writes to `energy_states` via `self._energy_repo`, which is shared ownership with the player module per the data ownership matrix. This shared access pattern is explicitly documented in the artifact (section 4.1) and the dependency graph. Reads go through `PlayerServiceProtocol`.

### P2-04: Transactions at Service Layer -- PARTIAL FAIL

`[P2-04] src/modules/energy/service.py:146-221 consume_heart() calls apply_pending_regeneration() then _energy_repo.update() as separate operations without an explicit transaction boundary -> fix: wrap the regen-then-consume sequence in a single session/transaction context to ensure atomicity per artifact spec`

The artifact (section 4.4) specifies that `consume_heart` must be a "Single transaction" with "atomic: check + update in one operation." The implementation calls `apply_pending_regeneration()` (which may do its own repo update) followed by a separate `_energy_repo.update()`. These are not wrapped in a single transaction boundary (`async with self._data_ctx.session()`), which could allow race conditions between the check and the consume step.

Note: The energy service does not receive a `DataContext` in its constructor, so it cannot create explicit transaction boundaries. This is a design-level gap that may need Orchestrator attention.

---

## P3 Findings (Best Practices & Testing)

### P3-01: Service File Length -- FAIL

`[P3-01] src/modules/energy/service.py:1-667 service.py is 667 lines, exceeds 500-line hard limit -> fix: extract EnergyInfo construction into a helper, extract record_login and grant_bonus_hearts into separate internal modules (e.g., energy/login_handler.py, energy/bonus_handler.py)`

### P3-02: Function Length -- FAIL

`[P3-02] src/modules/energy/service.py:146-221 consume_heart() is 76 lines, exceeds 50-line limit -> fix: extract EnergyInfo construction (repeated in multiple methods) into a shared _build_energy_info() helper`

`[P3-02] src/modules/energy/service.py:244-306 apply_pending_regeneration() is 63 lines, exceeds 50-line limit -> fix: extract EnergyInfo construction into _build_energy_info() helper`

`[P3-02] src/modules/energy/service.py:349-455 record_login() is 107 lines, exceeds 50-line limit -> fix: extract streak update logic, bonus granting, and EnergyInfo construction into smaller helpers`

`[P3-02] src/modules/energy/service.py:495-621 grant_bonus_hearts() is 127 lines, exceeds 50-line limit -> fix: extract idempotency check, bonus calculation, and EnergyInfo construction into helpers`

### P3-03: Constructor Parameters -- PASS

`__init__` has 6 parameters (config, logger, errors, player_service, energy_repo, redis). Within the 6-parameter limit.

### P3-04: No Magic Numbers -- FAIL

`[P3-04] src/modules/energy/service.py:565 magic number 86400 (seconds in 24 hours) used for Redis TTL -> fix: define as named constant IDEMPOTENCY_TTL_SECONDS = 86400 or read from config`

### P3-05: Tests Use Injected Mocks -- PASS

No `@mock.patch`, `@patch`, `mock.patch()`, or `monkeypatch.setattr` found in test files. All dependencies are injected through `__init__` via custom mock classes (MockPlayerService, MockEnergyRepo, MockRedis). Follows the correct injection pattern.

### P3-06: Test Naming Conventions -- PASS

All test methods follow `test_{method}_{scenario}` pattern. Test classes follow `Test{ClassName}` pattern. Mock classes follow `Mock{ProtocolName}` pattern. Fixtures are descriptive `snake_case`.

### P3-07: Error Path Tests Exist -- PASS (with note)

Error codes from the artifact and their test coverage:
- NOT_FOUND_PLAYER: 2 tests (test_get_player_not_found, test_refund_player_not_found)
- FORBIDDEN_INSUFFICIENT_ENERGY: 1 test (test_consume_insufficient_hearts)
- VALIDATION_INVALID_INPUT: 2 tests (test_consume_invalid_amount, test_grant_invalid_amount)
- CONFLICT_DUPLICATE_BONUS: **Implementation deviation** -- the artifact (section 3.3) specifies raising `CONFLICT_DUPLICATE_BONUS` when an idempotency key is already claimed, but the implementation returns `BonusGrantResult(granted=False, already_claimed=True)` instead of raising. The test (`test_grant_idempotency_duplicate`) verifies the return-value behavior, not the error-raise behavior. This is a design deviation from the artifact that should be documented or reconciled.

### P3-08: Async Tests Properly Structured -- PASS

All async test methods use `@pytest.mark.asyncio` and `async def`. All service calls are properly `await`ed. No `asyncio.run()` inside test methods.

### P3-09: Type Hints on Service Methods -- PASS

All public and private methods have full type annotations on parameters and return types. The `redis` parameter is typed as `Any` in `__init__` (no RedisProtocol defined), which is a minor gap but not a type hint omission.

---

## Changelog

| Date | Version | Change |
|------|---------|--------|
| 2026-02-07 | 1.0 | Initial Stage 3 P1-P3 review |
