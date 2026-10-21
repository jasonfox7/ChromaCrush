# Module Artifact: scoring

## Header
- **Author:** Scout Agent (scoring)
- **Date:** 2026-02-05
- **Version:** 1.0
- **Status:** Final
- **Dependencies:** `board` (Wave 1)
- **Dependents:** `special_gems`, `match`

---

## Purpose

The **scoring** module calculates points earned from match-3 actions in ChromaCrush. It takes match results from the `board` module and computes scores based on:

1. **Base points** per gem matched (configurable per gem type)
2. **Match length bonuses** for 4+ matches (linear scaling)
3. **Chain multipliers** that increase with each cascade step
4. **Special gem bonuses** when special gems are created or activated

This module is **synchronous** and **pure** — it performs arithmetic calculations on in-memory data with no I/O, no network calls, and no async behavior. All scoring rules are deterministic and configurable via the config service.

The scoring module returns detailed breakdowns of how points were calculated, enabling the UI to show players exactly why they earned their score (rewarding skilled play with visible feedback).

---

## Public Interface

### Class: `ScoringService`

The scoring module exposes a single service class that receives dependencies via `__init__` injection.

```python
class ScoringService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        ...
```

---

### Inputs

#### `calculate_match_score(match_result: MatchResult, chain_step: int = 1) -> MatchScore`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `match_result` | `MatchResult` | Match detection result from board module | Must be non-empty (at least one match) |
| `chain_step` | `int` | Current cascade step (1 = initial match, 2+ = cascade) | Must be >= 1 |

---

#### `calculate_move_score(move_result: MoveProcessingResult) -> MoveScore`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `move_result` | `MoveProcessingResult` | Complete move processing result from board module | Must have `was_valid_match=True` |

---

#### `calculate_special_gem_bonus(gem_type: GemType, gems_affected: int) -> SpecialGemBonus`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `gem_type` | `GemType` | The special gem type that was activated | Must be a special gem type (negative value) |
| `gems_affected` | `int` | Number of gems cleared by the special gem | Must be >= 0 |

---

#### `get_chain_multiplier(chain_step: int) -> float`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `chain_step` | `int` | The cascade step number | Must be >= 1 |

---

#### `get_match_length_multiplier(match_length: int) -> float`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `match_length` | `int` | Number of gems in the match | Must be >= 3 |

---

#### `get_base_points(gem_type: GemType) -> int`

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `gem_type` | `GemType` | The gem type to get base points for | Must be a standard gem (1-6) |

---

### Outputs

#### `calculate_match_score` returns `MatchScore`

```python
@dataclass(frozen=True)
class MatchScore:
    """Score for a single match detection (may contain multiple match groups)."""
    total_points: int
    base_points: int
    chain_multiplier: float
    chain_step: int
    match_breakdown: tuple[MatchGroupScore, ...]
    special_gem_creation_bonus: int  # Bonus for creating a special gem

@dataclass(frozen=True)
class MatchGroupScore:
    """Score breakdown for a single match group."""
    match_group: MatchGroup
    base_points: int
    length_multiplier: float
    length_bonus_points: int  # Points from length multiplier
    subtotal: int  # base_points * length_multiplier
```

The `total_points` is calculated as:
```
total_points = sum(match.subtotal for match in match_breakdown) * chain_multiplier + special_gem_creation_bonus
```

---

#### `calculate_move_score` returns `MoveScore`

```python
@dataclass(frozen=True)
class CascadeStepScore:
    """Score for a single cascade step."""
    step_number: int
    match_score: MatchScore
    special_gem_bonuses: tuple[SpecialGemBonus, ...]

@dataclass(frozen=True)
class MoveScore:
    """Complete score breakdown for a player's move."""
    total_points: int
    cascade_scores: tuple[CascadeStepScore, ...]
    chain_count: int
    total_gems_cleared: int
    highest_chain_multiplier: float
    special_gems_created: int
    special_gems_activated: int

    def summary(self) -> str:
        """Human-readable summary for UI display."""
        ...
```

---

#### `calculate_special_gem_bonus` returns `SpecialGemBonus`

