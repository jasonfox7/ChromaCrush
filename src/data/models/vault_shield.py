"""SQLAlchemy model for the vault_shields table.

Maps the ``vault_shields`` table to the ``VaultShieldModel`` ORM class.
Each player may have at most one shield (player_id is the PK).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base


class VaultShieldModel(Base):
    """ORM model for the ``vault_shields`` table.

    Columns:
        player_id: UUID PK + FK to players(id). One shield per player.
        activated_at: When the shield was activated.
        expires_at: When the shield expires.
        duration_hours: The configured duration at activation time.
    """

    __tablename__ = "vault_shields"

    player_id: Mapped[bytes] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        primary_key=True,
    )

    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    duration_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
