"""Ad module tables.

Revision ID: 007
Revises: 006
Create Date: 2026-02-06

Creates the six tables owned by the ads module:
- ``ad_requests`` -- ad request lifecycle tracking
- ``ad_impressions`` -- individual impression records
- ``ad_free_status`` -- per-player ad-free status
- ``ad_rewards_granted`` -- rewards from rewarded video completions
- ``event_ad_opportunities`` -- event-specific ad opportunities
- ``event_ad_claims`` -- player claims of event ad opportunities
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. ad_requests
    # ------------------------------------------------------------------
    op.create_table(
        "ad_requests",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "player_id", UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=False
        ),
        sa.Column("ad_type", sa.String(20), nullable=False),
        sa.Column("ad_unit_id", sa.String(100), nullable=True),
        sa.Column("trigger", sa.String(50), nullable=True),
        sa.Column("reward_type", sa.String(30), nullable=True),
        sa.Column("reward_value", sa.Integer(), nullable=True),
        sa.Column("match_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_response", JSONB(), nullable=True),
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
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("idx_ad_requests_player", "ad_requests", ["player_id"])
    op.create_index("idx_ad_requests_status", "ad_requests", ["status"])
    op.create_index(
        "idx_ad_requests_pending_expires",
        "ad_requests",
        ["expires_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # ------------------------------------------------------------------
    # 2. ad_impressions
    # ------------------------------------------------------------------
    op.create_table(
        "ad_impressions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "player_id", UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=False
        ),
        sa.Column(
            "ad_request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ad_requests.id"),
            nullable=True,
        ),
        sa.Column("ad_type", sa.String(20), nullable=False),
        sa.Column("trigger", sa.String(50), nullable=False),
        sa.Column("placement", sa.String(50), nullable=True),
        sa.Column("viewed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("view_duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("match_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_id", UUID(as_uuid=True), nullable=True),
        sa.Column("opponent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("attributed_to", UUID(as_uuid=True), nullable=True),
        sa.Column("attribution_share_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("estimated_revenue_cents", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "recorded_date",
            sa.Date(),
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
    )

    op.create_index("idx_ad_impressions_player", "ad_impressions", ["player_id"])
    op.create_index("idx_ad_impressions_request", "ad_impressions", ["ad_request_id"])
    op.create_index("idx_ad_impressions_match", "ad_impressions", ["match_id"])
    op.create_index(
        "idx_ad_impressions_attributed", "ad_impressions", ["attributed_to"]
    )
    op.create_index("idx_ad_impressions_date", "ad_impressions", ["recorded_date"])

    # ------------------------------------------------------------------
    # 3. ad_free_status
    # ------------------------------------------------------------------
    op.create_table(
        "ad_free_status",
        sa.Column(
            "player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            primary_key=True,
        ),
        sa.Column("is_ad_free", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reason", sa.String(50), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "granted_by", UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=True
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "idx_ad_free_status_active",
        "ad_free_status",
        ["player_id"],
        postgresql_where=sa.text("is_ad_free = true"),
    )
    op.create_index(
        "idx_ad_free_status_expiring",
        "ad_free_status",
        ["expires_at"],
        postgresql_where=sa.text("is_ad_free = true AND expires_at IS NOT NULL"),
    )

    # ------------------------------------------------------------------
    # 4. ad_rewards_granted
    # ------------------------------------------------------------------
    op.create_table(
        "ad_rewards_granted",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "player_id", UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=False
        ),
        sa.Column(
            "ad_request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ad_requests.id"),
            nullable=False,
        ),
        sa.Column(
            "impression_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ad_impressions.id"),
            nullable=False,
        ),
        sa.Column("reward_type", sa.String(30), nullable=False),
        sa.Column("reward_value", sa.Integer(), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("ad_request_id", name="unique_ad_reward"),
    )

    op.create_index("idx_ad_rewards_player", "ad_rewards_granted", ["player_id"])

    # ------------------------------------------------------------------
    # 5. event_ad_opportunities
    # ------------------------------------------------------------------
    op.create_table(
        "event_ad_opportunities",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column(
            "event_id", UUID(as_uuid=True), sa.ForeignKey("events.id"), primary_key=True
        ),
        sa.Column("ad_type", sa.String(20), nullable=False),
        sa.Column("reward_type", sa.String(30), nullable=False),
        sa.Column("reward_value", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "times_available_per_player",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ------------------------------------------------------------------
    # 6. event_ad_claims
    # ------------------------------------------------------------------
    op.create_table(
        "event_ad_claims",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "event_id", UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False
        ),
        sa.Column("opportunity_id", sa.String(100), nullable=False),
        sa.Column(
            "player_id", UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=False
        ),
        sa.Column(
            "impression_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ad_impressions.id"),
            nullable=False,
        ),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "event_id",
            "opportunity_id",
            "player_id",
            "claimed_at",
            name="unique_event_ad_claim",
        ),
    )

    op.create_index(
        "idx_event_ad_claims_player", "event_ad_claims", ["event_id", "player_id"]
    )
    op.create_index(
        "idx_event_ad_claims_opp", "event_ad_claims", ["event_id", "opportunity_id"]
    )


def downgrade() -> None:
    # Drop in reverse creation order
    op.drop_index("idx_event_ad_claims_opp", table_name="event_ad_claims")
    op.drop_index("idx_event_ad_claims_player", table_name="event_ad_claims")
    op.drop_table("event_ad_claims")

    op.drop_table("event_ad_opportunities")

    op.drop_index("idx_ad_rewards_player", table_name="ad_rewards_granted")
    op.drop_table("ad_rewards_granted")

    op.drop_index("idx_ad_free_status_expiring", table_name="ad_free_status")
    op.drop_index("idx_ad_free_status_active", table_name="ad_free_status")
    op.drop_table("ad_free_status")

    op.drop_index("idx_ad_impressions_date", table_name="ad_impressions")
    op.drop_index("idx_ad_impressions_attributed", table_name="ad_impressions")
    op.drop_index("idx_ad_impressions_match", table_name="ad_impressions")
    op.drop_index("idx_ad_impressions_request", table_name="ad_impressions")
    op.drop_index("idx_ad_impressions_player", table_name="ad_impressions")
    op.drop_table("ad_impressions")

    op.drop_index("idx_ad_requests_pending_expires", table_name="ad_requests")
    op.drop_index("idx_ad_requests_status", table_name="ad_requests")
    op.drop_index("idx_ad_requests_player", table_name="ad_requests")
    op.drop_table("ad_requests")
