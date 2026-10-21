# Module Architecture Report: scoring

**Module:** scoring
**Build Wave:** 2
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The scoring module is a pure, synchronous score calculation engine. It transforms match detection results from the board module into point values with detailed breakdowns. The module applies a three-tier scoring model: base points per gem, match-length multipliers for 4+ matches, and chain multipliers for cascade combos. It also calculates special gem creation and activation bonuses. All methods are **synchronous** (`def`, not `async def`) and perform pure arithmetic on in-memory data structures with no I/O, no persistence, and no side effects. All scoring parameters are fully configurable.

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `calculate_match_score` | `(match_result: MatchResult, chain_step: int = 1) -> MatchScore` | Score a single match detection result with chain multiplier |
| `calculate_move_score` | `(move_result: MoveProcessingResult) -> MoveScore` | Score a complete player move across all cascade steps |
| `calculate_special_gem_bonus` | `(gem_type: GemType, gems_affected: int) -> SpecialGemBonus` | Calculate bonus points from special gem activation |
| `get_chain_multiplier` | `(chain_step: int) -> float` | Look up chain multiplier for a cascade step |
| `get_match_length_multiplier` | `(match_length: int) -> float` | Look up length multiplier for a match size |
| `get_base_points` | `(gem_type: GemType) -> int` | Return base points for a standard gem type |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Read scoring parameters at init (all cached) |
| `logger` | `LoggerProtocol` | Structured logging at TRACE, DEBUG, WARN levels |
| `errors` | `ErrorServiceProtocol` | Create validation errors via `errors.validation()` |

No repository or data context dependencies. No module-level service dependencies.

**Note:** The service imports `MoveProcessingResult` from `src.modules.board.types` (cross-module type import, not a service dependency).

---

## 4. Data Owned

**Stateless.** The scoring module has no persistence layer. All computation is pure and in-memory.

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `scoring.base_points` | int | 50 | Points per gem in a match |
| `scoring.chain_multipliers` | list[float] | [1.0, 1.5, 2.0, 2.5, 3.0] | Multiplier per cascade step |
| `scoring.length_multipliers` | list[float] | [1.0, 2.0, 3.0, 4.0, 5.0] | Multiplier per match length (3, 4, 5, 6+) |
| `scoring.special_gem_creation_bonus` | int | 100 | Flat bonus for creating a special gem |
| `scoring.line_blast_activation_bonus` | int | 50 | Base bonus for LINE_BLAST activation |
| `scoring.line_blast_per_gem` | int | 25 | Per-gem bonus for LINE_BLAST |
| `scoring.radial_bomb_activation_bonus` | int | 100 | Base bonus for RADIAL_BOMB activation |
| `scoring.radial_bomb_per_gem` | int | 30 | Per-gem bonus for RADIAL_BOMB |
| `scoring.chromatic_orb_activation_bonus` | int | 200 | Base bonus for CHROMATIC_ORB activation |
| `scoring.chromatic_orb_per_gem` | int | 40 | Per-gem bonus for CHROMATIC_ORB |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_INVALID_INPUT` | 400 | Empty matches, chain_step < 1, invalid move, non-special gem type, negative gems_affected, match_length < 3, non-standard gem type |

Only `errors.validation()` is used throughout. No other error factory methods are called.

---

## 7. Cross-Module Interactions

**Called by:**
- `special_gems` -- calls `calculate_special_gem_bonus()` for activation bonuses
- `match` -- calls `calculate_move_score()` for point calculations after move processing

**Calls:** No other module services. Depends only on core types and board module types.

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `MatchGroupScore` | `src/modules/scoring/types.py` | Per-group score breakdown (frozen) |
| `MatchScore` | `src/modules/scoring/types.py` | Score for a match detection with chain multiplier (frozen) |
| `SpecialGemBonus` | `src/modules/scoring/types.py` | Bonus from special gem activation (frozen) |
| `CascadeStepScore` | `src/modules/scoring/types.py` | Score for one cascade step (frozen) |
| `MoveScore` | `src/modules/scoring/types.py` | Complete move score with cascade breakdown and `summary()` method (frozen) |
