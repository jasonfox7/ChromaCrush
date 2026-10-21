"""Bot earnings request and response schemas.

Pydantic v2 models for the ``/api/v1/bot-earnings`` endpoint group.
All bot earnings endpoints are API-key only (bot players).
Response schemas are frozen (immutable output).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# -- Request schemas ----------------------------------------------------------


class PayoutRequestSchema(BaseModel):
    """Request body for requesting a payout.

    The ``requesting_owner_id`` is extracted from the authenticated
    player context and does not appear in the request body.
    """


class AttributionQueryParams(BaseModel):
    """Query parameters for attribution entries endpoint."""

    start_date: str | None = Field(
        default=None,
        description="Start date filter (ISO 8601 date, e.g. 2026-01-01).",
    )
    end_date: str | None = Field(
        default=None,
        description="End date filter (ISO 8601 date, e.g. 2026-01-31).",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of entries per page.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset.",
    )


class PayoutHistoryQueryParams(BaseModel):
    """Query parameters for payout history endpoint."""

    status: str | None = Field(
        default=None,
        description=(
            "Filter by payout status. "
            "One of: pending, processing, completed, rejected, cancelled."
        ),
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of entries per page.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset.",
    )


# -- Response schemas ---------------------------------------------------------


class EarningsBalanceResponse(BaseModel):
    """Current earnings balance for a bot."""

    model_config = ConfigDict(frozen=True)

    bot_player_id: str
    total_earned_cents: int
    pending_payout_cents: int
    available_cents: int
    paid_out_cents: int
    last_sync_at: str | None = None


class SyncResultResponse(BaseModel):
    """Result of syncing attributions."""

    model_config = ConfigDict(frozen=True)

    new_attributions: int
    new_earnings_cents: int
    sync_date: str


class PayoutRequestResponse(BaseModel):
    """Payout request details."""

    model_config = ConfigDict(frozen=True)

    payout_request_id: str
    bot_player_id: str
    amount_cents: int
    status: str
    requested_at: str
    processed_at: str | None = None


class PayoutHistoryResponse(BaseModel):
    """Paginated payout history."""

    model_config = ConfigDict(frozen=True)

    entries: list[PayoutRequestResponse]
    total: int
    limit: int
    offset: int


class AttributionEntryResponse(BaseModel):
    """Single attribution entry."""

    model_config = ConfigDict(frozen=True)

    attribution_id: str
    ad_impression_id: str
    human_player_id: str
    bot_player_id: str
    revenue_share_cents: int
    attributed_at: str


class AttributionListResponse(BaseModel):
    """Paginated attribution entries."""

    model_config = ConfigDict(frozen=True)

    entries: list[AttributionEntryResponse]
    total: int
    limit: int
    offset: int
