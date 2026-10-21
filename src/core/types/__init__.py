"""Shared domain types for ChromaCrush.

All modules import from this package. No module defines its own version
of any shared concept.
"""

from src.core.types.auth import ApiKeyInfo, AuthToken, TokenType
from src.core.types.board import BoardGrid, BoardState, MatchGroup, MatchResult
from src.core.types.game import (
    ArtifactId,
    EventId,
    GemType,
    MatchId,
    Move,
    PlayerId,
    Position,
)
from src.core.types.match import MatchState, MatchStatus, MatchType, PlayerMatchState
from src.core.types.player import EnergyState, Player, PlayerStats, PlayerType
from src.core.types.websocket import (
    WSAuthMessage,
    WSChannel,
    WSMatchUpdate,
    WSMessage,
    WSMessageType,
    WSSubscribeMessage,
)

__all__ = [
    # game.py — identifiers
    "PlayerId",
    "MatchId",
    "ArtifactId",
    "EventId",
    # game.py — enums and value objects
    "GemType",
    "Position",
    "Move",
    # board.py
    "BoardGrid",
    "BoardState",
    "MatchGroup",
    "MatchResult",
    # match.py
    "MatchType",
    "MatchStatus",
    "PlayerMatchState",
    "MatchState",
    # player.py
    "PlayerType",
    "Player",
    "PlayerStats",
    "EnergyState",
    # auth.py
    "TokenType",
    "AuthToken",
    "ApiKeyInfo",
    # websocket.py
    "WSMessageType",
    "WSChannel",
    "WSMessage",
    "WSAuthMessage",
    "WSSubscribeMessage",
    "WSMatchUpdate",
]
