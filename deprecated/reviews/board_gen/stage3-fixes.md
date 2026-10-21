# Stage 3 Compliance Review: board_gen

**Reviewer:** Karen Agent (P1-P3)
**Date:** 2026-02-07
**Module:** board_gen
**Files reviewed:**
- `src/modules/board_gen/service.py` (877 lines)
- `src/modules/board_gen/types.py` (67 lines)
- `src/modules/board_gen/protocols.py` (53 lines)
- `src/modules/board_gen/__init__.py` (21 lines)
- `tests/unit/modules/board_gen/test_board_gen_service.py` (581 lines)
- `src/cli/commands/board_gen_commands.py` (185 lines)
- `docs/artifacts/board_gen/artifact.md`

---

## P1 -- Framework Rules

### P1-01: No Direct Service Instantiation
**PASS.** All grep patterns returned no matches in `src/modules/board_gen/`. Dependencies injected via `__init__`. Protocol types imported under `TYPE_CHECKING` only.

### P1-02: No Direct Environment Access
**PASS.** No `os.environ`, `os.getenv`, or `import os` found in module source.

### P1-03: No Bare Raises
**PASS.** All errors raised via `self._errors.validation(...)` or `self._errors.internal(...)`. No bare `raise Exception`, `raise ValueError`, etc.

### P1-04: No UI / Rendering Logic in Modules
**PASS.** No click, rich, print(), or terminal formatting found in `src/modules/board_gen/`.

### P1-05: No Raw Data Access in Business Logic
**PASS.** No SQL, ORM, or data store imports found. Module operates purely on in-memory NumPy arrays.

### P1-06: Async Matches Artifact Spec
**PASS.** Artifact specifies fully synchronous. No `async def`, `asyncio.run()`, or `asyncio.create_task()` found. All public methods are regular `def`.

### P1-07: CLI Exercises Same Code Paths
**PASS.** CLI commands call `svc.generate_board()`, `svc.generate_board_for_match()`, `svc.calculate_cascade_potential()`, `svc.validate_seed()`, and `svc.regenerate_from_deadlock()` -- all public service methods. No direct data access or business logic duplication in CLI.

**Note (non-blocking):** `board_gen_commands.py:38` imports `from tests.mocks.services import MockErrorService, MockLogService` for CLI wiring. Using test mocks in production CLI commands is unusual but does not violate P1-07 since the commands still exercise the same code paths. Consider using real services or a dedicated CLI composition root in a future cleanup.

---

## P2 -- Data Layer & Config Compliance

### P2-01: Config Keys Match Registered Namespaces
**PASS.** Config keys used:
- `game.board_width` -- registered namespace
- `game.board_height` -- registered namespace
- `game.gem_types` -- registered namespace
- `board_gen.default_cascade_potential` -- module-specific, declared in artifact
- `board_gen.default_near_miss_factor` -- module-specific, declared in artifact
- `board_gen.max_generation_attempts` -- module-specific, declared in artifact
- `board_gen.max_starting_specials` -- module-specific, declared in artifact
- `board_gen.enable_near_miss` -- module-specific, declared in artifact
- `board_gen.competitive_cascade_potential` -- module-specific, declared in artifact
- `board_gen.casual_cascade_potential` -- module-specific, declared in artifact
- `board_gen.tutorial_cascade_potential` -- module-specific, declared in artifact

All `board_gen.*` keys are declared in the artifact. The `board_gen` namespace is not in configuration.md -- this is an Orchestrator escalation item to register the namespace, but per checklist rules this does not block.

### P2-02: Repository Pattern Followed
**N/A.** Module has no data access. No repositories needed per artifact.

### P2-03: Data Ownership Respected
**N/A.** Module owns no data per artifact.

### P2-04: Transactions at Service Layer
**N/A.** No database operations.

---

## P3 -- Best Practices & Testing

### P3-01: Service File Length
**FAIL.**

`[P3-01] service.py:1-877 Service file is 877 lines, exceeding the 500-line hard limit -> Split into smaller modules: extract cascade analysis helpers (_count_favorable_patterns, _calculate_vertical_alignment, _calculate_color_clustering, _count_valid_moves) into a separate cascade_analysis.py; extract _apply_cascade_tuning and _apply_near_miss_tuning into tuning.py; extract _place_starting_specials and _find_random_special_position into placement.py`

### P3-02: Function Length
**FAIL.** Multiple functions exceed the 50-line limit:

