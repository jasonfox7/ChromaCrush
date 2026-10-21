# Module Report: special_gems

## Header
- **Author:** Scout Agent (special_gems)
- **Date:** 2026-02-05

---

## Summary

The special_gems module has been designed to handle all special gem mechanics in ChromaCrush:

1. **Effect Calculation** - Determines which positions are affected when a special gem is activated (Line Blast, Radial Bomb, Chromatic Orb)

2. **Fusion System** - Implements the 6 fusion types when two special gems are swapped together:
   - Cross Blast (Line + Line)
   - Triple Line (Line + Radial)
   - Color Line Blast (Line + Chromatic)
   - Mega Bomb (Radial + Radial)
   - Color Bomb (Radial + Chromatic)
   - Board Clear (Chromatic + Chromatic)

3. **Chain Reactions** - Detects special gems within affected areas that should trigger as chain reactions

4. **Special Gem Creation Rules** - Determines which special gem (if any) is created from match results

The module is fully synchronous and pure, operating on in-memory data structures with no side effects. This design supports deterministic replay for async versus matches.

### Key Design Outcomes

- **6 public methods** covering all special gem operations
- **2 main output types**: `SpecialGemEffect` and `FusionEffect` with full effect details
- **Integration with scoring** via injected `ScoringService` for bonus calculations
- **Configurable parameters** for effect radii and chain reaction behavior
- **Comprehensive CLI surface** for testing all functionality

---

## Alternatives Considered

### Alternative 1: Effect Execution vs. Calculation

**Considered:** Having the module both calculate AND apply effects in a single method.

**Rejected:** Separating calculation from application follows the single responsibility principle. The `match` module can inspect effects before applying them (useful for AI/bot move evaluation). Animation systems can use the calculated effect data without actually modifying board state.

**Decision:** Provide separate `calculate_effect()` and `apply_effect()` methods.

---

### Alternative 2: Chromatic Orb Target Selection

**Considered:** Auto-selecting target color based on most common gem on board.

**Rejected:** This is a game flow decision that belongs in the `match` module or UI layer. The special_gems module should remain pure and not make game flow decisions.

**Decision:** Require `target_color` as a parameter; validation error if missing for Chromatic operations.

---

### Alternative 3: Recursive Chain Reaction Processing

**Considered:** Having `calculate_effect()` recursively calculate all chain reactions.

**Rejected:** This would make the method complex and harder to test. Chain reactions involve board state changes between activations (gravity, fill). The `match` module is better positioned to coordinate the cascade loop.

**Decision:** Return `triggers_special_gems` list of positions. Let caller handle iteration.

---

### Alternative 4: Fusion Effect Inheritance

**Considered:** Having `FusionEffect` inherit from `SpecialGemEffect`.

**Rejected:** Fusions have distinct properties (two source positions, secondary effects, fusion type). Inheritance would be awkward and potentially confusing.

**Decision:** Separate dataclasses with clear composition (FusionEffect contains a list of secondary `SpecialGemEffect` objects).

---

### Alternative 5: Static vs. Instance Methods

**Considered:** Making effect calculations static methods since they're pure functions.

**Rejected:** Instance methods allow for proper dependency injection (config, logger, errors, scoring_service). Static methods would require passing all dependencies as parameters.

**Decision:** Use instance methods with injected dependencies following framework patterns.

---

## Risks

### Risk 1: Fusion Combination Explosion

**Risk:** The 6 fusion types could grow if new special gems are added.

**Likelihood:** Low (GDD specifies 4 special gem types)

**Mitigation:** Fusion dispatch is centralized in `_calculate_fusion()` method. Adding new combinations is straightforward. Consider a fusion matrix data structure if complexity grows.

---

### Risk 2: Performance with Large Effects

**Risk:** Board Clear and Color Bomb fusions affect many positions (up to 64 for 8x8 board).

**Likelihood:** Low

**Mitigation:** Operations are O(width * height) which is 64 iterations for an 8x8 board. This completes in microseconds. No optimization needed.

---

### Risk 3: Chain Reaction Loops

**Risk:** Theoretical infinite loop if chain reactions could create new special gems that trigger more chains.

**Likelihood:** Very Low

**Mitigation:** Special gems are only created from player moves (matches), not from chain reactions. Chain reactions only activate existing special gems. Additionally, the match module enforces a maximum cascade depth (100 steps).

---

### Risk 4: Chromatic Orb Target Color Confusion

**Risk:** Players may not understand which color the Chromatic Orb will target.

**Likelihood:** Medium (UX concern, not module concern)

**Mitigation:** The module provides clear `target_color` parameter. UI/match module responsible for communicating selection to player. Consider adding color preview in UI.

---

### Risk 5: Edge Position Effects

**Risk:** Effects at board edges may behave unexpectedly (e.g., Radial Bomb at corner only clears 4 positions instead of 9).

**Likelihood:** Low

**Mitigation:** Documented in edge cases. Effects are bounded by board dimensions. This is standard match-3 behavior and players will understand. UI should show effect preview.

---

## Dependencies & Sequencing Notes

### Build Order Position

- **Wave:** 3 (Scout Wave 3)
- **Depends on:**
  - `board` (Wave 1) - BoardState, Position, MatchResult types; GemType enum values
  - `scoring` (Wave 2) - ScoringService for bonus calculations, SpecialGemBonus type

### Dependency Details

**From board module:**
- `BoardState` type for grid representation
- `Position` type for coordinates
- `MatchResult` type for special gem creation detection
- `GemType` enum (especially negative values for special gems)

**From scoring module:**
- `ScoringServiceProtocol` interface (injected)
- `SpecialGemBonus` type for effect bonus scores
- `calculate_special_gem_bonus()` method

### Implementation Dependencies

Before special_gems can be implemented (Phase 2):
1. `src/core/types/game.py` - GemType enum with special gem values (-1 to -4)
2. `src/core/types/board.py` - BoardState, Position, MatchResult types
3. `src/modules/scoring/service.py` - ScoringService with `calculate_special_gem_bonus()` method
4. `src/modules/scoring/types.py` - SpecialGemBonus type

### Downstream Dependents

Modules that will depend on special_gems:
- `board_gen` (Wave 4) - Needs to know special gem positions for board generation validation
- `match` (Wave 5) - Coordinates special gem activation during move processing

### Coordination Notes

1. **With scoring module:** The scoring module artifact defines `SpecialGemBonus` type and `calculate_special_gem_bonus()` method. Verified these exist in scoring artifact.

2. **With board module:** The board module artifact defines special gem creation rules in match detection. This module implements the placement logic that board detects but doesn't enforce.

3. **With match module (future):** The match module will need to:
   - Call `calculate_effect()` when a special gem is activated
   - Call `calculate_fusion_effect()` when two special gems are swapped
   - Process `triggers_special_gems` list for chain reactions
   - Determine Chromatic Orb target color (game flow decision)
   - Apply effects and continue cascade loop

4. **Interface consistency:** All position-based operations use the shared `Position` type from `src/core/types/game.py`. All board state uses `BoardState` from `src/core/types/board.py`.

---

## Artifact Completeness Checklist

- [x] Purpose clearly defined
- [x] Public interface documented (inputs, outputs, errors, async behavior)
- [x] Mandatory service usage documented (config keys, logging events, error types)
- [x] Data access documented (none for this module)
- [x] Presentation boundary defined
- [x] Internal design with algorithms
- [x] CLI surface defined
- [x] Edge cases identified and resolved
- [x] No open questions
- [x] Dependencies verified against existing artifacts
