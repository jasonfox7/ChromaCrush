# Special Gems Module Implementation Document

**Module:** special_gems
**Phase:** 2.2
**Author:** Coding Agent
**Date:** 2026-02-05

---

## 1. Summary

The special_gems module is a pure, synchronous effect calculation engine for ChromaCrush's special gem system. It handles four special gem types (LINE_BLAST_H, LINE_BLAST_V, RADIAL_BOMB, CHROMATIC_ORB) and provides logic for:

- Checking whether a gem type is special
- Calculating activation effects (which positions are cleared, bonus scores, chain-reaction triggers)
- Calculating fusion effects when two adjacent special gems combine (6 fusion types)
- Applying calculated effects to a board state (producing a new board with cleared positions)
- Determining which special gem should be created from a match result (3-match, 4-match, 5-match, T/L-shape)
- Finding triggered special gems within a set of cleared positions (chain reactions)

All methods are synchronous `def` (not `async def`). The service performs pure computation on in-memory data with no I/O.

---

## 2. Files Created

### Module Code (`src/modules/special_gems/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Package init; exports `SpecialGemsService`, `SpecialGemsServiceProtocol`, `SpecialGemEffect`, `FusionEffect`, `FusionType`, `SPECIAL_GEM_TYPES` |
| `types.py` | Frozen dataclasses (`SpecialGemEffect`, `FusionEffect`), enums (`FusionType`), and constants (`SPECIAL_GEM_TYPES`, `STANDARD_GEM_TYPES`) |
| `protocols.py` | `typing.Protocol` interfaces: `SpecialGemsServiceProtocol` (consumed by dependent modules) and `ScoringServiceProtocol` (minimal scoring interface required by this module) |
| `service.py` | `SpecialGemsService` -- the concrete implementation with all public API methods and internal calculation/validation helpers |

### Data Layer (`src/data/`)

None -- this module has no persistence layer. It operates entirely on in-memory data structures passed as arguments.

### CLI (`src/cli/commands/`)

| File | Purpose |
|------|---------|
| `special_gems_commands.py` | Click command group `special-gems` with 5 commands: `check`, `activate`, `fuse`, `from-match`, `simulate`. Includes helper functions for service construction, position/gem-type parsing, and board display. |

### Tests (`tests/unit/modules/special_gems/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Empty package init |
| `test_special_gems_service.py` | 84 test functions across 13 test classes covering all public methods, validation, all 6 fusion types, edge cases, configuration overrides, and the `SPECIAL_GEM_TYPES` constant |

---

## 3. Deviations from Artifact

Not assessed -- document produced from code examination only.

---

## 4. Public Interface

### `SpecialGemsService` (class in `service.py`)

```python
def __init__(
    self,
    config: ConfigProtocol,
    logger: LoggerProtocol,
    errors: ErrorServiceProtocol,
    scoring_service: ScoringServiceProtocol,
) -> None
```

**Public methods:**

```python
def is_special_gem(self, gem_type: GemType) -> bool
```
Returns `True` if `gem_type` is in `SPECIAL_GEM_TYPES` (LINE_BLAST_H, LINE_BLAST_V, RADIAL_BOMB, CHROMATIC_ORB).

```python
def calculate_effect(
    self,
    board: BoardState,
    position: Position,
    target_color: GemType | None = None,
) -> SpecialGemEffect
```
Calculates the activation effect for a special gem at the given position. Dispatches to internal methods based on gem type. Raises `AppError` on validation failures.

```python
def calculate_fusion_effect(
    self,
    board: BoardState,
    pos_a: Position,
    pos_b: Position,
    target_color: GemType | None = None,
) -> FusionEffect
```
Calculates the fusion effect of two adjacent special gems. Normalizes gem order by type value (lower value = gem_a). Raises `AppError` on validation failures.

```python
def apply_effect(
    self,
    board: BoardState,
    effect: SpecialGemEffect | FusionEffect,
) -> tuple[BoardState, list[Position]]
```
Applies a calculated effect to the board. Returns a new `BoardState` (original unmodified) and a list of cleared positions. For `FusionEffect`, also applies secondary effects.

