"""Make board state columns nullable for post-match cleanup.

Revision ID: 014
Revises: 013
Create Date: 2026-02-14

After a match completes, board states and move records are cleaned up
to reclaim storage. Nullable columns allow setting board states to NULL.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("matches", "initial_board_state", nullable=True)
    op.alter_column("matches", "player1_board_state", nullable=True)
    op.alter_column("matches", "player2_board_state", nullable=True)


def downgrade() -> None:
    op.alter_column("matches", "initial_board_state", nullable=False)
    op.alter_column("matches", "player1_board_state", nullable=False)
    op.alter_column("matches", "player2_board_state", nullable=False)
