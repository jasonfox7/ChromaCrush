# Module Report: scoring

## Header
- **Author:** Scout Agent (scoring)
- **Date:** 2026-02-05

---

## Summary

The scoring module was designed as a **pure calculation layer** that transforms match detection results from the board module into point values with detailed breakdowns. Key design outcomes:

1. **Three-tier scoring model:**
   - Base points per gem (configurable, default 50)
   - Length multipliers for 4+ matches (2x to 5x)
   - Chain multipliers for cascade combos (1x to 3x)

2. **Special gem integration:**
   - Creation bonuses when matches create special gems
   - Activation bonuses when special gems clear additional gems
   - Configurable per-gem-type bonus structure

3. **Detailed breakdowns:**
   - Every score returns full breakdown showing how points were calculated
   - Enables rich UI feedback (score popups, multiplier callouts)
   - Supports replay/audit functionality

4. **Synchronous, pure design:**
   - No I/O, no async, no persistence
   - All state passed in as parameters, returned as immutable results
   - Thread-safe for concurrent reads

5. **Full configurability:**
   - All scoring parameters in config (base points, multipliers, bonuses)
   - Enables game balance tuning without code changes
   - Supports A/B testing of scoring models

---

## Alternatives Considered

### Alternative 1: Scoring Embedded in Board Module

**Considered:** Making scoring calculations part of the board module's `process_move` output.

**Rejected because:**
- Violates single responsibility principle
- Makes board module harder to test (mixing grid logic with arithmetic)
- Prevents scoring rule changes without touching board code
- scoring and special_gems both need scoring logic; embedding creates duplication

**Selected approach:** Separate scoring module with clear interface contracts.

---

### Alternative 2: Event-Based Scoring

**Considered:** Scoring module subscribes to match events and maintains running totals.

**Rejected because:**
- Adds unnecessary complexity for a synchronous calculation
- Makes testing harder (event ordering, subscription setup)
- State management overhead for what should be a pure function
- No benefit — board module already provides complete move results

**Selected approach:** Pure functions that calculate scores from complete match results.

---

### Alternative 3: Multiplier Tables as Database

**Considered:** Storing multiplier configurations in PostgreSQL for runtime updates.

**Rejected because:**
- Overkill for infrequently-changed game balance parameters
- Adds I/O to what should be a pure calculation
- Config service already supports hot-reloading via environment
- Database dependency creates testing complexity

**Selected approach:** Config service with file-based defaults, environment overrides.

---

### Alternative 4: Floating Point Scores

**Considered:** Using float for all score calculations to allow fractional bonuses.

**Rejected because:**
- Match-3 games traditionally use integer scores (player expectation)
- Floating point display complexity (rounding, formatting)
- No gameplay benefit from fractional points
- Integer arithmetic is faster and deterministic

**Selected approach:** All multipliers are floats, but final scores are always integers.

---

## Risks

### Risk 1: Score Inflation in Long Cascades

**Risk:** Chain multipliers combined with length multipliers could create unexpectedly high scores from lucky moves.

**Likelihood:** Medium
**Impact:** Medium (affects game balance and player psychology)

**Mitigation:**
- Chain multiplier capped at 3.0x (configurable)
- Length multiplier capped at 5.0x (configurable)
- All parameters tunable without code changes
- Detailed breakdowns enable analytics on score distributions

---

### Risk 2: Configuration Drift

**Risk:** Scoring config changes in production without corresponding documentation updates.

**Likelihood:** Low
**Impact:** Low (gameplay issue, not technical)

**Mitigation:**
- CLI command `scoring show-multipliers` displays current config
- Logging at service init records all cached config values
- Config validation rejects invalid values with warnings

---

### Risk 3: Integration Complexity with Special Gems

**Risk:** Coordination between scoring, special_gems, and match modules for activation bonuses may be error-prone.

**Likelihood:** Medium
**Impact:** Low (fixable in implementation)

**Mitigation:**
- Clear interface contracts: scoring provides primitives, match orchestrates
- Special gem bonuses calculated via explicit API call, not implicit
- Comprehensive edge cases documented in artifact

---

### Risk 4: Score Audit Trail

**Risk:** No persistent record of how scores were calculated (only final totals stored).

**Likelihood:** Low
**Impact:** Low (affects debugging, not gameplay)

**Mitigation:**
- Detailed MoveScore objects can be serialized for logging
- DEBUG-level logging captures score breakdowns
- Future enhancement: match module could store full breakdown JSON

---

## Dependencies & Sequencing Notes

### Build Order Position

- **Wave 2** in the scouting and implementation sequence
- Depends on: `board` (Wave 1) for type definitions
- Depended on by: `special_gems` (Wave 3), `match` (Wave 5)

### Dependencies

| Dependency | Type | What's Needed |
|------------|------|---------------|
| `board` artifact | Must exist | `MatchResult`, `MatchGroup`, `MoveProcessingResult` type definitions |
| `src/core/types/board.py` | Import | Shared types for match data |
| `src/core/types/game.py` | Import | `GemType` enum |
| Configuration guidance | Reference | Config key naming conventions |
| Interface guidance | Reference | Error taxonomy |

### Type Imports (No Module Dependencies)

The scoring module imports types from `src/core/types/`, NOT from the board module directly:
```python
from src.core.types.board import MatchResult, MatchGroup, MoveProcessingResult
from src.core.types.game import GemType
```

This follows Interface Agent guidance: shared types live in core, modules don't import each other.

### Coordination with special_gems

The `special_gems` module (Wave 3) will call `calculate_special_gem_bonus` for activation bonuses. This is a clean API call, not a circular dependency — special_gems depends on scoring, not vice versa.

### Coordination with match

The `match` module (Wave 5) orchestrates the full scoring flow:
1. Calls board.process_move to get MoveProcessingResult
2. Calls scoring.calculate_move_score to get MoveScore
3. Stores total in match record
4. Returns breakdown to presentation layer

The match module may also coordinate special gem activation bonuses by calling scoring and special_gems in sequence.

### Implementation Priority

Within Wave 2, scoring can be implemented in parallel with `auth` and `energy` (which depend on `player`). No inter-dependencies within the wave.

### Testing Notes

Scoring module is highly testable:
- Pure functions with no mocks needed for repositories
- Only config/logger/errors services need mocking
- Fixtures: predefined MatchResult objects for various scenarios
- Edge case coverage straightforward (all documented in artifact)

---

## Implementation Recommendations

1. **Start with multiplier lookup functions** — these are self-contained and easy to test.

2. **Add MatchGroupScore calculation** — test with single match groups first.

3. **Build up to MatchScore** — combine group scores with chain multiplier.

4. **Implement MoveScore last** — it aggregates CascadeStepScores.

5. **CLI commands should exercise the full chain** — useful for manual verification.

6. **Consider adding summary/display methods** — useful for debugging and CLI output.

---

*End of Module Report*
