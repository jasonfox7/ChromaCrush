"""Economy service implementation.

Manages the gold currency system: balance queries, selling equipped cards
for gold, buying marketplace items (mega specials and card packs).
All dependencies arrive via ``__init__`` injection.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING
from uuid import UUID

from src.core.types.game import PlayerId
from src.modules.economy.dto import (
    BuyResult,
    GoldInfo,
    MarketplaceItem,
    SellResult,
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.gold_balance_repository import (
        GoldBalanceRepositoryProtocol,
    )
    from src.data.protocols.gold_transaction_repository import (
        GoldTransactionRepositoryProtocol,
    )
    from src.modules.cards.service import CardService
    from src.modules.energy.protocols import EnergyServiceProtocol
    from src.modules.inventory.service import InventoryService

# Sell rate: 40% of base_value.
_SELL_RATE = 0.4

# Marketplace item definitions (config-driven from backend).
_MARKETPLACE_ITEMS: list[MarketplaceItem] = [
    # === ARSENAL (mega specials) ===
    MarketplaceItem(
        item_id="mega_shuffle_20",
        name="Shuffle",
        description="Randomize the entire board. 20 uses.",
        category="arsenal",
        price=200,
        quantity=20,
        item_type="mega_gem",
        item_params={"slot_index": 4},
    ),
    MarketplaceItem(
        item_id="mega_hh_10",
        name="H + H Blast",
        description="Clears 3 horizontal rows centered on target. 10 uses.",
        category="arsenal",
        price=500,
        quantity=10,
        item_type="mega_gem",
        item_params={"slot_index": 0},
    ),
    MarketplaceItem(
        item_id="mega_vv_10",
        name="V + V Blast",
        description="Clears 3 vertical columns centered on target. 10 uses.",
        category="arsenal",
        price=500,
        quantity=10,
        item_type="mega_gem",
        item_params={"slot_index": 1},
    ),
    MarketplaceItem(
        item_id="mega_bb_5",
        name="Bomb + Bomb",
        description="Massive radius-2 explosion centered on target. 5 uses.",
        category="arsenal",
        price=750,
        quantity=5,
        item_type="mega_gem",
        item_params={"slot_index": 2},
    ),
    MarketplaceItem(
        item_id="mega_oo_1",
        name="Orb + Orb",
        description="Clears the entire board. 1 use.",
        category="arsenal",
        price=500,
        quantity=1,
        item_type="mega_gem",
        item_params={"slot_index": 3},
    ),
    # === ENERGY (hearts for gold) ===
    MarketplaceItem(
        item_id="heart_1",
        name="1 Heart",
        description="Restore 1 heart of energy.",
        category="energy",
        price=100,
        quantity=1,
        item_type="heart",
        item_params={},
    ),
    MarketplaceItem(
        item_id="heart_3",
        name="3 Hearts",
        description="Restore 3 hearts of energy. 17% savings.",
        category="energy",
        price=250,
        quantity=3,
        item_type="heart",
        item_params={},
    ),
    MarketplaceItem(
        item_id="heart_7",
        name="Full Refill",
        description="Restore 7 hearts of energy. 29% savings.",
        category="energy",
        price=500,
        quantity=7,
        item_type="heart",
        item_params={},
    ),
    # === FORGE SUPPLY (card packs) ===
    MarketplaceItem(
        item_id="pack_common_20",
        name="Common Cards",
        description="20 random common cards.",
        category="forge_supply",
        price=1500,
        quantity=20,
        item_type="card_pack",
        item_params={"rarity": "common"},
    ),
    MarketplaceItem(
        item_id="pack_rare_10",
        name="Rare Cards",
        description="10 random rare cards.",
        category="forge_supply",
        price=3000,
        quantity=10,
        item_type="card_pack",
        item_params={"rarity": "rare"},
    ),
    MarketplaceItem(
        item_id="pack_epic_3",
        name="Epic Cards",
        description="3 random epic cards.",
        category="forge_supply",
        price=3000,
        quantity=3,
        item_type="card_pack",
        item_params={"rarity": "epic"},
    ),
    MarketplaceItem(
        item_id="pack_legendary_1",
        name="Legendary Card",
        description="1 random legendary card.",
        category="forge_supply",
        price=5000,
        quantity=1,
        item_type="card_pack",
        item_params={"rarity": "legendary"},
    ),
    # === GOLD PACKS (IAP — display only, purchased via StoreKit) ===
    MarketplaceItem(
        item_id="gold_1500",
        name="Coin Purse",
        description="1,500 gold.",
        category="gold_pack",
        price=49,
        quantity=1500,
        item_type="gold_iap",
        item_params={"cents": 49, "store_product_id": "chromacrush_gold_1500"},
    ),
    MarketplaceItem(
        item_id="gold_3000",
        name="Trader's Pouch",
        description="3,000 gold.",
        category="gold_pack",
        price=99,
        quantity=3000,
        item_type="gold_iap",
        item_params={"cents": 99, "store_product_id": "chromacrush_gold_3000"},
    ),
    MarketplaceItem(
        item_id="gold_15000",
        name="War Chest",
        description="15,000 gold.",
        category="gold_pack",
        price=499,
        quantity=15000,
        item_type="gold_iap",
        item_params={"cents": 499, "store_product_id": "chromacrush_gold_15000"},
    ),
    MarketplaceItem(
        item_id="gold_35000",
        name="King's Ransom",
        description="35,000 gold.",
        category="gold_pack",
        price=999,
        quantity=35000,
        item_type="gold_iap",
        item_params={"cents": 999, "store_product_id": "chromacrush_gold_35000"},
    ),
    MarketplaceItem(
        item_id="gold_80000",
        name="Emperor's Vault",
        description="80,000 gold.",
        category="gold_pack",
        price=1799,
        quantity=80000,
        item_type="gold_iap",
        item_params={"cents": 1799, "store_product_id": "chromacrush_gold_80000"},
    ),
]

# Lookup by item_id for fast access.
_MARKETPLACE_BY_ID: dict[str, MarketplaceItem] = {
    item.item_id: item for item in _MARKETPLACE_ITEMS
}


class EconomyService:
    """Concrete implementation of EconomyServiceProtocol.

    Manages gold currency: querying balances, selling cards for gold,
    and buying marketplace items.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        gold_repo: GoldBalanceRepositoryProtocol,
        card_service: CardService,
        inventory_service: InventoryService,
        energy_service: EnergyServiceProtocol | None = None,
        gold_tx_repo: GoldTransactionRepositoryProtocol | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._gold_repo = gold_repo
        self._gold_tx_repo = gold_tx_repo
        self._card_service = card_service
        self._inventory_service = inventory_service
        self._energy_service = energy_service

        self._equip_slots: int = int(config.get("cards.equip_slots", 3))

    # ========== Gold Balance ==========

    async def get_gold(self, player_id: PlayerId) -> GoldInfo:
        """Get player's current gold balance, creating if needed."""
        record = await self._ensure_balance(UUID(str(player_id)))
        return GoldInfo(
            player_id=str(player_id),
            balance=record.balance,
            lifetime_earned=record.lifetime_earned,
            lifetime_spent=record.lifetime_spent,
        )

    # ========== Sell Cards ==========

    async def sell_equipped_cards(self, player_id: PlayerId) -> SellResult:
        """Sell all 3 equipped cards for gold (40% of base_value each)."""
        pid = UUID(str(player_id))

        # Get equipped cards.
        loadout = await self._card_service.get_equipped_cards(pid)
        if len(loadout.cards) != self._equip_slots:
            raise self._errors.validation(
                f"All {self._equip_slots} equip slots must be filled to sell.",
                code="VALIDATION_SLOTS_NOT_FULL",
            )

        # Calculate gold for each card.
        card_values: list[int] = []
        for card in loadout.cards:
            sell_value = int(card.definition.base_value * _SELL_RATE)
            card_values.append(sell_value)

        total_gold = sum(card_values)

        # Remove all equipped cards.
        for card in loadout.cards:
            await self._card_service.remove_card(pid, card.id, reason="exchange_sell")

        # Credit gold via public method (updates balance + lifetime_earned + tx ledger).
        new_balance = await self.credit_gold(player_id, total_gold, "sell_cards")

        self._logger.info(
            "Cards sold for gold",
            player_id=str(player_id),
            cards_sold=len(loadout.cards),
            gold_earned=total_gold,
            card_values=card_values,
            new_balance=new_balance,
        )

        return SellResult(
            gold_earned=total_gold,
            cards_sold=len(loadout.cards),
            card_values=card_values,
            new_balance=new_balance,
        )

    # ========== Buy Items ==========

    async def buy_item(self, player_id: PlayerId, item_id: str) -> BuyResult:
        """Buy an item from the marketplace."""
        from src.modules.energy.dto import BonusSource

        pid = UUID(str(player_id))

        item = _MARKETPLACE_BY_ID.get(item_id)
        if item is None:
            raise self._errors.not_found(
                f"Marketplace item not found: {item_id}",
                code="NOT_FOUND_MARKETPLACE_ITEM",
                item_id=item_id,
            )

        # Gold IAP packs cannot be bought with gold — they use StoreKit.
        if item.item_type == "gold_iap":
            raise self._errors.validation(
                "Gold packs are purchased via in-app purchase, not gold.",
                code="VALIDATION_IAP_ONLY",
            )

        # Ensure balance exists.
        await self._ensure_balance(pid)

        # Debit gold (raises INSUFFICIENT_GOLD if not enough).
        record = await self._gold_repo.debit(pid, item.price)

        # Record in gold transaction ledger.
        if self._gold_tx_repo is not None:
            await self._gold_tx_repo.create(
                player_id=pid,
                tx_type="spent",
                amount=-item.price,
                balance_after=record.balance,
                source=f"buy:{item_id}",
                reference_id=item_id,
            )

        # Grant the purchased item via public reward methods.
        if item.item_type == "mega_gem":
            slot_index = item.item_params["slot_index"]
            await self.grant_mega_reward(player_id, slot_index, item.quantity)
        elif item.item_type == "card_pack":
            rarity = item.item_params["rarity"]
            await self.grant_card_pack(
                player_id, rarity, item.quantity, "marketplace_purchase"
            )
        elif item.item_type == "heart":
            if self._energy_service is None:
                raise self._errors.internal(
                    "Energy service not available",
                    code="INTERNAL_MISSING_ENERGY_SERVICE",
                )
            await self._energy_service.grant_bonus_hearts(
                player_id,
                item.quantity,
                source=BonusSource.PURCHASE,
            )

        self._logger.info(
            "Marketplace item purchased",
            player_id=str(player_id),
            item_id=item_id,
            item_name=item.name,
            gold_spent=item.price,
            quantity=item.quantity,
            new_balance=record.balance,
        )

        return BuyResult(
            item_id=item_id,
            item_name=item.name,
            gold_spent=item.price,
            new_balance=record.balance,
            quantity_granted=item.quantity,
        )

    # ========== Marketplace ==========

    async def get_marketplace(self) -> list[MarketplaceItem]:
        """List all available marketplace items."""
        return list(_MARKETPLACE_ITEMS)

    # ========== Public Reward Methods ==========
    # Used by campaign rewards, barter marketplace, and any future reward source.

    async def credit_gold(
        self, player_id: PlayerId, amount: int, source: str
    ) -> int:
        """Credit gold to a player. Returns new balance.

        Updates balance, lifetime_earned, and records a transaction.
        """
        pid = UUID(str(player_id))
        await self._ensure_balance(pid)
        record = await self._gold_repo.credit(pid, amount)

        if self._gold_tx_repo is not None:
            await self._gold_tx_repo.create(
                player_id=pid,
                tx_type="earned",
                amount=amount,
                balance_after=record.balance,
                source=source,
            )

        self._logger.info(
            "Gold credited",
            player_id=str(player_id),
            amount=amount,
            source=source,
            new_balance=record.balance,
        )
        return record.balance

    async def grant_card_pack(
        self, player_id: PlayerId, rarity: str, count: int, source: str
    ) -> None:
        """Grant random cards of a specific rarity to a player."""
        pid = UUID(str(player_id))
        definitions = await self._card_service.list_card_definitions(rarity=rarity)
        if not definitions:
            self._logger.warning(
                "No card definitions for rarity",
                rarity=rarity,
            )
            return

        for _ in range(count):
            chosen = random.choice(definitions)
            await self._card_service.grant_card(
                player_id=pid,
                card_id=chosen.card_id,
                source=source,
            )

        self._logger.info(
            "Card pack granted",
            player_id=str(player_id),
            rarity=rarity,
            count=count,
            source=source,
        )

    async def grant_mega_reward(
        self, player_id: PlayerId, slot_index: int, count: int
    ) -> None:
        """Grant mega gems to a player's inventory."""
        await self._inventory_service.grant_mega(
            str(player_id), slot_index, count
        )
        self._logger.info(
            "Mega gem reward granted",
            player_id=str(player_id),
            slot_index=slot_index,
            count=count,
        )

    # ========== Internal Helpers ==========

    async def _ensure_balance(self, player_id: UUID):
        """Get or create gold balance for a player."""
        record = await self._gold_repo.find_by_player_id(player_id)
        if record is None:
            record = await self._gold_repo.create(player_id)
        return record
