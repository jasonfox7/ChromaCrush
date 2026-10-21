# Vault Module Implementation Document

**Module:** vault
**Phase:** 2.2
**Author:** Coding Agent
**Date:** 2026-02-05

---

## 1. Summary

The vault module manages player artifact collections, raid mechanics between players, shield-based raid protection, and collection tracking for artifact sets. It is built around four subsystems:

1. **Artifact Management** -- Adding, retrieving, listing, removing, and transferring artifact instances owned by players. Artifacts are typed entries referencing a static catalog of artifact definitions.
2. **Artifact Catalog** -- Reading and filtering the static catalog of artifact definitions (type_id, name, rarity, set membership, value).
3. **Shield System** -- One-per-player time-limited raid protection. Shields are created with an expiration time and automatically cleaned up when queried after expiration.
4. **Raid System** -- Player-vs-player raid attempts with eligibility checks (self-raid prevention, shield protection, cooldown enforcement, empty vault protection), weighted random artifact selection favouring lower-rarity items, and probabilistic success determination with a legendary modifier.

Additionally, a **Collection System** tracks per-set completion progress using pure functions that calculate set intersection between owned artifact type IDs and set membership.

All public service methods are `async def`. The module uses `__init__` dependency injection exclusively -- no direct core service imports or environment access.

---

## 2. Files Created

### Module Code (`src/modules/vault/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Package init; re-exports all DTOs, `VaultService`, and `VaultServiceProtocol` via `__all__` |
| `dto.py` | Data Transfer Objects: `ArtifactRarity` enum, `ArtifactDefinition`, `VaultArtifact`, `VaultSummary`, `Shield`, `RaidResult`, `RaidEligibility`, `RaidLog`, `CollectionProgress`, `PaginatedResult[T]` |
| `protocols.py` | `VaultServiceProtocol` -- typing.Protocol defining the full public interface (17 async methods) |
| `service.py` | `VaultService` -- concrete implementation of all 17 public methods plus 3 static helper methods |
| `raid_engine.py` | Pure functions: `calculate_raid_success`, `select_raid_target_artifact`, `is_raid_on_cooldown`; plus `RARITY_WEIGHTS` constant dict |
| `collection.py` | Pure function: `calculate_collection_progress` for set completion tracking |

### Data Layer (`src/data/`)

| File | Purpose |
|------|---------|
| `models/vault_artifact.py` | `VaultArtifactModel` -- SQLAlchemy ORM model for `vault_artifacts` table (UUID PK, FK to players, artifact_type_id, acquired_at, source, source_id, created_at) |
| `models/vault_shield.py` | `VaultShieldModel` -- SQLAlchemy ORM model for `vault_shields` table (player_id UUID as PK + FK to players, activated_at, expires_at, duration_hours) |
| `models/artifact_definition.py` | `ArtifactDefinitionModel` -- SQLAlchemy ORM model for `artifact_definitions` table (type_id String PK, name, description, rarity, artifact_set, set_position, base_value, image_url, created_at) |
| `models/raid_log.py` | `RaidLogModel` -- SQLAlchemy ORM model for `raid_logs` table (UUID PK, attacker_id/defender_id FKs to players, success bool, artifact_id FK nullable, artifact_type_id nullable, timestamp) |
| `protocols/vault_artifact_repository.py` | `VaultArtifactRepositoryProtocol` -- Protocol with 9 async methods for vault artifact persistence |
| `protocols/vault_shield_repository.py` | `VaultShieldRepositoryProtocol` -- Protocol with 4 async methods for shield persistence |
| `protocols/artifact_definition_repository.py` | `ArtifactDefinitionRepositoryProtocol` -- Protocol with 5 async methods for artifact catalog |
| `protocols/raid_log_repository.py` | `RaidLogRepositoryProtocol` -- Protocol with 3 async methods for raid history |
| `repositories/vault_artifact_repository.py` | `SQLAlchemyVaultArtifactRepository` + `VaultArtifactRecord` dataclass -- concrete implementation with joined queries for rarity/set filtering, count by owner, count by rarity, create/update_owner/delete, random artifact selection |
| `repositories/vault_shield_repository.py` | `SQLAlchemyVaultShieldRepository` + `VaultShieldRecord` dataclass -- concrete implementation with create/find/delete/delete_expired |
| `repositories/artifact_definition_repository.py` | `SQLAlchemyArtifactDefinitionRepository` + `ArtifactDefinitionRecord` dataclass -- concrete implementation with find_by_type_id, list_all (with filters), list_by_set, get_set_type_ids, list_all_sets |
| `repositories/raid_log_repository.py` | `SQLAlchemyRaidLogRepository` + `RaidLogRecord` dataclass -- concrete implementation with create, find_by_player (with attacker/defender filtering), find_last_raid_between |
| `migrations/versions/004_vault_tables.py` | Alembic migration creating 4 tables: `artifact_definitions`, `vault_artifacts`, `vault_shields`, `raid_logs` with appropriate FKs, indexes, and server defaults |

