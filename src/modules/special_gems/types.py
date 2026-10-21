"""Special gems module types -- immutable result dataclasses and enums.

All types are frozen dataclasses for thread safety and clarity.
Special gems types are consumed by dependent modules (board_gen, match)
and by presentation adapters for display formatting.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.core.types.game import GemType, Position
from src.modules.scoring.types import SpecialGemBonus

# The canonical set of special gem types (negative GemType values).
SPECIAL_GEM_TYPES: frozenset[GemType] = frozenset(
    {
        GemType.LINE_BLAST_H,
        GemType.LINE_BLAST_V,
        GemType.RADIAL_BOMB,
        GemType.CHROMATIC_ORB,
    }
)

# Standard gem types (1-6) for target color validation.
STANDARD_GEM_TYPES: frozenset[GemType] = frozenset(
    {
        GemType.RED,
        GemType.BLUE,
        GemType.GREEN,
        GemType.YELLOW,
        GemType.PURPLE,
        GemType.ORANGE,
    }
)


class FusionType(Enum):
    """Categories of special gem fusions."""

    CROSS_BLAST = "cross_blast"  # Line + Line (any orientation)
    TRIPLE_LINE = "triple_line"  # Line + Radial
    COLOR_LINE_BLAST = "color_line_blast"  # Line + Chromatic
    MEGA_BOMB = "mega_bomb"  # Radial + Radial
    COLOR_BOMB = "color_bomb"  # Radial + Chromatic
    BOARD_CLEAR = "board_clear"  # Chromatic + Chromatic


@dataclass(frozen=True)
class SpecialGemEffect:
    """Result of calculating a special gem activation.

    Attributes:
        gem_type: The special gem type that was activated.
        source_position: Position of the activated special gem.
        affected_positions: Positions that will be cleared.
        bonus_score: Bonus points from scoring module.
        triggers_special_gems: Other special gems in affected area.
        description: Human-readable description.
    """

    gem_type: GemType
    source_position: Position
    affected_positions: frozenset[Position]
    bonus_score: SpecialGemBonus
    triggers_special_gems: list[Position]
    description: str


@dataclass(frozen=True)
class FusionEffect:
    """Result of calculating a special gem fusion.

    Attributes:
        gem_a_type: First special gem type (normalized: lower value).
        gem_b_type: Second special gem type (normalized: higher value).
        fusion_type: Enum describing the fusion category.
        source_positions: Positions of the two fused gems.
        affected_positions: All positions that will be cleared.
        bonus_score: Combined bonus from scoring module.
        triggers_special_gems: Other special gems in affected area.
        secondary_effects: Sub-effects for fusions that spawn new specials.
        description: Human-readable description.
    """

    gem_a_type: GemType
    gem_b_type: GemType
    fusion_type: FusionType
    source_positions: tuple[Position, Position]
    affected_positions: frozenset[Position]
    bonus_score: SpecialGemBonus
    triggers_special_gems: list[Position]
    secondary_effects: list[SpecialGemEffect]
    description: str
