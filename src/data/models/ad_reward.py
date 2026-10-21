"""SQLAlchemy model for the ad_rewards_granted table.

Maps the ``ad_rewards_granted`` table to the ``AdRewardModel`` ORM class.
Each row records a reward granted from watching a rewarded ad.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class AdRewardModel(Base, UUIDMixin):
    """ORM model for the ``ad_rewards_granted`` table."""

    __tablename__ = "ad_rewards_granted"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )
    ad_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_requests.id"),
        nullable=False,
    )
    impression_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_impressions.id"),
        nullable=False,
    )
    reward_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reward_value: Mapped[int] = mapped_column(Integer, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("ad_request_id", name="unique_ad_reward"),)
