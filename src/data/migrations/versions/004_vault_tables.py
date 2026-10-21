"""Vault module tables (vault_artifacts, vault_shields, artifact_definitions, raid_logs).

Revision ID: 004
Revises: 003
Create Date: 2026-02-05

Creates the four tables owned by the vault module:
- ``artifact_definitions`` — static catalog of artifact types
- ``vault_artifacts`` — player-owned artifact instances
- ``vault_shields`` — one-per-player raid protection shields
- ``raid_logs`` — raid attempt history for cooldown and analytics
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create artifact_definitions table (no FK dependencies)
    # ------------------------------------------------------------------

    op.create_table(
        "artifact_definitions",
        sa.Column(
            "type_id",
            sa.String(64),
            primary_key=True,
        ),
        sa.Column(
            "name",
            sa.String(128),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "rarity",
            sa.String(16),
            nullable=False,
        ),
        sa.Column(
            "artifact_set",
            sa.String(64),
            nullable=False,
        ),
        sa.Column(
            "set_position",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "base_value",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
        ),
        sa.Column(
            "image_url",
            sa.String(512),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "idx_artifact_definitions_rarity",
        "artifact_definitions",
        ["rarity"],
    )
    op.create_index(
        "idx_artifact_definitions_set",
        "artifact_definitions",
        ["artifact_set"],
    )

    # ------------------------------------------------------------------
    # 2. Create vault_artifacts table
    # ------------------------------------------------------------------

    op.create_table(
        "vault_artifacts",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column(
            "artifact_type_id",
            sa.String(64),
            nullable=False,
        ),
        sa.Column(
            "acquired_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "source",
            sa.String(32),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(64),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "idx_vault_artifacts_owner",
        "vault_artifacts",
        ["owner_id"],
    )
    op.create_index(
        "idx_vault_artifacts_type",
        "vault_artifacts",
        ["artifact_type_id"],
    )
    op.create_index(
        "idx_vault_artifacts_source",
        "vault_artifacts",
        ["source"],
    )

    # ------------------------------------------------------------------
    # 3. Create vault_shields table
    # ------------------------------------------------------------------

    op.create_table(
        "vault_shields",
        sa.Column(
            "player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            primary_key=True,
        ),
        sa.Column(
            "activated_at",
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
            "duration_hours",
            sa.Integer(),
            nullable=False,
        ),
    )

    op.create_index(
        "idx_vault_shields_expires",
        "vault_shields",
        ["expires_at"],
    )

    # ------------------------------------------------------------------
    # 4. Create raid_logs table
    # ------------------------------------------------------------------

    op.create_table(
        "raid_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "attacker_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column(
            "defender_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column(
            "success",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "artifact_id",
            UUID(as_uuid=True),
            sa.ForeignKey("vault_artifacts.id"),
            nullable=True,
        ),
        sa.Column(
            "artifact_type_id",
            sa.String(64),
            nullable=True,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "idx_raid_logs_attacker",
        "raid_logs",
        ["attacker_id", sa.text("timestamp DESC")],
    )
    op.create_index(
        "idx_raid_logs_defender",
        "raid_logs",
        ["defender_id", sa.text("timestamp DESC")],
    )
    op.create_index(
        "idx_raid_logs_cooldown",
        "raid_logs",
        ["attacker_id", "defender_id", sa.text("timestamp DESC")],
    )


def downgrade() -> None:
    # Drop in reverse creation order (respecting FK dependencies)

    # 4. raid_logs
    op.drop_index("idx_raid_logs_cooldown", table_name="raid_logs")
    op.drop_index("idx_raid_logs_defender", table_name="raid_logs")
    op.drop_index("idx_raid_logs_attacker", table_name="raid_logs")
    op.drop_table("raid_logs")

    # 3. vault_shields
    op.drop_index("idx_vault_shields_expires", table_name="vault_shields")
    op.drop_table("vault_shields")

    # 2. vault_artifacts
    op.drop_index("idx_vault_artifacts_source", table_name="vault_artifacts")
    op.drop_index("idx_vault_artifacts_type", table_name="vault_artifacts")
    op.drop_index("idx_vault_artifacts_owner", table_name="vault_artifacts")
    op.drop_table("vault_artifacts")

    # 1. artifact_definitions
    op.drop_index("idx_artifact_definitions_set", table_name="artifact_definitions")
    op.drop_index("idx_artifact_definitions_rarity", table_name="artifact_definitions")
    op.drop_table("artifact_definitions")
