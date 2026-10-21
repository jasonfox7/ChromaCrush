"""Bot earnings API routes.

Five endpoints for bot earnings management:

- ``GET  /api/v1/bot-earnings/balance`` -- Get earnings balance (API Key only).
- ``POST /api/v1/bot-earnings/sync`` -- Sync attributions (API Key only).
- ``POST /api/v1/bot-earnings/payout/request`` -- Request payout (API Key only).
- ``GET  /api/v1/bot-earnings/payout/history`` -- Get payout history (API Key only).
- ``GET  /api/v1/bot-earnings/attributions`` -- Get attribution details (API Key only).

All bot earnings endpoints are restricted to API-key-authenticated bot players.
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
from src.modules.api.schemas.bot_earnings import (
    AttributionEntryResponse,
    AttributionListResponse,
    EarningsBalanceResponse,
    PayoutHistoryResponse,
    PayoutRequestResponse,
    SyncResultResponse,
)

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter

router = APIRouter(prefix="/api/v1/bot-earnings", tags=["bot-earnings"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


@router.get("/balance")
async def get_earnings_balance(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the current earnings balance for the authenticated bot.

    API-key-only endpoint.

    Returns:
        Standard API envelope with EarningsBalanceResponse data.
    """
    _require_api_key(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.bot_earnings_service

    result = await svc.get_earnings_balance(bot_player_id=player_id)

    data = EarningsBalanceResponse(
        bot_player_id=str(result.bot_player_id),
        total_earned_cents=result.total_earned_cents,
        pending_payout_cents=result.pending_payout_cents,
        available_cents=result.available_balance_cents,
        paid_out_cents=result.total_paid_out_cents,
        last_sync_at=(
            result.last_sync_at.isoformat() if result.last_sync_at is not None else None
        ),
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.post("/sync")
async def sync_attributions(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Sync attribution entries from the ads module for the authenticated bot.

    Processes recent ad impressions and creates attribution entries,
    updating the bot's earnings balance.

    API-key-only endpoint.

    Returns:
        Standard API envelope with SyncResultResponse data.
    """
    _require_api_key(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.bot_earnings_service

    result = await svc.sync_attributions(bot_player_id=player_id)

    data = SyncResultResponse(
        new_attributions=result.new_attributions,
        new_earnings_cents=result.new_earnings_cents,
        sync_date=result.sync_end.isoformat(),
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.post("/payout/request")
async def request_payout(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Request a payout of available earnings for the authenticated bot.

    The requesting player (bot) is both the bot and the requester.
    Validation checks include minimum balance threshold and no
    existing pending payout.

    API-key-only endpoint.

    Returns:
        Standard API envelope with PayoutRequestResponse data.
    """
    _require_api_key(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.bot_earnings_service

    result = await svc.request_payout(
        bot_player_id=player_id,
        requesting_owner_id=player_id,
    )

    data = PayoutRequestResponse(
        payout_request_id=str(result.id),
        bot_player_id=str(result.bot_player_id),
        amount_cents=result.amount_cents,
        status=result.status.value,
        requested_at=result.requested_at.isoformat(),
        processed_at=(
            result.processed_at.isoformat() if result.processed_at is not None else None
        ),
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.get("/payout/history")
async def get_payout_history(
    request: Request,
    status: str | None = Query(
        default=None,
        description=(
            "Filter by payout status. "
            "One of: pending, processing, completed, rejected, cancelled."
        ),
    ),
    limit: int = Query(default=50, ge=1, le=100, description="Page size."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get payout request history for the authenticated bot.

    Supports filtering by status and pagination.

    API-key-only endpoint.

    Args:
        status: Optional status filter.
        limit: Maximum entries per page (1-100, default 50).
        offset: Pagination offset (default 0).

    Returns:
        Standard API envelope with PayoutHistoryResponse data.
    """
    _require_api_key(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.bot_earnings_service

    # Convert string status to enum if provided
    payout_status = None
    if status is not None:
        from src.modules.bot_earnings.types import PayoutStatus

        payout_status = PayoutStatus(status)

    result = await svc.get_payout_requests(
        bot_player_id=player_id,
        status=payout_status,
        limit=limit,
        offset=offset,
    )

    entries = [
        PayoutRequestResponse(
            payout_request_id=str(pr.id),
            bot_player_id=str(pr.bot_player_id),
            amount_cents=pr.amount_cents,
            status=pr.status.value,
            requested_at=pr.requested_at.isoformat(),
            processed_at=(
                pr.processed_at.isoformat() if pr.processed_at is not None else None
            ),
        )
        for pr in result.items
    ]

    data = PayoutHistoryResponse(
        entries=entries,
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.get("/attributions")
async def get_attribution_entries(
    request: Request,
    start_date: str | None = Query(
        default=None,
        description="Start date filter (ISO 8601, e.g. 2026-01-01).",
    ),
    end_date: str | None = Query(
        default=None,
        description="End date filter (ISO 8601, e.g. 2026-01-31).",
    ),
    limit: int = Query(default=50, ge=1, le=100, description="Page size."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get attribution entry details for the authenticated bot.

    Returns individual attribution records showing ad impressions
    attributed to the bot and the revenue share earned.

    Supports optional date range filtering and pagination.

    API-key-only endpoint.

    Args:
        start_date: Optional start date filter (ISO 8601 date).
        end_date: Optional end date filter (ISO 8601 date).
        limit: Maximum entries per page (1-100, default 50).
        offset: Pagination offset (default 0).

    Returns:
        Standard API envelope with AttributionListResponse data.
    """
    _require_api_key(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.bot_earnings_service

    parsed_start = date.fromisoformat(start_date) if start_date is not None else None
    parsed_end = date.fromisoformat(end_date) if end_date is not None else None

    result = await svc.get_attribution_entries(
        bot_player_id=player_id,
        start_date=parsed_start,
        end_date=parsed_end,
        limit=limit,
        offset=offset,
    )

    entries = [
        AttributionEntryResponse(
            attribution_id=str(entry.id),
            ad_impression_id=str(entry.ad_impression_id),
            human_player_id=str(entry.opponent_player_id),
            bot_player_id=str(entry.bot_player_id),
            revenue_share_cents=entry.attributed_cents,
            attributed_at=entry.recorded_at.isoformat(),
        )
        for entry in result.items
    ]

    data = AttributionListResponse(
        entries=entries,
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )
