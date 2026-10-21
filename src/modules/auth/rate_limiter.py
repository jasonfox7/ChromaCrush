"""Rate limiting helper for API key request throttling.

Encapsulates Redis-backed sliding window rate limiting. Tracks request
counts per API key and determines whether the limit has been exceeded.
Used internally by AuthService; not part of the public module interface.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from src.modules.auth.dto import RateLimitStatus

# Redis key prefix for rate limit counters
_REDIS_KEY_PREFIX = "chromacrush:ratelimit"


class RateLimiter:
    """Redis-backed rate limiter for API key requests.

    Maintains per-key request counters in Redis with automatic TTL-based
    window expiry. Each key gets ``max_requests`` calls per
    ``window_seconds`` sliding window.

    Args:
        redis: Async Redis client instance.
        max_requests: Maximum requests allowed per window.
        window_seconds: Duration of the rate limit window in seconds.
    """

    def __init__(
        self,
        redis: Any,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        self._redis = redis
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def get_status(self, key_id: UUID) -> RateLimitStatus:
        """Get current rate limit status for an API key.

        Reads the current request count from Redis without incrementing.

        Args:
            key_id: The API key to check.

        Returns:
            Current RateLimitStatus.
        """
        redis_key = f"{_REDIS_KEY_PREFIX}:{key_id}"
        current_count = await self._redis.get(redis_key)

        current_count_int = int(current_count) if current_count is not None else 0
        remaining = max(0, self._max_requests - current_count_int)
        now = datetime.now(timezone.utc)
        reset_at = now + timedelta(seconds=self._window_seconds)

        return RateLimitStatus(
            key_id=key_id,
            requests_remaining=remaining,
            requests_limit=self._max_requests,
            window_seconds=self._window_seconds,
            reset_at=reset_at,
        )

    async def record_request(self, key_id: UUID) -> RateLimitStatus:
        """Record a request and return updated rate limit status.

        Increments the request counter in Redis. If this is the first
        request in the current window, sets the TTL for automatic expiry.

        Args:
            key_id: The API key making the request.

        Returns:
            Updated RateLimitStatus (caller should check ``is_exceeded``).
        """
        redis_key = f"{_REDIS_KEY_PREFIX}:{key_id}"
        current_count = await self._redis.get(redis_key)

        if current_count is None:
            # First request in window -- set with TTL
            await self._redis.set(redis_key, "1", ex=self._window_seconds)
            current_count_int = 1
        else:
            current_count_int = int(current_count) + 1
            await self._redis.set(
                redis_key,
                str(current_count_int),
                ex=self._window_seconds,
            )

        remaining = max(0, self._max_requests - current_count_int)
        now = datetime.now(timezone.utc)
        reset_at = now + timedelta(seconds=self._window_seconds)

        return RateLimitStatus(
            key_id=key_id,
            requests_remaining=remaining,
            requests_limit=self._max_requests,
            window_seconds=self._window_seconds,
            reset_at=reset_at,
        )
