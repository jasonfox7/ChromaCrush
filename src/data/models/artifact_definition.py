"""SQLAlchemy model for the artifact_definitions table.

Maps the ``artifact_definitions`` table to the ``ArtifactDefinitionModel``
ORM class. This is the static catalog of artifact types. The primary key
is a string ``type_id`` rather than UUID.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base


class ArtifactDefinitionModel(Base):
    """ORM model for the ``artifact_definitions`` table.

    Columns:
        type_id: VARCHAR(64) primary key (string, not UUID).
        name: Display name of the artifact.
        description: Longer description text (nullable).
        rarity: One of common, rare, epic, legendary.
        artifact_set: Set identifier this artifact belongs to.
        set_position: Position within the set (1, 2, 3, ...).
        base_value: Point value for scoring.
        image_url: Optional URL for the artifact image.
        created_at: Row creation timestamp.
    """

    __tablename__ = "artifact_definitions"

    type_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    rarity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )

    artifact_set: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    set_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    base_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
