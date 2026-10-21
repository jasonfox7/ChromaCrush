# Special Gems Module — Stage 2 P0 Interface Compliance Report

**Reviewer:** Karen P0 Reviewer
**Date:** 2026-02-06
**Reference:** `docs/guidance/interface-contracts.md` (v1.0)
**Files reviewed:**
- `src/modules/special_gems/types.py`
- `src/modules/special_gems/protocols.py`
- `src/modules/special_gems/service.py`
- `src/modules/special_gems/__init__.py`

---

## Protocol Status

The special_gems module is not specified in interface-contracts.md §4 (which covers board §4.1, match §4.2, player §4.3, auth §4.4). The module defines its own `SpecialGemsServiceProtocol` in `protocols.py`. Since the contract does not prescribe a specific protocol for this module, P0 checks focus on:
1. Error codes used must be from the §2.2 taxonomy
2. Type aliases must use the §1 type registry
3. Types consumed from core must not be redefined
4. The locally defined `ScoringServiceProtocol` must match the scoring module's actual interface

---

## Error Codes — Compliant

All error codes used in the special_gems service match the error taxonomy in §2.2:
- `VALIDATION_OUT_OF_BOUNDS` — correct (§2.2 Validation Errors)
- `VALIDATION_INVALID_GEM_SWAP` — correct (§2.2 Validation Errors)
- `VALIDATION_POSITIONS_NOT_ADJACENT` — correct (§2.2 Validation Errors)
- `VALIDATION_INVALID_INPUT` — correct (§2.2 Validation Errors)

No other error codes are used. All errors are raised through the injected `ErrorServiceProtocol`.

---

## Type Aliases — Compliant

The module correctly imports from `src.core.types` and does not redefine:
- `BoardState`, `MatchResult` from `src.core.types.board`
- `GemType`, `Position` from `src.core.types.game`

---

## Local ScoringServiceProtocol Consistency Check

The `protocols.py` defines a minimal `ScoringServiceProtocol` with:
```python
def calculate_special_gem_bonus(self, gem_type: GemType, gems_affected: int) -> SpecialGemBonus
```

Compared to the actual `ScoringService.calculate_special_gem_bonus` (scoring/service.py:333-412):
```python
def calculate_special_gem_bonus(self, gem_type: GemType, gems_affected: int) -> SpecialGemBonus
```

These match exactly. No P0 issue.

---

## DTO / Dataclass Shape Review

### SpecialGemEffect (types.py:46-64)
- `gem_type: GemType` — uses core type, correct
- `source_position: Position` — uses core type, correct
- `affected_positions: frozenset[Position]` — uses core type, correct
- `bonus_score: SpecialGemBonus` — uses scoring module type, correct
- `triggers_special_gems: list[Position]` — uses core type, correct
- `description: str` — plain string, not presentation formatting, acceptable

### FusionEffect (types.py:67-91)
- `gem_a_type: GemType` — uses core type, correct
- `gem_b_type: GemType` — uses core type, correct
- `fusion_type: FusionType` — uses module-local enum, correct
- `source_positions: tuple[Position, Position]` — uses core type, correct
- `affected_positions: frozenset[Position]` — uses core type, correct
- `bonus_score: SpecialGemBonus` — uses scoring module type, correct
- `triggers_special_gems: list[Position]` — uses core type, correct
- `secondary_effects: list[SpecialGemEffect]` — uses module-local type, correct
- `description: str` — plain string, acceptable

### FusionType (types.py:35-43)
- Enum with values: `CROSS_BLAST`, `TRIPLE_LINE`, `COLOR_LINE_BLAST`, `MEGA_BOMB`, `COLOR_BOMB`, `BOARD_CLEAR`
- Module-local enum, not specified in interface-contracts.md, acceptable for module-internal use

---

## Protocol Method Signature Review

The `SpecialGemsServiceProtocol` in `protocols.py` matches the `SpecialGemsService` implementation in `service.py`:

| Method | Protocol (protocols.py) | Implementation (service.py) | Match? |
|--------|------------------------|-----------------------------|--------|
| `calculate_effect` | `(board: BoardState, position: Position, target_color: GemType \| None = None) -> SpecialGemEffect` | Same | Yes |
| `calculate_fusion_effect` | `(board: BoardState, pos_a: Position, pos_b: Position, target_color: GemType \| None = None) -> FusionEffect` | Same | Yes |
| `apply_effect` | `(board: BoardState, effect: SpecialGemEffect \| FusionEffect) -> tuple[BoardState, list[Position]]` | Same | Yes |
| `is_special_gem` | `(gem_type: GemType) -> bool` | Same | Yes |
| `get_special_gem_for_match` | `(match_result: MatchResult) -> tuple[GemType, Position] \| None` | Same | Yes |
| `find_triggered_special_gems` | `(board: BoardState, cleared_positions: set[Position]) -> list[Position]` | Same | Yes |

All protocol methods match the implementation exactly.

---

## Summary

No P0 issues found.

The special_gems module:
- Uses only valid error codes from §2.2
- Imports shared types correctly from `src.core.types`
- Does not redefine core domain types
- Local `ScoringServiceProtocol` matches the actual scoring service method
- All protocol methods match the implementation
- All dataclass fields use correct types from the type registry
