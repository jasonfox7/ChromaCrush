"""SQLAlchemy model for the ad_impressions table.

Maps the ``ad_impressions`` table to the ``AdImpressionModel`` ORM class.
Each row records a single ad impression event.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class AdImpressionModel(Base, UUIDMixin):
    """ORM model for the ``ad_impressions`` table."""

    __tablename__ = "ad_impressions"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )
    ad_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_requests.id"),
        nullable=True,
    )

    ad_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)
    placement: Mapped[str | None] = mapped_column(String(50), nullable=True)

    viewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    view_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    match_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    opponent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    attributed_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    attribution_share_percent: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    estimated_revenue_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    recorded_date: Mapped[date] = mapped_column(
        Date,
        default=lambda: datetime.now(timezone.utc).date(),
        nullable=False,
    )
