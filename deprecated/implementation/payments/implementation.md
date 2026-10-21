# Payments Module Implementation

## Header
- **Author:** Coding Agent (payments)
- **Date:** 2026-02-06
- **Artifact Version:** 1.0
- **Status:** Complete

---

## Files Created

### Module Code (`src/modules/payments/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Module exports (all public types + service) |
| `types.py` | Enums (PaymentProvider, ProductType, PurchaseIntentStatus, PurchaseStatus), NewTypes (PurchaseId, PurchaseIntentId, ProductId), input dataclasses (PurchaseReceipt, RefundNotification), output dataclasses (PurchaseIntent, PurchaseResult, ReceiptValidationResult, PlayerPurchaseStatus, PurchaseRecord, RefundResult, RestoreResult, Product) |
| `dto.py` | Data transfer objects for repository operations (PurchaseIntentCreate/Update, PurchaseCreate/Update, ReceiptValidationCreate/Update, RefundNotificationCreate, PaginatedResult[T]) |
| `protocols.py` | Protocol interfaces: PaymentServiceProtocol, PaymentProviderProtocol, 5 repository protocols, 2 minimal dependency protocols (PlayerServiceProtocol, AdServiceProtocol) |
| `service.py` | PaymentService implementation with all 8 public async methods + _hash_receipt helper |

### ORM Models (`src/data/models/`)
| File | Table | Notes |
|------|-------|-------|
| `product.py` | `products` | String PK (not UUID), no UUIDMixin |
| `purchase_intent.py` | `purchase_intents` | UUIDMixin + TimestampMixin |
| `purchase.py` | `purchases` | UUIDMixin + TimestampMixin, unique constraint on (provider, transaction_id) |
| `receipt_validation.py` | `receipt_validations` | UUIDMixin only (custom created_at, no updated_at) |
| `refund_notification.py` | `refund_notifications` | UUIDMixin only (custom received_at) |

### Repositories (`src/data/repositories/`)
| File | Class |
|------|-------|
| `product_repository.py` | SQLAlchemyProductRepository |
| `purchase_intent_repository.py` | SQLAlchemyPurchaseIntentRepository |
| `purchase_repository.py` | SQLAlchemyPurchaseRepository |
| `receipt_validation_repository.py` | SQLAlchemyReceiptValidationRepository |
| `refund_notification_repository.py` | SQLAlchemyRefundNotificationRepository |

### Migration
| File | Description |
|------|-------------|
| `src/data/migrations/versions/008_payment_tables.py` | Creates all 5 tables with proper FKs, indexes, and constraints |

### CLI Commands (`src/cli/commands/payments_commands.py`)
| Command | Description |
|---------|-------------|
| `payments products` | List available products |
| `payments initiate` | Initiate purchase intent |
| `payments validate` | Validate purchase receipt |
| `payments status` | Check player purchase status |
| `payments history` | View purchase history |
| `payments restore` | Restore purchases |
| `payments simulate-refund` | Simulate refund notification |
| `payments list-refunds` | List refund notifications |
| `payments get-purchase` | Get purchase details |
| `payments get-validation` | Get validation details |

### Tests (`tests/unit/modules/payments/`)
| File | Tests |
|------|-------|
| `__init__.py` | Package marker |
| `test_payment_service.py` | 27 tests covering all 8 public methods + error paths |

---

## Deviations from Artifact

### 1. Service Constructor Signature
The artifact shows `purchase_repository` and `receipt_repository` as parameter names. The implementation uses more specific names: `product_repo`, `intent_repo`, `purchase_repo`, `receipt_repo`, `refund_repo` for clarity and to avoid ambiguity when there are 5 separate repository dependencies.

### 2. Data Context Session Pattern
The artifact shows `async with self._data_ctx.session() as session:` wrapping purchase creation and ad-free granting. The implementation delegates session management to the repositories (each repository method manages its own session), which is consistent with all other modules in the project (ads, vault, etc.).

### 3. ProductModel Primary Key
The `products` table uses a `VARCHAR(100)` primary key (e.g., `"chromacrush_ad_free"`) rather than a UUID. This follows the artifact's SQL schema exactly but means `ProductModel` does not use `UUIDMixin`. It uses its own `created_at`/`updated_at` columns.

### 4. ReceiptValidationModel Timestamps
The `receipt_validations` table has only `created_at` (no `updated_at`) since validation records are immutable. The `purchase_id` field can be updated via `ReceiptValidationUpdate` to link the validation to its purchase after creation.

### 5. PurchaseRecord Type
The artifact defines `receipt_data` and `validation_result` fields on `PurchaseRecord`. The implementation omits these for the domain object since they belong to the receipt_validations table, not the purchases table. The `is_sandbox` field is included instead, matching the actual database schema.

---

## Key Decisions

1. **Repository-per-table pattern**: Each of the 5 database tables gets its own repository implementation, following the ads module pattern.
2. **Mock stubs in CLI**: The CLI uses stub implementations for AdService and PaymentProvider to enable testing without requiring the full ads module dependency chain.
3. **Idempotent refund processing**: Already-refunded purchases return success (not error), following the artifact's EC-5 and EC-6 guidance.
4. **SHA-256 receipt hashing**: Uses Python's standard `hashlib.sha256` for duplicate detection, matching the artifact specification.
5. **Error propagation**: All errors flow through the injected `ErrorServiceProtocol`. Provider errors are caught and wrapped in `INTERNAL_PAYMENT_PROVIDER_ERROR`. Cross-module errors from player_service propagate unchanged.

---

## Compliance

- All dependencies via `__init__` injection
- All public methods are `async def`
- All errors through `ErrorServiceProtocol` (no bare raises)
- No `os.environ` or `os.getenv`
- No raw SQL in service.py
- Repository protocols defined in module's own `protocols.py`
- Follows existing project patterns (ads module, vault module)
