# Module Architecture Report: player

**Module:** player
**Build Wave:** 1 (Leaf Node)
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The player module is the foundational account management module for ChromaCrush, managing player accounts, profiles, ELO ratings, statistics, and energy state data for both human and bot players. It provides GDPR-compliant soft delete with username release, case-insensitive username handling via a `username_lower` column, standard ELO calculation with configurable K-factor, and eager initialization of stats and energy state records at player creation. All public service methods are **asynchronous** (`async def`) with persistence through injected repository protocols.

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_player` | `(username, player_type, password_hash=None) -> Player` | Create a new player account |
| `get_player` | `(player_id) -> Player` | Get player by ID |
| `get_player_by_username` | `(username) -> Player \| None` | Case-insensitive username lookup |
| `update_player` | `(player_id, updates: PlayerUpdate) -> Player` | Update profile fields |
| `soft_delete_player` | `(player_id) -> None` | Soft-delete with username release |
| `list_players` | `(player_type=None, limit=50, offset=0) -> PaginatedResult[Player]` | List with optional filtering |
| `get_elo` | `(player_id) -> int` | Get current ELO rating |
| `update_elo` | `(player_id, new_rating) -> Player` | Update ELO rating |
| `calculate_elo_change` | `(winner_id, loser_id, is_draw=False) -> tuple[int, int]` | Calculate ELO changes (no persist) |
| `get_stats` | `(player_id) -> PlayerStats` | Get aggregate statistics |
| `record_match_result` | `(player_id, won, is_draw, score, longest_chain, gems_matched) -> PlayerStats` | Record match result in stats |
| `get_energy_state` | `(player_id) -> EnergyState` | Get raw energy state data |
| `update_energy_state` | `(player_id, energy_update: EnergyStateUpdate) -> EnergyState` | Update energy state fields |
| `initialize_energy_state` | `(player_id) -> EnergyState` | Initialize energy state for new player |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | ELO initial/K-factor, max hearts, username constraints |
| `logger` | `LoggerProtocol` | Structured logging |
| `errors` | `ErrorServiceProtocol` | Create validation, not_found, and conflict errors |
| `player_repo` | `PlayerRepositoryProtocol` | Player CRUD operations |
| `stats_repo` | `PlayerStatsRepositoryProtocol` | Player statistics CRUD |
| `energy_repo` | `EnergyStateRepositoryProtocol` | Energy state CRUD |

---

## 4. Data Owned

| Table | Storage | Description |
|-------|---------|-------------|
| `players` | PostgreSQL | Player accounts with UUID PK, username, username_lower, player_type, elo_rating, email, deleted_at |
| `player_stats` | PostgreSQL | Aggregate stats: total_matches, wins, losses, draws, highest_score, longest_chain, total_gems_matched |
| `energy_states` | PostgreSQL | Energy data: hearts, max_hearts, last_regen_at, daily_streak, last_login_date (shared ownership with energy module) |

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `matchmaking.elo_initial` | int | 1000 | Starting ELO rating for new players |
| `matchmaking.elo_k_factor` | int | 32 | ELO K-factor for rating calculations |
| `energy.max_hearts` | int | 5 | Maximum heart capacity for initialization |
| `player.username_min_length` | int | 3 | Minimum username length |
| `player.username_max_length` | int | 32 | Maximum username length |
| `player.username_pattern` | string | `^[a-zA-Z0-9_]+$` | Allowed username regex pattern |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_INVALID_INPUT` | 400 | Invalid username format, bot with password, negative ELO, invalid hearts, limit out of range, same player IDs |
| `NOT_FOUND_PLAYER` | 404 | Player ID does not exist or is soft-deleted |
| `CONFLICT_USERNAME_TAKEN` | 409 | Username already exists (case-insensitive) |

---

## 7. Cross-Module Interactions

**Called by:**
- `auth` -- uses `get_player_by_username()`, `get_player()` for authentication
- `energy` -- uses `get_energy_state()`, `update_energy_state()` for energy business logic
- `match` -- uses `get_player()`, `update_elo()`, `record_match_result()` for match lifecycle
- `matchmaking` -- uses `get_player()`, `get_elo()` for ELO-based pairing
- `vault`, `events`, `ads`, `payments`, `bot_earnings` -- read player data

**Calls:** No other modules. Player is a leaf node.

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `Player` | `src/core/types/player.py` | Core player entity (shared type) |
| `PlayerStats` | `src/core/types/player.py` | Aggregate statistics (shared type) |
| `EnergyState` | `src/core/types/player.py` | Energy state data (shared type) |
| `PlayerType` | `src/core/types/player.py` | Enum: HUMAN, BOT (shared type) |
| `PlayerUpdate` | `src/modules/player/dto.py` | DTO for profile update fields |
| `EnergyStateUpdate` | `src/modules/player/dto.py` | DTO for energy state update fields |
| `PaginatedResult[T]` | `src/modules/player/dto.py` | Generic paginated query result |
| `PlayerServiceProtocol` | `src/modules/player/protocols.py` | Protocol mirroring all 14 public methods for DI |
