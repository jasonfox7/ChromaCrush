# Auth Module -- Stage 3 Compliance Review (P1-P3)

**Module:** auth
**Reviewer:** Karen (Stage 3)
**Date:** 2026-02-07
**Checklist version:** 1.0

---

## Summary

- **P1 findings:** 1
- **P2 findings:** 2
- **P3 findings:** 5
- **Total findings:** 8

---

## P1 Findings (Framework Rules)

### P1-01: No Direct Service Instantiation -- PASS

All core services arrive via `__init__`. The `from src.core.errors import AppError` in `jwt_handler.py:14` is used for `raise AppError(...)` which is allowed per the checklist (constructing with proper error code).

### P1-02: No Direct Environment Access -- PASS

No `os.environ`, `os.getenv`, or `import os` found in any source file.

### P1-03: No Bare Raises -- PASS

All errors flow through `self._errors.*()` factory methods or `raise AppError(...)` with proper error codes. No bare `raise Exception()`, `raise ValueError()`, etc.

### P1-04: No UI / Rendering Logic in Modules -- PASS

No click, rich, print, sys.stdout, or HTTP response logic found in `src/modules/auth/`.

### P1-05: No Raw Data Access in Business Logic -- PASS

No SQLAlchemy, Redis, or raw SQL found in service/business logic files. All data access goes through injected repositories and the Redis client interface.

### P1-06: Async Matches Artifact Spec -- PASS

Artifact specifies all methods except `hash_password` and `verify_password` are `async def`. Implementation matches exactly. No hidden `asyncio.run()` or `asyncio.create_task()` in module source.

### P1-07: CLI Exercises Same Code Paths -- FAIL

`[P1-07] src/cli/commands/auth_commands.py:177-192 hash-password and verify-password CLI commands bypass AuthService -> fix: route through AuthService.hash_password() and AuthService.verify_password() which include password strength validation`

The `hash-password` CLI command (line 180) calls `do_hash_password(password)` from `password_handler` directly, bypassing `AuthService.hash_password()`. The `AuthService.hash_password()` method includes password strength validation (`VALIDATION_WEAK_PASSWORD` check) that the CLI command does not exercise. Similarly, `verify-password` calls the raw utility function.

The CLI commands should use the full `AuthService` path to exercise the same code paths as the primary presentation layer, per P1-07.

---

## P2 Findings (Data Layer & Config Compliance)

### P2-01: Config Keys Match Registered Namespaces -- PARTIAL FAIL

`[P2-01] src/modules/auth/service.py:88 config key "auth.access_token_expiry_minutes" not in registered namespace; registered key is "auth.jwt_expiry_minutes" -> fix: reconcile key name with configuration.md (Orchestrator escalation)`

The registered `auth` namespace (configuration.md section 2) defines `auth.jwt_expiry_minutes`, but the implementation uses `auth.access_token_expiry_minutes`. These are different key names.

`[P2-01] src/modules/auth/service.py:87-103 keys auth.jwt_algorithm, auth.access_token_expiry_minutes, auth.refresh_token_expiry_days, auth.api_key_length, auth.bcrypt_rounds, auth.password_min_length, auth.rate_limit_requests, auth.rate_limit_window_seconds, auth.max_sessions_per_player not in registered namespace -> fix: Orchestrator escalation to update configuration.md with artifact-declared keys`

These keys are all declared in the artifact (section 3.1) but not in the registered namespace table in configuration.md. Per checklist guidance, these are Orchestrator escalation items, not blocking fixes.

### P2-02: Repository Pattern Followed -- PASS

Service receives `session_repo`, `api_key_repo`, and `password_store` via `__init__`. Service calls `self._session_repo.*()`, `self._api_key_repo.*()`, etc. No raw data access in service.py.

### P2-03: Data Ownership Respected -- PASS

Auth module writes to `sessions` and `api_keys` tables (owned). Reads player data via injected `PlayerServiceProtocol`. No direct writes to player-owned tables.

### P2-04: Transactions at Service Layer -- PASS