### CLI (`src/cli/commands/`)

| File | Purpose |
|------|---------|
| `vault_commands.py` | Click CLI group `vault` with 10 commands: `list`, `summary`, `add`, `get`, `catalog`, `shield-status`, `shield-activate`, `raid`, `can-raid`, `raid-history`. Uses Rich tables for output. Bridges sync Click to async service via `asyncio.run()`. |

### Tests (`tests/unit/modules/vault/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Empty package init |
| `test_vault_service.py` | 44 async tests covering all VaultService methods: add_artifact (4), get_artifact (2), get_player_artifacts (3), get_vault_summary (1), remove_artifact (2), transfer_artifact (2), shield operations (9), raid operations (6), can_raid (5), raid_history (2), raid_cooldown (2), collection_progress (2), artifact_catalog (3). Uses in-memory mock repositories and pytest-asyncio. |
| `test_raid_engine.py` | 23 sync tests for pure raid functions: calculate_raid_success (9), select_raid_target_artifact (7), is_raid_on_cooldown (7). Uses `unittest.mock.patch` for deterministic random testing and seeded `random.Random` for weighted selection. |
| `test_collection.py` | 10 sync tests for `calculate_collection_progress`: empty set, no owned, partial, complete, extra items ignored, duplicates, field storage, single-item set (complete/missing), large set. |

---

## 3. Deviations from Artifact

Not assessed -- document produced from code examination only.

---

## 4. Public Interface

### `VaultServiceProtocol` / `VaultService`

All methods are `async def`.

**Artifact Management:**

```python
async def add_artifact(
    self,
    player_id: PlayerId,
    artifact_type_id: str,
    source: str,
    source_id: str | None = None,
) -> VaultArtifact

async def get_artifact(
    self,
    artifact_id: ArtifactId,
) -> VaultArtifact

async def get_player_artifacts(
    self,
    player_id: PlayerId,
    rarity: ArtifactRarity | None = None,
    artifact_set: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedResult[VaultArtifact]

async def get_vault_summary(
    self,
    player_id: PlayerId,
) -> VaultSummary

async def remove_artifact(
    self,
    artifact_id: ArtifactId,
    reason: str,
) -> None

async def transfer_artifact(
    self,
    artifact_id: ArtifactId,
    from_player_id: PlayerId,
    to_player_id: PlayerId,
    reason: str,
) -> VaultArtifact
```

**Artifact Catalog:**

```python
async def get_artifact_definition(
    self,
    artifact_type_id: str,
) -> ArtifactDefinition

async def list_artifact_definitions(
    self,
    rarity: ArtifactRarity | None = None,
    artifact_set: str | None = None,
) -> list[ArtifactDefinition]
```

**Collection System:**

```python
async def get_collection_progress(
    self,
    player_id: PlayerId,
    artifact_set: str | None = None,
) -> list[CollectionProgress]
```

**Shield System:**

