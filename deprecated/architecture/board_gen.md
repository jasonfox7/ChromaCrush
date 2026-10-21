# Module Architecture Report: board_gen

**Module:** board_gen
**Build Wave:** 4
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The board_gen module handles procedural, deterministic board generation for ChromaCrush. It creates seeded game boards guaranteed to have no initial matches and at least one valid move. Features include cascade potential tuning, near-miss psychology patterns, starting special gem placement, deadlock reshuffling, and match-type presets (standard, competitive, casual, tutorial). All methods are **synchronous** (`def`, not `async def`) -- pure computation on NumPy arrays with no I/O. The module is the highest-complexity core game module, positioned as the sole Wave 4 module.

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `generate_board` | `(seed: int, options: BoardGenOptions \| None) -> GeneratedBoard` | Generate a board with optional tuning overrides |
| `generate_board_for_match` | `(seed: int, match_type: MatchType) -> GeneratedBoard` | Generate using match-type presets |
| `validate_seed` | `(seed: int) -> bool` | Validate a seed produces a valid board |
| `regenerate_from_deadlock` | `(board: BoardState, seed: int) -> GeneratedBoard` | Reshuffle preserving special gems |
| `calculate_cascade_potential` | `(board: BoardState) -> float` | Analyze board's cascade potential (0.0-1.0) |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Board dimensions, generation defaults, match-type presets |
| `logger` | `LoggerProtocol` | Diagnostic logging |
| `errors` | `ErrorServiceProtocol` | Typed error creation |
| `board_service` | `BoardServiceProtocol` | Match detection, board validation, deadlock check |
| `special_gems_service` | `SpecialGemsServiceProtocol` | Special gem type validation for starting specials |

The module defines its own minimal `BoardServiceProtocol` in `protocols.py` with only the 4 methods it requires (`create_board`, `detect_matches`, `validate_board`, `has_valid_moves`).

---

## 4. Data Owned

**Stateless.** No persistence layer. All operations are pure computation returning new board states.

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `game.board_width` | int | 8 | Default board width |
| `game.board_height` | int | 8 | Default board height |
| `game.gem_types` | int | 6 | Number of standard gem colours |
| `board_gen.default_cascade_potential` | float | 0.5 | Default cascade potential target |
| `board_gen.default_near_miss_factor` | float | 0.3 | Default near-miss density |
| `board_gen.max_generation_attempts` | int | 100 | Max retry attempts before failure |
| `board_gen.max_starting_specials` | int | 3 | Maximum starting special gems |
| `board_gen.enable_near_miss` | bool | True | Whether near-miss tuning is active |
| `board_gen.competitive_cascade_potential` | float | 0.4 | Cascade potential for competitive mode |
| `board_gen.casual_cascade_potential` | float | 0.6 | Cascade potential for casual mode |
| `board_gen.tutorial_cascade_potential` | float | 0.7 | Cascade potential for tutorial mode |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_INVALID_INPUT` | 400 | Invalid cascade_potential, near_miss_factor, dimensions, gem_distribution, too many starting specials, non-special gem type, adjacent specials |
| `VALIDATION_OUT_OF_BOUNDS` | 400 | Starting special position outside grid |
| `INTERNAL_UNEXPECTED` | 500 | Generation exceeds max attempts (generate_board, regenerate_from_deadlock) |

---

## 7. Cross-Module Interactions

**Called by:**
- `match` -- uses `generate_board_for_match()` for board creation at match start; uses `regenerate_from_deadlock()` when deadlock detected

**Calls:**
- `board` -- calls `create_board()`, `detect_matches()`, `validate_board()`, `has_valid_moves()`
- `special_gems` -- calls `is_special_gem()` for starting special validation

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `MatchType` | `src/modules/board_gen/types.py` | Enum: STANDARD, COMPETITIVE, CASUAL, TUTORIAL |
| `StartingSpecial` | `src/modules/board_gen/types.py` | Frozen dataclass: gem_type and optional position |
| `BoardGenOptions` | `src/modules/board_gen/types.py` | Frozen dataclass: optional overrides for width, height, cascade, near_miss, specials, distribution |
| `GenerationMetadata` | `src/modules/board_gen/types.py` | Dataclass: width, height, cascade targets/actuals, near_miss_count, specials_placed, valid_moves, attempts, time_ms |
| `GeneratedBoard` | `src/modules/board_gen/types.py` | Dataclass: board_state, seed, generation_metadata |
| `BoardGenServiceProtocol` | `src/modules/board_gen/protocols.py` | Protocol mirroring all 5 public methods for DI |
