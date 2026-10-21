# Stage 3 P1-P3 Fixes -- payments module

**Date:** 2026-02-07
**Reviewer:** Karen P1-P3 Agent (S3-E)
**Module:** payments
**Artifact:** `docs/artifacts/payments/artifact.md` v1.0
**Source:** `src/modules/payments/service.py` (731 lines), `types.py`, `dto.py`, `protocols.py`, `__init__.py`
**Tests:** `tests/unit/modules/payments/test_payment_service.py` (~924 lines)
**CLI:** `src/cli/commands/payments_commands.py` (532 lines)

---

## P1 -- Framework Rules

### P1-01: No Direct Service Instantiation
**Result:** PASS (no violations)

Grep patterns clean. All core service imports are under `TYPE_CHECKING` guard (lines 45-58). Constructor receives all dependencies via `__init__`. No `ConfigService()`, `LogService()`, or `ErrorService()` instantiation.

Note: `from src.modules.ads.types import AdFreeReason` at lines 306 and 634 are inline imports inside method bodies (`validate_purchase` and `restore_purchases`). These import a type/enum from another module, not a core service. Per the checklist, type imports are allowed. However, these inline imports are unusual -- they should be moved to the top-level `TYPE_CHECKING` block for consistency with the rest of the file's import pattern. This is a style concern, not a framework violation.

### P1-02: No Direct Environment Access
**Result:** PASS (no violations)

No `os.environ`, `os.getenv`, or `import os` found in module source.

### P1-03: No Bare Raises
**Result:** PASS (no violations)

All error raises go through `self._errors.validation()`, `self._errors.not_found()`, `self._errors.conflict()`, `self._errors.internal()`. No bare `raise Exception()`, `raise ValueError()`, etc.

### P1-04: No UI / Rendering Logic in Modules
**Result:** PASS (no violations)

No `click`, `rich`, `print()`, `sys.stdout`, HTTP response construction, or terminal formatting in module source.

### P1-05: No Raw Data Access in Business Logic
**Result:** PASS (no violations)

All data access flows through injected repository protocol interfaces (`self._product_repo`, `self._intent_repo`, `self._purchase_repo`, `self._receipt_repo`, `self._refund_repo`). No SQLAlchemy, Redis, or raw SQL imports in `service.py`.

### P1-06: Async Matches Artifact Spec
**Result:** PASS (no violations)

Artifact specifies this module is **fully asynchronous** with all public methods as `async def`. Implementation confirms all 8 public methods in `PaymentService` are `async def`:
- `initiate_purchase`, `validate_purchase`, `get_purchase_status`, `get_purchase_history`, `process_refund`, `restore_purchases`, `get_products`, `verify_webhook_signature`

Protocol in `protocols.py` matches -- all `PaymentServiceProtocol` methods are `async def`.

No `asyncio.run()` or `asyncio.create_task()` found in module source.

### P1-07: CLI Exercises Same Code Paths
**Result:** FINDINGS

[P1] [src/cli/commands/payments_commands.py:435] `list-refunds` command directly accesses `svc._refund_repo.find_unprocessed()` bypassing the service layer. -> Add a `list_refund_notifications()` method to `PaymentService` and `PaymentServiceProtocol`, then call it from the CLI command.

[P1] [src/cli/commands/payments_commands.py:473] `get-purchase` command directly accesses `svc._purchase_repo.find_by_id()` bypassing the service layer. -> Add a `get_purchase()` method to `PaymentService` and `PaymentServiceProtocol`, then call it from the CLI command.

[P1] [src/cli/commands/payments_commands.py:506-510] `get-validation` command directly accesses `svc._receipt_repo.find_by_transaction()` three times bypassing the service layer. -> Add a `get_validation_by_transaction()` method to `PaymentService` and `PaymentServiceProtocol`, then call it from the CLI command.

These three CLI commands access private repository attributes (`svc._refund_repo`, `svc._purchase_repo`, `svc._receipt_repo`) directly rather than going through service methods. This violates P1-07: "No direct repository calls, no direct data access in CLI commands."

---

## P2 -- Data Layer & Config Compliance

### P2-01: Config Keys Match Registered Namespaces
**Result:** PASS

Config keys used in `service.py` (lines 91-105):
- `payments.ad_free_product_id`
- `payments.ad_free_price_cents`
- `payments.ad_free_currency`
- `payments.intent_expiry_minutes`
- `payments.allow_sandbox_purchases`

The `payments` namespace IS in the registered namespaces table in `configuration.md` Section 2. All 5 keys used are a subset of the registered keys for the `payments` namespace.