```python
@dataclass(frozen=True)
class SpecialGemBonus:
    """Bonus points from special gem activation."""
    gem_type: GemType
    base_activation_bonus: int
    gems_affected: int
    per_gem_bonus: int
    total_bonus: int  # base_activation_bonus + (gems_affected * per_gem_bonus)
```

---

#### `get_chain_multiplier` returns `float`

Returns the multiplier for the given chain step:
- Chain 1: `1.0x`
- Chain 2: `1.5x`
- Chain 3: `2.0x`
- Chain 4: `2.5x`
- Chain 5+: `3.0x` (capped)

---

#### `get_match_length_multiplier` returns `float`

Returns the multiplier for match length:
- 3 gems: `1.0x`
- 4 gems: `2.0x`
- 5 gems: `3.0x`
- 6 gems: `4.0x`
- 7+ gems: `5.0x` (capped)

---

#### `get_base_points` returns `int`

Returns base points for a gem type. All standard gems have the same base value (configurable, default 50).

---

### Error Cases

| Condition | Error Code | Error Type | Context Fields |
|-----------|------------|------------|----------------|
| Empty match result (no matches) | `VALIDATION_INVALID_INPUT` | validation | `field="match_result"`, `reason="No matches to score"` |
| Chain step < 1 | `VALIDATION_INVALID_INPUT` | validation | `field="chain_step"`, `value`, `reason="Chain step must be >= 1"` |
| Match length < 3 | `VALIDATION_INVALID_INPUT` | validation | `field="match_length"`, `value`, `reason="Match length must be >= 3"` |
| Invalid gem type for base points | `VALIDATION_INVALID_INPUT` | validation | `field="gem_type"`, `value`, `reason="Not a standard gem type"` |
| Special gem bonus on non-special gem | `VALIDATION_INVALID_INPUT` | validation | `field="gem_type"`, `value`, `reason="Not a special gem type"` |
| MoveProcessingResult with was_valid_match=False | `VALIDATION_INVALID_INPUT` | validation | `field="move_result"`, `reason="Cannot score invalid move"` |

---

### Async Behavior

**This module is fully synchronous.**

- All methods are regular `def`, not `async def`
- No I/O operations (no database, no network, no file system)
- No async imports or dependencies
- Thread-safe for read operations (immutable inputs, pure functions)

Rationale: The scoring module performs pure arithmetic calculations on small data structures. Operations complete in microseconds. Async would add complexity without benefit.

---

## Mandatory Service Usage

### Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `scoring.base_points` | int | 50 | Base points per gem matched |
| `scoring.chain_multipliers` | list[float] | `[1.0, 1.5, 2.0, 2.5, 3.0]` | Multipliers for chain steps 1-5 |
| `scoring.length_multipliers` | list[float] | `[1.0, 2.0, 3.0, 4.0, 5.0]` | Multipliers for lengths 3-7 |
| `scoring.special_gem_creation_bonus` | int | 100 | Bonus points for creating a special gem |
| `scoring.line_blast_activation_bonus` | int | 50 | Base bonus for LINE_BLAST activation |
| `scoring.line_blast_per_gem` | int | 25 | Per-gem bonus for LINE_BLAST |
| `scoring.radial_bomb_activation_bonus` | int | 100 | Base bonus for RADIAL_BOMB activation |
| `scoring.radial_bomb_per_gem` | int | 30 | Per-gem bonus for RADIAL_BOMB |
| `scoring.chromatic_orb_activation_bonus` | int | 200 | Base bonus for CHROMATIC_ORB activation |
| `scoring.chromatic_orb_per_gem` | int | 40 | Per-gem bonus for CHROMATIC_ORB |

Configuration is read once at service initialization and cached. Changes require service restart.

---

### Logging Events

| Event | Severity | Trigger | Context |
|-------|----------|---------|---------|
| `scoring.match_scored` | DEBUG | Match score calculated | `chain_step`, `total_points`, `match_count`, `creates_special` |
| `scoring.move_scored` | DEBUG | Full move score calculated | `total_points`, `chain_count`, `gems_cleared` |
| `scoring.special_gem_bonus` | DEBUG | Special gem bonus calculated | `gem_type`, `gems_affected`, `bonus_points` |
| `scoring.chain_multiplier_applied` | TRACE | Chain multiplier used | `chain_step`, `multiplier` |
| `scoring.length_multiplier_applied` | TRACE | Length multiplier used | `match_length`, `multiplier` |
| `scoring.validation_failed` | WARN | Invalid input rejected | `reason`, `field`, `value` |

