"""SQLAlchemy model for the raid_logs table.

Maps the ``raid_logs`` table to the ``RaidLogModel`` ORM class.
Records each raid attempt for cooldown enforcement and analytics.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class RaidLogModel(Base, UUIDMixin):
    """ORM model for the ``raid_logs`` table.

    Columns:
        id: UUID primary key (from ``UUIDMixin``).
        attacker_id: FK to players(id) -- the raiding player.
        defender_id: FK to players(id) -- the target player.
        success: Whether the raid succeeded.
        artifact_id: FK to vault_artifacts(id) if an artifact was stolen.
        artifact_type_id: Type of stolen artifact (denormalized for queries).
        timestamp: When the raid occurred.
    """

    __tablename__ = "raid_logs"

    attacker_id: Mapped[bytes] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )

    defender_id: Mapped[bytes] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    artifact_id: Mapped[bytes | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vault_artifacts.id"),
        nullable=True,
    )

    artifact_type_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
