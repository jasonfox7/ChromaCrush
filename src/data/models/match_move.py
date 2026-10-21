"""SQLAlchemy model for the match_moves table.

Maps the ``match_moves`` table to the ``MatchMoveModel`` ORM class. Each row
represents a single move made by a player in a match, including board states
before and after, scoring details, and chain information.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class MatchMoveModel(Base, UUIDMixin):
    """ORM model for the ``match_moves`` table.

    Columns:
        id: UUID primary key (from ``UUIDMixin``).
        match_id: FK to matches(id) -- the match this move belongs to.
        player_id: FK to players(id) -- the player who made the move.
        move_number: Sequential move number for this player in this match.
        from_row: Source row coordinate.
        from_col: Source column coordinate.
        to_row: Destination row coordinate.
        to_col: Destination column coordinate.
        client_timestamp_ms: Client-side timestamp in milliseconds.
        board_before: Board state before this move (JSONB).
        board_after: Board state after this move (JSONB).
        score_earned: Points earned from this move.
        chain_count: Number of chains triggered.
        gems_cleared: Total gems cleared.
        special_gems_created: List of special gems created (JSONB).
        special_gems_activated: List of special gems activated (JSONB).
        created_at: When the move was recorded.
    """

    __tablename__ = "match_moves"

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=False
    )
    move_number: Mapped[int] = mapped_column(Integer, nullable=False)

    from_row: Mapped[int] = mapped_column(Integer, nullable=False)
    from_col: Mapped[int] = mapped_column(Integer, nullable=False)
    to_row: Mapped[int] = mapped_column(Integer, nullable=False)
    to_col: Mapped[int] = mapped_column(Integer, nullable=False)
    client_timestamp_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)

    board_before: Mapped[dict] = mapped_column(JSONB, nullable=False)
    board_after: Mapped[dict] = mapped_column(JSONB, nullable=False)
    score_earned: Mapped[int] = mapped_column(Integer, nullable=False)
    chain_count: Mapped[int] = mapped_column(Integer, nullable=False)
    gems_cleared: Mapped[int] = mapped_column(Integer, nullable=False)
    special_gems_created: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    special_gems_activated: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "match_id", "player_id", "move_number", name="unique_player_move"
        ),
    )
