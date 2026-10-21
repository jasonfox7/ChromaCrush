# Module Artifact: payments

## Header
- **Author:** Scout Agent (payments)
- **Date:** 2026-02-05
- **Version:** 1.0
- **Status:** Final
- **Dependencies:** `player` (Wave 1), `ads` (Wave 7)
- **Dependents:** None (terminal monetization node)

---

## Purpose

The **payments** module handles the single $1 one-time purchase that permanently removes ads from ChromaCrush. This is the only in-app purchase in the game - no subscriptions, no consumables, no other IAP tiers.

Key responsibilities:

1. **Purchase Initiation** - Create purchase records when player initiates checkout
2. **Receipt Validation** - Validate receipts from Apple App Store and Google Play
3. **Ad-Free Granting** - Call ads module to grant permanent ad-free status on successful purchase
4. **Purchase History** - Maintain audit trail of all purchase attempts and outcomes
5. **Refund Handling** - Process refund notifications and revoke ad-free status
6. **Payment Provider Abstraction** - Abstract receipt validation behind Protocol for testability and future expansion

Per the GDD, this module handles server-side validation only. The client handles payment UI via app store / payment processor SDKs, then sends the receipt to the server for validation.

This module is **asynchronous** - all public methods involving database operations or external API calls are `async def`.

---

## Public Interface

### Class: `PaymentService`

The payments module exposes a single service class that receives dependencies via `__init__` injection.

```python
class PaymentService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        data_ctx: DataContextProtocol,
        player_service: PlayerServiceProtocol,
        ads_service: AdServiceProtocol,
        purchase_repository: PurchaseRepositoryProtocol,
        receipt_repository: ReceiptRepositoryProtocol,
        payment_provider: PaymentProviderProtocol,  # Receipt validation abstraction
    ) -> None:
        ...
```

---

### Inputs

#### `initiate_purchase(player_id: PlayerId, product_id: ProductId) -> PurchaseIntent`

Creates a purchase intent record when player initiates checkout.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The purchasing player | Must exist |
| `product_id` | `ProductId` | Product being purchased | Must be valid product |

---

#### `validate_purchase(player_id: PlayerId, receipt: PurchaseReceipt) -> PurchaseResult`

Validates a purchase receipt from the app store and grants ad-free status on success.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The purchasing player | Must exist |
| `receipt` | `PurchaseReceipt` | Receipt data from client | Must be valid format |

---

#### `get_purchase_status(player_id: PlayerId) -> PlayerPurchaseStatus`

Gets the current purchase status for a player.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player to check | Must exist |

---

#### `get_purchase_history(player_id: PlayerId, limit: int = 50, offset: int = 0) -> PaginatedResult[PurchaseRecord]`

Gets purchase history for a player.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist |
| `limit` | `int` | Max results | 1-100 |
| `offset` | `int` | Pagination offset | >= 0 |

---

#### `process_refund(refund_notification: RefundNotification) -> RefundResult`

Processes a refund notification from the payment provider (webhook handler).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `refund_notification` | `RefundNotification` | Refund data from provider | Must be valid, signature verified |

---

#### `restore_purchases(player_id: PlayerId, receipts: list[PurchaseReceipt]) -> RestoreResult`

Restores purchases for a player (e.g., after reinstall or new device).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist |
| `receipts` | `list[PurchaseReceipt]` | Receipts from app store restore | Must be valid |

---

#### `get_products() -> list[Product]`

Gets available products (currently just the $1 ad-free tier).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| (none) | - | - | - |

---

#### `verify_webhook_signature(payload: bytes, signature: str, provider: PaymentProvider) -> bool`

Verifies webhook signature from payment provider.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `payload` | `bytes` | Raw webhook payload | - |
| `signature` | `str` | Signature header value | - |
| `provider` | `PaymentProvider` | Which provider sent it | Valid enum |

---

### Outputs

#### `PurchaseIntent`

```python
@dataclass
class PurchaseIntent:
    """Purchase intent created when checkout begins."""
    intent_id: PurchaseIntentId
    player_id: PlayerId
    product_id: ProductId
    product_name: str
    price_cents: int
    currency: str
    status: PurchaseIntentStatus
    created_at: datetime
    expires_at: datetime
```

---

#### `PurchaseResult`

```python
@dataclass
class PurchaseResult:
    """Result of validating a purchase."""
    success: bool
    purchase_id: PurchaseId | None
    player_id: PlayerId
    product_id: ProductId
    transaction_id: str | None  # From payment provider
    receipt_validation: ReceiptValidationResult
    ad_free_granted: bool
    ad_free_status: AdFreeStatus | None
    error_code: str | None
    error_message: str | None
```

---

#### `ReceiptValidationResult`

```python
@dataclass
class ReceiptValidationResult:
    """Result of validating a receipt with payment provider."""
    valid: bool
    provider: PaymentProvider
    transaction_id: str | None
    product_id: str | None
    purchase_date: datetime | None
    is_duplicate: bool  # Same receipt already processed
    is_sandbox: bool  # Test environment purchase
    error_code: str | None
    raw_response: dict[str, Any] | None  # Provider's response (for debugging)
```

