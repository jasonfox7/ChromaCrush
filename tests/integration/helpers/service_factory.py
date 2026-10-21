"""Integration test service factory -- wires REAL services with REAL databases.

Creates a full service stack backed by PostgreSQL and Redis Docker
containers. Uses MockConfigService/MockLogService/MockErrorService for
non-I/O concerns, but everything else is production code.

Usage::

    factory = await IntegrationServiceFactory.create()
    try:
        match_state = await factory.match_service.create_match(...)
    finally:
        await factory.cleanup()
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from tests.mocks.services import MockConfigService, MockErrorService, MockLogService
from src.core.data_context import DataContext

# ---- Repositories (all real, backed by data_ctx) --------------------------
from src.data.repositories.player_repository import SQLAlchemyPlayerRepository
from src.data.repositories.player_stats_repository import (
    SQLAlchemyPlayerStatsRepository,
)
from src.data.repositories.energy_state_repository import (
    SQLAlchemyEnergyStateRepository,
)
from src.data.repositories.match_repository import (
    SQLAlchemyMatchRepository,
    SQLAlchemyMatchMoveRepository,
)
from src.data.repositories.session_repository import SQLAlchemySessionRepository
from src.data.repositories.api_key_repository import SQLAlchemyApiKeyRepository
from src.data.repositories.password_store_repository import (
    SQLAlchemyPasswordStoreRepository,
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
from src.data.repositories.event_repository import SQLAlchemyEventRepository
from src.data.repositories.event_participant_repository import (
    SQLAlchemyEventParticipantRepository,
)
from src.data.repositories.event_leaderboard_repository import (
    RedisEventLeaderboardRepository,
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
from src.data.repositories.matchmaking_queue_repository import (
    RedisMatchmakingQueueRepository,
)

# ---- Services (all real) --------------------------------------------------
from src.modules.board.service import BoardService
from src.modules.scoring.service import ScoringService
from src.modules.special_gems.service import SpecialGemsService
from src.modules.board_gen.service import BoardGenService
from src.modules.player.service import PlayerService
from src.modules.energy.service import EnergyService
from src.modules.auth.service import AuthService
from src.modules.match.service import MatchRepositoryBundle, MatchService
from src.modules.vault.service import VaultService
from src.modules.matchmaking.service import MatchmakingService
from src.modules.events.service import EventService
from src.modules.ads.service import AdRepositoryBundle, AdService
from src.modules.payments.service import PaymentRepositoryBundle, PaymentService
from src.modules.bot_earnings.service import BotEarningsService


class IntegrationServiceFactory:
    """Wires the full service stack against real PostgreSQL and Redis.

    Attributes expose every service and repository for direct use in tests.
    """

    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    async def create(
        cls,
        config_overrides: dict | None = None,
    ) -> IntegrationServiceFactory:
        """Create a fully wired factory with real database connections.

        Args:
            config_overrides: Optional dict of config key overrides
                merged on top of the integration-test defaults.

        Returns:
            Ready-to-use IntegrationServiceFactory instance.
        """
        # ---- Configuration ------------------------------------------------
        base_overrides: dict = {
            "database.host": "localhost",
            "database.port": 5432,
            "database.name": "chromacrush_test",
            "database.user": "chromacrush",
            "database.password": "chromacrush_dev",
            "database.pool_size": 2,
            "redis.host": "localhost",
            "redis.port": 6379,
            "match.moves_per_player": 20,
            "match.timeout_hours": 72,
            "match.energy_cost": 1,
            "match.allow_concurrent": False,
            "match.max_concurrent": 1,
            "match.deadlock_reshuffle": True,
            "matchmaking.initial_elo_range": 50,
            "matchmaking.elo_range_expansion": 50,
            "matchmaking.max_queue_time_seconds": 300,
        }
        if config_overrides:
            base_overrides.update(config_overrides)

        config = MockConfigService(base_overrides)
        logger = MockLogService()
        errors = MockErrorService(logger)

        # ---- Data Context (real PostgreSQL + Redis) -----------------------
        data_ctx = await DataContext.create(config, logger, errors)

        # ---- Repositories (all real, backed by data_ctx) ------------------
        # Player / stats / energy
        player_repo = SQLAlchemyPlayerRepository(data_ctx, logger, errors)
        stats_repo = SQLAlchemyPlayerStatsRepository(data_ctx, logger, errors)
        energy_repo = SQLAlchemyEnergyStateRepository(data_ctx, logger, errors)

        # Match
        match_repo = SQLAlchemyMatchRepository(data_ctx, logger, errors)
        match_move_repo = SQLAlchemyMatchMoveRepository(data_ctx, logger, errors)

        # Auth
        session_repo = SQLAlchemySessionRepository(data_ctx, logger, errors)
        api_key_repo = SQLAlchemyApiKeyRepository(data_ctx, logger, errors)
        password_store = SQLAlchemyPasswordStoreRepository(data_ctx)

        # Vault
        vault_artifact_repo = SQLAlchemyVaultArtifactRepository(
            data_ctx, logger, errors
        )
        vault_shield_repo = SQLAlchemyVaultShieldRepository(data_ctx, logger, errors)
        artifact_definition_repo = SQLAlchemyArtifactDefinitionRepository(
            data_ctx, logger, errors
        )
        raid_log_repo = SQLAlchemyRaidLogRepository(data_ctx, logger, errors)

        # Events
        event_repo = SQLAlchemyEventRepository(data_ctx, logger, errors)
        event_participant_repo = SQLAlchemyEventParticipantRepository(
            data_ctx, logger, errors
        )
        event_leaderboard_repo = RedisEventLeaderboardRepository(data_ctx.redis, logger)

        # Ads
        ad_request_repo = SQLAlchemyAdRequestRepository(data_ctx, logger, errors)
        ad_impression_repo = SQLAlchemyAdImpressionRepository(data_ctx, logger, errors)
        ad_free_status_repo = SQLAlchemyAdFreeStatusRepository(data_ctx, logger, errors)
        ad_reward_repo = SQLAlchemyAdRewardRepository(data_ctx, logger, errors)
        event_ad_opportunity_repo = SQLAlchemyEventAdOpportunityRepository(
            data_ctx, logger, errors
        )
        event_ad_claim_repo = SQLAlchemyEventAdClaimRepository(data_ctx, logger, errors)

        # Payments
        product_repo = SQLAlchemyProductRepository(data_ctx, logger, errors)
        purchase_intent_repo = SQLAlchemyPurchaseIntentRepository(
            data_ctx, logger, errors
        )
        purchase_repo = SQLAlchemyPurchaseRepository(data_ctx, logger, errors)
        receipt_repo = SQLAlchemyReceiptValidationRepository(data_ctx, logger, errors)
        refund_repo = SQLAlchemyRefundNotificationRepository(data_ctx, logger, errors)

        # Bot Earnings
        earnings_ledger_repo = SQLAlchemyEarningsLedgerRepository(
            data_ctx, logger, errors
        )
        attribution_entry_repo = SQLAlchemyAttributionEntryRepository(
            data_ctx, logger, errors
        )
        payout_request_repo = SQLAlchemyPayoutRequestRepository(
            data_ctx, logger, errors
        )
        daily_earnings_repo = SQLAlchemyDailyEarningsRepository(
            data_ctx, logger, errors
        )

        # Matchmaking (Redis-backed)
        matchmaking_queue_repo = RedisMatchmakingQueueRepository(data_ctx)

        # ---- Layer 0: Sync pure services ----------------------------------
        board_service = BoardService(config, logger, errors)
        scoring_service = ScoringService(config, logger, errors)
        special_gems_service = SpecialGemsService(
            config, logger, errors, scoring_service
        )
        board_gen_service = BoardGenService(
            config,
            logger,
            errors,
            board_service,
            special_gems_service,
        )

        # ---- Layer 1: Async services (player) -----------------------------
        player_service = PlayerService(
            config,
            logger,
            errors,
            player_repo,
            stats_repo,
            energy_repo,
        )

        # ---- Layer 2: Async services (energy, auth, vault) ----------------
        energy_service = EnergyService(
            config,
            logger,
            errors,
            player_service,
            energy_repo,
            redis=data_ctx.redis,
            data_ctx=data_ctx,
        )
        auth_service = AuthService(
            config,
            logger,
            errors,
            player_service,
            session_repo,
            api_key_repo,
            password_store,
            redis=data_ctx.redis,
        )
        vault_service = VaultService(
            config,
            logger,
            errors,
            player_service,
            vault_artifact_repo,
            vault_shield_repo,
            artifact_definition_repo,
            raid_log_repo,
            data_ctx=data_ctx,
        )

        # ---- Layer 3: Async services (match, matchmaking, events) ---------
        repos_bundle = MatchRepositoryBundle(match_repo, match_move_repo)
        match_service = MatchService(
            config,
            logger,
            errors,
            data_ctx,
            board_gen_service,
            board_service,
            scoring_service,
            special_gems_service,
            player_service,
            auth_service,
            energy_service,
            repos_bundle,
        )

        matchmaking_service = MatchmakingService(
            config,
            logger,
            errors,
            match_service,
            player_service,
            matchmaking_queue_repo,
        )

        event_service = EventService(
            config,
            logger,
            errors,
            data_ctx,
            vault_service,
            energy_service,
            match_service,
            player_service,
            event_repo,
            event_participant_repo,
            event_leaderboard_repo,
        )

        # ---- Layer 4: Async services (ads, payments, bot_earnings) --------
        ad_repos_bundle = AdRepositoryBundle(
            ad_request_repo,
            ad_impression_repo,
            ad_free_status_repo,
            ad_reward_repo,
            event_ad_opportunity_repo,
            event_ad_claim_repo,
        )
        # AdProviderProtocol is external — use AsyncMock
        ad_provider = AsyncMock()
        ad_service = AdService(
            config,
            logger,
            errors,
            player_service,
            event_service,
            ad_repos_bundle,
            ad_provider,
        )

        payment_repos_bundle = PaymentRepositoryBundle(
            product_repo,
            purchase_intent_repo,
            purchase_repo,
            receipt_repo,
            refund_repo,
        )
        # PaymentProviderProtocol is external — use AsyncMock
        payment_provider = AsyncMock()
        payment_service = PaymentService(
            config,
            logger,
            errors,
            player_service,
            ad_service,
            repos=payment_repos_bundle,
            payment_provider=payment_provider,
        )

        bot_earnings_service = BotEarningsService(
            config,
            logger,
            errors,
            player_service,
            ad_service,
            earnings_ledger_repo,
            attribution_entry_repo,
            payout_request_repo,
            daily_earnings_repo,
            data_ctx=data_ctx,
        )

        return cls(
            config=config,
            logger=logger,
            errors=errors,
            data_ctx=data_ctx,
            # Repositories
            player_repo=player_repo,
            stats_repo=stats_repo,
            energy_repo=energy_repo,
            match_repo=match_repo,
            match_move_repo=match_move_repo,
            session_repo=session_repo,
            api_key_repo=api_key_repo,
            password_store=password_store,
            vault_artifact_repo=vault_artifact_repo,
            vault_shield_repo=vault_shield_repo,
            artifact_definition_repo=artifact_definition_repo,
            raid_log_repo=raid_log_repo,
            event_repo=event_repo,
            event_participant_repo=event_participant_repo,
            event_leaderboard_repo=event_leaderboard_repo,
            ad_request_repo=ad_request_repo,
            ad_impression_repo=ad_impression_repo,
            ad_free_status_repo=ad_free_status_repo,
            ad_reward_repo=ad_reward_repo,
            event_ad_opportunity_repo=event_ad_opportunity_repo,
            event_ad_claim_repo=event_ad_claim_repo,
            product_repo=product_repo,
            purchase_intent_repo=purchase_intent_repo,
            purchase_repo=purchase_repo,
            receipt_repo=receipt_repo,
            refund_repo=refund_repo,
            earnings_ledger_repo=earnings_ledger_repo,
            attribution_entry_repo=attribution_entry_repo,
            payout_request_repo=payout_request_repo,
            daily_earnings_repo=daily_earnings_repo,
            matchmaking_queue_repo=matchmaking_queue_repo,
            # Services
            board_service=board_service,
            scoring_service=scoring_service,
            special_gems_service=special_gems_service,
            board_gen_service=board_gen_service,
            player_service=player_service,
            energy_service=energy_service,
            auth_service=auth_service,
            vault_service=vault_service,
            match_service=match_service,
            matchmaking_service=matchmaking_service,
            event_service=event_service,
            ad_service=ad_service,
            ad_provider=ad_provider,
            payment_service=payment_service,
            payment_provider=payment_provider,
            bot_earnings_service=bot_earnings_service,
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Close all database and Redis connections."""
        await self.data_ctx.close()
