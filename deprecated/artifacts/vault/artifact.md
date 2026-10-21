# Vault Module Artifact

> **Module:** vault
> **Author:** Scout Agent
> **Date:** 2026-02-05
> **Version:** 1.0
> **Status:** Draft
> **Build Wave:** 3 (depends on player)

---

## Dependencies

### Module Dependencies

| Module | Dependency Type | Interface Used |
|--------|-----------------|----------------|
| `player` | Direct | `PlayerServiceProtocol` — reads player data for vault ownership, raid eligibility |

### Core Service Dependencies

| Service | Injected Via | Usage |
|---------|--------------|-------|
| `ConfigProtocol` | `__init__` | Shield duration, raid cooldowns, energy costs, rarity weights |
| `LoggerProtocol` | `__init__` | Artifact acquisition, raids, shield activation |
| `ErrorServiceProtocol` | `__init__` | Validation errors, not found, forbidden (shield), conflict |
| `DataContext` | `__init__` | Database session management for all async operations |

### Repository Dependencies

| Repository | Ownership | Access Type |
|------------|-----------|-------------|
| `VaultArtifactRepository` | Owns | Read/Write |
| `VaultShieldRepository` | Owns | Read/Write |
| `ArtifactDefinitionRepository` | Owns | Read (static catalog, rarely written) |
| `RaidLogRepository` | Owns | Read/Write |
| `PlayerRepository` | Reads via player service | Read only (for raid eligibility checks) |

---

## 1. Purpose

The vault module manages the artifact collection and raid system in ChromaCrush. It provides:

1. **Artifact Management** — Storage and retrieval of player-owned artifacts with rarity tiers
2. **Vault Storage** — Each player has a personal vault holding their artifact collection
3. **Raid System** — Players can attempt to steal artifacts from other players' vaults
4. **Shield Protection** — Temporary immunity from raids with configurable duration
5. **Collection Tracking** — Track artifact sets and enable collection bonuses
6. **Raid History** — Log of raid attempts for cooldown enforcement and analytics

The vault module creates a loss-aversion engagement loop (risk of losing artifacts) balanced by shield mechanics, driving player retention and competitive behavior.

---

## 2. Public Interface

### 2.1 VaultService Protocol

