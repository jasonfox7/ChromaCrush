# Module Artifact: special_gems

## Header
- **Author:** Scout Agent (special_gems)
- **Date:** 2026-02-05
- **Version:** 1.0
- **Status:** Final
- **Dependencies:** `board` (Wave 1), `scoring` (Wave 2)
- **Dependents:** `board_gen`, `match`

---

## Purpose

The **special_gems** module handles the creation, activation, and fusion of special gem types in ChromaCrush. Special gems are powerful game elements created when players make matches of 4+ gems or special patterns (T-shape, L-shape). When activated, they clear gems in unique patterns, creating chain reactions and scoring opportunities.

Special gem types:
- **Line Blast (Horizontal/Vertical)** - Created by 4-match; clears entire row or column
- **Radial Bomb** - Created by 5-match straight; clears 3x3 area
- **Chromatic Orb** - Created by T-shape or L-shape; clears all gems of a target color

The module also handles **fusions** - when two special gems are swapped together, they combine for enhanced effects (e.g., two Radial Bombs create a 5x5 explosion).

This module is **synchronous** and **pure** - it operates on in-memory board state passed as parameters and returns effect results without side effects. No database I/O, no network calls, no async behavior. All calculations are deterministic for reproducibility in async versus matches.

---

## Public Interface

### Class: `SpecialGemsService`

The special_gems module exposes a single service class that receives dependencies via `__init__` injection.

```python
class SpecialGemsService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        scoring_service: ScoringServiceProtocol,
    ) -> None:
        ...
```

**Note:** The `scoring_service` is injected to calculate bonus points for special gem activations.

---

### Inputs

#### `calculate_effect(board: BoardState, position: Position, target_color: GemType | None = None) -> SpecialGemEffect`

Calculates the effect of activating a special gem at the given position.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Current board state | Must be valid BoardState |
| `position` | `Position` | Position of the special gem to activate | Must be in-bounds; must contain a special gem |
| `target_color` | `GemType \| None` | Target color for Chromatic Orb (required if gem is CHROMATIC_ORB) | If provided, must be a standard gem (1-6) |

---

#### `calculate_fusion_effect(board: BoardState, pos_a: Position, pos_b: Position, target_color: GemType | None = None) -> FusionEffect`

Calculates the effect of fusing two special gems by swapping them.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Current board state | Must be valid BoardState |
| `pos_a` | `Position` | Position of first special gem | Must be in-bounds; must contain a special gem |
| `pos_b` | `Position` | Position of second special gem | Must be in-bounds; must contain a special gem; must be adjacent to pos_a |
| `target_color` | `GemType \| None` | Target color for fusions involving Chromatic Orb | Required if either gem is CHROMATIC_ORB |

---

#### `apply_effect(board: BoardState, effect: SpecialGemEffect | FusionEffect) -> tuple[BoardState, list[Position]]`

Applies a calculated effect to the board, clearing affected positions.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Current board state | Must be valid BoardState |
| `effect` | `SpecialGemEffect \| FusionEffect` | The effect to apply | Must be a valid effect object |

---

#### `is_special_gem(gem_type: GemType) -> bool`

Checks if a gem type is a special gem.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `gem_type` | `GemType` | The gem type to check | Any GemType value |

---

#### `get_special_gem_for_match(match_result: MatchResult) -> tuple[GemType, Position] | None`

Determines which special gem (if any) should be created from a match result.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `match_result` | `MatchResult` | Match detection result from board module | Must have at least one match |

---

#### `find_triggered_special_gems(board: BoardState, cleared_positions: set[Position]) -> list[Position]`

Finds special gems that should be triggered by cleared positions (chain reactions).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `board` | `BoardState` | Current board state | Must be valid BoardState |
| `cleared_positions` | `set[Position]` | Positions being cleared | Must be non-empty |

---

### Outputs

#### `calculate_effect` returns `SpecialGemEffect`

```python
@dataclass(frozen=True)
class SpecialGemEffect:
    """Result of calculating a special gem activation."""
    gem_type: GemType
    source_position: Position
    affected_positions: frozenset[Position]  # Positions that will be cleared
    bonus_score: SpecialGemBonus  # From scoring module
    triggers_special_gems: list[Position]  # Other special gems in affected area
    description: str  # Human-readable description (e.g., "Line Blast clears row 3")
```

---

#### `calculate_fusion_effect` returns `FusionEffect`

