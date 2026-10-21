"""SQLAlchemy model for the campaign_attempts table.

Maps the ``campaign_attempts`` table to the ``CampaignAttemptModel`` ORM class.
One row per campaign level attempt, tracking board state and progress.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, TimestampMixin, UUIDMixin


class CampaignAttemptModel(Base, UUIDMixin, TimestampMixin):
    """ORM model for the ``campaign_attempts`` table.

    Columns:
        id: UUID primary key (from ``UUIDMixin``).
        player_id: UUID foreign key referencing ``players.id``.
        level_number: Campaign level being attempted.
        board_seed: RNG seed used for board generation.
        board_state: JSONB snapshot of current board (cells + functions).
        moves_remaining: Moves left in this attempt.
        obstacles_remaining: Obstacle cells still on the board.
        status: ``"in_progress"``, ``"won"``, ``"lost"``, or ``"abandoned"``.
        score: Cumulative score accumulated during this attempt.
        started_at: When the attempt began.
        completed_at: When the attempt ended (null if in progress).
        created_at: Row creation timestamp (from ``TimestampMixin``).
        updated_at: Last-modified timestamp (from ``TimestampMixin``).
    """

    __tablename__ = "campaign_attempts"

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable=False,
    )

    level_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    board_seed: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    board_state: Mapped[dict | None] = mapped_column(
        JSONB(),
        nullable=True,
    )

    moves_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    obstacles_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="in_progress",
    )

    score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
