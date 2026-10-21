"""WebSocket message types for ChromaCrush.

Defines message types, channel subscriptions, and typed message structures
for real-time communication alongside the REST API.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class WSMessageType(Enum):
    """All WebSocket message types for client-server communication."""

    # Client -> Server
    AUTH = "auth"
    PING = "ping"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"

    # Server -> Client
    AUTH_OK = "auth_ok"
    AUTH_FAILED = "auth_failed"
    PONG = "pong"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    ERROR = "error"

    # Event pushes (Server -> Client)
    MATCH_UPDATE = "match_update"
    MATCH_STARTED = "match_started"
    MATCH_ENDED = "match_ended"
    OPPONENT_MOVED = "opponent_moved"
    ENERGY_UPDATE = "energy_update"
    MATCHMAKING_FOUND = "matchmaking_found"
    MATCHMAKING_TIMEOUT = "matchmaking_timeout"
    EVENT_STARTED = "event_started"
    EVENT_ENDED = "event_ended"


class WSChannel(Enum):
    """Subscribable WebSocket channels."""

    MATCH = "match"  # Match state updates
    ENERGY = "energy"  # Energy regeneration
    MATCHMAKING = "matchmaking"  # Queue status
    EVENTS = "events"  # Event notifications


@dataclass
class WSMessage:
    """Base WebSocket message structure."""

    type: WSMessageType
    payload: dict[str, Any]
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class WSAuthMessage:
    """Client authentication message."""

    token: str  # JWT or API key


@dataclass
class WSSubscribeMessage:
    """Subscribe to a channel."""

    channel: WSChannel
    params: dict[str, Any] | None = None  # e.g., {"match_id": "..."}


@dataclass
class WSMatchUpdate:
    """Real-time match state push."""

    match_id: str
    board: list[list[int]]
    scores: dict[str, int]
    current_turn: str
    moves_remaining: dict[str, int]
    last_move: dict[str, Any] | None = None
