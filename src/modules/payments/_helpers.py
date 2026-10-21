"""Internal helpers for the payments module.

Pure utility functions extracted from ``PaymentService`` to reduce class
complexity.  These are *not* part of the public module API -- the leading
underscore signals they are implementation details.
"""

from __future__ import annotations

import hashlib
from typing import Any

from src.core.types.game import PlayerId
from src.modules.payments.types import (
    PaymentProvider,
    ProductId,
    PurchaseId,
    PurchaseRecord,
    PurchaseStatus,
)


def hash_receipt(receipt_data: str) -> str:
    """Create SHA-256 hash of receipt for duplicate detection."""
    return hashlib.sha256(receipt_data.encode()).hexdigest()


def to_purchase_record(rec: Any) -> PurchaseRecord:
    """Convert a repository record to a PurchaseRecord domain object."""
    return PurchaseRecord(
        id=PurchaseId(rec.id),
        player_id=PlayerId(rec.player_id),
        product_id=ProductId(rec.product_id),
        provider=PaymentProvider(rec.provider),
        transaction_id=rec.transaction_id,
        status=PurchaseStatus(rec.status),
        price_cents=rec.price_cents,
        currency=rec.currency,
        is_sandbox=rec.is_sandbox,
        created_at=rec.created_at,
        refunded_at=getattr(rec, "refunded_at", None),
    )