```python
@dataclass(frozen=True)
class FusionEffect:
    """Result of calculating a special gem fusion."""
    gem_a_type: GemType
    gem_b_type: GemType
    fusion_type: FusionType  # Enum describing the fusion category
    source_positions: tuple[Position, Position]
    affected_positions: frozenset[Position]
    bonus_score: SpecialGemBonus
    triggers_special_gems: list[Position]
    secondary_effects: list[SpecialGemEffect]  # For fusions that create new specials
    description: str

class FusionType(Enum):
    CROSS_BLAST = "cross_blast"           # Line + Line
    TRIPLE_LINE = "triple_line"           # Line + Radial
    COLOR_LINE_BLAST = "color_line_blast" # Line + Chromatic
    MEGA_BOMB = "mega_bomb"               # Radial + Radial
    COLOR_BOMB = "color_bomb"             # Radial + Chromatic
    BOARD_CLEAR = "board_clear"           # Chromatic + Chromatic
```

---

#### `apply_effect` returns `tuple[BoardState, list[Position]]`

Returns:
- New `BoardState` with affected positions set to `GemType.EMPTY (0)`
- List of positions that were cleared (for animation/scoring purposes)

---

#### `is_special_gem` returns `bool`

- `True` if gem_type is LINE_BLAST_H, LINE_BLAST_V, RADIAL_BOMB, or CHROMATIC_ORB
- `False` otherwise

---

#### `get_special_gem_for_match` returns `tuple[GemType, Position] | None`

Returns the special gem type and placement position based on match rules:
- **4-match horizontal**: `(LINE_BLAST_H, center_position)`
- **4-match vertical**: `(LINE_BLAST_V, center_position)`
- **5+ match straight**: `(RADIAL_BOMB, center_position)`
- **T-shape or L-shape**: `(CHROMATIC_ORB, intersection_position)`
- **3-match (no special)**: `None`

---

#### `find_triggered_special_gems` returns `list[Position]`

Returns positions of special gems that are within the cleared area and should be activated as part of a chain reaction.

---

### Error Cases

| Condition | Error Code | Error Type | Context Fields |
|-----------|------------|------------|----------------|
| Position out of bounds | `VALIDATION_OUT_OF_BOUNDS` | validation | `position`, `board_width`, `board_height` |
| Position does not contain special gem | `VALIDATION_INVALID_GEM_SWAP` | validation | `position`, `gem_type`, `reason="Not a special gem"` |
| Fusion positions not adjacent | `VALIDATION_POSITIONS_NOT_ADJACENT` | validation | `pos_a`, `pos_b` |
| Chromatic Orb without target color | `VALIDATION_INVALID_INPUT` | validation | `field="target_color"`, `reason="Chromatic Orb requires target color"` |
| Target color is not a standard gem | `VALIDATION_INVALID_INPUT` | validation | `field="target_color"`, `value`, `reason="Must be a standard gem color (1-6)"` |
| Empty match result for special gem detection | `VALIDATION_INVALID_INPUT` | validation | `field="match_result"`, `reason="No matches to analyze"` |

---

### Async Behavior

**This module is fully synchronous.**

- All methods are regular `def`, not `async def`
- No I/O operations (no database, no network, no file system)
- No async imports or dependencies
- Thread-safe for read operations (immutable inputs)

Rationale: The special_gems module performs pure computation on in-memory data structures. Calculating affected positions on an 8x8 grid is sub-millisecond. Async would add complexity without benefit.

---

## Mandatory Service Usage

### Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `game.board_width` | int | 8 | Board width (for effect calculations) |
| `game.board_height` | int | 8 | Board height (for effect calculations) |
| `special_gems.radial_bomb_radius` | int | 1 | Radius of Radial Bomb (1 = 3x3, 2 = 5x5) |
| `special_gems.mega_bomb_radius` | int | 2 | Radius of Radial+Radial fusion (2 = 5x5) |
| `special_gems.triple_line_count` | int | 3 | Number of rows/cols for Line+Radial fusion |
| `special_gems.chain_reaction_enabled` | bool | True | Whether special gems trigger chain reactions |

Configuration is read once at service initialization and cached.

---

### Logging Events

| Event | Severity | Trigger | Context |
|-------|----------|---------|---------|
| `special_gems.effect_calculated` | DEBUG | Effect calculation complete | `gem_type`, `position`, `affected_count` |
| `special_gems.fusion_calculated` | DEBUG | Fusion effect calculated | `gem_a`, `gem_b`, `fusion_type`, `affected_count` |
| `special_gems.effect_applied` | DEBUG | Effect applied to board | `cleared_count`, `triggered_specials` |
| `special_gems.chain_triggered` | DEBUG | Chain reaction detected | `triggering_position`, `triggered_positions` |
| `special_gems.match_creates_special` | DEBUG | Match creates special gem | `match_pattern`, `special_type`, `position` |
| `special_gems.validation_failed` | WARN | Invalid input rejected | `reason`, `position` |

---

### Error Types Used

From the error taxonomy (Interface Agent guidance):

