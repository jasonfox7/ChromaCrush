"""Internal helper functions for the matchmaking service.

Extracted from ``MatchmakingService`` to reduce class size. All functions
take explicit parameters instead of ``self`` — the service passes its
dependencies when calling them.

This module is internal (leading underscore) and should not be imported
outside ``src.modules.matchmaking``.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.modules.matchmaking.types import (
    MatchmakingResult,
    MatchmakingStatus,
    PoolType,
    QueueEntryData,
)

if TYPE_CHECKING:
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.matchmaking.protocols import (
        MatchServiceProtocol,
        MatchmakingQueueRepositoryProtocol,
    )

_BASE_WAIT_ESTIMATE_SECONDS = 30
_WAIT_REDUCTION_FACTOR = 5
_MIN_WAIT_ESTIMATE_SECONDS = 5


async def maybe_expand_elo_range(
    player_id: PlayerId,
    queue_state: QueueEntryData,
    *,
    min_wait_before_expansion: int,
    elo_range_expansion_interval_seconds: int,
    max_elo_range: int,
    elo_range_expansion: int,
    queue_repo: MatchmakingQueueRepositoryProtocol,
    logger: LoggerProtocol,
) -> None:
    """Expand ELO search range based on wait time."""
    now = datetime.now(timezone.utc)
    wait_seconds = (now - queue_state.joined_at).total_seconds()

    if wait_seconds < min_wait_before_expansion:
        return

    time_since_expansion = (now - queue_state.last_expansion_at).total_seconds()

    if time_since_expansion < elo_range_expansion_interval_seconds:
        return

    current_range = queue_state.current_max_elo - queue_state.elo_rating

    if current_range >= max_elo_range:
        return

    new_range = min(
        current_range + elo_range_expansion,
        max_elo_range,
    )

    new_min_elo = max(0, queue_state.elo_rating - new_range)
    new_max_elo = queue_state.elo_rating + new_range

    await queue_repo.update_elo_range(player_id, new_min_elo, new_max_elo)

    logger.debug(
        "ELO range expanded",
        player_id=str(player_id),
        old_range=(queue_state.current_min_elo, queue_state.current_max_elo),
        new_range=(new_min_elo, new_max_elo),
    )


async def try_create_match(
    player_id: PlayerId,
    player_elo: int,
    opponent_id: PlayerId,
    opponent_elo: int,
    pool_type: PoolType,
    wait_seconds: float,
    *,
    initial_elo_range: int,
    queue_repo: MatchmakingQueueRepositoryProtocol,
    match_service: MatchServiceProtocol,
    logger: LoggerProtocol,
    errors: ErrorServiceProtocol,
) -> MatchmakingResult | None:
    """Attempt to create a match with the opponent.

    Returns None if the opponent was already taken.
    """
    # 1. Atomically remove both from queue
    removed = await queue_repo.atomic_remove_pair(player_id, opponent_id)
    if not removed:
        logger.debug(
            "Opponent already taken",
            player_id=str(player_id),
            opponent_id=str(opponent_id),
        )
        return None

    # 2. Create match
    try:
        match_state = await match_service.create_match(
            player1_id=player_id,
            player2_id=opponent_id,
        )

        elo_diff = abs(player_elo - opponent_elo)

        logger.info(
            "Match found",
            player1_id=str(player_id),
            player2_id=str(opponent_id),
            match_id=str(match_state.match_id),
            elo_difference=elo_diff,
            wait_time_seconds=int(wait_seconds),
        )

        return MatchmakingResult(
            status=MatchmakingStatus.MATCHED,
            player_id=player_id,
            opponent_id=opponent_id,
            match_id=match_state.match_id,
            wait_time_seconds=int(wait_seconds),
            elo_difference=elo_diff,
            pool_type=pool_type,
            message="Match found!",
        )

    except AppError as e:
        # Compensate: re-add both to queues
        logger.error(
            "Match creation failed, compensating",
            player_id=str(player_id),
            opponent_id=str(opponent_id),
            error=str(e),
        )

        # Re-add to queues (best effort)
        try:
            await re_add_to_queue(
                player_id,
                player_elo,
                pool_type,
                initial_elo_range=initial_elo_range,
                queue_repo=queue_repo,
            )
            await re_add_to_queue(
                opponent_id,
                opponent_elo,
                pool_type,
                initial_elo_range=initial_elo_range,
                queue_repo=queue_repo,
            )
        except Exception:
            pass  # Best effort compensation

        raise errors.internal(
            "Match creation failed",
            code="INTERNAL_MATCHMAKING_ERROR",
            player_id=str(player_id),
            opponent_id=str(opponent_id),
            original_error=str(e),
        )


async def re_add_to_queue(
    player_id: PlayerId,
    elo_rating: int,
    pool_type: PoolType,
    *,
    initial_elo_range: int,
    queue_repo: MatchmakingQueueRepositoryProtocol,
) -> None:
    """Re-add a player to the queue after a failed match creation."""
    await queue_repo.add_to_queue(
        player_id=player_id,
        elo_rating=elo_rating,
        pool_type=pool_type,
        initial_elo_range=initial_elo_range,
    )


async def calculate_queue_position(
    player_id: PlayerId,
    pool_type: PoolType,
    *,
    queue_repo: MatchmakingQueueRepositoryProtocol,
) -> int:
    """Calculate a player's position in the queue (1-indexed)."""
    all_players = await queue_repo.get_all_queued_players(pool_type)

    for idx, entry in enumerate(all_players):
        if entry.player_id == player_id:
            return idx + 1

    return len(all_players) + 1


async def estimate_wait_time(
    elo_rating: int,
    pool_type: PoolType,
    *,
    queue_repo: MatchmakingQueueRepositoryProtocol,
) -> int | None:
    """Estimate wait time in seconds based on queue density.

    Returns None if estimation is not possible (empty queue).
    """
    count = await queue_repo.get_queue_count(pool_type)
    if count <= 1:
        return None

    base_wait = _BASE_WAIT_ESTIMATE_SECONDS
    reduction = math.sqrt(count - 1) * _WAIT_REDUCTION_FACTOR
    estimated = max(_MIN_WAIT_ESTIMATE_SECONDS, int(base_wait - reduction))

    return estimated
