"""SQLAlchemy model for the purchases table.

Maps the ``purchases`` table to the ``PurchaseModel`` ORM class.
Each row represents a completed (or refunded) in-app purchase.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin, UUIDMixin


class PurchaseModel(Base, UUIDMixin, TimestampMixin):
    """ORM model for the ``purchases`` table."""

    __tablename__ = "purchases"
    __table_args__ = (
        UniqueConstraint("provider", "transaction_id", name="unique_transaction"),
    )

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("products.id"),
        nullable=False,
    )
    intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_intents.id"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(255), nullable=False)
    original_transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="completed",
    )
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_sandbox: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