```python
def get_special_gem_for_match(
    self, match_result: MatchResult
) -> tuple[GemType, Position] | None
```
Determines which special gem a match creates. Returns `None` for 3-matches. Priority: T/L-shape overlaps -> CHROMATIC_ORB; 5+ match -> RADIAL_BOMB; 4-match -> LINE_BLAST_H or LINE_BLAST_V. Raises `AppError` if matches are empty.

```python
def find_triggered_special_gems(
    self, board: BoardState, cleared_positions: set[Position]
) -> list[Position]
```
Finds special gems within cleared positions that should chain-trigger. Returns a deterministically sorted list (row, col order). Returns empty list if chain reactions are disabled.

### `SpecialGemsServiceProtocol` (Protocol in `protocols.py`)

Mirrors all public methods of `SpecialGemsService` with identical signatures:
- `calculate_effect(board, position, target_color) -> SpecialGemEffect`
- `calculate_fusion_effect(board, pos_a, pos_b, target_color) -> FusionEffect`
- `apply_effect(board, effect) -> tuple[BoardState, list[Position]]`
- `is_special_gem(gem_type) -> bool`
- `get_special_gem_for_match(match_result) -> tuple[GemType, Position] | None`
- `find_triggered_special_gems(board, cleared_positions) -> list[Position]`

### `ScoringServiceProtocol` (Protocol in `protocols.py`)

Minimal protocol with a single method required by special_gems:
```python
def calculate_special_gem_bonus(
    self, gem_type: GemType, gems_affected: int
) -> SpecialGemBonus
```

### Types (`types.py`)

**Constants:**
- `SPECIAL_GEM_TYPES: frozenset[GemType]` -- `{LINE_BLAST_H, LINE_BLAST_V, RADIAL_BOMB, CHROMATIC_ORB}`
- `STANDARD_GEM_TYPES: frozenset[GemType]` -- `{RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE}`

**Enums:**
- `FusionType(Enum)` -- `CROSS_BLAST`, `TRIPLE_LINE`, `COLOR_LINE_BLAST`, `MEGA_BOMB`, `COLOR_BOMB`, `BOARD_CLEAR`

**Dataclasses (frozen):**
- `SpecialGemEffect` -- fields: `gem_type`, `source_position`, `affected_positions` (frozenset), `bonus_score` (SpecialGemBonus), `triggers_special_gems` (list[Position]), `description` (str)
- `FusionEffect` -- fields: `gem_a_type`, `gem_b_type`, `fusion_type`, `source_positions` (tuple of 2), `affected_positions` (frozenset), `bonus_score`, `triggers_special_gems`, `secondary_effects` (list[SpecialGemEffect]), `description`

---

## 5. Dependencies Injected

| Parameter | Protocol Type | Usage |
|-----------|--------------|-------|
| `config` | `ConfigProtocol` | Read configuration values for board dimensions, radial bomb radius, mega bomb radius, triple line count, chain reaction toggle |
| `logger` | `LoggerProtocol` | Structured logging for debug events (`special_gems.service_initialized`, `special_gems.effect_calculated`, `special_gems.fusion_calculated`, `special_gems.effect_applied`, `special_gems.chain_triggered`, `special_gems.match_creates_special`) and warn events (`special_gems.validation_failed`) |
| `errors` | `ErrorServiceProtocol` | Error factory for creating typed `AppError` instances via `errors.validation()` |
| `scoring_service` | `ScoringServiceProtocol` | Scoring bonus calculation via `calculate_special_gem_bonus()` |

All four are received via `__init__` and stored as private attributes (`self._config`, `self._logger`, `self._errors`, `self._scoring`).

---

## 6. Configuration Keys Used

| Key | Default Value | Type | Usage |
|-----|---------------|------|-------|
| `game.board_width` | `8` | `int` | Board width (cached at init) |
| `game.board_height` | `8` | `int` | Board height (cached at init) |
| `special_gems.radial_bomb_radius` | `1` | `int` | Radius for single Radial Bomb activation (3x3 at default) |
| `special_gems.mega_bomb_radius` | `2` | `int` | Radius for Radial+Radial fusion (5x5 at default) |
| `special_gems.triple_line_count` | `3` | `int` | Number of rows/columns cleared by Line+Radial fusion |
| `special_gems.chain_reaction_enabled` | `True` | `bool` | Whether chain reactions (triggered special gems) are active |

