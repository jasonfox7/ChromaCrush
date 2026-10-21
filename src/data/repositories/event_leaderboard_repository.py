"""Redis implementation of event leaderboard repository protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from src.core.protocols.logger import LoggerProtocol


class RedisEventLeaderboardRepository:
    """Concrete event leaderboard repository backed by Redis sorted sets.

    Uses the key pattern ``chromacrush:event:{event_id}:leaderboard``
    for each event's real-time leaderboard.
    """

    def __init__(self, redis: Redis, logger: LoggerProtocol) -> None:
        self._redis = redis
        self._logger = logger

    def _key(self, event_id: UUID) -> str:
        return f"chromacrush:event:{event_id}:leaderboard"

    async def update_score(
        self,
        event_id: UUID,
        player_id: UUID,
        score: int,
    ) -> None:
        """Update player's score on leaderboard."""
        key = self._key(event_id)
        await self._redis.zadd(key, {str(player_id): score})

    async def get_rank(self, event_id: UUID, player_id: UUID) -> int | None:
        """Get player's current rank (1-indexed)."""
        key = self._key(event_id)
        rank = await self._redis.zrevrank(key, str(player_id))
        if rank is None:
            return None
        return rank + 1  # Convert 0-indexed to 1-indexed

    async def get_score(self, event_id: UUID, player_id: UUID) -> int | None:
        """Get player's current score."""
        key = self._key(event_id)
        score = await self._redis.zscore(key, str(player_id))
        if score is None:
            return None
        return int(score)

    async def get_top(
        self,
        event_id: UUID,
        limit: int,
        offset: int = 0,
    ) -> list[tuple[str, int]]:
        """Get top players: list of (player_id_str, score)."""
        key = self._key(event_id)
        start = offset
        stop = offset + limit - 1
        results = await self._redis.zrevrange(
            key,
            start,
            stop,
            withscores=True,
        )
        return [(member, int(score)) for member, score in results]

    async def get_total_count(self, event_id: UUID) -> int:
        """Get total number of ranked players."""
        key = self._key(event_id)
        count = await self._redis.zcard(key)
        return count or 0

    async def get_percentile(
        self,
        event_id: UUID,
        player_id: UUID,
    ) -> float | None:
        """Get player's percentile (0-100, higher is better)."""
        rank = await self.get_rank(event_id, player_id)
        if rank is None:
            return None
        total = await self.get_total_count(event_id)
        if total == 0:
            return None
        return ((total - rank + 1) / total) * 100

    async def remove_player(self, event_id: UUID, player_id: UUID) -> None:
        """Remove player from leaderboard."""
        key = self._key(event_id)
        await self._redis.zrem(key, str(player_id))

    async def clear_leaderboard(self, event_id: UUID) -> None:
        """Clear entire leaderboard (for cleanup)."""
        key = self._key(event_id)
        await self._redis.delete(key)

    async def sync_to_database(
        self,
        event_id: UUID,
        participant_repo: Any,
    ) -> int:
        """Sync leaderboard ranks to database. Returns count synced."""
        key = self._key(event_id)
        total = await self._redis.zcard(key)
        if not total:
            return 0

        # Get all members with their ranks
        all_members = await self._redis.zrevrange(key, 0, -1, withscores=True)
        ranks: list[tuple[UUID, int]] = []
        for i, (member, _score) in enumerate(all_members):
            ranks.append((UUID(member), i + 1))

        count = await participant_repo.bulk_update_ranks(event_id, ranks)
        self._logger.debug(
            "Leaderboard synced to database",
            event_id=str(event_id),
            count=count,
        )
        return count
