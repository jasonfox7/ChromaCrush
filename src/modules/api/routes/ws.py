"""WebSocket route.

Mounts the WebSocket endpoint at the configured path (default ``/ws``).
Delegates all connection lifecycle handling to the ``WebSocketHandler``
stored on ``app.state``.
"""

from __future__ import annotations

from fastapi import APIRouter
from starlette.websockets import WebSocket

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket entry point.

    The handler is retrieved from ``app.state.ws_handler`` which is set
    by the ApiFactory during application creation.

    Args:
        websocket: The incoming WebSocket connection.
    """
    ws_handler = websocket.app.state.ws_handler
    await ws_handler.handle(websocket)
