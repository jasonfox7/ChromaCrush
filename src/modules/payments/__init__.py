"""Payments module for ChromaCrush.

Manages the single $1 one-time purchase that permanently removes ads.
Handles purchase initiation, receipt validation, ad-free granting,
refund processing, and purchase restoration. This module is fully async.

Exports:
    PaymentService: Concrete service implementation.
    PaymentServiceProtocol: Protocol interface for dependency injection.
"""

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
from src.modules.payments.protocols import PaymentServiceProtocol
from src.modules.payments.service import PaymentService
from src.modules.payments.types import (
    PaymentProvider,
    PlayerPurchaseStatus,
    Product,
    ProductId,
    ProductType,
    PurchaseId,
    PurchaseIntent,
    PurchaseIntentId,
    PurchaseIntentStatus,
    PurchaseRecord,
    PurchaseReceipt,
    PurchaseResult,
    PurchaseStatus,
    ReceiptValidationResult,
    RefundNotification,
    RefundResult,
    RestoreResult,
)

__all__ = [
    "PaginatedResult",
    "PaymentProvider",
    "PaymentService",
    "PaymentServiceProtocol",
    "PlayerPurchaseStatus",
    "Product",
    "ProductId",
    "ProductType",
    "PurchaseCreate",
    "PurchaseId",
    "PurchaseIntent",
    "PurchaseIntentCreate",
    "PurchaseIntentId",
    "PurchaseIntentStatus",
    "PurchaseIntentUpdate",
    "PurchaseRecord",
    "PurchaseReceipt",
    "PurchaseResult",
    "PurchaseStatus",
    "PurchaseUpdate",
    "ReceiptValidationCreate",
    "ReceiptValidationResult",
    "ReceiptValidationUpdate",
    "RefundNotification",
    "RefundNotificationCreate",
    "RefundResult",
    "RestoreResult",
]
