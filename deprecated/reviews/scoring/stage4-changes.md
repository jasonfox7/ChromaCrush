# Stage 4 — Compliance Fixes: scoring

**Date:** 2026-02-07

---

## P1-07: CLI `show-multipliers` accesses private attributes

**Finding:** `src/cli/commands/scoring_commands.py:142` -- the `show-multipliers` command accessed `scoring_svc._base_points`, `scoring_svc._chain_multipliers`, `scoring_svc._length_multipliers`, and all special gem config private attributes directly.

**Fix:**
1. Added `get_scoring_config()` public method to `ScoringService` in `src/modules/scoring/service.py` (line 503). Returns a `dict[str, object]` with all 10 scoring configuration values: `base_points`, `chain_multipliers`, `length_multipliers`, `special_gem_creation_bonus`, `line_blast_activation_bonus`, `line_blast_per_gem`, `radial_bomb_activation_bonus`, `radial_bomb_per_gem`, `chromatic_orb_activation_bonus`, `chromatic_orb_per_gem`.
2. Updated `show_multipliers` command in `src/cli/commands/scoring_commands.py` to call `scoring_svc.get_scoring_config()` and access values via dict keys instead of private attributes.

**Files changed:**
- `src/modules/scoring/service.py` -- added `get_scoring_config()` method
- `src/cli/commands/scoring_commands.py` -- updated `show_multipliers` to use public API

**Not fixed (per instructions):**
- P3-01: File length (593 lines)
- P3-02: Function length (`__init__`, `calculate_match_score`, `calculate_move_score`, `calculate_special_gem_bonus`)
- P3-04: No magic number findings (PASS in Stage 3)
