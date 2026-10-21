# Module Artifact: board

## Header
- **Author:** Scout Agent (board)
- **Date:** 2026-02-05
- **Version:** 1.0
- **Status:** Final
- **Dependencies:** None (Wave 1 leaf node)
- **Dependents:** scoring, special_gems, board_gen, match

---

## Purpose

The **board** module provides the core match-3 grid logic for ChromaCrush. It manages an 8x8 grid of gems, implements swap mechanics for adjacent gems, detects matches (3+ in a row/column), and handles the cascade/gravity system where gems fall and new gems fill empty spaces. This module is the foundation upon which all gameplay modules depend.

The board module is **synchronous** and **pure** — it operates on in-memory state passed in as parameters and returns new state without side effects. There is no database I/O, no network calls, and no async behavior. All randomness uses provided seeds for deterministic, reproducible results (critical for async versus matches where both players must see the same board evolution).

---

## Public Interface

### Class: `BoardService`

The board module exposes a single service class that receives dependencies via `__init__` injection.

```python
class BoardService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        ...
```

---

### Inputs

#### `create_board(width: int, height: int, seed: int) -> BoardState`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `width` | `int` | Board width in cells | Must equal `config.game.board_width` (default 8) |
| `height` | `int` | Board height in cells | Must equal `config.game.board_height` (default 8) |
| `seed` | `int` | RNG seed for deterministic generation | Any valid int64 |

---

#### `swap_gems(board: BoardState, move: Move) -> BoardState`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Current board state | Must be valid BoardState |
| `move` | `Move` | The swap to execute | Positions must be in-bounds and adjacent |

---

#### `detect_matches(board: BoardState, min_length: int = 3) -> MatchResult`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Board state to analyze | Must be valid BoardState |
| `min_length` | `int` | Minimum gems for a match | 3 <= min_length <= board.width |

---

#### `clear_matches(board: BoardState, matches: MatchResult) -> BoardState`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Board state with matches | Must be valid BoardState |
| `matches` | `MatchResult` | Matches to clear | Must be non-empty |

---

#### `apply_gravity(board: BoardState) -> tuple[BoardState, list[GemDrop]]`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Board with empty cells after match clearing | Must be valid BoardState |

---

#### `fill_empty(board: BoardState, seed: int) -> tuple[BoardState, list[GemSpawn]]`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Board after gravity, with top-row empty cells | Must be valid BoardState |
| `seed` | `int` | RNG seed for new gem generation | Any valid int64 |

---

#### `process_move(board: BoardState, move: Move, seed: int) -> MoveProcessingResult`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Starting board state | Must be valid BoardState |
| `move` | `Move` | The move to process | Positions must be in-bounds and adjacent |
| `seed` | `int` | RNG seed for cascades | Any valid int64 |

---

#### `validate_board(board: BoardState) -> bool`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Board to validate | Any BoardState |

---

#### `has_valid_moves(board: BoardState) -> bool`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Board to check for deadlock | Must be valid BoardState |

---

### Outputs

#### `create_board` returns `BoardState`

A new board state with:
- Grid populated with random standard gems (values 1-6)
- No initial 3-in-a-row matches (guaranteed by generation algorithm)
- At least one valid move available

---

#### `swap_gems` returns `BoardState`

A new board state (original unmodified) with the two gem positions exchanged. Does NOT validate whether the swap creates a match — that is the responsibility of the calling code to check via `detect_matches`.

---

#### `detect_matches` returns `MatchResult`

```python
@dataclass(frozen=True)
class MatchResult:
    matches: tuple[MatchGroup, ...]  # All distinct match groups found
    total_gems_matched: int           # Sum of all matched positions (de-duped)
    creates_special_gem: bool         # True if any match length >= 4
    special_gem_type: GemType | None  # The special gem to create (if any)
    special_gem_position: Position | None  # Where to place the special gem
```

Match groups may overlap (e.g., T-shape or L-shape). `total_gems_matched` counts each position only once.

