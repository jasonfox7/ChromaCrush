"""Event module tables (events, event_participants, event_matches).

Revision ID: 006
Revises: 005
Create Date: 2026-02-06

Creates the three tables owned by the events module:
- ``events`` -- time-limited event definitions
- ``event_participants`` -- player participation records
- ``event_matches`` -- individual match records within events
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create events table
    # ------------------------------------------------------------------
    op.create_table(
        "events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column("scoring_type", sa.String(30), nullable=False),
        sa.Column(
            "entry_requirements",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "reward_tiers",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "rules", sa.dialects.postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("max_participants", sa.Integer(), nullable=True),
        sa.Column(
            "participant_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by", UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=True
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("end_at > start_at", name="check_event_dates"),
    )

    op.create_index("idx_events_status", "events", ["status"])
    op.create_index("idx_events_type", "events", ["event_type"])
    op.create_index(
        "idx_events_start_at",
        "events",
        ["start_at"],
        postgresql_where=sa.text("status = 'scheduled'"),
    )
    op.create_index(
        "idx_events_end_at",
        "events",
        ["end_at"],
        postgresql_where=sa.text("status = 'active'"),
    )

    # ------------------------------------------------------------------
    # 2. Create event_participants table
    # ------------------------------------------------------------------
    op.create_table(
        "event_participants",
        sa.Column(
            "event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            primary_key=True,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_match_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_rank", sa.Integer(), nullable=True),
        sa.Column(
            "rewards_claimed", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("reward_tier", sa.String(50), nullable=True),
        sa.Column("last_match_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "idx_event_participants_player", "event_participants", ["player_id"]
    )
    op.create_index(
        "idx_event_participants_score",
        "event_participants",
        ["event_id", "total_score"],
    )
    op.create_index(
        "idx_event_participants_active",
        "event_participants",
        ["event_id"],
        postgresql_where=sa.text("left_at IS NULL"),
    )

    # ------------------------------------------------------------------
    # 3. Create event_matches table
    # ------------------------------------------------------------------
    op.create_table(
        "event_matches",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_id", UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=False
        ),
        sa.Column("match_id", UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("chain_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gems_cleared", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "special_gems_activated", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "event_id", "player_id", "match_id", name="unique_event_match"
        ),
    )

    op.create_index("idx_event_matches_event", "event_matches", ["event_id"])
    op.create_index(
        "idx_event_matches_player", "event_matches", ["event_id", "player_id"]
    )


def downgrade() -> None:
    # Drop in reverse creation order
    op.drop_index("idx_event_matches_player", table_name="event_matches")
    op.drop_index("idx_event_matches_event", table_name="event_matches")
    op.drop_table("event_matches")

    op.drop_index("idx_event_participants_active", table_name="event_participants")
    op.drop_index("idx_event_participants_score", table_name="event_participants")
    op.drop_index("idx_event_participants_player", table_name="event_participants")
    op.drop_table("event_participants")

    op.drop_index("idx_events_end_at", table_name="events")
    op.drop_index("idx_events_start_at", table_name="events")
    op.drop_index("idx_events_type", table_name="events")
    op.drop_index("idx_events_status", table_name="events")
    op.drop_table("events")