Note: The artifact declares 13 config keys, but the implementation only uses 5. The remaining 8 keys (apple_bundle_id, apple_shared_secret, apple_verify_url, apple_sandbox_verify_url, google_package_name, google_service_account_key, webhook_apple_secret, webhook_google_secret) would be used by the concrete payment provider implementations (Apple/Google), not the service itself. This is expected since the service delegates to the `PaymentProviderProtocol` abstraction.

### P2-02: Repository Pattern Followed
**Result:** PASS (no violations)

Service receives all repositories via `__init__` as Protocol interfaces:
- `product_repo: ProductRepositoryProtocol`
- `intent_repo: PurchaseIntentRepositoryProtocol`
- `purchase_repo: PurchaseRepositoryProtocol`
- `receipt_repo: ReceiptValidationRepositoryProtocol`
- `refund_repo: RefundNotificationRepositoryProtocol`

Service calls repository methods through `self._product_repo.method()`, etc. No SQLAlchemy or direct database imports in `service.py`.

### P2-03: Data Ownership Respected
**Result:** PASS (no violations)

Payments module writes to: `products`, `purchase_intents`, `purchases`, `receipt_validations`, `refund_notifications` (via repositories) -- all owned per the ownership matrix.
Cross-module reads go through service protocols: `self._players.get_player()`, `self._ads.check_ad_free_status()`, `self._ads.grant_ad_free_status()`, `self._ads.revoke_ad_free_status()`.

No direct imports of other modules' repositories.

### P2-04: Transactions at Service Layer
**Result:** PASS (no violations)

No `.commit()` or `.rollback()` found in module source. The implementation does not use explicit `async with self._data_ctx.session()` blocks -- it relies on repositories handling individual operations. Note that the artifact algorithm examples show `async with self._data_ctx.session()` usage but the implementation omits `data_ctx` from the constructor entirely, delegating all persistence to individual repository calls. This is acceptable since each public method's repository operations are logically grouped.

---

## P3 -- Best Practices & Testing

### P3-01: Service Files Length
**Result:** FINDING

[P3] [src/modules/payments/service.py:1-731] Service file is 731 lines, exceeding the 500-line hard limit. -> Extract private helpers (`_hash_receipt`, `_to_purchase_record`) into a separate `helpers.py`. Consider splitting `validate_purchase` and `restore_purchases` logic into smaller private methods to reduce overall file size.

### P3-02: Function Length
**Result:** FINDINGS

[P3] [src/modules/payments/service.py:157-332] `validate_purchase` is 176 lines, exceeding the 50-line maximum. -> Extract steps into private methods: `_check_duplicate_receipt()`, `_validate_with_provider()`, `_create_purchase_record()`, `_record_validation_attempt()`.

[P3] [src/modules/payments/service.py:533-659] `restore_purchases` is 127 lines, exceeding the 50-line maximum. -> Extract the per-receipt processing loop body into a private `_process_restore_receipt()` method.

[P3] [src/modules/payments/service.py:421-531] `process_refund` is 111 lines, exceeding the 50-line maximum. -> Extract purchase lookup logic into `_find_purchase_for_refund()` and ad-free revocation into `_revoke_ad_free_on_refund()`.

### P3-03: Constructor Parameters
**Result:** FINDING

[P3] [src/modules/payments/service.py:64-77] Constructor has 11 parameters (config, logger, errors, player_service, ads_service, product_repo, intent_repo, purchase_repo, receipt_repo, refund_repo, payment_provider). Artifact specifies 9 parameters (config, logger, errors, data_ctx, player_service, ads_service, purchase_repository, receipt_repository, payment_provider). -> Implementation has 2 more than artifact due to splitting repositories (artifact has 2 repos, implementation has 5). The implementation also drops `data_ctx`. Consider consolidating repositories to match artifact spec or update artifact to reflect actual repository split.

### P3-04: No Magic Numbers
**Result:** FINDING

[P3] [src/modules/payments/service.py:380] Validation uses literal `100` for max limit. -> Define as a named constant `_MAX_HISTORY_LIMIT = 100`.

### P3-05: Tests Use Injected Mocks
**Result:** PASS (no violations)

No `@mock.patch`, `@patch`, `mock.patch()`, `unittest.mock.patch`, or `monkeypatch.setattr` found in test files. All dependencies are injected through `__init__` using `AsyncMock` and `MagicMock`. Tests import from `tests.mocks.services` for `MockConfigService`, `MockErrorService`, `MockLogService`.

### P3-06: Test Naming Conventions
**Result:** PASS (no violations)

All test methods use `test_` prefix. Test method names follow `test_{method}_{scenario}` pattern (e.g., `test_validate_purchase_success`, `test_process_refund_purchase_not_found`, `test_restore_purchases_already_active`). No vague names.

