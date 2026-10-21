"""SQLAlchemy model for the event_participants table.

Maps the ``event_participants`` table to ``EventParticipantModel``.
Composite primary key (event_id, player_id) -- does NOT use UUIDMixin.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base


class EventParticipantModel(Base):
    """ORM model for the ``event_participants`` table."""

    __tablename__ = "event_participants"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        primary_key=True,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_match_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    current_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rewards_claimed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    reward_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)

    last_match_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
