"""SQLAlchemy model for the vault_artifacts table.

Maps the ``vault_artifacts`` table to the ``VaultArtifactModel`` ORM class.
Each row represents a single artifact instance owned by a player.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class VaultArtifactModel(Base, UUIDMixin):
    """ORM model for the ``vault_artifacts`` table.

    Columns:
        id: UUID primary key (from ``UUIDMixin``).
        owner_id: FK to players(id) -- the artifact's current owner.
        artifact_type_id: Reference to artifact_definitions(type_id).
        acquired_at: When the player acquired this artifact.
        source: How the artifact was acquired (match_reward, raid, etc.).
        source_id: Optional reference to source entity.
        created_at: Row creation timestamp.
    """

    __tablename__ = "vault_artifacts"

    owner_id: Mapped[bytes] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )

    artifact_type_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    source_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
