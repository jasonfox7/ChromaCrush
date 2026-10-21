"""Economy service protocol.

Defines the public interface for the economy module. All methods are
``async def`` because they involve database operations.

Other modules and the presentation layer depend on this protocol
interface; the concrete ``EconomyService`` implementation lives in
``src.modules.economy.service``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from src.core.types.game import PlayerId

if TYPE_CHECKING:
    from src.modules.economy.dto import (
        BuyResult,
        GoldInfo,
        MarketplaceItem,
        SellResult,
    )


class EconomyServiceProtocol(Protocol):
    """Public interface for the economy module."""

    async def get_gold(self, player_id: PlayerId) -> GoldInfo:
        """Get player's current gold balance.

        Creates a zero-balance record if one doesn't exist.

        Args:
            player_id: The player to query.

        Returns:
            GoldInfo with current balance and lifetime stats.
        """
        ...

    async def sell_equipped_cards(self, player_id: PlayerId) -> SellResult:
        """Sell all 3 equipped cards for gold.

        Requires all 3 equip slots to be filled. Any rarity mix is allowed.
        Each card earns 40% of its base_value in gold.

        Args:
            player_id: The player selling cards.

        Returns:
            SellResult with gold earned and new balance.

        Raises:
            VALIDATION_SLOTS_NOT_FULL: If fewer than 3 cards equipped.
        """
        ...

    async def buy_item(self, player_id: PlayerId, item_id: str) -> BuyResult:
        """Buy an item from the marketplace.

        Debits gold and grants the purchased item (mega gems or cards).

        Args:
            player_id: The player buying.
            item_id: Marketplace item identifier.

        Returns:
            BuyResult with purchase details and new balance.

        Raises:
            NOT_FOUND_MARKETPLACE_ITEM: If item_id is invalid.
            INSUFFICIENT_GOLD: If balance < price.
        """
        ...

    async def get_marketplace(self) -> list[MarketplaceItem]:
        """List all available marketplace items with prices.

        Returns:
            List of MarketplaceItem DTOs.
        """
        ...