---

### Error Types Used

From the error taxonomy (Interface Agent guidance):

- `VALIDATION_INVALID_INPUT` — Invalid input parameters (empty matches, negative chain step, etc.)

All errors created through injected `ErrorServiceProtocol`, never bare raises.

---

## Data Access

### Owned Data

**None.**

The scoring module does not own any persistent data. All score calculations are performed on in-memory data structures passed as parameters. Final scores are persisted by the `match` module in the `matches` table.

### Repository Interfaces Required

**None.**

No repository injection needed. This module operates purely on in-memory data structures.

### Data Read from Other Modules

**None (directly).**

The scoring module receives `MatchResult` and `MoveProcessingResult` as parameters from callers (typically the `match` module). It does not import or directly access the `board` module — it only uses the shared types from `src/core/types/board.py`.

### Transaction Requirements

**None.**

No database operations, no transactions.

---

## Presentation Boundary

### Business Logic API Surface

The scoring module exposes pure functions operating on domain types:
- Input: `MatchResult`, `MoveProcessingResult`, `GemType`, chain steps, match lengths
- Output: `MatchScore`, `MoveScore`, `SpecialGemBonus`, multipliers

All types are defined in this module (`src/modules/scoring/types.py`) or imported from `src/core/types/`.

### Adapter Needs

Presentation adapters need to:
1. Convert `MoveScore` to display-friendly format showing breakdown
2. Animate score popup showing chain multipliers and length bonuses
3. Display running score total during cascade animation
4. Show special gem bonus callouts

Example adapter output for API:
```python
{
    "total_points": 1350,
    "chain_count": 3,
    "cascade_breakdown": [
        {
            "step": 1,
            "points": 300,
            "chain_multiplier": 1.0,
            "matches": [
                {
                    "gem_type": "RED",
                    "length": 3,
                    "base_points": 150,
                    "length_bonus": "1.0x"
                }
            ]
        },
        {
            "step": 2,
            "points": 450,
            "chain_multiplier": 1.5,
            "matches": [
                {
                    "gem_type": "BLUE",
                    "length": 4,
                    "base_points": 200,
                    "length_bonus": "2.0x"
                }
            ]
        },
        {
            "step": 3,
            "points": 600,
            "chain_multiplier": 2.0,
            "matches": [...],
            "special_gem_created": "RADIAL_BOMB"
        }
    ],
    "summary": "Triple chain! +1350 points"
}
```

### What Does NOT Belong in This Module

- No JSON serialization (adapter responsibility)
- No formatting numbers with commas or currency symbols
- No animation timing or frame calculations
- No sound effect triggers
- No HTTP response construction
- No terminal formatting or colors
- No persistence of scores (match module responsibility)

---

## Internal Design

### Core Data Structures

All types are immutable dataclasses for thread safety and clarity.

```python
# src/modules/scoring/types.py

from dataclasses import dataclass
from src.core.types.board import MatchResult, MatchGroup
from src.core.types.game import GemType

@dataclass(frozen=True)
class MatchGroupScore:
    """Score breakdown for a single match group."""
    match_group: MatchGroup
    base_points: int
    length_multiplier: float
    length_bonus_points: int
    subtotal: int

@dataclass(frozen=True)
class MatchScore:
    """Score for a single match detection."""
    total_points: int
    base_points: int
    chain_multiplier: float
    chain_step: int
    match_breakdown: tuple[MatchGroupScore, ...]
    special_gem_creation_bonus: int

@dataclass(frozen=True)
class SpecialGemBonus:
    """Bonus from special gem activation."""
    gem_type: GemType
    base_activation_bonus: int
    gems_affected: int
    per_gem_bonus: int
    total_bonus: int

@dataclass(frozen=True)
class CascadeStepScore:
    """Score for one cascade step."""
    step_number: int
    match_score: MatchScore
    special_gem_bonuses: tuple[SpecialGemBonus, ...]

@dataclass(frozen=True)
class MoveScore:
    """Complete score for a move."""
    total_points: int
    cascade_scores: tuple[CascadeStepScore, ...]
    chain_count: int
    total_gems_cleared: int
    highest_chain_multiplier: float
    special_gems_created: int
    special_gems_activated: int
```

