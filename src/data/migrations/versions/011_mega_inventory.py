"""Mega gem inventory table.

Revision ID: 011
Revises: 010
Create Date: 2026-02-14

Creates the ``mega_gem_inventory`` table for storing player mega gem counts.
5 slots per player: 0-3 for mega gem types, 4 for shuffle.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mega_gem_inventory",
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
            "slot_index",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.CheckConstraint(
            "slot_index BETWEEN 0 AND 4",
            name="ck_mega_gem_inventory_slot_range",
        ),
        sa.CheckConstraint(
            "count >= 0",
            name="ck_mega_gem_inventory_count_non_negative",
        ),
        sa.UniqueConstraint(
            "player_id",
            "slot_index",
            name="uq_mega_gem_inventory_player_slot",
        ),
    )

    op.create_index(
        "idx_mega_gem_inventory_player",
        "mega_gem_inventory",
        ["player_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_mega_gem_inventory_player", table_name="mega_gem_inventory")
    op.drop_table("mega_gem_inventory")