**Special gem creation rules:**
- 4-match horizontal: `LINE_BLAST_H` at intersection point
- 4-match vertical: `LINE_BLAST_V` at intersection point
- 5-match straight: `RADIAL_BOMB` at center
- T-shape or L-shape (3+3 with shared corner): `CHROMATIC_ORB` at intersection

---

#### `clear_matches` returns `BoardState`

A new board state with all matched positions set to `GemType.EMPTY (0)`.

---

#### `apply_gravity` returns `tuple[BoardState, list[GemDrop]]`

```python
@dataclass(frozen=True)
class GemDrop:
    gem_type: GemType
    from_pos: Position
    to_pos: Position
    distance: int  # Number of cells dropped
```

Returns a new board state where:
- All non-empty gems have "fallen" to fill empty spaces below them
- `GemDrop` records track what moved (for animation purposes)

---

#### `fill_empty` returns `tuple[BoardState, list[GemSpawn]]`

```python
@dataclass(frozen=True)
class GemSpawn:
    gem_type: GemType
    position: Position
    column: int  # Which column this gem entered from
```

Returns a new board state where:
- All empty cells in the top row (and any remaining after gravity) are filled with new random standard gems
- `GemSpawn` records track what was created (for animation purposes)

---

#### `process_move` returns `MoveProcessingResult`

```python
@dataclass
class CascadeStep:
    step_number: int
    matches: MatchResult
    board_after_clear: BoardState
    gems_dropped: list[GemDrop]
    board_after_gravity: BoardState
    gems_spawned: list[GemSpawn]
    board_after_fill: BoardState

@dataclass
class MoveProcessingResult:
    initial_board: BoardState
    final_board: BoardState
    move: Move
    was_valid_match: bool  # False if swap created no matches (swap reverted)
    cascades: list[CascadeStep]
    total_matches: int
    total_gems_cleared: int
    chain_count: int  # Number of cascade steps (for chain multiplier)
    special_gems_created: list[tuple[Position, GemType]]
```

Full move processing:
1. Execute swap
2. Detect matches
3. If no matches: revert swap, return with `was_valid_match=False`
4. If matches: clear, gravity, fill, repeat until no new matches
5. Return complete cascade history

---

#### `validate_board` returns `bool`

- `True` if board dimensions match config, all values are valid GemType, and no structural issues
- `False` otherwise

---

#### `has_valid_moves` returns `bool`

- `True` if at least one adjacent swap would create a 3+ match
- `False` if board is in deadlock state (requires shuffle)

---

### Error Cases

| Condition | Error Code | Error Type | Context Fields |
|-----------|------------|------------|----------------|
| Position row/col negative | `VALIDATION_OUT_OF_BOUNDS` | validation | `position`, `board_width`, `board_height` |
| Position outside grid dimensions | `VALIDATION_OUT_OF_BOUNDS` | validation | `position`, `board_width`, `board_height` |
| Positions not orthogonally adjacent | `VALIDATION_POSITIONS_NOT_ADJACENT` | validation | `from_pos`, `to_pos` |
| Attempting to swap EMPTY cell | `VALIDATION_INVALID_GEM_SWAP` | validation | `from_gem`, `to_gem`, `reason="Cannot swap empty cell"` |
| Board dimensions don't match config | `VALIDATION_INVALID_INPUT` | validation | `field="board_dimensions"`, `expected`, `actual` |
| Invalid gem value in grid | `VALIDATION_INVALID_INPUT` | validation | `field="gem_type"`, `value`, `position` |

---

### Async Behavior

**This module is fully synchronous.**

- All methods are regular `def`, not `async def`
- No I/O operations (no database, no network, no file system)
- No async imports or dependencies
- Thread-safe for read operations (immutable inputs)

Rationale: The board module performs pure computation on in-memory data structures. NumPy operations on an 8x8 grid are sub-millisecond. Async would add complexity without benefit.

---

## Mandatory Service Usage

### Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `game.board_width` | int | 8 | Board width in cells |
| `game.board_height` | int | 8 | Board height in cells |
| `game.gem_types` | int | 6 | Number of standard gem colors (1-6) |
| `game.min_match_length` | int | 3 | Minimum gems for a valid match |

Configuration is read once at service initialization and cached. Board dimensions are validated against config.

---

### Logging Events

| Event | Severity | Trigger | Context |
|-------|----------|---------|---------|
| `board.created` | DEBUG | Board generation complete | `seed`, `width`, `height`, `has_valid_moves` |
| `board.match_detected` | DEBUG | Matches found | `match_count`, `total_gems`, `creates_special` |
| `board.cascade_step` | TRACE | Each cascade iteration | `step`, `matches_found`, `gems_cleared` |
| `board.move_processed` | DEBUG | Full move complete | `was_valid`, `chain_count`, `total_cleared` |
| `board.deadlock_detected` | WARN | No valid moves remain | `board_hash` |
| `board.validation_failed` | WARN | Invalid board state | `reason`, `position` |

---

### Error Types Used

From the error taxonomy (Interface Agent guidance):

- `VALIDATION_OUT_OF_BOUNDS` — Position coordinates outside grid
- `VALIDATION_POSITIONS_NOT_ADJACENT` — Swap positions not orthogonally adjacent
- `VALIDATION_INVALID_GEM_SWAP` — Cannot swap (empty cell or other invalid state)
- `VALIDATION_INVALID_INPUT` — General validation failure (dimensions, gem values)

All errors created through injected `ErrorServiceProtocol`, never bare raises.

---

## Data Access

### Owned Data

**None.**

The board module does not own any persistent data. All board state is passed in as parameters and returned as values. The `match` module owns the persisted board state in the `matches` table (JSONB column).

### Repository Interfaces Required

**None.**

No repository injection needed. This module operates purely on in-memory data structures.

### Data Read from Other Modules

**None.**

The board module has no module dependencies. It receives board state from callers and returns new state.

### Transaction Requirements

**None.**

No database operations, no transactions.

---

## Presentation Boundary

### Business Logic API Surface

The board module exposes pure functions operating on domain types:
- Input: `BoardState`, `Move`, `Position`, seeds
- Output: `BoardState`, `MatchResult`, `MoveProcessingResult`, etc.

All types are defined in `src/core/types/board.py` and `src/core/types/game.py`.

### Adapter Needs

Presentation adapters need to:
1. Convert `BoardState.grid` (NumPy array) to JSON-serializable `list[list[int]]` via `board.to_list()`
2. Convert `CascadeStep` list to animation timeline for frontend
3. Map `GemType` enum values to sprite identifiers

Example adapter output for API:
```python
{
    "board": [[1, 2, 3, ...], ...],  # 8x8 grid as nested lists
    "cascades": [
        {
            "step": 1,
            "matches": [{"positions": [[0,0], [0,1], [0,2]], "gem_type": 1}],
            "gems_dropped": [{"from": [1,0], "to": [3,0], "gem_type": 2}],
            "gems_spawned": [{"position": [0,0], "gem_type": 5}]
        }
    ]
}
```

### What Does NOT Belong in This Module

- No JSON serialization (that's adapter responsibility)
- No animation timing or frame calculations
- No sprite/texture references
- No HTTP response construction
- No terminal formatting or colors

---

## Internal Design

### Core Data Structures

#### BoardGrid

```python
BoardGrid = NDArray[np.int8]  # Shape: (height, width)
```

NumPy int8 array for memory efficiency. Values:
- `0`: Empty cell
- `1-6`: Standard gem colors (RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE)
- `-1`: LINE_BLAST_H (horizontal line blast)
- `-2`: LINE_BLAST_V (vertical line blast)
- `-3`: RADIAL_BOMB
- `-4`: CHROMATIC_ORB

#### Position Indexing

- `grid[row, col]` where `row=0` is top, `col=0` is left
- Position(0, 0) is top-left corner
- Position(7, 7) is bottom-right corner (for 8x8 board)

---

### Algorithm: Board Generation (No Initial Matches)

```
create_board(width, height, seed):
    rng = np.random.default_rng(seed)
    grid = np.zeros((height, width), dtype=np.int8)

    for row in range(height):
        for col in range(width):
            available_gems = [1, 2, 3, 4, 5, 6]  # All standard colors

            # Exclude gems that would create horizontal match
            if col >= 2:
                if grid[row, col-1] == grid[row, col-2] and grid[row, col-1] != 0:
                    available_gems.remove(grid[row, col-1])

            # Exclude gems that would create vertical match
            if row >= 2:
                if grid[row-1, col] == grid[row-2, col] and grid[row-1, col] != 0:
                    if grid[row-1, col] in available_gems:
                        available_gems.remove(grid[row-1, col])

            grid[row, col] = rng.choice(available_gems)

    return BoardState(grid=grid)
```

This guarantees no 3-in-a-row at generation time. Generation is O(width * height).

---

### Algorithm: Match Detection

Uses NumPy vectorized operations for efficiency:

```
detect_matches(board, min_length=3):
    matches = []

    # Horizontal matches
    for row in range(height):
        run_start = 0
        run_gem = board.grid[row, 0]

        for col in range(1, width + 1):
            current = board.grid[row, col] if col < width else -999

            if current == run_gem and run_gem > 0:  # Continue run (standard gems only)
                continue
            else:
                run_length = col - run_start
                if run_length >= min_length:
                    positions = frozenset(Position(row, c) for c in range(run_start, col))
                    matches.append(MatchGroup(positions, GemType(run_gem), is_horizontal=True))
                run_start = col
                run_gem = current

    # Vertical matches (similar logic, iterate columns then rows)
    ...

    # Merge overlapping matches for special gem detection
    return analyze_for_special_gems(matches)
```

**Special Gem Detection Logic:**

1. After finding all horizontal and vertical runs, check for overlaps
2. If a position appears in both a horizontal and vertical match:
   - If both are length 3: T-shape or L-shape -> CHROMATIC_ORB
   - If one is length 4+: prioritize the longer match's special
3. If a single match is length 4: LINE_BLAST (direction matches orientation)
4. If a single match is length 5+: RADIAL_BOMB

---

### Algorithm: Gravity (Column-Wise Fall)

```
apply_gravity(board):
    new_grid = board.grid.copy()
    drops = []

    for col in range(width):
        # Extract column, filter non-empty, stack at bottom
        column = new_grid[:, col]
        non_empty = column[column != 0]
        empty_count = height - len(non_empty)

        # Record drops
        for i, gem in enumerate(non_empty):
            old_row = np.where(column == gem)[0][i]  # Original position
            new_row = empty_count + i  # New position
            if old_row != new_row:
                drops.append(GemDrop(
                    gem_type=GemType(gem),
                    from_pos=Position(old_row, col),
                    to_pos=Position(new_row, col),
                    distance=new_row - old_row
                ))

        # Rebuild column: empties on top, gems below
        new_grid[:, col] = np.concatenate([
            np.zeros(empty_count, dtype=np.int8),
            non_empty
        ])

    return BoardState(grid=new_grid), drops
```

---

### Algorithm: Fill Empty Cells

```
fill_empty(board, seed):
    rng = np.random.default_rng(seed)
    new_grid = board.grid.copy()
    spawns = []

    for col in range(width):
        for row in range(height):
            if new_grid[row, col] == 0:
                gem = rng.integers(1, gem_types + 1)  # 1-6 for standard gems
                new_grid[row, col] = gem
                spawns.append(GemSpawn(
                    gem_type=GemType(gem),
                    position=Position(row, col),
                    column=col
                ))

    return BoardState(grid=new_grid), spawns
```

---

### Algorithm: Full Move Processing

```
process_move(board, move, seed):
    # Step 1: Execute swap
    swapped = swap_gems(board, move)

    # Step 2: Check for matches
    initial_matches = detect_matches(swapped)

    if not initial_matches.matches:
        # Invalid move - no match created, revert
        return MoveProcessingResult(
            initial_board=board,
            final_board=board,  # Unchanged
            move=move,
            was_valid_match=False,
            cascades=[],
            total_matches=0,
            total_gems_cleared=0,
            chain_count=0,
            special_gems_created=[]
        )

    # Step 3: Cascade loop
    cascades = []
    current_board = swapped
    chain = 0
    cascade_seed = seed  # Seed evolution for each cascade step
    total_cleared = 0
    special_gems = []

    while True:
        chain += 1
        matches = detect_matches(current_board)

        if not matches.matches:
            break

        # Track special gem creation
        if matches.creates_special_gem:
            special_gems.append((matches.special_gem_position, matches.special_gem_type))

        # Clear matched gems
        after_clear = clear_matches(current_board, matches)

        # Apply gravity
        after_gravity, drops = apply_gravity(after_clear)

        # Fill empty cells
        cascade_seed = cascade_seed * 1103515245 + 12345  # LCG for seed evolution
        after_fill, spawns = fill_empty(after_gravity, cascade_seed)

        cascades.append(CascadeStep(
            step_number=chain,
            matches=matches,
            board_after_clear=after_clear,
            gems_dropped=drops,
            board_after_gravity=after_gravity,
            gems_spawned=spawns,
            board_after_fill=after_fill
        ))

        total_cleared += matches.total_gems_matched
        current_board = after_fill

    return MoveProcessingResult(
        initial_board=board,
        final_board=current_board,
        move=move,
        was_valid_match=True,
        cascades=cascades,
        total_matches=len(cascades),  # Number of distinct match events
        total_gems_cleared=total_cleared,
        chain_count=len(cascades),
        special_gems_created=special_gems
    )
```

---

### Algorithm: Valid Move Detection (Deadlock Check)

```
has_valid_moves(board):
    # Check every possible adjacent swap
    for row in range(height):
        for col in range(width):
            # Check right swap
            if col < width - 1:
                test_board = swap_positions(board, Position(row, col), Position(row, col+1))
                if detect_matches(test_board).matches:
                    return True

            # Check down swap
            if row < height - 1:
                test_board = swap_positions(board, Position(row, col), Position(row+1, col))
                if detect_matches(test_board).matches:
                    return True

    return False
```

Worst case: O(width * height * match_detection_cost). For 8x8 board, this is ~128 swap tests. Acceptable for sync execution.

---

### Immutability Contract

All public methods:
1. Never modify input `BoardState`
2. Always return new `BoardState` instances
3. Input arrays are copied before any modification

This enables safe concurrent read access and simplifies debugging/testing.

---

### Seed Evolution Strategy

For deterministic cascades, the seed must evolve predictably:

1. Initial `seed` is provided (from match record)
2. Each cascade step derives a new seed: `next_seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF`
3. This Linear Congruential Generator (LCG) ensures reproducibility

Both players in an async match will see identical board evolution given the same initial seed.

---

## CLI Surface

### Commands

```
chromacrush board generate [--seed SEED] [--width W] [--height H]
```
Create and display a new board. Uses config defaults if dimensions not specified.

**Example:**
```bash
$ chromacrush board generate --seed 12345
Board generated (seed=12345):
  0 1 2 3 4 5 6 7
0 R B G Y P O R B
1 G Y P O R B G Y
2 P O R B G Y P O
3 ...
Has valid moves: True
```

---

```
chromacrush board show --board "[[1,2,3,...],...]"
```
Display a board from JSON representation.

---

```
chromacrush board detect-matches --board "[[1,2,3,...],...]"
```
Find and display all matches on the given board.

**Example:**
```bash
$ chromacrush board detect-matches --board "[[1,1,1,2,3,4,5,6],...]"
Matches found: 1
  Match 1: HORIZONTAL, gem_type=RED, positions=[(0,0), (0,1), (0,2)]
Total gems matched: 3
Creates special gem: No
```

---

```
chromacrush board swap --board "[[...]]" --from 0,0 --to 0,1
```
Execute a swap and show the result.

---

```
chromacrush board process-move --board "[[...]]" --from 0,0 --to 0,1 --seed 12345
```
Process a complete move with cascades.

**Example:**
```bash
$ chromacrush board process-move --board "..." --from 0,0 --to 0,1 --seed 12345
Move valid: True
Chain count: 3
Total gems cleared: 15
Cascade 1: 3 matches, 9 gems cleared
Cascade 2: 1 match, 3 gems cleared
Cascade 3: 1 match, 3 gems cleared
Special gems created: LINE_BLAST_H at (2, 3)
Final board:
  ...
```

---

```
chromacrush board validate --board "[[...]]"
```
Check if a board state is valid.

---

```
chromacrush board has-moves --board "[[...]]"
```
Check if any valid moves exist (deadlock detection).

---

### CLI Composition

Commands in `src/cli/commands/board_commands.py` use the same `BoardService` instance as the main application, injected through the CLI composition root.

---

## Edge Cases & Decisions

### EC-1: Multiple Overlapping Matches

**Scenario:** A single move creates multiple distinct match groups that share positions (e.g., T-shape where horizontal and vertical matches share a center gem).

**Decision:** Shared positions are counted only once in `total_gems_matched`. The overlap determines special gem creation:
- T-shape (3H + 3V sharing 1 corner) = CHROMATIC_ORB at intersection
- L-shape (3H + 3V sharing 1 corner) = CHROMATIC_ORB at intersection

**Rationale:** Follows standard match-3 conventions. Special gems reward complex moves.

---

### EC-2: Special Gem in Match

**Scenario:** A match includes a special gem (LINE_BLAST, RADIAL_BOMB, or CHROMATIC_ORB).

**Decision:** The board module clears the special gem position like any other. Special gem **activation** (triggering the line blast effect, etc.) is the responsibility of the `special_gems` module.

**Rationale:** Separation of concerns. Board handles grid state; special_gems handles activation effects. The `match` module coordinates calling both.

---

### EC-3: Cascade Creates No Valid Moves

**Scenario:** After cascade completion, the board has no valid moves (deadlock).

**Decision:** The board module detects and reports deadlock via `has_valid_moves() -> False`. It does NOT automatically shuffle. The `match` module decides how to handle deadlock (typically: reshuffle with same seed deterministically).

**Rationale:** Board is stateless and doesn't make game flow decisions.

---

### EC-4: Maximum Cascade Depth

**Scenario:** Theoretical infinite cascade loop (shouldn't happen with proper RNG, but defensive coding).

**Decision:** Enforce maximum cascade depth of 100. If reached, log a WARN and return current state.

**Rationale:** Defensive programming. In practice, cascades rarely exceed 10 steps.

---

### EC-5: Board Generation Fails to Find Valid State

**Scenario:** Highly unlikely but theoretically possible: the no-initial-match constraint cannot be satisfied with the given seed.

**Decision:** The algorithm always succeeds because at each cell, at least 4 gem types are always available (we can only exclude at most 2: one for horizontal, one for vertical).

**Rationale:** Mathematically guaranteed. No fallback needed.

---

### EC-6: Swap of Same Position

**Scenario:** `move.from_pos == move.to_pos`

**Decision:** Reject with `VALIDATION_POSITIONS_NOT_ADJACENT` (same position is not adjacent to itself).

**Rationale:** Consistent with adjacency validation.

---

### EC-7: Diagonal Swap Attempt

**Scenario:** Positions are diagonally adjacent (e.g., (0,0) to (1,1)).

**Decision:** Reject with `VALIDATION_POSITIONS_NOT_ADJACENT`. Only orthogonal (up/down/left/right) swaps allowed.

**Rationale:** Standard match-3 mechanic. The `Position.is_adjacent_to()` method already enforces this.

---

## Open Questions

None. All design decisions resolved within existing guidance.

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent (board) |