```python
# src/modules/vault/protocols.py
from typing import Protocol
from uuid import UUID
from datetime import datetime

from src.core.types.game import PlayerId, ArtifactId
from src.core.types.vault import (
    VaultArtifact,
    ArtifactDefinition,
    ArtifactRarity,
    Shield,
    RaidResult,
    VaultSummary,
    CollectionProgress,
)


class VaultServiceProtocol(Protocol):
    """Public interface for the vault module."""

    # ========== Artifact Management ==========

    async def add_artifact(
        self,
        player_id: PlayerId,
        artifact_type_id: str,
        source: str,
        source_id: str | None = None,
    ) -> VaultArtifact:
        """
        Add an artifact to a player's vault.

        Args:
            player_id: The owner's player ID.
            artifact_type_id: The artifact type from the definition catalog.
            source: How acquired ("match_reward", "event_reward", "raid", "purchase").
            source_id: Optional reference (match_id, event_id, raid_id).

        Returns:
            The created VaultArtifact.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If artifact_type_id is not in catalog.

        Logs:
            INFO: "Artifact acquired" with player_id, artifact_type_id, rarity, source.
        """
        ...

    async def get_artifact(
        self,
        artifact_id: ArtifactId,
    ) -> VaultArtifact:
        """
        Get a specific artifact by ID.

        Args:
            artifact_id: The artifact's unique identifier.

        Returns:
            VaultArtifact entity.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact doesn't exist.
        """
        ...

    async def get_player_artifacts(
        self,
        player_id: PlayerId,
        rarity: ArtifactRarity | None = None,
        artifact_set: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> "PaginatedResult[VaultArtifact]":
        """
        Get all artifacts in a player's vault with optional filtering.

        Args:
            player_id: The vault owner.
            rarity: Filter by rarity tier (common, rare, epic, legendary).
            artifact_set: Filter by set name.
            limit: Maximum results (1-100, default 50).
            offset: Pagination offset.

        Returns:
            PaginatedResult containing artifacts and pagination metadata.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If limit out of range.
        """
        ...

    async def get_vault_summary(
        self,
        player_id: PlayerId,
    ) -> VaultSummary:
        """
        Get a summary of a player's vault contents.

        Args:
            player_id: The vault owner.

        Returns:
            VaultSummary with counts by rarity and total value.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def remove_artifact(
        self,
        artifact_id: ArtifactId,
        reason: str,
    ) -> None:
        """
        Remove an artifact from vault (internal use for raid transfers).

        Args:
            artifact_id: The artifact to remove.
            reason: Why removed ("raid_stolen", "admin_action", "collection_trade").

        Raises:
            NOT_FOUND_ARTIFACT: If artifact doesn't exist.

        Logs:
            INFO: "Artifact removed" with artifact_id, previous_owner, reason.
        """
        ...

    async def transfer_artifact(
        self,
        artifact_id: ArtifactId,
        from_player_id: PlayerId,
        to_player_id: PlayerId,
        reason: str,
    ) -> VaultArtifact:
        """
        Transfer an artifact between players atomically.

        Args:
            artifact_id: The artifact to transfer.
            from_player_id: Current owner (for verification).
            to_player_id: New owner.
            reason: Why transferred ("raid_stolen", "trade", "gift").

        Returns:
            Updated VaultArtifact with new owner.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact doesn't exist.
            NOT_FOUND_PLAYER: If either player doesn't exist.
            VALIDATION_INVALID_INPUT: If from_player_id doesn't match current owner.

        Logs:
            INFO: "Artifact transferred" with artifact_id, from_player, to_player, reason.
        """
        ...

    # ========== Artifact Catalog ==========

    async def get_artifact_definition(
        self,
        artifact_type_id: str,
    ) -> ArtifactDefinition:
        """
        Get the definition for an artifact type.

        Args:
            artifact_type_id: The type identifier.

        Returns:
            ArtifactDefinition with name, rarity, set, value, image.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact type not in catalog.
        """
        ...

    async def list_artifact_definitions(
        self,
        rarity: ArtifactRarity | None = None,
        artifact_set: str | None = None,
    ) -> list[ArtifactDefinition]:
        """
        List all artifact definitions with optional filtering.

        Args:
            rarity: Filter by rarity tier.
            artifact_set: Filter by set name.

        Returns:
            List of matching ArtifactDefinitions.
        """
        ...

    # ========== Collection System ==========

    async def get_collection_progress(
        self,
        player_id: PlayerId,
        artifact_set: str | None = None,
    ) -> list[CollectionProgress]:
        """
        Get player's progress toward completing artifact sets.

        Args:
            player_id: The player.
            artifact_set: Specific set to check, or None for all sets.

        Returns:
            List of CollectionProgress entries showing owned/total per set.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def check_set_complete(
        self,
        player_id: PlayerId,
        artifact_set: str,
    ) -> bool:
        """
        Check if a player has completed an artifact set.

        Args:
            player_id: The player.
            artifact_set: The set to check.

        Returns:
            True if all artifacts in the set are owned.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If set doesn't exist.
        """
        ...

    # ========== Shield System ==========

    async def activate_shield(
        self,
        player_id: PlayerId,
        duration_hours: int | None = None,
    ) -> Shield:
        """
        Activate raid protection shield for a player.

        Args:
            player_id: The player to protect.
            duration_hours: Override default duration (uses config default if None).

        Returns:
            Shield entity with expiration time.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            CONFLICT_SHIELD_ALREADY_ACTIVE: If player already has active shield.
            VALIDATION_INVALID_INPUT: If duration_hours <= 0.

        Logs:
            INFO: "Shield activated" with player_id, expires_at, duration_hours.
        """
        ...

    async def get_shield_status(
        self,
        player_id: PlayerId,
    ) -> Shield | None:
        """
        Get a player's current shield status.

        Args:
            player_id: The player.

        Returns:
            Active Shield if protected, None if unprotected.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def deactivate_shield(
        self,
        player_id: PlayerId,
    ) -> None:
        """
        Manually deactivate a player's shield.

        Args:
            player_id: The player.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If no active shield exists.

        Logs:
            INFO: "Shield deactivated" with player_id, reason="manual".
        """
        ...

    async def is_protected(
        self,
        player_id: PlayerId,
    ) -> bool:
        """
        Check if a player is currently protected by a shield.

        Args:
            player_id: The player to check.

        Returns:
            True if shield is active and not expired.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Raid System ==========

    async def attempt_raid(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> RaidResult:
        """
        Attempt to raid another player's vault.

        Consumes energy from attacker, checks defender's shield status,
        applies raid cooldown rules, and if successful, transfers a random
        artifact from defender to attacker.

        Args:
            attacker_id: The raiding player.
            defender_id: The target player.

        Returns:
            RaidResult with success status, stolen artifact (if any), and details.

        Raises:
            NOT_FOUND_PLAYER: If either player doesn't exist.
            VALIDATION_INVALID_INPUT: If attacker == defender.
            FORBIDDEN_VAULT_PROTECTED: If defender has active shield.
            FORBIDDEN_INSUFFICIENT_ENERGY: If attacker lacks raid energy.
            CONFLICT_RAID_COOLDOWN: If raided same player too recently.

        Logs:
            INFO: "Raid attempted" with attacker_id, defender_id, success, artifact_id.
        """
        ...

    async def can_raid(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> "RaidEligibility":
        """
        Check if a raid is possible (without executing).

        Args:
            attacker_id: The potential attacker.
            defender_id: The potential target.

        Returns:
            RaidEligibility with can_raid bool and reason if not.

        Raises:
            NOT_FOUND_PLAYER: If either player doesn't exist.
        """
        ...

    async def get_raid_history(
        self,
        player_id: PlayerId,
        as_attacker: bool = True,
        as_defender: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> "PaginatedResult[RaidLog]":
        """
        Get raid history for a player.

        Args:
            player_id: The player.
            as_attacker: Include raids where player was attacker.
            as_defender: Include raids where player was defender.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            PaginatedResult containing raid log entries.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def get_raid_cooldown(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> datetime | None:
        """
        Get when the cooldown expires for raiding a specific player.

        Args:
            attacker_id: The attacker.
            defender_id: The target.

        Returns:
            Cooldown expiration datetime, or None if no cooldown.

        Raises:
            NOT_FOUND_PLAYER: If either player doesn't exist.
        """
        ...
```

