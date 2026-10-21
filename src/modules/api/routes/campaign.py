"""Campaign route handlers.

Provides ``/api/v1/campaign/*`` endpoints for single-player campaign
mode: level listings, progress tracking, attempt lifecycle, and
move submission with obstacle event tracking.

All handlers delegate to ``campaign_service`` retrieved from
``request.app.state``. Responses flow through the ``ResponseAdapter``
envelope.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.core.types.game import Move, PlayerId, Position
from src.modules.api.adapters.cascade_serializer import (
    serialize_applied_modifiers,
    serialize_cascade_steps,
)
from src.modules.api.dependencies import (
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)
from src.modules.api.schemas.campaign import (
    CampaignMegaRequest,
    CampaignMoveRequest,
    StartAttemptRequest,
)

router = APIRouter(prefix="/api/v1/campaign", tags=["campaign"])


@router.get("/levels")
async def list_levels(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: Any = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """List all campaign levels with unlock status for the player."""
    campaign_service = request.app.state.campaign_service
    progress = await campaign_service.get_player_progress(
        UUID(str(player_id))
    )

    levels = []
    for lvl_num in range(1, campaign_service.max_level + 1):
        level_def = campaign_service.get_level_definition(lvl_num)
        levels.append({
            "level": lvl_num,
            "moves": level_def["moves"],
            "gem_colors": level_def.get("gem_colors", 6),
            "objective": level_def["objective"],
            "is_checkpoint": level_def.get("is_checkpoint", False),
            "heart_cost": level_def.get("heart_cost", 0),
            "obstacle_count": len(level_def["obstacles"]),
            "unlocked": lvl_num <= progress["campaign_level"],
            "reward": level_def.get("reward"),
        })

    data = {
        "levels": levels,
        "campaign_level": progress["campaign_level"],
        "active_attempt_id": progress["active_attempt_id"],
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/levels/{level_number}")
async def get_level(
    level_number: int,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: Any = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Get a single campaign level definition."""
    campaign_service = request.app.state.campaign_service
    level_def = campaign_service.get_level_definition(level_number)

    data = {
        "level": level_def["level"],
        "moves": level_def["moves"],
        "gem_colors": level_def.get("gem_colors", 6),
        "objective": level_def["objective"],
        "is_checkpoint": level_def.get("is_checkpoint", False),
        "heart_cost": level_def.get("heart_cost", 0),
        "reward": level_def.get("reward"),
        "obstacles": level_def["obstacles"],
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/progress")
async def get_progress(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: Any = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Get the player's campaign progress."""
    campaign_service = request.app.state.campaign_service
    progress = await campaign_service.get_player_progress(
        UUID(str(player_id))
    )
    return response.success(data=progress, correlation_id=correlation_id)


@router.post("/attempts")
async def start_attempt(
    body: StartAttemptRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: Any = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Start a new campaign level attempt."""
    campaign_service = request.app.state.campaign_service
    attempt, board = await campaign_service.start_attempt(
        player_id=UUID(str(player_id)),
        level_number=body.level_number,
    )

    data = {
        "attempt_id": str(attempt.id),
        "level_number": attempt.level_number,
        "moves_remaining": attempt.moves_remaining,
        "obstacles_remaining": attempt.obstacles_remaining,
        "status": attempt.status,
        "board": {
            "cells": board.grid.tolist(),
            "functions": board.func_grid.tolist(),
        },
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/attempts/{attempt_id}")
async def get_attempt(
    attempt_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: Any = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Get the state of a campaign attempt."""
    campaign_service = request.app.state.campaign_service
    repo = campaign_service._campaign_repo
    attempt = await repo.find_by_id(UUID(attempt_id))

    if attempt is None:
        errors = request.app.state.errors
        raise errors.not_found(
            f"Campaign attempt not found: {attempt_id}",
            code="NOT_FOUND_CAMPAIGN_ATTEMPT",
        )

    if attempt.player_id != UUID(str(player_id)):
        errors = request.app.state.errors
        raise errors.forbidden(
            "Attempt does not belong to this player",
            code="FORBIDDEN_NOT_OWNER",
        )

    data = {
        "attempt_id": str(attempt.id),
        "level_number": attempt.level_number,
        "moves_remaining": attempt.moves_remaining,
        "obstacles_remaining": attempt.obstacles_remaining,
        "status": attempt.status,
        "board": attempt.board_state,
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/attempts/{attempt_id}/move")
async def submit_move(
    attempt_id: str,
    body: CampaignMoveRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: Any = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Submit a move for a campaign attempt."""
    campaign_service = request.app.state.campaign_service

    move = Move(
        from_pos=Position(row=body.from_row, col=body.from_col),
        to_pos=Position(row=body.to_row, col=body.to_col),
        timestamp_ms=0,
    )

    result = await campaign_service.submit_move(
        attempt_id=UUID(attempt_id),
        player_id=UUID(str(player_id)),
        move=move,
    )

    move_result = result["move_result"]

    # Serialize the board state.
    new_board = {
        "cells": move_result.final_board.grid.tolist(),
        "functions": move_result.final_board.func_grid.tolist(),
    }

    # Serialize cascade steps and modifiers using shared helper.
    cascade_steps = serialize_cascade_steps(move_result.cascades)
    applied_modifiers = serialize_applied_modifiers(move_result)

    # If board was reshuffled after deadlock, use the reshuffled board.
    reshuffled = result.get("reshuffled", False)
    if reshuffled and result.get("reshuffled_board"):
        new_board = result["reshuffled_board"]

    data = {
        "valid": move_result.was_valid_match,
        "new_board": new_board,
        "cascade_steps": cascade_steps,
        "applied_modifiers": applied_modifiers,
        "obstacles_remaining": result["obstacles_remaining"],
        "moves_remaining": result["moves_remaining"],
        "status": result["status"],
        "obstacle_events": result["obstacle_events"],
        "score_gained": result["score_gained"],
        "reshuffled": reshuffled,
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/attempts/{attempt_id}/mega")
async def activate_mega(
    attempt_id: str,
    body: CampaignMegaRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: Any = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Activate a banked mega gem or shuffle in a campaign attempt."""
    campaign_service = request.app.state.campaign_service

    result = await campaign_service.activate_mega(
        attempt_id=UUID(attempt_id),
        player_id=UUID(str(player_id)),
        slot_index=body.slot_index,
        source=body.source,
    )

    move_result = result["move_result"]

    # Serialize the board state.
    new_board = {
        "cells": move_result.final_board.grid.tolist(),
        "functions": move_result.final_board.func_grid.tolist(),
    }

    # Serialize cascade steps and modifiers using shared helper.
    cascade_steps = serialize_cascade_steps(move_result.cascades)
    applied_modifiers = serialize_applied_modifiers(move_result)

    # If board was reshuffled after deadlock, use the reshuffled board.
    reshuffled = result.get("reshuffled", False)
    if reshuffled and result.get("reshuffled_board"):
        new_board = result["reshuffled_board"]

    data = {
        "valid": True,
        "new_board": new_board,
        "cascade_steps": cascade_steps,
        "applied_modifiers": applied_modifiers,
        "obstacles_remaining": result["obstacles_remaining"],
        "moves_remaining": result["moves_remaining"],
        "status": result["status"],
        "obstacle_events": result["obstacle_events"],
        "score_gained": result["score_gained"],
        "reshuffled": reshuffled,
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/attempts/{attempt_id}/abandon")
async def abandon_attempt(
    attempt_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: Any = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Abandon an active campaign attempt."""
    campaign_service = request.app.state.campaign_service
    attempt = await campaign_service.abandon_attempt(
        attempt_id=UUID(attempt_id),
        player_id=UUID(str(player_id)),
    )

    data = {
        "attempt_id": str(attempt.id),
        "status": attempt.status,
    }
    return response.success(data=data, correlation_id=correlation_id)
