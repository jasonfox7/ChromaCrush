# Stage 1 Drift Review: board

**Artifact Report:** `docs/artifacts/board/report.md`
**Implementation Doc:** `docs/implementation/board/implementation.md`
**Reviewer:** Karen (Stage 1 Document Sweep)
**Date:** 2026-02-06

---

## Method Count Comparison

Artifact defines 8 public methods on `BoardService`:
1. `create_board`
2. `swap_gems`
3. `detect_matches`
4. `clear_matches`
5. `apply_gravity`
6. `fill_empty`
7. `process_move`
8. `validate_board`
9. `has_valid_moves`

(Corrected: 9 public methods in artifact.)

Implementation doc documents 9 public methods: `create_board`, `swap_gems`, `detect_matches`, `clear_matches`, `apply_gravity`, `fill_empty`, `process_move`, `validate_board`, `has_valid_moves`.

All 9 artifact methods are present in the implementation doc. No undocumented public methods.

---

## Findings

[DRIFT] Artifact error cases list `VALIDATION_INVALID_INPUT` for board dimensions and invalid gem values in `validate_board` -> Implementation doc does not mention `VALIDATION_INVALID_INPUT` in its Error Codes Used table (Section 7). Only `VALIDATION_OUT_OF_BOUNDS`, `VALIDATION_POSITIONS_NOT_ADJACENT`, and `VALIDATION_INVALID_GEM_SWAP` are listed.

[DRIFT] Artifact specifies `validate_board` should raise `VALIDATION_INVALID_INPUT` for bad dimensions and invalid gem values -> Implementation doc describes `validate_board` as returning `bool` with no mention of raising errors for these conditions.

[DRIFT] Artifact specifies `game.min_match_length` config key as used for minimum match validation -> Implementation doc (Section 6) notes `self._min_match_length` is cached but "not used within the service code" -- `detect_matches` uses a parameter default of `3` instead. This is a config key that is read but functionally dead.

[DRIFT] Artifact CLI section lists 7 commands: `generate`, `show`, `detect-matches`, `swap`, `process-move`, `validate`, `has-moves` -> Implementation doc CLI section lists 4 commands: `generate`, `detect-matches`, `process-move`, `has-moves`. Commands `show`, `swap`, and `validate` appear to be missing from the implementation.

[DRIFT] Artifact `CascadeStep` dataclass has no default values -> Implementation doc shows `CascadeStep` with `default_factory=list` for `gems_dropped`/`gems_spawned` and `default=None` for `board_after_gravity`/`board_after_fill`. Minor structural addition but changes the immutability expectation.

[DRIFT] Artifact special gem detection: "4-match horizontal: `LINE_BLAST_H` at intersection point" -> Implementation doc special gem priority: "4-match horizontal produces `LINE_BLAST_H` at the middle position (sorted, index `len//2`)". Placement logic described differently ("intersection point" vs "middle position of sorted positions").

---

## Document Health

Implementation doc is 222 lines -- adequate depth.

No document-level drift detected on: public interface shapes (inputs/outputs), async behavior (all sync), data access (none), dependency injection pattern (config/logger/errors), type definitions (GemDrop, GemSpawn, CascadeStep, MoveProcessingResult).

---

## Summary

6 drift items found. The missing CLI commands and the dead `min_match_length` config key are the most significant for Stage 3 code scrutiny.
