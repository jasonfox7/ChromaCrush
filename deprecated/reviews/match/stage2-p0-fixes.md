# Match Module - Stage 2 P0 Fix Report

**Reviewer:** Karen P0 (Stage 2 Interface Compliance Sweep)
**Date:** 2026-02-06
**Module:** match
**Files Reviewed:**
- `src/modules/match/protocols.py`
- `src/modules/match/types.py`
- `src/modules/match/dto.py`

**Reference:** `docs/guidance/interface-contracts.md` v1.5, Section 4.2 (Match Module Protocol Schema)

---

## Protocol Signatures

### Method-level findings

```
[P0] [protocols.py:34-40] create_match has extra parameter match_type: MatchType = MatchType.STANDARD -> interface-contracts.md Section 4.2 defines create_match(player1_id: PlayerId, player2_id: PlayerId, board_seed: int | None = None) with NO match_type parameter. per interface-contracts.md Section 4.2

[P0] [protocols.py:88-103] Method named get_match(match_id: MatchId) -> MatchState -> interface-contracts.md Section 4.2 defines this method as get_match_state(match_id: MatchId, for_player_id: PlayerId | None = None) -> MatchState. Method name is wrong AND the for_player_id parameter is missing. per interface-contracts.md Section 4.2

[P0] [protocols.py:105-123] Extra method get_player_board not in interface-contracts.md Section 4.2 -> interface-contracts.md Section 4.2 does not define this method. If this is intentional, the contract must be updated. per interface-contracts.md Section 4.2

[P0] [protocols.py:125-139] Extra method get_active_matches not in interface-contracts.md Section 4.2 -> interface-contracts.md Section 4.2 does not define this method. If this is intentional, the contract must be updated. per interface-contracts.md Section 4.2

[P0] [protocols.py:141-157] Extra method get_match_history not in interface-contracts.md Section 4.2 -> interface-contracts.md Section 4.2 does not define this method. If this is intentional, the contract must be updated. per interface-contracts.md Section 4.2

[P0] [protocols.py:159-176] Extra method get_move_history not in interface-contracts.md Section 4.2 -> interface-contracts.md Section 4.2 does not define this method. If this is intentional, the contract must be updated. per interface-contracts.md Section 4.2

[P0] [protocols.py:199-205] Extra method abandon_stale_matches not in interface-contracts.md Section 4.2 -> interface-contracts.md Section 4.2 does not define this method. If this is intentional, the contract must be updated. per interface-contracts.md Section 4.2
```

### Error code findings

```
[P0] [protocols.py:83] Error code CONFLICT_MATCH_COMPLETED referenced in submit_move docstring -> No such code in interface-contracts.md Section 2.2. The correct code is CONFLICT_MATCH_ALREADY_COMPLETED. per interface-contracts.md Section 2.2

[P0] [protocols.py:195] Error code CONFLICT_MATCH_COMPLETED referenced in forfeit_match docstring -> No such code in interface-contracts.md Section 2.2. The correct code is CONFLICT_MATCH_ALREADY_COMPLETED. per interface-contracts.md Section 2.2
```

## Type Aliases and Core Type Redefinition

```
[P0] [types.py:20-27] Module redefines MatchStatus enum locally -> interface-contracts.md Section 1.3 defines MatchStatus in src/core/types/match.py. Modules must import shared types, not redefine them. per interface-contracts.md Section 1 ("Modules import these types but NEVER define their own versions of shared concepts")

[P0] [types.py:29-35] Module defines new MatchType enum locally -> interface-contracts.md Section 1.3 does not define a MatchType enum. If this is a new shared type, it must be added to src/core/types/ and interface-contracts.md. per interface-contracts.md Section 1

[P0] [types.py:38-56] Module redefines PlayerMatchState dataclass locally -> interface-contracts.md Section 1.3 defines PlayerMatchState in src/core/types/match.py with fields: player_id: PlayerId, score: int = 0, moves_made: list[Move], moves_remaining: int = 20. The local version has entirely different fields (player_username, moves_made as int, current_board, longest_chain, etc.). per interface-contracts.md Section 1.3

[P0] [types.py:59-94] Module redefines MatchState dataclass locally -> interface-contracts.md Section 1.3 defines MatchState in src/core/types/match.py with fields: match_id, board_seed, board, status, player1, player2, current_player_id, winner_id, created_at, completed_at. The local version has different fields (initial_board instead of board, no current_player_id, adds match_type, forfeit_by, started_at, timeout_at). per interface-contracts.md Section 1.3
```

## DTO Shape (MoveSubmissionResult)

```
[P0] [types.py:142-171] MoveSubmissionResult has different shape from interface-contracts.md Section 4.2 -> Contract defines: match_state: MatchState, move_result: MoveProcessingResult, match_completed: bool, winner_id: PlayerId | None = None. Implementation adds 6 extra fields: score_result: MoveScore, special_effects: list[SpecialGemEffect], points_earned: int, move_number: int, moves_remaining: int, player_finished: bool. per interface-contracts.md Section 4.2
```

## Summary

| Check | Result |
|-------|--------|
| Method names | **1 P0 ISSUE** (get_match vs get_match_state) |
| Parameter names/types | **2 P0 ISSUES** (extra match_type param; missing for_player_id param) |
| Return types | PASS (all return MatchState or MoveSubmissionResult) |
| Extra methods | **5 P0 ISSUES** (methods not in contract) |
| Error codes | **2 P0 ISSUES** (CONFLICT_MATCH_COMPLETED should be CONFLICT_MATCH_ALREADY_COMPLETED) |
| Type aliases | PASS (PlayerId, MatchId imported correctly) |
| Core type redefinition | **4 P0 ISSUES** (MatchStatus, MatchType, PlayerMatchState, MatchState redefined locally) |
| DTO shapes | **1 P0 ISSUE** (MoveSubmissionResult has 6 extra fields) |

**Total P0 issues: 15**

This module has significant interface drift. The most critical issues are:
1. **Core type redefinition** -- MatchState, PlayerMatchState, MatchStatus are all redefined locally with different shapes, violating Section 1's rule against duplicate types.
2. **Method name mismatch** -- `get_match` should be `get_match_state` with the `for_player_id` parameter.
3. **Error code typo** -- `CONFLICT_MATCH_COMPLETED` should be `CONFLICT_MATCH_ALREADY_COMPLETED`.

Resolution path: Either (a) the implementation must be refactored to use core types and match the Section 4.2 contract exactly, or (b) the Orchestrator must update interface-contracts.md to reflect the expanded design. Given the magnitude of divergence, Orchestrator decision is required.
