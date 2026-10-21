"""SQLAlchemy model for the player_cards table.

Maps the ``player_cards`` table to the ``PlayerCardModel`` ORM class.
Each row represents a card instance owned by a player, with positional
ordering (positions 1-3 = equipped slots).

Card definitions live in ``config/card_definitions.json`` — the ``card_id``
column is a plain integer referencing the JSON definition (no DB FK).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class PlayerCardModel(Base, UUIDMixin):
    """ORM model for the ``player_cards`` table.

    Columns:
        id: UUID primary key (from ``UUIDMixin``).
        player_id: FK to players(id) -- the card's owner.
        card_id: Integer referencing card_definitions.json (no DB FK).
        position: Equip ordering (1-3 = equipped, 4+ = vault).
        acquired_at: When the player acquired this card.
        source: How the card was acquired (match_reward, merge, etc.).
        source_id: Optional reference to source entity.
        level: Card level for merge progression (default 1).
        created_at: Row creation timestamp.
    """

    __tablename__ = "player_cards"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "position", name="uq_player_cards_player_position"
        ),
    )

    player_id: Mapped[bytes] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )

    card_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
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

    level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