### 2.2 Data Transfer Objects

```python
# src/modules/vault/dto.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar
from uuid import UUID

from src.core.types.game import PlayerId, ArtifactId

T = TypeVar("T")


class ArtifactRarity(Enum):
    """Artifact rarity tiers."""
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass(frozen=True)
class ArtifactDefinition:
    """
    Static definition of an artifact type from the catalog.
    """
    type_id: str
    name: str
    description: str
    rarity: ArtifactRarity
    artifact_set: str
    set_position: int  # Position within set (1, 2, 3...)
    base_value: int  # Value points for scoring
    image_url: str | None = None


@dataclass
class VaultArtifact:
    """
    An artifact instance owned by a player.
    """
    id: ArtifactId
    owner_id: PlayerId
    artifact_type_id: str
    definition: ArtifactDefinition
    acquired_at: datetime
    source: str  # How acquired
    source_id: str | None  # Reference to match/event/raid


@dataclass
class VaultSummary:
    """
    Summary of a player's vault contents.
    """
    player_id: PlayerId
    total_artifacts: int
    by_rarity: dict[ArtifactRarity, int]
    total_value: int
    complete_sets: list[str]
    sets_in_progress: list[str]


@dataclass
class Shield:
    """
    Active raid protection shield.
    """
    player_id: PlayerId
    activated_at: datetime
    expires_at: datetime
    duration_hours: int

    @property
    def is_active(self) -> bool:
        return datetime.utcnow() < self.expires_at

    @property
    def remaining_seconds(self) -> int:
        if not self.is_active:
            return 0
        return int((self.expires_at - datetime.utcnow()).total_seconds())


@dataclass
class RaidResult:
    """
    Result of a raid attempt.
    """
    raid_id: UUID
    attacker_id: PlayerId
    defender_id: PlayerId
    success: bool
    stolen_artifact: VaultArtifact | None
    timestamp: datetime
    message: str  # Human-readable outcome


@dataclass
class RaidEligibility:
    """
    Result of raid eligibility check.
    """
    can_raid: bool
    reason: str | None = None
    cooldown_expires_at: datetime | None = None


@dataclass
class RaidLog:
    """
    Historical record of a raid.
    """
    raid_id: UUID
    attacker_id: PlayerId
    defender_id: PlayerId
    success: bool
    artifact_id: ArtifactId | None
    artifact_type_id: str | None
    timestamp: datetime


@dataclass
class CollectionProgress:
    """
    Progress toward completing an artifact set.
    """
    artifact_set: str
    set_name: str
    total_in_set: int
    owned_count: int
    owned_type_ids: list[str]
    missing_type_ids: list[str]

    @property
    def is_complete(self) -> bool:
        return self.owned_count >= self.total_in_set

    @property
    def completion_percent(self) -> float:
        if self.total_in_set == 0:
            return 100.0
        return (self.owned_count / self.total_in_set) * 100


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated query result."""
    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total
```

