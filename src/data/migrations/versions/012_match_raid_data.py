"""Add raid_data JSONB column to matches table.

Revision ID: 012
Revises: 011
Create Date: 2026-02-14

Stores post-match card raid results so the match state endpoint
can return them. Previously raid results were only returned
transiently in the move response.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("raid_data", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("matches", "raid_data")
