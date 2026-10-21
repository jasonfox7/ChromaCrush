"""Energy endpoints.

Provides heart/energy state queries and login streak recording.
All endpoints require JWT or API key authentication.

Three endpoints:

- ``GET  /api/v1/energy``       -- current energy state
- ``POST /api/v1/energy/login`` -- record login for streak
- ``GET  /api/v1/energy/streak`` -- get streak info
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
from src.modules.api.schemas.energy import (
    EnergyResponse,
    LoginStreakResponse,
    StreakResponse,
)

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter

router = APIRouter(prefix="/api/v1/energy", tags=["energy"])


# -- Helper -------------------------------------------------------------------


def _energy_info_to_response(energy_info: Any) -> dict[str, Any]:
    """Convert an EnergyInfo DTO to an EnergyResponse-compatible dict.

    Args:
        energy_info: EnergyInfo dataclass from energy service.

    Returns:
        Dict suitable for EnergyResponse schema.
    """
    next_heart_at = energy_info.next_heart_at
    return {
        "current_hearts": energy_info.current_hearts,
        "max_hearts": energy_info.max_hearts,
        "seconds_to_next_heart": energy_info.seconds_to_next_heart,
        "next_heart_at": next_heart_at.isoformat() if next_heart_at else None,
        "is_full": energy_info.is_full,
        "daily_streak": energy_info.daily_streak,
    }


# -- Endpoints ----------------------------------------------------------------


@router.get("")
async def get_energy(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Get the current energy (hearts) state for the authenticated player.

    Includes real-time regeneration calculations and streak information.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Current energy state.
    """
    energy_service = request.app.state.energy_service
    energy_info = await energy_service.get_energy(PlayerId(UUID(str(player_id))))

    data = EnergyResponse(
        **_energy_info_to_response(energy_info),
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.post("/login")
async def record_login(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Record a login for daily streak tracking.

    Updates the player's streak and grants bonus hearts at
    milestone thresholds (7, 14, 30 day streaks).

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Streak result and updated energy state.
    """
    energy_service = request.app.state.energy_service
    login_result = await energy_service.record_login(
        PlayerId(UUID(str(player_id))),
    )

    data = LoginStreakResponse(
        streak_day=login_result.streak_day,
        streak_continued=login_result.streak_continued,
        streak_broken=login_result.streak_broken,
        bonus_hearts_granted=login_result.bonus_hearts_granted,
        energy=EnergyResponse(
            **_energy_info_to_response(login_result.energy_info),
        ),
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.get("/streak")
async def get_streak(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Get streak information for the authenticated player.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Current streak details and next reward threshold.
    """
    energy_service = request.app.state.energy_service
    streak_info = await energy_service.get_streak(
        PlayerId(UUID(str(player_id))),
    )

    last_login = streak_info.last_login_date
    data = StreakResponse(
        current_streak=streak_info.current_streak,
        last_login_date=last_login.isoformat() if last_login else None,
        next_reward_threshold=streak_info.next_reward_threshold,
        days_until_reward=streak_info.days_until_reward,
        reward_hearts=streak_info.reward_hearts,
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)
