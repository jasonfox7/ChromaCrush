# Stage 4 Karen Compliance Sweep -- events module

**Date:** 2026-02-07
**Agent:** Compliance Coder (Stage 4)
**Module:** events
**Source:** `src/modules/events/service.py`

---

## Findings Addressed

### P3-04: Magic Numbers

All magic number findings from `stage3-fixes.md` have been resolved.

| Finding | Location | Constant Defined | Value |
|---------|----------|-----------------|-------|
| Level thresholds 5, 20, 50, 100 | service.py `_calculate_level` | `_LEVEL_THRESHOLDS` | `[5, 20, 50, 100]` |
| Minimum name length 3 | service.py:127 | `_MIN_EVENT_NAME_LENGTH` | `3` |
| Maximum name length 100 | service.py:134 | `_MAX_EVENT_NAME_LENGTH` | `100` |
| Max list limit 100 | service.py:181, 596 | `_MAX_LIST_LIMIT` | `100` |
| Max leaderboard limit 500 | service.py:468 | `_MAX_LEADERBOARD_LIMIT` | `500` |
| Max cancellation reason length 500 | service.py:776 | `_MAX_REASON_LENGTH` | `500` |

### Changes Made

1. **Added module-level constants** (after imports, before class definition):
   - `_MIN_EVENT_NAME_LENGTH = 3`
   - `_MAX_EVENT_NAME_LENGTH = 100`
   - `_MAX_LIST_LIMIT = 100`
   - `_MAX_LEADERBOARD_LIMIT = 500`
   - `_MAX_REASON_LENGTH = 500`
   - `_LEVEL_THRESHOLDS = [5, 20, 50, 100]`

2. **Replaced all bare numeric literals** with the named constants in:
   - `create_event()` -- name length checks
   - `list_events()` -- limit validation
   - `get_leaderboard()` -- limit validation
   - `get_player_events()` -- limit validation
   - `cancel_event()` -- reason length check
   - `_calculate_level()` -- refactored from explicit if-chain to loop over `_LEVEL_THRESHOLDS`

3. **Updated error messages** to use f-strings referencing the constants, so messages stay in sync with the values.

### Findings NOT Addressed (by design)

- **P3-01** (file length): Not in scope for Stage 4.
- **P3-02** (function length): Not in scope for Stage 4.

### Behavioral Equivalence

All changes are strictly mechanical replacements of literal values with named constants. The `_calculate_level` refactor produces identical output for all possible inputs:
- `total < 5` -> level 1
- `total < 20` -> level 2
- `total < 50` -> level 3
- `total < 100` -> level 4
- `total >= 100` -> level 5 (i.e., `len(_LEVEL_THRESHOLDS) + 1`)