---

## 3. Mandatory Service Usage

### 3.1 Configuration Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `vault.shield_duration_hours` | int | 8 | Default shield duration in hours |
| `vault.raid_cooldown_hours` | int | 24 | Hours before same player can be raided again |
| `vault.raid_energy_cost` | int | 1 | Hearts consumed per raid attempt |
| `vault.raid_success_base_chance` | float | 0.7 | Base probability of successful raid (0.0-1.0) |
| `vault.empty_vault_protection` | bool | true | Protect players with empty vaults from raids |
| `vault.legendary_steal_chance_modifier` | float | 0.5 | Multiplier for chance to steal legendary (lower = rarer) |
| `vault.max_artifacts_per_player` | int | 500 | Maximum artifacts a player can hold |

### 3.2 Logging Events

| Level | Event | Context Fields | When |
|-------|-------|----------------|------|
| INFO | "Artifact acquired" | `player_id`, `artifact_type_id`, `rarity`, `source` | After artifact added to vault |
| INFO | "Artifact removed" | `artifact_id`, `previous_owner`, `reason` | After artifact removed from vault |
| INFO | "Artifact transferred" | `artifact_id`, `from_player`, `to_player`, `reason` | After artifact ownership changes |
| INFO | "Shield activated" | `player_id`, `expires_at`, `duration_hours` | After shield activated |
| INFO | "Shield deactivated" | `player_id`, `reason` | After shield ends (manual or expired) |
| INFO | "Raid attempted" | `attacker_id`, `defender_id`, `success`, `artifact_id` | After raid attempt completes |
| DEBUG | "Raid eligibility check" | `attacker_id`, `defender_id`, `can_raid`, `reason` | During can_raid checks |
| WARN | "Raid blocked by shield" | `attacker_id`, `defender_id`, `shield_expires_at` | When raid blocked by active shield |
| WARN | "Raid blocked by cooldown" | `attacker_id`, `defender_id`, `cooldown_expires_at` | When raid blocked by cooldown |

### 3.3 Error Types Used

| Error Code | HTTP | When Raised |
|------------|------|-------------|
| `VALIDATION_INVALID_INPUT` | 400 | Invalid artifact type, invalid duration, self-raid attempt |
| `NOT_FOUND_PLAYER` | 404 | Player ID doesn't exist |
| `NOT_FOUND_ARTIFACT` | 404 | Artifact ID doesn't exist |
| `FORBIDDEN_VAULT_PROTECTED` | 403 | Defender has active shield |
| `FORBIDDEN_INSUFFICIENT_ENERGY` | 403 | Attacker lacks raid energy (delegates to energy module) |
| `CONFLICT_SHIELD_ALREADY_ACTIVE` | 409 | Attempting to activate shield when one exists |
| `CONFLICT_RAID_COOLDOWN` | 409 | Attempting to raid same player within cooldown |

---

## 4. Data Access

### 4.1 Owned Data

The vault module owns these database tables:

#### `vault_artifacts` Table

```sql
CREATE TABLE vault_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES players(id),
    artifact_type_id VARCHAR(64) NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(32) NOT NULL,  -- 'match_reward', 'event_reward', 'raid', 'purchase'
    source_id VARCHAR(64),  -- Reference to source entity
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_vault_artifacts_owner ON vault_artifacts(owner_id);
CREATE INDEX idx_vault_artifacts_type ON vault_artifacts(artifact_type_id);
CREATE INDEX idx_vault_artifacts_source ON vault_artifacts(source);
```

#### `vault_shields` Table

```sql
CREATE TABLE vault_shields (
    player_id UUID PRIMARY KEY REFERENCES players(id),
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    duration_hours INTEGER NOT NULL
);

CREATE INDEX idx_vault_shields_expires ON vault_shields(expires_at);
```

#### `artifact_definitions` Table

```sql
CREATE TABLE artifact_definitions (
    type_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    rarity VARCHAR(16) NOT NULL,  -- 'common', 'rare', 'epic', 'legendary'
    artifact_set VARCHAR(64) NOT NULL,
    set_position INTEGER NOT NULL,
    base_value INTEGER NOT NULL DEFAULT 100,
    image_url VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_artifact_definitions_rarity ON artifact_definitions(rarity);
CREATE INDEX idx_artifact_definitions_set ON artifact_definitions(artifact_set);
```

#### `raid_logs` Table

