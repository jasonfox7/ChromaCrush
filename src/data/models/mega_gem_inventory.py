"""SQLAlchemy model for the mega_gem_inventory table.

Maps the ``mega_gem_inventory`` table to the ``MegaGemInventoryModel`` ORM class.
Each row represents one inventory slot for a player, tracking the count of
a specific mega gem type (slots 0-3) or shuffle tokens (slot 4).
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class MegaGemInventoryModel(Base, UUIDMixin):
    """ORM model for the ``mega_gem_inventory`` table.

    Columns:
        id: UUID primary key (from ``UUIDMixin``).
        player_id: FK to players(id) -- the inventory owner.
        slot_index: Integer 0-4 identifying the mega gem type or shuffle.
        count: Number of mega gems available in this slot (default 0).
    """

    __tablename__ = "mega_gem_inventory"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "slot_index", name="uq_mega_gem_inventory_player_slot"
        ),
    )

    player_id: Mapped[bytes] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
        index=True,
    )

    slot_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