```python
async def activate_shield(
    self,
    player_id: PlayerId,
    duration_hours: int | None = None,
) -> Shield

async def get_shield_status(
    self,
    player_id: PlayerId,
) -> Shield | None

async def deactivate_shield(
    self,
    player_id: PlayerId,
) -> None

async def is_protected(
    self,
    player_id: PlayerId,
) -> bool
```

**Raid System:**

```python
async def attempt_raid(
    self,
    attacker_id: PlayerId,
    defender_id: PlayerId,
) -> RaidResult

async def can_raid(
    self,
    attacker_id: PlayerId,
    defender_id: PlayerId,
) -> RaidEligibility

async def get_raid_history(
    self,
    player_id: PlayerId,
    as_attacker: bool = True,
    as_defender: bool = True,
    limit: int = 20,
    offset: int = 0,
) -> PaginatedResult[RaidLog]

async def get_raid_cooldown(
    self,
    attacker_id: PlayerId,
    defender_id: PlayerId,
) -> datetime | None
```

**Static Helper Methods (on VaultService only, not in protocol):**

```python
@staticmethod
def _record_to_definition(record: object) -> ArtifactDefinition

@staticmethod
def _record_to_vault_artifact(record: object, definition: ArtifactDefinition) -> VaultArtifact

@staticmethod
def _record_to_shield(record: object) -> Shield
```

### Pure Functions (`raid_engine.py`)

```python
def calculate_raid_success(
    base_chance: float,
    target_artifact_rarity: str,
    legendary_modifier: float,
) -> bool

def select_raid_target_artifact(
    artifacts: list[object],
    rng: random.Random | None = None,
) -> object | None

def is_raid_on_cooldown(
    last_raid_timestamp: datetime | None,
    cooldown_hours: int,
) -> tuple[bool, datetime | None]
```

### Pure Functions (`collection.py`)

```python
def calculate_collection_progress(
    owned_type_ids: list[str],
    set_type_ids: list[str],
    set_name: str,
    artifact_set: str,
) -> CollectionProgress
```

### DTOs (`dto.py`)

```python
class ArtifactRarity(Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

@dataclass(frozen=True)
class ArtifactDefinition:
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
    id: ArtifactId
    owner_id: PlayerId
    artifact_type_id: str
    definition: ArtifactDefinition
    acquired_at: datetime
    source: str
    source_id: str | None

@dataclass
class VaultSummary:
    player_id: PlayerId
    total_artifacts: int
    by_rarity: dict[ArtifactRarity, int]
    total_value: int
    complete_sets: list[str]
    sets_in_progress: list[str]

@dataclass
class Shield:
    player_id: PlayerId
    activated_at: datetime
    expires_at: datetime
    duration_hours: int
    # Properties: is_active -> bool, remaining_seconds -> int

@dataclass
class RaidResult:
    raid_id: UUID
    attacker_id: PlayerId
    defender_id: PlayerId
    success: bool
    stolen_artifact: VaultArtifact | None
    timestamp: datetime
    message: str

@dataclass
class RaidEligibility:
    can_raid: bool
    reason: str | None = None
    cooldown_expires_at: datetime | None = None

@dataclass
class RaidLog:
    raid_id: UUID
    attacker_id: PlayerId
    defender_id: PlayerId
    success: bool
    artifact_id: ArtifactId | None
    artifact_type_id: str | None
    timestamp: datetime

@dataclass
class CollectionProgress:
    artifact_set: str
    set_name: str
    total_in_set: int
    owned_count: int
    owned_type_ids: list[str]
    missing_type_ids: list[str]
    # Properties: is_complete -> bool, completion_percent -> float

@dataclass
class PaginatedResult(Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    # Property: has_more -> bool
```

---

## 5. Dependencies Injected

### `VaultService.__init__`

