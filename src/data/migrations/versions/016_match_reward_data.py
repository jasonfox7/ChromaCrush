"""Add reward_data JSONB column to matches table.

Revision ID: 016
Revises: 015
Create Date: 2026-02-15

Stores post-match card reward results so the match state endpoint
can return them alongside raid results.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("reward_data", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("matches", "reward_data")
