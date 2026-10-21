"""SQLAlchemy model for the player_stats table.

Maps the ``player_stats`` table to the ``PlayerStatsModel`` ORM class. The
domain ``PlayerStats`` dataclass (``src.core.types.player``) is the public
interface; ``PlayerStatsModel`` is internal to the data layer and never leaks
into modules.
"""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin


class PlayerStatsModel(Base, TimestampMixin):
    """ORM model for the ``player_stats`` table.

    Columns:
        player_id: UUID foreign key referencing ``players.id`` (primary key).
        total_matches: Total number of matches played.
        wins: Total wins.
        losses: Total losses.
        draws: Total draws.
        highest_score: Highest score achieved in a single match.
        longest_chain: Longest cascade chain achieved.
        total_gems_matched: Cumulative gems matched across all matches.
        created_at: Row creation timestamp (from ``TimestampMixin``).
        updated_at: Last-modified timestamp (from ``TimestampMixin``).
    """

    __tablename__ = "player_stats"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        primary_key=True,
    )

    total_matches: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    wins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    losses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    draws: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    highest_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    longest_chain: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_gems_matched: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )
