# Player Module Implementation Document

**Module:** player
**Phase:** 2.2
**Author:** Coding Agent
**Date:** 2026-02-05

---

## 1. Summary

The player module has been implemented as specified in the artifact (`docs/artifacts/player/artifact.md`). All public methods are `async def`. Dependencies are injected via `__init__`. No direct service instantiation, environment access, bare raises, or raw data access exists in the module code.

## 2. Files Created

### Module Code (`src/modules/player/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Exports `PlayerService` and `PlayerServiceProtocol` |
| `protocols.py` | `PlayerServiceProtocol` — full async protocol interface |
| `dto.py` | `PlayerUpdate`, `EnergyStateUpdate`, `PaginatedResult[T]` |
| `elo.py` | `calculate_expected_score`, `calculate_elo_change` (pure sync) |
| `validation.py` | `validate_username` (pure sync) |
| `service.py` | `PlayerService` — full async implementation |

### Data Layer (`src/data/`)
| File | Purpose |
|------|---------|
| `models/player_stats.py` | `PlayerStatsModel` ORM (player_stats table) |
| `models/energy_state.py` | `EnergyStateModel` ORM (energy_states table) |
| `models/player.py` | Extended with `username_lower`, `email`, `deleted_at` columns |
| `protocols/player_stats_repository.py` | `PlayerStatsRepositoryProtocol` |
| `protocols/energy_state_repository.py` | `EnergyStateRepositoryProtocol` |
| `protocols/player_repository.py` | Extended with `list_players` method |
| `repositories/player_stats_repository.py` | `SQLAlchemyPlayerStatsRepository` |
| `repositories/energy_state_repository.py` | `SQLAlchemyEnergyStateRepository` |
| `repositories/player_repository.py` | Extended with `list_players` implementation |
| `migrations/versions/002_player_stats_and_energy.py` | Migration 002 |

### CLI (`src/cli/commands/`)
| File | Purpose |
|------|---------|
| `player_commands.py` | Click group with create/get/list/stats/elo/calc-elo/energy |

### Tests (`tests/unit/modules/player/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Package marker |
| `test_elo.py` | 13 ELO calculation tests |
| `test_validation.py` | 14 username validation tests |
| `test_player_service.py` | 27 async service tests with mock repos |

## 3. Deviations from Artifact

| Area | Artifact Spec | Implementation | Justification |
|------|--------------|----------------|---------------|
| `create_player` password_hash | "Required for humans" | Optional for humans | Per task instructions: allow `password_hash=None` for CLI/testing; auth module handles real auth |
| PlayerRepository protocol | Not shown with `list_players` | Added `list_players` method | Required for `list_players` service method; protocol extended in-place |

## 4. Configuration Keys Used

All keys from artifact Section 3.1 are read in `PlayerService.__init__`:
- `matchmaking.elo_initial` (default 1000)
- `matchmaking.elo_k_factor` (default 32)
- `energy.max_hearts` (default 5)
- `player.username_min_length` (default 3)
- `player.username_max_length` (default 32)
- `player.username_pattern` (default `^[a-zA-Z0-9_]+$`)

## 5. Error Codes Used

| Code | Method(s) |
|------|-----------|
| `VALIDATION_INVALID_INPUT` | create_player, update_player, update_elo, update_energy_state, list_players, calculate_elo_change |
| `NOT_FOUND_PLAYER` | get_player, get_stats, get_energy_state, calculate_elo_change |
| `CONFLICT_USERNAME_TAKEN` | create_player, update_player |

## 6. Async Behavior

All public service methods are `async def`. No fire-and-forget operations. All repository calls are awaited. Transaction boundaries are managed by the repository implementations via `DataContext.session()`.
