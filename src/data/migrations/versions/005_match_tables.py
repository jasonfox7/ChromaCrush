"""Match module tables (matches, match_moves).

Revision ID: 005
Revises: 004
Create Date: 2026-02-06

Creates the two tables owned by the match module:
- ``matches`` — match instances between two players
- ``match_moves`` — individual move records within matches
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create matches table
    # ------------------------------------------------------------------

    op.create_table(
        "matches",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "board_seed",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "initial_board_state",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "match_type",
            sa.String(20),
            nullable=False,
            server_default="standard",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "player1_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column(
            "player1_board_state",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "player1_score",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "player1_moves_made",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "player1_moves_remaining",
            sa.Integer(),
            nullable=False,
            server_default="20",
        ),
        sa.Column(
            "player1_longest_chain",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "player1_finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "player2_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column(
            "player2_board_state",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "player2_score",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "player2_moves_made",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "player2_moves_remaining",
            sa.Integer(),
            nullable=False,
            server_default="20",
        ),
        sa.Column(
            "player2_longest_chain",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "player2_finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "winner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=True,
        ),
        sa.Column(
            "forfeit_by",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "timeout_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "player1_id != player2_id",
            name="check_players_different",
        ),
    )

    # Indexes for matches table
    op.create_index(
        "idx_matches_status",
        "matches",
        ["status"],
    )

    op.create_index(
        "idx_matches_player1",
        "matches",
        ["player1_id"],
        postgresql_where=sa.text("status IN ('pending', 'in_progress')"),
    )

    op.create_index(
        "idx_matches_player2",
        "matches",
        ["player2_id"],
        postgresql_where=sa.text("status IN ('pending', 'in_progress')"),
    )

    op.create_index(
        "idx_matches_timeout",
        "matches",
        ["timeout_at"],
        postgresql_where=sa.text("status = 'in_progress'"),
    )

    # ------------------------------------------------------------------
    # 2. Create match_moves table
    # ------------------------------------------------------------------

    op.create_table(
        "match_moves",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "match_id",
            UUID(as_uuid=True),
            sa.ForeignKey("matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column(
            "move_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "from_row",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "from_col",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "to_row",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "to_col",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "client_timestamp_ms",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "board_before",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "board_after",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "score_earned",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "chain_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "gems_cleared",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "special_gems_created",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "special_gems_activated",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "match_id",
            "player_id",
            "move_number",
            name="unique_player_move",
        ),
    )

    # Indexes for match_moves table
    op.create_index(
        "idx_match_moves_match",
        "match_moves",
        ["match_id"],
    )

    op.create_index(
        "idx_match_moves_player",
        "match_moves",
        ["match_id", "player_id"],
    )


def downgrade() -> None:
    # Drop in reverse creation order (respecting FK dependencies)

    # 2. match_moves
    op.drop_index("idx_match_moves_player", table_name="match_moves")
    op.drop_index("idx_match_moves_match", table_name="match_moves")
    op.drop_table("match_moves")

    # 1. matches
    op.drop_index("idx_matches_timeout", table_name="matches")
    op.drop_index("idx_matches_player2", table_name="matches")
    op.drop_index("idx_matches_player1", table_name="matches")
    op.drop_index("idx_matches_status", table_name="matches")
    op.drop_table("matches")
