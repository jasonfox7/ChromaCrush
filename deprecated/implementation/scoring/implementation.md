# Scoring Module Implementation Document

**Module:** scoring
**Phase:** 2.2
**Author:** Coding Agent
**Date:** 2026-02-05

---

## 1. Summary

The scoring module is a pure, synchronous score calculation engine for the ChromaCrush match-3 game. It computes points earned from match-3 actions by taking match results from the board module and applying base points, match-length multipliers, cascade chain multipliers, and special gem bonuses. All methods are regular `def` (not `async def`) and perform pure arithmetic on in-memory data structures with no I/O. Dependencies (config, logger, error service) are injected via `__init__`.

---

## 2. Files Created

### Module Code (`src/modules/scoring/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Package init; exports `ScoringService` and all five result types (`CascadeStepScore`, `MatchGroupScore`, `MatchScore`, `MoveScore`, `SpecialGemBonus`) |
| `types.py` | Frozen dataclass definitions for all scoring result types: `MatchGroupScore`, `MatchScore`, `SpecialGemBonus`, `CascadeStepScore`, `MoveScore` (with a `summary()` method) |
| `service.py` | `ScoringService` class containing all score calculation logic, config validation, and multiplier lookups |

### Data Layer (`src/data/`)
| File | Purpose |
|------|---------|
| None | This module has no persistence layer. All computation is pure and in-memory. |

### CLI (`src/cli/commands/`)
| File | Purpose |
|------|---------|
| `scoring_commands.py` | Click CLI group with three commands: `calculate-match` (detect matches on a board JSON and score them), `show-multipliers` (display current scoring configuration tables), `special-gem-bonus` (calculate activation bonus for a specified special gem type) |

### Tests (`tests/unit/modules/scoring/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Empty package init |
| `test_scoring_service.py` | 54 test functions across 8 test classes covering match scoring, move scoring, special gem bonuses, multiplier lookups, configuration, base points, summary text, and combined/integration-like scenarios |

---

## 3. Deviations from Artifact

Not assessed -- document produced from code examination only.

---

## 4. Public Interface

### `ScoringService` (class in `service.py`)

**Constructor:**
```python
def __init__(
    self,
    config: ConfigProtocol,
    logger: LoggerProtocol,
    errors: ErrorServiceProtocol,
) -> None
```

**Public Methods:**

```python
def calculate_match_score(
    self, match_result: MatchResult, chain_step: int = 1
) -> MatchScore
```
Calculates score for a single match detection result. Validates that `match_result.matches` is non-empty and `chain_step >= 1`. Scores each match group with base points and length multiplier, applies chain multiplier to the aggregate, and adds special gem creation bonus if applicable. Raises `AppError` with code `VALIDATION_INVALID_INPUT` on invalid inputs.

```python
def calculate_move_score(self, move_result: MoveProcessingResult) -> MoveScore
```
Calculates complete score for a player's move. Iterates through all cascade steps calling `calculate_match_score` with incrementing chain step numbers. Aggregates totals for points, gems cleared, special gems created, and tracks highest chain multiplier. Validates `move_result.was_valid_match` is `True`. Note: `special_gem_bonuses` on each `CascadeStepScore` is always an empty tuple -- special gem activation scoring is noted as being coordinated by the match module. Raises `AppError` with code `VALIDATION_INVALID_INPUT` if the move was invalid.

```python
def calculate_special_gem_bonus(
    self, gem_type: GemType, gems_affected: int
) -> SpecialGemBonus
```
Calculates bonus points from special gem activation. Routes to different base bonus and per-gem values depending on gem type (`LINE_BLAST_H`/`LINE_BLAST_V`, `RADIAL_BOMB`, `CHROMATIC_ORB`). Validates that `gem_type` is in `_SPECIAL_GEM_TYPES` and `gems_affected >= 0`. Raises `AppError` with code `VALIDATION_INVALID_INPUT` on invalid inputs.

```python
def get_chain_multiplier(self, chain_step: int) -> float
```
Looks up the chain multiplier for a given cascade step number. Index is `min(chain_step - 1, len(chain_multipliers) - 1)`, capping at the last entry. Validates `chain_step >= 1`. Raises `AppError` with code `VALIDATION_INVALID_INPUT` if `chain_step < 1`.

```python
def get_match_length_multiplier(self, match_length: int) -> float
```
Looks up the length multiplier for a given match length. Index is `min(match_length - 3, len(length_multipliers) - 1)`, capping at the last entry. Validates `match_length >= 3`. Raises `AppError` with code `VALIDATION_INVALID_INPUT` if `match_length < 3`.