- `VALIDATION_OUT_OF_BOUNDS` - Position coordinates outside grid
- `VALIDATION_POSITIONS_NOT_ADJACENT` - Fusion positions not orthogonally adjacent
- `VALIDATION_INVALID_GEM_SWAP` - Position doesn't contain a special gem
- `VALIDATION_INVALID_INPUT` - General validation failure (missing target color, invalid gem type)

All errors created through injected `ErrorServiceProtocol`, never bare raises.

---

## Data Access

### Owned Data

**None.**

The special_gems module does not own any persistent data. All board state is passed in as parameters and returned as values. Special gem state is part of the board grid (negative GemType values).

### Repository Interfaces Required

**None.**

No repository injection needed. This module operates purely on in-memory data structures.

### Data Read from Other Modules

**None (directly).**

The special_gems module receives `BoardState` and `MatchResult` as parameters from callers. It uses the `scoring_service` (injected) to calculate bonus points.

### Transaction Requirements

**None.**

No database operations, no transactions.

---

## Presentation Boundary

### Business Logic API Surface

The special_gems module exposes pure functions operating on domain types:
- Input: `BoardState`, `Position`, `MatchResult`, `GemType`
- Output: `SpecialGemEffect`, `FusionEffect`, `BoardState`

All types are defined in this module (`src/modules/special_gems/types.py`) or imported from `src/core/types/`.

### Adapter Needs

Presentation adapters need to:
1. Convert `SpecialGemEffect.affected_positions` to animation coordinates
2. Map `FusionType` enum to visual effect identifiers
3. Sequence animations (gem glow, clear effect, chain reaction)
4. Display bonus score popup at effect origin

Example adapter output for API:
```python
{
    "effect_type": "fusion",
    "fusion_type": "mega_bomb",
    "source_positions": [[3, 4], [3, 5]],
    "affected_positions": [[2, 3], [2, 4], [2, 5], [2, 6], ...],  # 5x5 area
    "bonus_score": 450,
    "triggered_chain": [
        {"position": [2, 3], "gem_type": "LINE_BLAST_H"}
    ],
    "description": "Mega Bomb! 5x5 explosion!"
}
```

### What Does NOT Belong in This Module

- No JSON serialization (adapter responsibility)
- No animation timing or frame calculations
- No particle effect configurations
- No sound effect triggers
- No HTTP response construction
- No terminal formatting or colors
- No persistence of effects

---

## Internal Design

### Core Data Structures

All types are immutable dataclasses for thread safety and clarity.

```python
# src/modules/special_gems/types.py

from dataclasses import dataclass
from enum import Enum
from src.core.types.board import BoardState, Position
from src.core.types.game import GemType
from src.modules.scoring.types import SpecialGemBonus


SPECIAL_GEM_TYPES = frozenset({
    GemType.LINE_BLAST_H,
    GemType.LINE_BLAST_V,
    GemType.RADIAL_BOMB,
    GemType.CHROMATIC_ORB,
})


class FusionType(Enum):
    """Categories of special gem fusions."""
    CROSS_BLAST = "cross_blast"           # Line + Line (any orientation)
    TRIPLE_LINE = "triple_line"           # Line + Radial
    COLOR_LINE_BLAST = "color_line_blast" # Line + Chromatic
    MEGA_BOMB = "mega_bomb"               # Radial + Radial
    COLOR_BOMB = "color_bomb"             # Radial + Chromatic
    BOARD_CLEAR = "board_clear"           # Chromatic + Chromatic


@dataclass(frozen=True)
class SpecialGemEffect:
    """Result of calculating a special gem activation."""
    gem_type: GemType
    source_position: Position
    affected_positions: frozenset[Position]
    bonus_score: SpecialGemBonus
    triggers_special_gems: list[Position]
    description: str


@dataclass(frozen=True)
class FusionEffect:
    """Result of calculating a special gem fusion."""
    gem_a_type: GemType
    gem_b_type: GemType
    fusion_type: FusionType
    source_positions: tuple[Position, Position]
    affected_positions: frozenset[Position]
    bonus_score: SpecialGemBonus
    triggers_special_gems: list[Position]
    secondary_effects: list[SpecialGemEffect]
    description: str
```

---

### Special Gem Creation Rules

From the board module's match detection:

| Match Pattern | Special Gem Created | Placement Position |
|---------------|--------------------|--------------------|
| 4 horizontal | LINE_BLAST_H | Center of match (index 1 or 2) |
| 4 vertical | LINE_BLAST_V | Center of match |
| 5+ straight | RADIAL_BOMB | Center of match |
| T-shape (3H + 3V) | CHROMATIC_ORB | Intersection point |
| L-shape (3H + 3V) | CHROMATIC_ORB | Intersection point |

