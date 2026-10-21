"""SQLAlchemy model for the ad_requests table.

Maps the ``ad_requests`` table to the ``AdRequestModel`` ORM class.
Each row represents a single ad request from a player.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin, UUIDMixin


class AdRequestModel(Base, UUIDMixin, TimestampMixin):
    """ORM model for the ``ad_requests`` table."""

    __tablename__ = "ad_requests"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )
    ad_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ad_unit_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trigger: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reward_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reward_value: Mapped[int | None] = mapped_column(Integer, nullable=True)

    match_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    provider_response: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
