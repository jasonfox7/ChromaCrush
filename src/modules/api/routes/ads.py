"""Ads API routes.

Six endpoints for ad management:

- ``GET  /api/v1/ads/status`` -- Get ad-free status (JWT or API Key).
- ``POST /api/v1/ads/interstitial/request`` -- Request interstitial (JWT only).
- ``POST /api/v1/ads/interstitial/complete`` -- Complete interstitial (JWT only).
- ``POST /api/v1/ads/rewarded/request`` -- Request rewarded video (JWT only).
- ``POST /api/v1/ads/rewarded/complete`` -- Complete rewarded video (JWT only).
- ``GET  /api/v1/ads/bot/attributions`` -- Get bot ad attributions (API Key only).

Interstitial and rewarded endpoints are restricted to JWT-authenticated
human players (bots do not see ads). The bot attributions endpoint is
restricted to API-key-authenticated bot players.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query, Request

from src.modules.api.dependencies import (
    get_auth_type,
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)
from src.modules.api.schemas.ads import (
    AdFreeStatusResponse,
    BotAttributionResponse,
    DailyBreakdownItem,
    InterstitialCompleteRequest,
    InterstitialCompleteResponse,
    InterstitialRequest,
    InterstitialResponse,
    RewardedVideoCompleteRequest,
    RewardedVideoCompleteResponse,
    RewardedVideoRequestSchema,
    RewardedVideoResponse,
)

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter

router = APIRouter(prefix="/api/v1/ads", tags=["ads"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_jwt(request: Request) -> None:
    """Verify the request is authenticated via JWT (human players only).

    Args:
        request: The current HTTP request.

    Raises:
        AppError: FORBIDDEN if auth type is not JWT.
    """
    auth_type = get_auth_type(request)
    if auth_type != "jwt":
        errors = request.app.state.errors
        raise errors.forbidden(
            "This endpoint is for human players only",
            code="FORBIDDEN_BOT_NOT_ALLOWED",
        )


def _require_api_key(request: Request) -> None:
    """Verify the request is authenticated via API key (bot players only).

    Args:
        request: The current HTTP request.

    Raises:
        AppError: FORBIDDEN if auth type is not API key.
    """
    auth_type = get_auth_type(request)
    if auth_type != "api_key":
        errors = request.app.state.errors
        raise errors.forbidden(
            "This endpoint is for bot players only",
            code="FORBIDDEN_NOT_BOT",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status")
async def get_ad_free_status(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the ad-free status for the authenticated player.

    Available to both JWT and API key authenticated requests.

    Returns:
        Standard API envelope with AdFreeStatusResponse data.
    """
    player_id = get_current_player_id(request)
    svc = request.app.state.ad_service

    result = await svc.check_ad_free_status(player_id)

    data = AdFreeStatusResponse(
        is_ad_free=result.is_ad_free,
        reason=result.reason.value if result.reason is not None else None,
        expires_at=(
            result.expires_at.isoformat() if result.expires_at is not None else None
        ),
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.post("/interstitial/request")
async def request_interstitial(
    request: Request,
    body: InterstitialRequest,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Request an interstitial ad for the authenticated human player.

    JWT-only endpoint. Bots do not see ads.

    Args:
        body: Interstitial request with trigger and optional match_id.

    Returns:
        Standard API envelope with InterstitialResponse data.
    """
    _require_jwt(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.ad_service

    result = await svc.request_interstitial(
        player_id=player_id,
        trigger=body.trigger,
        match_id=body.match_id,
    )

    data = InterstitialResponse(
        ad_request_id=str(result.ad_request_id),
        should_show=result.should_show,
        ad_unit_id=result.ad_unit_id,
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.post("/interstitial/complete")
async def complete_interstitial(
    request: Request,
    body: InterstitialCompleteRequest,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Record completion of an interstitial ad impression.

    JWT-only endpoint.

    Args:
        body: Completion data with ad_request_id, viewed flag, and duration.

    Returns:
        Standard API envelope with InterstitialCompleteResponse data.
    """
    _require_jwt(request)
    svc = request.app.state.ad_service

    result = await svc.record_interstitial_impression(
        ad_request_id=body.ad_request_id,
        viewed=body.viewed,
        duration_ms=body.duration_ms,
    )

    data = InterstitialCompleteResponse(
        impression_id=str(result.id),
        viewed=result.viewed,
        duration_ms=result.view_duration_ms,
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.post("/rewarded/request")
async def request_rewarded_video(
    request: Request,
    body: RewardedVideoRequestSchema,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Request a rewarded video ad for the authenticated human player.

    JWT-only endpoint. Bots do not see ads.

    Args:
        body: Rewarded video request with reward_type.

    Returns:
        Standard API envelope with RewardedVideoResponse data.
    """
    _require_jwt(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.ad_service

    result = await svc.request_rewarded_video(
        player_id=player_id,
        reward_type=body.reward_type,
    )

    data = RewardedVideoResponse(
        ad_request_id=str(result.ad_request_id),
        ad_unit_id=result.ad_unit_id,
        reward_preview=(
            {
                "reward_type": result.reward_type.value,
                "reward_value": result.reward_value,
            }
            if result.reward_type is not None
            else None
        ),
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.post("/rewarded/complete")
async def complete_rewarded_video(
    request: Request,
    body: RewardedVideoCompleteRequest,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Record completion of a rewarded video ad.

    JWT-only endpoint.

    Args:
        body: Completion data with ad_request_id, completed flag,
            and watched_duration_ms.

    Returns:
        Standard API envelope with RewardedVideoCompleteResponse data.
    """
    _require_jwt(request)
    svc = request.app.state.ad_service

    result = await svc.complete_rewarded_video(
        ad_request_id=body.ad_request_id,
        completed=body.completed,
        watched_duration_ms=body.watched_duration_ms,
    )

    data = RewardedVideoCompleteResponse(
        reward_granted=result.reward_granted,
        reward_type=(
            result.reward_type.value if result.reward_type is not None else None
        ),
        reward_amount=result.reward_value,
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.get("/bot/attributions")
async def get_bot_attributions(
    request: Request,
    start_date: str = Query(
        ...,
        description="Start date (ISO 8601, e.g. 2026-01-01).",
    ),
    end_date: str = Query(
        ...,
        description="End date (ISO 8601, e.g. 2026-01-31).",
    ),
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get ad attribution report for the authenticated bot player.

    API-key-only endpoint.

    Args:
        start_date: Start date for the report (ISO 8601 date string).
        end_date: End date for the report (ISO 8601 date string).

    Returns:
        Standard API envelope with BotAttributionResponse data.
    """
    _require_api_key(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.ad_service

    parsed_start = date.fromisoformat(start_date)
    parsed_end = date.fromisoformat(end_date)

    result = await svc.get_bot_ad_attributions(
        bot_player_id=player_id,
        start_date=parsed_start,
        end_date=parsed_end,
    )

    daily_items = [
        DailyBreakdownItem(
            date=str(day.date),
            matches=day.matches,
            impressions=day.impressions,
            estimated_revenue_cents=day.estimated_revenue_cents,
            attributed_cents=day.attributed_cents,
        )
        for day in result.daily_breakdown
    ]

    data = BotAttributionResponse(
        bot_player_id=str(result.bot_player_id),
        start_date=str(result.start_date),
        end_date=str(result.end_date),
        total_impressions=result.total_attributed_impressions,
        total_revenue_cents=result.attributed_revenue_cents,
        daily_breakdown=daily_items,
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )
