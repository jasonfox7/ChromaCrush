"""Initial schema -- players table.

Revision ID: 001
Revises: None
Create Date: 2026-02-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "username",
            sa.String(64),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "player_type",
            sa.String(16),
            nullable=False,
            server_default="human",
        ),
        sa.Column(
            "elo_rating",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1000"),
        ),
        sa.Column(
            "password_hash",
            sa.String(256),
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

    op.create_index("idx_players_username", "players", ["username"])
    op.create_index("idx_players_elo_rating", "players", ["elo_rating"])


def downgrade() -> None:
    op.drop_index("idx_players_elo_rating", table_name="players")
    op.drop_index("idx_players_username", table_name="players")
    op.drop_table("players")
