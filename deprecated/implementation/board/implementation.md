# Board Module Implementation Document

**Module:** board
**Phase:** 2.2
**Author:** Coding Agent
**Date:** 2026-02-05

---

## 1. Summary

The board module implements the core match-3 grid engine for ChromaCrush. It provides deterministic board generation (with no initial 3-in-a-row matches), gem swapping with validation, horizontal and vertical match detection, special gem creation logic (LINE_BLAST_H, LINE_BLAST_V, RADIAL_BOMB, CHROMATIC_ORB), gravity (gems falling to fill cleared spaces), empty cell filling with new random gems, full move processing with cascade loops, board validation, and deadlock detection. All operations are synchronous and operate on immutable board state -- every method returns a new `BoardState` without modifying the input. The board grid is backed by NumPy `int8` arrays.

## 2. Files Created

### Module Code (`src/modules/board/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Package init; exports `BoardService`, `CascadeStep`, `GemDrop`, `GemSpawn`, `MoveProcessingResult` |
| `types.py` | Dataclass definitions for cascade tracking: `GemDrop`, `GemSpawn`, `CascadeStep`, `MoveProcessingResult` |
| `service.py` | `BoardService` class -- the core match-3 grid engine with all public and internal methods |

### Data Layer (`src/data/`)
| File | Purpose |
|------|---------|
| None | This module has no persistence layer. All operations are in-memory on NumPy arrays. |

### CLI (`src/cli/commands/`)
| File | Purpose |
|------|---------|
| `board_commands.py` | Click CLI group `board` with commands: `generate`, `detect-matches`, `process-move`, `has-moves`. Uses Rich for coloured terminal output. |

### Tests (`tests/unit/modules/board/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Empty package init |
| `test_board_service.py` | 32 test functions across 9 test classes covering all public methods of `BoardService` |

## 3. Deviations from Artifact

Not assessed -- document produced from code examination only.

## 4. Public Interface

### `BoardService` (class in `src/modules/board/service.py`)

```python
def __init__(
    self,
    config: ConfigProtocol,
    logger: LoggerProtocol,
    errors: ErrorServiceProtocol,
) -> None
```

**Public methods:**

```python
def create_board(self, width: int, height: int, seed: int) -> BoardState
```
Generates a new board with no initial 3-in-a-row matches using a cell-by-cell fill that excludes colours creating horizontal or vertical runs of 3.

```python
def swap_gems(self, board: BoardState, move: Move) -> BoardState
```
Swaps two adjacent gems, returning a new board. Validates both positions are in-bounds, orthogonally adjacent, and neither cell is empty. Does not check whether the swap creates a match.

```python
def detect_matches(self, board: BoardState, min_length: int = 3) -> MatchResult
```
Scans the board for horizontal and vertical runs of matching standard gems (value > 0). Returns a `MatchResult` with all match groups and any special gem that should be created.

```python
def clear_matches(self, board: BoardState, matches: MatchResult) -> BoardState
```
Sets all matched positions to `GemType.EMPTY`, returning a new board.

```python
def apply_gravity(self, board: BoardState) -> tuple[BoardState, list[GemDrop]]
```
Drops gems down to fill empty spaces within each column. Returns the new board and a list of `GemDrop` records.

```python
def fill_empty(self, board: BoardState, seed: int) -> tuple[BoardState, list[GemSpawn]]
```
Fills empty cells with new random standard gems. Iterates column-major for deterministic seed ordering.

```python
def process_move(self, board: BoardState, move: Move, seed: int) -> MoveProcessingResult
```
Processes a full player move: swap, detect, cascade loop (clear -> gravity -> fill -> detect, until stable). Returns the complete cascade history. If the swap produces no match, reverts and returns `was_valid_match=False`.

```python
def validate_board(self, board: BoardState) -> bool
```
Checks whether a board has valid dimensions (against configured width/height) and all cells contain recognised `GemType` values.

```python
def has_valid_moves(self, board: BoardState) -> bool
```
Checks whether at least one adjacent swap produces a match (deadlock detection). Tries every possible horizontal and vertical swap, returning `True` as soon as one valid move is found.

### Data Types (in `src/modules/board/types.py`)

```python
@dataclass(frozen=True)
class GemDrop:
    gem_type: GemType
    from_pos: Position
    to_pos: Position
    distance: int
```

```python
@dataclass(frozen=True)
class GemSpawn:
    gem_type: GemType
    position: Position
    column: int
```

```python
@dataclass
class CascadeStep:
    step_number: int
    matches: MatchResult
    board_after_clear: BoardState
    gems_dropped: list[GemDrop]        # default_factory=list
    board_after_gravity: BoardState     # default=None
    gems_spawned: list[GemSpawn]        # default_factory=list
    board_after_fill: BoardState        # default=None
```

```python
@dataclass
class MoveProcessingResult:
    initial_board: BoardState
    final_board: BoardState
    move: Move
    was_valid_match: bool
    cascades: list[CascadeStep]                        # default_factory=list
    total_matches: int                                  # default=0
    total_gems_cleared: int                             # default=0
    chain_count: int                                    # default=0
    special_gems_created: list[tuple[Position, GemType]]  # default_factory=list
```

## 5. Dependencies Injected

