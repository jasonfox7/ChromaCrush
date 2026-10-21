"""Card service implementation.

Manages card definitions, player card collections, equip slots (positions 1-3),
and merge progression. All dependencies arrive via ``__init__`` injection.

Card definitions are loaded from ``config/card_definitions.json`` at startup
and stored in memory. Only player card instances (ownership, positions) are
stored in the database.

Card effect hooks are deferred to Phase 4C (collaborative design with human).
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from src.modules.cards.dto import (
    CardDefinition,
    EquippedLoadout,
    MergeResult,
    PlayerCard,
)
from src.modules.vault.dto import PaginatedResult

if TYPE_CHECKING:
    from uuid import UUID

    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.player_card_repository import (
        PlayerCardRepositoryProtocol,
    )
    from src.modules.player.protocols import PlayerServiceProtocol

# Default path to card definitions JSON.
_DEFAULT_DEFINITIONS_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "card_definitions.json"
)

# Rarity ordering for merge validation.
_RARITY_ORDER = ["common", "rare", "epic", "legendary"]


@dataclass
class _DefinitionRecord:
    """In-memory representation of a card definition loaded from JSON."""

    card_id: int
    name: str
    description: str
    rarity: str
    card_set: str
    set_position: int
    base_value: int
    tags: list[str] = field(default_factory=list)
    trigger: str = "passive"
    effect: str = ""
    effect_params: dict = field(default_factory=dict)
    trigger_condition: dict | None = None


class CardService:
    """Manages card definitions, player cards, equipping, and merging.

    Card definitions are loaded from JSON at construction time and kept
    in memory. The database stores only player card instances.

    Args:
        config: Configuration service for reading settings.
        logger: Structured logging service.
        errors: Error factory service.
        player_service: Player module for existence checks.
        player_card_repo: Repository for player card instances.
        definitions_path: Optional path to card definitions JSON.
            If None, uses the default ``config/card_definitions.json``.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        player_card_repo: PlayerCardRepositoryProtocol,
        definitions_path: str | Path | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._player_service = player_service
        self._player_card_repo = player_card_repo

        self._equip_slots: int = config.get("cards.equip_slots", 3)

        # Load card definitions from JSON into memory.
        self._definitions: dict[int, _DefinitionRecord] = {}
        self._load_definitions(definitions_path)

    # ========== Definition Loading ==========

    def _load_definitions(self, path: str | Path | None = None) -> None:
        """Load card definitions from JSON file into memory."""
        definitions_path = Path(path) if path else _DEFAULT_DEFINITIONS_PATH

        try:
            with open(definitions_path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self._logger.warning(
                "Card definitions file not found",
                path=str(definitions_path),
            )
            return

        cards = data.get("cards", {})
        for card_id_str, defn in cards.items():
            card_id = int(card_id_str)
            self._definitions[card_id] = _DefinitionRecord(
                card_id=card_id,
                name=defn["name"],
                description=defn.get("description", ""),
                rarity=defn["rarity"],
                card_set=defn["set"],
                set_position=defn["set_position"],
                base_value=defn.get("base_value", 100),
                tags=defn.get("tags", []),
                trigger=defn.get("trigger", "passive"),
                effect=defn.get("effect", ""),
                effect_params=defn.get("effect_params", {}),
                trigger_condition=defn.get("trigger_condition", None),
            )

        self._logger.info(
            "Card definitions loaded",
            count=len(self._definitions),
            path=str(definitions_path),
        )

    # ========== Definitions ==========

    async def get_card_definition(self, card_id: int) -> CardDefinition:
        """Get a single card definition by ID."""
        record = self._definitions.get(card_id)
        if record is None:
            raise self._errors.not_found(
                f"Card definition not found: {card_id}",
                code="NOT_FOUND_CARD_DEFINITION",
                card_id=card_id,
            )
        return self._definition_from_record(record)

    def get_card_ids_by_rarity(self, rarity: str) -> list[int]:
        """Return all card IDs for a given rarity, from in-memory definitions."""
        return [cid for cid, d in self._definitions.items() if d.rarity == rarity]

    async def list_card_definitions(
        self,
        rarity: str | None = None,
        card_set: str | None = None,
    ) -> list[CardDefinition]:
        """List all card definitions with optional filters."""
        results = list(self._definitions.values())
        if rarity is not None:
            results = [r for r in results if r.rarity == rarity]
        if card_set is not None:
            results = [r for r in results if r.card_set == card_set]
        results.sort(key=lambda r: (r.card_set, r.set_position))
        return [self._definition_from_record(r) for r in results]

    # ========== Player Cards ==========

    async def get_player_cards(
        self,
        player_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[PlayerCard]:
        """Get all cards owned by a player."""
        records, total = await self._player_card_repo.find_by_player(
            player_id, limit=limit, offset=offset
        )

        items = []
        for record in records:
            definition = self._get_definition(record.card_id)
            items.append(self._player_card_from_record(record, definition))

        return PaginatedResult(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_equipped_cards(self, player_id: UUID) -> EquippedLoadout:
        """Get the player's equipped card loadout (positions 1-3)."""
        records = await self._player_card_repo.find_equipped(player_id)

        cards = []
        for record in records:
            definition = self._get_definition(record.card_id)
            cards.append(self._player_card_from_record(record, definition))

        return EquippedLoadout(player_id=player_id, cards=cards)

    async def build_modifier_engine(self, player_id: UUID) -> object:
        """Build a CardModifierEngine from a player's equipped cards.

        Looks up each equipped card's definition and extracts the
        effect-relevant fields into ``CardModifierDef`` instances.
        Cards without an ``effect`` are silently skipped.

        Args:
            player_id: The player whose loadout to build from.

        Returns:
            A ``CardModifierEngine`` ready for use during move processing.
        """
        from src.modules.cards.modifier_engine import CardModifierEngine
        from src.modules.cards.modifier_types import CardModifierDef

        loadout = await self.get_equipped_cards(player_id)
        card_defs: list[CardModifierDef] = []
        for card in loadout.cards:
            defn = self._definitions.get(card.card_id)
            if defn is not None and defn.effect:
                card_defs.append(
                    CardModifierDef(
                        card_id=defn.card_id,
                        name=defn.name,
                        trigger=defn.trigger,
                        effect=defn.effect,
                        effect_params=dict(defn.effect_params),
                        trigger_condition=(
                            dict(defn.trigger_condition)
                            if defn.trigger_condition
                            else None
                        ),
                        tags=list(defn.tags),
                    )
                )
        return CardModifierEngine(card_defs)

    async def grant_card(
        self,
        player_id: UUID,
        card_id: int,
        source: str,
        source_id: str | None = None,
    ) -> PlayerCard:
        """Grant a new card to a player.

        The card is placed at the next available position (after existing cards).
        """
        # Validate card definition exists in JSON.
        defn = self._definitions.get(card_id)
        if defn is None:
            raise self._errors.not_found(
                f"Card definition not found: {card_id}",
                code="NOT_FOUND_CARD_DEFINITION",
                card_id=card_id,
            )

        # Place at next available position.
        max_pos = await self._player_card_repo.find_max_position(player_id)
        new_position = max_pos + 1

        # If landing in an equip slot (1-3), check for duplicate card_id.
        if new_position <= self._equip_slots:
            equipped = await self._player_card_repo.find_equipped(player_id)
            equipped_card_ids = {r.card_id for r in equipped}
            if card_id in equipped_card_ids:
                # Push past equip slots to avoid duplicate in loadout.
                new_position = max(max_pos + 1, self._equip_slots + 1)

        record = await self._player_card_repo.create(
            player_id=player_id,
            card_id=card_id,
            position=new_position,
            source=source,
            source_id=source_id,
        )

        definition = self._definition_from_record(defn)
        return self._player_card_from_record(record, definition)

    async def equip_card(
        self,
        player_id: UUID,
        card_instance_id: UUID,
        slot: int,
    ) -> EquippedLoadout:
        """Equip a card into a specific slot (1-3).

        If another card occupies the target slot, it gets bumped to the
        first available position after the equip slots.
        """
        if slot < 1 or slot > self._equip_slots:
            raise self._errors.validation(
                f"Invalid equip slot: {slot}. Must be 1-{self._equip_slots}.",
                code="VALIDATION_INVALID_SLOT",
                slot=slot,
            )

        # Verify card exists and belongs to player.
        card_record = await self._player_card_repo.find_by_id(card_instance_id)
        if card_record is None:
            raise self._errors.not_found(
                f"Player card not found: {card_instance_id}",
                code="NOT_FOUND_PLAYER_CARD",
                card_instance_id=str(card_instance_id),
            )
        if card_record.player_id != player_id:
            raise self._errors.forbidden(
                "Card does not belong to this player",
                code="FORBIDDEN_CARD_NOT_OWNED",
            )

        # If card is already in this slot, no-op.
        if card_record.position == slot:
            return await self.get_equipped_cards(player_id)

        # Check if another card occupies the target slot.
        equipped = await self._player_card_repo.find_equipped(player_id)

        # Reject if another equipped card has the same card definition ID.
        for eq in equipped:
            if eq.card_id == card_record.card_id and eq.id != card_record.id:
                raise self._errors.validation(
                    "Cannot equip two cards with the same definition. "
                    f"Card '{card_record.card_id}' is already equipped.",
                    code="VALIDATION_DUPLICATE_EQUIPPED",
                )

        occupant = next((c for c in equipped if c.position == slot), None)

        if occupant is not None:
            # Bump the occupant to the card's old position (swap).
            await self._player_card_repo.update_position(
                occupant.id, card_record.position
            )

        # Move card to target slot.
        await self._player_card_repo.update_position(card_instance_id, slot)

        return await self.get_equipped_cards(player_id)

    async def unequip_card(
        self,
        player_id: UUID,
        card_instance_id: UUID,
    ) -> EquippedLoadout:
        """Unequip a card from its slot back to the vault.

        Moves the card to the first available position after equip slots.
        """
        card_record = await self._player_card_repo.find_by_id(card_instance_id)
        if card_record is None:
            raise self._errors.not_found(
                f"Player card not found: {card_instance_id}",
                code="NOT_FOUND_PLAYER_CARD",
                card_instance_id=str(card_instance_id),
            )
        if card_record.player_id != player_id:
            raise self._errors.forbidden(
                "Card does not belong to this player",
                code="FORBIDDEN_CARD_NOT_OWNED",
            )

        if card_record.position > self._equip_slots:
            raise self._errors.validation(
                "Card is not currently equipped",
                code="VALIDATION_CARD_NOT_EQUIPPED",
            )

        # Move to first available position after equip slots.
        max_pos = await self._player_card_repo.find_max_position(player_id)
        new_position = max(max_pos + 1, self._equip_slots + 1)
        await self._player_card_repo.update_position(card_instance_id, new_position)

        return await self.get_equipped_cards(player_id)

    async def reorder_card(
        self,
        player_id: UUID,
        card_instance_id: UUID,
        new_position: int,
    ) -> PlayerCard:
        """Move a card to a new position.

        For non-equip positions (> 3), this is a simple reorder.
        """
        card_record = await self._player_card_repo.find_by_id(card_instance_id)
        if card_record is None:
            raise self._errors.not_found(
                f"Player card not found: {card_instance_id}",
                code="NOT_FOUND_PLAYER_CARD",
                card_instance_id=str(card_instance_id),
            )
        if card_record.player_id != player_id:
            raise self._errors.forbidden(
                "Card does not belong to this player",
                code="FORBIDDEN_CARD_NOT_OWNED",
            )

        record = await self._player_card_repo.update_position(
            card_instance_id, new_position
        )

        definition = self._get_definition(record.card_id)
        return self._player_card_from_record(record, definition)

    async def remove_card(
        self,
        player_id: UUID,
        card_instance_id: UUID,
        reason: str,
    ) -> None:
        """Remove a card from a player's collection."""
        card_record = await self._player_card_repo.find_by_id(card_instance_id)
        if card_record is None:
            raise self._errors.not_found(
                f"Player card not found: {card_instance_id}",
                code="NOT_FOUND_PLAYER_CARD",
                card_instance_id=str(card_instance_id),
            )
        if card_record.player_id != player_id:
            raise self._errors.forbidden(
                "Card does not belong to this player",
                code="FORBIDDEN_CARD_NOT_OWNED",
            )

        self._logger.info(
            "Removing player card",
            card_instance_id=str(card_instance_id),
            reason=reason,
        )
        await self._player_card_repo.delete(card_instance_id)

    # ========== Merge ==========

    async def merge_equipped(self, player_id: UUID) -> MergeResult:
        """Merge all 3 equipped cards into a random higher-tier card.

        Requirements:
        - All 3 equip slots must be filled.
        - All 3 cards must share the same rarity.
        - Rarity must be below legendary (cannot merge legendaries).

        Returns:
            MergeResult with consumed card IDs and the new card.
        """
        equipped = await self._player_card_repo.find_equipped(player_id)

        if len(equipped) != self._equip_slots:
            raise self._errors.validation(
                f"All {self._equip_slots} equip slots must be filled to merge.",
                code="VALIDATION_MERGE_SLOTS_NOT_FULL",
            )

        # Resolve definitions to check rarities.
        rarities = set()
        for record in equipped:
            defn = self._definitions.get(record.card_id)
            if defn is None:
                raise self._errors.internal(
                    f"Card definition missing for card_id {record.card_id}",
                    code="INTERNAL_MISSING_DEFINITION",
                )
            rarities.add(defn.rarity)

        if len(rarities) != 1:
            raise self._errors.validation(
                "All equipped cards must share the same rarity to merge.",
                code="VALIDATION_MERGE_RARITY_MISMATCH",
            )

        source_rarity = rarities.pop()
        rarity_idx = (
            _RARITY_ORDER.index(source_rarity) if source_rarity in _RARITY_ORDER else -1
        )

        if rarity_idx < 0:
            raise self._errors.validation(
                f"Unknown rarity: {source_rarity}",
                code="VALIDATION_UNKNOWN_RARITY",
            )
        if rarity_idx >= len(_RARITY_ORDER) - 1:
            raise self._errors.validation(
                "Cannot merge cards of the highest rarity.",
                code="VALIDATION_MERGE_MAX_RARITY",
            )

        target_rarity = _RARITY_ORDER[rarity_idx + 1]

        # Pick a random card from the next rarity tier (from in-memory definitions).
        candidates = [
            d for d in self._definitions.values() if d.rarity == target_rarity
        ]
        if not candidates:
            raise self._errors.internal(
                f"No card definitions found for rarity: {target_rarity}",
                code="INTERNAL_NO_CANDIDATES",
            )

        chosen = random.choice(candidates)

        # Consume the 3 equipped cards.
        consumed_ids = [record.id for record in equipped]
        await self._player_card_repo.delete_multiple(consumed_ids)

        # Grant the new card at position 1.
        new_record = await self._player_card_repo.create(
            player_id=player_id,
            card_id=chosen.card_id,
            position=1,
            source="merge",
            source_id=None,
        )

        definition = self._definition_from_record(chosen)
        new_card = self._player_card_from_record(new_record, definition)

        self._logger.info(
            "Cards merged",
            player_id=str(player_id),
            consumed=len(consumed_ids),
            source_rarity=source_rarity,
            target_rarity=target_rarity,
            new_card_id=chosen.card_id,
        )

        return MergeResult(
            consumed_card_ids=consumed_ids,
            new_card=new_card,
            source_rarity=source_rarity,
            target_rarity=target_rarity,
        )

    # ========== Raid Card Transfer ==========

    async def steal_random_equipped(self, from_player_id: UUID) -> PlayerCard | None:
        """Pick a random equipped card from a player and return it.

        Does NOT remove the card — caller decides whether to transfer or unequip.
        Returns None if the player has no equipped cards.
        """
        equipped = await self._player_card_repo.find_equipped(from_player_id)
        if not equipped:
            return None
        chosen = random.choice(equipped)
        definition = self._get_definition(chosen.card_id)
        return self._player_card_from_record(chosen, definition)

    async def transfer_card(
        self,
        card_instance_id: UUID,
        from_player_id: UUID,
        to_player_id: UUID,
    ) -> PlayerCard:
        """Transfer a card from one player to another.

        Deletes the card from the source player and grants the same
        card_id to the destination player with source='raid_steal'.
        """
        card_record = await self._player_card_repo.find_by_id(card_instance_id)
        if card_record is None or card_record.player_id != from_player_id:
            raise self._errors.not_found(
                "Card not found for transfer",
                code="NOT_FOUND_PLAYER_CARD",
            )

        card_id = card_record.card_id
        await self._player_card_repo.delete(card_instance_id)

        return await self.grant_card(
            player_id=to_player_id,
            card_id=card_id,
            source="raid_steal",
            source_id=str(from_player_id),
        )

    async def unequip_to_vault(self, card_instance_id: UUID, player_id: UUID) -> None:
        """Move an equipped card to the first unequipped position (vault).

        Used when a shield protects the card from being stolen.
        """
        max_pos = await self._player_card_repo.find_max_position(player_id)
        new_position = max(max_pos + 1, self._equip_slots + 1)
        await self._player_card_repo.update_position(card_instance_id, new_position)

    # ========== Bot Loadout ==========

    async def ensure_bot_loadout(self, player_id: UUID) -> None:
        """Idempotently grant and equip 3 random cards for a bot player.

        If the bot already has 3+ equipped cards, this is a no-op.
        Cards are granted with source='bot_loadout' and placed in
        equip slots 1-3.
        """
        equipped = await self._player_card_repo.find_equipped(player_id)
        if len(equipped) >= self._equip_slots:
            return  # Already has a full loadout.

        # Pick random card definitions (one per slot that needs filling).
        all_defs = list(self._definitions.values())
        if not all_defs:
            return

        needed = self._equip_slots - len(equipped)
        occupied_slots = {r.position for r in equipped}
        chosen = random.sample(all_defs, min(needed, len(all_defs)))

        slot = 1
        for defn in chosen:
            while slot in occupied_slots and slot <= self._equip_slots:
                slot += 1
            if slot > self._equip_slots:
                break
            await self._player_card_repo.create(
                player_id=player_id,
                card_id=defn.card_id,
                position=slot,
                source="bot_loadout",
                source_id=None,
            )
            occupied_slots.add(slot)
            slot += 1

        self._logger.info(
            "Bot loadout ensured",
            player_id=str(player_id),
            cards_granted=len(chosen),
        )

    # ========== Starter Pack & Bot Full Loadout ==========

    async def grant_starter_pack(self, player_id: UUID) -> list:
        """Grant 15 starter cards to a new human player.

        Each card: 97% common, 3% rare. Pools resolved dynamically
        from card definitions JSON. The first 3 cards (which land in
        equip slots 1-3) are guaranteed to have distinct card_ids.
        """
        commons = self.get_card_ids_by_rarity("common")
        rares = self.get_card_ids_by_rarity("rare")
        if not commons:
            return []

        granted = []
        equipped_card_ids: set[int] = set()
        for i in range(15):
            pool = rares if (random.random() < 0.03 and rares) else commons
            card_id = random.choice(pool)

            # First 3 cards go to equip slots — ensure distinct card_ids.
            if i < self._equip_slots:
                available = [cid for cid in pool if cid not in equipped_card_ids]
                if available:
                    card_id = random.choice(available)
                equipped_card_ids.add(card_id)

            card = await self.grant_card(
                player_id,
                card_id,
                source="starter_pack",
            )
            granted.append(card)

        self._logger.info(
            "Starter pack granted",
            player_id=str(player_id),
            count=len(granted),
        )
        return granted

    async def grant_bot_full_loadout(self, player_id: UUID) -> None:
        """Grant a bot its full card inventory and equip 3 cards.

        All commons + 5 random rares + 5 random epics + 3 random legendaries.
        Pools resolved dynamically from card definitions JSON.
        """
        for card_id in self.get_card_ids_by_rarity("common"):
            await self.grant_card(player_id, card_id, source="bot_inventory")

        rares = self.get_card_ids_by_rarity("rare")
        if rares:
            for card_id in random.sample(rares, min(5, len(rares))):
                await self.grant_card(player_id, card_id, source="bot_inventory")

        epics = self.get_card_ids_by_rarity("epic")
        if epics:
            for card_id in random.sample(epics, min(5, len(epics))):
                await self.grant_card(player_id, card_id, source="bot_inventory")

        legendaries = self.get_card_ids_by_rarity("legendary")
        if legendaries:
            for card_id in random.sample(legendaries, min(3, len(legendaries))):
                await self.grant_card(player_id, card_id, source="bot_inventory")

        await self.ensure_bot_loadout(player_id)

        self._logger.info(
            "Bot full loadout granted",
            player_id=str(player_id),
        )

    # ========== Internal helpers ==========

    def _get_definition(self, card_id: int) -> CardDefinition | None:
        """Look up a card definition from memory and convert to DTO."""
        record = self._definitions.get(card_id)
        if record is None:
            return None
        return self._definition_from_record(record)

    @staticmethod
    def _definition_from_record(record: _DefinitionRecord) -> CardDefinition:
        """Convert a definition record to a CardDefinition DTO."""
        return CardDefinition(
            card_id=record.card_id,
            name=record.name,
            description=record.description or "",
            rarity=record.rarity,
            card_set=record.card_set,
            set_position=record.set_position,
            base_value=record.base_value,
            tags=record.tags if record.tags else [],
            trigger=record.trigger,
            effect=record.effect,
            effect_params=record.effect_params if record.effect_params else {},
            trigger_condition=record.trigger_condition,
        )

    @staticmethod
    def _player_card_from_record(
        record, definition: CardDefinition | None
    ) -> PlayerCard:
        """Convert a player card record + definition to a PlayerCard DTO."""
        return PlayerCard(
            id=record.id,
            player_id=record.player_id,
            card_id=record.card_id,
            definition=definition
            or CardDefinition(
                card_id=record.card_id,
                name="Unknown",
                description="",
                rarity="common",
                card_set="",
                set_position=0,
                base_value=0,
                tags=[],
            ),
            position=record.position,
            level=record.level,
            acquired_at=record.acquired_at,
            source=record.source,
            source_id=record.source_id,
        )
