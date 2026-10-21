"""Unit tests for API middleware.

Tests correlation, auth, rate limit, and error handler middleware
independently. Each middleware is mounted on a minimal FastAPI app
with mock services injected via app.state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from src.core.errors import AppError
from src.modules.api.middleware.auth import AuthMiddleware
from src.modules.api.middleware.correlation import (
    CORRELATION_PREFIX,
    HEADER_NAME,
    CorrelationMiddleware,
)
from src.modules.api.middleware.error_handler import (
    _resolve_status_code,
    register_error_handlers,
)
from src.modules.api.middleware.rate_limit import RateLimitMiddleware

# ---------------------------------------------------------------------------
# Correlation Middleware Tests
# ---------------------------------------------------------------------------


class TestCorrelationMiddleware:
    """Tests for X-Correlation-ID generation and propagation."""

    @pytest.fixture
    def correlation_app(self) -> FastAPI:
        """Minimal app with only the correlation middleware."""
        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)

        @app.get("/test")
        async def test_endpoint(request: Request) -> dict[str, str]:
            return {"correlation_id": request.state.correlation_id}

        return app

    @pytest.fixture
    def correlation_client(self, correlation_app: FastAPI) -> TestClient:
        return TestClient(correlation_app)

    def test_generates_correlation_id_when_none_provided(
        self,
        correlation_client: TestClient,
    ) -> None:
        """A new correlation ID is generated if the client does not send one."""
        resp = correlation_client.get("/test")

        assert resp.status_code == 200
        body = resp.json()
        assert body["correlation_id"].startswith(CORRELATION_PREFIX)

    def test_preserves_client_provided_correlation_id(
        self,
        correlation_client: TestClient,
    ) -> None:
        """The middleware uses the client-supplied correlation ID verbatim."""
        custom_id = "custom-trace-id-abc"
        resp = correlation_client.get(
            "/test",
            headers={HEADER_NAME: custom_id},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["correlation_id"] == custom_id

    def test_correlation_id_appears_in_response_headers(
        self,
        correlation_client: TestClient,
    ) -> None:
        """The correlation ID is echoed in the response X-Correlation-ID header."""
        resp = correlation_client.get("/test")

        assert HEADER_NAME in resp.headers
        assert resp.headers[HEADER_NAME].startswith(CORRELATION_PREFIX)

    def test_client_id_echoed_in_response_header(
        self,
        correlation_client: TestClient,
    ) -> None:
        """When the client provides a correlation ID it is echoed back unchanged."""
        custom_id = "my-trace-123"
        resp = correlation_client.get(
            "/test",
            headers={HEADER_NAME: custom_id},
        )

        assert resp.headers[HEADER_NAME] == custom_id

    def test_generated_id_format(
        self,
        correlation_client: TestClient,
    ) -> None:
        """Generated IDs follow cc_{hex}_{hex} format."""
        resp = correlation_client.get("/test")

        cid = resp.headers[HEADER_NAME]
        assert cid.startswith("cc_")
        parts = cid.split("_", 2)  # "cc", timestamp_hex, random_hex
        assert len(parts) == 3
        # Both hex portions should be valid hex
        int(parts[1], 16)
        int(parts[2], 16)


# ---------------------------------------------------------------------------
# Auth Middleware Tests
# ---------------------------------------------------------------------------


class TestAuthMiddleware:
    """Tests for JWT and API key authentication middleware."""

    @pytest.fixture
    def mock_auth_service(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def auth_app(self, mock_auth_service: AsyncMock) -> FastAPI:
        """Minimal app with auth middleware."""
        app = FastAPI()
        app.state.auth_service = mock_auth_service
        app.add_middleware(AuthMiddleware, auth_service=mock_auth_service)

        @app.get("/api/v1/auth/login")
        async def login() -> dict[str, str]:
            return {"status": "login_page"}

        @app.get("/api/v1/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        @app.get("/api/v1/protected")
        async def protected(request: Request) -> dict[str, Any]:
            return {
                "player_id": request.state.player_id,
                "auth_type": request.state.auth_type,
            }

        return app

    @pytest.fixture
    def auth_client(self, auth_app: FastAPI) -> TestClient:
        return TestClient(auth_app, raise_server_exceptions=False)

    def test_public_paths_skip_auth(
        self,
        auth_client: TestClient,
    ) -> None:
        """Public endpoints do not require authentication."""
        resp = auth_client.get("/api/v1/auth/login")
        assert resp.status_code == 200

    def test_health_path_skips_auth(
        self,
        auth_client: TestClient,
    ) -> None:
        """Health endpoint is public."""
        resp = auth_client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_missing_auth_header_returns_401(
        self,
        auth_client: TestClient,
    ) -> None:
        """Requests without auth headers return 401."""
        resp = auth_client.get("/api/v1/protected")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_TOKEN_INVALID"

    def test_invalid_bearer_format_returns_401(
        self,
        auth_client: TestClient,
    ) -> None:
        """Authorization header without 'Bearer ' prefix returns 401."""
        resp = auth_client.get(
            "/api/v1/protected",
            headers={"Authorization": "Basic abc123"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_TOKEN_INVALID"

    def test_valid_jwt_sets_request_state(
        self,
        auth_client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Valid JWT populates request.state with player_id and auth_type."""

        @dataclass
        class _FakeAuthToken:
            player_id: str = "player-uuid-123"
            session_id: str = "session-456"

        mock_auth_service.validate_token.return_value = _FakeAuthToken()

        resp = auth_client.get(
            "/api/v1/protected",
            headers={"Authorization": "Bearer valid-jwt-token"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["player_id"] == "player-uuid-123"
        assert body["auth_type"] == "jwt"

    def test_valid_api_key_sets_request_state(
        self,
        auth_client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Valid API key populates request.state with player_id and auth_type."""

        @dataclass
        class _FakeAuthToken:
            player_id: str = "bot-uuid-789"
            key_id: str = "key-id-abc"

        mock_auth_service.validate_token.return_value = _FakeAuthToken()

        resp = auth_client.get(
            "/api/v1/protected",
            headers={"X-API-Key": "cc_valid_key_123"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["player_id"] == "bot-uuid-789"
        assert body["auth_type"] == "api_key"

    def test_invalid_token_returns_401(
        self,
        auth_client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Auth service raising AppError for bad token results in 401."""
        mock_auth_service.validate_token.side_effect = AppError(
            code="AUTH_TOKEN_INVALID",
            message="Token expired",
            http_status=401,
        )

        resp = auth_client.get(
            "/api/v1/protected",
            headers={"Authorization": "Bearer expired-jwt"},
        )

        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_TOKEN_INVALID"

    def test_invalid_api_key_returns_401(
        self,
        auth_client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Auth service raising AppError for bad API key results in 401."""
        mock_auth_service.validate_token.side_effect = AppError(
            code="AUTH_API_KEY_INVALID",
            message="API key not found",
            http_status=401,
        )

        resp = auth_client.get(
            "/api/v1/protected",
            headers={"X-API-Key": "cc_bad_key"},
        )

        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_API_KEY_INVALID"

    def test_api_key_checked_before_jwt(
        self,
        auth_client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """When both headers are present, API key is checked first."""

        @dataclass
        class _FakeAuthToken:
            player_id: str = "api-key-player"
            key_id: str = "key-id"

        mock_auth_service.validate_token.return_value = _FakeAuthToken()

        resp = auth_client.get(
            "/api/v1/protected",
            headers={
                "X-API-Key": "cc_key_value",
                "Authorization": "Bearer jwt-value",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["auth_type"] == "api_key"
        # validate_token should have been called with the API key, not the JWT
        mock_auth_service.validate_token.assert_called_once_with("cc_key_value")


# ---------------------------------------------------------------------------
# Rate Limit Middleware Tests
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    """Tests for per-identifier rate limiting."""

    @pytest.fixture
    def mock_auth_service(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_config(self) -> MagicMock:
        config = MagicMock()
        config.get = MagicMock(
            side_effect=lambda key, default=None: {
                "api.rate_limit.requests_per_minute": 60,
                "api.rate_limit.burst_size": 10,
            }.get(key, default)
        )
        return config

    @pytest.fixture
    def rate_app(
        self,
        mock_auth_service: AsyncMock,
        mock_config: MagicMock,
    ) -> FastAPI:
        """Minimal app with rate limit middleware."""
        app = FastAPI()
        app.state.auth_service = mock_auth_service
        app.add_middleware(
            RateLimitMiddleware,
            auth_service=mock_auth_service,
            config=mock_config,
        )

        @app.get("/api/v1/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        @app.get("/api/v1/data")
        async def data(request: Request) -> dict[str, str]:
            return {"status": "allowed"}

        return app

    @pytest.fixture
    def rate_client(self, rate_app: FastAPI) -> TestClient:
        return TestClient(rate_app, raise_server_exceptions=False)

    def test_health_paths_skip_rate_limiting(
        self,
        rate_client: TestClient,
    ) -> None:
        """Health endpoints are exempt from rate limiting."""
        resp = rate_client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_rate_limit_exceeded_returns_429(
        self,
        rate_client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """When rate limit is exceeded for an API key, returns 429."""
        # Simulate that request.state has api_key_id set
        # Since we cannot set request.state directly in the rate limit test,
        # we test the code path where check_rate_limit reports exceeded

        @dataclass
        class _RateStatus:
            is_exceeded: bool = True
            window_seconds: int = 60

        # The rate limit middleware checks getattr(request.state, "api_key_id")
        # Without auth middleware, api_key_id won't be on state.
        # We need to add a middleware that sets it.

        from starlette.middleware.base import BaseHTTPMiddleware

        class SetApiKeyMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                request.state.api_key_id = "test-key-id"
                request.state.player_id = "test-player"
                return await call_next(request)

        # Build a new app with both middlewares.
        # Starlette processes add_middleware in reverse order: the last
        # middleware added is outermost (runs first). We need
        # SetApiKeyMiddleware to run BEFORE RateLimitMiddleware so that
        # request.state.api_key_id is set by the time RateLimit checks it.
        app = FastAPI()
        mock_config = MagicMock()
        mock_config.get = MagicMock(
            side_effect=lambda key, default=None: {
                "api.rate_limit.requests_per_minute": 60,
                "api.rate_limit.burst_size": 10,
            }.get(key, default)
        )

        # Add RateLimitMiddleware first (it becomes inner, runs second)
        app.add_middleware(
            RateLimitMiddleware,
            auth_service=mock_auth_service,
            config=mock_config,
        )
        # Add SetApiKeyMiddleware last (it becomes outer, runs first)
        app.add_middleware(SetApiKeyMiddleware)

        @app.get("/api/v1/data")
        async def data() -> dict[str, str]:
            return {"status": "allowed"}

        mock_auth_service.check_rate_limit.return_value = _RateStatus()

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/data")

        assert resp.status_code == 429
        body = resp.json()
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in resp.headers

    def test_rate_limit_not_exceeded_passes_through(
        self,
        rate_client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Non-API-key requests pass through without rate limit checks."""
        resp = rate_client.get("/api/v1/data")
        assert resp.status_code == 200

    def test_jwt_rate_limit_enforced(self) -> None:
        """JWT-authenticated requests are rate limited via generic Redis check."""
        from starlette.middleware.base import BaseHTTPMiddleware

        class SetPlayerMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                request.state.player_id = "test-player-id"
                return await call_next(request)

        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 61  # Over the default 60 jwt rpm
        mock_redis.expire.return_value = True

        mock_ctx = MagicMock()
        mock_ctx.data_ctx.redis = mock_redis

        mock_config = MagicMock()
        mock_config.get = MagicMock(
            side_effect=lambda key, default=None: {
                "api.rate_limit.requests_per_minute": 60,
                "api.rate_limit.burst_size": 10,
                "api.rate_limit.jwt_requests_per_minute": 60,
                "api.rate_limit.ip_requests_per_minute": 30,
            }.get(key, default)
        )

        app = FastAPI()
        app.state.auth_service = AsyncMock()
        app.state.ctx = mock_ctx

        app.add_middleware(
            RateLimitMiddleware,
            auth_service=app.state.auth_service,
            config=mock_config,
        )
        app.add_middleware(SetPlayerMiddleware)

        @app.get("/api/v1/data")
        async def data() -> dict[str, str]:
            return {"status": "allowed"}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/data")

        assert resp.status_code == 429
        body = resp.json()
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    def test_ip_rate_limit_enforced(self) -> None:
        """Unauthenticated requests are rate limited by IP via Redis."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 31  # Over the default 30 ip rpm
        mock_redis.expire.return_value = True

        mock_ctx = MagicMock()
        mock_ctx.data_ctx.redis = mock_redis

        mock_config = MagicMock()
        mock_config.get = MagicMock(
            side_effect=lambda key, default=None: {
                "api.rate_limit.requests_per_minute": 60,
                "api.rate_limit.burst_size": 10,
                "api.rate_limit.jwt_requests_per_minute": 60,
                "api.rate_limit.ip_requests_per_minute": 30,
            }.get(key, default)
        )

        app = FastAPI()
        app.state.auth_service = AsyncMock()
        app.state.ctx = mock_ctx

        app.add_middleware(
            RateLimitMiddleware,
            auth_service=app.state.auth_service,
            config=mock_config,
        )

        @app.get("/api/v1/data")
        async def data() -> dict[str, str]:
            return {"status": "allowed"}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/data")

        assert resp.status_code == 429
        body = resp.json()
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    def test_generic_limit_passes_under_threshold(self) -> None:
        """JWT requests under the limit pass through normally."""
        from starlette.middleware.base import BaseHTTPMiddleware

        class SetPlayerMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                request.state.player_id = "test-player-id"
                return await call_next(request)

        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 5  # Well under 60
        mock_redis.expire.return_value = True

        mock_ctx = MagicMock()
        mock_ctx.data_ctx.redis = mock_redis

        mock_config = MagicMock()
        mock_config.get = MagicMock(
            side_effect=lambda key, default=None: {
                "api.rate_limit.requests_per_minute": 60,
                "api.rate_limit.burst_size": 10,
                "api.rate_limit.jwt_requests_per_minute": 60,
                "api.rate_limit.ip_requests_per_minute": 30,
            }.get(key, default)
        )

        app = FastAPI()
        app.state.auth_service = AsyncMock()
        app.state.ctx = mock_ctx

        app.add_middleware(
            RateLimitMiddleware,
            auth_service=app.state.auth_service,
            config=mock_config,
        )
        app.add_middleware(SetPlayerMiddleware)

        @app.get("/api/v1/data")
        async def data() -> dict[str, str]:
            return {"status": "allowed"}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/data")

        assert resp.status_code == 200

    def test_graceful_degradation_no_redis(self) -> None:
        """When Redis is unavailable, requests pass through without rate limiting."""
        mock_config = MagicMock()
        mock_config.get = MagicMock(
            side_effect=lambda key, default=None: {
                "api.rate_limit.requests_per_minute": 60,
                "api.rate_limit.burst_size": 10,
                "api.rate_limit.jwt_requests_per_minute": 60,
                "api.rate_limit.ip_requests_per_minute": 30,
            }.get(key, default)
        )

        app = FastAPI()
        app.state.auth_service = AsyncMock()
        # No ctx on app.state — Redis stays None

        app.add_middleware(
            RateLimitMiddleware,
            auth_service=app.state.auth_service,
            config=mock_config,
        )

        @app.get("/api/v1/data")
        async def data() -> dict[str, str]:
            return {"status": "allowed"}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/data")

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Error Handler Tests
# ---------------------------------------------------------------------------


class TestErrorHandler:
    """Tests for the global exception handler middleware."""

    @pytest.fixture
    def error_app(self) -> FastAPI:
        """Minimal app with error handlers registered."""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/validation-error")
        async def validation_error() -> None:
            raise AppError(
                code="VALIDATION_OUT_OF_BOUNDS",
                message="Position out of bounds",
                http_status=400,
            )

        @app.get("/auth-error")
        async def auth_error() -> None:
            raise AppError(
                code="AUTH_TOKEN_EXPIRED",
                message="Token has expired",
                http_status=401,
            )

        @app.get("/forbidden-error")
        async def forbidden_error() -> None:
            raise AppError(
                code="FORBIDDEN_NOT_BOT",
                message="Only bots can do this",
                http_status=403,
            )

        @app.get("/not-found-error")
        async def not_found_error() -> None:
            raise AppError(
                code="NOT_FOUND_PLAYER",
                message="Player not found",
                http_status=404,
            )

        @app.get("/conflict-error")
        async def conflict_error() -> None:
            raise AppError(
                code="CONFLICT_ALREADY_IN_QUEUE",
                message="Already in queue",
                http_status=409,
                context={"queue": "mixed"},
            )

        @app.get("/rate-limit-error")
        async def rate_limit_error() -> None:
            raise AppError(
                code="RATE_LIMIT_EXCEEDED",
                message="Too many requests",
                http_status=429,
            )

        @app.get("/unhandled-error")
        async def unhandled_error() -> None:
            raise RuntimeError("Something unexpected")

        return app

    @pytest.fixture
    def error_client(self, error_app: FastAPI) -> TestClient:
        return TestClient(error_app, raise_server_exceptions=False)

    def test_validation_error_returns_400(
        self,
        error_client: TestClient,
    ) -> None:
        """AppError with VALIDATION prefix returns HTTP 400."""
        resp = error_client.get("/validation-error")
        assert resp.status_code == 400
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_OUT_OF_BOUNDS"
        assert body["error"]["message"] == "Position out of bounds"

    def test_auth_error_returns_401(
        self,
        error_client: TestClient,
    ) -> None:
        """AppError with AUTH prefix returns HTTP 401."""
        resp = error_client.get("/auth-error")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_TOKEN_EXPIRED"

    def test_forbidden_error_returns_403(
        self,
        error_client: TestClient,
    ) -> None:
        """AppError with FORBIDDEN prefix returns HTTP 403."""
        resp = error_client.get("/forbidden-error")
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "FORBIDDEN_NOT_BOT"

    def test_not_found_error_returns_404(
        self,
        error_client: TestClient,
    ) -> None:
        """AppError with NOT_FOUND prefix returns HTTP 404."""
        resp = error_client.get("/not-found-error")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND_PLAYER"

    def test_conflict_error_returns_409(
        self,
        error_client: TestClient,
    ) -> None:
        """AppError with CONFLICT prefix returns HTTP 409."""
        resp = error_client.get("/conflict-error")
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"]["code"] == "CONFLICT_ALREADY_IN_QUEUE"
        assert body["error"]["details"] == {"queue": "mixed"}

    def test_rate_limit_error_returns_429(
        self,
        error_client: TestClient,
    ) -> None:
        """AppError with RATE_LIMIT prefix returns HTTP 429."""
        resp = error_client.get("/rate-limit-error")
        assert resp.status_code == 429

    def test_unhandled_exception_returns_500(
        self,
        error_client: TestClient,
    ) -> None:
        """Unhandled exceptions return HTTP 500 with generic message."""
        resp = error_client.get("/unhandled-error")
        assert resp.status_code == 500
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INTERNAL_UNEXPECTED"
        assert body["error"]["message"] == "An unexpected error occurred"

    def test_error_response_includes_meta(
        self,
        error_client: TestClient,
    ) -> None:
        """Error responses include meta with correlation_id and timestamp."""
        resp = error_client.get("/not-found-error")
        body = resp.json()
        assert "meta" in body
        assert "correlation_id" in body["meta"]
        assert "timestamp" in body["meta"]

    def test_unhandled_error_meta_has_correlation_id(
        self,
        error_client: TestClient,
    ) -> None:
        """Unhandled errors still include meta section."""
        resp = error_client.get("/unhandled-error")
        body = resp.json()
        assert body["meta"]["correlation_id"] is not None


class TestResolveStatusCode:
    """Tests for the _resolve_status_code helper function."""

    def test_validation_prefix(self) -> None:
        assert _resolve_status_code("VALIDATION_INVALID_INPUT") == 400

    def test_auth_prefix(self) -> None:
        assert _resolve_status_code("AUTH_TOKEN_EXPIRED") == 401

    def test_forbidden_prefix(self) -> None:
        assert _resolve_status_code("FORBIDDEN_NOT_OWNER") == 403

    def test_not_found_prefix(self) -> None:
        assert _resolve_status_code("NOT_FOUND_PLAYER") == 404

    def test_conflict_prefix(self) -> None:
        assert _resolve_status_code("CONFLICT_DUPLICATE") == 409

    def test_rate_limit_prefix(self) -> None:
        assert _resolve_status_code("RATE_LIMIT_EXCEEDED") == 429

    def test_internal_prefix(self) -> None:
        assert _resolve_status_code("INTERNAL_UNEXPECTED") == 500

    def test_unknown_prefix_defaults_to_500(self) -> None:
        assert _resolve_status_code("UNKNOWN_CODE") == 500
