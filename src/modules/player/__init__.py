"""Player module for ChromaCrush.

Manages player accounts, ELO ratings, statistics, and energy state
data ownership. This module is fully async -- all public service methods
are ``async def``.

Exports:
    PlayerService: Concrete service implementation.
    PlayerServiceProtocol: Protocol interface for dependency injection.
"""

from src.modules.player.protocols import PlayerServiceProtocol
from src.modules.player.service import PlayerService

__all__ = [
    "PlayerService",
    "PlayerServiceProtocol",
]
