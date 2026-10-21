# Board Gen Module Implementation Document

**Module:** board_gen
**Phase:** 2.2
**Author:** Coding Agent
**Date:** 2026-02-06

---

## 1. Summary

The board_gen module handles procedural, deterministic board generation for ChromaCrush. It creates seeded game boards guaranteed to have no initial matches and at least one valid move. Features include cascade potential tuning, near-miss psychology patterns, starting special gem placement, deadlock reshuffling, and match-type presets (standard, competitive, casual, tutorial). All methods are synchronous — pure computation on NumPy arrays with no I/O.

## 2. Files Created

### Module Code (`src/modules/board_gen/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Exports `BoardGenService`, `BoardGenServiceProtocol`, all type classes |
| `types.py` | `MatchType`, `StartingSpecial`, `BoardGenOptions`, `GenerationMetadata`, `GeneratedBoard` |
| `protocols.py` | `BoardGenServiceProtocol` (5 methods), `BoardServiceProtocol` (4 methods) |
| `service.py` | `BoardGenService` — full implementation with generation, tuning, analysis |

### Data Layer (`src/data/`)
None — this module has no persistence layer.

### CLI (`src/cli/commands/`)
| File | Purpose |
|------|---------|
| `board_gen_commands.py` | Click group "board-gen" with generate, for-match, analyze, validate-seed, reshuffle |

### Tests (`tests/unit/modules/board_gen/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Package marker |
| `test_board_gen_service.py` | 62 tests: generation, options, specials, match types, validation, seed evolution, cascade, metadata, edge cases |

## 3. Deviations from Artifact
Not assessed — document produced from code examination only.

## 4. Public Interface

### `BoardGenService`

```python
def __init__(
    self,
    config: ConfigProtocol,
    logger: LoggerProtocol,
    errors: ErrorServiceProtocol,
    board_service: BoardServiceProtocol,
    special_gems_service: SpecialGemsServiceProtocol,
) -> None
```

| Method | Signature | Return Type |
|--------|-----------|-------------|
| `generate_board` | `(seed: int, options: BoardGenOptions \| None = None)` | `GeneratedBoard` |
| `generate_board_for_match` | `(seed: int, match_type: MatchType = MatchType.STANDARD)` | `GeneratedBoard` |
| `validate_seed` | `(seed: int)` | `bool` |
| `regenerate_from_deadlock` | `(board: BoardState, seed: int)` | `GeneratedBoard` |
| `calculate_cascade_potential` | `(board: BoardState)` | `float` |

### Types

| Type | Kind | Description |
|------|------|-------------|
| `MatchType` | Enum | STANDARD, COMPETITIVE, CASUAL, TUTORIAL |
| `StartingSpecial` | frozen dataclass | `gem_type: GemType`, `position: Position \| None` |
| `BoardGenOptions` | frozen dataclass | Optional overrides: width, height, cascade_potential, near_miss_factor, starting_specials, gem_distribution |
| `GenerationMetadata` | dataclass | width, height, cascade targets/actuals, near_miss_count, specials_placed, valid_moves, attempts, time_ms |
| `GeneratedBoard` | dataclass | board_state, seed, generation_metadata |

### Protocols

| Protocol | Methods |
|----------|---------|
| `BoardGenServiceProtocol` | generate_board, generate_board_for_match, validate_seed, regenerate_from_deadlock, calculate_cascade_potential |
| `BoardServiceProtocol` | create_board, detect_matches, validate_board, has_valid_moves |

## 5. Dependencies Injected

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Board dimensions, generation defaults |
| `logger` | `LoggerProtocol` | Diagnostic logging |
| `errors` | `ErrorServiceProtocol` | Typed error creation |
| `board_service` | `BoardServiceProtocol` | Match detection, board validation |
| `special_gems_service` | `SpecialGemsServiceProtocol` | Special gem type validation |

## 6. Configuration Keys Used

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `game.board_width` | int | 8 | Default board width |
| `game.board_height` | int | 8 | Default board height |
| `game.gem_types` | int | 6 | Number of standard gem colours |
| `board_gen.default_cascade_potential` | float | 0.5 | Default cascade potential target |
| `board_gen.default_near_miss_factor` | float | 0.3 | Default near-miss psychology factor |
| `board_gen.max_generation_attempts` | int | 100 | Max retry attempts before failure |
| `board_gen.max_starting_specials` | int | 3 | Maximum starting special gems |
| `board_gen.enable_near_miss` | bool | True | Whether near-miss tuning is active |
| `board_gen.competitive_cascade_potential` | float | 0.4 | Cascade potential for competitive |
| `board_gen.casual_cascade_potential` | float | 0.6 | Cascade potential for casual |
| `board_gen.tutorial_cascade_potential` | float | 0.7 | Cascade potential for tutorial |

## 7. Error Codes Used

| Code | Method(s) |
|------|-----------|
| `VALIDATION_INVALID_INPUT` | generate_board (cascade_potential, near_miss_factor, dimensions, gem_distribution, starting_specials count, non-special gem type, adjacent specials) |
| `VALIDATION_OUT_OF_BOUNDS` | generate_board (starting special position outside grid) |
| `INTERNAL_UNEXPECTED` | generate_board, regenerate_from_deadlock (max attempts exceeded) |

## 8. Async Behavior

Fully synchronous — all methods are regular `def`. No I/O, no database, no network. Thread-safe for read operations (immutable inputs, new state returned). Uses `time.perf_counter()` for timing.

## 9. Internal Design Notes

### Base Board Generation
Cell-by-cell fill using `np.random.default_rng(seed)`. At each cell, excludes gems that would create horizontal or vertical 3-in-a-row (checks 2 left and 2 above). With 6 gem types and at most 2 exclusions, ≥4 colours always available — algorithm always succeeds. Supports weighted gem distribution via probability arrays.

### Cascade Potential Tuning
Iterative optimization (max 50 iterations, tolerance 0.05). Picks random positions, tries alternative gems, accepts changes that move cascade potential closer to target without creating matches. Uses `_would_create_match` for fast local validation instead of full `detect_matches`.

### Cascade Potential Calculation
Four weighted factors: favorable patterns (40% — XX_X gaps, vertical pairs), vertical alignment (30% — same-colour with gap), colour clustering (20% — adjacent same-colour density), valid move density (10%). Returns clamped 0.0-1.0.

### Near-Miss Tuning
Target count = `int(width * height * factor * 0.1)`. Places horizontal near-miss patterns (two same-colour adjacent gems where a third would complete a match). Each placement verified to not create actual matches.

### Starting Special Placement
Special gems placed at explicit or random positions. Line blasts and radial bombs placed in inner area (1 cell from edge). No two specials may be adjacent (prevents accidental first-move fusion). Chromatic orbs can be placed anywhere.

### Match-Type Presets
- STANDARD: default cascade, default near_miss
- COMPETITIVE: 0.4 cascade, 0.1 near_miss, no specials
- CASUAL: 0.6 cascade, 0.4 near_miss, one RADIAL_BOMB
- TUTORIAL: 0.7 cascade, 0.0 near_miss, weighted distribution (fewer colour 5/6)

### Seed Evolution
Linear Congruential Generator: `(seed * 1103515245 + 12345) & 0x7FFFFFFF`. Used for retries and deterministic sub-operations.

### Deadlock Reshuffle
Preserves all special gem positions. Collects standard gems, shuffles with seeded RNG, validates no matches + has valid moves. Retries with evolved seed if invalid.