---

#### `PlayerPurchaseStatus`

```python
@dataclass
class PlayerPurchaseStatus:
    """Current purchase status for a player."""
    player_id: PlayerId
    has_purchased_ad_free: bool
    purchase_date: datetime | None
    transaction_id: str | None
    provider: PaymentProvider | None
    is_refunded: bool
    refund_date: datetime | None
```

---

#### `PurchaseRecord`

```python
@dataclass
class PurchaseRecord:
    """Historical record of a purchase attempt."""
    id: PurchaseId
    player_id: PlayerId
    product_id: ProductId
    provider: PaymentProvider
    transaction_id: str | None
    status: PurchaseStatus
    price_cents: int
    currency: str
    receipt_data: str  # Stored for audit/debugging
    validation_result: str  # JSON of validation response
    created_at: datetime
    completed_at: datetime | None
    refunded_at: datetime | None
```

---

#### `RefundResult`

```python
@dataclass
class RefundResult:
    """Result of processing a refund."""
    success: bool
    purchase_id: PurchaseId | None
    player_id: PlayerId | None
    transaction_id: str
    ad_free_revoked: bool
    error_code: str | None
    error_message: str | None
```

---

#### `RestoreResult`

```python
@dataclass
class RestoreResult:
    """Result of restoring purchases."""
    player_id: PlayerId
    restored_count: int
    already_active_count: int
    invalid_count: int
    ad_free_status: AdFreeStatus | None
    restored_purchases: list[PurchaseRecord]
```

---

#### `Product`

```python
@dataclass
class Product:
    """Available in-app product."""
    product_id: ProductId
    name: str
    description: str
    price_cents: int
    currency: str
    product_type: ProductType  # ONE_TIME, SUBSCRIPTION, CONSUMABLE
    is_active: bool
```

---

### Error Cases

| Condition | Error Code | Error Type | Context Fields |
|-----------|------------|------------|----------------|
| Player not found | `NOT_FOUND_PLAYER` | not_found | `player_id` |
| Invalid product ID | `NOT_FOUND_PRODUCT` | not_found | `product_id` |
| Purchase not found | `NOT_FOUND_PURCHASE` | not_found | `purchase_id` |
| Receipt already processed | `CONFLICT_RECEIPT_ALREADY_PROCESSED` | conflict | `transaction_id`, `original_purchase_id` |
| Receipt validation failed | `VALIDATION_RECEIPT_INVALID` | validation | `provider`, `error_code`, `error_detail` |
| Receipt for wrong product | `VALIDATION_RECEIPT_WRONG_PRODUCT` | validation | `expected_product`, `actual_product` |
| Receipt for wrong player | `VALIDATION_RECEIPT_WRONG_PLAYER` | validation | `expected_player`, `receipt_user_id` |
| Purchase already refunded | `CONFLICT_PURCHASE_ALREADY_REFUNDED` | conflict | `purchase_id`, `refund_date` |
| Player already has ad-free | `CONFLICT_PLAYER_ALREADY_AD_FREE` | conflict | `player_id`, `granted_at` |
| Intent expired | `CONFLICT_PURCHASE_INTENT_EXPIRED` | conflict | `intent_id`, `expired_at` |
| Invalid webhook signature | `AUTH_INVALID_WEBHOOK_SIGNATURE` | unauthorized | `provider` |
| Payment provider error | `INTERNAL_PAYMENT_PROVIDER_ERROR` | internal | `provider`, `error` |
| Refund notification invalid | `VALIDATION_INVALID_REFUND_NOTIFICATION` | validation | `reason` |

---

### Async Behavior

**This module is fully asynchronous.**

All public methods are `async def` because they involve:
- Database reads/writes via repositories
- External payment provider API calls (Apple App Store, Google Play)
- Cross-module service calls to `player_service`, `ads_service`

**Async operations:**
- `initiate_purchase` - DB write
- `validate_purchase` - DB read/write + external API call + ads service call
- `get_purchase_status` - DB read
- `get_purchase_history` - DB read
- `process_refund` - DB write + ads service call
- `restore_purchases` - DB read/write + external API calls + ads service call
- `get_products` - DB read (could be cached)
- `verify_webhook_signature` - Cryptographic verification (sync but wrapped for consistency)

**Error propagation:** All errors are raised through the injected `ErrorServiceProtocol`. External payment provider errors are caught and wrapped in `INTERNAL_PAYMENT_PROVIDER_ERROR`. Cross-module errors propagate unchanged.

---

## Mandatory Service Usage

### Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `payments.ad_free_product_id` | str | `"chromacrush_ad_free"` | Product ID for ad-free tier |
| `payments.ad_free_price_cents` | int | `100` | Price in cents ($1.00) |
| `payments.ad_free_currency` | str | `"USD"` | Currency code |
| `payments.intent_expiry_minutes` | int | `30` | Purchase intent expiration |
| `payments.apple_bundle_id` | str | (required) | iOS app bundle ID |
| `payments.apple_shared_secret` | str | (secret) | App Store Connect shared secret |
| `payments.apple_verify_url` | str | (production URL) | Apple receipt verification endpoint |
| `payments.apple_sandbox_verify_url` | str | (sandbox URL) | Apple sandbox verification endpoint |
| `payments.google_package_name` | str | (required) | Android package name |
| `payments.google_service_account_key` | str | (secret) | Google Play service account JSON |
| `payments.webhook_apple_secret` | str | (secret) | Apple webhook signing secret |
| `payments.webhook_google_secret` | str | (secret) | Google webhook signing secret |
| `payments.allow_sandbox_purchases` | bool | `false` | Allow sandbox receipts (dev only) |

---

### Logging Events

| Event | Severity | Trigger | Context |
|-------|----------|---------|---------|
| `payments.intent_created` | INFO | Purchase intent created | `player_id`, `product_id`, `intent_id` |
| `payments.validation_started` | INFO | Receipt validation started | `player_id`, `provider` |
| `payments.validation_success` | INFO | Receipt validated successfully | `player_id`, `transaction_id`, `product_id` |
| `payments.validation_failed` | WARN | Receipt validation failed | `player_id`, `provider`, `error_code`, `error_detail` |
| `payments.validation_duplicate` | INFO | Duplicate receipt submitted | `player_id`, `transaction_id`, `original_purchase_id` |
| `payments.purchase_completed` | INFO | Purchase completed and ad-free granted | `player_id`, `purchase_id`, `transaction_id` |
| `payments.refund_received` | INFO | Refund notification received | `transaction_id`, `provider` |
| `payments.refund_processed` | INFO | Refund processed, ad-free revoked | `player_id`, `purchase_id`, `transaction_id` |
| `payments.refund_failed` | ERROR | Refund processing failed | `transaction_id`, `error` |
| `payments.restore_started` | INFO | Purchase restore initiated | `player_id`, `receipt_count` |
| `payments.restore_completed` | INFO | Purchase restore completed | `player_id`, `restored_count` |
| `payments.webhook_received` | DEBUG | Webhook received from provider | `provider`, `event_type` |
| `payments.webhook_signature_invalid` | WARN | Invalid webhook signature | `provider` |
| `payments.provider_error` | ERROR | Payment provider API error | `provider`, `operation`, `error` |

---

### Error Types Used

From the error taxonomy (Interface Agent guidance):

- `NOT_FOUND_PLAYER` - Player ID doesn't exist
- `NOT_FOUND_PRODUCT` - Product ID doesn't exist
- `NOT_FOUND_PURCHASE` - Purchase record doesn't exist
- `VALIDATION_INVALID_INPUT` - Invalid parameters
- `VALIDATION_RECEIPT_INVALID` - Receipt failed validation
- `VALIDATION_RECEIPT_WRONG_PRODUCT` - Receipt for different product
- `VALIDATION_RECEIPT_WRONG_PLAYER` - Receipt tied to different user
- `VALIDATION_INVALID_REFUND_NOTIFICATION` - Malformed refund data
- `CONFLICT_RECEIPT_ALREADY_PROCESSED` - Duplicate receipt
- `CONFLICT_PURCHASE_ALREADY_REFUNDED` - Refund already processed
- `CONFLICT_PLAYER_ALREADY_AD_FREE` - Player already has ad-free
- `CONFLICT_PURCHASE_INTENT_EXPIRED` - Intent timed out
- `AUTH_INVALID_WEBHOOK_SIGNATURE` - Webhook signature verification failed
- `INTERNAL_PAYMENT_PROVIDER_ERROR` - External payment API error
- `INTERNAL_DATABASE_ERROR` - Database operation failed

All errors created through injected `ErrorServiceProtocol`, never bare raises.

---

## Data Access

### Owned Data

The payments module owns these database tables:

#### `products` Table

```sql
CREATE TABLE products (
    id VARCHAR(100) PRIMARY KEY,  -- e.g., 'chromacrush_ad_free'
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    product_type VARCHAR(20) NOT NULL,  -- 'one_time', 'subscription', 'consumable'
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `purchase_intents` Table

```sql
CREATE TABLE purchase_intents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES players(id),
    product_id VARCHAR(100) NOT NULL REFERENCES products(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'completed', 'expired', 'cancelled'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_purchase_intents_player ON purchase_intents(player_id, created_at DESC);
CREATE INDEX idx_purchase_intents_status ON purchase_intents(status) WHERE status = 'pending';
```

#### `purchases` Table

```sql
CREATE TABLE purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES players(id),
    product_id VARCHAR(100) NOT NULL REFERENCES products(id),
    intent_id UUID REFERENCES purchase_intents(id),

    provider VARCHAR(20) NOT NULL,  -- 'apple', 'google'
    transaction_id VARCHAR(255) NOT NULL,
    original_transaction_id VARCHAR(255),  -- For subscription renewals (not used for one-time)

    status VARCHAR(20) NOT NULL DEFAULT 'completed',  -- 'completed', 'refunded', 'disputed'

    price_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL,

    is_sandbox BOOLEAN NOT NULL DEFAULT false,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    refunded_at TIMESTAMPTZ,

    CONSTRAINT unique_transaction UNIQUE (provider, transaction_id)
);

