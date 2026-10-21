"""Mock Redis client for unit testing.

Provides an in-memory dict-backed implementation of the async Redis
methods used by ChromaCrush services. Tracks all operations so tests
can assert on the exact sequence of calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RedisOperation:
    """Record of a single Redis operation for test assertions."""

    method: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any] = field(default_factory=dict)


class MockRedis:
    """In-memory mock of an async Redis client.

    Supports the subset of Redis commands used by ChromaCrush modules:
    GET, SET, SETEX, DELETE, EXISTS, ZADD, ZREVRANK. All methods are
    async to match the real ``redis.asyncio.Redis`` interface.

    Usage::

        redis = MockRedis()
        await redis.set("key", "value", ex=60)
        result = await redis.get("key")
        assert result == "value"
        assert len(redis.operations) == 2
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._sorted_sets: dict[str, dict[str, float]] = {}
        self.operations: list[RedisOperation] = []

    # ------------------------------------------------------------------
    # String commands
    # ------------------------------------------------------------------

    async def get(self, key: str) -> str | None:
        """Get the value of *key*, or ``None`` if it does not exist."""
        self.operations.append(RedisOperation(method="get", args=(key,)))
        return self._store.get(key)

    async def set(
        self,
        key: str,
        value: str | bytes | int | float,
        ex: int | None = None,
    ) -> bool:
        """Set *key* to *value*. The *ex* parameter is accepted but not enforced.

        Returns:
            ``True`` (matching Redis SET behaviour).
        """
        self.operations.append(
            RedisOperation(method="set", args=(key, value), kwargs={"ex": ex})
        )
        self._store[key] = value if isinstance(value, str) else str(value)
        return True

    async def setex(
        self, key: str, timeout: int, value: str | bytes | int | float
    ) -> bool:
        """Set *key* to *value* with an expiry of *timeout* seconds.

        Expiry tracking is not enforced; the value persists until deleted.

        Returns:
            ``True``.
        """
        self.operations.append(
            RedisOperation(method="setex", args=(key, timeout, value))
        )
        self._store[key] = value if isinstance(value, str) else str(value)
        return True

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys.

        Returns:
            The number of keys that were actually removed.
        """
        self.operations.append(RedisOperation(method="delete", args=keys))
        removed = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                removed += 1
            if key in self._sorted_sets:
                del self._sorted_sets[key]
                removed += 1
        return removed

    async def exists(self, key: str) -> int:
        """Check if *key* exists.

        Returns:
            ``1`` if the key exists, ``0`` otherwise.
        """
        self.operations.append(RedisOperation(method="exists", args=(key,)))
        return 1 if key in self._store or key in self._sorted_sets else 0

    # ------------------------------------------------------------------
    # Sorted set commands
    # ------------------------------------------------------------------

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        """Add members to the sorted set at *key*.

        Args:
            key: The sorted set key.
            mapping: A dict mapping member names to scores.

        Returns:
            The number of **new** members added (not counting score updates).
        """
        self.operations.append(
            RedisOperation(method="zadd", args=(key,), kwargs={"mapping": mapping})
        )
        if key not in self._sorted_sets:
            self._sorted_sets[key] = {}

        added = 0
        for member, score in mapping.items():
            if member not in self._sorted_sets[key]:
                added += 1
            self._sorted_sets[key][member] = score
        return added

    async def zrevrank(self, key: str, member: str) -> int | None:
        """Get the 0-based rank of *member* in the sorted set at *key*, ordered
        from highest to lowest score.

        Returns:
            The rank, or ``None`` if the member or key does not exist.
        """
        self.operations.append(RedisOperation(method="zrevrank", args=(key, member)))
        if key not in self._sorted_sets or member not in self._sorted_sets[key]:
            return None

        # Sort members by score descending, then by member name for ties.
        sorted_members = sorted(
            self._sorted_sets[key].items(),
            key=lambda item: (-item[1], item[0]),
        )
        for rank, (m, _score) in enumerate(sorted_members):
            if m == member:
                return rank
        return None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        """No-op close for compatibility with the real client."""
        self.operations.append(RedisOperation(method="aclose", args=()))

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset all stored data and recorded operations."""
        self._store.clear()
        self._sorted_sets.clear()
        self.operations.clear()

    def assert_called(self, method: str, *, times: int | None = None) -> None:
        """Assert that *method* was called, optionally exactly *times* times.

        Raises:
            AssertionError: If the assertion fails.
        """
        calls = [op for op in self.operations if op.method == method]
        if times is not None:
            if len(calls) != times:
                raise AssertionError(
                    f"Expected {method!r} to be called {times} time(s), "
                    f"but it was called {len(calls)} time(s)."
                )
        elif not calls:
            raise AssertionError(
                f"Expected {method!r} to be called at least once, but it was never called."
            )
