# Module Architecture Report: board

**Module:** board
**Build Wave:** 1 (Leaf Node)
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The board module is the foundational match-3 grid engine for ChromaCrush. It provides deterministic board generation with no initial matches, gem swapping with validation, horizontal and vertical match detection, gravity simulation, empty cell filling, full move processing with cascade loops, board validation, and deadlock detection. All operations are **synchronous** (`def`, not `async def`) and operate on immutable board state backed by NumPy `int8` arrays. The module performs pure in-memory computation with no I/O, no persistence, and no side effects. Every method returns a new `BoardState` without mutating the input.

**Two-Grid Model:** `BoardState` carries two parallel int8 arrays — `grid` (colors: 0=EMPTY, 1-6=standard colors) and `func_grid` (functions: 0=NEUTRAL, 1-4=special abilities). Match detection reads only `grid`, so colored special gems participate in same-color runs automatically. All grid mutation operations (clear, gravity, fill) operate on both grids in parallel. Special gem placement writes the match's base color to `grid` and the special function to `func_grid`.

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_board` | `(width: int, height: int, seed: int) -> BoardState` | Generate a new board with no initial 3-in-a-row matches |
| `swap_gems` | `(board: BoardState, move: Move) -> BoardState` | Swap two adjacent gems, returning a new board |
| `detect_matches` | `(board: BoardState, min_length: int = 3) -> MatchResult` | Find all horizontal and vertical matches |
| `clear_matches` | `(board: BoardState, matches: MatchResult) -> BoardState` | Set matched positions to EMPTY |
| `apply_gravity` | `(board: BoardState) -> tuple[BoardState, list[GemDrop]]` | Drop gems down to fill empty spaces |
| `fill_empty` | `(board: BoardState, seed: int) -> tuple[BoardState, list[GemSpawn]]` | Fill empty cells with new random gems |
| `process_move` | `(board: BoardState, move: Move, seed: int) -> MoveProcessingResult` | Full move: swap, match, cascade until stable |
| `validate_board` | `(board: BoardState) -> bool` | Check board dimensions and gem value validity |
| `has_valid_moves` | `(board: BoardState) -> bool` | Check for at least one valid swap (deadlock detection) |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Read board dimensions and gem count at init |
| `logger` | `LoggerProtocol` | Structured diagnostic logging |
| `errors` | `ErrorServiceProtocol` | Create typed validation errors |

No repository, data context, or async dependencies. No module-level dependencies.

---

## 4. Data Owned

**Stateless.** The board module has no persistence layer. All operations are pure in-memory computation on NumPy arrays. Board state is passed in and returned; no data is stored.

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `game.board_width` | int | 8 | Default board width |
| `game.board_height` | int | 8 | Default board height |
| `game.gem_types` | int | 6 | Number of standard gem colours |
| `game.min_match_length` | int | 3 | Minimum match length (cached but unused; `detect_matches` uses parameter default) |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_OUT_OF_BOUNDS` | 400 | Position outside grid bounds |
| `VALIDATION_POSITIONS_NOT_ADJACENT` | 400 | Swap positions not orthogonally adjacent |
| `VALIDATION_INVALID_GEM_SWAP` | 400 | Swapping an empty cell |

---

## 7. Cross-Module Interactions

**Called by:**
- `scoring` -- uses `MatchResult` to calculate points
- `special_gems` -- uses board state and match info for activation effects
- `board_gen` -- wraps board creation with tuning; calls `detect_matches`, `validate_board`, `has_valid_moves`
- `match` -- uses all board operations for gameplay flow

**Calls:** No other modules. Board is a leaf node.

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `GemDrop` | `src/modules/board/types.py` | Record of a gem falling due to gravity |
| `GemSpawn` | `src/modules/board/types.py` | Record of a new gem spawned to fill empty cell |
| `CascadeStep` | `src/modules/board/types.py` | One step in the cascade loop (detect-clear-gravity-fill) |
| `MoveProcessingResult` | `src/modules/board/types.py` | Complete result of processing a player's move |
| `BoardState` | `src/core/types/board.py` | NumPy-backed immutable board snapshot with dual grids: `grid` (colors) + `func_grid` (functions) |
| `GemFunction` | `src/core/types/game.py` | Enum: NEUTRAL=0, LINE_BLAST_H=1, LINE_BLAST_V=2, RADIAL_BOMB=3, CHROMATIC_ORB=4 |
| `MatchResult` | `src/core/types/board.py` | Result of match detection (shared core type) |
| `MatchGroup` | `src/core/types/board.py` | A group of matched gems (shared core type) |
