"""Add missing indexes on frequently queried columns.

Revision ID: 021
Revises: 020
Create Date: 2026-03-21

Adds indexes for columns used in WHERE clauses by repository queries
that were previously doing full table scans:
- campaign_attempts (player_id, status)
- raid_logs (attacker_id, defender_id)
- match_moves (player_id)
- gold_transactions (player_id)
- bot_payout_requests (bot_player_id, status)
- ad_free_status (expires_at)
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # campaign_attempts: find_active_by_player() filters (player_id, status)
    op.create_index(
        "idx_campaign_attempts_player_status",
        "campaign_attempts",
        ["player_id", "status"],
    )
    # raid_logs: find_by_player() filters on attacker_id
    op.create_index("idx_raid_logs_attacker_id", "raid_logs", ["attacker_id"])
    # raid_logs: find_by_player() filters on defender_id
    op.create_index("idx_raid_logs_defender_id", "raid_logs", ["defender_id"])
    # raid_logs: find_last_raid_between(attacker_id, defender_id)
    op.create_index(
        "idx_raid_logs_attacker_defender",
        "raid_logs",
        ["attacker_id", "defender_id"],
    )
    # match_moves: count_by_player(match_id, player_id) — match_id already indexed
    op.create_index("idx_match_moves_player_id", "match_moves", ["player_id"])
    # gold_transactions: find_by_player(player_id)
    op.create_index(
        "idx_gold_transactions_player_id", "gold_transactions", ["player_id"]
    )
    # bot_payout_requests: find_by_bot(bot_player_id, status)
    op.create_index(
        "idx_bot_payout_requests_bot_status",
        "bot_payout_requests",
        ["bot_player_id", "status"],
    )
    # ad_free_status: find_expiring(before) filters expires_at < before
    op.create_index(
        "idx_ad_free_status_expires_at", "ad_free_status", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_ad_free_status_expires_at", table_name="ad_free_status")
    op.drop_index(
        "idx_bot_payout_requests_bot_status", table_name="bot_payout_requests"
    )
    op.drop_index("idx_gold_transactions_player_id", table_name="gold_transactions")
    op.drop_index("idx_match_moves_player_id", table_name="match_moves")
    op.drop_index("idx_raid_logs_attacker_defender", table_name="raid_logs")
    op.drop_index("idx_raid_logs_defender_id", table_name="raid_logs")
    op.drop_index("idx_raid_logs_attacker_id", table_name="raid_logs")
    op.drop_index(
        "idx_campaign_attempts_player_status", table_name="campaign_attempts"
    )
