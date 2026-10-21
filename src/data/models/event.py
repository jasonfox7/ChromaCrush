"""SQLAlchemy model for the events table.

Maps the ``events`` table to the ``EventModel`` ORM class.
Each row represents a time-limited event with lifecycle tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin, UUIDMixin


class EventModel(Base, UUIDMixin, TimestampMixin):
    """ORM model for the ``events`` table."""

    __tablename__ = "events"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="scheduled",
        index=True,
    )
    scoring_type: Mapped[str] = mapped_column(String(30), nullable=False)

    entry_requirements: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    reward_tiers: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    participant_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=True,
    )

    __table_args__ = (CheckConstraint("end_at > start_at", name="check_event_dates"),)