```python
def get_special_gem_for_match(match_result: MatchResult) -> tuple[GemType, Position] | None:
    """Determine special gem creation from match result."""

    if not match_result.matches:
        raise validation_error("No matches to analyze")

    # Check for overlapping matches (T/L shape)
    all_positions = set()
    overlaps = set()
    for match in match_result.matches:
        for pos in match.positions:
            if pos in all_positions:
                overlaps.add(pos)
            all_positions.add(pos)

    # T-shape or L-shape: overlapping matches
    if overlaps and len(match_result.matches) >= 2:
        # Chromatic Orb at intersection
        intersection = next(iter(overlaps))
        return (GemType.CHROMATIC_ORB, intersection)

    # Single match analysis
    for match in match_result.matches:
        length = match.length

        if length >= 5:
            # Radial Bomb at center
            center_pos = _find_center(match.positions)
            return (GemType.RADIAL_BOMB, center_pos)

        if length == 4:
            # Line Blast (direction matches orientation)
            center_pos = _find_center(match.positions)
            if match.is_horizontal:
                return (GemType.LINE_BLAST_H, center_pos)
            else:
                return (GemType.LINE_BLAST_V, center_pos)

    # 3-match: no special gem
    return None
```

---

### Algorithm: Line Blast Effect

```python
def _calculate_line_blast_effect(
    self,
    board: BoardState,
    position: Position,
    is_horizontal: bool,
) -> SpecialGemEffect:
    """Calculate positions affected by Line Blast."""

    affected = set()
    width, height = board.width, board.height

    if is_horizontal:
        # Clear entire row
        for col in range(width):
            affected.add(Position(position.row, col))
        description = f"Line Blast clears row {position.row}"
    else:
        # Clear entire column
        for row in range(height):
            affected.add(Position(row, position.col))
        description = f"Line Blast clears column {position.col}"

    # Find triggered special gems
    triggered = self._find_triggered_specials(board, affected, exclude={position})

    # Calculate bonus score
    bonus = self._scoring.calculate_special_gem_bonus(
        GemType.LINE_BLAST_H if is_horizontal else GemType.LINE_BLAST_V,
        len(affected)
    )

    return SpecialGemEffect(
        gem_type=GemType.LINE_BLAST_H if is_horizontal else GemType.LINE_BLAST_V,
        source_position=position,
        affected_positions=frozenset(affected),
        bonus_score=bonus,
        triggers_special_gems=triggered,
        description=description,
    )
```

---

### Algorithm: Radial Bomb Effect

```python
def _calculate_radial_bomb_effect(
    self,
    board: BoardState,
    position: Position,
    radius: int = 1,
) -> SpecialGemEffect:
    """Calculate positions affected by Radial Bomb (3x3 for radius=1)."""

    affected = set()
    width, height = board.width, board.height

    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            row = position.row + dr
            col = position.col + dc
            if 0 <= row < height and 0 <= col < width:
                affected.add(Position(row, col))

    size = (2 * radius + 1)
    description = f"Radial Bomb explodes {size}x{size} at ({position.row}, {position.col})"

    # Find triggered special gems
    triggered = self._find_triggered_specials(board, affected, exclude={position})

    # Calculate bonus score
    bonus = self._scoring.calculate_special_gem_bonus(
        GemType.RADIAL_BOMB,
        len(affected)
    )

    return SpecialGemEffect(
        gem_type=GemType.RADIAL_BOMB,
        source_position=position,
        affected_positions=frozenset(affected),
        bonus_score=bonus,
        triggers_special_gems=triggered,
        description=description,
    )
```

---

### Algorithm: Chromatic Orb Effect

```python
def _calculate_chromatic_orb_effect(
    self,
    board: BoardState,
    position: Position,
    target_color: GemType,
) -> SpecialGemEffect:
    """Calculate positions affected by Chromatic Orb (all gems of one color)."""

    if target_color not in range(1, 7):
        raise validation_error("Target color must be a standard gem (1-6)")

    affected = set()
    width, height = board.width, board.height

    # Find all gems of target color
    for row in range(height):
        for col in range(width):
            if board.get(Position(row, col)) == target_color:
                affected.add(Position(row, col))

    # Also include the orb itself
    affected.add(position)

    color_name = GemType(target_color).name
    description = f"Chromatic Orb clears all {color_name} gems ({len(affected)} total)"

    # Find triggered special gems
    triggered = self._find_triggered_specials(board, affected, exclude={position})

    # Calculate bonus score
    bonus = self._scoring.calculate_special_gem_bonus(
        GemType.CHROMATIC_ORB,
        len(affected)
    )

    return SpecialGemEffect(
        gem_type=GemType.CHROMATIC_ORB,
        source_position=position,
        affected_positions=frozenset(affected),
        bonus_score=bonus,
        triggers_special_gems=triggered,
        description=description,
    )
```

