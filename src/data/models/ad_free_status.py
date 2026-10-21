"""SQLAlchemy model for the ad_free_status table.

Maps the ``ad_free_status`` table to the ``AdFreeStatusModel`` ORM class.
Each row tracks whether a player has ad-free status.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base


class AdFreeStatusModel(Base):
    """ORM model for the ``ad_free_status`` table."""

    __tablename__ = "ad_free_status"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        primary_key=True,
    )
    is_ad_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
