"""SQLAlchemy model for the event_matches table.

Maps the ``event_matches`` table to ``EventMatchRecordModel``.
Each row records a single match played within an event context.
Named ``EventMatchRecordModel`` to avoid confusion with ``MatchModel``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class EventMatchRecordModel(Base, UUIDMixin):
    """ORM model for the ``event_matches`` table."""

    __tablename__ = "event_matches"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    score: Mapped[int] = mapped_column(Integer, nullable=False)
    chain_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gems_cleared: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    special_gems_activated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "player_id",
            "match_id",
            name="unique_event_match",
        ),
    )
