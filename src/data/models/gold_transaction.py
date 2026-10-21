"""SQLAlchemy model for the gold_transactions table.

Maps the ``gold_transactions`` table to the ``GoldTransactionModel`` ORM
class.  Each row is an immutable ledger entry recording a single gold
balance change — purchase, earned, spent, or refund.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class GoldTransactionModel(Base, UUIDMixin):
    """ORM model for the ``gold_transactions`` table."""

    __tablename__ = "gold_transactions"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )

    tx_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    balance_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    reference_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