| Parameter | Protocol Type | Purpose |
|-----------|---------------|---------|
| `config` | `ConfigProtocol` | Reading vault configuration keys |
| `logger` | `LoggerProtocol` | Structured logging (info, warn, debug) |
| `errors` | `ErrorServiceProtocol` | Error factory for validation, not_found, conflict, forbidden, internal |
| `player_service` | `PlayerServiceProtocol` | Player existence verification via `get_player()` |
| `vault_artifact_repo` | `VaultArtifactRepositoryProtocol` | CRUD and query operations for vault artifact records |
| `vault_shield_repo` | `VaultShieldRepositoryProtocol` | CRUD operations for shield records |
| `artifact_definition_repo` | `ArtifactDefinitionRepositoryProtocol` | Read operations for artifact catalog |
| `raid_log_repo` | `RaidLogRepositoryProtocol` | Create and query operations for raid history |

### Repository Implementations (each)

| Parameter | Protocol Type |
|-----------|---------------|
| `data_ctx` | `DataContextProtocol` |
| `logger` | `LoggerProtocol` |
| `errors` | `ErrorServiceProtocol` |

---

## 6. Configuration Keys Used

All read at `VaultService.__init__` time via `self._config.get(key, default)`:

| Config Key | Default Value | Type | Purpose |
|------------|---------------|------|---------|
| `vault.shield_duration_hours` | `8` | `int` | Default shield duration when not overridden by caller |
| `vault.raid_cooldown_hours` | `24` | `int` | Hours between raids on the same target |
| `vault.raid_energy_cost` | `1` | `int` | Energy cost per raid (stored but not consumed by vault service directly) |
| `vault.raid_success_base_chance` | `0.7` | `float` | Base probability of a raid succeeding (0.0-1.0) |
| `vault.empty_vault_protection` | `True` | `bool` | Whether empty vaults automatically cause raid failure |
| `vault.legendary_steal_chance_modifier` | `0.5` | `float` | Multiplier applied to base chance when targeting legendary artifacts |
| `vault.max_artifacts_per_player` | `500` | `int` | Maximum artifacts a player can hold; used for capacity check and as limit when fetching all artifacts |

---

## 7. Error Codes Used

| Code | Method(s) | Error Type |
|------|-----------|------------|
| `VALIDATION_INVALID_INPUT` | `add_artifact` (invalid type_id, vault full), `get_player_artifacts` (invalid limit), `transfer_artifact` (wrong owner), `activate_shield` (invalid duration), `deactivate_shield` (no active shield / expired shield), `attempt_raid` (self-raid) | `errors.validation()` |
| `NOT_FOUND_ARTIFACT` | `get_artifact`, `remove_artifact`, `transfer_artifact`, `get_artifact_definition` | `errors.not_found()` |
| `NOT_FOUND_PLAYER` | `add_artifact`, `get_vault_summary`, `get_collection_progress`, `activate_shield`, `attempt_raid` (both players), `get_raid_history` -- raised by `player_service.get_player()` | via `PlayerServiceProtocol` |
| `INTERNAL_UNEXPECTED` | `get_artifact` (definition missing for existing artifact), `transfer_artifact` (definition missing after transfer) | `errors.internal()` |
| `CONFLICT_SHIELD_ALREADY_ACTIVE` | `activate_shield` | `errors.conflict()` |
| `FORBIDDEN_VAULT_PROTECTED` | `attempt_raid` | `errors.forbidden()` |
| `CONFLICT_RAID_COOLDOWN` | `attempt_raid` | `errors.conflict()` |
| `NOT_FOUND_RESOURCE` | `vault_shield_repository.delete` (shield not found) | `errors.not_found()` (in repository) |

---

## 8. Async Behavior

All 17 public methods on `VaultService` are `async def`. This is because every public method involves at least one repository call that performs database I/O through the async SQLAlchemy session context manager (`async with self._data_ctx.session()`).

The three pure helper modules (`raid_engine.py`, `collection.py`) are synchronous. They are called from within async service methods but perform no I/O.

The CLI commands bridge synchronous Click to async service methods using `asyncio.run()` via the `_run_async()` helper function, which creates a full `ApplicationContext`, builds the `VaultService`, runs the coroutine, and ensures proper shutdown.

Repository methods are all `async def` and use `async with self._data_ctx.session() as session:` for session scoping.

---

## 9. Internal Design Notes

### Raid Engine Architecture

