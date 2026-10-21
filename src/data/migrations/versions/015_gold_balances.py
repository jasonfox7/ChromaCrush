"""Gold balances table for economy system.

Revision ID: 015
Revises: 014
Create Date: 2026-02-14

Creates the ``gold_balances`` table to track player gold currency.
One row per player with current balance and lifetime stats.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gold_balances",
        sa.Column(
            "player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            primary_key=True,
        ),
        sa.Column(
            "balance",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "lifetime_earned",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "lifetime_spent",
            sa.Integer(),
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


def downgrade() -> None:
    op.drop_table("gold_balances")
