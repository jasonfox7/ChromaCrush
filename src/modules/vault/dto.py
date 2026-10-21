"""Data Transfer Objects for the vault module.

Defines artifact rarity, definitions, vault artifacts, shields,
raid results, collection progress, and pagination. No database
awareness -- pure data carriers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Generic, TypeVar
from uuid import UUID

from src.core.types.game import ArtifactId, PlayerId

T = TypeVar("T")


class ArtifactRarity(Enum):
    """Artifact rarity tiers."""

    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass(frozen=True)
class ArtifactDefinition:
    """Static definition of an artifact type from the catalog."""

    type_id: str
    name: str
    description: str
    rarity: ArtifactRarity
    artifact_set: str
    set_position: int
    base_value: int
    image_url: str | None = None


@dataclass
class VaultArtifact:
    """An artifact instance owned by a player."""

    id: ArtifactId
    owner_id: PlayerId
    artifact_type_id: str
    definition: ArtifactDefinition
    acquired_at: datetime
    source: str
    source_id: str | None


@dataclass
class VaultSummary:
    """Summary of a player's vault contents."""

    player_id: PlayerId
    total_artifacts: int
    by_rarity: dict[ArtifactRarity, int]
    total_value: int
    complete_sets: list[str]
    sets_in_progress: list[str]


@dataclass
class Shield:
    """Active raid protection shield."""

    player_id: PlayerId
    activated_at: datetime
    expires_at: datetime
    duration_hours: int

    @property
    def is_active(self) -> bool:
        """Return True if shield has not yet expired."""
        return datetime.now(timezone.utc) < self.expires_at

    @property
    def remaining_seconds(self) -> int:
        """Return seconds until shield expires, or 0 if expired."""
        if not self.is_active:
            return 0
        return int((self.expires_at - datetime.now(timezone.utc)).total_seconds())


@dataclass
class RaidResult:
    """Result of a raid attempt."""

    raid_id: UUID
    attacker_id: PlayerId
    defender_id: PlayerId
    success: bool
    stolen_artifact: VaultArtifact | None
    timestamp: datetime
    message: str


@dataclass
class RaidEligibility:
    """Result of raid eligibility check."""

    can_raid: bool
    reason: str | None = None
    cooldown_expires_at: datetime | None = None


@dataclass
class RaidLog:
    """Historical record of a raid."""

    raid_id: UUID
    attacker_id: PlayerId
    defender_id: PlayerId
    success: bool
    artifact_id: ArtifactId | None
    artifact_type_id: str | None
    timestamp: datetime


@dataclass
class CollectionProgress:
    """Progress toward completing an artifact set."""

    artifact_set: str
    set_name: str
    total_in_set: int
    owned_count: int
    owned_type_ids: list[str]
    missing_type_ids: list[str]

    @property
    def is_complete(self) -> bool:
        """Return True if the set is fully collected."""
        return self.owned_count >= self.total_in_set

    @property
    def completion_percent(self) -> float:
        """Return completion as a percentage (0.0-100.0)."""
        if self.total_in_set == 0:
            return 100.0
        return (self.owned_count / self.total_in_set) * 100


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated query result with metadata."""

    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        """Return True if there are more items beyond the current page."""
        return self.offset + len(self.items) < self.total
