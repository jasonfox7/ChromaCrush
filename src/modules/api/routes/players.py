"""Player endpoints.

CRUD operations for player profiles, statistics, and the ELO
leaderboard. All endpoints require JWT or API key authentication.

Seven endpoints:

- ``GET    /api/v1/players/me``                -- current player profile
- ``GET    /api/v1/players/check-username``    -- check username availability
- ``GET    /api/v1/players/{player_id}``       -- player by ID
- ``PATCH  /api/v1/players/me``                -- update current player
- ``DELETE /api/v1/players/me``                -- soft-delete account
- ``GET    /api/v1/players/{player_id}/stats`` -- player statistics
- ``GET    /api/v1/players/leaderboard``       -- ELO leaderboard
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.core.types.game import PlayerId
from src.modules.api.dependencies import (
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)
from src.modules.api.schemas.player import (
    LeaderboardEntry,
    LeaderboardResponse,
    PlayerProfileResponse,
    PlayerStatsResponse,
    PlayerUpdateRequest,
    UsernameCheckResponse,
)
from src.modules.player.dto import PlayerUpdate
from src.modules.player.validation import validate_username

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter

router = APIRouter(prefix="/api/v1/players", tags=["players"])


# -- Helper -------------------------------------------------------------------


def _player_to_profile(player: Any, include_email: bool = False) -> dict[str, Any]:
    """Convert a Player domain object to a PlayerProfileResponse dict.

    Args:
        player: Player domain entity.
        include_email: Whether to include the email field.

    Returns:
        Dict suitable for PlayerProfileResponse schema.
    """
    data: dict[str, Any] = {
        "player_id": str(player.id),
        "username": player.username,
        "player_type": player.player_type.value,
        "elo_rating": player.elo_rating,
        "created_at": player.created_at.isoformat(),
    }
    if include_email:
        data["email"] = getattr(player, "email", None)
    return data


# -- Endpoints ----------------------------------------------------------------


@router.get("/leaderboard")
async def get_leaderboard(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    limit: int = Query(default=50, ge=1, le=100, description="Page size."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    sort_by: str = Query(
        default="elo",
        pattern="^(elo|high_score)$",
        description="Sort by 'elo' or 'high_score'.",
    ),
) -> dict[str, Any]:
    """Get the leaderboard sorted by ELO or highest score.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        limit: Maximum entries to return (1-100).
        offset: Pagination offset.
        sort_by: Sort mode — 'elo' (default) or 'high_score'.

    Returns:
        Leaderboard entries with pagination metadata.
    """
    player_service = request.app.state.player_service

    if sort_by == "high_score":
        paginated = await player_service.get_high_score_leaderboard(
            limit=limit, offset=offset
        )
        entries = [
            LeaderboardEntry(
                rank=offset + idx + 1,
                player_id=str(stats.player_id),
                username=username,
                elo_rating=elo_rating,
                highest_score=stats.highest_score,
            ).model_dump(mode="json")
            for idx, (stats, username, elo_rating) in enumerate(paginated.items)
        ]
    else:
        paginated = await player_service.list_players(
            player_type=None,
            limit=limit,
            offset=offset,
        )
        sorted_players = sorted(
            paginated.items,
            key=lambda p: p.elo_rating,
            reverse=True,
        )
        entries = [
            LeaderboardEntry(
                rank=offset + idx + 1,
                player_id=str(player.id),
                username=player.username,
                elo_rating=player.elo_rating,
            ).model_dump(mode="json")
            for idx, player in enumerate(sorted_players)
        ]

    data = LeaderboardResponse(
        entries=entries,
        total=paginated.total,
        limit=paginated.limit,
        offset=paginated.offset,
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.get("/me")
async def get_current_player(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Get the current authenticated player's profile.

    Includes email when viewing own profile.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Full player profile including email.
    """
    player_service = request.app.state.player_service
    player = await player_service.get_player(PlayerId(UUID(str(player_id))))

    data = PlayerProfileResponse(
        **_player_to_profile(player, include_email=True),
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.get("/check-username")
async def check_username(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
    username: str = Query(..., description="Username to check availability for."),
) -> dict[str, Any]:
    """Check if a username is available and valid.

    Validates the username format and checks uniqueness (case-insensitive).

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.
        username: The username to check.

    Returns:
        Availability and validation result.
    """
    player_service = request.app.state.player_service

    # Read validation config from the player service.
    min_len = player_service._username_min_length
    max_len = player_service._username_max_length
    pattern = player_service._username_pattern

    is_valid, error_msg = validate_username(username, min_len, max_len, pattern)

    if not is_valid:
        data = UsernameCheckResponse(
            available=False,
            valid=False,
            error=error_msg,
        ).model_dump(mode="json")
        return response.success(data=data, correlation_id=correlation_id)

    existing = await player_service.get_player_by_username(username)
    available = existing is None

    data = UsernameCheckResponse(
        available=available,
        valid=True,
        error=None if available else "Username already taken",
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.get("/{target_player_id}")
async def get_player_by_id(
    target_player_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get a player's public profile by ID.

    Does not include email (privacy).

    Args:
        target_player_id: The player ID to look up.
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.

    Returns:
        Public player profile (no email).
    """
    player_service = request.app.state.player_service
    player = await player_service.get_player(PlayerId(UUID(target_player_id)))

    data = PlayerProfileResponse(
        **_player_to_profile(player, include_email=False),
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.patch("/me")
async def update_current_player(
    body: PlayerUpdateRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Update the current player's profile.

    Args:
        body: Fields to update (username, email).
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Updated player profile.
    """
    player_service = request.app.state.player_service

    updates = PlayerUpdate(
        username=body.username,
        email=body.email,
    )

    player = await player_service.update_player(
        player_id=PlayerId(UUID(str(player_id))),
        updates=updates,
    )

    data = PlayerProfileResponse(
        **_player_to_profile(player, include_email=True),
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.delete("/me")
async def delete_current_player(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Soft-delete the current player's account.

    The account is marked as deleted but data is retained. The
    username is released by appending a deletion timestamp suffix.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Success acknowledgement.
    """
    player_service = request.app.state.player_service

    await player_service.soft_delete_player(
        player_id=PlayerId(UUID(str(player_id))),
    )

    return response.success(
        data={"message": "Account deleted"},
        correlation_id=correlation_id,
    )


@router.get("/{target_player_id}/stats")
async def get_player_stats(
    target_player_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get statistics for a player.

    Args:
        target_player_id: The player ID to get stats for.
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.

    Returns:
        Player statistics.
    """
    player_service = request.app.state.player_service
    stats = await player_service.get_stats(PlayerId(UUID(target_player_id)))

    data = PlayerStatsResponse(
        player_id=str(stats.player_id),
        matches_played=stats.total_matches,
        matches_won=stats.wins,
        matches_lost=stats.losses,
        matches_drawn=stats.draws,
        total_score=stats.highest_score,
        highest_score=stats.highest_score,
        longest_chain=stats.longest_chain,
        total_gems_matched=stats.total_gems_matched,
        win_rate=stats.win_rate,
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)
