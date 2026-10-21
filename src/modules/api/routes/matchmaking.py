"""Matchmaking endpoints.

Queue management for the matchmaking system. Players join a pool
(human, bot, or mixed) and are paired based on ELO rating proximity.

All endpoints require JWT or API key authentication.

Five endpoints:

- ``POST   /api/v1/matchmaking/queue``        -- join matchmaking queue
- ``DELETE /api/v1/matchmaking/queue``         -- leave matchmaking queue
- ``GET    /api/v1/matchmaking/queue/status``  -- get queue position
- ``GET    /api/v1/matchmaking/pools``         -- get pool sizes (bot hint)
- ``POST   /api/v1/matchmaking/quick-match``   -- instant bot match (single-player)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.core.types.game import PlayerId
from src.modules.api.dependencies import (
    get_auth_type,
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)
from src.modules.api.schemas.matchmaking import (
    JoinQueueRequest,
    PoolStatsResponse,
    QueueEntryResponse,
    QueueStatusResponse,
    QuickMatchRequest,
)
from src.core.types.player import PlayerType
from src.modules.matchmaking.types import PoolType

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter
    from src.modules.auth.protocols import AuthServiceProtocol

router = APIRouter(prefix="/api/v1/matchmaking", tags=["matchmaking"])


# -- Endpoints ----------------------------------------------------------------


@router.post("/queue")
async def join_queue(
    body: JoinQueueRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Join the matchmaking queue.

    Places the player in the specified pool and returns their queue
    entry with position and estimated wait time.

    Args:
        body: Queue join parameters (pool_type).
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Queue entry details.
    """
    matchmaking_service = request.app.state.matchmaking_service

    # Convert string pool_type to enum
    pool_type = PoolType(body.pool_type)

    queue_entry = await matchmaking_service.join_queue(
        player_id=PlayerId(UUID(str(player_id))),
        pool_type=pool_type,
    )

    data = QueueEntryResponse(
        player_id=str(queue_entry.player_id),
        pool_type=queue_entry.pool_type.value,
        elo_rating=queue_entry.elo_rating,
        position=queue_entry.position_in_queue,
        estimated_wait_seconds=queue_entry.estimated_wait_seconds,
        joined_at=queue_entry.joined_at.isoformat(),
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.delete("/queue")
async def leave_queue(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Leave the matchmaking queue.

    Removes the player from whichever pool they are currently in.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Success status indicating whether the player was in the queue.
    """
    matchmaking_service = request.app.state.matchmaking_service

    was_in_queue = await matchmaking_service.leave_queue(
        player_id=PlayerId(UUID(str(player_id))),
    )

    return response.success(
        data={"removed": was_in_queue},
        correlation_id=correlation_id,
    )


@router.get("/queue/status")
async def get_queue_status(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Get the current queue status for the authenticated player.

    Returns queue position and estimated wait time, or indicates
    the player is not in the queue.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Queue status details.
    """
    matchmaking_service = request.app.state.matchmaking_service

    status = await matchmaking_service.get_queue_status(
        player_id=PlayerId(UUID(str(player_id))),
    )

    if status is None:
        data = QueueStatusResponse(
            in_queue=False,
        ).model_dump(mode="json")
    else:
        data = QueueStatusResponse(
            in_queue=True,
            position=status.position_in_queue,
            pool_type=status.pool_type.value,
            estimated_wait_seconds=status.estimated_wait_seconds,
            joined_at=status.joined_at.isoformat(),
        ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.get("/pools")
async def get_pool_stats(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    auth_type: str = Depends(get_auth_type),
) -> dict[str, Any]:
    """Get matchmaking pool statistics.

    Useful as a bot hint to decide which pool to join.
    Returns player counts and average wait times per pool.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        auth_type: Authentication type (jwt or api_key).

    Returns:
        List of pool statistics.
    """
    matchmaking_service = request.app.state.matchmaking_service

    pools: list[dict[str, Any]] = []
    for pool_type in PoolType:
        stats = await matchmaking_service.get_queue_stats(pool_type=pool_type)

        avg_wait = (
            int(stats.average_wait_seconds) if stats.average_wait_seconds else None
        )
        pools.append(
            PoolStatsResponse(
                pool_type=pool_type.value,
                player_count=stats.total_players,
                average_wait_seconds=avg_wait,
            ).model_dump(mode="json"),
        )

    return response.success(data={"pools": pools}, correlation_id=correlation_id)


@router.post("/quick-match")
async def quick_match(
    request: Request,
    body: QuickMatchRequest | None = None,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Create an instant single-player match against a bot.

    Bypasses the matchmaking queue. If ``bot_player_id`` is provided,
    uses that pre-existing bot; otherwise picks a random bot from the
    pool (or creates an ephemeral one as fallback). Returns match state
    with board ready to play, including a per-match bot JWT token.

    Args:
        request: The current HTTP request.
        body: Optional request body with bot_player_id.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Match state with match_id, player info, board data, and bot_token.
    """
    player_service = request.app.state.player_service
    match_service = request.app.state.match_service

    if body and body.bot_player_id:
        # Use a specific pre-existing bot.
        bot_id = PlayerId(UUID(body.bot_player_id))
    else:
        # Pick a random bot from the pool (skip bots in active matches).
        bot_id = await _pick_random_bot(player_service, match_service)
        if bot_id is None:
            # Fallback: create an ephemeral bot.
            import time

            bot_username = f"bot_{int(time.time() * 1000) % 1_000_000_000}"
            bot_player = await player_service.create_player(
                username=bot_username,
                player_type=PlayerType.BOT,
            )
            bot_id = bot_player.id

    # Ensure bot has a card loadout.
    card_service = getattr(request.app.state, "card_service", None)
    if card_service is not None:
        try:
            await card_service.ensure_bot_loadout(bot_id)
        except Exception:
            pass  # Non-critical — match proceeds without bot cards.

    # Create a match directly (no queue).
    match_state = await match_service.create_match(
        player1_id=PlayerId(UUID(str(player_id))),
        player2_id=bot_id,
    )

    # Generate a per-match JWT token for the bot.
    bot_token = None
    auth_service: AuthServiceProtocol | None = getattr(
        request.app.state,
        "auth_service",
        None,
    )
    if auth_service is not None:
        try:
            bot_token = await auth_service.create_bot_match_token(
                bot_player_id=bot_id,
                match_id=str(match_state.match_id),
            )
        except Exception:
            pass  # Non-critical — frontend can still play without bot token.

    # Return match state in the same shape as GET /matches/{id}.
    p1 = match_state.player1
    p2 = match_state.player2

    if str(p1.player_id) == player_id:
        my_state, opp_state = p1, p2
    else:
        my_state, opp_state = p2, p1

    data = {
        "match_id": str(match_state.match_id),
        "status": match_state.status.value,
        "match_type": match_state.match_type.value,
        "player1": {
            "player_id": str(p1.player_id),
            "username": p1.player_username,
            "is_bot": p1.is_bot,
            "score": p1.score,
            "moves_made": p1.moves_made,
            "moves_remaining": p1.moves_remaining,
        },
        "player2": {
            "player_id": str(p2.player_id),
            "username": p2.player_username,
            "is_bot": p2.is_bot,
            "score": p2.score,
            "moves_made": p2.moves_made,
            "moves_remaining": p2.moves_remaining,
        },
        "is_my_turn": my_state.moves_remaining > 0,
        "my_score": my_state.score,
        "opponent_score": opp_state.score,
        "turns_remaining": my_state.moves_remaining,
        "bot_token": bot_token,
        "bot_player_id": str(bot_id),
        "opponent_is_bot": opp_state.is_bot,
    }

    return response.success(data=data, correlation_id=correlation_id)


async def _pick_random_bot(
    player_service: object,
    match_service: object,
) -> PlayerId | None:
    """Pick a random bot not currently in an active match."""
    import random

    try:
        result = await player_service.list_players(  # type: ignore[attr-defined]
            player_type=PlayerType.BOT,
            limit=100,
            offset=0,
        )
        bots = list(result.items) if hasattr(result, "items") else []
        if not bots:
            return None
        random.shuffle(bots)
        for bot in bots:
            active = await match_service.get_active_matches(bot.id)  # type: ignore[attr-defined]
            if not active:
                return bot.id
    except Exception:
        pass
    return None
