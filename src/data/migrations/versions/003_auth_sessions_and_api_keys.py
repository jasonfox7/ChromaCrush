"""Auth sessions and API keys tables.

Revision ID: 003
Revises: 002
Create Date: 2026-02-05

Creates ``sessions`` and ``api_keys`` tables for the auth module.
Includes partial indexes for active-only queries and prefix-based
API key lookups.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create sessions table
    # ------------------------------------------------------------------

    op.create_table(
        "sessions",
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
            "refresh_token_hash",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "device_info",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Partial indexes for active sessions
    op.create_index(
        "idx_sessions_player",
        "sessions",
        ["player_id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "idx_sessions_expires",
        "sessions",
        ["expires_at"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    # ------------------------------------------------------------------
    # 2. Create api_keys table
    # ------------------------------------------------------------------

    op.create_table(
        "api_keys",
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
            "key_hash",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "key_prefix",
            sa.String(16),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Indexes for API key lookups
    op.create_index(
        "idx_api_keys_player",
        "api_keys",
        ["player_id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "idx_api_keys_prefix",
        "api_keys",
        ["key_prefix"],
    )


def downgrade() -> None:
    # Drop indexes first, then tables
    op.drop_index("idx_api_keys_prefix", table_name="api_keys")
    op.drop_index("idx_api_keys_player", table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_index("idx_sessions_expires", table_name="sessions")
    op.drop_index("idx_sessions_player", table_name="sessions")
    op.drop_table("sessions")
