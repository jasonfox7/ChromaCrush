"""SQLAlchemy model for the sessions table.

Maps the ``sessions`` table to the ``SessionModel`` ORM class. Session
records track human player authentication sessions with refresh token
rotation support. The domain layer accesses sessions via the
``SessionRepositoryProtocol``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin, UUIDMixin


class SessionModel(Base, UUIDMixin, TimestampMixin):
    """ORM model for the ``sessions`` table.

    Columns:
        id: UUID primary key (from ``UUIDMixin``).
        player_id: Foreign key to players table.
        refresh_token_hash: Bcrypt hash of the refresh token.
        device_info: Optional client/device identifier.
        last_used_at: Timestamp of last activity.
        expires_at: When the session expires.
        revoked_at: Timestamp of revocation, ``None`` if active.
        created_at: Row creation timestamp (from ``TimestampMixin``).
        updated_at: Last-modified timestamp (from ``TimestampMixin``).
    """

    __tablename__ = "sessions"

    player_id: Mapped[bytes] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )

    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    device_info: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "idx_sessions_player",
            "player_id",
            postgresql_where="revoked_at IS NULL",
        ),
        Index(
            "idx_sessions_expires",
            "expires_at",
            postgresql_where="revoked_at IS NULL",
        ),
    )