All configuration values are read once at `__init__` and cached as private instance attributes. They are not re-read during method calls.

---

## 7. Error Codes Used

| Code | Method(s) |
|------|-----------|
| `VALIDATION_OUT_OF_BOUNDS` | `_validate_position()` (called by `calculate_effect`, `calculate_fusion_effect`) |
| `VALIDATION_INVALID_GEM_SWAP` | `calculate_effect()` (position not a special gem), `calculate_fusion_effect()` (either position not a special gem) |
| `VALIDATION_INVALID_INPUT` | `_validate_target_color()` (target_color is None or not standard 1-6), `get_special_gem_for_match()` (empty matches), `_calculate_fusion()` (unknown fusion combination -- defensive fallthrough) |
| `VALIDATION_POSITIONS_NOT_ADJACENT` | `calculate_fusion_effect()` (pos_a and pos_b are not adjacent) |

All errors are raised via `self._errors.validation(message, code=..., **kwargs)` which produces `AppError` instances. No bare `raise Exception()` or similar patterns are used.

---

## 8. Async Behavior

All methods are synchronous `def` (not `async def`). The module's docstring explicitly states: "All methods are synchronous. The service performs pure computation on in-memory data with no I/O." There are no `await` calls, no async generators, and no background tasks anywhere in the module.

---

## 9. Internal Design Notes

### Effect Calculation Dispatch

`calculate_effect` uses a simple if/elif chain to dispatch to the appropriate internal method:
- `GemType.LINE_BLAST_H` -> `_calculate_line_blast(board, position, is_horizontal=True)`
- `GemType.LINE_BLAST_V` -> `_calculate_line_blast(board, position, is_horizontal=False)`
- `GemType.RADIAL_BOMB` -> `_calculate_radial_bomb(board, position, self._radial_bomb_radius)`
- `GemType.CHROMATIC_ORB` -> `_calculate_chromatic_orb(board, position, target_color)`

### Fusion Normalization

In `calculate_fusion_effect`, the two gem types are normalized so that `gem_a.value <= gem_b.value`. Since special gems have negative enum values (`LINE_BLAST_H=-1`, `LINE_BLAST_V=-2`, `RADIAL_BOMB=-3`, `CHROMATIC_ORB=-4`), gem_a is always the "stronger" gem (more negative value). This ensures consistent dispatch regardless of argument order.

### Fusion Type Dispatch

`_calculate_fusion` dispatches to 6 private methods based on gem type combination:
- `CHROMATIC_ORB + CHROMATIC_ORB` -> `_fusion_board_clear` (clears entire board)
- `CHROMATIC_ORB + RADIAL_BOMB` -> `_fusion_color_bomb` (all gems of target color become radial bombs)
- `CHROMATIC_ORB + LINE_BLAST_*` -> `_fusion_color_line_blast` (all gems of target color become line blasts)
- `RADIAL_BOMB + RADIAL_BOMB` -> `_fusion_mega_bomb` (larger explosion, default 5x5)
- `RADIAL_BOMB + LINE_BLAST_*` -> `_fusion_triple_line` (3 adjacent rows or columns)
- `LINE_BLAST_* + LINE_BLAST_*` -> `_fusion_cross_blast` (clears both row and column at midpoint)

### Fusion Midpoint Calculation

Cross Blast, Mega Bomb, and Triple Line fusions calculate their center point as the integer midpoint of the two source positions: `mid = (pos_a + pos_b) // 2`.

### Board Boundary Clipping

All position calculations clip to board boundaries using `0 <= row < height` and `0 <= col < width` checks. Radial bomb at a corner or edge will produce fewer affected positions than the theoretical area. The same applies to mega bomb and triple line fusions.

### Chain Reaction Detection

The internal method `_find_triggered_specials` scans affected positions (excluding source gems) for special gems on the board. Results are sorted by `(row, col)` for deterministic ordering. Chain detection is gated by the `special_gems.chain_reaction_enabled` config flag.

