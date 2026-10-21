"""Unit tests for the CardService.

Uses mock repositories to test business logic without a real database.
Card definitions are loaded from a temporary JSON file.
All tests are async using ``pytest-asyncio``.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.core.errors import AppError
from src.modules.cards.service import CardService
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ---------------------------------------------------------------------------
# Test card definitions (written to a temp JSON file)
# ---------------------------------------------------------------------------


_TEST_DEFINITIONS = {
    "version": "1.0",
    "equip_slots": 3,
    "rarity_weights": {"common": 0.60, "rare": 0.25, "epic": 0.12, "legendary": 0.03},
    "rarity_order": ["common", "rare", "epic", "legendary"],
    "sets": {
        "elements": {"name": "Elemental Collection", "size": 5},
        "chrono": {"name": "Chrono Shards", "size": 5},
    },
    "cards": {
        "1": {
            "name": "Ember Shard",
            "description": "Fire card",
            "rarity": "common",
            "set": "elements",
            "set_position": 1,
            "base_value": 100,
            "tags": ["fire"],
        },
        "2": {
            "name": "Frost Prism",
            "description": "Ice card",
            "rarity": "common",
            "set": "elements",
            "set_position": 2,
            "base_value": 100,
            "tags": ["ice"],
        },
        "3": {
            "name": "Gale Feather",
            "description": "Wind card",
            "rarity": "common",
            "set": "elements",
            "set_position": 3,
            "base_value": 100,
            "tags": ["wind"],
        },
        "4": {
            "name": "Stone Heart",
            "description": "Earth card",
            "rarity": "rare",
            "set": "elements",
            "set_position": 4,
            "base_value": 250,
            "tags": ["earth"],
        },
        "5": {
            "name": "Tempest Core",
            "description": "Storm card",
            "rarity": "epic",
            "set": "elements",
            "set_position": 5,
            "base_value": 500,
            "tags": ["storm"],
        },
        "10": {
            "name": "Eternity Gear",
            "description": "Time card",
            "rarity": "legendary",
            "set": "chrono",
            "set_position": 5,
            "base_value": 1000,
            "tags": ["time"],
        },
    },
}


# ---------------------------------------------------------------------------
# Mock data classes for repository records
# ---------------------------------------------------------------------------


@dataclass
class FakePlayerCardRecord:
    """Minimal player card record for mock repository."""

    id: UUID
    player_id: UUID
    card_id: int
    position: int
    acquired_at: datetime
    source: str
    source_id: str | None
    level: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Mock repositories
# ---------------------------------------------------------------------------


class MockPlayerCardRepository:
    """In-memory mock for PlayerCardRepositoryProtocol."""

    def __init__(self):
        self._cards: dict[UUID, FakePlayerCardRecord] = {}

    async def find_by_id(self, card_instance_id: UUID) -> FakePlayerCardRecord | None:
        return self._cards.get(card_instance_id)

    async def find_by_player(
        self,
        player_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[FakePlayerCardRecord], int]:
        items = sorted(
            [c for c in self._cards.values() if c.player_id == player_id],
            key=lambda c: c.position,
        )
        total = len(items)
        return items[offset : offset + limit], total

    async def find_equipped(self, player_id: UUID) -> list[FakePlayerCardRecord]:
        items = [
            c
            for c in self._cards.values()
            if c.player_id == player_id and c.position <= 3
        ]
        return sorted(items, key=lambda c: c.position)

    async def count_by_player(self, player_id: UUID) -> int:
        return len([c for c in self._cards.values() if c.player_id == player_id])

    async def find_max_position(self, player_id: UUID) -> int:
        positions = [
            c.position for c in self._cards.values() if c.player_id == player_id
        ]
        return max(positions) if positions else 0

    async def create(
        self,
        player_id: UUID,
        card_id: int,
        position: int,
        source: str,
        source_id: str | None = None,
    ) -> FakePlayerCardRecord:
        record = FakePlayerCardRecord(
            id=uuid4(),
            player_id=player_id,
            card_id=card_id,
            position=position,
            acquired_at=datetime.now(timezone.utc),
            source=source,
            source_id=source_id,
            level=1,
            created_at=datetime.now(timezone.utc),
        )
        self._cards[record.id] = record
        return record

    async def update_position(
        self,
        card_instance_id: UUID,
        new_position: int,
    ) -> FakePlayerCardRecord:
        record = self._cards.get(card_instance_id)
        if record is None:
            raise ValueError(f"Card not found: {card_instance_id}")
        record.position = new_position
        return record

    async def delete(self, card_instance_id: UUID) -> None:
        self._cards.pop(card_instance_id, None)

    async def delete_multiple(self, card_instance_ids: list[UUID]) -> None:
        for cid in card_instance_ids:
            self._cards.pop(cid, None)


# ---------------------------------------------------------------------------
# Mock player service
# ---------------------------------------------------------------------------


class MockPlayerService:
    """Minimal mock for PlayerServiceProtocol."""

    async def get_player(self, player_id: Any) -> Any:
        return {"id": player_id, "username": "testplayer"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def definitions_path(tmp_path: Path) -> Path:
    """Write test card definitions to a temporary JSON file."""
    path = tmp_path / "card_definitions.json"
    path.write_text(json.dumps(_TEST_DEFINITIONS), encoding="utf-8")
    return path


@pytest.fixture
def card_service(definitions_path: Path) -> CardService:
    """Create a CardService with mock dependencies and temp definitions."""
    config = MockConfigService()
    logger = MockLogService()
    errors = MockErrorService()
    return CardService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=MockPlayerService(),
        player_card_repo=MockPlayerCardRepository(),
        definitions_path=definitions_path,
    )


@pytest.fixture
def player_id() -> UUID:
    """A consistent test player UUID."""
    return UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


# ---------------------------------------------------------------------------
# Tests: Card Definitions
# ---------------------------------------------------------------------------


class TestCardDefinitions:
    """Tests for card definition queries."""

    @pytest.mark.asyncio
    async def test_get_card_definition(self, card_service: CardService):
        defn = await card_service.get_card_definition(1)
        assert defn.card_id == 1
        assert defn.name == "Ember Shard"
        assert defn.rarity == "common"

    @pytest.mark.asyncio
    async def test_get_card_definition_not_found(self, card_service: CardService):
        with pytest.raises(AppError):
            await card_service.get_card_definition(999)

    @pytest.mark.asyncio
    async def test_list_definitions_all(self, card_service: CardService):
        definitions = await card_service.list_card_definitions()
        assert len(definitions) == 6

    @pytest.mark.asyncio
    async def test_list_definitions_by_rarity(self, card_service: CardService):
        commons = await card_service.list_card_definitions(rarity="common")
        assert len(commons) == 3
        assert all(d.rarity == "common" for d in commons)


# ---------------------------------------------------------------------------
# Tests: Grant & Collection
# ---------------------------------------------------------------------------


class TestGrantAndCollection:
    """Tests for granting cards and querying player collections."""

    @pytest.mark.asyncio
    async def test_grant_card(self, card_service: CardService, player_id: UUID):
        card = await card_service.grant_card(player_id, 1, "match_reward")
        assert card.card_id == 1
        assert card.player_id == player_id
        assert card.source == "match_reward"
        assert card.position == 1  # First card

    @pytest.mark.asyncio
    async def test_grant_card_increments_position(
        self, card_service: CardService, player_id: UUID
    ):
        c1 = await card_service.grant_card(player_id, 1, "test")
        c2 = await card_service.grant_card(player_id, 2, "test")
        c3 = await card_service.grant_card(player_id, 3, "test")
        assert c1.position == 1
        assert c2.position == 2
        assert c3.position == 3

    @pytest.mark.asyncio
    async def test_grant_nonexistent_card_fails(
        self, card_service: CardService, player_id: UUID
    ):
        with pytest.raises(AppError):
            await card_service.grant_card(player_id, 999, "test")

    @pytest.mark.asyncio
    async def test_get_player_cards(self, card_service: CardService, player_id: UUID):
        await card_service.grant_card(player_id, 1, "test")
        await card_service.grant_card(player_id, 2, "test")

        result = await card_service.get_player_cards(player_id)
        assert result.total == 2
        assert len(result.items) == 2


# ---------------------------------------------------------------------------
# Tests: Equip & Unequip
# ---------------------------------------------------------------------------


class TestEquipUnequip:
    """Tests for equipping and unequipping cards."""

    @pytest.mark.asyncio
    async def test_equip_card(self, card_service: CardService, player_id: UUID):
        card = await card_service.grant_card(player_id, 1, "test")
        # Card starts at position 1 (first granted), equip to slot 1.
        loadout = await card_service.equip_card(player_id, card.id, slot=1)
        assert len(loadout.cards) == 1
        assert loadout.cards[0].position == 1

    @pytest.mark.asyncio
    async def test_equip_swaps_with_occupant(
        self, card_service: CardService, player_id: UUID
    ):
        # Grant 2 cards: positions 1 and 2
        c1 = await card_service.grant_card(player_id, 1, "test")
        c2 = await card_service.grant_card(player_id, 2, "test")

        # Equip c2 into slot 1 (c1's slot) — should swap
        loadout = await card_service.equip_card(player_id, c2.id, slot=1)

        # c2 should now be in slot 1
        slot1_cards = [c for c in loadout.cards if c.position == 1]
        assert len(slot1_cards) == 1
        assert slot1_cards[0].card_id == 2

    @pytest.mark.asyncio
    async def test_equip_invalid_slot_fails(
        self, card_service: CardService, player_id: UUID
    ):
        card = await card_service.grant_card(player_id, 1, "test")
        with pytest.raises(AppError):
            await card_service.equip_card(player_id, card.id, slot=4)

    @pytest.mark.asyncio
    async def test_equip_card_not_owned_fails(
        self, card_service: CardService, player_id: UUID
    ):
        card = await card_service.grant_card(player_id, 1, "test")
        other_player = UUID("11111111-2222-3333-4444-555555555555")
        with pytest.raises(AppError):
            await card_service.equip_card(other_player, card.id, slot=1)

    @pytest.mark.asyncio
    async def test_unequip_card(self, card_service: CardService, player_id: UUID):
        card = await card_service.grant_card(player_id, 1, "test")
        # Card is at position 1 (equipped)
        loadout = await card_service.unequip_card(player_id, card.id)
        # Should have 0 equipped cards now
        assert len(loadout.cards) == 0

    @pytest.mark.asyncio
    async def test_unequip_non_equipped_card_fails(
        self, card_service: CardService, player_id: UUID
    ):
        # Grant 4 cards to push one past equip slots
        await card_service.grant_card(player_id, 1, "test")
        await card_service.grant_card(player_id, 2, "test")
        await card_service.grant_card(player_id, 3, "test")
        c4 = await card_service.grant_card(player_id, 4, "test")
        # c4 is at position 4 (not equipped)
        with pytest.raises(AppError):
            await card_service.unequip_card(player_id, c4.id)


# ---------------------------------------------------------------------------
# Tests: Merge
# ---------------------------------------------------------------------------


class TestMerge:
    """Tests for merging 3 equipped cards."""

    @pytest.mark.asyncio
    async def test_merge_success(self, card_service: CardService, player_id: UUID):
        # Grant 3 common cards (they'll be at positions 1,2,3 = equipped)
        await card_service.grant_card(player_id, 1, "test")
        await card_service.grant_card(player_id, 2, "test")
        await card_service.grant_card(player_id, 3, "test")

        result = await card_service.merge_equipped(player_id)
        assert result.source_rarity == "common"
        assert result.target_rarity == "rare"
        assert len(result.consumed_card_ids) == 3
        assert result.new_card.definition.rarity == "rare"

    @pytest.mark.asyncio
    async def test_merge_not_enough_cards_fails(
        self, card_service: CardService, player_id: UUID
    ):
        await card_service.grant_card(player_id, 1, "test")
        await card_service.grant_card(player_id, 2, "test")
        # Only 2 equipped cards
        with pytest.raises(AppError):
            await card_service.merge_equipped(player_id)

    @pytest.mark.asyncio
    async def test_merge_mixed_rarities_fails(
        self, card_service: CardService, player_id: UUID
    ):
        # Grant 2 common + 1 rare
        await card_service.grant_card(player_id, 1, "test")  # common
        await card_service.grant_card(player_id, 2, "test")  # common
        await card_service.grant_card(player_id, 4, "test")  # rare
        with pytest.raises(AppError):
            await card_service.merge_equipped(player_id)

    @pytest.mark.asyncio
    async def test_merge_legendary_fails(
        self, card_service: CardService, player_id: UUID
    ):
        # We need 3 legendary cards — use card_id 10 three times
        await card_service.grant_card(player_id, 10, "test")
        await card_service.grant_card(player_id, 10, "test")
        await card_service.grant_card(player_id, 10, "test")
        with pytest.raises(AppError):
            await card_service.merge_equipped(player_id)

    @pytest.mark.asyncio
    async def test_merge_clears_equipped(
        self, card_service: CardService, player_id: UUID
    ):
        await card_service.grant_card(player_id, 1, "test")
        await card_service.grant_card(player_id, 2, "test")
        await card_service.grant_card(player_id, 3, "test")

        await card_service.merge_equipped(player_id)

        # After merge, player should have 1 card (the new one at position 1)
        result = await card_service.get_player_cards(player_id)
        assert result.total == 1
        assert result.items[0].position == 1


# ---------------------------------------------------------------------------
# Tests: Remove
# ---------------------------------------------------------------------------


class TestRemove:
    """Tests for removing cards."""

    @pytest.mark.asyncio
    async def test_remove_card(self, card_service: CardService, player_id: UUID):
        card = await card_service.grant_card(player_id, 1, "test")
        await card_service.remove_card(player_id, card.id, "test_cleanup")

        result = await card_service.get_player_cards(player_id)
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_card_fails(
        self, card_service: CardService, player_id: UUID
    ):
        with pytest.raises(AppError):
            await card_service.remove_card(player_id, uuid4(), "test")
