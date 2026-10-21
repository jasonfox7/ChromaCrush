# Module Artifact: board_gen

## Header
- **Author:** Scout Agent (board_gen)
- **Date:** 2026-02-05
- **Version:** 1.0
- **Status:** Final
- **Dependencies:** `board` (Wave 1), `special_gems` (Wave 3)
- **Dependents:** `match`

---

## Purpose

The **board_gen** module handles procedural board generation for ChromaCrush. It creates deterministic, fair game boards using seeded random number generation, ensuring that both players in an asynchronous versus match receive identical starting positions.

Core responsibilities:
- **Seeded generation** - Deterministic boards from a seed value, enabling async fairness where both players play the same board
- **No initial matches** - Generated boards are guaranteed to have no 3-in-a-row matches at start
- **Cascade potential tuning** - Configurable parameter (0.0-1.0) controlling how "favorable" the board is for cascades
- **Near-miss psychology** - Subtle gem placement bias creating "almost matches" that feel engaging
- **Starting special gems** - Optional placement of special gems at board generation time

This module is **synchronous** and **pure** - it operates entirely on parameters passed in and returns new state without side effects. No database I/O, no network calls, no async behavior. All randomness uses provided seeds for deterministic, reproducible results.

---

## Public Interface

### Class: `BoardGenService`

The board_gen module exposes a single service class that receives dependencies via `__init__` injection.

```python
class BoardGenService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        board_service: BoardServiceProtocol,
        special_gems_service: SpecialGemsServiceProtocol,
    ) -> None:
        ...
```

**Note:** The `board_service` is injected to use `validate_board` and `has_valid_moves` checks. The `special_gems_service` is injected for special gem type information and validation.

---

### Inputs

#### `generate_board(seed: int, options: BoardGenOptions | None = None) -> GeneratedBoard`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `seed` | `int` | RNG seed for deterministic generation | Any valid int64 |
| `options` | `BoardGenOptions \| None` | Optional generation parameters | If None, uses config defaults |

```python
@dataclass(frozen=True)
class BoardGenOptions:
    """Options for board generation."""
    width: int | None = None           # Override config default
    height: int | None = None          # Override config default
    cascade_potential: float | None = None  # 0.0-1.0 (None = config default)
    near_miss_factor: float | None = None   # 0.0-1.0 (None = config default)
    starting_specials: list[StartingSpecial] | None = None  # Pre-placed special gems
    gem_distribution: dict[int, float] | None = None  # Color frequency weights

@dataclass(frozen=True)
class StartingSpecial:
    """Specification for a starting special gem."""
    gem_type: GemType  # Must be a special gem type
    position: Position | None = None  # If None, placed randomly
```

---

#### `generate_board_for_match(seed: int, match_type: MatchType = MatchType.STANDARD) -> GeneratedBoard`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `seed` | `int` | RNG seed for deterministic generation | Any valid int64 |
| `match_type` | `MatchType` | Type of match (affects generation parameters) | Must be valid MatchType |

```python
class MatchType(Enum):
    STANDARD = "standard"     # Normal generation settings
    COMPETITIVE = "competitive"  # No cascade bias, balanced distribution
    CASUAL = "casual"         # Higher cascade potential, more "fun"
    TUTORIAL = "tutorial"     # Guaranteed easy moves, no near-misses
```

This is a convenience method that applies preset `BoardGenOptions` based on match type.

---

#### `validate_seed(seed: int) -> bool`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `seed` | `int` | Seed value to validate | Any value |

Returns `True` if the seed produces a valid, playable board. Useful for pre-validation before match creation.

---

#### `regenerate_from_deadlock(board: BoardState, seed: int) -> GeneratedBoard`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Current deadlocked board | Must be valid BoardState |
| `seed` | `int` | RNG seed for deterministic shuffle | Any valid int64 |

Creates a new board that preserves special gems from the original but reshuffles standard gems to eliminate deadlock.

---

#### `calculate_cascade_potential(board: BoardState) -> float`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Board to analyze | Must be valid BoardState |

Analyzes a board and returns a cascade potential score (0.0-1.0) indicating how likely the board is to produce cascades.

---

### Outputs

#### `generate_board` and `generate_board_for_match` return `GeneratedBoard`

