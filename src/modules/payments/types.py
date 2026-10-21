"""Payments module types -- enums and domain dataclasses.

Defines payment-related types, statuses, providers, and all output
dataclasses returned by the PaymentService public interface.

Note: ``PlayerId`` is imported from ``src.core.types.game`` and
is NOT redefined here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, NewType
from uuid import UUID

from src.core.types.game import PlayerId

# ---------------------------------------------------------------------------
# Opaque identifiers
# ---------------------------------------------------------------------------

PurchaseId = NewType("PurchaseId", UUID)
PurchaseIntentId = NewType("PurchaseIntentId", UUID)
ProductId = NewType("ProductId", str)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PaymentProvider(Enum):
    """Payment provider identifiers."""

    APPLE = "apple"
    GOOGLE = "google"
    MOCK = "mock"  # For testing


class ProductType(Enum):
    """Types of in-app products."""

    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"  # Not used currently
    CONSUMABLE = "consumable"  # Not used currently


class PurchaseIntentStatus(Enum):
    """Lifecycle states for a purchase intent."""

    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PurchaseStatus(Enum):
    """Lifecycle states for a purchase."""

    COMPLETED = "completed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


# ---------------------------------------------------------------------------
# Input dataclasses
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Output domain objects
# ---------------------------------------------------------------------------


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
    ad_free_status: Any | None  # AdFreeStatus from ads module
    error_code: str | None
    error_message: str | None


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
    is_sandbox: bool
    created_at: datetime
    refunded_at: datetime | None


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


@dataclass
class RestoreResult:
    """Result of restoring purchases."""

    player_id: PlayerId
    restored_count: int
    already_active_count: int
    invalid_count: int
    ad_free_status: Any | None  # AdFreeStatus from ads module
    restored_purchases: list[PurchaseRecord]


@dataclass
class Product:
    """Available in-app product."""

    product_id: ProductId
    name: str
    description: str
    price_cents: int
    currency: str
    product_type: ProductType
    is_active: bool
