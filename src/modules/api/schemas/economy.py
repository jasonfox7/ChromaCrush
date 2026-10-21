"""Economy request and response schemas.

Pydantic v2 models for the ``/api/v1/economy`` endpoint group.
All response schemas are frozen (immutable).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GoldResponse(BaseModel):
    """Current gold balance response."""

    model_config = ConfigDict(frozen=True)

    balance: int
    lifetime_earned: int
    lifetime_spent: int


class SellResponse(BaseModel):
    """Result of selling equipped cards for gold."""

    model_config = ConfigDict(frozen=True)

    gold_earned: int
    cards_sold: int
    card_values: list[int]
    new_balance: int


class BuyRequest(BaseModel):
    """Request to buy a marketplace item."""

    model_config = ConfigDict(frozen=True)

    item_id: str


class BuyResponse(BaseModel):
    """Result of buying a marketplace item."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    item_name: str
    gold_spent: int
    new_balance: int
    quantity_granted: int


class MarketplaceItemResponse(BaseModel):
    """A single marketplace item."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    name: str
    description: str
    category: str
    price: int
    quantity: int
    item_type: str
    item_params: dict


class MarketplaceResponse(BaseModel):
    """Full marketplace listing."""

    model_config = ConfigDict(frozen=True)

    items: list[MarketplaceItemResponse]
