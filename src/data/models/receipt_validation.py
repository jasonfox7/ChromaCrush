"""SQLAlchemy model for the receipt_validations table.

Maps the ``receipt_validations`` table to the ``ReceiptValidationModel``
ORM class. Each row records a receipt validation attempt.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class ReceiptValidationModel(Base, UUIDMixin):
    """ORM model for the ``receipt_validations`` table."""

    __tablename__ = "receipt_validations"

    purchase_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id"),
        nullable=True,
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    receipt_data: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    validation_result: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    validation_response: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    product_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    purchase_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_sandbox: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    error_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
