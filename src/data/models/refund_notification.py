"""SQLAlchemy model for the refund_notifications table.

Maps the ``refund_notifications`` table to the ``RefundNotificationModel``
ORM class. Each row stores a refund notification from a payment provider.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class RefundNotificationModel(Base, UUIDMixin):
    """ORM model for the ``refund_notifications`` table."""

    __tablename__ = "refund_notifications"

    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(255), nullable=False)
    original_transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    notification_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    purchase_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id"),
        nullable=True,
    )
    processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    process_result: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    process_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
