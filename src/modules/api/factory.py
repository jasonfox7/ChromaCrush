"""API application factory.

``ApiFactory`` implements ``ApiFactoryProtocol`` and creates a fully
configured FastAPI application. All service dependencies are received
via ``__init__`` injection -- no direct imports of core service
constructors.

The factory:
1. Creates the FastAPI app with optional OpenAPI docs.
2. Stores injected services on ``app.state`` for dependency access.
3. Registers middleware in the correct order.
4. Registers exception handlers.
5. Mounts all route routers (health, websocket, and 10 domain routers).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.modules.api.adapters.bot_hints import BotHintGenerator
from src.modules.api.adapters.response import ResponseAdapter
from src.modules.api.middleware.auth import AuthMiddleware
from src.modules.api.middleware.correlation import CorrelationMiddleware
from src.modules.api.middleware.error_handler import register_error_handlers
from src.modules.api.middleware.rate_limit import RateLimitMiddleware
from src.modules.api.routes import (
    ads_router,
    auth_router,
    bot_earnings_router,
    campaign_router,
    cards_router,
    economy_router,
    energy_router,
    events_router,
    health_router,
    inventory_router,
    matchmaking_router,
    matches_router,
    payments_router,
    players_router,
    vault_router,
    ws_router,
)
from src.modules.api.websocket.channels import ChannelManager
from src.modules.api.websocket.handler import WebSocketHandler
from src.modules.api.websocket.manager import ConnectionManager

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.protocols import AdServiceProtocol
    from src.modules.auth.protocols import AuthServiceProtocol
    from src.modules.bot_earnings.protocols import BotEarningsServiceProtocol
    from src.modules.energy.protocols import EnergyServiceProtocol
    from src.modules.events.protocols import EventServiceProtocol
    from src.modules.match.protocols import MatchServiceProtocol
    from src.modules.matchmaking.protocols import MatchmakingServiceProtocol
    from src.modules.payments.protocols import PaymentServiceProtocol
    from src.modules.player.protocols import PlayerServiceProtocol
    from src.modules.cards.service import CardService
    from src.modules.economy.protocols import EconomyServiceProtocol
    from src.modules.vault.protocols import VaultServiceProtocol

# Default configuration values
_DEFAULT_HOST = "0.0.0.0"
_DEFAULT_PORT = 8000
_DEFAULT_CORS_ORIGINS = ["http://localhost:8080"]
_DEFAULT_DOCS_ENABLED = True
_DEFAULT_BOT_HINTS_ENABLED = True
_DEFAULT_APP_VERSION = "0.1.0"


class ApiFactory:
    """Factory that creates and configures the FastAPI application.

    All service dependencies are received through the constructor.
    The composition root is responsible for instantiating this factory
    with the correct service instances.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        auth_service: AuthServiceProtocol,
        player_service: PlayerServiceProtocol,
        energy_service: EnergyServiceProtocol,
        matchmaking_service: MatchmakingServiceProtocol,
        match_service: MatchServiceProtocol,
        vault_service: VaultServiceProtocol,
        event_service: EventServiceProtocol,
        ad_service: AdServiceProtocol,
        payment_service: PaymentServiceProtocol,
        bot_earnings_service: BotEarningsServiceProtocol,
        card_service: CardService | None = None,
        economy_service: EconomyServiceProtocol | None = None,
    ) -> None:
        """Initialise the factory with injected services.

        Args:
            config: Application configuration.
            logger: Structured logger.
            errors: Error creation service.
            auth_service: Authentication and rate-limit service.
            player_service: Player management service.
            energy_service: Energy / hearts service.
            matchmaking_service: Matchmaking queue service.
            match_service: Match lifecycle service.
            vault_service: Vault artifact service.
            event_service: Event management service.
            ad_service: Ad impression service.
            payment_service: Payment processing service.
            bot_earnings_service: Bot earnings tracking service.
            card_service: Card collection and equip service.
            economy_service: Gold economy service.
        """
        self._config = config
        self._logger = logger
        self._errors = errors
        self._auth_service = auth_service
        self._player_service = player_service
        self._energy_service = energy_service
        self._matchmaking_service = matchmaking_service
        self._match_service = match_service
        self._vault_service = vault_service
        self._event_service = event_service
        self._ad_service = ad_service
        self._payment_service = payment_service
        self._bot_earnings_service = bot_earnings_service
        self._card_service = card_service
        self._economy_service = economy_service

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application.

        Returns:
            Fully configured FastAPI instance with middleware, exception
            handlers, and routers registered.
        """
        docs_enabled: bool = self._config.get(
            "api.docs_enabled",
            _DEFAULT_DOCS_ENABLED,
        )
        app_version: str = self._config.get(
            "app.version",
            _DEFAULT_APP_VERSION,
        )

        app = FastAPI(
            title="ChromaCrush API",
            version=app_version,
            docs_url="/docs" if docs_enabled else None,
            redoc_url="/redoc" if docs_enabled else None,
            openapi_url="/openapi.json" if docs_enabled else None,
        )

        # Store services on app state for dependency injection
        self._configure_state(app)

        # Register middleware (order matters: outermost first)
        self._register_middleware(app)

        # Register exception handlers
        register_error_handlers(app)

        # Register all routers
        self._register_routers(app)

        self._logger.info(
            "API application created",
            version=app_version,
            docs_enabled=docs_enabled,
        )

        return app

    def _configure_state(self, app: FastAPI) -> None:
        """Store services and adapters on app.state.

        Args:
            app: The FastAPI application.
        """
        # Core services
        app.state.config = self._config
        app.state.logger = self._logger
        app.state.errors = self._errors
        app.state.auth_service = self._auth_service
        app.state.app_version = self._config.get("app.version", _DEFAULT_APP_VERSION)

        # Module services
        app.state.player_service = self._player_service
        app.state.energy_service = self._energy_service
        app.state.matchmaking_service = self._matchmaking_service
        app.state.match_service = self._match_service
        app.state.vault_service = self._vault_service
        app.state.event_service = self._event_service
        app.state.ad_service = self._ad_service
        app.state.payment_service = self._payment_service
        app.state.bot_earnings_service = self._bot_earnings_service
        app.state.card_service = self._card_service
        app.state.economy_service = self._economy_service

        # Board service (for debug endpoint)
        app.state.board_service = getattr(self._match_service, "_board_service", None)

        # Adapters
        app.state.response_adapter = ResponseAdapter()
        app.state.bot_hint_generator = BotHintGenerator()

        # WebSocket infrastructure
        connection_manager = ConnectionManager()
        channel_manager = ChannelManager()

        app.state.connection_manager = connection_manager
        app.state.channel_manager = channel_manager
        app.state.ws_handler = WebSocketHandler(
            connection_manager=connection_manager,
            channel_manager=channel_manager,
            auth_service=self._auth_service,
            config=self._config,
            logger=self._logger,
        )

    def _register_middleware(self, app: FastAPI) -> None:
        """Register middleware in execution order.

        Starlette processes middleware in reverse registration order,
        so the first registered middleware is outermost (runs first).
        We register: CORS -> Correlation -> Auth -> RateLimit.

        Args:
            app: The FastAPI application.
        """
        cors_origins: list[str] = self._config.get(
            "api.cors_origins",
            _DEFAULT_CORS_ORIGINS,
        )

        # CORS (outermost)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["X-Correlation-ID"],
        )

        # Correlation ID
        app.add_middleware(CorrelationMiddleware)

        # Authentication (must run before rate limiting)
        app.add_middleware(
            AuthMiddleware,
            auth_service=self._auth_service,
        )

        # Rate limiting
        app.add_middleware(
            RateLimitMiddleware,
            auth_service=self._auth_service,
            config=self._config,
        )

    def _register_routers(self, app: FastAPI) -> None:
        """Register all route routers on the application.

        Includes infrastructure routers (health, websocket) and all
        ten domain routers (auth, players, energy, matchmaking, matches,
        vault, events, ads, payments, bot_earnings).

        Args:
            app: The FastAPI application.
        """
        # Infrastructure routers
        app.include_router(health_router)
        app.include_router(ws_router)

        # Domain routers
        app.include_router(auth_router)
        app.include_router(players_router)
        app.include_router(energy_router)
        app.include_router(matchmaking_router)
        app.include_router(matches_router)
        app.include_router(vault_router)
        app.include_router(cards_router)
        app.include_router(inventory_router)
        app.include_router(events_router)
        app.include_router(ads_router)
        app.include_router(payments_router)
        app.include_router(bot_earnings_router)
        app.include_router(economy_router)
        app.include_router(campaign_router)


# ---------------------------------------------------------------------------
# Module-level factory for uvicorn --factory mode
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create a fully-wired FastAPI application.

    This is a module-level sync factory suitable for ``uvicorn`` with
    ``factory=True``.  Async service creation happens in the lifespan
    handler which runs before the first request is served.

    Usage::

        uvicorn src.modules.api.factory:create_app --factory
    """
    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    from src.core.composition_root import (
        create_application_context,
        load_config,
        shutdown_application_context,
    )

    config = load_config()

    async def _periodic_cleanup(ctx: object) -> None:
        """Background task that periodically cleans up expired data."""
        import asyncio

        interval = config.get("server.cleanup_interval_seconds", 3600)
        while True:
            await asyncio.sleep(interval)
            try:
                await ctx.auth_service.cleanup_expired_sessions()  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                await ctx.match_service.abandon_stale_matches()  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                await ctx.campaign_service.abandon_stale_attempts()  # type: ignore[attr-defined]
            except Exception:
                pass

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        import asyncio

        ctx = await create_application_context()
        factory = ApiFactory(
            config=ctx.config,
            logger=ctx.logger,
            errors=ctx.errors,
            auth_service=ctx.auth_service,
            player_service=ctx.player_service,
            energy_service=ctx.energy_service,
            matchmaking_service=ctx.matchmaking_service,
            match_service=ctx.match_service,
            vault_service=ctx.vault_service,
            event_service=ctx.event_service,
            ad_service=ctx.ad_service,
            payment_service=ctx.payment_service,
            bot_earnings_service=ctx.bot_earnings_service,
            card_service=ctx.card_service,
            economy_service=ctx.economy_service,
        )
        # Populate app.state with all services and adapters
        factory._configure_state(app)
        # Expose board_service, debug_logger, and inventory_service from context
        app.state.board_service = ctx.board_service
        app.state.debug_logger = ctx.debug_logger
        app.state.inventory_service = ctx.inventory_service
        app.state.campaign_service = ctx.campaign_service
        app.state.ctx = ctx

        # Start periodic cleanup (expired sessions, stale matches)
        cleanup_task = asyncio.create_task(_periodic_cleanup(ctx))

        yield

        cleanup_task.cancel()
        await shutdown_application_context(ctx)

    docs_enabled: bool = config.get("api.docs_enabled", _DEFAULT_DOCS_ENABLED)
    app_version: str = config.get("app.version", _DEFAULT_APP_VERSION)
    cors_origins: list[str] = config.get("api.cors_origins", _DEFAULT_CORS_ORIGINS)

    app = FastAPI(
        title="ChromaCrush API",
        version=app_version,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )

    # -- Middleware (outermost first) --
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Correlation ID
    from src.modules.api.middleware.correlation import CorrelationMiddleware

    app.add_middleware(CorrelationMiddleware)

    # Auth and rate-limit (lazy-loading: services populated on first request
    # via app.state after lifespan runs)
    from src.modules.api.middleware.auth import AuthMiddleware
    from src.modules.api.middleware.rate_limit import RateLimitMiddleware

    # Rate limit must be added BEFORE auth so that auth (added last = outermost)
    # runs first and sets request.state.player_id before rate limit checks it.
    app.add_middleware(RateLimitMiddleware, config=config)
    app.add_middleware(AuthMiddleware)

    # -- Exception handlers --
    register_error_handlers(app)

    # -- Routers --
    app.include_router(health_router)
    app.include_router(ws_router)
    app.include_router(auth_router)
    app.include_router(players_router)
    app.include_router(energy_router)
    app.include_router(matchmaking_router)
    app.include_router(matches_router)
    app.include_router(vault_router)
    app.include_router(cards_router)
    app.include_router(inventory_router)
    app.include_router(events_router)
    app.include_router(ads_router)
    app.include_router(payments_router)
    app.include_router(bot_earnings_router)
    app.include_router(economy_router)
    app.include_router(campaign_router)

    return app
