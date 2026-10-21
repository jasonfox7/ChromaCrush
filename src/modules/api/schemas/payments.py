"""Payments request and response schemas.

Pydantic v2 models for the ``/api/v1/payments`` endpoint group.
Request schemas are mutable (accept user input), response schemas
are frozen (immutable output).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# -- Request schemas ----------------------------------------------------------


class InitiatePurchaseRequest(BaseModel):
    """Request body for initiating a purchase."""

    product_id: str = Field(
        ...,
        description="The product ID to purchase (e.g. chromacrush_ad_free).",
    )


class ValidatePurchaseRequest(BaseModel):
    """Request body for validating a purchase receipt."""

    receipt_data: str = Field(
        ...,
        description="Base64-encoded receipt data (Apple) or purchase token (Google).",
    )
    product_id: str = Field(
        ...,
        description="The product ID being purchased.",
    )
    transaction_id: str = Field(
        ...,
        description="Transaction ID from the app store.",
    )
    provider: str = Field(
        ...,
        description="Payment provider: 'apple' or 'google'.",
    )


class RestorePurchasesRequest(BaseModel):
    """Request body for restoring purchases."""

    receipts: list[ValidatePurchaseRequest] = Field(
        ...,
        description="List of purchase receipts to restore.",
    )


# -- Response schemas ---------------------------------------------------------


class PurchaseIntentResponse(BaseModel):
    """Response after initiating a purchase."""

    model_config = ConfigDict(frozen=True)

    intent_id: str
    product_id: str
    status: str
    created_at: str


class PurchaseResultResponse(BaseModel):
    """Response after validating a purchase."""

    model_config = ConfigDict(frozen=True)

    success: bool
    purchase_id: str | None = None
    product_id: str
    message: str


class RestoreResultResponse(BaseModel):
    """Response after restoring purchases."""

    model_config = ConfigDict(frozen=True)

    restored_count: int
    failed_count: int
    results: list[PurchaseResultResponse]


class PurchaseStatusResponse(BaseModel):
    """Current purchase status for a player."""

    model_config = ConfigDict(frozen=True)

    is_ad_free: bool
    active_purchases: list[dict]
    purchase_history_count: int