```python
def get_base_points(self, gem_type: GemType) -> int
```
Returns the configured base points value for a standard gem type (values 1-6: RED through ORANGE). All standard gems return the same value. Validates that `gem_type` is in `_STANDARD_GEM_TYPES`. Raises `AppError` with code `VALIDATION_INVALID_INPUT` for non-standard gem types (EMPTY or special gems).

### Result Types (all frozen dataclasses in `types.py`)

**`MatchGroupScore`**
- `match_group: MatchGroup` -- the match group being scored
- `base_points: int` -- raw points (base_points_per_gem * length)
- `length_multiplier: float` -- multiplier from match length
- `length_bonus_points: int` -- additional points from length multiplier
- `subtotal: int` -- final points for this group (base_points * length_multiplier)

**`MatchScore`**
- `total_points: int` -- final score after chain multiplier and bonuses
- `base_points: int` -- sum of all group subtotals before chain multiplier
- `chain_multiplier: float` -- multiplier for cascade chain step
- `chain_step: int` -- which cascade step this was calculated for
- `match_breakdown: tuple[MatchGroupScore, ...]` -- per-group breakdown
- `special_gem_creation_bonus: int` -- bonus for creating a special gem

**`SpecialGemBonus`**
- `gem_type: GemType` -- the special gem type activated
- `base_activation_bonus: int` -- flat bonus for activation
- `gems_affected: int` -- number of gems cleared
- `per_gem_bonus: int` -- points per gem affected
- `total_bonus: int` -- base_activation_bonus + (gems_affected * per_gem_bonus)

**`CascadeStepScore`**
- `step_number: int` -- 1-based cascade step index
- `match_score: MatchScore` -- score from match detection in this step
- `special_gem_bonuses: tuple[SpecialGemBonus, ...]` -- bonuses from special gems activated

**`MoveScore`**
- `total_points: int` -- sum of all cascade step scores
- `cascade_scores: tuple[CascadeStepScore, ...]` -- per-step breakdown
- `chain_count: int` -- number of cascade steps
- `total_gems_cleared: int` -- total gems cleared across all cascades
- `highest_chain_multiplier: float` -- peak chain multiplier reached
- `special_gems_created: int` -- count of special gems created
- `special_gems_activated: int` -- count of special gems activated
- `def summary(self) -> str` -- human-readable summary (e.g., "Single match! +150 points", "Double chain! +375 points | 1 special gem(s) created")

---

## 5. Dependencies Injected

| Parameter | Protocol Type | Usage |
|-----------|--------------|-------|
| `config` | `ConfigProtocol` (from `src.core.protocols.config`) | Read scoring parameters at init time; all config values cached as instance attributes |
| `logger` | `LoggerProtocol` (from `src.core.protocols.logger`) | Structured diagnostic logging at TRACE, DEBUG, and WARN levels |
| `errors` | `ErrorServiceProtocol` (from `src.core.protocols.error_service`) | Factory for creating typed `AppError` instances (only `errors.validation()` is used) |

The service also imports concrete types (not services) directly:
- `MatchResult` from `src.core.types.board`
- `GemType` from `src.core.types.game`
- `MoveProcessingResult` from `src.modules.board.types`
- All scoring result types from `src.modules.scoring.types`

---

## 6. Configuration Keys Used

All configuration keys are read once during `__init__` and cached as instance attributes. Invalid values (non-numeric, non-positive, wrong type) fall back to defaults with a warning logged.

| Key | Default | Type | Description |
|-----|---------|------|-------------|
| `scoring.base_points` | `50` | `int` | Points per gem in a match |
| `scoring.chain_multipliers` | `[1.0, 1.5, 2.0, 2.5, 3.0]` | `list[float]` | Multiplier for each cascade step (index 0 = step 1); last value caps all higher steps |
| `scoring.length_multipliers` | `[1.0, 2.0, 3.0, 4.0, 5.0]` | `list[float]` | Multiplier for match length (index 0 = 3-match); last value caps all longer matches |
| `scoring.special_gem_creation_bonus` | `100` | `int` | Flat bonus for creating a special gem |
| `scoring.line_blast_activation_bonus` | `50` | `int` | Base activation bonus for LINE_BLAST_H/V |
| `scoring.line_blast_per_gem` | `25` | `int` | Per-gem bonus for LINE_BLAST_H/V |
| `scoring.radial_bomb_activation_bonus` | `100` | `int` | Base activation bonus for RADIAL_BOMB |
| `scoring.radial_bomb_per_gem` | `30` | `int` | Per-gem bonus for RADIAL_BOMB |
| `scoring.chromatic_orb_activation_bonus` | `200` | `int` | Base activation bonus for CHROMATIC_ORB |
| `scoring.chromatic_orb_per_gem` | `40` | `int` | Per-gem bonus for CHROMATIC_ORB |

