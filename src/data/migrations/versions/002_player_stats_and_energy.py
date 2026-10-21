"""Player stats and energy states tables, plus player table additions.

Revision ID: 002
Revises: 001
Create Date: 2026-02-05

Creates ``player_stats`` and ``energy_states`` tables.
Adds ``username_lower``, ``email``, and ``deleted_at`` columns to ``players``.
Adds partial indexes for soft-delete-aware queries.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Extend players table
    # ------------------------------------------------------------------

    # Add username_lower for case-insensitive uniqueness
    op.add_column(
        "players",
        sa.Column("username_lower", sa.String(64), nullable=True),
    )

    # Backfill username_lower from existing username values
    op.execute("UPDATE players SET username_lower = LOWER(username)")

    # Now make it NOT NULL and UNIQUE
    op.alter_column("players", "username_lower", nullable=False)
    op.create_unique_constraint(
        "uq_players_username_lower", "players", ["username_lower"]
    )

    # Add email column (optional, unique when present)
    op.add_column(
        "players",
        sa.Column("email", sa.String(255), nullable=True),
    )
    op.create_unique_constraint("uq_players_email", "players", ["email"])

    # Add deleted_at for soft deletes
    op.add_column(
        "players",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add partial indexes for active (non-deleted) players
    op.create_index(
        "idx_players_elo_active",
        "players",
        ["elo_rating"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_players_type_active",
        "players",
        ["player_type"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------------------------
    # 2. Create player_stats table
    # ------------------------------------------------------------------

    op.create_table(
        "player_stats",
        sa.Column(
            "player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            primary_key=True,
        ),
        sa.Column(
            "total_matches",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "wins",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "losses",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "draws",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "highest_score",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "longest_chain",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_gems_matched",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
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
    )

    # ------------------------------------------------------------------
    # 3. Create energy_states table
    # ------------------------------------------------------------------

    op.create_table(
        "energy_states",
        sa.Column(
            "player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            primary_key=True,
        ),
        sa.Column(
            "hearts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5"),
        ),
        sa.Column(
            "max_hearts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5"),
        ),
        sa.Column(
            "last_regen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "daily_streak",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "last_login_date",
            sa.Date(),
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
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("energy_states")
    op.drop_table("player_stats")

    # Remove player table additions
    op.drop_index("idx_players_type_active", table_name="players")
    op.drop_index("idx_players_elo_active", table_name="players")
    op.drop_column("players", "deleted_at")
    op.drop_constraint("uq_players_email", "players", type_="unique")
    op.drop_column("players", "email")
    op.drop_constraint("uq_players_username_lower", "players", type_="unique")
    op.drop_column("players", "username_lower")