---

### Algorithm: Match Score Calculation

```
calculate_match_score(match_result, chain_step):
    # Validate input
    if not match_result.matches:
        raise validation_error("No matches to score")
    if chain_step < 1:
        raise validation_error("Chain step must be >= 1")

    # Get configuration
    base_points = config.get("scoring.base_points", 50)
    chain_multiplier = get_chain_multiplier(chain_step)

    # Score each match group
    match_breakdown = []
    total_base = 0

    for match_group in match_result.matches:
        # Base points for gems in this match
        group_base = base_points * match_group.length

        # Length multiplier
        length_mult = get_match_length_multiplier(match_group.length)
        length_bonus = int(group_base * (length_mult - 1.0))

        # Subtotal before chain multiplier
        subtotal = int(group_base * length_mult)

        match_breakdown.append(MatchGroupScore(
            match_group=match_group,
            base_points=group_base,
            length_multiplier=length_mult,
            length_bonus_points=length_bonus,
            subtotal=subtotal
        ))

        total_base += subtotal

    # Special gem creation bonus
    special_bonus = 0
    if match_result.creates_special_gem:
        special_bonus = config.get("scoring.special_gem_creation_bonus", 100)

    # Apply chain multiplier to base total, add special bonus
    total = int(total_base * chain_multiplier) + special_bonus

    return MatchScore(
        total_points=total,
        base_points=total_base,
        chain_multiplier=chain_multiplier,
        chain_step=chain_step,
        match_breakdown=tuple(match_breakdown),
        special_gem_creation_bonus=special_bonus
    )
```

---

### Algorithm: Move Score Calculation

```
calculate_move_score(move_result):
    # Validate input
    if not move_result.was_valid_match:
        raise validation_error("Cannot score invalid move")

    cascade_scores = []
    total_points = 0
    total_gems = 0
    special_created = 0
    special_activated = 0
    highest_mult = 1.0

    for i, cascade_step in enumerate(move_result.cascades, start=1):
        # Score the matches in this cascade
        match_score = calculate_match_score(cascade_step.matches, chain_step=i)

        # Track special gem bonuses (from special_gems module, passed in)
        # Note: special gem activation scoring is coordinated by match module
        special_bonuses = ()  # Populated when special gems activate

        cascade_scores.append(CascadeStepScore(
            step_number=i,
            match_score=match_score,
            special_gem_bonuses=special_bonuses
        ))

        total_points += match_score.total_points
        total_gems += cascade_step.matches.total_gems_matched
        highest_mult = max(highest_mult, match_score.chain_multiplier)

        if cascade_step.matches.creates_special_gem:
            special_created += 1

    return MoveScore(
        total_points=total_points,
        cascade_scores=tuple(cascade_scores),
        chain_count=len(cascade_scores),
        total_gems_cleared=total_gems,
        highest_chain_multiplier=highest_mult,
        special_gems_created=special_created,
        special_gems_activated=special_activated
    )
```

---

### Algorithm: Chain Multiplier Lookup

```
get_chain_multiplier(chain_step):
    if chain_step < 1:
        raise validation_error("Chain step must be >= 1")

    multipliers = config.get("scoring.chain_multipliers", [1.0, 1.5, 2.0, 2.5, 3.0])

    # Index into multipliers array (0-based), capped at last value
    index = min(chain_step - 1, len(multipliers) - 1)
    return multipliers[index]
```

Default multipliers:
| Chain Step | Multiplier |
|------------|------------|
| 1 | 1.0x |
| 2 | 1.5x |
| 3 | 2.0x |
| 4 | 2.5x |
| 5+ | 3.0x |

---

### Algorithm: Match Length Multiplier Lookup