---

### Fusion Matrix

| Gem A | Gem B | Fusion Type | Effect |
|-------|-------|-------------|--------|
| LINE_BLAST_H/V | LINE_BLAST_H/V | CROSS_BLAST | Clears both row AND column of activation point |
| LINE_BLAST_H/V | RADIAL_BOMB | TRIPLE_LINE | Clears 3 adjacent rows or columns |
| LINE_BLAST_H/V | CHROMATIC_ORB | COLOR_LINE_BLAST | All gems of target color become Line Blasts and activate |
| RADIAL_BOMB | RADIAL_BOMB | MEGA_BOMB | 5x5 explosion (radius=2) |
| RADIAL_BOMB | CHROMATIC_ORB | COLOR_BOMB | All gems of target color become Radial Bombs and activate |
| CHROMATIC_ORB | CHROMATIC_ORB | BOARD_CLEAR | Clears entire board |

---

### Algorithm: Fusion Effect Calculation

```python
def calculate_fusion_effect(
    self,
    board: BoardState,
    pos_a: Position,
    pos_b: Position,
    target_color: GemType | None = None,
) -> FusionEffect:
    """Calculate the effect of fusing two special gems."""

    gem_a = board.get(pos_a)
    gem_b = board.get(pos_b)

    # Validate both are special gems
    if not self.is_special_gem(gem_a):
        raise validation_error("Not a special gem", position=pos_a)
    if not self.is_special_gem(gem_b):
        raise validation_error("Not a special gem", position=pos_b)

    # Validate adjacency
    if not pos_a.is_adjacent_to(pos_b):
        raise validation_error("Positions must be adjacent", pos_a=pos_a, pos_b=pos_b)

    # Determine fusion type and calculate effect
    fusion_type, affected, secondary, description = self._calculate_fusion(
        board, gem_a, gem_b, pos_a, pos_b, target_color
    )

    # Find triggered special gems (excluding the fusion sources)
    triggered = self._find_triggered_specials(
        board, affected, exclude={pos_a, pos_b}
    )

    # Calculate combined bonus
    total_affected = len(affected)
    for effect in secondary:
        total_affected += len(effect.affected_positions)

    bonus = self._scoring.calculate_special_gem_bonus(
        gem_a,  # Use first gem type for bonus category
        total_affected
    )

    return FusionEffect(
        gem_a_type=gem_a,
        gem_b_type=gem_b,
        fusion_type=fusion_type,
        source_positions=(pos_a, pos_b),
        affected_positions=frozenset(affected),
        bonus_score=bonus,
        triggers_special_gems=triggered,
        secondary_effects=secondary,
        description=description,
    )


def _calculate_fusion(
    self,
    board: BoardState,
    gem_a: GemType,
    gem_b: GemType,
    pos_a: Position,
    pos_b: Position,
    target_color: GemType | None,
) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
    """Internal fusion calculation dispatch."""

    # Normalize order: sort by gem type value
    if gem_a.value > gem_b.value:
        gem_a, gem_b = gem_b, gem_a
        pos_a, pos_b = pos_b, pos_a

    # Chromatic + Chromatic = Board Clear
    if gem_a == GemType.CHROMATIC_ORB and gem_b == GemType.CHROMATIC_ORB:
        return self._fusion_board_clear(board, pos_a, pos_b)

    # Radial + Chromatic = Color Bomb
    if gem_a == GemType.RADIAL_BOMB and gem_b == GemType.CHROMATIC_ORB:
        return self._fusion_color_bomb(board, pos_a, pos_b, target_color)

    # Line + Chromatic = Color Line Blast
    if gem_a in (GemType.LINE_BLAST_H, GemType.LINE_BLAST_V) and gem_b == GemType.CHROMATIC_ORB:
        return self._fusion_color_line_blast(board, pos_a, pos_b, target_color, gem_a)

    # Radial + Radial = Mega Bomb
    if gem_a == GemType.RADIAL_BOMB and gem_b == GemType.RADIAL_BOMB:
        return self._fusion_mega_bomb(board, pos_a, pos_b)

    # Line + Radial = Triple Line
    if gem_a in (GemType.LINE_BLAST_H, GemType.LINE_BLAST_V) and gem_b == GemType.RADIAL_BOMB:
        return self._fusion_triple_line(board, pos_a, pos_b, gem_a)

    # Line + Line = Cross Blast
    if gem_a in (GemType.LINE_BLAST_H, GemType.LINE_BLAST_V) and gem_b in (GemType.LINE_BLAST_H, GemType.LINE_BLAST_V):
        return self._fusion_cross_blast(board, pos_a, pos_b)

    # Should not reach here if validation is correct
    raise validation_error("Unknown fusion combination")
```

---

