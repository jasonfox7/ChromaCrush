# Module Architecture Report: vault

**Module:** vault
**Build Wave:** 3
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The vault module manages player artifact collections, raid mechanics between players, shield-based raid protection, and collection set tracking for ChromaCrush. It provides four subsystems: artifact management (CRUD for player-owned artifact instances), an artifact catalog (static definitions of artifact types with rarity and set membership), a shield system (one-per-player time-limited raid protection with lazy expiration cleanup), and a raid system (player-vs-player raids with eligibility checks, weighted random artifact selection favouring lower-rarity items, and probabilistic success determination). Additionally, a collection system tracks per-set completion progress via pure set-intersection functions. All 17 public service methods are **asynchronous** (`async def`) because every method involves at least one database operation through injected repository protocols. Three internal helper modules (`raid_engine.py`, `collection.py`) contain synchronous pure functions with no I/O.

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `add_artifact` | `(player_id, artifact_type_id, source, source_id?) -> VaultArtifact` | Add artifact instance to player vault |
| `get_artifact` | `(artifact_id) -> VaultArtifact` | Get artifact by ID |
| `get_player_artifacts` | `(player_id, rarity?, artifact_set?, limit?, offset?) -> PaginatedResult[VaultArtifact]` | List player artifacts with filters |
| `get_vault_summary` | `(player_id) -> VaultSummary` | Aggregate vault stats (totals, rarity counts, sets) |
| `remove_artifact` | `(artifact_id, reason) -> None` | Remove artifact from vault |
| `transfer_artifact` | `(artifact_id, from_player_id, to_player_id, reason) -> VaultArtifact` | Transfer artifact between players |
| `get_artifact_definition` | `(artifact_type_id) -> ArtifactDefinition` | Look up artifact catalog entry |
| `list_artifact_definitions` | `(rarity?, artifact_set?) -> list[ArtifactDefinition]` | List catalog with optional filters |
| `get_collection_progress` | `(player_id, artifact_set?) -> list[CollectionProgress]` | Set completion progress |
| `activate_shield` | `(player_id, duration_hours?) -> Shield` | Activate raid protection |
| `get_shield_status` | `(player_id) -> Shield or None` | Check active shield |
| `deactivate_shield` | `(player_id) -> None` | Remove active shield |
| `is_protected` | `(player_id) -> bool` | Check if player has active shield |
| `attempt_raid` | `(attacker_id, defender_id) -> RaidResult` | Execute raid attempt |
| `can_raid` | `(attacker_id, defender_id) -> RaidEligibility` | Check raid eligibility without acting |
| `get_raid_history` | `(player_id, as_attacker?, as_defender?, limit?, offset?) -> PaginatedResult[RaidLog]` | Paginated raid history |
| `get_raid_cooldown` | `(attacker_id, defender_id) -> datetime or None` | Get cooldown expiry between two players |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Read vault configuration keys at init |
| `logger` | `LoggerProtocol` | Structured diagnostic logging |
| `errors` | `ErrorServiceProtocol` | Create typed validation, not_found, conflict, forbidden, and internal errors |
| `player_service` | `PlayerServiceProtocol` | Verify player existence via `get_player()` |
| `vault_artifact_repo` | `VaultArtifactRepositoryProtocol` | CRUD and query for vault artifact records |
| `vault_shield_repo` | `VaultShieldRepositoryProtocol` | CRUD for shield records |
| `artifact_definition_repo` | `ArtifactDefinitionRepositoryProtocol` | Read operations for artifact catalog |
| `raid_log_repo` | `RaidLogRepositoryProtocol` | Create and query raid history |

---

## 4. Data Owned

| Table | Description |
|-------|-------------|
| `vault_artifacts` | Player-owned artifact instances (UUID PK, FK to players, artifact_type_id, source) |
| `vault_shields` | One-per-player shield records (player_id as PK + FK, activated_at, expires_at) |
| `artifact_definitions` | Static artifact catalog (String PK type_id, rarity, set, value) |
| `raid_logs` | Raid attempt audit trail (UUID PK, attacker/defender FKs, success, artifact reference) |

No Redis usage. All persistence is PostgreSQL via async SQLAlchemy repositories.

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `vault.shield_duration_hours` | int | 24 | Default shield protection duration |
| `vault.raid_cooldown_hours` | int | 4 | Hours between raids on same target |
| `vault.raid_energy_cost` | int | 2 | Hearts consumed per raid |
| `vault.raid_success_base_chance` | float | 0.5 | Base raid success probability |
| `vault.empty_vault_protection` | bool | true | Prevent raids on empty vaults |
| `vault.legendary_steal_chance_modifier` | float | 0.5 | Multiplier for legendary artifact steal chance |
| `vault.max_artifacts_per_player` | int | 100 | Maximum artifacts a player can hold |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_INVALID_INPUT` | 400 | Invalid type_id, vault full, invalid duration, self-raid, wrong owner, limit out of range |
| `NOT_FOUND_ARTIFACT` | 404 | Artifact or artifact definition not found |
| `NOT_FOUND_PLAYER` | 404 | Player does not exist (via player_service) |
| `INTERNAL_UNEXPECTED` | 500 | Definition missing for existing artifact (defensive) |
| `CONFLICT_SHIELD_ALREADY_ACTIVE` | 409 | Shield already exists for player |
| `FORBIDDEN_VAULT_PROTECTED` | 403 | Defender has active shield |
| `CONFLICT_RAID_COOLDOWN` | 409 | Raid cooldown not yet expired |

---

## 7. Cross-Module Interactions

**Called by:**
- `events` -- grants artifacts as event rewards via `add_artifact`
- `api` -- exposes vault endpoints (artifacts, shield, raid, collection)

**Calls:**
- `player` -- verifies player existence via `get_player()`

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `ArtifactRarity` | `src/modules/vault/dto.py` | Enum: COMMON, RARE, EPIC, LEGENDARY |
| `ArtifactDefinition` | `src/modules/vault/dto.py` | Frozen dataclass for catalog entries |
| `VaultArtifact` | `src/modules/vault/dto.py` | Player-owned artifact instance with definition |
| `VaultSummary` | `src/modules/vault/dto.py` | Aggregate vault statistics |
| `Shield` | `src/modules/vault/dto.py` | Active shield with expiry tracking |
| `RaidResult` | `src/modules/vault/dto.py` | Outcome of a raid attempt |
| `RaidEligibility` | `src/modules/vault/dto.py` | Pre-check result for raid eligibility |
| `CollectionProgress` | `src/modules/vault/dto.py` | Set completion tracking with owned/missing lists |
