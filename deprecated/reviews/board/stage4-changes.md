# Stage 4 Change Report: board

**Agent:** Compliance Coder
**Date:** 2026-02-07
**Module:** board
**File modified:** `src/modules/board/service.py`

---

## P3-04 Magic Number Fixes

### Fix 1: Sentinel value in match detection

**Finding:** `service.py:190,216` used inline `-999` sentinel to terminate run detection loops.

**Change:** Defined `_SENTINEL = -999` at module level (line 29). Replaced both inline `-999` occurrences in `detect_matches()` horizontal scan (line 194) and vertical scan (line 220) with `_SENTINEL`.

### Fix 2: LCG constants in cascade seed evolution

**Finding:** `service.py:431` used inline LCG constants `1103515245`, `12345`, `0x7FFFFFFF` for deterministic seed evolution.

**Change:** Defined three module-level constants (lines 30-32):
- `_LCG_MULTIPLIER = 1103515245`
- `_LCG_INCREMENT = 12345`
- `_LCG_MASK = 0x7FFFFFFF`

Replaced inline expression in `process_move()` (line 435) with named constants.

---

## Summary

| Finding | Location | Status |
|---------|----------|--------|
| P3-04 sentinel `-999` | service.py:190,216 | Fixed |
| P3-04 LCG constants | service.py:431 | Fixed |

No behavioural changes. All replacements are value-identical to the original literals.
