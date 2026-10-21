"""WebSocket channel subscription management.

Defines the four channel types and their allowed event types:

- ``match``:  match_update, opponent_moved, match_ended
- ``energy``: energy_update
- ``matchmaking``: matchmaking_found, matchmaking_timeout
- ``events``: event_started, event_ended

The ChannelManager tracks per-player channel subscriptions and provides
helpers for determining which events should be delivered to a player.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from src.core.types.websocket import WSChannel, WSMessageType

# Channel -> allowed event types mapping
CHANNEL_EVENTS: dict[WSChannel, frozenset[WSMessageType]] = {
    WSChannel.MATCH: frozenset(
        {
            WSMessageType.MATCH_UPDATE,
            WSMessageType.OPPONENT_MOVED,
            WSMessageType.MATCH_ENDED,
        }
    ),
    WSChannel.ENERGY: frozenset(
        {
            WSMessageType.ENERGY_UPDATE,
        }
    ),
    WSChannel.MATCHMAKING: frozenset(
        {
            WSMessageType.MATCHMAKING_FOUND,
            WSMessageType.MATCHMAKING_TIMEOUT,
        }
    ),
    WSChannel.EVENTS: frozenset(
        {
            WSMessageType.EVENT_STARTED,
            WSMessageType.EVENT_ENDED,
        }
    ),
}


class _Subscription:
    """A single channel subscription with optional parameters."""

    __slots__ = ("channel", "params")

    def __init__(
        self, channel: WSChannel, params: dict[str, Any] | None = None
    ) -> None:
        self.channel = channel
        self.params = params or {}


class ChannelManager:
    """Manage per-player channel subscriptions.

    Thread-safe via asyncio lock. Tracks which channels each player
    is subscribed to and provides query methods for event routing.
    """

    def __init__(self) -> None:
        # player_id -> list of subscriptions
        self._subscriptions: dict[UUID, list[_Subscription]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        player_id: UUID,
        channel: WSChannel,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """Subscribe a player to a channel.

        Args:
            player_id: The player subscribing.
            channel: The channel to subscribe to.
            params: Optional subscription parameters (e.g., match_id for match channel).

        Returns:
            True if newly subscribed, False if already subscribed.
        """
        async with self._lock:
            if player_id not in self._subscriptions:
                self._subscriptions[player_id] = []

            # Check for duplicate subscription
            for sub in self._subscriptions[player_id]:
                if sub.channel == channel and sub.params == (params or {}):
                    return False

            self._subscriptions[player_id].append(
                _Subscription(channel=channel, params=params),
            )
            return True

    async def unsubscribe(
        self,
        player_id: UUID,
        channel: WSChannel,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """Unsubscribe a player from a channel.

        Args:
            player_id: The player unsubscribing.
            channel: The channel to unsubscribe from.
            params: Optional subscription parameters to match.

        Returns:
            True if unsubscribed, False if no matching subscription found.
        """
        target_params = params or {}
        async with self._lock:
            subs = self._subscriptions.get(player_id)
            if subs is None:
                return False

            for i, sub in enumerate(subs):
                if sub.channel == channel and sub.params == target_params:
                    subs.pop(i)
                    if not subs:
                        del self._subscriptions[player_id]
                    return True

            return False

    async def unsubscribe_all(self, player_id: UUID) -> None:
        """Remove all subscriptions for a player (e.g., on disconnect).

        Args:
            player_id: The player whose subscriptions to clear.
        """
        async with self._lock:
            self._subscriptions.pop(player_id, None)

    async def is_subscribed(
        self,
        player_id: UUID,
        channel: WSChannel,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """Check if a player is subscribed to a specific channel.

        Args:
            player_id: The player to check.
            channel: The channel to check.
            params: Optional parameters to match.

        Returns:
            True if subscribed with matching parameters.
        """
        target_params = params or {}
        async with self._lock:
            subs = self._subscriptions.get(player_id, [])
            return any(s.channel == channel and s.params == target_params for s in subs)

    async def get_subscribed_players(
        self,
        channel: WSChannel,
        params: dict[str, Any] | None = None,
    ) -> list[UUID]:
        """Get all players subscribed to a channel with given params.

        Args:
            channel: The channel to query.
            params: Optional parameters to filter by.

        Returns:
            List of subscribed player UUIDs.
        """
        target_params = params or {}
        async with self._lock:
            result: list[UUID] = []
            for player_id, subs in self._subscriptions.items():
                for sub in subs:
                    if sub.channel == channel and sub.params == target_params:
                        result.append(player_id)
                        break
            return result

    @staticmethod
    def get_channel_events(channel: WSChannel) -> frozenset[WSMessageType]:
        """Get the event types allowed for a channel.

        Args:
            channel: The channel to query.

        Returns:
            Frozenset of allowed WSMessageType values.
        """
        return CHANNEL_EVENTS.get(channel, frozenset())
