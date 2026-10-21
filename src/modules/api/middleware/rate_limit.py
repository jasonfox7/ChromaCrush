"""Rate limiting middleware.

Checks per-identifier rate limits before each request using the injected
AuthServiceProtocol. The identifier is determined by auth type:

- ``api_key:{key_id}`` for API-key-authenticated requests
- ``player:{player_id}`` for JWT-authenticated requests
- ``ip:{host}`` for unauthenticated requests

Returns HTTP 429 with ``Retry-After`` header when exceeded.

Config keys:
    ``api.rate_limit.requests_per_minute`` (default 60)
    ``api.rate_limit.burst_size`` (default 10)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.core.errors import AppError

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.modules.auth.protocols import AuthServiceProtocol

# Default rate limit settings
_DEFAULT_REQUESTS_PER_MINUTE = 60
_DEFAULT_BURST_SIZE = 10

# Paths exempt from rate limiting
_EXEMPT_PATH_PREFIX = "/api/v1/health"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce per-identifier rate limits."""

    def __init__(
        self,
        app: object,
        auth_service: AuthServiceProtocol | None = None,
        config: ConfigProtocol | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._auth = auth_service
        self._requests_per_minute: int = (
            config.get(
                "api.rate_limit.requests_per_minute",
                _DEFAULT_REQUESTS_PER_MINUTE,
            )
            if config
            else _DEFAULT_REQUESTS_PER_MINUTE
        )
        self._burst_size: int = (
            config.get(
                "api.rate_limit.burst_size",
                _DEFAULT_BURST_SIZE,
            )
            if config
            else _DEFAULT_BURST_SIZE
        )
        self._jwt_rpm: int = (
            config.get(
                "api.rate_limit.jwt_requests_per_minute",
                self._requests_per_minute,
            )
            if config
            else self._requests_per_minute
        )
        self._ip_rpm: int = (
            config.get(
                "api.rate_limit.ip_requests_per_minute",
                30,
            )
            if config
            else 30
        )
        self._redis: Any = None

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Check rate limit, record request, then continue pipeline.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The HTTP response, or a 429 JSON error if rate limited.
        """
        # Lazy-load auth service from app.state if not provided at construction
        if self._auth is None:
            self._auth = getattr(request.app.state, "auth_service", None)
        if self._auth is None:
            return await call_next(request)

        # Skip CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path.startswith(_EXEMPT_PATH_PREFIX):
            return await call_next(request)

        identifier = self._get_identifier(request)

        # For API-key-authenticated requests, delegate to auth service
        api_key_id = getattr(request.state, "api_key_id", None)
        if api_key_id is not None:
            try:
                status = await self._auth.check_rate_limit(api_key_id)
                if status.is_exceeded:
                    retry_after = status.window_seconds
                    return self._rate_limit_response(identifier, retry_after, request)

                await self._auth.record_api_request(api_key_id)
            except AppError as exc:
                if exc.code.startswith("RATE_LIMIT"):
                    retry_after_ctx = exc.context.get("retry_after", 60)
                    return self._rate_limit_response(
                        identifier, retry_after_ctx, request
                    )
                # Non-rate-limit errors propagate normally
                raise
        else:
            # JWT-authenticated or unauthenticated: generic Redis rate limit
            if self._redis is None:
                ctx = getattr(request.app.state, "ctx", None)
                if ctx is not None:
                    self._redis = ctx.data_ctx.redis
            if self._redis is not None:
                player_id = getattr(request.state, "player_id", None)
                rpm = self._jwt_rpm if player_id else self._ip_rpm
                exceeded, retry_after = await self._check_generic_limit(
                    identifier, rpm,
                )
                if exceeded:
                    return self._rate_limit_response(
                        identifier, retry_after, request,
                    )

        return await call_next(request)

    @staticmethod
    def _get_identifier(request: Request) -> str:
        """Determine the rate-limit identifier for the request.

        Args:
            request: The current HTTP request.

        Returns:
            A string key for rate-limit tracking.
        """
        api_key_id = getattr(request.state, "api_key_id", None)
        if api_key_id is not None:
            return f"api_key:{api_key_id}"

        player_id = getattr(request.state, "player_id", None)
        if player_id is not None:
            return f"player:{player_id}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def _check_generic_limit(
        self, identifier: str, max_requests: int,
    ) -> tuple[bool, int]:
        """Check and record a request against a generic Redis rate limit.

        Uses atomic INCR to avoid race conditions. INCR on a nonexistent
        key atomically creates it with value 1. EXPIRE is set only on the
        first request in the window.

        Args:
            identifier: The rate-limit key (e.g. "player:uuid" or "ip:1.2.3.4").
            max_requests: Maximum requests allowed per 60-second window.

        Returns:
            Tuple of (is_exceeded, retry_after_seconds).
        """
        window = 60
        redis_key = f"chromacrush:ratelimit:generic:{identifier}"
        count = await self._redis.incr(redis_key)
        if count == 1:
            await self._redis.expire(redis_key, window)
        if count > max_requests:
            return True, window
        return False, window

    @staticmethod
    def _rate_limit_response(
        identifier: str,
        retry_after: int,
        request: Request,
    ) -> JSONResponse:
        """Build a 429 JSON error response with Retry-After header.

        Args:
            identifier: The rate-limit key that was exceeded.
            retry_after: Seconds until the rate limit resets.
            request: The current HTTP request (for correlation ID).

        Returns:
            JSONResponse with 429 status and Retry-After header.
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded",
                    "details": {
                        "identifier": identifier,
                        "retry_after": retry_after,
                    },
                },
                "meta": {
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0",
                },
            },
        )
