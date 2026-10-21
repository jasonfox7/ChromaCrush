"""Economy module for ChromaCrush.

Manages the gold currency system: balance tracking, selling cards
for gold, and buying items from the marketplace.

Exports:
    EconomyService: Concrete service implementation.
    EconomyServiceProtocol: Protocol interface for dependency injection.
    GoldInfo: Gold balance DTO.
    SellResult: Result of selling cards.
    BuyResult: Result of buying an item.
    MarketplaceItem: A purchasable marketplace item.
"""

from src.modules.economy.dto import (
    BuyResult,
    GoldInfo,
    MarketplaceItem,
    SellResult,
)
from src.modules.economy.protocols import EconomyServiceProtocol
from src.modules.economy.service import EconomyService

__all__ = [
    "BuyResult",
    "EconomyService",
    "EconomyServiceProtocol",
    "GoldInfo",
    "MarketplaceItem",
    "SellResult",
]
