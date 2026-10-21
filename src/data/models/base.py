"""SQLAlchemy declarative base and common mixins.

All ORM models inherit from ``Base`` and apply the ``UUIDMixin`` and
``TimestampMixin`` to get consistent primary key and audit columns.

Uses SQLAlchemy 2.0 ``Mapped`` / ``mapped_column`` style exclusively.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ChromaCrush ORM models."""

    pass


class UUIDMixin:
    """Provides a UUID primary key column.

    Applied as a mixin class on ORM models::

        class PlayerModel(Base, UUIDMixin, TimestampMixin):
            __tablename__ = "players"
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Provides ``created_at`` and ``updated_at`` audit columns.

    Both columns store timezone-aware UTC timestamps. ``updated_at``
    is automatically refreshed on every UPDATE via ``onupdate``.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
