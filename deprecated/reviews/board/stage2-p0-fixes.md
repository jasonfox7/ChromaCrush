# Board Module — Stage 2 P0 Interface Compliance Report

**Reviewer:** Karen P0 Reviewer
**Date:** 2026-02-06
**Reference:** `docs/guidance/interface-contracts.md` (v1.0)
**Files reviewed:**
- `src/modules/board/types.py`
- `src/modules/board/service.py`
- `src/modules/board/__init__.py`

---

## Missing Protocol File

[P0] [src/modules/board/protocols.py:N/A] No `protocols.py` file exists for the board module → interface-contracts.md §4.1 defines `BoardServiceProtocol` at `src/modules/board/protocols.py`. This file must be created containing the `BoardServiceProtocol`, `MoveProcessingResult`, and `CascadeStep` definitions per the contract.

---

## Method Signature Mismatches

[P0] [src/modules/board/service.py:287] `apply_gravity(self, board: BoardState) -> tuple[BoardState, list[GemDrop]]` — missing `seed: int` parameter and wrong return type → should be `apply_gravity(self, board: BoardState, seed: int) -> tuple[BoardState, int]` per interface-contracts.md §4.1

---

## DTO / Dataclass Shape Mismatches

### MoveProcessingResult (types.py:76-103)

[P0] [src/modules/board/types.py:76-103] `MoveProcessingResult` has wrong field set compared to contract → per interface-contracts.md §4.1, `MoveProcessingResult` should have exactly: `final_board: BoardState`, `cascades: list[CascadeStep]`, `total_score: int`, `special_gems_created: list[tuple[Position, GemType]]`

Specific deviations:

[P0] [src/modules/board/types.py:76] `MoveProcessingResult` is missing field `total_score: int` → required per interface-contracts.md §4.1

[P0] [src/modules/board/types.py:95] `MoveProcessingResult` has extra field `initial_board: BoardState` → not in contract §4.1

[P0] [src/modules/board/types.py:97] `MoveProcessingResult` has extra field `move: Move` → not in contract §4.1

[P0] [src/modules/board/types.py:98] `MoveProcessingResult` has extra field `was_valid_match: bool` → not in contract §4.1

[P0] [src/modules/board/types.py:100] `MoveProcessingResult` has extra field `total_matches: int` → not in contract §4.1

[P0] [src/modules/board/types.py:101] `MoveProcessingResult` has extra field `total_gems_cleared: int` → not in contract §4.1

[P0] [src/modules/board/types.py:102] `MoveProcessingResult` has extra field `chain_count: int` → not in contract §4.1

### CascadeStep (types.py:50-72)

[P0] [src/modules/board/types.py:50-72] `CascadeStep` has wrong field set compared to contract → per interface-contracts.md §4.1, `CascadeStep` should have exactly: `matches: MatchResult`, `board_after_clear: BoardState`, `board_after_gravity: BoardState`, `gems_dropped: int`, `step_score: int`

Specific deviations:

[P0] [src/modules/board/types.py:69] `CascadeStep.gems_dropped` has type `list[GemDrop]` → should be `int` per interface-contracts.md §4.1

[P0] [src/modules/board/types.py:50] `CascadeStep` is missing field `step_score: int` → required per interface-contracts.md §4.1

[P0] [src/modules/board/types.py:66] `CascadeStep` has extra field `step_number: int` → not in contract §4.1

[P0] [src/modules/board/types.py:71] `CascadeStep` has extra field `gems_spawned: list[GemSpawn]` → not in contract §4.1

[P0] [src/modules/board/types.py:72] `CascadeStep` has extra field `board_after_fill: BoardState` → not in contract §4.1

---

## Additional Module-Defined Types Not in Contract

[P0] [src/modules/board/types.py:17-31] `GemDrop` dataclass is defined in the module but not specified in interface-contracts.md §4.1 → Either add to contract or remove from module. This type is used as the return type for `apply_gravity` which itself diverges from contract.

[P0] [src/modules/board/types.py:34-46] `GemSpawn` dataclass is defined in the module but not specified in interface-contracts.md §4.1 → Either add to contract or remove from module. This type is used in `CascadeStep.gems_spawned` which itself diverges from contract.

---

## Service Methods Not in Contract

[P0] [src/modules/board/service.py:271] `clear_matches(self, board: BoardState, matches: MatchResult) -> BoardState` — method exists in implementation but is not in `BoardServiceProtocol` per interface-contracts.md §4.1 → Either add to protocol or make private

[P0] [src/modules/board/service.py:338] `fill_empty(self, board: BoardState, seed: int) -> tuple[BoardState, list[GemSpawn]]` — method exists in implementation but is not in `BoardServiceProtocol` per interface-contracts.md §4.1 → Either add to protocol or make private

[P0] [src/modules/board/service.py:482] `validate_board(self, board: BoardState) -> bool` — method exists in implementation but is not in `BoardServiceProtocol` per interface-contracts.md §4.1 → Either add to protocol or make private

[P0] [src/modules/board/service.py:520] `has_valid_moves(self, board: BoardState) -> bool` — method exists in implementation but is not in `BoardServiceProtocol` per interface-contracts.md §4.1 → Either add to protocol or make private

---

## Error Codes — Compliant

All error codes used in the board service match the error taxonomy in §2.2:
- `VALIDATION_OUT_OF_BOUNDS` — correct (§2.2 Validation Errors)
- `VALIDATION_POSITIONS_NOT_ADJACENT` — correct (§2.2 Validation Errors)
- `VALIDATION_INVALID_GEM_SWAP` — correct (§2.2 Validation Errors)

---

## Type Aliases — Compliant

The module correctly imports from `src.core.types` and does not redefine:
- `BoardState`, `MatchResult`, `MatchGroup` from `src.core.types.board`
- `GemType`, `Move`, `Position` from `src.core.types.game`

---

## Summary

The board module has significant P0 drift in three areas:
1. **Missing protocol file** — no `protocols.py` exists
2. **`apply_gravity` signature mismatch** — missing `seed` parameter, wrong return type
3. **DTO shape drift** — both `MoveProcessingResult` and `CascadeStep` have substantial field differences from the contract

The extra fields and types (`GemDrop`, `GemSpawn`, `initial_board`, `was_valid_match`, etc.) suggest the implementation was designed with richer output than the contract specifies. This needs an Orchestrator decision: either update the contract to match the richer implementation, or trim the implementation to match the contract.
