"""Payments module protocols -- typing.Protocol interfaces.

Defines the PaymentServiceProtocol (public interface), PaymentProviderProtocol
(receipt validation abstraction), repository protocols, and minimal dependency
protocols for cross-module interactions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.core.types.game import PlayerId
from src.modules.payments.dto import (
    PaginatedResult,
    PurchaseCreate,
    PurchaseIntentCreate,
    PurchaseIntentUpdate,
    PurchaseUpdate,
    ReceiptValidationCreate,
    ReceiptValidationUpdate,
    RefundNotificationCreate,
)
from src.modules.payments.types import (
    PaymentProvider,
    PlayerPurchaseStatus,
    Product,
    ProductId,
    PurchaseIntent,
    PurchaseRecord,
    PurchaseReceipt,
    PurchaseResult,
    ReceiptValidationResult,
    RefundNotification,
    RefundResult,
    RestoreResult,
)

# ---------------------------------------------------------------------------
# Public service protocol
# ---------------------------------------------------------------------------


class PaymentServiceProtocol(Protocol):
    """Public interface for the payments module."""

    async def initiate_purchase(
        self,
        player_id: PlayerId,
        product_id: ProductId,
    ) -> PurchaseIntent: ...

    async def validate_purchase(
        self,
        player_id: PlayerId,
        receipt: PurchaseReceipt,
    ) -> PurchaseResult: ...

    async def get_purchase_status(
        self,
        player_id: PlayerId,
    ) -> PlayerPurchaseStatus: ...

    async def get_purchase_history(
        self,
        player_id: PlayerId,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[PurchaseRecord]: ...

    async def process_refund(
        self,
        refund_notification: RefundNotification,
    ) -> RefundResult: ...

    async def restore_purchases(
        self,
        player_id: PlayerId,
        receipts: list[PurchaseReceipt],
    ) -> RestoreResult: ...

    async def get_products(self) -> list[Product]: ...

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        provider: PaymentProvider,
    ) -> bool: ...

    async def list_refund_notifications(
        self,
        unprocessed_only: bool = True,
    ) -> list[Any]: ...

    async def get_purchase(self, purchase_id: str) -> Any: ...

    async def get_validation_by_transaction(
        self,
        transaction_id: str,
    ) -> Any: ...


# ---------------------------------------------------------------------------
# Payment provider abstraction
# ---------------------------------------------------------------------------


class PaymentProviderProtocol(Protocol):
    """Interface for payment provider receipt validation."""

    async def validate_receipt(
        self,
        receipt_data: str,
        product_id: str,
        is_sandbox: bool = False,
    ) -> ReceiptValidationResult:
        """Validate a purchase receipt with the payment provider."""
        ...

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify webhook payload signature."""
        ...


# ---------------------------------------------------------------------------
# Repository protocols
# ---------------------------------------------------------------------------


class ProductRepositoryProtocol(Protocol):
    """Repository interface for products."""

    async def find_by_id(self, product_id: str) -> Any | None:
        """Find product by ID."""
        ...

    async def find_all_active(self) -> list[Any]:
        """Find all active products."""
        ...


class PurchaseIntentRepositoryProtocol(Protocol):
    """Repository interface for purchase intents."""

    async def create(self, data: PurchaseIntentCreate) -> Any:
        """Create a new purchase intent."""
        ...

    async def find_by_id(self, intent_id: UUID) -> Any | None:
        """Find intent by ID."""
        ...

    async def update(self, intent_id: UUID, changes: PurchaseIntentUpdate) -> Any:
        """Update intent status."""
        ...

    async def find_pending_by_player(self, player_id: UUID) -> list[Any]:
        """Find pending intents for a player."""
        ...

    async def expire_old_intents(self, before: datetime) -> int:
        """Expire old pending intents. Returns count expired."""
        ...


class PurchaseRepositoryProtocol(Protocol):
    """Repository interface for purchases."""

    async def create(self, data: PurchaseCreate) -> Any:
        """Create a new purchase record."""
        ...

    async def find_by_id(self, purchase_id: UUID) -> Any | None:
        """Find purchase by ID."""
        ...

    async def find_by_transaction(
        self,
        provider: str,
        transaction_id: str,
    ) -> Any | None:
        """Find purchase by provider transaction ID."""
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """Find purchases for a player."""
        ...

    async def find_completed_by_player(
        self,
        player_id: UUID,
        product_id: str | None = None,
    ) -> list[Any]:
        """Find completed (non-refunded) purchases for a player."""
        ...

    async def update(self, purchase_id: UUID, changes: PurchaseUpdate) -> Any:
        """Update purchase record."""
        ...


class ReceiptValidationRepositoryProtocol(Protocol):
    """Repository interface for receipt validations."""

    async def create(self, data: ReceiptValidationCreate) -> Any:
        """Create a new validation record."""
        ...

    async def find_by_hash(self, receipt_hash: str) -> Any | None:
        """Find validation by receipt hash (for duplicate detection)."""
        ...

    async def find_by_transaction(
        self,
        provider: str,
        transaction_id: str,
    ) -> Any | None:
        """Find validation by transaction ID."""
        ...

    async def update(
        self, validation_id: UUID, changes: ReceiptValidationUpdate
    ) -> Any:
        """Update validation record."""
        ...


class RefundNotificationRepositoryProtocol(Protocol):
    """Repository interface for refund notifications."""

    async def create(self, data: RefundNotificationCreate) -> Any:
        """Store incoming refund notification."""
        ...

    async def find_unprocessed(self) -> list[Any]:
        """Find unprocessed refund notifications."""
        ...

    async def mark_processed(
        self,
        notification_id: UUID,
        result: str,
        error: str | None = None,
    ) -> Any:
        """Mark notification as processed."""
        ...


# ---------------------------------------------------------------------------
# Minimal dependency protocols (avoid circular imports)
# ---------------------------------------------------------------------------


class PlayerServiceProtocol(Protocol):
    """Subset of player service used by payments module."""

    async def get_player(self, player_id: PlayerId) -> Any: ...


class AdServiceProtocol(Protocol):
    """Subset of ads service used by payments module."""

    async def check_ad_free_status(self, player_id: PlayerId) -> Any: ...

    async def grant_ad_free_status(
        self,
        player_id: PlayerId,
        reason: Any,
        duration_days: int | None = None,
        granted_by: PlayerId | None = None,
    ) -> Any: ...

    async def revoke_ad_free_status(
        self,
        player_id: PlayerId,
        reason: str,
    ) -> None: ...