```sql
CREATE TABLE raid_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attacker_id UUID NOT NULL REFERENCES players(id),
    defender_id UUID NOT NULL REFERENCES players(id),
    success BOOLEAN NOT NULL,
    artifact_id UUID REFERENCES vault_artifacts(id),
    artifact_type_id VARCHAR(64),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_raid_logs_attacker ON raid_logs(attacker_id, timestamp DESC);
CREATE INDEX idx_raid_logs_defender ON raid_logs(defender_id, timestamp DESC);
CREATE INDEX idx_raid_logs_cooldown ON raid_logs(attacker_id, defender_id, timestamp DESC);
```

### 4.2 Repository Interfaces

```python
# src/data/protocols/vault_repository.py
from typing import Protocol
from uuid import UUID
from datetime import datetime

from src.core.types.game import PlayerId, ArtifactId
from src.modules.vault.dto import ArtifactRarity


class VaultArtifactRepository(Protocol):
    """Repository interface for vault artifacts."""

    async def find_by_id(self, artifact_id: UUID) -> "VaultArtifactRecord | None":
        ...

    async def find_by_owner(
        self,
        owner_id: UUID,
        rarity: str | None = None,
        artifact_set: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list["VaultArtifactRecord"], int]:
        """Returns (items, total_count)."""
        ...

    async def count_by_owner(self, owner_id: UUID) -> int:
        ...

    async def count_by_owner_and_rarity(self, owner_id: UUID) -> dict[str, int]:
        """Returns counts grouped by rarity."""
        ...

    async def find_by_owner_and_type(
        self,
        owner_id: UUID,
        artifact_type_id: str,
    ) -> "VaultArtifactRecord | None":
        """Find if owner has a specific artifact type."""
        ...

    async def list_owned_type_ids(
        self,
        owner_id: UUID,
        artifact_set: str | None = None,
    ) -> list[str]:
        """List all artifact type IDs owned by player."""
        ...

    async def create(self, data: "VaultArtifactCreate") -> "VaultArtifactRecord":
        ...

    async def update_owner(
        self,
        artifact_id: UUID,
        new_owner_id: UUID,
    ) -> "VaultArtifactRecord":
        ...

    async def delete(self, artifact_id: UUID) -> None:
        ...

    async def get_random_artifact(
        self,
        owner_id: UUID,
        exclude_legendary: bool = False,
    ) -> "VaultArtifactRecord | None":
        """Get a random artifact from owner's vault for raid selection."""
        ...


class VaultShieldRepository(Protocol):
    """Repository interface for vault shields."""

    async def find_by_player(self, player_id: UUID) -> "VaultShieldRecord | None":
        ...

    async def create(self, data: "VaultShieldCreate") -> "VaultShieldRecord":
        ...

    async def delete(self, player_id: UUID) -> None:
        ...

    async def delete_expired(self) -> int:
        """Delete all expired shields, returns count deleted."""
        ...


class ArtifactDefinitionRepository(Protocol):
    """Repository interface for artifact catalog."""

    async def find_by_type_id(self, type_id: str) -> "ArtifactDefinitionRecord | None":
        ...

    async def list_all(
        self,
        rarity: str | None = None,
        artifact_set: str | None = None,
    ) -> list["ArtifactDefinitionRecord"]:
        ...

    async def list_by_set(self, artifact_set: str) -> list["ArtifactDefinitionRecord"]:
        ...

    async def get_set_type_ids(self, artifact_set: str) -> list[str]:
        """Get all type IDs in a set."""
        ...

    async def list_all_sets(self) -> list[str]:
        """List all unique artifact set names."""
        ...


class RaidLogRepository(Protocol):
    """Repository interface for raid history."""

    async def create(self, data: "RaidLogCreate") -> "RaidLogRecord":
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        as_attacker: bool = True,
        as_defender: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list["RaidLogRecord"], int]:
        ...

    async def find_last_raid_between(
        self,
        attacker_id: UUID,
        defender_id: UUID,
    ) -> "RaidLogRecord | None":
        """Find most recent raid from attacker to defender."""
        ...
```

### 4.3 Data Read from Other Modules

| Module | Data Read | Method |
|--------|-----------|--------|
| `player` | Player existence, player type | `PlayerServiceProtocol.get_player()` |
| `energy` | Energy balance for raid cost | Energy module's `consume_energy()` called during raid |

### 4.4 Transaction Requirements

