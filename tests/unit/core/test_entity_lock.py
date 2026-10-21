"""Unit tests for EntityLockManager.

Verifies single acquire/release, concurrent same-entity rejection,
concurrent different-entity success, cleanup, reacquire, and
exception safety.
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest

from src.core.entity_lock import EntityBusyError, EntityLockManager


class TestEntityLockManager:
    """Tests for the EntityLockManager."""

    @pytest.mark.asyncio
    async def test_single_acquire_release(self) -> None:
        """A single acquire/release cycle works without error."""
        mgr = EntityLockManager()
        entity_id = uuid4()

        async with mgr.acquire(entity_id):
            pass  # Lock held, then released.

        # After release, no locks should remain.
        assert entity_id not in mgr._locks

    @pytest.mark.asyncio
    async def test_concurrent_same_entity_raises(self) -> None:
        """Two concurrent acquires on the same entity raise EntityBusyError."""
        mgr = EntityLockManager()
        entity_id = uuid4()
        reached_inner = False

        async with mgr.acquire(entity_id):
            with pytest.raises(EntityBusyError) as exc_info:
                async with mgr.acquire(entity_id):
                    reached_inner = True

            assert exc_info.value.entity_id == entity_id

        assert not reached_inner

    @pytest.mark.asyncio
    async def test_concurrent_different_entities_succeed(self) -> None:
        """Locks on different entities don't interfere."""
        mgr = EntityLockManager()
        entity_a = uuid4()
        entity_b = uuid4()
        results: list[str] = []

        async def task_a():
            async with mgr.acquire(entity_a):
                results.append("a_start")
                await asyncio.sleep(0.01)
                results.append("a_end")

        async def task_b():
            async with mgr.acquire(entity_b):
                results.append("b_start")
                await asyncio.sleep(0.01)
                results.append("b_end")

        await asyncio.gather(task_a(), task_b())

        assert "a_start" in results
        assert "a_end" in results
        assert "b_start" in results
        assert "b_end" in results

    @pytest.mark.asyncio
    async def test_cleanup_after_release(self) -> None:
        """Lock dict is cleaned up after all references are released."""
        mgr = EntityLockManager()
        entity_id = uuid4()

        async with mgr.acquire(entity_id):
            assert entity_id in mgr._locks

        # After context exit, lock should be cleaned up.
        assert entity_id not in mgr._locks
        assert entity_id not in mgr._refs

    @pytest.mark.asyncio
    async def test_reacquire_after_release(self) -> None:
        """An entity can be re-acquired after the previous holder releases."""
        mgr = EntityLockManager()
        entity_id = uuid4()

        async with mgr.acquire(entity_id):
            pass

        # Should succeed — lock was released.
        async with mgr.acquire(entity_id):
            pass

    @pytest.mark.asyncio
    async def test_cleanup_on_exception(self) -> None:
        """Lock is properly released even if the body raises an exception."""
        mgr = EntityLockManager()
        entity_id = uuid4()

        with pytest.raises(ValueError, match="test error"):
            async with mgr.acquire(entity_id):
                raise ValueError("test error")

        # Lock should be cleaned up despite the exception.
        assert entity_id not in mgr._locks

        # Should be re-acquirable.
        async with mgr.acquire(entity_id):
            pass

    @pytest.mark.asyncio
    async def test_entity_busy_error_message(self) -> None:
        """EntityBusyError has a useful string representation."""
        entity_id = uuid4()
        error = EntityBusyError(entity_id)

        assert str(entity_id) in str(error)
        assert "busy" in str(error).lower()


class TestEntityBusyError:
    """Tests for the EntityBusyError exception."""

    def test_is_exception(self) -> None:
        """EntityBusyError is a proper Exception subclass."""
        error = EntityBusyError(uuid4())
        assert isinstance(error, Exception)

    def test_entity_id_stored(self) -> None:
        """The entity_id is accessible on the exception."""
        entity_id = uuid4()
        error = EntityBusyError(entity_id)
        assert error.entity_id == entity_id