The raid logic is split into pure functions in `raid_engine.py` and orchestration in `VaultService.attempt_raid`:

1. **Eligibility checks** are performed sequentially: self-raid, player existence, shield protection, cooldown, empty vault.
2. **Artifact selection** uses weighted random: artifacts are expanded into a weighted list where `common` gets weight 4, `rare` gets 3, `epic` gets 2, `legendary` gets 1. A random choice is made from the expanded list. This favours stealing lower-rarity items.
3. **Success calculation** uses a base chance (default 0.7) that is multiplied by the legendary modifier (default 0.5) only when the targeted artifact is legendary. All other rarities use the unmodified base chance.
4. On success, the artifact's owner is changed via `vault_artifact_repo.update_owner()` and a raid log is created with the artifact ID. On failure, only the raid log is created.

### Shield Lazy Cleanup

Expired shields are not cleaned up by a background process. Instead, `get_shield_status` checks expiration when queried and deletes the shield record if expired. `activate_shield` also cleans up expired shield records before creating new ones. `deactivate_shield` handles the case where a shield exists but is expired by cleaning up and then raising `VALIDATION_INVALID_INPUT`.

### Collection Progress Calculation

Collection progress is a pure set intersection operation. `calculate_collection_progress` takes all owned type IDs (which may include IDs from other sets) and the set's type IDs, computes the intersection to find owned-in-set, and the difference to find missing. The function returns sorted lists for deterministic output.

### Record-to-DTO Mapping Pattern

The service uses three static helper methods (`_record_to_definition`, `_record_to_vault_artifact`, `_record_to_shield`) that accept generic `object` parameters and access attributes by name. This decouples the service from specific repository record types. The repositories return lightweight `@dataclass` records (e.g., `VaultArtifactRecord`, `VaultShieldRecord`) rather than ORM models.

### Enrichment Pattern for Raid Artifact Selection

In `attempt_raid`, defender artifacts are fetched from the repository, then each record is enriched with a `rarity` attribute by looking up its definition. The `rarity` attribute is set dynamically on the record object (`rec.rarity = rarity_str`). This enriched list is then passed to `select_raid_target_artifact`, which reads the `rarity` attribute via `getattr`.

### Vault Capacity Enforcement

Before adding an artifact, the service checks `count_by_owner` against `_max_artifacts_per_player` (default 500). This is also used as the `limit` parameter when fetching all artifacts for summary calculations and raid target selection, ensuring all artifacts are retrieved.

### Pagination

`get_player_artifacts` and `get_raid_history` return `PaginatedResult[T]` with `items`, `total`, `limit`, and `offset`. Limit validation in `get_player_artifacts` enforces 1-100 range.

### CLI Wiring

The CLI commands file (`vault_commands.py`) contains a `_build_vault_service` helper that manually constructs all required repositories and the `PlayerService` dependency from the `ApplicationContext`. This includes inline imports of `SQLAlchemyEnergyStateRepository` and `SQLAlchemyPlayerStatsRepository` to satisfy `PlayerService`'s dependencies without circular imports.

### Database Schema Notes

- `vault_shields` uses `player_id` as both primary key and foreign key to `players`, enforcing one shield per player at the database level.
- `artifact_definitions` uses a `String(64)` primary key (`type_id`) rather than UUID.
- `raid_logs` has a composite index on `(attacker_id, defender_id, timestamp DESC)` for efficient cooldown lookups.
- `vault_artifacts` does not have a foreign key to `artifact_definitions`; the relationship is maintained by convention through the `artifact_type_id` string column.

### Logger Usage

The service uses three log levels:
- `self._logger.info()` for significant state changes: artifact acquired, artifact removed, artifact transferred, shield activated, shield deactivated, raid attempted.
- `self._logger.warn()` for blocked operations: raid blocked by shield, raid blocked by cooldown.
- `self._logger.debug()` for eligibility checks in `can_raid`.

### Config Caching

All seven configuration values are read once during `__init__` and cached as instance attributes. This means configuration changes require service restart to take effect.
