# Stage 3 — P1-P3 Compliance Review: scoring

**Reviewer:** Karen (P1-P3 Sweep)
**Date:** 2026-02-07
**Module:** scoring
**Files reviewed:**
- `src/modules/scoring/service.py` (593 lines)
- `src/modules/scoring/types.py` (132 lines)
- `src/modules/scoring/__init__.py` (19 lines)
- `tests/unit/modules/scoring/test_scoring_service.py` (763 lines)
- `src/cli/commands/scoring_commands.py` (244 lines)
- `docs/artifacts/scoring/artifact.md`

---

## P1 — Framework Rules

### P1-01: No Direct Service Instantiation — PASS
Grep patterns: no matches. All dependencies injected via `__init__`. Protocol imports are under `TYPE_CHECKING` guard — correct pattern.

### P1-02: No Direct Environment Access — PASS
Grep patterns: no matches. No `os.environ`, `os.getenv`, or `import os`.

### P1-03: No Bare Raises — PASS
Grep patterns: no matches. All errors use `self._errors.validation(...)`.

### P1-04: No UI / Rendering Logic in Modules — PASS
Grep patterns: no matches. No click, rich, print, or HTTP imports.

### P1-05: No Raw Data Access in Business Logic — PASS
Grep patterns: no matches.

### P1-06: Async Matches Artifact Spec — PASS
Scoring is specified as fully synchronous. One grep hit for `async def` is in a docstring comment (line 7: "All methods are synchronous ``def`` (not ``async def``)"). No actual async methods. No `asyncio.run()` or `asyncio.create_task()`.

### P1-07: CLI Exercises Same Code Paths — FAIL

[P1] [src/cli/commands/scoring_commands.py:142] `show-multipliers` command accesses private attributes (`scoring_svc._base_points`, `scoring_svc._chain_multipliers`, `scoring_svc._length_multipliers`, `scoring_svc._special_gem_creation_bonus`, `scoring_svc._line_blast_activation_bonus`, `scoring_svc._line_blast_per_gem`, `scoring_svc._radial_bomb_activation_bonus`, `scoring_svc._radial_bomb_per_gem`, `scoring_svc._chromatic_orb_activation_bonus`, `scoring_svc._chromatic_orb_per_gem`) instead of using the public service API -> Refactor to use `get_base_points()`, `get_chain_multiplier()`, `get_match_length_multiplier()` for multiplier display. For special gem config, either expose a public method on `ScoringService` (e.g., `get_scoring_config() -> ScoringConfig`) or add public read-only properties.

**Note:** The artifact specifies 4 CLI commands but only 3 are implemented (missing `calculate-move`). This is an interface completeness gap, not a P1 compliance violation. Likely already flagged in Stage 2 P0 review.

---

## P2 — Data Layer & Config Compliance

### P2-01: Config Keys Match Registered Namespaces — FLAG (escalation)

Config keys used:
- `scoring.base_points`
- `scoring.chain_multipliers`
- `scoring.length_multipliers`
- `scoring.special_gem_creation_bonus`
- `scoring.line_blast_activation_bonus`
- `scoring.line_blast_per_gem`
- `scoring.radial_bomb_activation_bonus`
- `scoring.radial_bomb_per_gem`
- `scoring.chromatic_orb_activation_bonus`
- `scoring.chromatic_orb_per_gem`

The `scoring` namespace is NOT listed in configuration.md registered namespaces table. However, ALL of these keys are explicitly declared in the scoring artifact (lines 232-243).

**Escalation:** The entire `scoring.*` namespace is declared in the artifact but missing from configuration.md. Orchestrator should add the `scoring` namespace with all 10 keys to the registered namespaces table.

### P2-02: Repository Pattern — N/A
Scoring module has no data access. No repositories required.

### P2-03: Data Ownership — N/A
Scoring module owns no persistent data.

### P2-04: Transactions at Service Layer — N/A
No database operations.

---

## P3 — Best Practices & Testing

### P3-01: Service File Length — FAIL

[P3] [src/modules/scoring/service.py] 593 lines exceeds hard limit of 500 -> Extract config validation helpers into a separate `_config_validation.py` module, or extract the lengthy `calculate_match_score` and `calculate_special_gem_bonus` methods to reduce total size below 500 lines.

### P3-02: Function Length — FAIL

[P3] [src/modules/scoring/service.py:65] `__init__` is ~68 lines, exceeds 50-line limit -> Extract config loading and validation into a private `_load_config()` helper method called from `__init__`.

[P3] [src/modules/scoring/service.py:138] `calculate_match_score` is ~114 lines, exceeds 50-line limit -> Extract match group scoring loop into a private `_score_match_groups()` method, and logging into a separate step.

[P3] [src/modules/scoring/service.py:253] `calculate_move_score` is ~79 lines, exceeds 50-line limit -> Extract cascade scoring loop into a private `_score_cascades()` method.

[P3] [src/modules/scoring/service.py:333] `calculate_special_gem_bonus` is ~80 lines, exceeds 50-line limit -> Extract gem-type-to-config mapping into a private lookup method or dictionary.

### P3-03: Constructor Parameters — PASS
`__init__` has 3 parameters (config, logger, errors). Matches artifact exactly.

### P3-04: Magic Numbers — PASS
Numeric literals in scoring service are all configuration defaults (50, 100, 25, 30, 200, 40) used as fallback values in `config.get()` and `_validate_positive_int()` calls. These are contextually clear as config defaults.

### P3-05: Tests Use Injected Mocks — PASS
No `@mock.patch`, `@patch`, `monkeypatch.setattr` found. All dependencies injected via constructor using `MockConfigService`, `MockErrorService`, `MockLogService`.

### P3-06: Test Naming Conventions — PASS
All test classes follow `Test{ClassName}` pattern. All test methods follow `test_{method}_{scenario}` pattern. Names are descriptive and clear. Good use of sectioned test classes: `TestCalculateMatchScore`, `TestCalculateMoveScore`, `TestCalculateSpecialGemBonus`, `TestMultiplierLookups`, `TestConfiguration`, `TestGetBasePoints`, `TestMoveScoreSummary`, `TestCombinedScoring`.

### P3-07: Error Path Tests Exist — PASS
All error codes from the artifact are tested:
- Empty match result → `test_empty_matches_raises_error`
- Chain step < 1 → `test_chain_step_zero_raises_error`, `test_chain_step_negative_raises_error`
- Match length < 3 → `test_length_multiplier_invalid_raises`
- Invalid gem type for base points → `test_empty_gem_type_raises_error`, `test_special_gem_type_raises_error`
- Special gem bonus on non-special gem → `test_non_special_gem_raises_error`, `test_empty_gem_type_raises_error`
- Invalid move result → `test_invalid_move_raises_error`
- Negative gems affected → `test_negative_gems_affected_raises_error`

### P3-08: Async Tests Properly Structured — PASS
Scoring is a sync module. No async test methods found. Correct.

### P3-09: Type Hints on Service Methods — PASS
All public methods have full parameter and return type annotations.

---

## Summary

| Priority | Count | Details |
|----------|-------|---------|
| P1 | 1 | CLI `show-multipliers` bypasses public API via private attributes |
| P2 | 0 + 1 escalation | `scoring.*` namespace missing from configuration.md (Orchestrator escalation) |
| P3 | 5 | File length (1), function length (4) |

**Recommendation:** P1 finding must be fixed in Stage 4 — `show-multipliers` CLI command should use public service methods instead of accessing private attributes. P3 items should be addressed if time permits. P2 escalation item for Orchestrator to update configuration.md.
