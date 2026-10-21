# Stage 2 P0 Fixes: payments

**Reviewer:** Karen P0 (Stage 2 Interface Compliance)
**Date:** 2026-02-06
**Files reviewed:**
- `src/modules/payments/protocols.py`
- `src/modules/payments/types.py`
- `src/modules/payments/dto.py`

**Reference documents:**
- `docs/guidance/interface-contracts.md` (Sections 1-2)
- `docs/artifacts/payments/artifact.md` (Public Interface & Outputs)

---

## Protocol Signature Checks

All `PaymentServiceProtocol` method signatures in `protocols.py` match the artifact exactly:
- `initiate_purchase(player_id, product_id) -> PurchaseIntent`: match
- `validate_purchase(player_id, receipt) -> PurchaseResult`: match
- `get_purchase_status(player_id) -> PlayerPurchaseStatus`: match
- `get_purchase_history(player_id, limit, offset) -> PaginatedResult[PurchaseRecord]`: match
- `process_refund(refund_notification) -> RefundResult`: match
- `restore_purchases(player_id, receipts) -> RestoreResult`: match
- `get_products() -> list[Product]`: match
- `verify_webhook_signature(payload, signature, provider) -> bool`: match

All methods are `async def`: confirmed.

No P0 issues found in protocol signatures.

---

## Type Alias Checks

- `PlayerId` imported from `src.core.types.game`: correct per interface-contracts.md Section 1.1
- `PurchaseId = NewType("PurchaseId", UUID)`: correct (module-specific opaque ID)
- `PurchaseIntentId = NewType("PurchaseIntentId", UUID)`: correct (module-specific opaque ID)
- `ProductId = NewType("ProductId", str)`: correct (module-specific opaque ID)

No P0 issues found in type aliases.

---

## DTO / Dataclass Shape Checks

### `PurchaseIntent`
Implementation (types.py:101-112) vs artifact (artifact.md:151-163):
- `intent_id: PurchaseIntentId`: match
- `player_id: PlayerId`: match
- `product_id: ProductId`: match
- `product_name: str`: match
- `price_cents: int`: match
- `currency: str`: match
- `status: PurchaseIntentStatus`: match
- `created_at: datetime`: match
- `expires_at: datetime`: match

PASS.

### `PurchaseResult`
Implementation (types.py:131-143) vs artifact (artifact.md:170-183):

[P0] [src/modules/payments/types.py:141] `PurchaseResult.ad_free_status` has type `Any | None` -- artifact spec says `AdFreeStatus | None` per artifact.md line 180

The implementation types `ad_free_status` as `Any | None` instead of `AdFreeStatus | None`. This weakens the type contract. Any caller relying on the return type sees `Any` instead of the specific `AdFreeStatus` type, losing type safety. This is likely done to avoid importing `AdFreeStatus` from the ads module, but it violates the artifact output spec.

### `ReceiptValidationResult`
Implementation (types.py:116-127) vs artifact (artifact.md:190-202):
- All fields match exactly.

PASS.

### `PlayerPurchaseStatus`
Implementation (types.py:147-157) vs artifact (artifact.md:209-219):
- All fields match exactly.

PASS.

### `PurchaseRecord`
Implementation (types.py:160-174) vs artifact (artifact.md:226-242):

[P0] [src/modules/payments/types.py:160-174] `PurchaseRecord` is MISSING two fields from artifact spec: `receipt_data: str` and `validation_result: str` -- artifact.md lines 238-239 include these fields

The artifact defines `PurchaseRecord` with:
```
receipt_data: str  # Stored for audit/debugging
validation_result: str  # JSON of validation response
```
But the implementation in `types.py` does not include these two fields. Also the implementation does not include `completed_at: datetime | None` which the artifact does NOT show either, so that's fine. But `is_sandbox: bool` IS in both. Let me recheck:

Artifact PurchaseRecord fields:
- id, player_id, product_id, provider, transaction_id, status, price_cents, currency, receipt_data, validation_result, created_at, completed_at, refunded_at

Implementation PurchaseRecord fields:
- id, player_id, product_id, provider, transaction_id, status, price_cents, currency, is_sandbox, created_at, refunded_at

Differences:
- Implementation MISSING: `receipt_data`, `validation_result`, `completed_at`
- Implementation EXTRA: `is_sandbox`

### `RefundResult`
Implementation (types.py:177-187) vs artifact (artifact.md:250-259):
- All fields match exactly.

PASS.

### `RestoreResult`
Implementation (types.py:190-198) vs artifact (artifact.md:266-275):

[P0] [src/modules/payments/types.py:197] `RestoreResult.ad_free_status` has type `Any | None` -- artifact spec says `AdFreeStatus | None` per artifact.md line 273

Same issue as `PurchaseResult` -- `Any | None` instead of `AdFreeStatus | None`.

### `Product`
Implementation (types.py:201-212) vs artifact (artifact.md:282-292):
- All fields match exactly.

PASS.

### `PurchaseReceipt` (input)
Implementation (types.py:73-81) vs artifact (artifact.md:823-829):
- All fields match exactly.

PASS.

### `RefundNotification` (input)
Implementation (types.py:84-92) vs artifact (artifact.md:832-839):
- All fields match exactly.

PASS.

---

## Error Code Checks

All error codes referenced in the artifact's "Error Cases" are verified against interface-contracts.md Section 2:

- `NOT_FOUND_PLAYER`: present in Section 2 Not Found Errors table. PASS.
- `NOT_FOUND_PRODUCT`: present in Section 2 Not Found Errors table. PASS.
- `NOT_FOUND_PURCHASE`: present in Section 2 Not Found Errors table. PASS.
- `CONFLICT_RECEIPT_ALREADY_PROCESSED`: present in Section 2 Conflict Errors table. PASS.
- `VALIDATION_RECEIPT_INVALID`: present in Section 2 Validation Errors table. PASS.
- `VALIDATION_RECEIPT_WRONG_PRODUCT`: present in Section 2 Validation Errors table. PASS.
- `VALIDATION_RECEIPT_WRONG_PLAYER`: present in Section 2 Validation Errors table. PASS.
- `CONFLICT_PURCHASE_ALREADY_REFUNDED`: present in Section 2 Conflict Errors table. PASS.
- `CONFLICT_PLAYER_ALREADY_AD_FREE`: present in Section 2 Conflict Errors table. PASS.
- `CONFLICT_PURCHASE_INTENT_EXPIRED`: present in Section 2 Conflict Errors table. PASS.
- `AUTH_INVALID_WEBHOOK_SIGNATURE`: present in Section 2 Authentication Errors table. PASS.
- `INTERNAL_PAYMENT_PROVIDER_ERROR`: present in Section 2 Internal Errors table. PASS.
- `VALIDATION_INVALID_REFUND_NOTIFICATION`: present in Section 2 Validation Errors table. PASS.
- `VALIDATION_INVALID_INPUT`: present in Section 2 Validation Errors table. PASS.
- `INTERNAL_DATABASE_ERROR`: present in Section 2 Internal Errors table. PASS.

All error codes are present in the interface-contracts.md taxonomy. PASS.

---

## Summary

| Check | Result |
|-------|--------|
| Protocol method signatures | PASS |
| Parameter names/types | PASS |
| Return types | PASS |
| Async behavior | PASS |
| Type aliases from core | PASS |
| DTO/dataclass shapes | 3 P0 findings |
| Error codes in taxonomy | PASS |

### P0 Findings

```
[P0] [src/modules/payments/types.py:141] PurchaseResult.ad_free_status typed as Any | None -> should be AdFreeStatus | None per artifact.md §Outputs/PurchaseResult
[P0] [src/modules/payments/types.py:160-174] PurchaseRecord missing fields receipt_data: str, validation_result: str, completed_at: datetime | None from artifact spec; has extra field is_sandbox: bool not in artifact output spec -> should match artifact.md §Outputs/PurchaseRecord
[P0] [src/modules/payments/types.py:197] RestoreResult.ad_free_status typed as Any | None -> should be AdFreeStatus | None per artifact.md §Outputs/RestoreResult
```

**Recommendation:** Corrections needed.

1. **`PurchaseResult.ad_free_status` and `RestoreResult.ad_free_status`**: Change type from `Any | None` to a properly typed reference. If circular import is a concern, define a local `AdFreeStatusProtocol` or use `TYPE_CHECKING` import guard. The `Any` type defeats type checking for every downstream caller and mock.

2. **`PurchaseRecord`**: Add missing `receipt_data: str`, `validation_result: str`, and `completed_at: datetime | None` fields to match the artifact output spec. The `is_sandbox: bool` field is reasonable (matches DB schema) but should be added to the artifact spec (Orchestrator action).
