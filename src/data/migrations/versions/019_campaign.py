"""Campaign tables: player campaign level + campaign attempts.

Revision ID: 019
Revises: 018
Create Date: 2026-02-21

Adds ``campaign_level`` column to the ``players`` table and creates the
``campaign_attempts`` table for tracking single-player campaign progress.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add campaign_level to players.
    op.add_column(
        "players",
        sa.Column(
            "campaign_level",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    # Create campaign_attempts table.
    op.create_table(
        "campaign_attempts",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column(
            "level_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "board_seed",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "board_state",
            JSONB(),
            nullable=True,
        ),
        sa.Column(
            "moves_remaining",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "obstacles_remaining",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="in_progress",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('in_progress', 'won', 'lost', 'abandoned')",
            name="ck_campaign_attempts_status",
        ),
    )

    op.create_index(
        "ix_campaign_attempts_player_id",
        "campaign_attempts",
        ["player_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_campaign_attempts_player_id")
    op.drop_table("campaign_attempts")
    op.drop_column("players", "campaign_level")