CREATE INDEX idx_purchases_player ON purchases(player_id, created_at DESC);
CREATE INDEX idx_purchases_transaction ON purchases(provider, transaction_id);
CREATE INDEX idx_purchases_status ON purchases(status);
```

#### `receipt_validations` Table

```sql
CREATE TABLE receipt_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_id UUID REFERENCES purchases(id),
    player_id UUID NOT NULL REFERENCES players(id),

    provider VARCHAR(20) NOT NULL,
    receipt_data TEXT NOT NULL,  -- Stored for audit trail
    receipt_hash VARCHAR(64) NOT NULL,  -- SHA-256 of receipt for duplicate detection

    validation_result VARCHAR(20) NOT NULL,  -- 'valid', 'invalid', 'duplicate', 'error'
    validation_response JSONB,  -- Raw provider response

    transaction_id VARCHAR(255),
    product_id VARCHAR(100),
    purchase_date TIMESTAMPTZ,
    is_sandbox BOOLEAN NOT NULL DEFAULT false,

    error_code VARCHAR(50),
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_receipt_validations_player ON receipt_validations(player_id, created_at DESC);
CREATE INDEX idx_receipt_validations_hash ON receipt_validations(receipt_hash);
CREATE INDEX idx_receipt_validations_transaction ON receipt_validations(transaction_id) WHERE transaction_id IS NOT NULL;
```

#### `refund_notifications` Table

```sql
CREATE TABLE refund_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(20) NOT NULL,
    transaction_id VARCHAR(255) NOT NULL,
    original_transaction_id VARCHAR(255),

    notification_type VARCHAR(50) NOT NULL,  -- 'REFUND', 'CONSUMPTION_REQUEST', etc.
    notification_payload JSONB NOT NULL,

    purchase_id UUID REFERENCES purchases(id),

    processed BOOLEAN NOT NULL DEFAULT false,
    processed_at TIMESTAMPTZ,
    process_result VARCHAR(20),  -- 'success', 'already_refunded', 'not_found', 'error'
    process_error TEXT,

    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refund_notifications_transaction ON refund_notifications(provider, transaction_id);
CREATE INDEX idx_refund_notifications_unprocessed ON refund_notifications(processed) WHERE processed = false;
```

---

### Repository Interfaces Required

```python
# src/data/protocols/purchase_repository.py
from typing import Protocol
from uuid import UUID
from datetime import datetime

from src.core.types.game import PlayerId


class ProductRepository(Protocol):
    """Repository interface for products."""

    async def find_by_id(self, product_id: str) -> "ProductRecord | None":
        """Find product by ID."""
        ...

    async def find_all_active(self) -> list["ProductRecord"]:
        """Find all active products."""
        ...


class PurchaseIntentRepository(Protocol):
    """Repository interface for purchase intents."""

    async def create(self, data: "PurchaseIntentCreate") -> "PurchaseIntentRecord":
        """Create a new purchase intent."""
        ...

    async def find_by_id(self, intent_id: UUID) -> "PurchaseIntentRecord | None":
        """Find intent by ID."""
        ...

    async def update(self, intent_id: UUID, changes: "PurchaseIntentUpdate") -> "PurchaseIntentRecord":
        """Update intent status."""
        ...

    async def find_pending_by_player(self, player_id: UUID) -> list["PurchaseIntentRecord"]:
        """Find pending intents for a player."""
        ...

    async def expire_old_intents(self, before: datetime) -> int:
        """Expire old pending intents. Returns count expired."""
        ...


class PurchaseRepository(Protocol):
    """Repository interface for purchases."""

    async def create(self, data: "PurchaseCreate") -> "PurchaseRecord":
        """Create a new purchase record."""
        ...

    async def find_by_id(self, purchase_id: UUID) -> "PurchaseRecord | None":
        """Find purchase by ID."""
        ...

    async def find_by_transaction(
        self,
        provider: str,
        transaction_id: str,
    ) -> "PurchaseRecord | None":
        """Find purchase by provider transaction ID."""
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list["PurchaseRecord"], int]:
        """Find purchases for a player."""
        ...

    async def find_completed_by_player(
        self,
        player_id: UUID,
        product_id: str | None = None,
    ) -> list["PurchaseRecord"]:
        """Find completed (non-refunded) purchases for a player."""
        ...

    async def update(self, purchase_id: UUID, changes: "PurchaseUpdate") -> "PurchaseRecord":
        """Update purchase record."""
        ...


class ReceiptValidationRepository(Protocol):
    """Repository interface for receipt validations."""

    async def create(self, data: "ReceiptValidationCreate") -> "ReceiptValidationRecord":
        """Create a new validation record."""
        ...

    async def find_by_hash(self, receipt_hash: str) -> "ReceiptValidationRecord | None":
        """Find validation by receipt hash (for duplicate detection)."""
        ...

    async def find_by_transaction(
        self,
        provider: str,
        transaction_id: str,
    ) -> "ReceiptValidationRecord | None":
        """Find validation by transaction ID."""
        ...