### Algorithm: Cross Blast Fusion (Line + Line)

```python
def _fusion_cross_blast(
    self,
    board: BoardState,
    pos_a: Position,
    pos_b: Position,
) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
    """Line + Line = clears both row AND column at midpoint."""

    affected = set()
    width, height = board.width, board.height

    # Use midpoint between the two gems as activation point
    mid_row = (pos_a.row + pos_b.row) // 2
    mid_col = (pos_a.col + pos_b.col) // 2

    # Clear entire row
    for col in range(width):
        affected.add(Position(mid_row, col))

    # Clear entire column
    for row in range(height):
        affected.add(Position(row, mid_col))

    description = f"Cross Blast clears row {mid_row} and column {mid_col}"

    return (FusionType.CROSS_BLAST, affected, [], description)
```

---

### Algorithm: Mega Bomb Fusion (Radial + Radial)

```python
def _fusion_mega_bomb(
    self,
    board: BoardState,
    pos_a: Position,
    pos_b: Position,
) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
    """Radial + Radial = 5x5 explosion."""

    affected = set()
    width, height = board.width, board.height
    radius = self._config.get("special_gems.mega_bomb_radius", 2)

    # Center at midpoint
    center_row = (pos_a.row + pos_b.row) // 2
    center_col = (pos_a.col + pos_b.col) // 2

    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            row = center_row + dr
            col = center_col + dc
            if 0 <= row < height and 0 <= col < width:
                affected.add(Position(row, col))

    size = 2 * radius + 1
    description = f"Mega Bomb! {size}x{size} explosion!"

    return (FusionType.MEGA_BOMB, affected, [], description)
```

---

### Algorithm: Triple Line Fusion (Line + Radial)

```python
def _fusion_triple_line(
    self,
    board: BoardState,
    pos_a: Position,
    pos_b: Position,
    line_type: GemType,
) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
    """Line + Radial = 3 rows or 3 columns."""

    affected = set()
    width, height = board.width, board.height
    count = self._config.get("special_gems.triple_line_count", 3)

    # Center at midpoint
    center_row = (pos_a.row + pos_b.row) // 2
    center_col = (pos_a.col + pos_b.col) // 2

    half = count // 2

    if line_type == GemType.LINE_BLAST_H:
        # Clear 3 rows
        for r_offset in range(-half, half + 1):
            row = center_row + r_offset
            if 0 <= row < height:
                for col in range(width):
                    affected.add(Position(row, col))
        description = f"Triple Line clears rows {center_row - half} to {center_row + half}"
    else:
        # Clear 3 columns
        for c_offset in range(-half, half + 1):
            col = center_col + c_offset
            if 0 <= col < width:
                for row in range(height):
                    affected.add(Position(row, col))
        description = f"Triple Line clears columns {center_col - half} to {center_col + half}"

    return (FusionType.TRIPLE_LINE, affected, [], description)
```

---

### Algorithm: Color Line Blast Fusion (Line + Chromatic)

```python
def _fusion_color_line_blast(
    self,
    board: BoardState,
    pos_a: Position,
    pos_b: Position,
    target_color: GemType | None,
    line_type: GemType,
) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
    """Line + Chromatic = All gems of color become Line Blasts and activate."""

    if target_color is None:
        raise validation_error("Chromatic fusion requires target color")

    width, height = board.width, board.height
    affected = set()
    secondary_effects = []

    # Find all gems of target color
    color_positions = []
    for row in range(height):
        for col in range(width):
            pos = Position(row, col)
            if board.get(pos) == target_color:
                color_positions.append(pos)

    # Each becomes a Line Blast and activates
    for pos in color_positions:
        # Calculate line blast effect at this position
        if line_type == GemType.LINE_BLAST_H:
            for col in range(width):
                affected.add(Position(pos.row, col))
        else:
            for row in range(height):
                affected.add(Position(row, pos.col))

        # Track as secondary effect for animation
        secondary_effects.append(SpecialGemEffect(
            gem_type=line_type,
            source_position=pos,
            affected_positions=frozenset(),  # Will be included in main affected
            bonus_score=self._scoring.calculate_special_gem_bonus(line_type, width if line_type == GemType.LINE_BLAST_H else height),
            triggers_special_gems=[],
            description=f"Line Blast at ({pos.row}, {pos.col})",
        ))

    color_name = GemType(target_color).name
    description = f"Color Line Blast! All {color_name} gems become Line Blasts ({len(color_positions)} total)"

    return (FusionType.COLOR_LINE_BLAST, affected, secondary_effects, description)
```

---

### Algorithm: Color Bomb Fusion (Radial + Chromatic)

