"""Redis-backed matchmaking queue repository.

Implements ``MatchmakingQueueRepositoryProtocol`` using Redis sorted sets
for ELO-based queues and hashes for player state. All operations are async.

Key patterns:
    - ``chromacrush:matchmaking:queue:{pool_type}`` -- Sorted set (score = ELO)
    - ``chromacrush:matchmaking:player:{player_id}`` -- Hash (player queue state)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from src.modules.matchmaking.types import PoolType, QueueEntryData

if TYPE_CHECKING:
    from src.core.data_context import DataContext


_QUEUE_KEY_PREFIX = "chromacrush:matchmaking:queue:"
_PLAYER_KEY_PREFIX = "chromacrush:matchmaking:player:"


def _queue_key(pool_type: PoolType) -> str:
    """Build the Redis sorted set key for a pool."""
    return f"{_QUEUE_KEY_PREFIX}{pool_type.value}"


def _player_key(player_id: UUID) -> str:
    """Build the Redis hash key for a player's queue state."""
    return f"{_PLAYER_KEY_PREFIX}{player_id}"


def _parse_queue_entry_data(player_id: UUID, data: dict[str, str]) -> QueueEntryData:
    """Parse a Redis hash into a QueueEntryData dataclass."""
    return QueueEntryData(
        player_id=player_id,
        elo_rating=int(data["elo_rating"]),
        pool_type=PoolType(data["pool_type"]),
        joined_at=datetime.fromisoformat(data["joined_at"]),
        last_expansion_at=datetime.fromisoformat(data["last_expansion_at"]),
        current_min_elo=int(data["current_min_elo"]),
        current_max_elo=int(data["current_max_elo"]),
    )


