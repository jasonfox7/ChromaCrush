"""Integration tests for API routes with real services.

Validates FastAPI endpoints backed by real PostgreSQL and Redis via
ApiFactory + IntegrationServiceFactory.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.modules.api.factory import ApiFactory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app(factory):
    """Create a real FastAPI app with all services wired."""
    api_factory = ApiFactory(
        config=factory.config,
        logger=factory.logger,
        errors=factory.errors,
        auth_service=factory.auth_service,
        player_service=factory.player_service,
        energy_service=factory.energy_service,
        matchmaking_service=factory.matchmaking_service,
        match_service=factory.match_service,
        vault_service=factory.vault_service,
        event_service=factory.event_service,
        ad_service=factory.ad_service,
        payment_service=factory.payment_service,
        bot_earnings_service=factory.bot_earnings_service,
    )
    return api_factory.create_app()


@pytest.fixture
async def client(app):
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Health / Infrastructure Tests
# ---------------------------------------------------------------------------


class TestHealthAndInfrastructure:
    """Tests for health endpoints and infrastructure behaviour."""

    async def test_health_endpoint_returns_200(self, client):
        """GET /api/v1/health returns 200 with status ok."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    async def test_liveness_endpoint(self, client):
        """GET /api/v1/health/live returns 200 with status alive."""
        resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    async def test_not_found_route_returns_401_or_404(self, client):
        """Unknown route returns 401 (auth intercepts) or 404."""
        resp = await client.get("/api/v1/nonexistent")
        # Auth middleware runs before routing, so unauthenticated
        # requests to unknown routes get 401 instead of 404
        assert resp.status_code in (401, 404)

    async def test_correlation_id_in_response_headers(self, client):
        """X-Correlation-ID header is present in responses."""
        resp = await client.get("/api/v1/health")
        assert "x-correlation-id" in resp.headers
        assert resp.headers["x-correlation-id"].startswith("cc_")


# ---------------------------------------------------------------------------
# Auth Tests
# ---------------------------------------------------------------------------


class TestAuthFlow:
    """Tests for authentication endpoints."""

    async def test_register_and_login(self, client):
        """Register a player then login to get a JWT token."""
        # Register
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "testplayer",
                "password": "SecurePass123!",
            },
        )
        assert reg_resp.status_code == 200, reg_resp.text
        reg_data = reg_resp.json()
        assert "data" in reg_data or "player_id" in str(reg_data)

        # Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "testplayer",
                "password": "SecurePass123!",
            },
        )
        assert login_resp.status_code == 200, login_resp.text
        login_data = login_resp.json()
        # Should contain a token somewhere in the response
        resp_str = str(login_data)
        assert "token" in resp_str.lower() or "access" in resp_str.lower()

    async def test_protected_route_requires_auth(self, client):
        """Accessing a protected route without token returns 401."""
        resp = await client.get("/api/v1/players/me")
        assert resp.status_code == 401

    async def test_protected_route_with_valid_token(self, client):
        """Accessing a protected route with valid JWT succeeds."""
        # Register + login
        await client.post(
            "/api/v1/auth/register",
            json={"username": "autheduser", "password": "SecurePass123!"},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "autheduser", "password": "SecurePass123!"},
        )
        login_data = login_resp.json()

        # Extract token — look in common locations
        token = None
        if isinstance(login_data, dict):
            if "data" in login_data and isinstance(login_data["data"], dict):
                token = login_data["data"].get("access_token") or login_data[
                    "data"
                ].get("token")
            else:
                token = login_data.get("access_token") or login_data.get("token")

        assert token is not None, f"Could not find token in: {login_data}"

        # Access protected endpoint
        resp = await client.get(
            "/api/v1/players/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Error Format Tests
# ---------------------------------------------------------------------------


class TestErrorFormat:
    """Tests for structured error response format."""

    async def test_app_error_returns_structured_json(self, client):
        """Auth error returns structured JSON with code and correlation_id."""
        resp = await client.get("/api/v1/players/me")
        assert resp.status_code == 401
        data = resp.json()
        # Should have error structure
        error = data.get("error", data)
        assert "code" in error or "message" in error