```python
def _fusion_color_bomb(
    self,
    board: BoardState,
    pos_a: Position,
    pos_b: Position,
    target_color: GemType | None,
) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
    """Radial + Chromatic = All gems of color become Radial Bombs and activate."""

    if target_color is None:
        raise validation_error("Chromatic fusion requires target color")

    width, height = board.width, board.height
    radius = self._config.get("special_gems.radial_bomb_radius", 1)
    affected = set()
    secondary_effects = []

    # Find all gems of target color
    color_positions = []
    for row in range(height):
        for col in range(width):
            pos = Position(row, col)
            if board.get(pos) == target_color:
                color_positions.append(pos)

    # Each becomes a Radial Bomb and activates
    for pos in color_positions:
        bomb_affected = set()
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                r = pos.row + dr
                c = pos.col + dc
                if 0 <= r < height and 0 <= c < width:
                    affected.add(Position(r, c))
                    bomb_affected.add(Position(r, c))

        secondary_effects.append(SpecialGemEffect(
            gem_type=GemType.RADIAL_BOMB,
            source_position=pos,
            affected_positions=frozenset(bomb_affected),
            bonus_score=self._scoring.calculate_special_gem_bonus(GemType.RADIAL_BOMB, len(bomb_affected)),
            triggers_special_gems=[],
            description=f"Radial Bomb at ({pos.row}, {pos.col})",
        ))

    color_name = GemType(target_color).name
    description = f"Color Bomb! All {color_name} gems become Radial Bombs ({len(color_positions)} total)"

    return (FusionType.COLOR_BOMB, affected, secondary_effects, description)
```

---

### Algorithm: Board Clear Fusion (Chromatic + Chromatic)

```python
def _fusion_board_clear(
    self,
    board: BoardState,
    pos_a: Position,
    pos_b: Position,
) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
    """Chromatic + Chromatic = Clears entire board."""

    affected = set()
    width, height = board.width, board.height

    for row in range(height):
        for col in range(width):
            affected.add(Position(row, col))

    description = "Double Chromatic! Entire board cleared!"

    return (FusionType.BOARD_CLEAR, affected, [], description)
```

---

### Algorithm: Chain Reaction Detection

```python
def _find_triggered_specials(
    self,
    board: BoardState,
    affected: set[Position],
    exclude: set[Position],
) -> list[Position]:
    """Find special gems in affected area that should chain-trigger."""

    if not self._config.get("special_gems.chain_reaction_enabled", True):
        return []

    triggered = []

    for pos in affected:
        if pos in exclude:
            continue

        gem = board.get(pos)
        if self.is_special_gem(gem):
            triggered.append(pos)

    return triggered
```

---

### Algorithm: Apply Effect

```python
def apply_effect(
    self,
    board: BoardState,
    effect: SpecialGemEffect | FusionEffect,
) -> tuple[BoardState, list[Position]]:
    """Apply a calculated effect to the board."""

    new_grid = board.grid.copy()
    cleared = []

    for pos in effect.affected_positions:
        new_grid[pos.row, pos.col] = GemType.EMPTY.value
        cleared.append(pos)

    # For fusion effects, also apply secondary effects
    if isinstance(effect, FusionEffect):
        for secondary in effect.secondary_effects:
            for pos in secondary.affected_positions:
                if new_grid[pos.row, pos.col] != GemType.EMPTY.value:
                    new_grid[pos.row, pos.col] = GemType.EMPTY.value
                    cleared.append(pos)

    return BoardState(grid=new_grid), cleared
```

---

### Immutability Contract

All public methods:
1. Never modify input `BoardState`
2. Always return new data structures
3. Input arrays are copied before any modification

This enables safe concurrent read access and simplifies debugging/testing.

---

## CLI Surface

### Commands

```
chromacrush special-gems activate --board "[[...]]" --position 3,4 [--target-color RED]
```
Calculate and display the effect of activating a special gem.

**Example:**
```bash
$ chromacrush special-gems activate --board "..." --position 3,4
Special Gem Effect:
  Type: RADIAL_BOMB
  Position: (3, 4)
  Affected: 9 positions (3x3 area)
  Bonus Score: 370 points
  Chain Triggers: 1 (LINE_BLAST_H at (2, 3))
  Description: Radial Bomb explodes 3x3 at (3, 4)
```

---

```
chromacrush special-gems fuse --board "[[...]]" --pos-a 3,4 --pos-b 3,5 [--target-color BLUE]
```
Calculate and display the effect of fusing two special gems.

**Example:**
```bash
$ chromacrush special-gems fuse --board "..." --pos-a 3,4 --pos-b 3,5
Fusion Effect:
  Gem A: RADIAL_BOMB at (3, 4)
  Gem B: RADIAL_BOMB at (3, 5)
  Fusion Type: MEGA_BOMB
  Affected: 25 positions (5x5 area)
  Bonus Score: 850 points
  Chain Triggers: 2
  Description: Mega Bomb! 5x5 explosion!
```

