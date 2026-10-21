# Board Gen Module — Stage 2 P0 Interface Compliance Report

**Reviewer:** Karen P0 Reviewer
**Date:** 2026-02-06
**Reference:** `docs/guidance/interface-contracts.md` (v1.0)
**Files reviewed:**
- `src/modules/board_gen/types.py`
- `src/modules/board_gen/protocols.py`
- `src/modules/board_gen/service.py`
- `src/modules/board_gen/__init__.py`

---

## Protocol Status

The board_gen module is not specified in interface-contracts.md §4 (which covers board §4.1, match §4.2, player §4.3, auth §4.4). The module defines its own `BoardGenServiceProtocol` and a local `BoardServiceProtocol` in `protocols.py`. Since the contract does not prescribe a specific protocol for board_gen, P0 checks focus on:
1. Error codes used must be from the §2.2 taxonomy
2. Type aliases must use the §1 type registry
3. Types consumed from core must not be redefined
4. The locally defined `BoardServiceProtocol` must be compatible with the actual board module's interface

---

## Local BoardServiceProtocol Drift

The `protocols.py` defines a minimal `BoardServiceProtocol` with these methods:

```python
def create_board(self, width: int, height: int, seed: int) -> BoardState
def detect_matches(self, board: BoardState) -> MatchResult
def validate_board(self, board: BoardState) -> bool
def has_valid_moves(self, board: BoardState) -> bool
```

[P0] [src/modules/board_gen/protocols.py:24] `BoardServiceProtocol.detect_matches(self, board: BoardState) -> MatchResult` is missing the `min_length: int = 3` parameter → The actual board module's `detect_matches` signature is `detect_matches(self, board: BoardState, min_length: int = 3) -> MatchResult` per interface-contracts.md §4.1 and the implementation at `src/modules/board/service.py:160`. While the default means this is technically call-compatible, the protocol signature should match exactly for structural typing correctness. The protocol should be `def detect_matches(self, board: BoardState, min_length: int = 3) -> MatchResult: ...`

[P0] [src/modules/board_gen/protocols.py:26-28] `BoardServiceProtocol` includes `validate_board` and `has_valid_moves` which are NOT part of the canonical `BoardServiceProtocol` defined in interface-contracts.md §4.1 → These methods exist in the board service implementation but are not part of the contract's protocol. If the board module creates its `protocols.py` per the contract, these methods will not be included. The board_gen protocol either needs these methods added to the board contract, or board_gen needs to work without them.

---

## Error Codes — Compliant

All error codes used in the board_gen service match the error taxonomy in §2.2:
- `VALIDATION_INVALID_INPUT` — correct (§2.2 Validation Errors)
- `VALIDATION_OUT_OF_BOUNDS` — correct (§2.2 Validation Errors)
- `INTERNAL_UNEXPECTED` — correct (§2.2 Internal Errors)

No other error codes are used. All errors are raised through the injected `ErrorServiceProtocol`.

---

## Type Aliases — Compliant

The module correctly imports from `src.core.types` and does not redefine:
- `BoardState` from `src.core.types.board`
- `GemType`, `Position` from `src.core.types.game`

---

## DTO / Dataclass Shape Review

### MatchType (types.py:12-18)
- Enum with values: `STANDARD`, `COMPETITIVE`, `CASUAL`, `TUTORIAL`
- Module-local enum, not specified in interface-contracts.md, acceptable

### StartingSpecial (types.py:21-26)
- `gem_type: GemType` — uses core type, correct
- `position: Position | None = None` — uses core type, correct

### BoardGenOptions (types.py:29-41)
- `width: int | None`, `height: int | None`, `cascade_potential: float | None`, `near_miss_factor: float | None`, `starting_specials: list[StartingSpecial] | None`, `gem_distribution: dict[int, float] | None`
- All types are standard Python or module-local, correct

### GenerationMetadata (types.py:44-57)
- Fields use standard Python types and core types (`Position`, `GemType`) — correct

### GeneratedBoard (types.py:60-66)
- `board_state: BoardState` — uses core type, correct
- `seed: int` — correct
- `generation_metadata: GenerationMetadata` — module-local type, correct

---

## Protocol Method Signature Review — BoardGenServiceProtocol

The `BoardGenServiceProtocol` in `protocols.py` compared to `BoardGenService` in `service.py`:

| Method | Protocol (protocols.py) | Implementation (service.py) | Match? |
|--------|------------------------|-----------------------------|--------|
| `generate_board` | `(seed: int, options: BoardGenOptions \| None = None) -> GeneratedBoard` | Same | Yes |
| `generate_board_for_match` | `(seed: int, match_type: MatchType = MatchType.STANDARD) -> GeneratedBoard` | Same | Yes |
| `validate_seed` | `(seed: int) -> bool` | Same | Yes |
| `regenerate_from_deadlock` | `(board: BoardState, seed: int) -> GeneratedBoard` | Same | Yes |
| `calculate_cascade_potential` | `(board: BoardState) -> float` | Same | Yes |

All `BoardGenServiceProtocol` methods match the implementation exactly.

---

## Cross-Module Dependency: SpecialGemsServiceProtocol

The `service.py` imports `SpecialGemsServiceProtocol` from `src.modules.special_gems.protocols` (service.py:36). The service uses `special_gems_service.is_special_gem()` which is defined on the protocol. This is correct and uses the injected protocol pattern.

---

## Summary

Two P0 issues found, both in the local `BoardServiceProtocol`:

1. **`detect_matches` signature drift** — missing `min_length: int = 3` parameter compared to the canonical board service interface
2. **Extra methods** — `validate_board` and `has_valid_moves` are included in the local protocol but are not part of the canonical `BoardServiceProtocol` per interface-contracts.md §4.1. These methods are used by the board_gen service and exist in the board service implementation, but they are not in the contract. This creates a dependency on undocumented interface surface area.

All other aspects (error codes, type aliases, DTO shapes, own protocol methods) are compliant.