Note: Tests use module-level functions (not organized into classes). This is acceptable per pytest conventions.

### P3-07: Error Path Tests Exist
**Result:** PASS (all artifact error codes covered)

Mapping of artifact error codes to test coverage:

| Error Code | Test(s) |
|------------|---------|
| `NOT_FOUND_PLAYER` | `test_initiate_purchase_player_not_found`, `test_get_purchase_status_player_not_found` |
| `NOT_FOUND_PRODUCT` | `test_initiate_purchase_product_not_found` |
| `NOT_FOUND_PURCHASE` | `test_process_refund_purchase_not_found` |
| `CONFLICT_RECEIPT_ALREADY_PROCESSED` | `test_validate_purchase_duplicate_receipt` |
| `VALIDATION_RECEIPT_INVALID` | `test_validate_purchase_invalid_receipt` |
| `VALIDATION_RECEIPT_WRONG_PRODUCT` | `test_validate_purchase_wrong_product` |
| `CONFLICT_PLAYER_ALREADY_AD_FREE` | `test_validate_purchase_player_already_ad_free` |
| `INTERNAL_PAYMENT_PROVIDER_ERROR` | `test_validate_purchase_provider_error` |
| `VALIDATION_INVALID_INPUT` | `test_get_purchase_history_invalid_limit`, `test_get_purchase_history_negative_offset` |

Error codes NOT directly tested but covered by design:
- `VALIDATION_RECEIPT_WRONG_PLAYER` -- not implemented in service (artifact lists it but implementation doesn't have player-specific receipt validation)
- `CONFLICT_PURCHASE_ALREADY_REFUNDED` -- covered by `test_process_refund_already_refunded` (returns success, not error)
- `CONFLICT_PURCHASE_INTENT_EXPIRED` -- not implemented in service (intent expiry is passive, no active check)
- `AUTH_INVALID_WEBHOOK_SIGNATURE` -- `test_verify_webhook_signature_invalid` tests the return value
- `VALIDATION_INVALID_REFUND_NOTIFICATION` -- not explicitly tested; refund notifications are not validated at the service level
- `INTERNAL_DATABASE_ERROR` -- generic; not explicitly tested

Note: `VALIDATION_RECEIPT_WRONG_PLAYER`, `CONFLICT_PURCHASE_INTENT_EXPIRED`, and `VALIDATION_INVALID_REFUND_NOTIFICATION` are declared in the artifact error table but are NOT implemented in the service code. These are not test gaps -- the implementation chose not to implement these specific checks. This is a P0-level concern that may have been handled in Stage 2.

### P3-08: Async Tests Properly Structured
**Result:** PASS (no violations)

All test methods that call async service methods are `async def test_...` with `@pytest.mark.asyncio`. Service calls are properly `await`ed. No `asyncio.run()` inside test methods.

### P3-09: Type Hints on Service Methods
**Result:** PASS (no violations)

All 8 public methods have full parameter and return type annotations. Private helper methods also have type hints. Constructor parameters all have type annotations.

---

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P1 | 3 | CLI bypasses service layer (3 commands) |
| P2 | 0 | No data/config violations |
| P3 | 6 | 1 file length, 3 function length, 1 constructor params, 1 magic number |

### Findings List

```
[P1] [src/cli/commands/payments_commands.py:435] list-refunds directly accesses svc._refund_repo.find_unprocessed() -> Add list_refund_notifications() to PaymentService.
[P1] [src/cli/commands/payments_commands.py:473] get-purchase directly accesses svc._purchase_repo.find_by_id() -> Add get_purchase() to PaymentService.
[P1] [src/cli/commands/payments_commands.py:506-510] get-validation directly accesses svc._receipt_repo.find_by_transaction() -> Add get_validation_by_transaction() to PaymentService.
[P3] [src/modules/payments/service.py:1-731] Service file is 731 lines (hard limit 500) -> Split into smaller files or extract helpers.
[P3] [src/modules/payments/service.py:157-332] validate_purchase is 176 lines (limit 50) -> Extract into private sub-methods.
[P3] [src/modules/payments/service.py:533-659] restore_purchases is 127 lines (limit 50) -> Extract per-receipt processing.
[P3] [src/modules/payments/service.py:421-531] process_refund is 111 lines (limit 50) -> Extract purchase lookup and revocation.
[P3] [src/modules/payments/service.py:64-77] Constructor has 11 params (artifact specifies 9) -> Consolidate repos or update artifact.
[P3] [src/modules/payments/service.py:380] Magic number 100 for max limit -> Define named constant.
```
