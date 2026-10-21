"""WebSocket connection lifecycle handler.

Manages the full lifecycle of a WebSocket connection:

1. Accept connection
2. Receive auth message -> validate via AuthServiceProtocol
3. Send auth_ok or auth_failed
4. Enter message loop: subscribe, unsubscribe, ping/pong
5. Push server events to subscribed channels
6. Close on timeout, error, or explicit disconnect

The handler delegates to ConnectionManager for tracking and
ChannelManager for subscription logic.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from src.core.errors import AppError
from src.core.types.websocket import WSChannel, WSMessage, WSMessageType
from src.modules.api.websocket.channels import ChannelManager
from src.modules.api.websocket.manager import ConnectionManager

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.auth.protocols import AuthServiceProtocol

# Default config values
_DEFAULT_HEARTBEAT_INTERVAL = 30
_DEFAULT_CONNECTION_TIMEOUT = 60
_DEFAULT_MAX_CONNECTIONS_PER_PLAYER = 3
_DEFAULT_MAX_MESSAGE_SIZE = 65536


class WebSocketHandler:
    """Handle individual WebSocket connection lifecycles.

    Each connected client goes through: auth -> message loop -> disconnect.
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        channel_manager: ChannelManager,
        auth_service: AuthServiceProtocol,
        config: ConfigProtocol,
        logger: LoggerProtocol,
    ) -> None:
        self._connections = connection_manager
        self._channels = channel_manager
        self._auth = auth_service
        self._logger = logger

        self._heartbeat_interval: int = config.get(
            "websocket.heartbeat_interval_seconds",
            _DEFAULT_HEARTBEAT_INTERVAL,
        )
        self._connection_timeout: int = config.get(
            "websocket.connection_timeout_seconds",
            _DEFAULT_CONNECTION_TIMEOUT,
        )
        self._max_connections_per_player: int = config.get(
            "websocket.max_connections_per_player",
            _DEFAULT_MAX_CONNECTIONS_PER_PLAYER,
        )
        self._max_message_size: int = config.get(
            "websocket.max_message_size_bytes",
            _DEFAULT_MAX_MESSAGE_SIZE,
        )

    async def handle(self, websocket: WebSocket) -> None:
        """Handle a WebSocket connection from accept to close.

        Args:
            websocket: The incoming WebSocket connection.
        """
        await websocket.accept()

        player_id = await self._authenticate(websocket)
        if player_id is None:
            return

        # Check connection limit
        current_count = self._connections.get_player_connection_count(player_id)
        if current_count >= self._max_connections_per_player:
            await self._send_error(
                websocket,
                "WS_RATE_LIMITED",
                "Maximum connections per player exceeded",
            )
            await websocket.close()
            return

        await self._connections.connect(websocket, player_id)
        self._logger.info(
            "WebSocket connected",
            player_id=str(player_id),
        )

        try:
            await self._message_loop(websocket, player_id)
        except WebSocketDisconnect:
            self._logger.info(
                "WebSocket disconnected",
                player_id=str(player_id),
            )
        except Exception:
            self._logger.error(
                "WebSocket error",
                player_id=str(player_id),
            )
        finally:
            await self._cleanup(websocket, player_id)

    async def _authenticate(self, websocket: WebSocket) -> UUID | None:
        """Wait for and process the auth message.

        Args:
            websocket: The WebSocket connection.

        Returns:
            The authenticated player_id, or None if auth failed.
        """
        try:
            raw = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=self._connection_timeout,
            )
        except asyncio.TimeoutError:
            await self._send_error(
                websocket,
                "WS_AUTH_REQUIRED",
                "Authentication timeout",
            )
            await websocket.close()
            return None

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            await self._send_error(
                websocket,
                "WS_INVALID_MESSAGE",
                "Malformed JSON",
            )
            await websocket.close()
            return None

        msg_type = data.get("type")
        if msg_type != WSMessageType.AUTH.value:
            await self._send_error(
                websocket,
                "WS_AUTH_REQUIRED",
                "First message must be auth",
            )
            await websocket.close()
            return None

        token = data.get("payload", {}).get("token")
        if not token:
            await self._send_auth_failed(websocket, "WS_AUTH_REQUIRED", "Token missing")
            await websocket.close()
            return None

        try:
            auth_token = await self._auth.validate_token(token)
        except AppError as exc:
            await self._send_auth_failed(websocket, exc.code, exc.message)
            await websocket.close()
            return None

        # Send auth_ok
        await self._send_message(
            websocket,
            WSMessage(
                type=WSMessageType.AUTH_OK,
                payload={"player_id": str(auth_token.player_id)},
            ),
        )

        return auth_token.player_id

    async def _message_loop(self, websocket: WebSocket, player_id: UUID) -> None:
        """Process messages from the client in a loop.

        Args:
            websocket: The authenticated WebSocket connection.
            player_id: The authenticated player's ID.
        """
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=self._connection_timeout,
                )
            except asyncio.TimeoutError:
                # Send ping to check if connection is alive
                await self._send_message(
                    websocket,
                    WSMessage(
                        type=WSMessageType.PONG,
                        payload={"reason": "timeout_check"},
                    ),
                )
                continue

            if len(raw) > self._max_message_size:
                await self._send_error(
                    websocket,
                    "WS_MESSAGE_TOO_LARGE",
                    "Message exceeds size limit",
                )
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await self._send_error(
                    websocket,
                    "WS_INVALID_MESSAGE",
                    "Malformed JSON",
                )
                continue

            msg_type = data.get("type")
            payload = data.get("payload", {})

            await self._handle_message(websocket, player_id, msg_type, payload)

    async def _handle_message(
        self,
        websocket: WebSocket,
        player_id: UUID,
        msg_type: str | None,
        payload: dict[str, Any],
    ) -> None:
        """Route a client message to the appropriate handler.

        Args:
            websocket: The WebSocket connection.
            player_id: The authenticated player's ID.
            msg_type: The message type string.
            payload: The message payload dict.
        """
        if msg_type == WSMessageType.PING.value:
            await self._send_message(
                websocket,
                WSMessage(
                    type=WSMessageType.PONG,
                    payload={},
                ),
            )

        elif msg_type == WSMessageType.SUBSCRIBE.value:
            await self._handle_subscribe(websocket, player_id, payload)

        elif msg_type == WSMessageType.UNSUBSCRIBE.value:
            await self._handle_unsubscribe(websocket, player_id, payload)

        else:
            await self._send_error(
                websocket,
                "WS_INVALID_MESSAGE",
                f"Unknown message type: {msg_type}",
            )

    async def _handle_subscribe(
        self,
        websocket: WebSocket,
        player_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        """Process a channel subscription request.

        Args:
            websocket: The WebSocket connection.
            player_id: The authenticated player's ID.
            payload: Must contain ``channel``; may contain subscription params.
        """
        channel_name = payload.get("channel")
        if channel_name is None:
            await self._send_error(
                websocket,
                "WS_CHANNEL_INVALID",
                "Channel name is required",
            )
            return

        try:
            channel = WSChannel(channel_name)
        except ValueError:
            await self._send_error(
                websocket,
                "WS_CHANNEL_INVALID",
                f"Invalid channel: {channel_name}",
            )
            return

        params = {k: v for k, v in payload.items() if k != "channel"}

        # For match channel, also subscribe in connection manager
        if channel == WSChannel.MATCH:
            match_id_str = params.get("match_id")
            if match_id_str:
                try:
                    match_uuid = UUID(match_id_str)
                    await self._connections.subscribe_to_match(player_id, match_uuid)
                except ValueError:
                    await self._send_error(
                        websocket,
                        "WS_CHANNEL_INVALID",
                        "Invalid match_id format",
                    )
                    return

        await self._channels.subscribe(player_id, channel, params or None)

        await self._send_message(
            websocket,
            WSMessage(
                type=WSMessageType.SUBSCRIBED,
                payload={"channel": channel.value},
            ),
        )

    async def _handle_unsubscribe(
        self,
        websocket: WebSocket,
        player_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        """Process a channel unsubscription request.

        Args:
            websocket: The WebSocket connection.
            player_id: The authenticated player's ID.
            payload: Must contain ``channel``.
        """
        channel_name = payload.get("channel")
        if channel_name is None:
            await self._send_error(
                websocket,
                "WS_CHANNEL_INVALID",
                "Channel name is required",
            )
            return

        try:
            channel = WSChannel(channel_name)
        except ValueError:
            await self._send_error(
                websocket,
                "WS_CHANNEL_INVALID",
                f"Invalid channel: {channel_name}",
            )
            return

        params = {k: v for k, v in payload.items() if k != "channel"}

        # For match channel, also unsubscribe in connection manager
        if channel == WSChannel.MATCH:
            match_id_str = params.get("match_id")
            if match_id_str:
                try:
                    match_uuid = UUID(match_id_str)
                    await self._connections.unsubscribe_from_match(
                        player_id,
                        match_uuid,
                    )
                except ValueError:
                    pass  # Non-critical; continue unsubscribing from channel

        await self._channels.unsubscribe(player_id, channel, params or None)

        await self._send_message(
            websocket,
            WSMessage(
                type=WSMessageType.UNSUBSCRIBED,
                payload={"channel": channel.value},
            ),
        )

    async def _cleanup(self, websocket: WebSocket, player_id: UUID) -> None:
        """Clean up after a connection ends.

        Args:
            websocket: The disconnected WebSocket.
            player_id: The player who disconnected.
        """
        await self._connections.disconnect(websocket)
        await self._channels.unsubscribe_all(player_id)

    @staticmethod
    async def _send_message(websocket: WebSocket, message: WSMessage) -> None:
        """Send a WSMessage to the client.

        Args:
            websocket: Target WebSocket.
            message: The message to send.
        """
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(message.to_dict())
            except Exception:  # noqa: BLE001
                pass

    @staticmethod
    async def _send_error(
        websocket: WebSocket,
        code: str,
        message: str,
    ) -> None:
        """Send a WS error message to the client.

        Args:
            websocket: Target WebSocket.
            code: Error code.
            message: Error description.
        """
        error_msg = WSMessage(
            type=WSMessageType.ERROR,
            payload={"code": code, "message": message},
        )
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(error_msg.to_dict())
            except Exception:  # noqa: BLE001
                pass

    @staticmethod
    async def _send_auth_failed(
        websocket: WebSocket,
        code: str,
        message: str,
    ) -> None:
        """Send an auth_failed message to the client.

        Args:
            websocket: Target WebSocket.
            code: Error code.
            message: Error description.
        """
        auth_failed = WSMessage(
            type=WSMessageType.AUTH_FAILED,
            payload={"code": code, "message": message},
        )
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(auth_failed.to_dict())
            except Exception:  # noqa: BLE001
                pass
