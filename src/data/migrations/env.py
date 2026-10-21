"""Alembic migration environment.

Loads the database URL dynamically from the ConfigService and runs
migrations against the PostgreSQL database using an async engine.

Offline mode uses a plain URL; online mode creates an async engine
and bridges to Alembic's synchronous runner with ``run_sync``.
"""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.core.config import ConfigService

# Import the declarative base so Alembic can see the metadata.
from src.data.models.base import Base

# Import all models to ensure their tables are registered with Base.metadata.
from src.data.models.player import PlayerModel  # noqa: F401
from src.data.models.player_stats import PlayerStatsModel  # noqa: F401
from src.data.models.energy_state import EnergyStateModel  # noqa: F401
from src.data.models.session import SessionModel  # noqa: F401
from src.data.models.api_key import ApiKeyModel  # noqa: F401
from src.data.models.vault_artifact import VaultArtifactModel  # noqa: F401
from src.data.models.vault_shield import VaultShieldModel  # noqa: F401
from src.data.models.artifact_definition import ArtifactDefinitionModel  # noqa: F401
from src.data.models.raid_log import RaidLogModel  # noqa: F401
from src.data.models.match import MatchModel  # noqa: F401
from src.data.models.match_move import MatchMoveModel  # noqa: F401
from src.data.models.event import EventModel  # noqa: F401
from src.data.models.event_participant import EventParticipantModel  # noqa: F401
from src.data.models.event_match import EventMatchRecordModel  # noqa: F401
from src.data.models.ad_request import AdRequestModel  # noqa: F401
from src.data.models.ad_impression import AdImpressionModel  # noqa: F401
from src.data.models.ad_free_status import AdFreeStatusModel  # noqa: F401
from src.data.models.ad_reward import AdRewardModel  # noqa: F401
from src.data.models.event_ad_opportunity import EventAdOpportunityModel  # noqa: F401
from src.data.models.event_ad_claim import EventAdClaimModel  # noqa: F401
from src.data.models.product import ProductModel  # noqa: F401
from src.data.models.purchase_intent import PurchaseIntentModel  # noqa: F401
from src.data.models.purchase import PurchaseModel  # noqa: F401
from src.data.models.receipt_validation import ReceiptValidationModel  # noqa: F401
from src.data.models.refund_notification import RefundNotificationModel  # noqa: F401
from src.data.models.bot_earnings_ledger import BotEarningsLedgerModel  # noqa: F401
from src.data.models.bot_attribution_entry import BotAttributionEntryModel  # noqa: F401
from src.data.models.bot_payout_request import BotPayoutRequestModel  # noqa: F401
from src.data.models.bot_earnings_daily import BotEarningsDailyModel  # noqa: F401

# Alembic Config object — provides access to alembic.ini values.
config = context.config

# Target metadata for autogenerate support.
target_metadata = Base.metadata


def _build_database_url() -> str:
    """Build a PostgreSQL async URL from the application config.

    Reads host, port, name, user, and password from the ``[database]``
    section of ``config/app.toml`` (with env-var overrides applied).

    Returns:
        An ``asyncpg`` connection URL string.
    """
    app_config = ConfigService.load()

    host = app_config.get("database.host", "localhost")
    port = app_config.get("database.port", 5432)
    name = app_config.get("database.name", "chromacrush")
    user = app_config.get("database.user", "chromacrush")
    password = app_config.get("database.password", "")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine. Calls to
    ``context.execute()`` emit the given SQL string to the script output.
    """
    url = _build_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    """Configure the Alembic context with a live connection and run."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def _run_migrations_online_async() -> None:
    """Run migrations in 'online' mode using an async engine.

    Creates an ``AsyncEngine`` and uses ``run_sync`` to bridge into
    Alembic's synchronous migration runner.
    """
    url = _build_database_url()

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (entry point for Alembic)."""
    asyncio.run(_run_migrations_online_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
