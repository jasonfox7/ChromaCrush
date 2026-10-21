"""Gold transactions ledger table for audit trail.

Revision ID: 018
Revises: 017
Create Date: 2026-02-17

Creates the ``gold_transactions`` table — an immutable append-only ledger
recording every gold balance change (IAP purchase, card sell, marketplace
buy, refund reversal).  Required for Apple consumable IAP compliance.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gold_transactions",
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
            "tx_type",
            sa.String(20),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "balance_after",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(100),
            nullable=False,
        ),
        sa.Column(
            "reference_id",
            sa.String(200),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "tx_type IN ('purchase', 'earned', 'spent', 'refund')",
            name="ck_gold_transactions_tx_type",
        ),
    )

    op.create_index(
        "ix_gold_transactions_player_id",
        "gold_transactions",
        ["player_id"],
    )
    op.create_index(
        "ix_gold_transactions_reference_id",
        "gold_transactions",
        ["reference_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_gold_transactions_reference_id")
    op.drop_index("ix_gold_transactions_player_id")
    op.drop_table("gold_transactions")