---

```
chromacrush special-gems check --board "[[...]]" --position 3,4
```
Check if a position contains a special gem and show its type.

**Example:**
```bash
$ chromacrush special-gems check --board "..." --position 3,4
Position (3, 4):
  Gem Type: CHROMATIC_ORB
  Is Special: Yes
```

---

```
chromacrush special-gems from-match --match-result-json "..."
```
Determine what special gem (if any) would be created from a match result.

**Example:**
```bash
$ chromacrush special-gems from-match --match-result-json "..."
Match Analysis:
  Pattern: 4-match horizontal
  Creates: LINE_BLAST_H
  Placement: (2, 3)
```

---

```
chromacrush special-gems simulate --board "[[...]]" --position 3,4 [--apply]
```
Simulate a special gem activation and optionally show the resulting board.

**Example:**
```bash
$ chromacrush special-gems simulate --board "..." --position 3,4 --apply
Before:
  ...
After (9 gems cleared):
  ...
Chain Reactions Triggered: 1
  - LINE_BLAST_H at (2, 3) -> clears row 2
```

---

### CLI Composition

Commands in `src/cli/commands/special_gems_commands.py` use the same `SpecialGemsService` instance as the main application, injected through the CLI composition root.

---

## Edge Cases & Decisions

### EC-1: Chromatic Orb Target Color Selection

**Scenario:** Chromatic Orb is activated - how is the target color determined?

**Decision:** Target color is provided as a parameter. In a normal match, the Chromatic Orb swapped with a standard gem uses that gem's color. In fusions, the target color must be explicitly provided. The UI handles showing color selection.

**Rationale:** Keeps the module pure - target selection is a game flow concern handled by the `match` module.

---

### EC-2: Chain Reaction Depth Limit

**Scenario:** Special gem triggers special gem triggers special gem (deep chain).

**Decision:** No explicit depth limit. Chain reactions continue until no more special gems are in affected areas. The `match` module coordinates the cascade loop with a maximum iteration limit (100 from board module).

**Rationale:** Extremely deep chains are rare and exciting. Let them play out.

---

### EC-3: Special Gem Survives Its Own Effect

**Scenario:** Does the activating special gem get cleared with its effect?

**Decision:** Yes. The source position is always included in `affected_positions`. The special gem is consumed upon activation.

**Rationale:** Standard match-3 behavior. Special gems are single-use.

---

### EC-4: Multiple Special Gems in Affected Area

**Scenario:** A Radial Bomb's 3x3 area contains two other special gems.

**Decision:** Both triggered special gems are returned in `triggers_special_gems`. The `match` module processes them in order (by position, top-to-bottom, left-to-right).

**Rationale:** Deterministic ordering ensures reproducibility for async matches.

---

### EC-5: Fusion With No Adjacent Standard Gem (Chromatic Target)

**Scenario:** Chromatic Orb is involved in fusion but there's no obvious target color.

**Decision:** The `target_color` parameter is required. If not provided, validation error is raised. The `match` module is responsible for determining target color (e.g., most common color on board, or player choice).

**Rationale:** Keeps special_gems pure. Game flow decisions are external.

---

### EC-6: Empty Board After Effect

**Scenario:** Board Clear fusion clears entire board.

**Decision:** Return a board full of `GemType.EMPTY`. The `board` module's `fill_empty` handles repopulation. This creates massive cascades.

**Rationale:** Board Clear is the ultimate reward. Let it be epic.

---

### EC-7: Special Gem at Edge/Corner

**Scenario:** Line Blast at row 0 or Radial Bomb at corner.

**Decision:** Effects are bounded by board dimensions. Line Blast at row 0 still clears the entire row. Radial Bomb at (0,0) clears 4 positions (2x2 visible area).

**Rationale:** Effects don't wrap around. Stay within grid bounds.

---

### EC-8: Two Identical Special Gems Fused

**Scenario:** LINE_BLAST_H swapped with LINE_BLAST_H.

**Decision:** Same as any Line+Line fusion: Cross Blast. The specific orientations don't matter for the fusion type.

**Rationale:** Simplifies fusion rules. All Line+Line combinations produce Cross Blast.

---

### EC-9: Invalid Position for Effect Application

**Scenario:** `apply_effect` called with effect containing out-of-bounds positions.

**Decision:** Effects are calculated with bounds checking, so this shouldn't happen. If it does, the operation succeeds for valid positions and ignores invalid ones (defensive coding).

**Rationale:** Defensive programming. Invalid effects are a bug upstream, but we don't want to crash.

---

## Open Questions

None. All design decisions resolved within existing guidance and the GDD specifications.

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent (special_gems) |
