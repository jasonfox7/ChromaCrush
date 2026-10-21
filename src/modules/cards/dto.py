"""Data Transfer Objects for the cards module.

Defines card definitions, player card instances, equipped loadouts,
and merge results. No database awareness -- pure data carriers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

T = TypeVar("T")


@dataclass(frozen=True)
class CardDefinition:
    """Static definition of a card type from the catalog."""

    card_id: int
    name: str
    description: str
    rarity: str  # "common" | "rare" | "epic" | "legendary"
    card_set: str
    set_position: int
    base_value: int
    tags: list[str]

    # Card modifier system fields (Phase A).
    trigger: str = "passive"
    effect: str = ""
    effect_params: dict = field(default_factory=dict)
    trigger_condition: dict | None = None


@dataclass(frozen=True)
class PlayerCard:
    """A card instance owned by a player."""

    id: UUID
    player_id: UUID
    card_id: int
    definition: CardDefinition
    position: int  # 1-3 = equipped, 4+ = vault
    level: int
    acquired_at: datetime
    source: str
    source_id: str | None = None


@dataclass(frozen=True)
class EquippedLoadout:
    """The cards currently equipped in a player's slots (max 3)."""

    player_id: UUID
    cards: list[PlayerCard]  # max 3, sorted by position


@dataclass(frozen=True)
class MergeResult:
    """Result of merging 3 equipped cards into a higher-tier card."""

    consumed_card_ids: list[UUID]
    new_card: PlayerCard
    source_rarity: str
    target_rarity: str