---

## 7. Error Codes Used

| Code | Method(s) |
|------|-----------|
| `VALIDATION_INVALID_INPUT` | `calculate_match_score` (empty matches, chain_step < 1), `calculate_move_score` (invalid move), `calculate_special_gem_bonus` (non-special gem type, negative gems_affected), `get_chain_multiplier` (chain_step < 1), `get_match_length_multiplier` (match_length < 3), `get_base_points` (non-standard gem type) |

Only `errors.validation()` is used throughout the module. No other error factory methods (`not_found`, `unauthorized`, `conflict`, etc.) are called.

---

## 8. Async Behavior

All methods in `ScoringService` are synchronous `def` (not `async def`). The service performs pure arithmetic on in-memory data structures with no I/O, no database access, no network calls, and no background tasks. This is explicitly documented in the module and class docstrings.

The CLI commands are also fully synchronous -- no async bridge or event loop is needed.

---

## 9. Internal Design Notes

### Configuration Validation at Init Time
All configuration values are read and validated in `__init__` using two private helper methods:
- `_validate_positive_int(value, key, default)` -- validates a value is a positive integer; falls back to default with a warning if invalid (non-numeric, zero, or negative).
- `_validate_multiplier_list(value, key, default)` -- validates a value is a non-empty list of positive floats; falls back to default with a warning if invalid (not a list, empty, contains non-numeric values, or contains non-positive values).

This "validate once at construction" pattern means config errors are detected early and all subsequent calculations use validated cached values without repeated config lookups.

### Multiplier Lookup Pattern
Both chain multipliers and length multipliers use the same indexing pattern: `min(input - offset, len(list) - 1)`. This ensures that values beyond the list's range are capped at the last entry rather than raising an index error. For chain multipliers, `offset = 1` (step 1 maps to index 0). For length multipliers, `offset = 3` (a 3-match maps to index 0).

### Score Calculation Formula
For a single match group:
1. `group_base = base_points * match_group.length`
2. `length_mult = length_multipliers[min(length - 3, len - 1)]`
3. `subtotal = int(group_base * length_mult)`

For a match detection:
1. Sum all group subtotals to get `total_base`
2. Apply chain multiplier: `int(total_base * chain_multiplier)`
3. Add special gem creation bonus (flat, not multiplied by chain)

For a full move:
1. Iterate cascade steps, scoring each with incrementing chain step
2. Aggregate totals across all cascade steps

### Special Gem Bonus Calculation
`total_bonus = base_activation_bonus + (gems_affected * per_gem_bonus)` where base and per-gem values differ by gem type (LINE_BLAST_H and LINE_BLAST_V share the same values).

### Module-Level Constants
Two `frozenset` constants are defined at module level for validation:
- `_SPECIAL_GEM_TYPES`: `{GemType.LINE_BLAST_H, LINE_BLAST_V, RADIAL_BOMB, CHROMATIC_ORB}`
- `_STANDARD_GEM_TYPES`: `{GemType.RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE}`

### Incomplete Special Gem Activation Scoring in `calculate_move_score`
In the `calculate_move_score` method, `special_gem_bonuses` on each `CascadeStepScore` is always set to an empty tuple `()`. A code comment states: "activation scoring is coordinated by match module." The `special_gems_activated` counter on `MoveScore` always remains at `0`. The method `calculate_special_gem_bonus` exists and is fully implemented, but it is never called from within `calculate_move_score`. This suggests that special gem activation bonus integration is deferred to the match module's orchestration layer.

### Logging Strategy
The service uses structured logging at three levels:
- **TRACE**: Per-match-group multiplier application details (high-frequency, step-level)
- **DEBUG**: Service initialization, per-match scoring totals, per-move totals, special gem bonuses
- **WARN**: Input validation failures, invalid config values falling back to defaults

All log events use dot-notation event names prefixed with `scoring.` (e.g., `scoring.service_initialized`, `scoring.match_scored`, `scoring.validation_failed`, `scoring.config_invalid`).

### CLI Design
The CLI creates its own service instances via two helper functions (`_make_scoring_service`, `_make_board_service`) that instantiate concrete services from a TOML config path. The `calculate-match` command requires a `BoardService` from the board module to perform match detection before scoring. Uses Rich library for colored terminal output and formatted tables.

### Type Immutability
All five result types (`MatchGroupScore`, `MatchScore`, `SpecialGemBonus`, `CascadeStepScore`, `MoveScore`) are frozen dataclasses, ensuring thread safety and preventing accidental mutation. The test suite explicitly verifies this immutability with `pytest.raises(AttributeError)` checks.
