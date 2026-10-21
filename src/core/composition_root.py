"""Composition root -- the ONLY place services are created and wired.

Creates all services in dependency order, provides them as a typed context.
No other code in the application instantiates services directly.

Usage:
    ctx = await create_application_context("config/app.toml")
    # ... use ctx.config, ctx.logger, ctx.errors, ctx.data_ctx, etc.
    await shutdown_application_context(ctx)
"""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass

from src.core.config import ConfigService
from src.core.data_context import DataContext
from src.core.debug_logger import DebugLogger
from src.core.error_service import ErrorService
from src.core.logger import LogService
from src.core.protocols.config import ConfigProtocol
from src.core.protocols.data_context import DataContextProtocol
from src.core.protocols.error_service import ErrorServiceProtocol
from src.core.protocols.logger import LoggerProtocol

# -- Repository imports -------------------------------------------------------
from src.data.repositories.player_repository import SQLAlchemyPlayerRepository
from src.data.repositories.player_stats_repository import (
    SQLAlchemyPlayerStatsRepository,
)
from src.data.repositories.energy_state_repository import (
    SQLAlchemyEnergyStateRepository,
)
from src.data.repositories.session_repository import SQLAlchemySessionRepository
from src.data.repositories.api_key_repository import SQLAlchemyApiKeyRepository
from src.data.repositories.password_store_repository import (
    SQLAlchemyPasswordStoreRepository,
)
from src.data.repositories.match_repository import (
    SQLAlchemyMatchRepository,
    SQLAlchemyMatchMoveRepository,
)
from src.data.repositories.vault_artifact_repository import (
    SQLAlchemyVaultArtifactRepository,
)
from src.data.repositories.vault_shield_repository import (
    SQLAlchemyVaultShieldRepository,
)
from src.data.repositories.artifact_definition_repository import (
    SQLAlchemyArtifactDefinitionRepository,
)
from src.data.repositories.raid_log_repository import SQLAlchemyRaidLogRepository
from src.data.repositories.player_card_repository import (
    SQLAlchemyPlayerCardRepository,
)
from src.data.repositories.event_repository import SQLAlchemyEventRepository
from src.data.repositories.event_participant_repository import (
    SQLAlchemyEventParticipantRepository,
)
from src.data.repositories.event_leaderboard_repository import (
    RedisEventLeaderboardRepository,
)
from src.data.repositories.matchmaking_queue_repository import (
    RedisMatchmakingQueueRepository,
)
from src.data.repositories.ad_request_repository import SQLAlchemyAdRequestRepository
from src.data.repositories.ad_impression_repository import (
    SQLAlchemyAdImpressionRepository,
)
from src.data.repositories.ad_free_status_repository import (
    SQLAlchemyAdFreeStatusRepository,
)
from src.data.repositories.ad_reward_repository import SQLAlchemyAdRewardRepository
from src.data.repositories.event_ad_opportunity_repository import (
    SQLAlchemyEventAdOpportunityRepository,
)
from src.data.repositories.event_ad_claim_repository import (
    SQLAlchemyEventAdClaimRepository,
)
from src.data.repositories.product_repository import SQLAlchemyProductRepository
from src.data.repositories.purchase_intent_repository import (
    SQLAlchemyPurchaseIntentRepository,
)
from src.data.repositories.purchase_repository import SQLAlchemyPurchaseRepository
from src.data.repositories.receipt_validation_repository import (
    SQLAlchemyReceiptValidationRepository,
)
from src.data.repositories.refund_notification_repository import (
    SQLAlchemyRefundNotificationRepository,
)
from src.data.repositories.bot_earnings_ledger_repository import (
    SQLAlchemyEarningsLedgerRepository,
)
from src.data.repositories.bot_attribution_entry_repository import (
    SQLAlchemyAttributionEntryRepository,
)
from src.data.repositories.bot_payout_request_repository import (
    SQLAlchemyPayoutRequestRepository,
)
from src.data.repositories.bot_daily_earnings_repository import (
    SQLAlchemyDailyEarningsRepository,
)