`[P3-02] service.py:81-196 generate_board() is ~115 lines -> Extract the generation-loop body into a helper method (e.g. _attempt_generation) and the metadata construction into _build_generation_result()`

`[P3-02] service.py:376-459 _validate_options() is ~83 lines -> Extract starting special validation into _validate_starting_specials() and gem distribution validation into _validate_gem_distribution()`

`[P3-02] service.py:557-619 _apply_near_miss_tuning() is ~62 lines -> Acceptable at 62 lines (moderate overage), but could extract the horizontal/vertical near-miss placement branches into helpers`

### P3-03: Constructor Parameters
**PASS.** `__init__` has 5 dependencies (config, logger, errors, board_service, special_gems_service), matching the artifact specification.

### P3-04: No Magic Numbers
**FAIL.** Several significant numeric literals embedded in business logic:

`[P3-04] service.py:516 tolerance = 0.05 -> Define as named constant CASCADE_TUNING_TOLERANCE = 0.05 or pull from config`

`[P3-04] service.py:517 max_iterations = 50 -> Define as named constant CASCADE_TUNING_MAX_ITERATIONS = 50 or pull from config`

`[P3-04] service.py:347 Cascade weight factors 0.4, 0.3, 0.2, 0.1 used inline -> Define as named constants (e.g. CASCADE_WEIGHT_PATTERNS = 0.4, CASCADE_WEIGHT_VERTICAL = 0.3, etc.)`

`[P3-04] service.py:568 factor * 0.1 multiplier -> Define as named constant NEAR_MISS_DENSITY_FACTOR = 0.1`

`[P3-04] service.py:574 max_tries = target_count * 10 -> Define multiplier as named constant NEAR_MISS_MAX_TRIES_MULTIPLIER = 10`

`[P3-04] service.py:679 range(200) fallback loop limit -> Define as named constant SPECIAL_PLACEMENT_MAX_TRIES = 200`

### P3-05: Tests Use Injected Mocks
**PASS.** No `@mock.patch`, `@patch`, or `monkeypatch.setattr` found. All dependencies injected through `__init__` via `_make_service()` helper.

### P3-06: Test Naming Conventions
**PASS.** Test files follow `test_board_gen_service.py` naming. Test classes follow `Test{Name}` convention. Test methods follow `test_{method}_{scenario}` pattern.

### P3-07: Error Path Tests Exist
**FAIL.** One error path from the artifact is not covered:

`[P3-07] test_board_gen_service.py INTERNAL_UNEXPECTED error path (generation exceeds max attempts) is not tested -> Add a test that configures board_gen.max_generation_attempts=1 with conditions that force generation failure, then asserts AppError with code INTERNAL_UNEXPECTED`

Covered error paths: VALIDATION_INVALID_INPUT (cascade_potential, near_miss_factor, dimensions, gem_distribution, starting_specials count, non-special gem type, adjacent specials), VALIDATION_OUT_OF_BOUNDS (starting special position).

### P3-08: Async Tests Properly Structured
**N/A.** Sync module -- no async tests needed.

### P3-09: Type Hints on Service Methods
**PASS.** All public methods have complete parameter and return type annotations.

---

## Summary

| Priority | Count | Details |
|----------|-------|---------|
| P1 | 0 | All framework rule checks pass |
| P2 | 0 | All data/config compliance checks pass |
| P3 | 4 | File length, function length, magic numbers, missing error path test |

### All Findings (consolidated)

```
[P3-01] service.py:1-877 Service file is 877 lines (hard limit 500) -> Split into cascade_analysis.py, tuning.py, placement.py
[P3-02] service.py:81-196 generate_board() is ~115 lines -> Extract helper methods
[P3-02] service.py:376-459 _validate_options() is ~83 lines -> Extract sub-validators
[P3-02] service.py:557-619 _apply_near_miss_tuning() is ~62 lines -> Minor overage, extract branches if splitting file
[P3-04] service.py:516-517 tolerance=0.05, max_iterations=50 -> Named constants
[P3-04] service.py:347 Cascade weights 0.4/0.3/0.2/0.1 inline -> Named constants
[P3-04] service.py:568 Near-miss density factor 0.1 inline -> Named constant
[P3-04] service.py:574 max_tries multiplier 10 inline -> Named constant
[P3-04] service.py:679 Placement fallback loop 200 inline -> Named constant
[P3-07] test_board_gen_service.py Missing INTERNAL_UNEXPECTED error path test -> Add test
```
