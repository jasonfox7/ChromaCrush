"""Matchmaking module for ChromaCrush.

Manages matchmaking queues, ELO-based pairing, and match creation.
This module is fully async -- all public service methods are ``async def``.

Exports:
    MatchmakingService: Concrete service implementation.
    MatchmakingServiceProtocol: Protocol interface for dependency injection.
"""

from src.modules.matchmaking.protocols import MatchmakingServiceProtocol
from src.modules.matchmaking.service import MatchmakingService
from src.modules.matchmaking.types import (
    MatchmakingResult,
    MatchmakingStatus,
    PoolType,
    QueueEntry,
    QueueEntryData,
    QueueStats,
    QueueStatus,
)

__all__ = [
    "MatchmakingResult",
    "MatchmakingService",
    "MatchmakingServiceProtocol",
    "MatchmakingStatus",
    "PoolType",
    "QueueEntry",
    "QueueEntryData",
    "QueueStats",
    "QueueStatus",
]