| Parameter | Protocol Type | Usage |
|-----------|--------------|-------|
| `config` | `ConfigProtocol` (from `src.core.protocols.config`) | Read board dimensions and gem count at init time |
| `logger` | `LoggerProtocol` (from `src.core.protocols.logger`) | Structured diagnostic logging (debug, trace, warn levels) |
| `errors` | `ErrorServiceProtocol` (from `src.core.protocols.error_service`) | Create typed validation errors via `errors.validation()` |

No repository or data context dependencies. No async dependencies.

## 6. Configuration Keys Used

| Key | Default Value | Read Location |
|-----|--------------|---------------|
| `game.board_width` | `8` | `__init__` (cached as `self._board_width`) |
| `game.board_height` | `8` | `__init__` (cached as `self._board_height`) |
| `game.gem_types` | `6` | `__init__` (cached as `self._gem_types`) |
| `game.min_match_length` | `3` | `__init__` (cached as `self._min_match_length`) |

Note: `self._min_match_length` is cached but not used within the service code. The `detect_matches` method uses a `min_length` parameter (default `3`) passed by callers rather than the cached config value.

## 7. Error Codes Used

| Code | Method(s) | Error Factory |
|------|-----------|---------------|
| `VALIDATION_OUT_OF_BOUNDS` | `_validate_position` (called by `swap_gems`) | `errors.validation()` |
| `VALIDATION_POSITIONS_NOT_ADJACENT` | `swap_gems` | `errors.validation()` |
| `VALIDATION_INVALID_GEM_SWAP` | `swap_gems` | `errors.validation()` |

All errors are raised by the caller pattern: `raise self._errors.validation(...)`.

## 8. Async Behavior

All methods are synchronous (`def`, not `async def`). The service operates entirely on in-memory NumPy arrays and never performs I/O. No async patterns, no background tasks, no fire-and-forget operations exist in this module.

## 9. Internal Design Notes

### Board Generation Algorithm
The `create_board` method uses a cell-by-cell fill strategy that scans left-to-right, top-to-bottom. For each cell, it builds a list of available gem types (1 through `gem_types`) and removes any colour that would create a horizontal or vertical run of 3 by checking the two cells to the left and the two cells above. With 6 gem types and at most 2 exclusions, at least 4 colours are always available, guaranteeing the algorithm succeeds. Uses `numpy.random.default_rng(seed)` for deterministic generation.

### Match Detection
Horizontal and vertical scans are separate linear passes. Horizontal scans iterate row-by-row left-to-right tracking run starts; vertical scans iterate column-by-column top-to-bottom. Only standard gem values (`> 0`) are eligible for matching. A sentinel value of `-999` is used at the boundary (one past the last column/row) to flush the final run.

### Special Gem Priority
The `_determine_special_gem` method applies this priority:
1. T/L shape (a position appearing in both a horizontal and vertical match) produces `CHROMATIC_ORB` at the intersection point.
2. 5+ match produces `RADIAL_BOMB` at the centre position (sorted by row,col, index `len//2`).
3. 4-match horizontal produces `LINE_BLAST_H` at the middle position (sorted, index `len//2`).
4. 4-match vertical produces `LINE_BLAST_V` at the middle position (sorted, index `len//2`).

### Cascade Loop
`process_move` runs a cascade loop capped at `_MAX_CASCADE_STEPS = 100`. Each iteration: detect matches, clear, apply gravity, fill empty cells. The RNG seed evolves per cascade step using a linear congruential generator: `seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF`. A warning is logged if the maximum cascade depth is reached.

### Gravity Implementation
`apply_gravity` processes each column independently. It separates non-empty gems from empty cells using a boolean mask, then rebuilds each column with empties stacked on top and non-empty gems packed at the bottom. `GemDrop` records are created for every gem that changes row position.

### Fill Strategy
`fill_empty` iterates column-major (col outer, row inner) so that deterministic seed ordering is consistent across platforms. Each empty cell receives a random standard gem value from `[1, gem_types]`.

### Board Immutability
Every public method that modifies the board returns a new `BoardState` via `board.copy()` (which copies the underlying NumPy array). The original board is never mutated.

### Module-Level Constant
`_MAX_CASCADE_STEPS = 100` is defined at module level as a safety valve against infinite cascade loops.

### CLI Architecture
The CLI (`board_commands.py`) creates a `BoardService` instance via a helper function `_make_board_service` that calls `load_config` from the composition root, then instantiates `LogService` and `ErrorService` concretely. This is the only place where concrete service classes are created for CLI usage. The CLI uses Rich for coloured board rendering with a colour map and label map for all gem types including specials. Four commands are provided:
- `generate` -- create and display a new board with optional seed/width/height overrides
- `detect-matches` -- find matches on a board provided as JSON
- `process-move` -- execute a full move with cascades on a board provided as JSON
- `has-moves` -- deadlock detection on a board provided as JSON

### Test Design
All 32 tests inject mocks (`MockConfigService`, `MockLogService`, `MockErrorService`) via pytest fixtures, following the `__init__` injection pattern. No global state is used. Tests cover: board creation (dimensions, determinism, no initial matches, gem value range), swap validation (basic swap, out-of-bounds, non-adjacent, empty cell), match detection (horizontal/vertical 3-match, no matches, 4-match specials, 5-match radial, T-shape chromatic orb, special gem exclusion from matching, vertical 4-match), match clearing, gravity, empty cell filling (correctness and determinism), full move processing (valid move, no-match revert, determinism, input immutability), board validation (valid board, wrong dimensions, invalid gem values), and deadlock detection (board with moves, deadlocked cyclic board).