No `.commit()` or `.rollback()` found in module source. The auth service does not have an explicit DataContext/session manager pattern because it delegates to repository methods. This is consistent with the implementation -- repositories handle the session management internally.

---

## P3 Findings (Best Practices & Testing)

### P3-01: Service File Length -- FAIL

`[P3-01] src/modules/auth/service.py:1-705 service.py is 705 lines, exceeds 500-line hard limit -> fix: extract _create_session, _validate_jwt, _validate_api_key, _get_rate_limit_status into separate internal modules (e.g., auth/token_validator.py, auth/session_manager.py, auth/rate_limiter.py)`

### P3-02: Function Length -- FAIL

`[P3-02] src/modules/auth/service.py:111-186 authenticate() is 75 lines, exceeds 50-line limit -> fix: extract session limit enforcement into a helper method`

`[P3-02] src/modules/auth/service.py:301-362 create_api_key() is 61 lines, exceeds 50-line limit -> fix: extract key generation and storage into a helper`

`[P3-02] src/modules/auth/service.py:439-500 record_api_request() is 61 lines, exceeds 50-line limit -> fix: extract Redis increment logic into a helper`

`[P3-02] src/modules/auth/service.py:521-582 _create_session() is 61 lines, exceeds 50-line limit -> fix: extract token creation and session storage into smaller helpers`

`[P3-02] src/modules/auth/service.py:623-681 _validate_api_key() is 58 lines, exceeds 50-line limit -> fix: extract candidate iteration logic into a helper`

### P3-03: Constructor Parameters -- PASS (deferred to artifact)

`__init__` has 8 parameters. The artifact specifies all 8 dependencies. Per checklist note: "If the artifact specifies the constructor signature, defer to the artifact."

### P3-04: No Magic Numbers -- PASS (minor)

`src/modules/auth/service.py:318` uses `255` for description length validation and `service.py:580` uses `* 60` for minutes-to-seconds conversion. These are minor and well-documented in context. The `255` could be a constant (`MAX_DESCRIPTION_LENGTH`) but is not blocking.

### P3-05: Tests Use Injected Mocks -- PASS

No `@mock.patch`, `@patch`, `mock.patch()`, or `monkeypatch.setattr` found in test files. All dependencies are injected through `__init__` via custom mock classes (MockPlayerService, MockPasswordStore, MockSessionRepository, MockApiKeyRepository). Follows the correct injection pattern.

### P3-06: Test Naming Conventions -- PASS

All test methods follow `test_{method}_{scenario}` pattern. Test classes follow `Test{ClassName}` pattern. Mock classes follow `Mock{ProtocolName}` pattern. Fixtures are descriptive `snake_case`.

### P3-07: Error Path Tests Exist -- PASS

All 12 error codes from the artifact have at least one corresponding test:
- AUTH_INVALID_CREDENTIALS: 4 tests
- AUTH_TOKEN_INVALID: 4 tests
- AUTH_TOKEN_EXPIRED: 1 test (jwt_handler)
- AUTH_API_KEY_INVALID: 1 test
- AUTH_API_KEY_REVOKED: 1 test
- RATE_LIMIT_API_KEY: 1 test
- NOT_FOUND_PLAYER: 3 tests
- NOT_FOUND_API_KEY: 2 tests
- FORBIDDEN_NOT_BOT: 1 test
- FORBIDDEN_NOT_KEY_OWNER: 1 test
- VALIDATION_WEAK_PASSWORD: 1 test
- VALIDATION_INVALID_INPUT: 1 test

### P3-08: Async Tests Properly Structured -- PASS

All async test methods use `@pytest.mark.asyncio` and `async def`. All service calls are properly `await`ed. No `asyncio.run()` inside test methods.

### P3-09: Type Hints on Service Methods -- PASS

All public and private methods have full type annotations on parameters and return types. The `redis` parameter is typed as `Any` in `__init__` (no RedisProtocol defined), which is a minor gap but not a type hint omission.

---

## Changelog

| Date | Version | Change |
|------|---------|--------|
| 2026-02-07 | 1.0 | Initial Stage 3 P1-P3 review |
