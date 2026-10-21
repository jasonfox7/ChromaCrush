"""Data Transfer Objects for the economy module.

Defines gold balance info, sell results, buy results, and marketplace
items. No database awareness -- pure data carriers.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GoldInfo:
    """Current gold balance state."""

    player_id: str
    balance: int
    lifetime_earned: int
    lifetime_spent: int


@dataclass(frozen=True)
class SellResult:
    """Result of selling equipped cards for gold."""

    gold_earned: int
    cards_sold: int
    card_values: list[int]  # gold value of each sold card
    new_balance: int


@dataclass(frozen=True)
class MarketplaceItem:
    """A purchasable item in the marketplace."""

    item_id: str
    name: str
    description: str
    category: str  # "arsenal" or "forge_supply"
    price: int  # gold cost
    quantity: int  # how many you get
    item_type: str  # "mega_gem" or "card_pack"
    item_params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class BuyResult:
    """Result of buying an item from the marketplace."""

    item_id: str
    item_name: str
    gold_spent: int
    new_balance: int
    quantity_granted: int
