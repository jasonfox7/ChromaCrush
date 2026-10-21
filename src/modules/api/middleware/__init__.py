"""API middleware for request processing pipeline.

Middleware runs in order: correlation -> auth -> rate_limit.
Error handling is registered as FastAPI exception handlers.
"""

from src.modules.api.middleware.auth import AuthMiddleware
from src.modules.api.middleware.correlation import CorrelationMiddleware
from src.modules.api.middleware.rate_limit import RateLimitMiddleware

__all__ = [
    "AuthMiddleware",
    "CorrelationMiddleware",
    "RateLimitMiddleware",
]