| Operation | Transaction Scope | Notes |
|-----------|-------------------|-------|
| `add_artifact` | Single transaction | Simple insert |
| `transfer_artifact` | Single transaction | Update owner atomically |
| `attempt_raid` | Single transaction | Create raid log + optionally transfer artifact |
| `activate_shield` | Single transaction | Insert/replace shield record |
| Other operations | Single transaction | Simple reads or updates |

---

## 5. Presentation Boundary

### 5.1 What This Module Returns

The vault module returns domain objects (`VaultArtifact`, `Shield`, `RaidResult`, `VaultSummary`, `CollectionProgress`) and DTOs (`PaginatedResult`). It does NOT return:
- JSON objects
- HTTP responses
- Formatted strings for display
- Error response dictionaries

### 5.2 Presentation Layer Responsibility

The presentation layer (`src/presentation/adapters/vault_adapter.py`) handles:
- Converting `VaultArtifact` to `VaultArtifactResponse` (formatting dates, image URLs)
- Converting `RaidResult` to `RaidResultResponse` (hiding internal IDs where appropriate)
- Formatting shield countdown timers
- Calculating human-readable time strings ("2 hours remaining")
- Selecting which fields to expose based on viewer (e.g., don't show defender's artifact details until raid succeeds)

### 5.3 Example Boundary

```python
# Module returns domain object
raid_result = await vault_service.attempt_raid(attacker_id, defender_id)
# raid_result is a RaidResult dataclass

# Adapter converts for API
response = vault_adapter.to_raid_response(raid_result, for_player_id=attacker_id)
# response is RaidResultResponse Pydantic model for JSON serialization
```

---

## 6. Internal Design

### 6.1 Service Implementation Structure

```
src/modules/vault/
    __init__.py           # Exports VaultService, protocols
    service.py            # VaultService implementation
    protocols.py          # VaultServiceProtocol
    dto.py                # All DTOs and enums
    raid_engine.py        # Raid probability and selection logic
    collection.py         # Collection tracking helpers
```

### 6.2 Component Diagram

```
                    VaultService
                         │
        ┌────────────────┼────────────────────────┐
        │                │                        │
        ▼                ▼                        ▼
  VaultArtifact    VaultShield           ArtifactDefinition
   Repository       Repository              Repository
        │                │                        │
        └────────────────┼────────────────────────┘
                         │
                         ▼
                    RaidLog
                   Repository
                         │
                         ▼
                   DataContext
                   (PostgreSQL)

External Dependencies:
  ┌─────────────┐
  │   player    │ ◄── VaultService reads player data
  │   module    │     via PlayerServiceProtocol
  └─────────────┘
```

### 6.3 Raid Engine Logic

```python
# src/modules/vault/raid_engine.py
import random
from datetime import datetime, timedelta

def calculate_raid_success(
    base_chance: float,
    target_artifact_rarity: str,
    legendary_modifier: float,
) -> bool:
    """
    Determine if a raid attempt succeeds.

    Args:
        base_chance: Base success probability (from config).
        target_artifact_rarity: Rarity of selected artifact.
        legendary_modifier: Multiplier for legendary items.

    Returns:
        True if raid succeeds.
    """
    effective_chance = base_chance
    if target_artifact_rarity == "legendary":
        effective_chance *= legendary_modifier

    return random.random() < effective_chance


def select_raid_target_artifact(
    artifacts: list["VaultArtifactRecord"],
    rng: random.Random | None = None,
) -> "VaultArtifactRecord | None":
    """
    Select which artifact the raider will attempt to steal.

    Uses weighted random selection favoring lower rarity items
    to make legendary theft rare.

    Weights:
    - common: 4
    - rare: 3
    - epic: 2
    - legendary: 1

    Args:
        artifacts: Available artifacts in defender's vault.
        rng: Optional seeded RNG for testing.

    Returns:
        Selected artifact, or None if vault is empty.
    """
    if not artifacts:
        return None

    if rng is None:
        rng = random.Random()

    RARITY_WEIGHTS = {
        "common": 4,
        "rare": 3,
        "epic": 2,
        "legendary": 1,
    }

    weighted = []
    for artifact in artifacts:
        weight = RARITY_WEIGHTS.get(artifact.rarity, 1)
        weighted.extend([artifact] * weight)

    return rng.choice(weighted)


def is_raid_on_cooldown(
    last_raid_timestamp: datetime | None,
    cooldown_hours: int,
) -> tuple[bool, datetime | None]:
    """
    Check if raid cooldown is still active.

    Args:
        last_raid_timestamp: When the last raid occurred.
        cooldown_hours: Cooldown duration from config.

    Returns:
        Tuple of (is_on_cooldown, cooldown_expires_at or None).
    """
    if last_raid_timestamp is None:
        return False, None

    cooldown_expires = last_raid_timestamp + timedelta(hours=cooldown_hours)
    now = datetime.utcnow()

    if now < cooldown_expires:
        return True, cooldown_expires

    return False, None
```

