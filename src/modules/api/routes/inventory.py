"""Inventory route handlers.

Provides ``/api/v1/inventory/*`` endpoints for mega gem inventory management.

All handlers delegate to ``inventory_service`` retrieved from ``request.app.state``.
Responses flow through the ``ResponseAdapter`` envelope.
``AppError`` exceptions propagate to the error handler middleware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.core.types.game import PlayerId
from src.modules.api.dependencies import (
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])

# Slot index -> mega value mapping (mirrors service.SLOT_MEGA_VALUES).
SLOT_MEGA_VALUES: dict[int, int] = {0: 11, 1: 22, 2: 33, 3: 44, 4: -1}


# -- Endpoints ----------------------------------------------------------------


@router.get("/mega")
async def get_mega_inventory(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the authenticated player's mega gem inventory counts.

    Returns all 5 inventory slots with their mega value mappings
    and current counts.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.

    Returns:
        Inventory slots with slot_index, mega_value, and count.
    """
    player_id = get_current_player_id(request)
    svc = request.app.state.inventory_service

    counts = await svc.get_mega_counts(PlayerId(UUID(player_id)))

    slots = [
        {
            "slot_index": i,
            "mega_value": SLOT_MEGA_VALUES[i],
            "count": counts.get(i, 0),
        }
        for i in range(5)
    ]

    return response.success(data={"slots": slots}, correlation_id=correlation_id)