```
get_match_length_multiplier(match_length):
    if match_length < 3:
        raise validation_error("Match length must be >= 3")

    multipliers = config.get("scoring.length_multipliers", [1.0, 2.0, 3.0, 4.0, 5.0])

    # Index: length 3 = index 0, length 4 = index 1, etc.
    index = min(match_length - 3, len(multipliers) - 1)
    return multipliers[index]
```

Default multipliers:
| Match Length | Multiplier |
|--------------|------------|
| 3 | 1.0x |
| 4 | 2.0x |
| 5 | 3.0x |
| 6 | 4.0x |
| 7+ | 5.0x |

---

### Algorithm: Special Gem Bonus Calculation

```
calculate_special_gem_bonus(gem_type, gems_affected):
    if gem_type not in SPECIAL_GEM_TYPES:
        raise validation_error("Not a special gem type")
    if gems_affected < 0:
        raise validation_error("Gems affected must be >= 0")

    # Get config for this gem type
    if gem_type in (GemType.LINE_BLAST_H, GemType.LINE_BLAST_V):
        base_bonus = config.get("scoring.line_blast_activation_bonus", 50)
        per_gem = config.get("scoring.line_blast_per_gem", 25)
    elif gem_type == GemType.RADIAL_BOMB:
        base_bonus = config.get("scoring.radial_bomb_activation_bonus", 100)
        per_gem = config.get("scoring.radial_bomb_per_gem", 30)
    elif gem_type == GemType.CHROMATIC_ORB:
        base_bonus = config.get("scoring.chromatic_orb_activation_bonus", 200)
        per_gem = config.get("scoring.chromatic_orb_per_gem", 40)
    else:
        base_bonus = 0
        per_gem = 0

    total = base_bonus + (gems_affected * per_gem)

    return SpecialGemBonus(
        gem_type=gem_type,
        base_activation_bonus=base_bonus,
        gems_affected=gems_affected,
        per_gem_bonus=per_gem,
        total_bonus=total
    )
```

---

### Immutability Contract

All public methods:
1. Never modify input data structures
2. Always return new immutable dataclass instances
3. Use `frozen=True` on all dataclasses

This enables safe concurrent access and simplifies debugging/testing.

---

### Configuration Caching

Configuration values are read once at service initialization:

```python
def __init__(self, config, logger, errors):
    self._config = config
    self._logger = logger
    self._errors = errors

    # Cache config values for performance
    self._base_points = config.get("scoring.base_points", 50)
    self._chain_multipliers = tuple(config.get("scoring.chain_multipliers", [1.0, 1.5, 2.0, 2.5, 3.0]))
    self._length_multipliers = tuple(config.get("scoring.length_multipliers", [1.0, 2.0, 3.0, 4.0, 5.0]))
    # ... other cached values
```

---

## CLI Surface

### Commands

```
chromacrush scoring calculate-match --board "[[...]]" [--chain-step N]
```
Detect matches on the board and calculate score.

**Example:**
```bash
$ chromacrush scoring calculate-match --board "[[1,1,1,2,3,4,5,6],...]" --chain-step 2
Match Score:
  Chain Step: 2
  Chain Multiplier: 1.5x
  Matches Found: 1
    Match 1: RED, length=3, base=150, length_mult=1.0x, subtotal=150
  Base Total: 150
  After Chain: 225
  Special Bonus: 0
  Total: 225 points
```

---

```
chromacrush scoring calculate-move --move-result-json "..."
```
Calculate score from a complete move processing result.

**Example:**
```bash
$ chromacrush scoring calculate-move --move-result-json "$(chromacrush board process-move ...)"
Move Score:
  Total Points: 1350
  Chain Count: 3
  Cascade 1: 300 pts (1.0x chain)
  Cascade 2: 450 pts (1.5x chain)
  Cascade 3: 600 pts (2.0x chain)
  Highest Chain: 2.0x
  Special Gems Created: 1
```

---

```
chromacrush scoring show-multipliers
```
Display current scoring configuration.

