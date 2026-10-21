"""SQLAlchemy model for the api_keys table.

Maps the ``api_keys`` table to the ``ApiKeyModel`` ORM class. API key
records store hashed bot API keys with prefix for identification.
The domain layer accesses keys via the ``ApiKeyRepositoryProtocol``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin, UUIDMixin


class ApiKeyModel(Base, UUIDMixin, TimestampMixin):
    """ORM model for the ``api_keys`` table.

    Columns:
        id: UUID primary key (from ``UUIDMixin``).
        player_id: Foreign key to players table.
        key_hash: Bcrypt hash of the full API key.
        key_prefix: First characters for identification in UI/logs.
        description: Optional description of the key's purpose.
        last_used_at: Timestamp of last API request with this key.
        revoked_at: Timestamp of revocation, ``None`` if active.
        created_at: Row creation timestamp (from ``TimestampMixin``).
        updated_at: Last-modified timestamp (from ``TimestampMixin``).
    """

    __tablename__ = "api_keys"

    player_id: Mapped[bytes] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )

    key_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    key_prefix: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "idx_api_keys_player",
            "player_id",
            postgresql_where="revoked_at IS NULL",
        ),
        Index(
            "idx_api_keys_prefix",
            "key_prefix",
        ),
    )
