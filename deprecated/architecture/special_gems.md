# Module Architecture Report: special_gems

**Module:** special_gems
**Build Wave:** 3
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The special_gems module handles all special gem mechanics in ChromaCrush: effect calculation for four gem types (LINE_BLAST_H, LINE_BLAST_V, RADIAL_BOMB, CHROMATIC_ORB), a fusion system for six combination types when two special gems are swapped together, chain reaction detection, and special gem creation rules from match results. All operations are **synchronous** (`def`, not `async def`) and perform pure computation on in-memory data with no I/O. The module separates effect calculation from application, enabling callers to inspect effects before applying them.

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `is_special_gem` | `(gem_type: GemType) -> bool` | Check if a gem type is special |
| `calculate_effect` | `(board: BoardState, position: Position, target_color: GemType \| None) -> SpecialGemEffect` | Calculate activation effect for a special gem |
| `calculate_fusion_effect` | `(board: BoardState, pos_a: Position, pos_b: Position, target_color: GemType \| None) -> FusionEffect` | Calculate fusion effect of two adjacent special gems |
| `apply_effect` | `(board: BoardState, effect: SpecialGemEffect \| FusionEffect) -> tuple[BoardState, list[Position]]` | Apply calculated effect to board, returning new board and cleared positions |
| `get_special_gem_for_match` | `(match_result: MatchResult) -> tuple[GemType, Position] \| None` | Determine which special gem a match creates |
| `find_triggered_special_gems` | `(board: BoardState, cleared_positions: set[Position]) -> list[Position]` | Find special gems in cleared area for chain reactions |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Board dimensions, bomb radii, chain reaction toggle |
| `logger` | `LoggerProtocol` | Structured logging for effects, fusions, chain triggers |
| `errors` | `ErrorServiceProtocol` | Create validation errors |
| `scoring_service` | `ScoringServiceProtocol` | Calculate activation bonus scores via `calculate_special_gem_bonus()` |

The module defines its own minimal `ScoringServiceProtocol` in `protocols.py` with only the single method it requires.

---

## 4. Data Owned

**Stateless.** No persistence layer. All operations are pure computation on data structures passed as arguments.

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `game.board_width` | int | 8 | Board width for boundary clipping |
| `game.board_height` | int | 8 | Board height for boundary clipping |
| `special_gems.radial_bomb_radius` | int | 1 | Radius for single Radial Bomb (3x3 at default) |
| `special_gems.mega_bomb_radius` | int | 2 | Radius for Radial+Radial fusion (5x5 at default) |
| `special_gems.triple_line_count` | int | 3 | Lines cleared by Line+Radial fusion |
| `special_gems.chain_reaction_enabled` | bool | True | Whether chain reactions are active |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_OUT_OF_BOUNDS` | 400 | Position outside grid bounds |
| `VALIDATION_INVALID_GEM_SWAP` | 400 | Position does not contain a special gem |
| `VALIDATION_INVALID_INPUT` | 400 | Missing/invalid target color, empty match result, unknown fusion combination |
| `VALIDATION_POSITIONS_NOT_ADJACENT` | 400 | Fusion positions not adjacent |

---

## 7. Cross-Module Interactions

**Called by:**
- `board_gen` -- uses `is_special_gem()` for special gem type validation during board generation
- `match` -- coordinates special gem activation during move processing; calls `calculate_effect()`, `calculate_fusion_effect()`, `apply_effect()`, and `find_triggered_special_gems()`

**Calls:**
- `scoring` -- calls `calculate_special_gem_bonus()` for bonus score calculation

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `SpecialGemEffect` | `src/modules/special_gems/types.py` | Activation effect: affected positions, bonus score, chain triggers (frozen) |
| `FusionEffect` | `src/modules/special_gems/types.py` | Fusion effect: two sources, secondary effects, fusion type (frozen) |
| `FusionType` | `src/modules/special_gems/types.py` | Enum: CROSS_BLAST, TRIPLE_LINE, COLOR_LINE_BLAST, MEGA_BOMB, COLOR_BOMB, BOARD_CLEAR |
| `SPECIAL_GEM_TYPES` | `src/modules/special_gems/types.py` | Frozenset of the four special gem GemType values |
| `STANDARD_GEM_TYPES` | `src/modules/special_gems/types.py` | Frozenset of the six standard gem GemType values |
| `SpecialGemsServiceProtocol` | `src/modules/special_gems/protocols.py` | Protocol mirroring all 6 public methods for DI |
