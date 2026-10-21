"""Payment module tables.

Revision ID: 008
Revises: 007
Create Date: 2026-02-06

Creates the five tables owned by the payments module:
- ``products`` -- available in-app purchase products
- ``purchase_intents`` -- purchase intent tracking
- ``purchases`` -- completed purchase records
- ``receipt_validations`` -- receipt validation audit trail
- ``refund_notifications`` -- refund notification tracking
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. products
    # ------------------------------------------------------------------
    op.create_table(
        "products",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("product_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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

    # ------------------------------------------------------------------
    # 2. purchase_intents
    # ------------------------------------------------------------------
    op.create_table(
        "purchase_intents",
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
            "product_id", sa.String(100), sa.ForeignKey("products.id"), nullable=False
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
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
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "idx_purchase_intents_player", "purchase_intents", ["player_id", "created_at"]
    )
    op.create_index(
        "idx_purchase_intents_status",
        "purchase_intents",
        ["status"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # ------------------------------------------------------------------
    # 3. purchases
    # ------------------------------------------------------------------
    op.create_table(
        "purchases",
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
            "product_id", sa.String(100), sa.ForeignKey("products.id"), nullable=False
        ),
        sa.Column(
            "intent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("purchase_intents.id"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("transaction_id", sa.String(255), nullable=False),
        sa.Column("original_transaction_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_sandbox", sa.Boolean(), nullable=False, server_default="false"),
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
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("provider", "transaction_id", name="unique_transaction"),
    )

    op.create_index("idx_purchases_player", "purchases", ["player_id", "created_at"])
    op.create_index(
        "idx_purchases_transaction", "purchases", ["provider", "transaction_id"]
    )
    op.create_index("idx_purchases_status", "purchases", ["status"])

    # ------------------------------------------------------------------
    # 4. receipt_validations
    # ------------------------------------------------------------------
    op.create_table(
        "receipt_validations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "purchase_id",
            UUID(as_uuid=True),
            sa.ForeignKey("purchases.id"),
            nullable=True,
        ),
        sa.Column(
            "player_id", UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=False
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("receipt_data", sa.Text(), nullable=False),
        sa.Column("receipt_hash", sa.String(64), nullable=False),
        sa.Column("validation_result", sa.String(20), nullable=False),
        sa.Column("validation_response", JSONB(), nullable=True),
        sa.Column("transaction_id", sa.String(255), nullable=True),
        sa.Column("product_id", sa.String(100), nullable=True),
        sa.Column("purchase_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_sandbox", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "idx_receipt_validations_player",
        "receipt_validations",
        ["player_id", "created_at"],
    )
    op.create_index(
        "idx_receipt_validations_hash", "receipt_validations", ["receipt_hash"]
    )
    op.create_index(
        "idx_receipt_validations_transaction",
        "receipt_validations",
        ["transaction_id"],
        postgresql_where=sa.text("transaction_id IS NOT NULL"),
    )

    # ------------------------------------------------------------------
    # 5. refund_notifications
    # ------------------------------------------------------------------
    op.create_table(
        "refund_notifications",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("transaction_id", sa.String(255), nullable=False),
        sa.Column("original_transaction_id", sa.String(255), nullable=True),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("notification_payload", JSONB(), nullable=False),
        sa.Column(
            "purchase_id",
            UUID(as_uuid=True),
            sa.ForeignKey("purchases.id"),
            nullable=True,
        ),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("process_result", sa.String(20), nullable=True),
        sa.Column("process_error", sa.Text(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "idx_refund_notifications_transaction",
        "refund_notifications",
        ["provider", "transaction_id"],
    )
    op.create_index(
        "idx_refund_notifications_unprocessed",
        "refund_notifications",
        ["processed"],
        postgresql_where=sa.text("processed = false"),
    )


def downgrade() -> None:
    # Drop in reverse creation order
    op.drop_index(
        "idx_refund_notifications_unprocessed", table_name="refund_notifications"
    )
    op.drop_index(
        "idx_refund_notifications_transaction", table_name="refund_notifications"
    )
    op.drop_table("refund_notifications")

    op.drop_index(
        "idx_receipt_validations_transaction", table_name="receipt_validations"
    )
    op.drop_index("idx_receipt_validations_hash", table_name="receipt_validations")
    op.drop_index("idx_receipt_validations_player", table_name="receipt_validations")
    op.drop_table("receipt_validations")

    op.drop_index("idx_purchases_status", table_name="purchases")
    op.drop_index("idx_purchases_transaction", table_name="purchases")
    op.drop_index("idx_purchases_player", table_name="purchases")
    op.drop_table("purchases")

    op.drop_index("idx_purchase_intents_status", table_name="purchase_intents")
    op.drop_index("idx_purchase_intents_player", table_name="purchase_intents")
    op.drop_table("purchase_intents")

    op.drop_table("products")
