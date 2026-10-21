"""Economy endpoints.

Provides gold balance queries, card selling, marketplace browsing,
and marketplace purchasing. All endpoints require JWT or API key
authentication.

Four endpoints:

- ``GET  /api/v1/economy/gold``        -- current gold balance
- ``POST /api/v1/economy/sell-cards``   -- sell 3 equipped cards for gold
- ``GET  /api/v1/economy/marketplace``  -- list marketplace items
- ``POST /api/v1/economy/buy``          -- buy a marketplace item
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
from src.modules.api.schemas.economy import (
    BuyRequest,
    BuyResponse,
    GoldResponse,
    MarketplaceItemResponse,
    MarketplaceResponse,
    SellResponse,
)

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter
    from src.modules.match.types import MatchState

router = APIRouter(prefix="/api/v1/economy", tags=["economy"])


# -- Endpoints ----------------------------------------------------------------


@router.get("/gold")
async def get_gold(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Get the current gold balance for the authenticated player.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Current gold balance and lifetime stats.
    """
    economy_service = request.app.state.economy_service
    gold_info = await economy_service.get_gold(PlayerId(UUID(str(player_id))))

    data = GoldResponse(
        balance=gold_info.balance,
        lifetime_earned=gold_info.lifetime_earned,
        lifetime_spent=gold_info.lifetime_spent,
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.post("/sell-cards")
async def sell_cards(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Sell all 3 equipped cards for gold.

    Cards are removed and gold is credited at 40% of each card's
    base_value.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Gold earned, cards sold, and new balance.
    """
    # Block card sales during active matches.
    match_service = request.app.state.match_service
    active: list[MatchState] = await match_service.get_active_matches(
        PlayerId(UUID(str(player_id)))
    )
    if active:
        errors = request.app.state.errors
        raise errors.conflict(
            "Cannot modify card loadout while a match is active",
            code="CONFLICT_ACTIVE_MATCH",
        )

    economy_service = request.app.state.economy_service
    sell_result = await economy_service.sell_equipped_cards(
        PlayerId(UUID(str(player_id)))
    )

    data = SellResponse(
        gold_earned=sell_result.gold_earned,
        cards_sold=sell_result.cards_sold,
        card_values=sell_result.card_values,
        new_balance=sell_result.new_balance,
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.get("/marketplace")
async def get_marketplace(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """List all available marketplace items with prices.

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        List of marketplace items grouped by category.
    """
    economy_service = request.app.state.economy_service
    items = await economy_service.get_marketplace()

    data = MarketplaceResponse(
        items=[
            MarketplaceItemResponse(
                item_id=item.item_id,
                name=item.name,
                description=item.description,
                category=item.category,
                price=item.price,
                quantity=item.quantity,
                item_type=item.item_type,
                item_params=item.item_params,
            )
            for item in items
        ],
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.post("/buy")
async def buy_item(
    body: BuyRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Buy an item from the marketplace.

    Debits gold and grants the purchased item (mega gems or cards).

    Args:
        body: BuyRequest with item_id.
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        player_id: Authenticated player ID.

    Returns:
        Purchase confirmation with new gold balance.
    """
    economy_service = request.app.state.economy_service
    buy_result = await economy_service.buy_item(
        PlayerId(UUID(str(player_id))),
        body.item_id,
    )

    data = BuyResponse(
        item_id=buy_result.item_id,
        item_name=buy_result.item_name,
        gold_spent=buy_result.gold_spent,
        new_balance=buy_result.new_balance,
        quantity_granted=buy_result.quantity_granted,
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)
