"""Add score column to campaign_attempts.

Revision ID: 020
Revises: 019
Create Date: 2026-02-22

Tracks cumulative score per campaign attempt so mega activation seeds
can XOR with ``current_score`` (matching PvP behaviour for unique
special-gem placement).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaign_attempts",
        sa.Column(
            "score",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("campaign_attempts", "score")
