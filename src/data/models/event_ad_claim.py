"""SQLAlchemy model for the event_ad_claims table.

Maps the ``event_ad_claims`` table to the ``EventAdClaimModel`` ORM class.
Each row records a player claiming an event ad opportunity.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class EventAdClaimModel(Base, UUIDMixin):
    """ORM model for the ``event_ad_claims`` table."""

    __tablename__ = "event_ad_claims"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False,
    )
    opportunity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )
    impression_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_impressions.id"),
        nullable=False,
    )
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "opportunity_id",
            "player_id",
            "claimed_at",
            name="unique_event_ad_claim",
        ),
    )
