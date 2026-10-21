# Stage 4 Change Report: board_gen

**Agent:** Compliance Coder
**Date:** 2026-02-07
**Module:** board_gen
**File modified:** `src/modules/board_gen/service.py`

---

## P3-04 Magic Number Fixes

### Fix 1: Cascade tuning tolerance and max iterations

**Finding:** `service.py:516-517` used inline `0.05` tolerance and `50` max iterations in `_apply_cascade_tuning()`.

**Change:** Defined module-level constants:
- `_CASCADE_TUNING_TOLERANCE = 0.05`
- `_CASCADE_TUNING_MAX_ITERATIONS = 50`

Replaced local variable assignments at lines 526-527 with named constants.

### Fix 2: Cascade weight factors

**Finding:** `service.py:347` used inline weight factors `0.4, 0.3, 0.2, 0.1` in `calculate_cascade_potential()`.

**Change:** Defined four module-level constants:
- `_CASCADE_WEIGHT_PATTERNS = 0.4`
- `_CASCADE_WEIGHT_VERTICAL = 0.3`
- `_CASCADE_WEIGHT_CLUSTERING = 0.2`
- `_CASCADE_WEIGHT_MOVE_DENSITY = 0.1`

Replaced inline literals in the weighted sum at line 357 with named constants.

### Fix 3: Near-miss density factor

**Finding:** `service.py:568` used inline `0.1` multiplier in `_apply_near_miss_tuning()`.

**Change:** Defined `_NEAR_MISS_DENSITY_FACTOR = 0.1` at module level. Replaced inline literal at line 578.

### Fix 4: Near-miss max tries multiplier

**Finding:** `service.py:574` used inline `10` multiplier for `max_tries` in `_apply_near_miss_tuning()`.

**Change:** Defined `_NEAR_MISS_MAX_TRIES_MULTIPLIER = 10` at module level. Replaced inline literal at line 584.

### Fix 5: Special placement max tries

**Finding:** `service.py:679` used inline `200` loop limit in `_find_random_special_position()`.

**Change:** Defined `_SPECIAL_PLACEMENT_MAX_TRIES = 200` at module level. Replaced `range(200)` with `range(_SPECIAL_PLACEMENT_MAX_TRIES)` at line 689.

---

## Summary

| Finding | Location | Status |
|---------|----------|--------|
| P3-04 cascade tuning tolerance | service.py:516 | Fixed |
| P3-04 cascade tuning max iterations | service.py:517 | Fixed |
| P3-04 cascade weight factors | service.py:347 | Fixed |
| P3-04 near-miss density factor | service.py:568 | Fixed |
| P3-04 near-miss max tries multiplier | service.py:574 | Fixed |
| P3-04 special placement max tries | service.py:679 | Fixed |

No behavioural changes. All replacements are value-identical to the original literals.
