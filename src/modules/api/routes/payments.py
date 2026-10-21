"""Payments API routes.

Four endpoints for payment management:

- ``POST /api/v1/payments/purchase/initiate`` -- Start ad-free purchase (JWT only).
- ``POST /api/v1/payments/purchase/validate`` -- Validate purchase receipt (JWT only).
- ``POST /api/v1/payments/restore`` -- Restore purchases (JWT only).
- ``GET  /api/v1/payments/status`` -- Get purchase status (JWT only).

All payment endpoints are restricted to JWT-authenticated human players.
Bot players cannot make purchases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request

from src.modules.api.dependencies import (
    get_auth_type,
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)
from src.modules.api.schemas.payments import (
    InitiatePurchaseRequest,
    PurchaseIntentResponse,
    PurchaseResultResponse,
    PurchaseStatusResponse,
    RestorePurchasesRequest,
    RestoreResultResponse,
    ValidatePurchaseRequest,
)

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/purchase/initiate")
async def initiate_purchase(
    request: Request,
    body: InitiatePurchaseRequest,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Initiate a purchase intent for the authenticated human player.

    Creates a purchase intent record that tracks the checkout process.
    The client should then proceed to the platform-specific payment flow
    and call ``/purchase/validate`` upon completion.

    JWT-only endpoint.

    Args:
        body: Purchase initiation request with product_id.

    Returns:
        Standard API envelope with PurchaseIntentResponse data.
    """
    _require_jwt(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.payment_service

    result = await svc.initiate_purchase(
        player_id=player_id,
        product_id=body.product_id,
    )

    data = PurchaseIntentResponse(
        intent_id=str(result.intent_id),
        product_id=str(result.product_id),
        status=result.status.value,
        created_at=result.created_at.isoformat(),
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.post("/purchase/validate")
async def validate_purchase(
    request: Request,
    body: ValidatePurchaseRequest,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Validate a purchase receipt with the payment provider.

    After completing the platform payment flow, the client submits the
    receipt for server-side validation. On success, ad-free status is
    granted to the player.

    JWT-only endpoint.

    Args:
        body: Validation request with receipt_data, product_id,
            transaction_id, and provider.

    Returns:
        Standard API envelope with PurchaseResultResponse data.
    """
    _require_jwt(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.payment_service

    # Import the domain type to construct the receipt
    from src.modules.payments.types import PaymentProvider, PurchaseReceipt

    receipt = PurchaseReceipt(
        provider=PaymentProvider(body.provider),
        receipt_data=body.receipt_data,
        product_id=body.product_id,
        transaction_id=body.transaction_id,
    )

    result = await svc.validate_purchase(
        player_id=player_id,
        receipt=receipt,
    )

    message = (
        "Purchase validated successfully"
        if result.success
        else (result.error_message or "Purchase validation failed")
    )

    data = PurchaseResultResponse(
        success=result.success,
        purchase_id=str(result.purchase_id) if result.purchase_id is not None else None,
        product_id=str(result.product_id),
        message=message,
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.post("/restore")
async def restore_purchases(
    request: Request,
    body: RestorePurchasesRequest,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Restore purchases for the authenticated human player.

    Accepts a list of receipts from the client and validates each one.
    Useful when a player reinstalls the app or switches devices.

    JWT-only endpoint.

    Args:
        body: Restore request with list of purchase receipts.

    Returns:
        Standard API envelope with RestoreResultResponse data.
    """
    _require_jwt(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.payment_service

    from src.modules.payments.types import PaymentProvider, PurchaseReceipt

    receipts = [
        PurchaseReceipt(
            provider=PaymentProvider(r.provider),
            receipt_data=r.receipt_data,
            product_id=r.product_id,
            transaction_id=r.transaction_id,
        )
        for r in body.receipts
    ]

    result = await svc.restore_purchases(
        player_id=player_id,
        receipts=receipts,
    )

    individual_results = [
        PurchaseResultResponse(
            success=pr.status.value == "completed",
            purchase_id=str(pr.id) if pr.id is not None else None,
            product_id=str(pr.product_id),
            message="Restored" if pr.status.value == "completed" else "Failed",
        )
        for pr in result.restored_purchases
    ]

    data = RestoreResultResponse(
        restored_count=result.restored_count,
        failed_count=result.invalid_count,
        results=individual_results,
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )


@router.get("/status")
async def get_purchase_status(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get purchase status for the authenticated human player.

    Returns whether the player has ad-free status, along with details
    about active purchases and history count.

    JWT-only endpoint.

    Returns:
        Standard API envelope with PurchaseStatusResponse data.
    """
    _require_jwt(request)
    player_id = get_current_player_id(request)
    svc = request.app.state.payment_service

    result = await svc.get_purchase_status(player_id=player_id)

    active_purchases = []
    if result.has_purchased_ad_free:
        purchase_info: dict[str, Any] = {
            "product_id": "ad_free",
            "is_active": not result.is_refunded,
        }
        if result.purchase_date is not None:
            purchase_info["purchase_date"] = result.purchase_date.isoformat()
        if result.provider is not None:
            purchase_info["provider"] = result.provider.value
        active_purchases.append(purchase_info)

    # Get purchase history count
    history = await svc.get_purchase_history(player_id=player_id, limit=0, offset=0)
    history_count = history.total

    data = PurchaseStatusResponse(
        is_ad_free=result.has_purchased_ad_free and not result.is_refunded,
        active_purchases=active_purchases,
        purchase_history_count=history_count,
    )

    return response.success(
        data=data.model_dump(mode="json"),
        correlation_id=correlation_id,
    )