**Example:**
```bash
$ chromacrush scoring show-multipliers
Scoring Configuration:
  Base Points: 50 per gem

  Chain Multipliers:
    Chain 1: 1.0x
    Chain 2: 1.5x
    Chain 3: 2.0x
    Chain 4: 2.5x
    Chain 5+: 3.0x

  Length Multipliers:
    3-match: 1.0x
    4-match: 2.0x
    5-match: 3.0x
    6-match: 4.0x
    7+-match: 5.0x

  Special Gem Bonuses:
    Creation: +100
    LINE_BLAST: 50 base + 25/gem
    RADIAL_BOMB: 100 base + 30/gem
    CHROMATIC_ORB: 200 base + 40/gem
```

---

```
chromacrush scoring special-gem-bonus --gem-type LINE_BLAST_H --gems-affected 8
```
Calculate special gem activation bonus.

**Example:**
```bash
$ chromacrush scoring special-gem-bonus --gem-type LINE_BLAST_H --gems-affected 8
Special Gem Bonus:
  Type: LINE_BLAST_H
  Base Activation: 50
  Gems Affected: 8
  Per-Gem Bonus: 25
  Total: 250 points
```

---

### CLI Composition

Commands in `src/cli/commands/scoring_commands.py` use the same `ScoringService` instance as the main application, injected through the CLI composition root.

---

## Edge Cases & Decisions

### EC-1: Overlapping Matches in Match Groups

**Scenario:** Multiple match groups share positions (T-shape, L-shape). Should overlapping gems be scored multiple times?

**Decision:** Each gem position is scored only once. The `MatchResult.total_gems_matched` from the board module already de-duplicates positions. Each `MatchGroup` in the breakdown shows its contribution, but the totals do not double-count.

**Rationale:** Follows standard match-3 conventions. The board module handles de-duplication; scoring trusts its output.

---

### EC-2: Zero Matches Passed to Score Calculation

**Scenario:** `calculate_match_score` called with empty `match_result.matches`.

**Decision:** Raise `VALIDATION_INVALID_INPUT`. Do not return zero silently.

**Rationale:** Calling score calculation with no matches indicates a bug in the calling code. Fail fast.

---

### EC-3: Chain Multiplier Cap

**Scenario:** Very long cascades (chain step > 5).

**Decision:** Chain multiplier caps at 3.0x (the last value in the array). Configured via `scoring.chain_multipliers`.

**Rationale:** Prevents runaway scores from lucky cascades. Maintains game balance. Cap is configurable for tuning.

---

### EC-4: Match Length Cap

**Scenario:** Very long matches (7+ gems in a row).

**Decision:** Length multiplier caps at 5.0x. Configured via `scoring.length_multipliers`.

**Rationale:** 7+ matches are extremely rare and already rewarded with special gems. Capping prevents score explosion.

---

### EC-5: Special Gem Activation Without Match

**Scenario:** Special gem activated by another special gem (fusion cascade), not by a normal match.

**Decision:** The `special_gems` module coordinates this and calls `calculate_special_gem_bonus` directly. Chain multipliers still apply based on cascade step.

**Rationale:** Special gem interactions are complex. The scoring module provides primitive calculations; orchestration lives in `special_gems` and `match`.

---

### EC-6: Configuration Values Out of Range

**Scenario:** Config provides negative base points or invalid multipliers.

**Decision:** Service initialization validates config values. Negative or zero values are rejected with descriptive errors logged at WARN level, and defaults are used.

**Rationale:** Defensive programming. Bad config should not crash the game.

---

### EC-7: All Gems Same Color (theoretical 8-match)

**Scenario:** Entire row is same color (8-match on 8-wide board).

**Decision:** Treated as 7+ match (5.0x multiplier). Board module handles the special gem creation (RADIAL_BOMB for 5+ straight match).

**Rationale:** Board's match detection already handles oversized matches. Scoring applies capped multiplier.

---

### EC-8: Score Integer Overflow

**Scenario:** Theoretical score calculation exceeds int limits.

**Decision:** Python integers have unlimited precision. No overflow possible. For display/storage, scores are clamped to reasonable maximum (e.g., 2^31-1 for database storage).

**Rationale:** Practically impossible with normal gameplay. Defensive clamping for database compatibility.

---

## Open Questions

None. All design decisions resolved within existing guidance.

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent (scoring) |