### Center Finding

The static method `_find_center` sorts positions by `(row, col)` and returns the element at index `len // 2`. For even-length lists (e.g., 4-match), this returns the element at index 2 (the third position in sorted order), which biases slightly right/downward.

### Secondary Effects in Fusions

Color-based fusions (`COLOR_LINE_BLAST`, `COLOR_BOMB`) produce `secondary_effects` -- a list of `SpecialGemEffect` objects representing each converted gem's individual activation. In `COLOR_LINE_BLAST`, the secondary effects have empty `affected_positions` (all affected positions are aggregated into the primary `FusionEffect.affected_positions`). In `COLOR_BOMB`, secondary effects contain their individual bomb areas in `affected_positions`.

### Board State Immutability

`apply_effect` creates a copy of the board grid via `board.grid.copy()` before modifying cells. The original `BoardState` is never mutated. Tests verify this explicitly.

### Type Imports

The module imports concrete types from `src.core.types.board` and `src.core.types.game` (value types like `BoardState`, `Position`, `GemType`, `MatchResult`, `MatchGroup`) and from `src.modules.scoring.types` (`SpecialGemBonus`). Protocol types for injected services (`ConfigProtocol`, `LoggerProtocol`, `ErrorServiceProtocol`) are imported under `TYPE_CHECKING` only, avoiding runtime dependency on core implementations.

### CLI Commands

The CLI provides 5 commands under the `special-gems` group:

| Command | Description |
|---------|-------------|
| `check` | Check if a board position contains a special gem |
| `activate` | Calculate the activation effect of a special gem |
| `fuse` | Calculate the fusion effect of two adjacent special gems |
| `from-match` | Determine what special gem a match result creates |
| `simulate` | Simulate activation with optional `--apply` flag to show resulting board |

The CLI constructs services via `_make_special_gems_service()` which is the sole instantiation point, using `load_config`, `LogService`, `ErrorService`, `ScoringService`, and `SpecialGemsService` wired together. Board display uses Rich tables with single-letter gem abbreviations (R, B, G, Y, P, O, LH, LV, RB, CO, `.` for empty).

### Test Coverage Structure

The 84 tests are organized into 13 classes across 10 logical sections:

| Section | Class | Test Count |
|---------|-------|------------|
| 1. is_special_gem | `TestIsSpecialGem` | 8 |
| 2. calculate_effect (LINE_BLAST_H) | `TestCalculateEffectLineBlastH` | 4 |
| 2. calculate_effect (LINE_BLAST_V) | `TestCalculateEffectLineBlastV` | 3 |
| 2. calculate_effect (RADIAL_BOMB) | `TestCalculateEffectRadialBomb` | 5 |
| 2. calculate_effect (CHROMATIC_ORB) | `TestCalculateEffectChromaticOrb` | 3 |
| 3. calculate_effect validation | `TestCalculateEffectValidation` | 7 |
| 4. Fusion: Cross Blast | `TestFusionCrossBlast` | 3 |
| 4. Fusion: Triple Line | `TestFusionTripleLine` | 3 |
| 4. Fusion: Mega Bomb | `TestFusionMegaBomb` | 3 |
| 4. Fusion: Color Line Blast | `TestFusionColorLineBlast` | 2 |
| 4. Fusion: Color Bomb | `TestFusionColorBomb` | 2 |
| 4. Fusion: Board Clear | `TestFusionBoardClear` | 2 |
| 5. Fusion validation | `TestFusionValidation` | 5 |
| 6. apply_effect | `TestApplyEffect` | 5 |
| 7. get_special_gem_for_match | `TestGetSpecialGemForMatch` | 9 |
| 8. find_triggered_special_gems | `TestFindTriggeredSpecialGems` | 6 |
| 9. Edge cases / config | `TestEdgeCases` | 12 |
| 10. SPECIAL_GEM_TYPES constant | `TestSpecialGemTypesConstant` | 3 |

Tests use mock services (`MockConfigService`, `MockErrorService`, `MockLogService` from `tests.mocks.services`) and a local `MockScoringService` that returns predictable bonus values (base=100, per_gem=10). No global state is used; all dependencies are injected via fixtures.
