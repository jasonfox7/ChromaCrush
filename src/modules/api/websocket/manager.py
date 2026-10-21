"""WebSocket connection manager.

Tracks active WebSocket connections per player and provides methods for
broadcasting messages to individual players or all participants in a match.
Thread-safe via asyncio locks.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from starlette.websockets import WebSocket

from src.core.types.websocket import WSMessage


class ConnectionManager:
    """Manage active WebSocket connections.

    Connections are tracked per player, allowing fan-out to all sessions
    for a given player or match.
    """

    def __init__(self) -> None:
        # player_id -> set of WebSocket connections
        self._connections: dict[UUID, set[WebSocket]] = {}
        # match_id -> set of player_ids subscribed to that match
        self._match_subscriptions: dict[UUID, set[UUID]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, player_id: UUID) -> None:
        """Register a new WebSocket connection for a player.

        Args:
            websocket: The WebSocket connection to track.
            player_id: The authenticated player's ID.
        """
        async with self._lock:
            if player_id not in self._connections:
                self._connections[player_id] = set()
            self._connections[player_id].add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from tracking.

        Cleans up empty player entries and match subscriptions.

        Args:
            websocket: The WebSocket connection to remove.
        """
        async with self._lock:
            player_id = self._find_player_for_connection(websocket)
            if player_id is None:
                return

            self._connections[player_id].discard(websocket)
            if not self._connections[player_id]:
                del self._connections[player_id]
                # Remove from all match subscriptions
                for match_subs in self._match_subscriptions.values():
                    match_subs.discard(player_id)
                # Clean up empty match subscriptions
                self._match_subscriptions = {
                    mid: subs for mid, subs in self._match_subscriptions.items() if subs
                }

    async def subscribe_to_match(
        self,
        player_id: UUID,
        match_id: UUID,
    ) -> None:
        """Subscribe a player to receive updates for a match.

        Args:
            player_id: The player subscribing.
            match_id: The match to subscribe to.
        """
        async with self._lock:
            if match_id not in self._match_subscriptions:
                self._match_subscriptions[match_id] = set()
            self._match_subscriptions[match_id].add(player_id)

    async def unsubscribe_from_match(
        self,
        player_id: UUID,
        match_id: UUID,
    ) -> None:
        """Unsubscribe a player from a match's updates.

        Args:
            player_id: The player unsubscribing.
            match_id: The match to unsubscribe from.
        """
        async with self._lock:
            subs = self._match_subscriptions.get(match_id)
            if subs is not None:
                subs.discard(player_id)
                if not subs:
                    del self._match_subscriptions[match_id]

    async def broadcast_to_player(
        self,
        player_id: UUID,
        message: WSMessage,
    ) -> None:
        """Send a message to all connections for a player.

        Failed sends are silently ignored (connection may have closed).

        Args:
            player_id: Target player.
            message: The WebSocket message to send.
        """
        async with self._lock:
            connections = self._connections.get(player_id, set()).copy()

        payload = message.to_dict()
        for ws in connections:
            await self._safe_send(ws, payload)

    async def broadcast_to_match(
        self,
        match_id: UUID,
        message: WSMessage,
    ) -> None:
        """Send a message to all players subscribed to a match.

        Args:
            match_id: The match whose subscribers should receive the message.
            message: The WebSocket message to send.
        """
        async with self._lock:
            player_ids = self._match_subscriptions.get(match_id, set()).copy()

        payload = message.to_dict()
        for pid in player_ids:
            async with self._lock:
                connections = self._connections.get(pid, set()).copy()
            for ws in connections:
                await self._safe_send(ws, payload)

    def get_player_connection_count(self, player_id: UUID) -> int:
        """Return the number of active connections for a player.

        Args:
            player_id: The player to check.

        Returns:
            Number of active WebSocket connections.
        """
        return len(self._connections.get(player_id, set()))

    def _find_player_for_connection(self, websocket: WebSocket) -> UUID | None:
        """Find the player ID associated with a WebSocket connection.

        Must be called while holding the lock.

        Args:
            websocket: The WebSocket to look up.

        Returns:
            The player UUID, or None if not found.
        """
        for player_id, conns in self._connections.items():
            if websocket in conns:
                return player_id
        return None

    @staticmethod
    async def _safe_send(websocket: WebSocket, payload: dict[str, Any]) -> None:
        """Send JSON to a WebSocket, ignoring errors on closed connections.

        Args:
            websocket: Target WebSocket.
            payload: The dict to send as JSON.
        """
        try:
            await websocket.send_json(payload)
        except Exception:  # noqa: BLE001  -- connection may be closed
            pass
