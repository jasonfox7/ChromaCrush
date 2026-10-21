"""Merge payment and card branches.

Revision ID: 013
Revises: 008, 012
Create Date: 2026-02-14

No-op merge — payment (008) and card/raid (009-012) branches
were parallel. This merge revision gives a single head.
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = ("008", "012")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
