"""Data Transfer Objects for the payments module.

Pure data carriers used by repositories and the service layer.
No database or business logic awareness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.types.pagination import PaginatedResult as PaginatedResult  # noqa: F401


@dataclass
class PurchaseIntentCreate:
    """Data required to create a purchase intent record."""

    player_id: UUID
    product_id: str
    status: str = "pending"
    expires_at: datetime | None = None


@dataclass
class PurchaseIntentUpdate:
    """Fields that can be updated on a purchase intent."""

    status: str | None = None
    completed_at: datetime | None = None


@dataclass
class PurchaseCreate:
    """Data required to create a purchase record."""

    player_id: UUID
    product_id: str
    provider: str
    transaction_id: str
    status: str = "completed"
    price_cents: int = 100
    currency: str = "USD"
    is_sandbox: bool = False
    intent_id: UUID | None = None
    original_transaction_id: str | None = None


@dataclass
class PurchaseUpdate:
    """Fields that can be updated on a purchase record."""

    status: str | None = None
    refunded_at: datetime | None = None


@dataclass
class ReceiptValidationCreate:
    """Data required to create a receipt validation record."""

    player_id: UUID
    provider: str
    receipt_data: str
    receipt_hash: str
    validation_result: str  # 'valid', 'invalid', 'duplicate', 'error'
    validation_response: dict[str, Any] | None = None
    transaction_id: str | None = None
    product_id: str | None = None
    purchase_date: datetime | None = None
    is_sandbox: bool = False
    error_code: str | None = None
    error_message: str | None = None
    purchase_id: UUID | None = None


@dataclass
class ReceiptValidationUpdate:
    """Fields that can be updated on a receipt validation record."""

    purchase_id: UUID | None = None


@dataclass
class RefundNotificationCreate:
    """Data required to store a refund notification."""

    provider: str
    transaction_id: str
    original_transaction_id: str | None = None
    notification_type: str = "REFUND"
    notification_payload: dict[str, Any] | None = None
