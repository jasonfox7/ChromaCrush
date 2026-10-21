"""SQLAlchemy model for the players table.

Maps the ``players`` table to the ``PlayerModel`` ORM class. The domain
``Player`` dataclass (``src.core.types.player``) is the public interface;
``PlayerModel`` is internal to the data layer and never leaks into modules.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin, UUIDMixin


class PlayerModel(Base, UUIDMixin, TimestampMixin):
    """ORM model for the ``players`` table.

    Columns:
        id: UUID primary key (from ``UUIDMixin``).
        username: Unique display name.
        username_lower: Lowercased username for case-insensitive uniqueness.
        email: Optional email address (unique when present).
        player_type: ``"human"`` or ``"bot"``.
        elo_rating: Elo matchmaking rating, default 1000.
        password_hash: Nullable bcrypt hash (bots have no password).
        deleted_at: Timestamp of soft-deletion, ``None`` if active.
        created_at: Row creation timestamp (from ``TimestampMixin``).
        updated_at: Last-modified timestamp (from ``TimestampMixin``).
    """

    __tablename__ = "players"

    # UUIDMixin provides: id (UUID PK, default uuid4)
    # TimestampMixin provides: created_at, updated_at

    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    username_lower: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    player_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="human",
    )

    elo_rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1000,
    )

    campaign_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
        default=1,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )

    apple_user_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    auth_provider: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        default="password",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