### 6.4 Collection Tracking

```python
# src/modules/vault/collection.py

async def calculate_collection_progress(
    owned_type_ids: list[str],
    set_type_ids: list[str],
    set_name: str,
    artifact_set: str,
) -> "CollectionProgress":
    """
    Calculate progress toward completing an artifact set.

    Args:
        owned_type_ids: Type IDs the player owns in this set.
        set_type_ids: All type IDs in the set.
        set_name: Display name of the set.
        artifact_set: Set identifier.

    Returns:
        CollectionProgress instance.
    """
    owned_set = set(owned_type_ids)
    total_set = set(set_type_ids)

    return CollectionProgress(
        artifact_set=artifact_set,
        set_name=set_name,
        total_in_set=len(total_set),
        owned_count=len(owned_set & total_set),
        owned_type_ids=list(owned_set & total_set),
        missing_type_ids=list(total_set - owned_set),
    )
```

---

## 7. CLI Surface

### 7.1 Commands

```bash
# Artifact management
chromacrush vault list <player-id> [--rarity common|rare|epic|legendary] [--set <set-name>]
chromacrush vault summary <player-id>
chromacrush vault add <player-id> <artifact-type-id> --source <source>
chromacrush vault get <artifact-id>
chromacrush vault transfer <artifact-id> <from-player-id> <to-player-id>

# Artifact catalog
chromacrush vault catalog [--rarity common|rare|epic|legendary] [--set <set-name>]
chromacrush vault catalog-show <artifact-type-id>

# Collections
chromacrush vault collection <player-id> [--set <set-name>]
chromacrush vault collection-check <player-id> <set-name>

# Shields
chromacrush vault shield-status <player-id>
chromacrush vault shield-activate <player-id> [--hours N]
chromacrush vault shield-deactivate <player-id>

# Raids
chromacrush vault raid <attacker-id> <defender-id>
chromacrush vault can-raid <attacker-id> <defender-id>
chromacrush vault raid-history <player-id> [--as-attacker] [--as-defender]
chromacrush vault raid-cooldown <attacker-id> <defender-id>
```

### 7.2 CLI Command Implementation Example