```python
@dataclass
class GeneratedBoard:
    """Result of board generation."""
    board_state: BoardState
    seed: int
    generation_metadata: GenerationMetadata

@dataclass
class GenerationMetadata:
    """Metadata about how the board was generated."""
    width: int
    height: int
    cascade_potential_target: float
    cascade_potential_actual: float
    near_miss_factor: float
    near_miss_count: int              # How many near-miss patterns created
    starting_specials_placed: list[tuple[Position, GemType]]
    valid_moves_count: int
    generation_attempts: int          # Attempts before valid board found
    generation_time_ms: float
```

---

#### `validate_seed` returns `bool`

- `True` if seed produces a valid, playable board
- `False` if seed produces a deadlocked or invalid board (should not happen with proper algorithm)

---

#### `regenerate_from_deadlock` returns `GeneratedBoard`

A new board with:
- All special gems from the original board preserved in their positions
- Standard gems reshuffled to eliminate deadlock
- At least one valid move guaranteed

---

#### `calculate_cascade_potential` returns `float`

A score from 0.0 to 1.0:
- **0.0-0.3**: Low cascade potential (few favorable patterns)
- **0.3-0.6**: Medium cascade potential (balanced)
- **0.6-1.0**: High cascade potential (many favorable patterns)

---

### Error Cases

