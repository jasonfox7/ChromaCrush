"""SQLAlchemy model for the bot_payout_requests table.

Maps the ``bot_payout_requests`` table to the ``BotPayoutRequestModel``
ORM class. Each row represents a payout request from a bot owner.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class BotPayoutRequestModel(Base, UUIDMixin):
    """ORM model for the ``bot_payout_requests`` table."""

    __tablename__ = "bot_payout_requests"

    bot_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )
    owner_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )
    amount_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    hold_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=True,
    )
    external_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
