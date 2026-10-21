"""Correlation ID middleware.

Generates or extracts a correlation ID for every request and stores it
on ``request.state.correlation_id``. The correlation ID is also set in
the async-safe ``ContextVar`` for downstream service consumption, and
echoed back in the ``X-Correlation-ID`` response header.

Format: ``cc_{timestamp_hex}_{random_hex}``
Example: ``cc_18d4f2a8_7b3e9c1d``
"""

from __future__ import annotations

import secrets
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.core.protocols.correlation import correlation_id_var

HEADER_NAME = "X-Correlation-ID"
CORRELATION_PREFIX = "cc_"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to every request/response cycle."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Extract or generate correlation ID, then propagate it.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The HTTP response with ``X-Correlation-ID`` header set.
        """
        correlation_id = request.headers.get(HEADER_NAME)
        if not correlation_id:
            correlation_id = _generate_correlation_id()

        # Store on request state for access in route handlers
        request.state.correlation_id = correlation_id

        # Set in ContextVar for async-safe downstream access
        token = correlation_id_var.set(correlation_id)

        try:
            response = await call_next(request)
            response.headers[HEADER_NAME] = correlation_id
            return response
        finally:
            correlation_id_var.reset(token)


def _generate_correlation_id() -> str:
    """Generate a new correlation ID.

    Returns:
        String in format ``cc_{timestamp_hex}_{random_hex}``.
    """
    timestamp_hex = format(int(time.time()), "x")
    random_hex = secrets.token_hex(4)
    return f"{CORRELATION_PREFIX}{timestamp_hex}_{random_hex}"
