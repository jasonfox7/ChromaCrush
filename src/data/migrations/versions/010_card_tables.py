"""Card system table (player_cards).

Revision ID: 010
Revises: 009
Create Date: 2026-02-13

Creates the ``player_cards`` table for the card meta-game.
Card definitions live in ``config/card_definitions.json`` (JSON-only,
not stored in the database). The ``card_id`` column is a plain integer
referencing the JSON definition.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "player_cards",
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
            "card_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "acquired_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "source",
            sa.String(32),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(64),
            nullable=True,
        ),
        sa.Column(
            "level",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "player_id",
            "position",
            name="uq_player_cards_player_position",
        ),
    )

    op.create_index(
        "idx_player_cards_player",
        "player_cards",
        ["player_id"],
    )
    op.create_index(
        "idx_player_cards_card",
        "player_cards",
        ["card_id"],
    )
    op.create_index(
        "idx_player_cards_source",
        "player_cards",
        ["source"],
    )


def downgrade() -> None:
    op.drop_index("idx_player_cards_source", table_name="player_cards")
    op.drop_index("idx_player_cards_card", table_name="player_cards")
    op.drop_index("idx_player_cards_player", table_name="player_cards")
    op.drop_table("player_cards")
