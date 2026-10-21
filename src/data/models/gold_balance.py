"""SQLAlchemy model for the gold_balances table.

Maps the ``gold_balances`` table to the ``GoldBalanceModel`` ORM class.
One row per player, tracking current balance and lifetime stats.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin


class GoldBalanceModel(Base, TimestampMixin):
    """ORM model for the ``gold_balances`` table.

    Columns:
        player_id: UUID foreign key referencing ``players.id`` (primary key).
        balance: Current gold balance.
        lifetime_earned: Total gold earned over all time.
        lifetime_spent: Total gold spent over all time.
        created_at: Row creation timestamp (from ``TimestampMixin``).
        updated_at: Last-modified timestamp (from ``TimestampMixin``).
    """

    __tablename__ = "gold_balances"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        primary_key=True,
    )

    balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    lifetime_earned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    lifetime_spent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