```python
# src/cli/commands/vault_commands.py
import click
from uuid import UUID

@click.group()
def vault():
    """Vault and artifact management commands."""
    pass

@vault.command()
@click.argument("player_id")
@click.option("--rarity", type=click.Choice(["common", "rare", "epic", "legendary"]))
@click.option("--set", "artifact_set", help="Filter by set name")
@click.pass_context
async def list(ctx, player_id: str, rarity: str | None, artifact_set: str | None):
    """List artifacts in a player's vault."""
    vault_service = ctx.obj["vault_service"]

    rarity_enum = ArtifactRarity(rarity) if rarity else None
    result = await vault_service.get_player_artifacts(
        player_id=PlayerId(UUID(player_id)),
        rarity=rarity_enum,
        artifact_set=artifact_set,
    )

    click.echo(f"Vault contents for player {player_id[:8]}...")
    click.echo(f"  Total: {result.total}")
    for artifact in result.items:
        click.echo(f"  - {artifact.definition.name} ({artifact.definition.rarity.value})")
        click.echo(f"    ID: {artifact.id}")
        click.echo(f"    Set: {artifact.definition.artifact_set}")

@vault.command()
@click.argument("player_id")
@click.pass_context
async def summary(ctx, player_id: str):
    """Get vault summary for a player."""
    vault_service = ctx.obj["vault_service"]

    summary = await vault_service.get_vault_summary(PlayerId(UUID(player_id)))

    click.echo(f"Vault summary for player {player_id[:8]}...")
    click.echo(f"  Total artifacts: {summary.total_artifacts}")
    click.echo(f"  By rarity:")
    for rarity, count in summary.by_rarity.items():
        click.echo(f"    {rarity.value}: {count}")
    click.echo(f"  Total value: {summary.total_value}")
    click.echo(f"  Complete sets: {', '.join(summary.complete_sets) or 'None'}")

@vault.command()
@click.argument("attacker_id")
@click.argument("defender_id")
@click.pass_context
async def raid(ctx, attacker_id: str, defender_id: str):
    """Attempt to raid another player's vault."""
    vault_service = ctx.obj["vault_service"]

    result = await vault_service.attempt_raid(
        attacker_id=PlayerId(UUID(attacker_id)),
        defender_id=PlayerId(UUID(defender_id)),
    )

    click.echo(f"Raid result:")
    click.echo(f"  Success: {result.success}")
    click.echo(f"  Message: {result.message}")
    if result.stolen_artifact:
        click.echo(f"  Stolen: {result.stolen_artifact.definition.name}")
        click.echo(f"  Rarity: {result.stolen_artifact.definition.rarity.value}")

@vault.command("shield-status")
@click.argument("player_id")
@click.pass_context
async def shield_status(ctx, player_id: str):
    """Check shield status for a player."""
    vault_service = ctx.obj["vault_service"]

    shield = await vault_service.get_shield_status(PlayerId(UUID(player_id)))

    if shield is None:
        click.echo(f"Player {player_id[:8]}... has no active shield.")
    else:
        click.echo(f"Player {player_id[:8]}... shield status:")
        click.echo(f"  Active: {shield.is_active}")
        click.echo(f"  Expires: {shield.expires_at}")
        click.echo(f"  Remaining: {shield.remaining_seconds // 3600}h {(shield.remaining_seconds % 3600) // 60}m")

@vault.command("shield-activate")
@click.argument("player_id")
@click.option("--hours", type=int, help="Duration in hours (uses config default if not specified)")
@click.pass_context
async def shield_activate(ctx, player_id: str, hours: int | None):
    """Activate shield protection for a player."""
    vault_service = ctx.obj["vault_service"]

    shield = await vault_service.activate_shield(
        player_id=PlayerId(UUID(player_id)),
        duration_hours=hours,
    )

    click.echo(f"Shield activated for player {player_id[:8]}...")
    click.echo(f"  Expires: {shield.expires_at}")
    click.echo(f"  Duration: {shield.duration_hours} hours")
```

---

## 8. Edge Cases & Decisions

### 8.1 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Artifact ownership model | One artifact instance per player | Simpler than shared ownership; each acquisition creates a new instance |
| Raid target selection | Weighted random favoring common | Legendary theft should be rare and exciting, not guaranteed |
| Shield stacking | Not allowed | Prevents indefinite protection; one shield at a time |
| Empty vault protection | Configurable | Prevents griefing new players, but can be disabled |
| Cooldown scope | Per attacker-defender pair | Player A can raid B once per cooldown, but can raid C immediately |
| Artifact catalog | Database table | More flexible than config file; supports admin additions |
| Collection completion | No automatic reward | Events module handles granting set bonuses |
| Raid energy cost | Consumes from player energy | Creates resource tradeoff between playing matches and raiding |

### 8.2 Edge Cases

| Scenario | Handling |
|----------|----------|
| Raid when defender vault is empty | Raid fails with "Vault is empty" message (if empty_vault_protection enabled) |
| Raid when attacker has no energy | Reject with FORBIDDEN_INSUFFICIENT_ENERGY |
| Shield activated during active shield | Reject with CONFLICT_SHIELD_ALREADY_ACTIVE |
| Artifact type not in catalog | Reject add_artifact with VALIDATION_INVALID_INPUT |
| Transfer artifact to non-existent player | Reject with NOT_FOUND_PLAYER |
| Self-raid attempt | Reject with VALIDATION_INVALID_INPUT |
| Raid blocked by shield | Reject with FORBIDDEN_VAULT_PROTECTED, include expires_at in error |
| Player reaches max artifact limit | Reject new artifact with VALIDATION_INVALID_INPUT |
| Concurrent raids on same defender | Database transaction isolation handles this; only one succeeds |
| Artifact in deleted player's vault | Artifacts remain; admin cleanup process needed (not in scope) |

### 8.3 Escalation Required

None. All edge cases are covered by existing error taxonomy and guidance.

---

## 9. Async Behavior Summary

All public methods are `async def` because they involve database operations. This module follows the async contract:

- All repository calls are awaited
- No fire-and-forget operations
- Transaction boundaries managed via DataContext
- Errors propagate correctly through async chain
- Player service calls are awaited (cross-module async)

---

## 10. Open Questions

None. All design decisions have been resolved based on:
- Feasibility report specifications
- Interface contracts guidance
- Data layer guidance
- Player module artifact (dependency)
- Dispatch instructions from Orchestrator

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent |
