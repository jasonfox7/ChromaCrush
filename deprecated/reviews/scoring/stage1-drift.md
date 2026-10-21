# Stage 1 Drift Review: scoring

**Artifact Report:** `docs/artifacts/scoring/report.md`
**Implementation Doc:** `docs/implementation/scoring/implementation.md`
**Reviewer:** Karen (Stage 1 Document Sweep)
**Date:** 2026-02-06

---

## Method Count Comparison

Artifact defines 6 public methods on `ScoringService`:
1. `calculate_match_score`
2. `calculate_move_score`
3. `calculate_special_gem_bonus`
4. `get_chain_multiplier`
5. `get_match_length_multiplier`
6. `get_base_points`

Implementation doc documents 6 public methods: `calculate_match_score`, `calculate_move_score`, `calculate_special_gem_bonus`, `get_chain_multiplier`, `get_match_length_multiplier`, `get_base_points`.

All 6 artifact methods are present. No undocumented public methods.

---

## Findings

[DRIFT] Artifact defines 5 result types: `MatchGroupScore`, `MatchScore`, `SpecialGemBonus`, `CascadeStepScore`, `MoveScore` -> Implementation doc documents the same 5 types. Match confirmed. Implementation additionally documents a `summary()` method on `MoveScore` which is consistent with the artifact (artifact shows `def summary(self) -> str` in the MoveScore class).

[DRIFT] Artifact specifies only `VALIDATION_INVALID_INPUT` as the error code -> Implementation doc confirms only `errors.validation()` is used throughout. Match confirmed.

[DRIFT] Artifact CLI section lists 4 commands: `calculate-match`, `calculate-move`, `show-multipliers`, `special-gem-bonus` -> Implementation doc CLI section lists 3 commands: `calculate-match`, `show-multipliers`, `special-gem-bonus`. The `calculate-move` command appears missing from the implementation doc.

[DRIFT] Artifact describes `special_gem_bonuses` on `CascadeStepScore` as "Populated when special gems activate" -> Implementation doc Section 4 explicitly states: "`special_gem_bonuses` on each `CascadeStepScore` is always an empty tuple -- special gem activation scoring is noted as being coordinated by the match module." This is a design simplification that leaves the field structurally present but functionally hollow.

[DRIFT] Artifact report mentions types imported from `src/core/types/board.py` -> Implementation doc Section 5 notes that `MoveProcessingResult` is imported from `src.modules.board.types` (not from `src/core/types/`). This is a cross-module import rather than the shared-types-in-core pattern described in the artifact report's Dependencies section.

---

## Document Health

Implementation doc is 244 lines -- thorough depth with detailed internal design notes, config validation strategy, logging levels, and CLI architecture documented.

---

## Summary

3 drift items found: 1 missing CLI command, 1 functionally empty field (special_gem_bonuses always empty tuple), and 1 import path deviation (MoveProcessingResult from board module types instead of core types). The special_gem_bonuses issue is architecturally intentional (deferred to match module orchestration) but represents a gap between artifact intent and implementation reality.