# -- Service imports ----------------------------------------------------------
from src.modules.board.service import BoardService
from src.modules.scoring.service import ScoringService
from src.modules.special_gems.service import SpecialGemsService
from src.modules.board_gen.service import BoardGenService
from src.modules.player.service import PlayerService
from src.modules.auth.service import AuthService
from src.modules.energy.service import EnergyService
from src.modules.match.service import MatchRepositoryBundle, MatchService
from src.modules.matchmaking.service import MatchmakingService
from src.modules.vault.service import VaultService
from src.modules.events.service import EventService
from src.modules.ads.service import AdRepositoryBundle, AdService
from src.modules.payments.service import PaymentRepositoryBundle, PaymentService
from src.modules.bot_earnings.service import BotEarningsService
from src.modules.cards.service import CardService
from src.modules.inventory.service import InventoryService
from src.data.repositories.mega_gem_inventory_repository import (
    SQLAlchemyMegaGemInventoryRepository,
)
from src.data.repositories.gold_balance_repository import (
    SQLAlchemyGoldBalanceRepository,
)
from src.data.repositories.gold_transaction_repository import (
    SQLAlchemyGoldTransactionRepository,
)
from src.data.repositories.campaign_attempt_repository import (
    SQLAlchemyCampaignAttemptRepository,
)

# -- Economy service import ---------------------------------------------------
from src.modules.economy.service import EconomyService

# -- Campaign service import -------------------------------------------------
from src.modules.campaign.service import CampaignService

# -- Mock providers (development stubs) --------------------------------------


class _MockAdProvider:
    """No-op ad provider for development. Replace with real SDK integration."""

    async def request_interstitial(self, ad_unit_id: str, user_id: str) -> Any:
        from src.modules.ads.types import AdProviderResponse

        return AdProviderResponse(ad_available=True, ad_data={"provider": "mock"})

    async def request_rewarded_video(self, ad_unit_id: str, user_id: str) -> Any:
        from src.modules.ads.types import AdProviderResponse

        return AdProviderResponse(ad_available=True, ad_data={"provider": "mock"})

    async def verify_impression(
        self, ad_request_id: str, impression_data: dict[str, Any]
    ) -> bool:
        return True

    async def get_estimated_cpm(self, ad_type: str) -> int:
        return 200


class _MockPaymentProvider:
    """No-op payment provider for development. Replace with Apple/Google SDK."""

    async def validate_receipt(
        self, receipt_data: str, product_id: str, is_sandbox: bool = False
    ) -> Any:
        from src.modules.payments.types import PaymentProvider, ReceiptValidationResult

        return ReceiptValidationResult(
            valid=True,
            provider=PaymentProvider.MOCK,
            transaction_id=f"mock_txn_{__import__('uuid').uuid4().hex[:16]}",
            product_id=product_id,
            purchase_date=None,
            is_duplicate=False,
            is_sandbox=True,
            error_code=None,
            raw_response=None,
        )

    async def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        return True


# -- Application context ------------------------------------------------------


@dataclass(frozen=True)
class ApplicationContext:
    """Holds all application services.

    Created once at startup by ``create_application_context``.
    Passed to route handlers and CLI commands via dependency injection.

    All fields are typed as protocol interfaces so that consuming code
    never couples to concrete implementations.
    """

    config: ConfigProtocol
    logger: LoggerProtocol
    errors: ErrorServiceProtocol
    data_ctx: DataContextProtocol
    debug_logger: Any  # DebugLogger

    # Module services (all 14, in dependency-wave order)
    player_service: Any  # PlayerServiceProtocol
    auth_service: Any  # AuthServiceProtocol
    energy_service: Any  # EnergyServiceProtocol
    board_service: Any  # BoardServiceProtocol
    scoring_service: Any  # ScoringServiceProtocol
    special_gems_service: Any  # SpecialGemsServiceProtocol
    board_gen_service: Any  # BoardGenServiceProtocol
    match_service: Any  # MatchServiceProtocol
    matchmaking_service: Any  # MatchmakingServiceProtocol
    vault_service: Any  # VaultServiceProtocol
    event_service: Any  # EventServiceProtocol
    ad_service: Any  # AdServiceProtocol
    payment_service: Any  # PaymentServiceProtocol
    bot_earnings_service: Any  # BotEarningsServiceProtocol
    card_service: Any  # CardService
    inventory_service: Any  # InventoryServiceProtocol
    economy_service: Any  # EconomyServiceProtocol
    campaign_service: Any  # CampaignService

    # Keep player_repo for backward compatibility with CLI commands
    player_repo: Any = None


