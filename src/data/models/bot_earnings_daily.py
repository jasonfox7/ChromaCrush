"""SQLAlchemy model for the bot_earnings_daily table.

Maps the ``bot_earnings_daily`` table to the ``BotEarningsDailyModel``
ORM class. Each row represents aggregated earnings for one bot on one day.
Uses a composite primary key of (bot_player_id, earnings_date).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base


class BotEarningsDailyModel(Base):
    """ORM model for the ``bot_earnings_daily`` table."""

    __tablename__ = "bot_earnings_daily"

    bot_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        primary_key=True,
    )
    earnings_date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
    )
    attributions_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    matches_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    impressions_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    earnings_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