class RedisMatchmakingQueueRepository:
    """Concrete Redis-backed matchmaking queue repository.

    Uses sorted sets for efficient ELO range queries and hashes for
    per-player queue state. All methods are ``async def``.

    Args:
        data_ctx: DataContext providing the Redis client via ``.redis``.
    """

    def __init__(self, data_ctx: DataContext) -> None:
        self._redis = data_ctx.redis

    async def add_to_queue(
        self,
        player_id: UUID,
        elo_rating: int,
        pool_type: PoolType,
        initial_elo_range: int,
    ) -> QueueEntryData:
        """Add player to matchmaking queue atomically."""
        now = datetime.now(timezone.utc)
        min_elo = max(0, elo_rating - initial_elo_range)
        max_elo = elo_rating + initial_elo_range

        player_hash_key = _player_key(player_id)
        queue_sorted_set_key = _queue_key(pool_type)

        # Use pipeline for atomicity
        pipe = self._redis.pipeline()
        pipe.zadd(queue_sorted_set_key, {str(player_id): float(elo_rating)})
        pipe.hset(
            player_hash_key,
            mapping={
                "pool_type": pool_type.value,
                "elo_rating": str(elo_rating),
                "joined_at": now.isoformat(),
                "last_expansion_at": now.isoformat(),
                "current_min_elo": str(min_elo),
                "current_max_elo": str(max_elo),
            },
        )
        # TTL = queue_timeout + 60s buffer (360 seconds default)
        pipe.expire(player_hash_key, 360)
        await pipe.execute()

        return QueueEntryData(
            player_id=player_id,
            elo_rating=elo_rating,
            pool_type=pool_type,
            joined_at=now,
            last_expansion_at=now,
            current_min_elo=min_elo,
            current_max_elo=max_elo,
        )

    async def remove_from_queue(self, player_id: UUID) -> bool:
        """Remove player from queue. Returns True if they were in queue."""
        player_hash_key = _player_key(player_id)

        # Get the player's pool type so we know which sorted set to remove from
        data = await self._redis.hgetall(player_hash_key)
        if not data:
            return False

        pool_type = PoolType(data["pool_type"])
        queue_key = _queue_key(pool_type)

        pipe = self._redis.pipeline()
        pipe.zrem(queue_key, str(player_id))
        pipe.delete(player_hash_key)
        await pipe.execute()

        return True

    async def get_player_queue_state(self, player_id: UUID) -> QueueEntryData | None:
        """Get player's current queue state from hash."""
        player_hash_key = _player_key(player_id)
        data = await self._redis.hgetall(player_hash_key)
        if not data:
            return None

        return _parse_queue_entry_data(player_id, data)

    async def is_in_queue(self, player_id: UUID) -> bool:
        """Check if player is in any queue."""
        player_hash_key = _player_key(player_id)
        return bool(await self._redis.exists(player_hash_key))

    async def find_opponents_in_range(
        self,
        pool_type: PoolType,
        min_elo: int,
        max_elo: int,
        exclude_player_id: UUID,
        limit: int = 10,
    ) -> list[tuple[UUID, int]]:
        """Find players in ELO range using ZRANGEBYSCORE."""
        queue_key = _queue_key(pool_type)

        # Fetch more than limit to account for exclusion
        members = await self._redis.zrangebyscore(
            queue_key,
            min=float(min_elo),
            max=float(max_elo),
            withscores=True,
            start=0,
            num=limit + 1,
        )

        results: list[tuple[UUID, int]] = []
        exclude_str = str(exclude_player_id)

        for member, score in members:
            if member == exclude_str:
                continue
            results.append((UUID(member), int(score)))
            if len(results) >= limit:
                break

        return results

    async def get_queue_count(self, pool_type: PoolType) -> int:
        """Get count of players in a queue."""
        queue_key = _queue_key(pool_type)
        return await self._redis.zcard(queue_key)

    async def get_all_queued_players(
        self,
        pool_type: PoolType,
    ) -> list[QueueEntryData]:
        """Get all players in a queue, ordered by join time (FIFO)."""
        queue_key = _queue_key(pool_type)

        # Get all members with scores
        members = await self._redis.zrangebyscore(
            queue_key,
            min="-inf",
            max="+inf",
            withscores=True,
        )

        entries: list[QueueEntryData] = []
        for member_id_str, _score in members:
            player_id = UUID(member_id_str)
            state = await self.get_player_queue_state(player_id)
            if state is not None:
                entries.append(state)

        # Sort by joined_at for FIFO ordering
        entries.sort(key=lambda e: e.joined_at)
        return entries

    async def update_elo_range(
        self,
        player_id: UUID,
        new_min_elo: int,
        new_max_elo: int,
    ) -> None:
        """Update player's expanded ELO range."""
        player_hash_key = _player_key(player_id)
        now = datetime.now(timezone.utc)

        await self._redis.hset(
            player_hash_key,
            mapping={
                "current_min_elo": str(new_min_elo),
                "current_max_elo": str(new_max_elo),
                "last_expansion_at": now.isoformat(),
            },
        )

    async def remove_stale_entries(
        self,
        cutoff_time: datetime,
    ) -> int:
        """Remove entries older than cutoff. Returns count removed."""
        removed_count = 0

        # Check all pool types
        for pool_type in PoolType:
            queue_key = _queue_key(pool_type)

            # Get all members
            members = await self._redis.zrangebyscore(
                queue_key,
                min="-inf",
                max="+inf",
                withscores=True,
            )

            for member_id_str, _score in members:
                player_id = UUID(member_id_str)
                state = await self.get_player_queue_state(player_id)

                if state is None:
                    # Orphaned sorted set entry, remove it
                    await self._redis.zrem(queue_key, member_id_str)
                    removed_count += 1
                    continue

                if state.joined_at < cutoff_time:
                    # Stale entry, remove from both sorted set and hash
                    pipe = self._redis.pipeline()
                    pipe.zrem(queue_key, member_id_str)
                    pipe.delete(_player_key(player_id))
                    await pipe.execute()
                    removed_count += 1

        return removed_count

    async def get_players_by_elo_bucket(
        self,
        pool_type: PoolType,
        bucket_size: int = 100,
    ) -> dict[str, int]:
        """Get count of players in each ELO bucket."""
        queue_key = _queue_key(pool_type)

        members = await self._redis.zrangebyscore(
            queue_key,
            min="-inf",
            max="+inf",
            withscores=True,
        )

        buckets: dict[str, int] = {}
        for _member, score in members:
            elo = int(score)
            bucket_start = (elo // bucket_size) * bucket_size
            bucket_end = bucket_start + bucket_size
            label = f"{bucket_start}-{bucket_end}"
            buckets[label] = buckets.get(label, 0) + 1

        return buckets

    async def atomic_remove_pair(
        self,
        player1_id: UUID,
        player2_id: UUID,
    ) -> bool:
        """Atomically remove two players from queue.

        Checks both players are still in queue, then removes them
        atomically using a pipeline. Returns False if either was
        already gone.
        """
        p1_key = _player_key(player1_id)
        p2_key = _player_key(player2_id)

        # Check both are still in queue
        p1_data = await self._redis.hgetall(p1_key)
        p2_data = await self._redis.hgetall(p2_key)

        if not p1_data or not p2_data:
            return False

        p1_pool = PoolType(p1_data["pool_type"])
        p2_pool = PoolType(p2_data["pool_type"])

        # Remove both atomically
        pipe = self._redis.pipeline()
        pipe.zrem(_queue_key(p1_pool), str(player1_id))
        pipe.zrem(_queue_key(p2_pool), str(player2_id))
        pipe.delete(p1_key)
        pipe.delete(p2_key)
        await pipe.execute()

        return True
