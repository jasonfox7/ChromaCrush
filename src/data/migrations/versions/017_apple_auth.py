"""Add apple_user_id and auth_provider columns to players table.

Revision ID: 017
Revises: 016
Create Date: 2026-02-15

Supports Apple Sign-In: apple_user_id stores the Apple `sub` claim,
auth_provider tracks the authentication method (password, apple).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "players",
        sa.Column("apple_user_id", sa.String(255), nullable=True, unique=True),
    )
    op.add_column(
        "players",
        sa.Column(
            "auth_provider",
            sa.String(32),
            nullable=True,
            server_default="password",
        ),
    )


def downgrade() -> None:
    op.drop_column("players", "auth_provider")
    op.drop_column("players", "apple_user_id")
