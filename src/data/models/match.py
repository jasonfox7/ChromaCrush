"""SQLAlchemy model for the matches table.

Maps the ``matches`` table to the ``MatchModel`` ORM class. Each row represents
a single match between two players, tracking both players' board states, scores,
and move counts independently.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, UUIDMixin


class MatchModel(Base, UUIDMixin):
    """ORM model for the ``matches`` table.

    Columns:
        id: UUID primary key (from ``UUIDMixin``).
        board_seed: Random seed used to generate the initial board.
        initial_board_state: The starting board configuration (JSONB).
        match_type: Type of match (e.g., "standard", "ranked").
        status: Current match status (pending, in_progress, completed, abandoned).
        player1_id: FK to players(id) -- first player.
        player1_board_state: Player 1's current board state (JSONB).
        player1_score: Player 1's current score.
        player1_moves_made: Number of moves player 1 has made.
        player1_moves_remaining: Moves remaining for player 1.
        player1_longest_chain: Longest chain achieved by player 1.
        player1_finished_at: When player 1 finished their moves.
        player2_id: FK to players(id) -- second player.
        player2_board_state: Player 2's current board state (JSONB).
        player2_score: Player 2's current score.
        player2_moves_made: Number of moves player 2 has made.
        player2_moves_remaining: Moves remaining for player 2.
        player2_longest_chain: Longest chain achieved by player 2.
        player2_finished_at: When player 2 finished their moves.
        winner_id: FK to players(id) -- the winning player (nullable until determined).
        forfeit_by: FK to players(id) -- player who forfeited (nullable).
        created_at: When the match was created.
        started_at: When the match started (nullable).
        completed_at: When the match completed (nullable).
        timeout_at: Deadline for match completion.
    """

    __tablename__ = "matches"

    board_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    initial_board_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    match_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="standard"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )

    player1_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=False
    )
    player1_board_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    player1_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    player1_moves_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    player1_moves_remaining: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20
    )
    player1_longest_chain: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    player1_finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    player2_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=False
    )
    player2_board_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    player2_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    player2_moves_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    player2_moves_remaining: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20
    )
    player2_longest_chain: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    player2_finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    raid_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reward_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    winner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=True
    )
    forfeit_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timeout_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint("player1_id != player2_id", name="check_players_different"),
    )
