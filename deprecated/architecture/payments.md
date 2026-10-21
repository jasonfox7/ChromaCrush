# Module Architecture Report: payments

**Module:** payments
**Build Wave:** 8 (Terminal Node)
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The payments module handles ChromaCrush's single monetization purchase: a $1 one-time payment to permanently remove ads. It manages the complete purchase lifecycle including purchase intent creation, server-side receipt validation against Apple App Store and Google Play, ad-free status granting via the ads module, purchase history retrieval, purchase restoration for device transfers, and webhook-based refund processing that revokes ad-free status. The payment provider (Apple/Google) is abstracted behind a Protocol interface for testability and future expansion. All 8 public service methods are **asynchronous** (`async def`) because they involve database operations and external provider API calls. The module is a terminal node in the dependency graph with no downstream dependents.

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `initiate_purchase` | `(player_id, product_id, provider) -> PurchaseIntent` | Create purchase intent with expiry |
| `validate_purchase` | `(player_id, receipt: PurchaseReceipt) -> PurchaseResult` | Validate receipt and grant ad-free |
| `get_purchase_status` | `(player_id) -> PlayerPurchaseStatus` | Check player's purchase and ad-free status |
| `get_purchase_history` | `(player_id, limit?, offset?) -> PaginatedResult[PurchaseRecord]` | Paginated purchase history |
| `process_refund` | `(notification: RefundNotification) -> RefundResult` | Process refund webhook, revoke ad-free |
| `restore_purchases` | `(player_id, receipts) -> RestoreResult` | Restore purchases on new device |
| `get_products` | `() -> list[Product]` | List available products |
| `verify_webhook_signature` | `(provider, payload, signature) -> bool` | Verify webhook authenticity |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Payment configuration (product IDs, provider URLs, secrets) |
| `logger` | `LoggerProtocol` | Structured diagnostic logging |
| `errors` | `ErrorServiceProtocol` | Create typed errors |
| `data_ctx` | `DataContextProtocol` | Session management |
| `player_service` | `PlayerServiceProtocol` | Player existence verification |
| `ads_service` | `AdServiceProtocol` | Grant/revoke ad-free status |
| `product_repo` | `ProductRepositoryProtocol` | Product catalog persistence |
| `intent_repo` | `PurchaseIntentRepositoryProtocol` | Purchase intent lifecycle |
| `purchase_repo` | `PurchaseRepositoryProtocol` | Purchase record persistence |
| `receipt_repo` | `ReceiptValidationRepositoryProtocol` | Receipt validation audit trail |
| `refund_repo` | `RefundNotificationRepositoryProtocol` | Refund notification records |
| `payment_provider` | `PaymentProviderProtocol` | Apple/Google receipt validation abstraction |

---

## 4. Data Owned

| Table | Description |
|-------|-------------|
| `products` | Product catalog (String PK, not UUID; contains ad-free product definition) |
| `purchase_intents` | Purchase intent records with expiry tracking |
| `purchases` | Completed purchase records with provider transaction IDs |
| `receipt_validations` | Receipt validation audit trail (immutable records) |
| `refund_notifications` | Webhook refund notification records |

Read-only access to `players` (via player service) and `ad_free_status` (via ads service).

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `payments.ad_free_product_id` | string | "chromacrush_ad_free" | Product ID for ad-free tier |
| `payments.ad_free_price_cents` | int | 100 | Price in cents |
| `payments.ad_free_currency` | string | "USD" | Currency code |
| `payments.intent_expiry_minutes` | int | 30 | Purchase intent timeout |
| `payments.apple_bundle_id` | string | *(required)* | iOS bundle ID |
| `payments.apple_shared_secret` | string | *(secret)* | App Store shared secret |
| `payments.apple_verify_url` | string | *(production URL)* | Apple production verify URL |
| `payments.apple_sandbox_verify_url` | string | *(sandbox URL)* | Apple sandbox verify URL |
| `payments.google_package_name` | string | *(required)* | Android package name |
| `payments.google_service_account_key` | string | *(secret)* | GCP service account JSON |
| `payments.webhook_apple_secret` | string | *(secret)* | Apple webhook secret |
| `payments.webhook_google_secret` | string | *(secret)* | Google webhook secret |
| `payments.allow_sandbox_purchases` | bool | false | Allow sandbox receipts |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `NOT_FOUND_PRODUCT` | 404 | Product ID does not exist |
| `NOT_FOUND_PURCHASE` | 404 | Purchase record not found |
| `NOT_FOUND_PLAYER` | 404 | Player does not exist (via player_service) |
| `CONFLICT_RECEIPT_ALREADY_PROCESSED` | 409 | Duplicate receipt submission |
| `CONFLICT_PURCHASE_ALREADY_REFUNDED` | 409 | Already refunded (idempotent return) |
| `CONFLICT_PLAYER_ALREADY_AD_FREE` | 409 | Player already has ad-free status |
| `CONFLICT_PURCHASE_INTENT_EXPIRED` | 409 | Purchase intent timed out |
| `VALIDATION_RECEIPT_INVALID` | 400 | Receipt validation failed |
| `VALIDATION_RECEIPT_WRONG_PRODUCT` | 400 | Receipt for different product |
| `VALIDATION_RECEIPT_WRONG_PLAYER` | 400 | Receipt tied to different user |
| `VALIDATION_INVALID_REFUND_NOTIFICATION` | 400 | Malformed refund webhook data |
| `AUTH_INVALID_WEBHOOK_SIGNATURE` | 401 | Webhook signature verification failed |
| `INTERNAL_PAYMENT_PROVIDER_ERROR` | 500 | External payment API failure |

---

## 7. Cross-Module Interactions

**Called by:**
- `api` -- exposes payment endpoints

**Calls:**
- `player` -- player existence verification
- `ads` -- grant/revoke ad-free status on purchase/refund

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `PaymentProvider` | `src/modules/payments/types.py` | Enum: APPLE, GOOGLE |
| `PurchaseStatus` | `src/modules/payments/types.py` | Enum: PENDING, COMPLETED, REFUNDED, FAILED |
| `PurchaseIntent` | `src/modules/payments/types.py` | Purchase intent record with expiry |
| `PurchaseResult` | `src/modules/payments/types.py` | Result of receipt validation and purchase |
| `PurchaseReceipt` | `src/modules/payments/types.py` | Input: receipt data from client for validation |
| `RefundNotification` | `src/modules/payments/types.py` | Input: refund webhook data from provider |
| `PlayerPurchaseStatus` | `src/modules/payments/types.py` | Player's purchase and ad-free state |
| `Product` | `src/modules/payments/types.py` | Product catalog entry |
