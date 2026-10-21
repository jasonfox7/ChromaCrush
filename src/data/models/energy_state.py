"""SQLAlchemy model for the energy_states table.

Maps the ``energy_states`` table to the ``EnergyStateModel`` ORM class. The
domain ``EnergyState`` dataclass (``src.core.types.player``) is the public
interface; ``EnergyStateModel`` is internal to the data layer and never leaks
into modules.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin


class EnergyStateModel(Base, TimestampMixin):
    """ORM model for the ``energy_states`` table.

    Columns:
        player_id: UUID foreign key referencing ``players.id`` (primary key).
        hearts: Current number of hearts.
        max_hearts: Maximum number of hearts.
        last_regen_at: Timestamp of last energy regeneration.
        daily_streak: Current consecutive daily login streak.
        last_login_date: Date of the most recent login.
        created_at: Row creation timestamp (from ``TimestampMixin``).
        updated_at: Last-modified timestamp (from ``TimestampMixin``).
    """

    __tablename__ = "energy_states"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        primary_key=True,
    )

    hearts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    max_hearts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    last_regen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    daily_streak: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_login_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
