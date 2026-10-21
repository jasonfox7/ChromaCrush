"""Shared fixtures for API unit tests.

Provides mock services, a test FastAPI application, and a test client.
All dependencies are injected via app.state -- no @patch or monkeypatch.
"""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.core.types.player import Player, PlayerStats, PlayerType
from src.modules.api.adapters.bot_hints import BotHintGenerator
from src.modules.api.adapters.response import ResponseAdapter
from src.modules.api.middleware.error_handler import register_error_handlers
from src.modules.api.routes.auth import router as auth_router
from src.modules.api.routes.energy import router as energy_router
from src.modules.api.routes.health import router as health_router
from src.modules.api.routes.matchmaking import router as matchmaking_router
from src.modules.api.routes.players import router as players_router
from src.modules.player.dto import PaginatedResult

# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

TEST_PLAYER_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
TEST_CORRELATION_ID = "cc_test_12345678"


# ---------------------------------------------------------------------------
# Test auth middleware (injects auth state for route tests)
# ---------------------------------------------------------------------------


class TestAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that simulates authentication for route tests.

    Sets request.state.player_id, auth_type, and correlation_id so
    route handlers can access them without the real auth middleware.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request.state.player_id = TEST_PLAYER_ID
        request.state.auth_type = "jwt"
        request.state.correlation_id = TEST_CORRELATION_ID
        return await call_next(request)


# ---------------------------------------------------------------------------
# Mock service factories
# ---------------------------------------------------------------------------


def _make_player(
    player_id: UUID | None = None,
    username: str = "testuser",
    player_type: PlayerType = PlayerType.HUMAN,
    elo_rating: int = 1000,
) -> Player:
    """Create a Player domain entity for testing."""
    return Player(
        id=PlayerId(player_id or UUID(TEST_PLAYER_ID)),
        username=username,
        player_type=player_type,
        elo_rating=elo_rating,
        created_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


def _make_player_stats(player_id: UUID | None = None) -> PlayerStats:
    """Create PlayerStats for testing."""
    return PlayerStats(
        player_id=PlayerId(player_id or UUID(TEST_PLAYER_ID)),
        total_matches=100,
        wins=60,
        losses=35,
        draws=5,
        highest_score=15000,
        longest_chain=12,
        total_gems_matched=5000,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config() -> MagicMock:
    """Mock configuration service."""
    config = MagicMock()
    config.get = MagicMock(
        side_effect=lambda key, default=None: {
            "api.cors_origins": ["*"],
            "api.docs_enabled": False,
            "api.bot_hints_enabled": True,
            "api.rate_limit.requests_per_minute": 60,
            "api.rate_limit.burst_size": 10,
            "app.version": "0.1.0",
        }.get(key, default)
    )
    return config


@pytest.fixture
def mock_logger() -> MagicMock:
    """Mock logger service."""
    logger = MagicMock()
    for method in ("trace", "debug", "info", "warn", "error", "fatal"):
        setattr(logger, method, MagicMock())
    return logger


@pytest.fixture
def mock_errors() -> MagicMock:
    """Mock error service."""
    return MagicMock()


@pytest.fixture
def mock_auth_service() -> AsyncMock:
    """Mock auth service with default behaviours."""
    svc = AsyncMock()
    svc.hash_password = MagicMock(return_value="$2b$04$hashed")
    svc.verify_password = MagicMock(return_value=True)
    return svc


@pytest.fixture
def mock_player_service() -> AsyncMock:
    """Mock player service."""
    return AsyncMock()


@pytest.fixture
def mock_energy_service() -> AsyncMock:
    """Mock energy service."""
    return AsyncMock()


@pytest.fixture
def mock_matchmaking_service() -> AsyncMock:
    """Mock matchmaking service."""
    return AsyncMock()


@pytest.fixture
def test_app(
    mock_config: MagicMock,
    mock_logger: MagicMock,
    mock_errors: MagicMock,
    mock_auth_service: AsyncMock,
    mock_player_service: AsyncMock,
    mock_energy_service: AsyncMock,
    mock_matchmaking_service: AsyncMock,
) -> FastAPI:
    """Create a test FastAPI app with all mocks injected via app.state."""
    app = FastAPI()

    # Core services
    app.state.config = mock_config
    app.state.logger = mock_logger
    app.state.errors = mock_errors
    app.state.auth_service = mock_auth_service
    app.state.app_version = "0.1.0"

    # Module services
    app.state.player_service = mock_player_service
    app.state.energy_service = mock_energy_service
    app.state.matchmaking_service = mock_matchmaking_service

    # Adapters (use real implementations -- they are pure functions)
    app.state.response_adapter = ResponseAdapter()
    app.state.bot_hint_generator = BotHintGenerator()

    # Test auth middleware to populate request.state for route handlers
    app.add_middleware(TestAuthMiddleware)

    # Register error handlers
    register_error_handlers(app)

    # Register routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(players_router)
    app.include_router(energy_router)
    app.include_router(matchmaking_router)

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """FastAPI test client wrapping the test application."""
    return TestClient(test_app, raise_server_exceptions=False)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Standard JWT auth headers for testing."""
    return {"Authorization": "Bearer test-token-123"}


@pytest.fixture
def api_key_headers() -> dict[str, str]:
    """Standard API key headers for testing."""
    return {"X-API-Key": "test-api-key-123"}
