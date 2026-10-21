"""Integration test fixtures -- real PostgreSQL + Redis.

Session-scoped engine creates/drops all tables once.
Per-test factory truncates tables and flushes Redis between tests.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Import all models so Base.metadata has full table set.
from src.data.models.base import Base  # noqa: F401
from src.data.models.player import PlayerModel  # noqa: F401
from src.data.models.player_stats import PlayerStatsModel  # noqa: F401
from src.data.models.energy_state import EnergyStateModel  # noqa: F401
from src.data.models.match import MatchModel  # noqa: F401
from src.data.models.match_move import MatchMoveModel  # noqa: F401
from src.data.models.session import SessionModel  # noqa: F401
from src.data.models.api_key import ApiKeyModel  # noqa: F401
from src.data.models.vault_artifact import VaultArtifactModel  # noqa: F401
from src.data.models.vault_shield import VaultShieldModel  # noqa: F401
from src.data.models.artifact_definition import ArtifactDefinitionModel  # noqa: F401
from src.data.models.raid_log import RaidLogModel  # noqa: F401
from src.data.models.ad_free_status import AdFreeStatusModel  # noqa: F401
from src.data.models.ad_reward import AdRewardModel  # noqa: F401
from src.data.models.ad_impression import AdImpressionModel  # noqa: F401
from src.data.models.ad_request import AdRequestModel  # noqa: F401
from src.data.models.bot_earnings_daily import BotEarningsDailyModel  # noqa: F401
from src.data.models.bot_attribution_entry import BotAttributionEntryModel  # noqa: F401
from src.data.models.bot_earnings_ledger import BotEarningsLedgerModel  # noqa: F401
from src.data.models.bot_payout_request import BotPayoutRequestModel  # noqa: F401
from src.data.models.event_ad_claim import EventAdClaimModel  # noqa: F401
from src.data.models.event_ad_opportunity import EventAdOpportunityModel  # noqa: F401
from src.data.models.event_match import EventMatchRecordModel  # noqa: F401
from src.data.models.event import EventModel  # noqa: F401
from src.data.models.event_participant import EventParticipantModel  # noqa: F401
from src.data.models.product import ProductModel  # noqa: F401
from src.data.models.purchase_intent import PurchaseIntentModel  # noqa: F401
from src.data.models.purchase import PurchaseModel  # noqa: F401
from src.data.models.refund_notification import RefundNotificationModel  # noqa: F401
from src.data.models.receipt_validation import ReceiptValidationModel  # noqa: F401

from tests.integration.helpers.service_factory import IntegrationServiceFactory

# ---- Database URL (matches service_factory config) -------------------------
_DB_URL = (
    "postgresql+asyncpg://chromacrush:chromacrush_dev"
    "@localhost:5432/chromacrush_test"
)


# ---------------------------------------------------------------------------
# Session-scoped: create/drop all tables once per test session
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create all tables at session start, drop at session end."""
    engine = create_async_engine(_DB_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ---------------------------------------------------------------------------
# Per-test: truncate all tables and flush Redis between tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def factory(db_engine):
    """Per-test factory: truncates all tables and flushes Redis.

    Yields an IntegrationServiceFactory with all services wired.
    """
    f = await IntegrationServiceFactory.create()

    yield f

    # ---- Cleanup: truncate all tables (CASCADE) and flush Redis ------
    # Use Base.metadata to dynamically get all table names.
    table_names = [t.name for t in reversed(Base.metadata.sorted_tables)]
    if table_names:
        joined = ", ".join(table_names)
        async with f.data_ctx.session() as session:
            await session.execute(text(f"TRUNCATE TABLE {joined} CASCADE"))

    await f.data_ctx.redis.flushdb()
    await f.cleanup()
