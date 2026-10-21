# Scoring Module — Stage 2 P0 Interface Compliance Report

**Reviewer:** Karen P0 Reviewer
**Date:** 2026-02-06
**Reference:** `docs/guidance/interface-contracts.md` (v1.0)
**Files reviewed:**
- `src/modules/scoring/types.py`
- `src/modules/scoring/service.py`
- `src/modules/scoring/__init__.py`

---

## Missing Protocol File

The scoring module has no `protocols.py`. Interface-contracts.md does not define a dedicated `ScoringServiceProtocol` in its Section 4 module schemas (Sections 4.1-4.4 cover board, match, player, auth). The special_gems module defines a minimal `ScoringServiceProtocol` in its own `protocols.py` covering only `calculate_special_gem_bonus`. Since the contract does not prescribe a scoring protocol, this is not a P0 issue, but is noted for completeness.

---

## Module-Level Protocol Conformance

The scoring module is not explicitly specified in interface-contracts.md §4 (which covers board, match, player, auth). The scoring module's public interface is defined by its artifact, not by §4 of the contracts. Therefore, P0 checks focus on:
1. Error codes used must be from the §2.2 taxonomy
2. Type aliases must use the §1 type registry
3. Types consumed from core must not be redefined

---

## Error Codes — Compliant

All error codes used in the scoring service match the error taxonomy in §2.2:
- `VALIDATION_INVALID_INPUT` — correct (§2.2 Validation Errors)

No other error codes are used. All errors are raised through the injected `ErrorServiceProtocol`.

---

## Type Aliases — Compliant

The module correctly imports from `src.core.types` and does not redefine:
- `MatchResult`, `MatchGroup` from `src.core.types.board`
- `GemType` from `src.core.types.game`

---

## DTO / Dataclass Shape Review

The scoring module defines its own types in `types.py`. These are not specified in interface-contracts.md §4 (scoring has no dedicated section), but they are part of the module's public interface per its artifact. Reviewing for internal consistency and type registry compliance:

### MatchGroupScore (types.py:17-32)
- Fields: `match_group: MatchGroup`, `base_points: int`, `length_multiplier: float`, `length_bonus_points: int`, `subtotal: int`
- Uses `MatchGroup` from `src.core.types.board` — correct

### MatchScore (types.py:35-53)
- Fields: `total_points: int`, `base_points: int`, `chain_multiplier: float`, `chain_step: int`, `match_breakdown: tuple[MatchGroupScore, ...]`, `special_gem_creation_bonus: int`
- All types are standard Python types or module-local types — correct

### SpecialGemBonus (types.py:56-72)
- Fields: `gem_type: GemType`, `base_activation_bonus: int`, `gems_affected: int`, `per_gem_bonus: int`, `total_bonus: int`
- Uses `GemType` from `src.core.types.game` — correct

### CascadeStepScore (types.py:75-87)
- Fields: `step_number: int`, `match_score: MatchScore`, `special_gem_bonuses: tuple[SpecialGemBonus, ...]`
- All types are module-local or standard — correct

### MoveScore (types.py:90-131)
- Fields: `total_points: int`, `cascade_scores: tuple[CascadeStepScore, ...]`, `chain_count: int`, `total_gems_cleared: int`, `highest_chain_multiplier: float`, `special_gems_created: int`, `special_gems_activated: int`
- All types are standard Python types — correct
- Has `summary()` method returning `str` — presentation-adjacent but returns plain text, not formatted HTML/terminal output. Borderline but acceptable as it returns a plain string.

---

## Cross-Module Dependency Check

The scoring service imports `MoveProcessingResult` from `src.modules.board.types` (service.py:20). This is a direct cross-module import. Per the framework rules, module interfaces should be through injected protocols. However, this is a type import for input data (not a service instantiation), and the board module's types are designated as its "public interface for consumption by dependent modules" (board/types.py docstring). This is an architectural concern but not an interface-contracts.md P0 violation.

---

## Summary

No P0 issues found.

The scoring module:
- Uses only valid error codes from §2.2
- Imports shared types correctly from `src.core.types`
- Does not redefine core domain types
- Has no method signature mismatches (scoring is not specified in §4 of interface-contracts.md)
- All dataclass fields use correct types from the type registry
