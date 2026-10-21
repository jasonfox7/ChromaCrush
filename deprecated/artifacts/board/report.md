# Module Report: board

## Header
- **Author:** Scout Agent (board)
- **Date:** 2026-02-05

---

## Summary

The board module artifact has been designed as the foundational component for ChromaCrush's match-3 gameplay. Key outcomes:

1. **Pure synchronous design** — No async, no I/O, no database dependencies. All operations are deterministic functions on in-memory data.

2. **NumPy-based grid representation** — Using `int8` NDArray for efficient match detection and memory usage. An 8x8 board is only 64 bytes.

3. **Immutable operations** — All methods return new `BoardState` instances without mutating inputs. This enables safe concurrent reads and simplifies testing.

4. **Seeded RNG throughout** — All randomness uses provided seeds for deterministic, reproducible results. Critical for async versus matches.

5. **Complete cascade tracking** — The `MoveProcessingResult` captures every step of a cascade chain, enabling both scoring calculation and frontend animation.

6. **No initial matches guarantee** — Board generation algorithm mathematically ensures no 3-in-a-row at creation.

7. **Special gem detection built-in** — Match detection identifies when matches should create special gems (4-match, 5-match, T/L-shapes), though activation is delegated to `special_gems` module.

---

## Alternatives Considered

### Alternative 1: Nested Python Lists Instead of NumPy

**Considered:** Using `list[list[int]]` for board representation.

**Rejected because:**
- Slower iteration for match detection (no vectorization)
- Higher memory overhead (Python objects vs. raw int8)
- Less convenient slicing operations
- NumPy's `default_rng` provides better seeded randomness

**Kept:** NumPy `int8` arrays. Even for 8x8 boards, the efficiency gains and API conveniences outweigh any added dependency.

---

### Alternative 2: Mutable Board State

**Considered:** Methods that modify `BoardState` in place (e.g., `board.swap(pos1, pos2)`).

**Rejected because:**
- Complicates undo/redo scenarios
- Makes cascade history harder to track (need explicit snapshots)
- Violates functional purity principle
- Thread-safety concerns if boards are shared

**Kept:** Immutable operations returning new states. The copy overhead is negligible for 64-byte arrays.

---

### Alternative 3: Async Match Detection for Large Boards

**Considered:** Making match detection `async` to avoid blocking, especially for future board size expansions.

**Rejected because:**
- 8x8 board match detection is sub-millisecond (< 0.1ms typically)
- Async adds complexity without measurable benefit at this scale
- Would propagate async requirements to all callers
- Board module has no I/O that would benefit from async

**Kept:** Synchronous methods. If board sizes grow significantly (e.g., 100x100), this decision can be revisited.

---

### Alternative 4: Board Class with Methods vs. Service Class

**Considered:** Making `BoardState` itself a rich class with methods like `board.detect_matches()`.

**Rejected because:**
- Violates the service injection pattern
- Makes it harder to inject dependencies (config, logger, errors)
- Mixes data and behavior in ways that complicate testing
- Framework prefers services with injected dependencies

**Kept:** Thin `BoardState` dataclass + `BoardService` with injected dependencies.

---

### Alternative 5: Database-Stored Match History

**Considered:** Having the board module write cascade history to a database for replay.

**Rejected because:**
- Adds unnecessary coupling to data layer
- Board module should be pure computation
- `match` module owns persistence; it can store the `MoveProcessingResult`
- Keeps board module simple and testable

**Kept:** Return cascade data to caller; let upstream modules decide on persistence.

---

### Alternative 6: Different Special Gem Detection Strategies

**Considered approaches:**
1. Post-processing all matches to find overlaps
2. During-detection overlap tracking
3. Separate "special gem analyzer" component

**Chosen:** Option 1 (post-processing). Match detection finds all runs first, then a separate analysis step checks for overlaps and determines special gem type.

**Rationale:** Cleaner separation of concerns. Match detection is already O(width*height); the post-processing overlap check is O(matches^2) but matches are typically < 10.

---

## Risks

### Risk 1: Performance at Scale (Low Likelihood, Low Impact)

**Risk:** Match detection or cascade processing becomes slow with larger boards or more complex cascade chains.

**Mitigation:**
- Current design is O(width * height) for match detection
- 8x8 boards keep this trivial (64 cells)
- Maximum cascade depth limit (100) prevents runaway loops
- NumPy vectorization provides buffer for growth

**Monitoring:** Log cascade duration at DEBUG level for performance baseline.

---

### Risk 2: Seed Collision in Concurrent Matches (Low Likelihood, Medium Impact)

**Risk:** Two matches starting at the exact same millisecond could get the same seed, causing identical boards.

**Mitigation:**
- Seeds are generated by `match` module, not `board`
- Recommend using `(timestamp_ms << 16) | match_id_hash` for seed generation
- Seeds are 64-bit, collision space is enormous

**Note:** This is ultimately the `match` module's responsibility.

---

### Risk 3: Special Gem Interaction Complexity (Medium Likelihood, Medium Impact)

**Risk:** The boundary between `board` (detection) and `special_gems` (activation) may cause confusion or bugs.

**Mitigation:**
- Clear documentation in artifact
- Board module ONLY reports that a special gem should be created
- Board module NEVER triggers special gem effects
- `match` module coordinates: call board.process_move(), then special_gems.activate() if needed

**Escalation path:** If this boundary proves problematic during implementation, escalate to Orchestrator for interface review.

---

### Risk 4: Deadlock Frequency Unknown (Medium Likelihood, Low Impact)

**Risk:** Don't know how often random fills will create deadlock states.

**Mitigation:**
- `has_valid_moves()` check available
- `board_gen` module will tune generation to minimize deadlock likelihood
- `match` module can trigger reshuffle when deadlock detected

**Note:** Deadlock handling is a game design decision outside board module scope.

---

## Dependencies & Sequencing Notes

### Upstream Dependencies

**None.** Board is a Wave 1 leaf node with no module dependencies.

Core service dependencies (all injected):
- `ConfigProtocol` — for board dimensions
- `LoggerProtocol` — for debug/trace logging
- `ErrorServiceProtocol` — for error creation

### Downstream Dependents

The following modules will depend on board:

1. **scoring** (Wave 2) — Needs `MatchResult` to calculate points
2. **special_gems** (Wave 3) — Needs board state and match info for activation effects
3. **board_gen** (Wave 4) — Needs `BoardState` creation, wraps `create_board` with additional tuning
4. **match** (Wave 5) — Needs all board operations for gameplay flow

### Build Order Notes

- Board should be implemented in Phase 2, Wave 1 (first wave of modules)
- Can be implemented in parallel with `player` module (both are Wave 1)
- Should be complete and tested before `scoring` scout begins
- Provides foundational types (`BoardState`, `Position`, `Move`) used by many downstream modules

### Coordination with Type Registry

The following types are defined in `src/core/types/` (per Interface Agent guidance) and used by this module:
- `GemType` (IntEnum)
- `Position` (frozen dataclass)
- `Move` (frozen dataclass)
- `BoardState` (dataclass with NumPy grid)
- `BoardGrid` (type alias for NDArray[np.int8])
- `MatchGroup` (frozen dataclass)
- `MatchResult` (frozen dataclass)

Additional types defined by board module (to be added to type registry):
- `GemDrop` (animation support)
- `GemSpawn` (animation support)
- `CascadeStep` (cascade tracking)
- `MoveProcessingResult` (complete move result)

These should be added to `src/core/types/board.py` during implementation.

---

## Testing Considerations

### Unit Test Categories

1. **Board generation** — Verify no initial matches, correct dimensions, seed determinism
2. **Match detection** — Horizontal, vertical, multiple, overlapping, edge cases
3. **Gravity** — Column-wise fall, multi-step drops, empty board handling
4. **Fill** — Random gem generation, seed determinism
5. **Full move processing** — Cascade chains, chain counting, special gem flagging
6. **Validation** — Invalid boards, out-of-bounds, edge cases
7. **Deadlock detection** — Boards with and without valid moves

### Property-Based Test Opportunities

- Generated boards never have initial matches (for any seed)
- Gravity preserves gem count minus cleared
- Fill operation fills all empty cells
- Determinism: same inputs = same outputs (for any seed)

### Integration Points to Test

- CLI commands exercise all public methods
- Config injection affects board dimensions correctly
- Logger receives expected events at expected severity

---

## Appendix: Type Summary

For quick reference, the complete public type surface:

```python
# From src/core/types/
class GemType(IntEnum): EMPTY, RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE, LINE_BLAST_H, LINE_BLAST_V, RADIAL_BOMB, CHROMATIC_ORB
class Position: row, col, is_adjacent_to()
class Move: from_pos, to_pos, timestamp_ms
class BoardState: grid, width, height, get(), copy(), to_list(), from_list()
class MatchGroup: positions, gem_type, is_horizontal, length
class MatchResult: matches, total_gems_matched, creates_special_gem, special_gem_type, special_gem_position

# Board module additions
class GemDrop: gem_type, from_pos, to_pos, distance
class GemSpawn: gem_type, position, column
class CascadeStep: step_number, matches, board_after_clear, gems_dropped, board_after_gravity, gems_spawned, board_after_fill
class MoveProcessingResult: initial_board, final_board, move, was_valid_match, cascades, total_matches, total_gems_cleared, chain_count, special_gems_created
```

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial report | Scout Agent (board) |
