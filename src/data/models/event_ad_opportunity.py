"""SQLAlchemy model for the event_ad_opportunities table.

Maps the ``event_ad_opportunities`` table to the
``EventAdOpportunityModel`` ORM class. Each row defines a special
ad opportunity available during an event.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base


class EventAdOpportunityModel(Base):
    """ORM model for the ``event_ad_opportunities`` table."""

    __tablename__ = "event_ad_opportunities"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id"),
        primary_key=True,
    )
    ad_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reward_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reward_value: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    times_available_per_player: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    cooldown_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
