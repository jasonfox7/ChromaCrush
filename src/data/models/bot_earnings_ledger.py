"""SQLAlchemy model for the bot_earnings_ledger table.

Maps the ``bot_earnings_ledger`` table to the ``BotEarningsLedgerModel``
ORM class. Each row represents the cumulative earnings ledger for one bot.
Note: bot_player_id is the primary key (not UUID mixin).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin


class BotEarningsLedgerModel(Base, TimestampMixin):
    """ORM model for the ``bot_earnings_ledger`` table."""

    __tablename__ = "bot_earnings_ledger"

    bot_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        primary_key=True,
    )
    owner_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )
    total_earned_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_paid_out_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    pending_payout_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    last_attribution_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
