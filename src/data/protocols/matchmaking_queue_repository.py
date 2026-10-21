"""Matchmaking queue repository protocol.

Defines the repository interface for matchmaking queue data backed by Redis.
The concrete implementation uses Redis sorted sets for ELO-based queues
and hashes for player state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.matchmaking.types import PoolType, QueueEntryData


class MatchmakingQueueRepositoryProtocol(Protocol):
    """Repository interface for matchmaking queue data (Redis-backed)."""

    async def add_to_queue(
        self,
        player_id: UUID,
        elo_rating: int,
        pool_type: PoolType,
        initial_elo_range: int,
    ) -> QueueEntryData:
        """Add player to matchmaking queue.

        Creates sorted set entry and player hash atomically.

        Args:
            player_id: The player joining the queue.
            elo_rating: Player's current ELO rating (used as sorted set score).
            pool_type: Which queue pool to join.
            initial_elo_range: Starting +/- ELO search range.

        Returns:
            QueueEntryData with the created entry's state.
        """
        ...

    async def remove_from_queue(self, player_id: UUID) -> bool:
        """Remove player from queue.

        Removes from sorted set and deletes player hash.

        Args:
            player_id: The player to remove.

        Returns:
            True if player was in queue, False otherwise.
        """
        ...

    async def get_player_queue_state(self, player_id: UUID) -> QueueEntryData | None:
        """Get player's current queue state from hash.

        Args:
            player_id: The player to look up.

        Returns:
            QueueEntryData if player is in queue, None otherwise.
        """
        ...

    async def is_in_queue(self, player_id: UUID) -> bool:
        """Check if player is in any queue.

        Args:
            player_id: The player to check.

        Returns:
            True if player has a queue state hash.
        """
        ...

    async def find_opponents_in_range(
        self,
        pool_type: PoolType,
        min_elo: int,
        max_elo: int,
        exclude_player_id: UUID,
        limit: int = 10,
    ) -> list[tuple[UUID, int]]:
        """Find players in ELO range using ZRANGEBYSCORE.

        Returns list of (player_id, elo_rating) tuples.
        Sorted by wait time (FIFO within range).

        Args:
            pool_type: Which pool to search.
            min_elo: Minimum ELO rating (inclusive).
            max_elo: Maximum ELO rating (inclusive).
            exclude_player_id: Player to exclude from results.
            limit: Maximum number of results.

        Returns:
            List of (player_id, elo_rating) tuples.
        """
        ...

    async def get_queue_count(self, pool_type: PoolType) -> int:
        """Get count of players in a queue.

        Args:
            pool_type: Which pool to count.

        Returns:
            Number of players in the queue.
        """
        ...

    async def get_all_queued_players(
        self,
        pool_type: PoolType,
    ) -> list[QueueEntryData]:
        """Get all players in a queue (for processing).

        Args:
            pool_type: Which pool to retrieve.

        Returns:
            List of QueueEntryData ordered by join time (FIFO).
        """
        ...

    async def update_elo_range(
        self,
        player_id: UUID,
        new_min_elo: int,
        new_max_elo: int,
    ) -> None:
        """Update player's expanded ELO range.

        Args:
            player_id: The player to update.
            new_min_elo: New minimum ELO in search range.
            new_max_elo: New maximum ELO in search range.
        """
        ...

    async def remove_stale_entries(
        self,
        cutoff_time: datetime,
    ) -> int:
        """Remove entries older than cutoff.

        Args:
            cutoff_time: Entries with joined_at before this time are removed.

        Returns:
            Count of entries removed.
        """
        ...

    async def get_players_by_elo_bucket(
        self,
        pool_type: PoolType,
        bucket_size: int = 100,
    ) -> dict[str, int]:
        """Get count of players in each ELO bucket.

        Args:
            pool_type: Which pool to analyze.
            bucket_size: Size of each ELO bucket (default 100).

        Returns:
            Dict mapping bucket labels to player counts.
        """
        ...

    async def atomic_remove_pair(
        self,
        player1_id: UUID,
        player2_id: UUID,
    ) -> bool:
        """Atomically remove two players from queue.

        Uses Redis WATCH/MULTI for atomicity.

        Args:
            player1_id: First player to remove.
            player2_id: Second player to remove.

        Returns:
            True if both were removed, False if either was already gone.
        """
        ...
