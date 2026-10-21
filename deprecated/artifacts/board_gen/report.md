# Module Report: board_gen

## Header
- **Author:** Scout Agent (board_gen)
- **Date:** 2026-02-05

---

## Summary

The `board_gen` module has been designed to handle procedural board generation for ChromaCrush with the following key capabilities:

1. **Seeded Deterministic Generation** - Uses `numpy.random.Generator` with provided seeds to ensure identical boards for both players in async versus matches. This is critical for fair competitive play.

2. **No Initial Matches Guarantee** - The generation algorithm mathematically prevents 3-in-a-row matches by excluding conflicting colors at each cell. This guarantee is absolute and does not depend on retries.

3. **Cascade Potential Tuning** - Configurable parameter (0.0-1.0) that biases gem placement to create more or fewer "favorable patterns" that lead to chain reactions. This enables different game modes (competitive vs casual).

4. **Near-Miss Psychology** - Subtle tuning that creates "almost match" patterns to increase player engagement. Research shows near-misses activate similar reward pathways as actual wins, increasing player retention.

5. **Starting Special Gems** - Optional placement of LINE_BLAST, RADIAL_BOMB, or CHROMATIC_ORB gems at board creation for enhanced opening excitement.

6. **Deadlock Reshuffle** - Ability to regenerate a board while preserving special gems when the board reaches a no-valid-moves state during gameplay.

The module is fully synchronous, pure (no side effects), and designed for sub-millisecond performance on standard 8x8 boards.

---

## Alternatives Considered

### Alternative 1: Post-Hoc Match Removal vs Constrained Generation

**Considered:** Generate random board, then scan for and replace matches.

**Rejected:**
- Less efficient (O(n) passes potentially required)
- Non-deterministic iteration count
- More complex code

**Chosen:** Constrained generation that excludes match-creating colors at each cell.
- Single pass, O(width * height)
- Deterministic execution path
- Simpler to verify correctness

### Alternative 2: Separate Near-Miss Module

**Considered:** Create a dedicated `near_miss` module for psychological tuning.

**Rejected:**
- Near-miss logic is tightly coupled to generation
- Separate module would require passing board state back and forth
- Complexity budget doesn't justify separation

**Chosen:** Near-miss tuning as an internal component of `board_gen`.

### Alternative 3: Async Generation for Large Boards

**Considered:** Making generation async to handle potential large board scenarios.

**Rejected:**
- Standard 8x8 boards generate in <5ms
- Async adds complexity to an otherwise pure module
- Callers would need to handle async unnecessarily

**Chosen:** Synchronous generation with WARN logging if generation exceeds 100ms. Future enhancement if large boards become common.

### Alternative 4: Machine Learning for Cascade Prediction

**Considered:** Training a model to predict cascade potential more accurately.

**Rejected:**
- Overkill for initial implementation
- Adds deployment complexity (model files, inference runtime)
- Simple heuristic calculation is sufficient and interpretable

**Chosen:** Weighted heuristic calculation based on pattern counting and clustering metrics.

### Alternative 5: Client-Side Generation

**Considered:** Having clients generate boards with server-provided seeds.

**Rejected:**
- Trust issues (clients could generate favorable boards)
- Consistency issues across platforms
- Server must validate anyway

**Chosen:** Server-side generation with deterministic seeds shared to clients.

---

## Risks

### Risk 1: Near-Miss Perception Varies by Player

**Risk:** Near-miss tuning may feel manipulative to some players or go unnoticed by others.

**Mitigation:**
- Near-miss factor is configurable and can be disabled entirely
- Competitive mode minimizes near-miss tuning
- Transparent: metadata includes near-miss count for debugging/analytics

**Severity:** Low (affects player perception, not game integrity)

### Risk 2: Cascade Potential Tuning Creates Unfair Advantage

**Risk:** If cascade_potential tuning is too aggressive, some boards may be objectively "luckier."

**Mitigation:**
- Both players in a match share the same seed and board
- Competitive mode uses lower cascade potential variance
- Actual cascade_potential is logged in metadata for analysis

**Severity:** Medium (could affect competitive balance if misconfigured)

### Risk 3: Generation Algorithm Edge Cases

**Risk:** Despite mathematical guarantees, edge cases could produce invalid boards.

**Mitigation:**
- Post-generation validation via `board_service.validate_board()`
- Valid moves check via `board_service.has_valid_moves()`
- Retry loop with max attempts before failure
- Extensive unit tests for edge cases

**Severity:** Low (algorithm is mathematically sound)

### Risk 4: Performance on Non-Standard Board Sizes

**Risk:** If the game adds larger boards (12x12, 16x16), generation time could become noticeable.

**Mitigation:**
- Current algorithm scales as O(width * height * tuning_iterations)
- Tuning iterations can be reduced for large boards
- WARN logging for slow generation
- Can be made async in future if needed

**Severity:** Low (not in current scope)

### Risk 5: RNG Quality for Fair Competitive Play

**Risk:** If the RNG is predictable or biased, players could exploit seed patterns.

**Mitigation:**
- Using numpy's modern `default_rng` with PCG64 algorithm
- Seeds are generated server-side with cryptographic randomness
- Seed evolution uses well-known LCG (Linear Congruential Generator)

**Severity:** Low (numpy's RNG is well-tested)

---

## Dependencies & Sequencing Notes

### Dependencies (Must Be Complete Before board_gen Implementation)

1. **board module** (Wave 1)
   - Required interfaces: `BoardState`, `BoardServiceProtocol`
   - Required methods: `validate_board()`, `has_valid_moves()`, `detect_matches()`
   - Artifact status: Complete

2. **special_gems module** (Wave 3)
   - Required interfaces: `GemType` enum values for special gems, `SpecialGemsServiceProtocol`
   - Required methods: `is_special_gem()`
   - Artifact status: Complete

3. **Core services** (Wave 0)
   - ConfigProtocol, LoggerProtocol, ErrorServiceProtocol
   - All defined in guidance documents

### Build Order Position

- **Wave:** 4
- **Parallel with:** None (single module in Wave 4)
- **Blockers:** Depends on board and special_gems being implemented first

### Coordination Needed

1. **With match module:** The `match` module (Wave 5) will be the primary consumer of `board_gen`. Match creation will call `generate_board_for_match()`. Match state machine will call `regenerate_from_deadlock()` when needed.

2. **With config schema:** The Configuration Agent guidance must include the `board_gen.*` config keys defined in this artifact.

3. **With testing strategy:** Test fixtures need deterministic seeds that produce known board states. Document recommended test seeds in test guidance.

### Implementation Notes for Coder

1. All NumPy operations should use `np.int8` for memory efficiency
2. RNG should be created fresh for each generation call using the provided seed
3. Seed evolution must use the documented LCG formula exactly for reproducibility
4. The validation loop should track attempts and include in metadata
5. Tuning algorithms can be optimized later; prioritize correctness first

---

## Appendix: Test Seeds

The following seeds are recommended for testing specific scenarios:

| Seed | Scenario | Expected Behavior |
|------|----------|-------------------|
| 12345 | Standard generation | Valid board, ~0.5 cascade potential |
| 99999 | High cascade potential test | Use with cascade_potential=0.8, verify actual > 0.7 |
| 11111 | Low cascade potential test | Use with cascade_potential=0.2, verify actual < 0.3 |
| 42 | Determinism test | Generate twice, verify identical boards |
| 0 | Edge case: zero seed | Should work normally |
| -1 | Edge case: negative seed | Should work normally (RNG handles negative seeds) |
| 2^31-1 | Edge case: max int32 | Should work normally |

---

*End of Module Report*