class RefundNotificationRepository(Protocol):
    """Repository interface for refund notifications."""

    async def create(self, data: "RefundNotificationCreate") -> "RefundNotificationRecord":
        """Store incoming refund notification."""
        ...

    async def find_unprocessed(self) -> list["RefundNotificationRecord"]:
        """Find unprocessed refund notifications."""
        ...

    async def mark_processed(
        self,
        notification_id: UUID,
        result: str,
        error: str | None = None,
    ) -> "RefundNotificationRecord":
        """Mark notification as processed."""
        ...
```

---

### Data Read from Other Modules

| Data | Source Module | Access Method | Purpose |
|------|---------------|---------------|---------|
| Player entity | `player` | `PlayerServiceProtocol.get_player()` | Validate player exists |
| Ad-free status | `ads` | `AdServiceProtocol.check_ad_free_status()` | Check if already ad-free |
| Grant ad-free | `ads` | `AdServiceProtocol.grant_ad_free_status()` | Grant ad-free on success |
| Revoke ad-free | `ads` | `AdServiceProtocol.revoke_ad_free_status()` | Revoke on refund |

---

### Transaction Requirements

| Operation | Transaction Scope | Notes |
|-----------|-------------------|-------|
| `initiate_purchase` | Single transaction | Create intent |
| `validate_purchase` | Single transaction | Create validation + purchase + call ads.grant_ad_free |
| `get_purchase_status` | Read only | Simple lookup |
| `get_purchase_history` | Read only | Paginated query |
| `process_refund` | Single transaction | Update purchase + call ads.revoke_ad_free |
| `restore_purchases` | Single transaction | For each valid receipt: validate + grant if needed |

---

## Presentation Boundary

### Business Logic API Surface

The payments module exposes domain objects and DTOs:
- Input: `PlayerId`, `ProductId`, `PurchaseReceipt`, `RefundNotification`
- Output: `PurchaseIntent`, `PurchaseResult`, `PlayerPurchaseStatus`, `PurchaseRecord`, `RefundResult`, `RestoreResult`, `Product`

All types are defined in this module (`src/modules/payments/types.py`) or imported from `src/core/types/`.

### Adapter Needs

Presentation adapters need to:
1. Convert `PurchaseResult` to `PurchaseResponse` (format dates, exclude raw receipt data)
2. Convert `Product` to `ProductResponse` (format price for display)
3. Convert `PlayerPurchaseStatus` to `PurchaseStatusResponse`
4. Format price_cents as locale-appropriate currency string (e.g., "$1.00")
5. Handle webhook payloads from different providers

### What Does NOT Belong in This Module

- No JSON serialization (adapter responsibility)
- No HTTP response construction
- No terminal formatting
- No payment UI (client-side responsibility)
- No ad display logic (ads module responsibility)
- No actual ad rendering (client-side)
- No price localization (client gets price from app store)

---

## Internal Design

### Payment Provider Abstraction

The module uses a `Protocol` interface to abstract receipt validation, allowing for mock testing and provider switching.

```python
# src/modules/payments/protocols.py

