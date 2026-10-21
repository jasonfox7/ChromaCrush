"""SQLAlchemy model for the purchase_intents table.

Maps the ``purchase_intents`` table to the ``PurchaseIntentModel`` ORM class.
Each row represents a purchase intent created when checkout begins.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin, UUIDMixin


class PurchaseIntentModel(Base, UUIDMixin, TimestampMixin):
    """ORM model for the ``purchase_intents`` table."""

    __tablename__ = "purchase_intents"

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
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