| Condition | Error Code | Error Type | Context Fields |
|-----------|------------|------------|----------------|
| Invalid cascade_potential (outside 0.0-1.0) | `VALIDATION_INVALID_INPUT` | validation | `field="cascade_potential"`, `value`, `reason="Must be between 0.0 and 1.0"` |
| Invalid near_miss_factor (outside 0.0-1.0) | `VALIDATION_INVALID_INPUT` | validation | `field="near_miss_factor"`, `value`, `reason="Must be between 0.0 and 1.0"` |
| Invalid board dimensions | `VALIDATION_INVALID_INPUT` | validation | `field="dimensions"`, `width`, `height`, `reason="Dimensions must match config"` |
| Starting special at invalid position | `VALIDATION_OUT_OF_BOUNDS` | validation | `position`, `board_width`, `board_height` |
| Starting special with non-special gem type | `VALIDATION_INVALID_INPUT` | validation | `field="gem_type"`, `value`, `reason="Must be a special gem type"` |
| Too many starting specials for board size | `VALIDATION_INVALID_INPUT` | validation | `field="starting_specials"`, `count`, `max_allowed` |
| Invalid gem distribution (weights don't sum positive) | `VALIDATION_INVALID_INPUT` | validation | `field="gem_distribution"`, `reason="Weights must sum to positive value"` |
| Generation exceeds max attempts | `INTERNAL_UNEXPECTED` | internal | `seed`, `attempts`, `reason="Failed to generate valid board"` |

---

### Async Behavior

**This module is fully synchronous.**

- All methods are regular `def`, not `async def`
- No I/O operations (no database, no network, no file system)
- No async imports or dependencies
- Thread-safe for read operations (immutable inputs)

Rationale: The board_gen module performs pure computation on in-memory data structures. NumPy operations on an 8x8 grid with tuning algorithms are sub-millisecond to low-millisecond. Async would add complexity without benefit.

---

## Mandatory Service Usage

### Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `game.board_width` | int | 8 | Default board width |
| `game.board_height` | int | 8 | Default board height |
| `game.gem_types` | int | 6 | Number of standard gem colors (1-6) |
| `board_gen.default_cascade_potential` | float | 0.5 | Default cascade potential target |
| `board_gen.default_near_miss_factor` | float | 0.3 | Default near-miss psychology factor |
| `board_gen.max_generation_attempts` | int | 100 | Max attempts before generation failure |
| `board_gen.max_starting_specials` | int | 3 | Maximum allowed starting special gems |
| `board_gen.enable_near_miss` | bool | True | Whether near-miss tuning is enabled |
| `board_gen.competitive_cascade_potential` | float | 0.4 | Cascade potential for competitive matches |
| `board_gen.casual_cascade_potential` | float | 0.6 | Cascade potential for casual matches |
| `board_gen.tutorial_cascade_potential` | float | 0.7 | Cascade potential for tutorial |

Configuration is read once at service initialization and cached.

---

### Logging Events

| Event | Severity | Trigger | Context |
|-------|----------|---------|---------|
| `board_gen.generation_started` | DEBUG | Generation begins | `seed`, `options` |
| `board_gen.generation_complete` | DEBUG | Generation succeeds | `seed`, `attempts`, `time_ms`, `cascade_potential`, `valid_moves` |
| `board_gen.near_miss_placed` | TRACE | Near-miss pattern created | `position`, `pattern_type` |
| `board_gen.starting_special_placed` | DEBUG | Special gem placed | `gem_type`, `position` |
| `board_gen.cascade_tuning_applied` | TRACE | Cascade potential adjustment made | `target`, `before`, `after` |
| `board_gen.deadlock_reshuffle` | INFO | Deadlock reshuffled | `seed`, `specials_preserved` |
| `board_gen.generation_retry` | DEBUG | Generation attempt failed, retrying | `seed`, `attempt`, `reason` |
| `board_gen.generation_failed` | ERROR | Generation exceeded max attempts | `seed`, `attempts` |
| `board_gen.validation_failed` | WARN | Invalid generation parameters | `field`, `reason` |

---

### Error Types Used

From the error taxonomy (Interface Agent guidance):

- `VALIDATION_INVALID_INPUT` - Invalid generation parameters
- `VALIDATION_OUT_OF_BOUNDS` - Position outside grid for starting specials
- `INTERNAL_UNEXPECTED` - Generation failure (should be rare, indicates algorithm issue)

All errors created through injected `ErrorServiceProtocol`, never bare raises.

---

## Data Access

### Owned Data

**None.**

The board_gen module does not own any persistent data. It produces `BoardState` objects that are passed to callers. The `match` module owns persisted board state in the `matches` table.

### Repository Interfaces Required

**None.**

No repository injection needed. This module operates purely on in-memory data structures.

### Data Read from Other Modules

**None (directly).**

The board_gen module receives configuration parameters and uses injected services (`board_service`, `special_gems_service`) for validation and type information. It does not read from any data stores.

### Transaction Requirements

**None.**

No database operations, no transactions.

---

## Presentation Boundary

### Business Logic API Surface

The board_gen module exposes pure functions operating on domain types:
- Input: `int` (seed), `BoardGenOptions`, `MatchType`, `BoardState`
- Output: `GeneratedBoard`, `GenerationMetadata`, `bool`, `float`

All types are defined in this module (`src/modules/board_gen/types.py`) or imported from `src/core/types/`.

### Adapter Needs

Presentation adapters need to:
1. Convert `GeneratedBoard.board_state` to JSON via `board_state.to_list()`
2. Serialize `GenerationMetadata` for debugging/analytics endpoints
3. Handle match type selection in UI before calling generation

Example adapter output for API:
```python
{
    "board": [[1, 2, 3, ...], ...],  # 8x8 grid
    "seed": 12345678,
    "metadata": {
        "cascade_potential": 0.52,
        "near_miss_count": 4,
        "valid_moves": 23,
        "generation_time_ms": 2.3
    }
}
```

### What Does NOT Belong in This Module

- No JSON serialization (adapter responsibility)
- No animation timing or reveal effects
- No UI for seed input or match type selection
- No HTTP response construction
- No terminal formatting or colors
- No persistence of generated boards

---

## Internal Design

### Core Data Structures

```python
# src/modules/board_gen/types.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import numpy as np
from numpy.typing import NDArray

from src.core.types.board import BoardState, Position
from src.core.types.game import GemType


class MatchType(Enum):
    """Match types with preset generation parameters."""
    STANDARD = "standard"
    COMPETITIVE = "competitive"
    CASUAL = "casual"
    TUTORIAL = "tutorial"


@dataclass(frozen=True)
class StartingSpecial:
    """Specification for a starting special gem."""
    gem_type: GemType
    position: Position | None = None


@dataclass(frozen=True)
class BoardGenOptions:
    """Options for board generation."""
    width: int | None = None
    height: int | None = None
    cascade_potential: float | None = None
    near_miss_factor: float | None = None
    starting_specials: list[StartingSpecial] | None = None
    gem_distribution: dict[int, float] | None = None


@dataclass
class GenerationMetadata:
    """Metadata about board generation."""
    width: int
    height: int
    cascade_potential_target: float
    cascade_potential_actual: float
    near_miss_factor: float
    near_miss_count: int
    starting_specials_placed: list[tuple[Position, GemType]]
    valid_moves_count: int
    generation_attempts: int
    generation_time_ms: float


@dataclass
class GeneratedBoard:
    """Complete generation result."""
    board_state: BoardState
    seed: int
    generation_metadata: GenerationMetadata
```

---

### Algorithm: Core Generation (No Initial Matches)

The fundamental generation algorithm ensures no 3-in-a-row exists at board creation. This is the same algorithm used in the `board` module's `create_board`, but extended with tuning capabilities.

```
generate_base_board(width, height, seed, gem_weights):
    rng = np.random.default_rng(seed)
    grid = np.zeros((height, width), dtype=np.int8)

    for row in range(height):
        for col in range(width):
            available_gems = get_weighted_choices(gem_weights)

            # Exclude gems that would create horizontal match
            if col >= 2:
                if grid[row, col-1] == grid[row, col-2] and grid[row, col-1] != 0:
                    available_gems = remove_gem(available_gems, grid[row, col-1])

            # Exclude gems that would create vertical match
            if row >= 2:
                if grid[row-1, col] == grid[row-2, col] and grid[row-1, col] != 0:
                    available_gems = remove_gem(available_gems, grid[row-1, col])

            grid[row, col] = rng.choice(available_gems, p=normalize(weights))

    return BoardState(grid=grid)
```

This mathematically guarantees no initial matches because at each cell, at least 4 gem types remain available (we exclude at most 2).

---

### Algorithm: Cascade Potential Tuning

Cascade potential represents how likely the board is to produce chain reactions from a single move. The tuning algorithm biases gem placement to create or avoid "almost-cascade" patterns.

**Favorable patterns (increase cascade potential):**
- Two gems of same color with one space between them in a row/column
- Three gems of same color in an L-shape (potential for corner match)
- Columns with same-color gems that would fall into matches after a clear

**Unfavorable patterns:**
- Maximum color diversity in each 3x3 region
- No gems of same color within 2 cells of each other

```
apply_cascade_tuning(board, target_potential, rng):
    current = calculate_cascade_potential(board)

    # Iteratively adjust toward target
    max_iterations = 50
    tolerance = 0.05

    for _ in range(max_iterations):
        if abs(current - target_potential) < tolerance:
            break

        if current < target_potential:
            # Increase potential: introduce favorable patterns
            position = find_tunable_position(board, "increase")
            new_gem = select_gem_for_potential(board, position, "increase", rng)
        else:
            # Decrease potential: break up favorable patterns
            position = find_tunable_position(board, "decrease")
            new_gem = select_gem_for_potential(board, position, "decrease", rng)

        # Apply change only if it doesn't create a match
        if not would_create_match(board, position, new_gem):
            board = set_gem(board, position, new_gem)
            current = calculate_cascade_potential(board)

    return board
```

---

### Algorithm: Near-Miss Psychology

Near-misses create the psychological sensation of being "so close" to a big match. The brain perceives these as "almost wins" and increases engagement.

**Near-miss patterns:**
- Two gems in a row with the third gem just one swap away from creating a match
- A 4-match that would exist if one gem were different
- Special gem "almost" in position to clear a lucrative area

```
apply_near_miss_tuning(board, near_miss_factor, rng):
    target_near_misses = int(board.width * board.height * near_miss_factor * 0.1)
    current_near_misses = count_near_misses(board)

    while current_near_misses < target_near_misses:
        # Find a position where we can create a near-miss
        position = find_near_miss_candidate(board, rng)

        if position is None:
            break  # Board saturated with near-misses

        # Create the near-miss pattern
        pattern_type = rng.choice(["horizontal_2", "vertical_2", "l_shape_partial"])

        success = create_near_miss_pattern(board, position, pattern_type, rng)

        if success:
            # Verify no actual match was created
            if not has_matches(board):
                current_near_misses += 1
            else:
                # Undo - this would be a real match
                revert_near_miss(board, position, pattern_type)

    return board

def count_near_misses(board):
    """Count patterns that are one swap away from a match."""
    count = 0

    for row in range(board.height):
        for col in range(board.width):
            # Check horizontal near-miss: XX_X or X_XX
            if col < board.width - 3:
                gems = [board.get(Position(row, col + i)) for i in range(4)]
                if is_near_miss_horizontal(gems):
                    count += 1

            # Check vertical near-miss
            if row < board.height - 3:
                gems = [board.get(Position(row + i, col)) for i in range(4)]
                if is_near_miss_vertical(gems):
                    count += 1

    return count
```

---

### Algorithm: Starting Special Gem Placement

Starting special gems add excitement to the opening board. Placement must avoid creating immediate matches or unfair advantages.

```
place_starting_specials(board, specials, rng):
    placed = []

    for spec in specials:
        if spec.position is not None:
            # Explicit position
            position = spec.position
        else:
            # Random position - avoid edges for some specials
            if spec.gem_type in (GemType.LINE_BLAST_H, GemType.LINE_BLAST_V):
                # Line blasts more impactful in middle rows/cols
                position = find_central_position(board, rng)
            elif spec.gem_type == GemType.RADIAL_BOMB:
                # Bombs best not at corners (partial effect)
                position = find_non_corner_position(board, rng)
            elif spec.gem_type == GemType.CHROMATIC_ORB:
                # Chromatic orbs work anywhere
                position = find_random_position(board, rng)

        # Place the special gem
        board = set_gem(board, position, spec.gem_type)
        placed.append((position, spec.gem_type))

    return board, placed
```

**Placement rules:**
1. Special gems cannot be adjacent to each other (prevents immediate fusion)
2. Maximum 3 starting specials per board (configurable)
3. LINE_BLAST placed in inner 6x6 area for full effect
4. RADIAL_BOMB placed at least 1 cell from edge
5. CHROMATIC_ORB can be placed anywhere

---

### Algorithm: Cascade Potential Calculation

This metric quantifies how "lucky" a board is for producing chain reactions.

```
calculate_cascade_potential(board) -> float:
    score = 0.0
    max_score = 0.0

    # Factor 1: Pre-existing favorable patterns (weight: 40%)
    favorable_patterns = count_favorable_patterns(board)
    max_patterns = board.width * board.height // 4  # Theoretical max
    score += 0.4 * (favorable_patterns / max_patterns)
    max_score += 0.4

    # Factor 2: Vertical alignment (cascades come from above) (weight: 30%)
    vertical_score = calculate_vertical_alignment_score(board)
    score += 0.3 * vertical_score
    max_score += 0.3

    # Factor 3: Color clustering (tight clusters cascade more) (weight: 20%)
    clustering = calculate_color_clustering(board)
    score += 0.2 * clustering
    max_score += 0.2

    # Factor 4: Valid move density (more moves = more cascade opportunity) (weight: 10%)
    valid_moves = count_valid_moves(board)
    max_moves = (board.width - 1) * board.height + board.width * (board.height - 1)
    score += 0.1 * (valid_moves / max_moves)
    max_score += 0.1

    return min(1.0, score / max_score)

def count_favorable_patterns(board):
    """Count patterns likely to cascade."""
    count = 0

    # Pattern: Two gems with gap that could fill (XX_X becomes XXXX after clear)
    for row in range(board.height):
        for col in range(board.width - 3):
            gems = [board.get(Position(row, col + i)) for i in range(4)]
            if gems[0] == gems[1] and gems[0] == gems[3] and gems[2] != gems[0]:
                count += 1

    # Pattern: Vertical pairs that would match if gem above fell
    for col in range(board.width):
        for row in range(board.height - 2):
            if board.get(Position(row, col)) == board.get(Position(row + 1, col)):
                # Two matching vertically - check if gem above differs
                if row > 0 and board.get(Position(row - 1, col)) != board.get(Position(row, col)):
                    count += 1

    return count
```

---

### Algorithm: Deadlock Reshuffle

When a board has no valid moves, we must reshuffle while preserving special gems.

```
regenerate_from_deadlock(board, seed):
    rng = np.random.default_rng(seed)

    # Extract special gem positions
    specials = []
    standard_positions = []

    for row in range(board.height):
        for col in range(board.width):
            pos = Position(row, col)
            gem = board.get(pos)
            if gem < 0:  # Special gem (negative values)
                specials.append((pos, gem))
            else:
                standard_positions.append(pos)

    # Collect all standard gem colors
    standard_gems = [board.get(pos) for pos in standard_positions]

    # Shuffle standard gems
    rng.shuffle(standard_gems)

    # Create new board
    new_grid = board.grid.copy()

    # Place shuffled standard gems
    for pos, gem in zip(standard_positions, standard_gems):
        new_grid[pos.row, pos.col] = gem

    new_board = BoardState(grid=new_grid)

    # Verify no matches and has valid moves
    # If not valid, repeat with evolved seed
    attempt = 0
    while has_matches(new_board) or not has_valid_moves(new_board):
        attempt += 1
        if attempt > 100:
            raise internal_error("Failed to reshuffle deadlocked board")

        seed = evolve_seed(seed)
        rng = np.random.default_rng(seed)
        rng.shuffle(standard_gems)

        for pos, gem in zip(standard_positions, standard_gems):
            new_grid[pos.row, pos.col] = gem

        new_board = BoardState(grid=new_grid)

    return GeneratedBoard(
        board_state=new_board,
        seed=seed,
        generation_metadata=GenerationMetadata(...)
    )
```

---

### Seed Evolution Strategy

For deterministic sub-operations (cascade tuning iterations, near-miss placement, etc.), the seed must evolve predictably:

```python
def evolve_seed(seed: int) -> int:
    """Linear Congruential Generator for seed evolution."""
    return (seed * 1103515245 + 12345) & 0x7FFFFFFF
```

This ensures reproducibility: given the same initial seed and options, the same board is always generated.

---

### Match Type Presets

Each match type maps to specific `BoardGenOptions`:

```python
MATCH_TYPE_PRESETS = {
    MatchType.STANDARD: BoardGenOptions(
        cascade_potential=0.5,
        near_miss_factor=0.3,
        starting_specials=None,
        gem_distribution=None,  # Uniform
    ),
    MatchType.COMPETITIVE: BoardGenOptions(
        cascade_potential=0.4,  # Lower cascade randomness
        near_miss_factor=0.1,   # Minimal psychology
        starting_specials=None,
        gem_distribution=None,
    ),
    MatchType.CASUAL: BoardGenOptions(
        cascade_potential=0.6,  # More cascades = more fun
        near_miss_factor=0.4,   # More engagement hooks
        starting_specials=[StartingSpecial(GemType.RADIAL_BOMB)],  # Start with a bomb!
        gem_distribution=None,
    ),
    MatchType.TUTORIAL: BoardGenOptions(
        cascade_potential=0.7,  # Easy cascades for new players
        near_miss_factor=0.0,   # No psychological pressure
        starting_specials=None,
        gem_distribution={1: 0.2, 2: 0.2, 3: 0.2, 4: 0.2, 5: 0.1, 6: 0.1},  # Fewer colors
    ),
}
```

---

### Immutability Contract

All public methods:
1. Never modify input `BoardState`
2. Always return new data structures
3. Input arrays are copied before any modification

This enables safe concurrent read access and simplifies debugging/testing.

---

## CLI Surface

### Commands

```
chromacrush board-gen generate [--seed SEED] [OPTIONS]
```
Generate a new board with optional parameters.

**Options:**
- `--seed SEED` - RNG seed (random if not provided)
- `--cascade-potential FLOAT` - Cascade potential target (0.0-1.0)
- `--near-miss-factor FLOAT` - Near-miss factor (0.0-1.0)
- `--match-type TYPE` - Match type preset (standard, competitive, casual, tutorial)
- `--starting-special TYPE` - Add a starting special gem (can be repeated)

**Example:**
```bash
$ chromacrush board-gen generate --seed 12345 --cascade-potential 0.7
Board generated:
  Seed: 12345
  Cascade potential: 0.68 (target: 0.70)
  Near-misses: 5
  Valid moves: 24
  Generation time: 2.1ms

Board:
  0 1 2 3 4 5 6 7
0 R B G Y P O R B
1 G Y P O R B G Y
2 P O R B G Y P O
3 ...
```

---

```
chromacrush board-gen for-match --seed SEED --match-type TYPE
```
Generate a board using match type presets.

**Example:**
```bash
$ chromacrush board-gen for-match --seed 12345 --match-type casual
Board generated (casual match):
  Seed: 12345
  Cascade potential: 0.62 (target: 0.60)
  Starting specials: RADIAL_BOMB at (3, 4)
  Valid moves: 28
```

---

```
chromacrush board-gen analyze --board "[[...]]"
```
Analyze an existing board's generation characteristics.

**Example:**
```bash
$ chromacrush board-gen analyze --board "..."
Board Analysis:
  Cascade potential: 0.45
  Near-miss count: 3
  Valid moves: 19
  Color distribution: R=12 B=11 G=10 Y=11 P=10 O=10
  Favorable patterns: 7
```

---

```
chromacrush board-gen validate-seed --seed SEED
```
Check if a seed produces a valid board.

**Example:**
```bash
$ chromacrush board-gen validate-seed --seed 12345
Seed 12345: VALID
  Valid moves: 22
  No initial matches: True
  Deadlock: False
```

---

```
chromacrush board-gen reshuffle --board "[[...]]" --seed SEED
```
Reshuffle a deadlocked board.

**Example:**
```bash
$ chromacrush board-gen reshuffle --board "..." --seed 99999
Reshuffled board:
  Preserved specials: 2
  New valid moves: 18
  Reshuffle attempts: 3
```

---

### CLI Composition

Commands in `src/cli/commands/board_gen_commands.py` use the same `BoardGenService` instance as the main application, injected through the CLI composition root.

---

## Edge Cases & Decisions

### EC-1: Seed Produces Deadlocked Board

**Scenario:** A seed value, through unlikely but possible RNG, produces a board with no valid moves.

**Decision:** The generation algorithm includes a validation loop. If the initial generation results in deadlock, evolve the seed and regenerate. Track attempts in metadata. Fail with `INTERNAL_UNEXPECTED` only after exceeding `max_generation_attempts`.

**Rationale:** Determinism is preserved (evolved seed is deterministic). In practice, deadlock from generation is extremely rare with 6 gem colors on 8x8.

---

### EC-2: Cascade Potential Unreachable

**Scenario:** Requested cascade potential (e.g., 0.95) cannot be achieved without creating matches.

**Decision:** Tune toward target with best-effort approach. Return actual achieved cascade_potential in metadata. If actual differs from target by more than 0.1, log a WARN. Never compromise the no-initial-match guarantee.

**Rationale:** Game integrity (no initial matches) takes priority over tuning precision. The small variance is acceptable.

---

### EC-3: Near-Miss Creates Actual Match

**Scenario:** Placing a near-miss pattern inadvertently creates a 3-in-a-row.

**Decision:** Near-miss placement includes match verification. If a match would be created, the placement is rejected and another position is tried.

**Rationale:** Near-misses must feel "almost there" but never actually be matches.

---

### EC-4: All Starting Special Positions Requested Explicitly

**Scenario:** User provides explicit positions for all starting specials, but two positions are adjacent.

**Decision:** Validate that no two starting specials are adjacent. If adjacent positions are requested, return `VALIDATION_INVALID_INPUT`.

**Rationale:** Adjacent special gems can be accidentally fused on first move, which may not be the intended experience.

---

### EC-5: Gem Distribution Weights Are Zero

**Scenario:** User provides `gem_distribution` with all zeros or negative weights.

**Decision:** Validate that weights sum to a positive value. If not, return `VALIDATION_INVALID_INPUT`.

**Rationale:** Cannot sample from a zero or negative probability distribution.

---

### EC-6: Tutorial Mode Generates Too-Easy Board

**Scenario:** Tutorial board has obvious 4-match or 5-match immediately available.

**Decision:** Tutorial mode intentionally generates favorable boards. Having an obvious good move is a feature, not a bug. Do not artificially limit first-move quality.

**Rationale:** Tutorials should teach players that big matches are exciting and achievable.

---

### EC-7: Competitive Mode Cascade Potential Too Low

**Scenario:** Competitive preset with 0.4 cascade potential creates a "boring" board.

**Decision:** Competitive mode prioritizes fairness over excitement. Both players get the same board, so lower cascade potential reduces luck factor. The slight reduction in "fun" is acceptable for competitive integrity.

**Rationale:** Competitive players prefer skill-based outcomes over lucky cascades.

---

### EC-8: Maximum Starting Specials Exceeded

**Scenario:** User requests more starting specials than `max_starting_specials` config allows.

**Decision:** Return `VALIDATION_INVALID_INPUT` with `count` and `max_allowed` in context.

**Rationale:** Too many starting specials unbalances the game. The limit is a design constraint.

---

### EC-9: Generation Performance on Large Boards

**Scenario:** Non-standard large board (e.g., 16x16) takes longer to generate.

**Decision:** The algorithm complexity is O(width * height * tuning_iterations). For large boards, tuning iterations should be reduced. Log a WARN if generation exceeds 100ms.

**Rationale:** Generation should remain interactive. If large boards are common, consider async generation as a future enhancement.

---

## Open Questions

None. All design decisions resolved within existing guidance and project requirements.

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent (board_gen) |