class PaymentProviderProtocol(Protocol):
    """Interface for payment provider receipt validation."""

    async def validate_receipt(
        self,
        receipt_data: str,
        product_id: str,
        is_sandbox: bool = False,
    ) -> ReceiptValidationResult:
        """
        Validate a purchase receipt with the payment provider.

        Args:
            receipt_data: Raw receipt string from client
            product_id: Expected product ID
            is_sandbox: Whether to use sandbox validation endpoint

        Returns:
            ReceiptValidationResult with validation outcome
        """
        ...

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify webhook payload signature."""
        ...


class ApplePaymentProvider:
    """Apple App Store receipt validation."""
    pass


class GooglePaymentProvider:
    """Google Play receipt validation."""
    pass


class MockPaymentProvider:
    """Mock provider for testing."""
    pass
```

---

### Core Data Structures

```python
# src/modules/payments/types.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NewType, Any
from uuid import UUID

from src.core.types.game import PlayerId


PurchaseId = NewType("PurchaseId", UUID)
PurchaseIntentId = NewType("PurchaseIntentId", UUID)
ProductId = NewType("ProductId", str)


class PaymentProvider(Enum):
    APPLE = "apple"
    GOOGLE = "google"
    MOCK = "mock"  # For testing


class ProductType(Enum):
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"  # Not used currently
    CONSUMABLE = "consumable"  # Not used currently


class PurchaseIntentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PurchaseStatus(Enum):
    COMPLETED = "completed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


@dataclass
class PurchaseReceipt:
    """Receipt data from client."""
    provider: PaymentProvider
    receipt_data: str  # Base64 encoded for Apple, purchase token for Google
    product_id: ProductId
    transaction_id: str | None = None  # May be included by client


@dataclass
class RefundNotification:
    """Refund notification from payment provider webhook."""
    provider: PaymentProvider
    notification_type: str
    transaction_id: str
    original_transaction_id: str | None
    payload: dict[str, Any]
    signature: str
```

---

### Algorithm: Validate Purchase

```python
async def validate_purchase(
    self,
    player_id: PlayerId,
    receipt: PurchaseReceipt,
) -> PurchaseResult:
    # 1. Validate player exists
    player = await self._player_service.get_player(player_id)

    # 2. Check if already ad-free
    ad_free_status = await self._ads_service.check_ad_free_status(player_id)
    if ad_free_status.is_ad_free:
        raise self._errors.conflict(
            "Player already has ad-free status",
            code="CONFLICT_PLAYER_ALREADY_AD_FREE",
            player_id=str(player_id),
            granted_at=ad_free_status.granted_at.isoformat() if ad_free_status.granted_at else None,
        )

    # 3. Check for duplicate receipt
    receipt_hash = self._hash_receipt(receipt.receipt_data)
    existing_validation = await self._receipt_repo.find_by_hash(receipt_hash)

    if existing_validation is not None and existing_validation.validation_result == "valid":
        # Same receipt already processed
        existing_purchase = await self._purchase_repo.find_by_id(existing_validation.purchase_id)

        if existing_purchase is not None and existing_purchase.status == PurchaseStatus.COMPLETED:
            raise self._errors.conflict(
                "Receipt has already been processed",
                code="CONFLICT_RECEIPT_ALREADY_PROCESSED",
                transaction_id=existing_validation.transaction_id,
                original_purchase_id=str(existing_validation.purchase_id),
            )

    # 4. Validate with payment provider
    self._logger.info(
        "Receipt validation started",
        player_id=str(player_id),
        provider=receipt.provider.value,
    )

    allow_sandbox = self._config.get("payments.allow_sandbox_purchases", False)

    try:
        validation_result = await self._payment_provider.validate_receipt(
            receipt_data=receipt.receipt_data,
            product_id=str(receipt.product_id),
            is_sandbox=allow_sandbox,
        )
    except Exception as e:
        self._logger.error(
            "Payment provider error",
            provider=receipt.provider.value,
            operation="validate_receipt",
            error=str(e),
        )
        raise self._errors.internal(
            "Payment provider error",
            code="INTERNAL_PAYMENT_PROVIDER_ERROR",
            provider=receipt.provider.value,
            error=str(e),
        )

    # 5. Record validation attempt
    validation_record = await self._receipt_repo.create(ReceiptValidationCreate(
        player_id=player_id,
        provider=receipt.provider.value,
        receipt_data=receipt.receipt_data,
        receipt_hash=receipt_hash,
        validation_result="valid" if validation_result.valid else "invalid",
        validation_response=validation_result.raw_response,
        transaction_id=validation_result.transaction_id,
        product_id=validation_result.product_id,
        purchase_date=validation_result.purchase_date,
        is_sandbox=validation_result.is_sandbox,
        error_code=validation_result.error_code,
    ))

    # 6. Handle validation failure
    if not validation_result.valid:
        self._logger.warn(
            "Receipt validation failed",
            player_id=str(player_id),
            provider=receipt.provider.value,
            error_code=validation_result.error_code,
        )
        return PurchaseResult(
            success=False,
            purchase_id=None,
            player_id=player_id,
            product_id=receipt.product_id,
            transaction_id=None,
            receipt_validation=validation_result,
            ad_free_granted=False,
            ad_free_status=None,
            error_code="VALIDATION_RECEIPT_INVALID",
            error_message=validation_result.error_code,
        )

    # 7. Verify product matches
    expected_product = self._config.get("payments.ad_free_product_id")
    if validation_result.product_id != expected_product:
        self._logger.warn(
            "Receipt validation failed - wrong product",
            player_id=str(player_id),
            expected_product=expected_product,
            actual_product=validation_result.product_id,
        )
        raise self._errors.validation(
            "Receipt is for different product",
            code="VALIDATION_RECEIPT_WRONG_PRODUCT",
            expected_product=expected_product,
            actual_product=validation_result.product_id,
        )

    # 8. Create purchase record
    async with self._data_ctx.session() as session:
        purchase = await self._purchase_repo.create(PurchaseCreate(
            player_id=player_id,
            product_id=receipt.product_id,
            provider=receipt.provider.value,
            transaction_id=validation_result.transaction_id,
            status=PurchaseStatus.COMPLETED.value,
            price_cents=self._config.get("payments.ad_free_price_cents", 100),
            currency=self._config.get("payments.ad_free_currency", "USD"),
            is_sandbox=validation_result.is_sandbox,
        ))

        # Update validation record with purchase_id
        await self._receipt_repo.update(
            validation_record.id,
            ReceiptValidationUpdate(purchase_id=purchase.id),
        )

        # 9. Grant ad-free status
        new_ad_free_status = await self._ads_service.grant_ad_free_status(
            player_id=player_id,
            reason=AdFreeReason.PURCHASE,
            duration_days=None,  # Permanent
        )

    self._logger.info(
        "Purchase completed",
        player_id=str(player_id),
        purchase_id=str(purchase.id),
        transaction_id=validation_result.transaction_id,
    )

    return PurchaseResult(
        success=True,
        purchase_id=PurchaseId(purchase.id),
        player_id=player_id,
        product_id=receipt.product_id,
        transaction_id=validation_result.transaction_id,
        receipt_validation=validation_result,
        ad_free_granted=True,
        ad_free_status=new_ad_free_status,
        error_code=None,
        error_message=None,
    )
```

---

### Algorithm: Process Refund

```python
async def process_refund(
    self,
    refund_notification: RefundNotification,
) -> RefundResult:
    # 1. Store the notification
    notification_record = await self._refund_repo.create(RefundNotificationCreate(
        provider=refund_notification.provider.value,
        transaction_id=refund_notification.transaction_id,
        original_transaction_id=refund_notification.original_transaction_id,
        notification_type=refund_notification.notification_type,
        notification_payload=refund_notification.payload,
    ))

    self._logger.info(
        "Refund notification received",
        transaction_id=refund_notification.transaction_id,
        provider=refund_notification.provider.value,
    )

    # 2. Find the original purchase
    purchase = await self._purchase_repo.find_by_transaction(
        provider=refund_notification.provider.value,
        transaction_id=refund_notification.transaction_id,
    )

    if purchase is None:
        # Try original_transaction_id if available
        if refund_notification.original_transaction_id:
            purchase = await self._purchase_repo.find_by_transaction(
                provider=refund_notification.provider.value,
                transaction_id=refund_notification.original_transaction_id,
            )

    if purchase is None:
        await self._refund_repo.mark_processed(
            notification_record.id,
            result="not_found",
            error="No matching purchase found",
        )
        return RefundResult(
            success=False,
            purchase_id=None,
            player_id=None,
            transaction_id=refund_notification.transaction_id,
            ad_free_revoked=False,
            error_code="NOT_FOUND_PURCHASE",
            error_message="No matching purchase found for refund",
        )

    # 3. Check if already refunded
    if purchase.status == PurchaseStatus.REFUNDED:
        await self._refund_repo.mark_processed(
            notification_record.id,
            result="already_refunded",
        )
        return RefundResult(
            success=True,  # Not an error, just already done
            purchase_id=PurchaseId(purchase.id),
            player_id=PlayerId(purchase.player_id),
            transaction_id=refund_notification.transaction_id,
            ad_free_revoked=False,  # Already was revoked
            error_code=None,
            error_message=None,
        )

    # 4. Update purchase status
    async with self._data_ctx.session() as session:
        await self._purchase_repo.update(
            purchase.id,
            PurchaseUpdate(
                status=PurchaseStatus.REFUNDED.value,
                refunded_at=datetime.utcnow(),
            ),
        )

        # 5. Revoke ad-free status
        try:
            await self._ads_service.revoke_ad_free_status(
                player_id=PlayerId(purchase.player_id),
                reason=f"Refund processed: {refund_notification.transaction_id}",
            )
            ad_free_revoked = True
        except Exception as e:
            # Player might not have ad-free anymore (e.g., already expired)
            self._logger.warn(
                "Failed to revoke ad-free status on refund",
                player_id=str(purchase.player_id),
                error=str(e),
            )
            ad_free_revoked = False

    await self._refund_repo.mark_processed(
        notification_record.id,
        result="success",
    )

    self._logger.info(
        "Refund processed",
        player_id=str(purchase.player_id),
        purchase_id=str(purchase.id),
        transaction_id=refund_notification.transaction_id,
    )

    return RefundResult(
        success=True,
        purchase_id=PurchaseId(purchase.id),
        player_id=PlayerId(purchase.player_id),
        transaction_id=refund_notification.transaction_id,
        ad_free_revoked=ad_free_revoked,
        error_code=None,
        error_message=None,
    )
```

---

### Algorithm: Idempotent Receipt Handling

To ensure idempotency (same receipt submitted twice doesn't create duplicate purchases):

1. **Hash the receipt** - SHA-256 hash of receipt_data stored with each validation
2. **Check hash before validation** - If hash exists with valid result, check if purchase completed
3. **Check transaction_id** - Unique constraint on (provider, transaction_id) in purchases table
4. **Return existing purchase** - If duplicate detected, return the existing purchase data (not an error in restore flow)

```python
def _hash_receipt(self, receipt_data: str) -> str:
    """Create SHA-256 hash of receipt for duplicate detection."""
    import hashlib
    return hashlib.sha256(receipt_data.encode()).hexdigest()
```

---

## CLI Surface

### Commands

```bash
# Purchase operations
chromacrush payments products
chromacrush payments initiate <player-id> --product <product-id>
chromacrush payments validate <player-id> --provider apple|google --receipt <receipt-data>
chromacrush payments status <player-id>
chromacrush payments history <player-id> [--limit 50] [--offset 0]
chromacrush payments restore <player-id> --provider apple|google --receipt <receipt-data>

# Refund operations (admin/testing)
chromacrush payments simulate-refund --provider apple|google --transaction <transaction-id>
chromacrush payments list-refunds [--unprocessed]

# Debug operations
chromacrush payments get-purchase <purchase-id>
chromacrush payments get-validation <player-id> --transaction <transaction-id>
```

### Example Invocations

```bash
$ chromacrush payments products
Available Products:
  chromacrush_ad_free - Remove Ads Forever
    Price: $1.00 USD
    Type: One-time purchase
    Status: Active

$ chromacrush payments status abc123
Purchase Status for player abc123:
  Has Ad-Free: No
  Purchase History: 0 purchases

$ chromacrush payments validate abc123 --provider apple --receipt "MIIbh..."
Validating receipt...
  Provider: apple
  Validation: Success
  Transaction ID: 1000000123456789
  Product: chromacrush_ad_free

Purchase completed!
  Purchase ID: 550e8400-e29b-41d4-a716-446655440001
  Ad-Free Status: Granted (permanent)

$ chromacrush payments status abc123
Purchase Status for player abc123:
  Has Ad-Free: Yes
  Purchase Date: 2026-02-05 15:30:00 UTC
  Transaction ID: 1000000123456789
  Provider: apple
  Refunded: No

$ chromacrush payments history abc123
Purchase History for player abc123:
  1. 2026-02-05 15:30:00 UTC
     Product: chromacrush_ad_free ($1.00)
     Provider: apple
     Transaction: 1000000123456789
     Status: Completed

$ chromacrush payments simulate-refund --provider apple --transaction 1000000123456789
Simulating refund notification...
  Transaction: 1000000123456789
  Provider: apple

Refund processed!
  Purchase ID: 550e8400-e29b-41d4-a716-446655440001
  Player ID: abc123
  Ad-Free Revoked: Yes
```

---

## Edge Cases & Decisions

### EC-1: Duplicate Receipt Submission

**Scenario:** Player submits the same receipt twice (e.g., network retry).

**Decision:** Use receipt hash for duplicate detection. If same receipt with successful validation exists:
- If purchase completed and not refunded, return CONFLICT_RECEIPT_ALREADY_PROCESSED
- If purchase was refunded, allow re-validation (player re-purchased)

**Rationale:** Prevents fraud while allowing legitimate re-purchases after refund.

---

### EC-2: Player Already Has Ad-Free

**Scenario:** Player tries to purchase when they already have ad-free status.

**Decision:** Return CONFLICT_PLAYER_ALREADY_AD_FREE error. Do not process receipt.

**Rationale:** Prevents double-charging. Client should check status before showing purchase UI.

---

### EC-3: Receipt for Different Product

**Scenario:** Receipt validated but product_id doesn't match expected ad-free product.

**Decision:** Reject with VALIDATION_RECEIPT_WRONG_PRODUCT. Do not create purchase.

**Rationale:** Security - only accept receipts for products we actually sell.

---

### EC-4: Sandbox Receipt in Production

**Scenario:** Someone submits a sandbox/test receipt in production.

**Decision:** Reject unless `payments.allow_sandbox_purchases` is true (dev only).

**Rationale:** Sandbox receipts should never grant real ad-free status in production.

---

### EC-5: Refund Without Matching Purchase

**Scenario:** Refund notification received but no matching purchase found.

**Decision:** Store the notification, mark as "not_found", return error. Do not fail silently.

**Rationale:** Audit trail for investigation. Could be timing issue, data sync issue, or fraud.

---

### EC-6: Player Deleted After Purchase

**Scenario:** Refund notification received for a soft-deleted player.

**Decision:** Process refund normally. Update purchase status. Ad-free revocation may fail (player not found in ads module), log warning but complete refund processing.

**Rationale:** Financial records must be accurate regardless of player account status.

---

### EC-7: Network Error During Validation

**Scenario:** Payment provider API times out or returns error.

**Decision:** Return INTERNAL_PAYMENT_PROVIDER_ERROR. Do not grant ad-free. Client should retry.

**Rationale:** Never grant entitlements on validation failure. Safe to retry.

---

### EC-8: Purchase Restore on New Device

**Scenario:** Player reinstalls app or gets new device, needs to restore purchase.

**Decision:** `restore_purchases` accepts list of receipts from app store restore API. For each:
- If already in our system and valid, return existing purchase info
- If not in system, validate and create purchase record
- Grant ad-free if any valid purchase found

**Rationale:** Standard app store restore flow. Must be idempotent.

---

### EC-9: Concurrent Validation Requests

**Scenario:** Two validate_purchase calls race for same player.

**Decision:** Database unique constraint on (provider, transaction_id) prevents duplicate purchases. Second request will fail with constraint violation, which we catch and return as CONFLICT_RECEIPT_ALREADY_PROCESSED.

**Rationale:** Database-level protection against race conditions.

---

### EC-10: Webhook Replay Attack

**Scenario:** Attacker replays old refund webhook.

**Decision:** Store all webhook notifications with unique ID. Check if notification already processed before processing. Verify webhook signature.

**Rationale:** Idempotent processing + signature verification protects against replay.

---

## Open Questions

None. All design decisions have been resolved based on:
- Feasibility report specifications
- Interface contracts guidance
- Data layer guidance
- Ads module artifact (for integration)
- Player module artifact (for integration)
- GDD requirements for $1 ad-free tier

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent (payments) |
