"""SQLAlchemy model for the bot_attribution_entries table.

Maps the ``bot_attribution_entries`` table to the
``BotAttributionEntryModel`` ORM class. Each row represents a single
attribution of ad revenue to a bot.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class BotAttributionEntryModel(Base, UUIDMixin):
    """ORM model for the ``bot_attribution_entries`` table."""

    __tablename__ = "bot_attribution_entries"

    bot_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    ad_impression_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
    )
    opponent_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )
    estimated_impression_revenue_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    attribution_share_percent: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    attributed_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    attribution_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
