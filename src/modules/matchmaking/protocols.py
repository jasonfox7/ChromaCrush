"""Matchmaking module protocols.

Defines ``MatchmakingServiceProtocol`` for dependent modules and the
presentation layer, plus minimal dependency protocols for injected services.
All methods are ``async def`` because they involve Redis operations and
cross-module service calls.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.core.types.game import MatchId, PlayerId
from src.modules.matchmaking.types import (
    MatchmakingResult,
    PoolType,
    QueueEntry,
    QueueEntryData,
    QueueStats,
    QueueStatus,
)


class MatchmakingServiceProtocol(Protocol):
    """Public interface for the matchmaking module.

    All methods are ``async def`` because they involve Redis operations
    and cross-module coordination.
    """

    async def join_queue(
        self,
        player_id: PlayerId,
        pool_type: PoolType = PoolType.MIXED,
    ) -> QueueEntry:
        """Add a player to the matchmaking queue.

        Args:
            player_id: The player joining the queue.
            pool_type: Which queue pool to join.

        Returns:
            QueueEntry with position and estimated wait time.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            CONFLICT_ALREADY_IN_QUEUE: If player is already queued.
            CONFLICT_PLAYER_IN_MATCH: If player is in an active match.
            FORBIDDEN_POOL_RESTRICTED: If player type not allowed in pool.
        """
        ...

    async def leave_queue(self, player_id: PlayerId) -> bool:
        """Remove a player from the matchmaking queue.

        Args:
            player_id: The player leaving the queue.

        Returns:
            True if player was removed, False if they weren't in queue.
        """
        ...

    async def get_queue_status(self, player_id: PlayerId) -> QueueStatus | None:
        """Get the current queue status for a player.

        Args:
            player_id: The player to check.

        Returns:
            QueueStatus if player is in queue, None otherwise.
        """
        ...

    async def find_match(self, player_id: PlayerId) -> MatchmakingResult:
        """Attempt to find and create a match for a queued player.

        Args:
            player_id: The player seeking a match.

        Returns:
            MatchmakingResult with match details or search status.

        Raises:
            VALIDATION_NOT_IN_QUEUE: If player is not in queue.
        """
        ...

    async def process_queue(self, pool_type: PoolType) -> list[MatchmakingResult]:
        """Background operation to process all pending matches in a queue pool.

        Args:
            pool_type: Which pool to process.

        Returns:
            List of MatchmakingResult for each match created.
        """
        ...

    async def cleanup_stale_entries(self) -> int:
        """Background operation to remove players who have exceeded queue timeout.

        Returns:
            Count of entries removed.
        """
        ...

    async def get_queue_stats(self, pool_type: PoolType | None = None) -> QueueStats:
        """Get statistics about queue status.

        Args:
            pool_type: Filter to specific pool (None for all).

        Returns:
            QueueStats with player counts and wait time info.
        """
        ...


class MatchmakingQueueRepositoryProtocol(Protocol):
    """Repository interface for matchmaking queue data (Redis-backed)."""

    async def add_to_queue(
        self,
        player_id: UUID,
        elo_rating: int,
        pool_type: PoolType,
        initial_elo_range: int,
    ) -> QueueEntryData:
        """Add player to matchmaking queue."""
        ...

    async def remove_from_queue(self, player_id: UUID) -> bool:
        """Remove player from queue. Returns True if player was in queue."""
        ...

    async def get_player_queue_state(self, player_id: UUID) -> QueueEntryData | None:
        """Get player's current queue state from hash."""
        ...

    async def is_in_queue(self, player_id: UUID) -> bool:
        """Check if player is in any queue."""
        ...

    async def find_opponents_in_range(
        self,
        pool_type: PoolType,
        min_elo: int,
        max_elo: int,
        exclude_player_id: UUID,
        limit: int = 10,
    ) -> list[tuple[UUID, int]]:
        """Find players in ELO range using ZRANGEBYSCORE."""
        ...

    async def get_queue_count(self, pool_type: PoolType) -> int:
        """Get count of players in a queue."""
        ...

    async def get_all_queued_players(
        self,
        pool_type: PoolType,
    ) -> list[QueueEntryData]:
        """Get all players in a queue (for processing)."""
        ...

    async def update_elo_range(
        self,
        player_id: UUID,
        new_min_elo: int,
        new_max_elo: int,
    ) -> None:
        """Update player's expanded ELO range."""
        ...

    async def remove_stale_entries(
        self,
        cutoff_time: datetime,
    ) -> int:
        """Remove entries older than cutoff. Returns count removed."""
        ...

    async def get_players_by_elo_bucket(
        self,
        pool_type: PoolType,
        bucket_size: int = 100,
    ) -> dict[str, int]:
        """Get count of players in each ELO bucket."""
        ...

    async def atomic_remove_pair(
        self,
        player1_id: UUID,
        player2_id: UUID,
    ) -> bool:
        """Atomically remove two players from queue.

        Returns True if both were removed, False if either was already gone.
        """
        ...


# ---------------------------------------------------------------------------
# Minimal dependency protocols (only the methods matchmaking uses)
# ---------------------------------------------------------------------------


class MatchServiceProtocol(Protocol):
    """Minimal match service interface required by matchmaking module."""

    async def create_match(
        self,
        player1_id: PlayerId,
        player2_id: PlayerId,
        board_seed: int | None = None,
        match_type: Any = None,
    ) -> Any:
        """Create a new match between two players."""
        ...

    async def get_active_matches(
        self,
        player_id: PlayerId,
    ) -> list[Any]:
        """Get all active matches for a player."""
        ...


class PlayerServiceProtocol(Protocol):
    """Minimal player service interface required by matchmaking module."""

    async def get_player(self, player_id: PlayerId) -> Any:
        """Get player by ID. Raises NOT_FOUND_PLAYER if not found."""
        ...

    async def get_elo(self, player_id: PlayerId) -> int:
        """Get player's current ELO rating."""
        ...

    async def list_players(
        self,
        player_type: Any = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Any:
        """List players with optional filtering."""
        ...
