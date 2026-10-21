"""Bot earnings module tables.

Revision ID: 009
Revises: 007
Create Date: 2026-02-06

Creates the four tables owned by the bot_earnings module:
- ``bot_earnings_ledger`` -- cumulative earnings per bot
- ``bot_attribution_entries`` -- individual attribution records
- ``bot_payout_requests`` -- payout request lifecycle
- ``bot_earnings_daily`` -- daily aggregated earnings
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. bot_earnings_ledger
    # ------------------------------------------------------------------
    op.create_table(
        "bot_earnings_ledger",
        sa.Column(
            "bot_player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            primary_key=True,
        ),
        sa.Column(
            "owner_player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column(
            "total_earned_cents", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "total_paid_out_cents", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "pending_payout_cents", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_attribution_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("total_earned_cents >= 0", name="chk_earned_non_negative"),
        sa.CheckConstraint("total_paid_out_cents >= 0", name="chk_paid_non_negative"),
        sa.CheckConstraint(
            "pending_payout_cents >= 0", name="chk_pending_non_negative"
        ),
        sa.CheckConstraint(
            "total_paid_out_cents <= total_earned_cents", name="chk_paid_le_earned"
        ),
    )

    op.create_index(
        "idx_bot_earnings_owner", "bot_earnings_ledger", ["owner_player_id"]
    )
    op.create_index(
        "idx_bot_earnings_last_sync", "bot_earnings_ledger", ["last_sync_at"]
    )

    # ------------------------------------------------------------------
    # 2. bot_attribution_entries
    # ------------------------------------------------------------------
    op.create_table(
        "bot_attribution_entries",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "bot_player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column("match_id", UUID(as_uuid=True), nullable=False),
        sa.Column("ad_impression_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column(
            "opponent_player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column("estimated_impression_revenue_cents", sa.Integer(), nullable=False),
        sa.Column("attribution_share_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("attributed_cents", sa.Integer(), nullable=False),
        sa.Column("attribution_date", sa.Date(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "estimated_impression_revenue_cents >= 0", name="chk_revenue_non_negative"
        ),
        sa.CheckConstraint(
            "attribution_share_percent >= 0 AND attribution_share_percent <= 100",
            name="chk_share_valid",
        ),
        sa.CheckConstraint("attributed_cents >= 0", name="chk_attributed_non_negative"),
    )

    op.create_index(
        "idx_attribution_bot",
        "bot_attribution_entries",
        ["bot_player_id", "attribution_date"],
        postgresql_ops={"attribution_date": "DESC"},
    )
    op.create_index(
        "idx_attribution_date", "bot_attribution_entries", ["attribution_date"]
    )
    op.create_index("idx_attribution_match", "bot_attribution_entries", ["match_id"])
    op.create_index(
        "idx_attribution_recorded", "bot_attribution_entries", ["recorded_at"]
    )

    # ------------------------------------------------------------------
    # 3. bot_payout_requests
    # ------------------------------------------------------------------
    op.create_table(
        "bot_payout_requests",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "bot_player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column(
            "owner_player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("hold_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "processed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=True,
        ),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("amount_cents > 0", name="chk_amount_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'rejected', 'cancelled')",
            name="chk_valid_status",
        ),
    )

    op.create_index(
        "idx_payout_bot",
        "bot_payout_requests",
        ["bot_player_id", "requested_at"],
        postgresql_ops={"requested_at": "DESC"},
    )
    op.create_index(
        "idx_payout_status",
        "bot_payout_requests",
        ["status"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "idx_payout_owner",
        "bot_payout_requests",
        ["owner_player_id", "requested_at"],
        postgresql_ops={"requested_at": "DESC"},
    )
    op.create_index(
        "idx_payout_hold",
        "bot_payout_requests",
        ["hold_until"],
        postgresql_where=sa.text("status = 'pending' AND hold_until IS NOT NULL"),
    )

    # ------------------------------------------------------------------
    # 4. bot_earnings_daily
    # ------------------------------------------------------------------
    op.create_table(
        "bot_earnings_daily",
        sa.Column(
            "bot_player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id"),
            nullable=False,
        ),
        sa.Column("earnings_date", sa.Date(), nullable=False),
        sa.Column(
            "attributions_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("matches_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "impressions_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("earnings_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("bot_player_id", "earnings_date"),
    )

    op.create_index("idx_daily_date", "bot_earnings_daily", ["earnings_date"])


def downgrade() -> None:
    # Drop in reverse creation order
    op.drop_index("idx_daily_date", table_name="bot_earnings_daily")
    op.drop_table("bot_earnings_daily")

    op.drop_index("idx_payout_hold", table_name="bot_payout_requests")
    op.drop_index("idx_payout_owner", table_name="bot_payout_requests")
    op.drop_index("idx_payout_status", table_name="bot_payout_requests")
    op.drop_index("idx_payout_bot", table_name="bot_payout_requests")
    op.drop_table("bot_payout_requests")

    op.drop_index("idx_attribution_recorded", table_name="bot_attribution_entries")
    op.drop_index("idx_attribution_match", table_name="bot_attribution_entries")
    op.drop_index("idx_attribution_date", table_name="bot_attribution_entries")
    op.drop_index("idx_attribution_bot", table_name="bot_attribution_entries")
    op.drop_table("bot_attribution_entries")

    op.drop_index("idx_bot_earnings_last_sync", table_name="bot_earnings_ledger")
    op.drop_index("idx_bot_earnings_owner", table_name="bot_earnings_ledger")
    op.drop_table("bot_earnings_ledger")