async def create_application_context(
    config_path: str = "config/app.toml",
) -> ApplicationContext:
    """Create and wire all application services in dependency order.

    Construction order follows the dependency wave graph from
    ``docs/architecture/architecture.md``:
        1. Core (sync): config, logger, errors
        2. Data (async): data_ctx + all repositories
        3. Wave 1: BoardService, PlayerService
        4. Wave 2: ScoringService, AuthService, EnergyService
        5. Wave 3: SpecialGemsService, VaultService
        6. Wave 4: BoardGenService
        7. Wave 5: MatchService
        8. Wave 6: EventService, MatchmakingService
        9. Wave 7: AdService
       10. Wave 8: PaymentService, BotEarningsService

    Args:
        config_path: Path to the base TOML configuration file.

    Returns:
        A fully-wired ``ApplicationContext`` ready for use.
    """
    # ================================================================
    # 1. Core services (sync)
    # ================================================================
    config = ConfigService.load(config_path)
    logger = LogService(config)
    errors = ErrorService(logger)
    debug_logger = DebugLogger(config)

    # ================================================================
    # 2. Data context (async) -- PostgreSQL engine + Redis client
    # ================================================================
    data_ctx = await DataContext.create(config, logger, errors)

    # ================================================================
    # 3. Repositories
    # ================================================================
    # Player / auth repos
    player_repo = SQLAlchemyPlayerRepository(data_ctx, logger, errors)
    stats_repo = SQLAlchemyPlayerStatsRepository(data_ctx, logger, errors)
    energy_repo = SQLAlchemyEnergyStateRepository(data_ctx, logger, errors)
    session_repo = SQLAlchemySessionRepository(data_ctx, logger, errors)
    api_key_repo = SQLAlchemyApiKeyRepository(data_ctx, logger, errors)
    password_store = SQLAlchemyPasswordStoreRepository(data_ctx)

    # Match repos
    match_repo = SQLAlchemyMatchRepository(data_ctx, logger, errors)
    match_move_repo = SQLAlchemyMatchMoveRepository(data_ctx, logger, errors)

    # Vault repos
    vault_artifact_repo = SQLAlchemyVaultArtifactRepository(data_ctx, logger, errors)
    vault_shield_repo = SQLAlchemyVaultShieldRepository(data_ctx, logger, errors)
    artifact_definition_repo = SQLAlchemyArtifactDefinitionRepository(
        data_ctx, logger, errors
    )
    raid_log_repo = SQLAlchemyRaidLogRepository(data_ctx, logger, errors)

    # Card repos
    player_card_repo = SQLAlchemyPlayerCardRepository(data_ctx, logger, errors)

    # Inventory repos
    mega_inventory_repo = SQLAlchemyMegaGemInventoryRepository(data_ctx, logger, errors)

    # Economy repos
    gold_balance_repo = SQLAlchemyGoldBalanceRepository(data_ctx, logger, errors)
    gold_tx_repo = SQLAlchemyGoldTransactionRepository(data_ctx, logger, errors)

    # Event repos
    event_repo = SQLAlchemyEventRepository(data_ctx, logger, errors)
    event_participant_repo = SQLAlchemyEventParticipantRepository(
        data_ctx, logger, errors
    )
    event_leaderboard_repo = RedisEventLeaderboardRepository(data_ctx.redis, logger)

    # Matchmaking repo (Redis-based)
    matchmaking_queue_repo = RedisMatchmakingQueueRepository(data_ctx)

    # Ad repos
    ad_request_repo = SQLAlchemyAdRequestRepository(data_ctx, logger, errors)
    ad_impression_repo = SQLAlchemyAdImpressionRepository(data_ctx, logger, errors)
    ad_free_status_repo = SQLAlchemyAdFreeStatusRepository(data_ctx, logger, errors)
    ad_reward_repo = SQLAlchemyAdRewardRepository(data_ctx, logger, errors)
    event_ad_opportunity_repo = SQLAlchemyEventAdOpportunityRepository(
        data_ctx, logger, errors
    )
    event_ad_claim_repo = SQLAlchemyEventAdClaimRepository(data_ctx, logger, errors)

    # Payment repos
    product_repo = SQLAlchemyProductRepository(data_ctx, logger, errors)
    purchase_intent_repo = SQLAlchemyPurchaseIntentRepository(data_ctx, logger, errors)
    purchase_repo = SQLAlchemyPurchaseRepository(data_ctx, logger, errors)
    receipt_validation_repo = SQLAlchemyReceiptValidationRepository(
        data_ctx, logger, errors
    )
    refund_notification_repo = SQLAlchemyRefundNotificationRepository(
        data_ctx, logger, errors
    )

    # Bot earnings repos
    earnings_ledger_repo = SQLAlchemyEarningsLedgerRepository(data_ctx, logger, errors)
    attribution_entry_repo = SQLAlchemyAttributionEntryRepository(
        data_ctx, logger, errors
    )
    payout_request_repo = SQLAlchemyPayoutRequestRepository(data_ctx, logger, errors)
    daily_earnings_repo = SQLAlchemyDailyEarningsRepository(data_ctx, logger, errors)

    # Campaign repos
    campaign_attempt_repo = SQLAlchemyCampaignAttemptRepository(data_ctx, logger, errors)

    # ================================================================
    # 4. Wave 1 -- Leaf services (no module dependencies)
    # ================================================================
    board_service = BoardService(config, logger, errors, debug_logger=debug_logger)

    player_service = PlayerService(
        config=config,
        logger=logger,
        errors=errors,
        player_repo=player_repo,
        stats_repo=stats_repo,
        energy_repo=energy_repo,
    )

    # ================================================================
    # 5. Wave 2
    # ================================================================
    scoring_service = ScoringService(config, logger, errors)

    auth_service = AuthService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=player_service,
        session_repo=session_repo,
        api_key_repo=api_key_repo,
        password_store=password_store,
        redis=data_ctx.redis,
    )

    energy_service = EnergyService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=player_service,
        energy_repo=energy_repo,
        redis=data_ctx.redis,
    )

    # ================================================================
    # 6. Wave 3
    # ================================================================
    special_gems_service = SpecialGemsService(config, logger, errors, scoring_service)

    card_service = CardService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=player_service,
        player_card_repo=player_card_repo,
    )

    vault_service = VaultService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=player_service,
        vault_artifact_repo=vault_artifact_repo,
        vault_shield_repo=vault_shield_repo,
        artifact_definition_repo=artifact_definition_repo,
        raid_log_repo=raid_log_repo,
        card_service=card_service,
    )

    inventory_service = InventoryService(
        config=config,
        logger=logger,
        errors=errors,
        inventory_repo=mega_inventory_repo,
    )

    economy_service = EconomyService(
        config=config,
        logger=logger,
        errors=errors,
        gold_repo=gold_balance_repo,
        gold_tx_repo=gold_tx_repo,
        card_service=card_service,
        inventory_service=inventory_service,
        energy_service=energy_service,
    )

    # ================================================================
    # 7. Wave 4
    # ================================================================
    board_gen_service = BoardGenService(
        config, logger, errors, board_service, special_gems_service
    )

    campaign_service = CampaignService(
        config=config,
        logger=logger,
        errors=errors,
        board_service=board_service,
        energy_service=energy_service,
        player_repo=player_repo,
        campaign_repo=campaign_attempt_repo,
        card_service=card_service,
        scoring_service=scoring_service,
        economy_service=economy_service,
        board_gen_service=board_gen_service,
    )

    # ================================================================
    # 8. Wave 5
    # ================================================================
    match_repos = MatchRepositoryBundle(
        match_repository=match_repo,
        match_move_repository=match_move_repo,
    )

    match_service = MatchService(
        config=config,
        logger=logger,
        errors=errors,
        data_ctx=data_ctx,
        board_gen_service=board_gen_service,
        board_service=board_service,
        scoring_service=scoring_service,
        special_gems_service=special_gems_service,
        player_service=player_service,
        auth_service=auth_service,
        energy_service=energy_service,
        repos=match_repos,
        card_service=card_service,
        inventory_service=inventory_service,
        debug_logger=debug_logger,
    )

    # ================================================================
    # 9. Wave 6
    # ================================================================
    event_service = EventService(
        config=config,
        logger=logger,
        errors=errors,
        data_ctx=data_ctx,
        vault_service=vault_service,
        energy_service=energy_service,
        match_service=match_service,
        player_service=player_service,
        event_repository=event_repo,
        event_participant_repository=event_participant_repo,
        event_leaderboard_repository=event_leaderboard_repo,
    )

    matchmaking_service = MatchmakingService(
        config=config,
        logger=logger,
        errors=errors,
        match_service=match_service,
        player_service=player_service,
        matchmaking_queue_repository=matchmaking_queue_repo,
    )

    # ================================================================
    # 10. Wave 7
    # ================================================================
    ad_repos = AdRepositoryBundle(
        ad_request=ad_request_repo,
        ad_impression=ad_impression_repo,
        ad_free_status=ad_free_status_repo,
        ad_reward=ad_reward_repo,
        event_opportunity=event_ad_opportunity_repo,
        event_claim=event_ad_claim_repo,
    )

    ad_service = AdService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=player_service,
        events_service=event_service,
        repos=ad_repos,
        ad_provider=_MockAdProvider(),
    )

    # ================================================================
    # 11. Wave 8 (terminal)
    # ================================================================
    payment_repos = PaymentRepositoryBundle(
        product_repo=product_repo,
        intent_repo=purchase_intent_repo,
        purchase_repo=purchase_repo,
        receipt_repo=receipt_validation_repo,
        refund_repo=refund_notification_repo,
    )

    # Use real Apple provider when keys are configured, else mock for dev.
    apple_key_id = config.get("payments.apple_key_id", "")
    apple_private_key_path = config.get("payments.apple_private_key_path", "")
    if apple_key_id and apple_private_key_path:
        from src.modules.payments.apple_provider import AppleAppStoreProvider

        payment_provider: Any = AppleAppStoreProvider(
            key_id=apple_key_id,
            issuer_id=config.get("payments.apple_issuer_id", ""),
            bundle_id=config.get("payments.apple_bundle_id", ""),
            private_key_path=apple_private_key_path,
            is_sandbox=config.get("payments.allow_sandbox_purchases", False),
        )
        logger.info(
            "Apple App Store provider configured",
            key_id=apple_key_id,
        )
    else:
        payment_provider = _MockPaymentProvider()
        logger.info("Using mock payment provider (no Apple keys configured)")

    payment_service = PaymentService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=player_service,
        ads_service=ad_service,
        repos=payment_repos,
        payment_provider=payment_provider,
        gold_repo=gold_balance_repo,
        gold_tx_repo=gold_tx_repo,
    )

    bot_earnings_service = BotEarningsService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=player_service,
        ads_service=ad_service,
        earnings_ledger_repository=earnings_ledger_repo,
        attribution_entry_repository=attribution_entry_repo,
        payout_request_repository=payout_request_repo,
        daily_earnings_repository=daily_earnings_repo,
        data_ctx=data_ctx,
    )

    logger.info(
        "Application context created",
        config_path=config_path,
        environment=config.get("app.environment", "unknown"),
        services_wired=18,
        repositories_wired=34,
    )

    return ApplicationContext(
        config=config,
        logger=logger,
        errors=errors,
        data_ctx=data_ctx,
        debug_logger=debug_logger,
        player_service=player_service,
        auth_service=auth_service,
        energy_service=energy_service,
        board_service=board_service,
        scoring_service=scoring_service,
        special_gems_service=special_gems_service,
        board_gen_service=board_gen_service,
        match_service=match_service,
        matchmaking_service=matchmaking_service,
        vault_service=vault_service,
        event_service=event_service,
        ad_service=ad_service,
        payment_service=payment_service,
        bot_earnings_service=bot_earnings_service,
        card_service=card_service,
        inventory_service=inventory_service,
        economy_service=economy_service,
        campaign_service=campaign_service,
        player_repo=player_repo,
    )


def load_config(config_path: str = "config/app.toml") -> ConfigProtocol:
    """Load configuration without creating the full application context.

    Useful for synchronous CLI commands that only need config values
    (e.g., ``version``, ``show-config``) and do not require database
    or async services.

    Args:
        config_path: Path to the base TOML configuration file.

    Returns:
        A ``ConfigProtocol`` instance backed by the TOML file and env vars.
    """
    return ConfigService.load(config_path)


async def shutdown_application_context(ctx: ApplicationContext) -> None:
    """Gracefully shut down all application services.

    Closes database connection pools and the Redis client.

    Args:
        ctx: The application context to shut down.
    """
    await ctx.data_ctx.close()
    ctx.logger.info("Application context shut down")
