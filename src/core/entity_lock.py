"""Per-entity asyncio lock manager.

Provides try-acquire semantics: if an entity is already locked (e.g. a
concurrent request is processing a move), the second caller gets an
``EntityBusyError`` immediately — no queuing, no deadlocks.

Usage:
    locks = EntityLockManager()

    async with locks.acquire(attempt_id):
        # Only one coroutine at a time per entity.
        ...

    # EntityBusyError is raised if another coroutine already holds the lock.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID


class EntityBusyError(Exception):
    """Raised when an entity lock cannot be acquired (already held)."""

    def __init__(self, entity_id: UUID | Any) -> None:
        self.entity_id = entity_id
        super().__init__(f"Entity {entity_id} is busy (concurrent request)")


class EntityLockManager:
    """Manages per-entity asyncio locks with reference counting.

    Each entity gets its own ``asyncio.Lock``. A reference counter tracks
    how many coroutines are waiting or holding the lock so we can clean up
    unused locks and avoid memory leaks.
    """

    def __init__(self) -> None:
        self._locks: dict[Any, asyncio.Lock] = {}
        self._refs: dict[Any, int] = {}

    @asynccontextmanager
    async def acquire(self, entity_id: UUID | Any):
        """Try to acquire the lock for *entity_id*.

        If the lock is already held, raises ``EntityBusyError`` immediately
        (no blocking). On success, yields and releases the lock on exit.
        """
        # Get or create the lock (and bump the ref count).
        if entity_id not in self._locks:
            self._locks[entity_id] = asyncio.Lock()
            self._refs[entity_id] = 0
        self._refs[entity_id] += 1

        lock = self._locks[entity_id]

        # Non-blocking acquire — fail fast if already held.
        acquired = lock.locked()
        if acquired:
            self._refs[entity_id] -= 1
            self._cleanup(entity_id)
            raise EntityBusyError(entity_id)

        await lock.acquire()
        try:
            yield
        finally:
            lock.release()
            self._refs[entity_id] -= 1
            self._cleanup(entity_id)

    def _cleanup(self, entity_id: Any) -> None:
        """Remove lock if no one references it."""
        if self._refs.get(entity_id, 0) <= 0:
            self._locks.pop(entity_id, None)
            self._refs.pop(entity_id, None)
