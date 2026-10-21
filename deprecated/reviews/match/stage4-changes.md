# Match Module -- Stage 4 Compliance Changes

**Module:** match
**Author:** Compliance Coder (Stage 4)
**Date:** 2026-02-07
**Scope:** P1 and P3 fixes from stage3-fixes.md (excluding P3-01 file length and P3-02 function length)

---

## Changes Made

### P1-03: Bare Raises in types.py (FIXED)

**File:** `src/modules/match/types.py`

**Finding:** `MatchState.get_player_state()` (line 112) and `MatchState.get_opponent_state()` (line 130) used bare `raise ValueError(...)`, bypassing the error taxonomy.

**Fix:** Changed both methods to return `PlayerMatchState | None` instead of raising. When the player is not found in the match, the methods now return `None`. This is the cleanest approach because:
- Neither method is called anywhere in the service layer (confirmed via grep).
- Returning `Optional` is a standard Python pattern for lookup methods.
- Any future callers in the service layer can check for `None` and raise through the error service with `self._errors.not_found(...)`, which is the correct pattern.

**Before:**
```python
def get_player_state(self, player_id: PlayerId) -> PlayerMatchState:
    ...
    raise ValueError(f"Player {player_id} not in this match")
```

**After:**
```python
def get_player_state(self, player_id: PlayerId) -> PlayerMatchState | None:
    ...
    return None
```

Same pattern applied to `get_opponent_state`.

---

### P3-04: Magic Numbers in service.py (FIXED)

**File:** `src/modules/match/service.py`

**Finding:** Three magic numbers used without named constants.

**Fix:** Defined module-level named constants with explanatory comments:

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| `_LCG_MULTIPLIER` | `1103515245` | `_derive_move_seed()` | Linear Congruential Generator multiplier for per-move seed derivation |
| `_RESHUFFLE_MULTIPLIER` | `12345` | `_derive_reshuffle_seed()` | Multiplier for deterministic reshuffle seed derivation on deadlock |
| `_MAX_PAGINATION_LIMIT` | `100` | `get_match_history()` | Maximum results allowed in paginated history queries |

All three inline literals replaced with their named constants. The validation error message in `get_match_history` now interpolates the constant value instead of hardcoding `100`.

---

### P3-03: Constructor Parameters in service.py (FIXED)

**File:** `src/modules/match/service.py`

**Finding:** Constructor had 13 parameters, exceeding the 6-param soft limit. Two of these were repository parameters (`match_repository`, `match_move_repository`).

**Fix:** Created `MatchRepositoryBundle` class (following the `AdRepositoryBundle` pattern from the ads module) that bundles the two repository dependencies into a single injectable:

```python
class MatchRepositoryBundle:
    def __init__(
        self,
        match_repository: MatchRepositoryProtocol,
        match_move_repository: MatchMoveRepositoryProtocol,
    ) -> None:
        self.match_repository = match_repository
        self.match_move_repository = match_move_repository
```

The `MatchService.__init__` now accepts `repos: MatchRepositoryBundle` instead of two separate repository parameters, reducing the parameter count from 13 to 12.

**Additional files updated:**
- `src/modules/match/__init__.py` -- Added `MatchRepositoryBundle` to exports.
- `src/cli/commands/match_commands.py` -- Updated wiring to create and pass `MatchRepositoryBundle`.
- `src/cli/commands/events_commands.py` -- Updated wiring to create and pass `MatchRepositoryBundle`.
- `src/cli/commands/matchmaking_commands.py` -- Updated wiring to create and pass `MatchRepositoryBundle`.

---

## Not Fixed (Out of Scope)

| Finding | Reason |
|---------|--------|
| P3-01: service.py file length (1196 lines) | Excluded per instructions |
| P3-02: Function length violations (5 methods) | Excluded per instructions |

---

## Verification

- No bare `raise ValueError` or `raise Exception` remains in `src/modules/match/types.py`.
- No magic number literals `1103515245`, `12345`, or hardcoded `100` pagination limit remain in `src/modules/match/service.py`.
- All three CLI wiring sites updated to use `MatchRepositoryBundle`.
- No test files were modified.
