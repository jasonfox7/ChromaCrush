"""Authentication middleware.

Validates JWT tokens (``Authorization: Bearer <token>``) and API keys
(``X-API-Key`` header) by delegating to the injected AuthServiceProtocol.
Sets ``request.state.auth_type``, ``request.state.player_id``, and
optionally ``request.state.api_key_id`` or ``request.state.session_id``.

Public paths (registration, login, health, docs) skip authentication.
API keys are checked before JWTs when both headers are present.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.core.errors import AppError

if TYPE_CHECKING:
    from src.modules.auth.protocols import AuthServiceProtocol

# Paths that do not require authentication
_PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/apple",
        "/api/v1/auth/bot/register",
        "/api/v1/health",
        "/api/v1/health/ready",
        "/api/v1/health/live",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)


class AuthMiddleware(BaseHTTPMiddleware):
    """Authenticate requests via JWT or API key."""

    def __init__(
        self,
        app: object,
        auth_service: AuthServiceProtocol | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._auth = auth_service

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Validate authentication for non-public paths.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The HTTP response, or a 401 JSON error if authentication fails.
        """
        # Lazy-load auth service from app.state if not provided at construction
        auth = self._auth or getattr(request.app.state, "auth_service", None)
        if auth is None:
            return await call_next(request)
        self._auth = auth

        # Skip CORS preflight requests (OPTIONS) — let CORSMiddleware handle them
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for public paths
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # Try API key first (X-API-Key header)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return await self._authenticate_api_key(api_key, request, call_next)

        # Try JWT (Authorization: Bearer <token>)
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return self._auth_error(
                "AUTH_TOKEN_INVALID", "Authentication required", request
            )

        if not auth_header.startswith("Bearer "):
            return self._auth_error(
                "AUTH_TOKEN_INVALID", "Invalid token format", request
            )

        token = auth_header[len("Bearer ") :]
        return await self._authenticate_jwt(token, request, call_next)

    async def _authenticate_api_key(
        self,
        api_key: str,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Validate an API key and set request state."""
        try:
            auth_token = await self._auth.validate_token(api_key)
        except AppError as exc:
            return self._auth_error(exc.code, exc.message, request)

        request.state.auth_type = "api_key"
        request.state.player_id = auth_token.player_id
        request.state.api_key_id = getattr(auth_token, "key_id", None)
        return await call_next(request)

    async def _authenticate_jwt(
        self,
        token: str,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Validate a JWT and set request state."""
        try:
            auth_token = await self._auth.validate_token(token)
        except AppError as exc:
            return self._auth_error(exc.code, exc.message, request)

        request.state.auth_type = "jwt"
        request.state.player_id = auth_token.player_id
        request.state.session_id = getattr(auth_token, "session_id", None)
        return await call_next(request)

    @staticmethod
    def _auth_error(code: str, message: str, request: Request) -> JSONResponse:
        """Build a 401 JSON error response.

        Args:
            code: Machine-readable error code.
            message: Human-readable error description.
            request: The current HTTP request (for correlation ID).

        Returns:
            JSONResponse with 401 status.
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "data": None,
                "error": {"code": code, "message": message, "details": None},
                "meta": {
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0",
                },
            },
        )
