"""Core domain types for ChromaCrush.

Defines opaque identifiers, gem types, positions, and moves.
All modules import these types but NEVER define their own versions.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import NewType
from uuid import UUID

# Opaque identifiers — use NewType so static analysis catches misuse,
# but at runtime these are just UUIDs.
PlayerId = NewType("PlayerId", UUID)
MatchId = NewType("MatchId", UUID)
ArtifactId = NewType("ArtifactId", UUID)
EventId = NewType("EventId", UUID)


class GemType(IntEnum):
    """Gem colors represented as integers for NumPy compatibility.

    Values 1-6 are standard gems, 0 is empty, negatives are special gem
    type identifiers (used in MatchResult / _determine_special_gem, but
    no longer stored directly on the board grid).
    """

    EMPTY = 0
    RED = 1
    BLUE = 2
    GREEN = 3
    YELLOW = 4
    PURPLE = 5
    ORANGE = 6
    OBSTACLE = 7

    # Special gem type identifiers (used in MatchResult, not on grid)
    LINE_BLAST_H = -1
    LINE_BLAST_V = -2
    RADIAL_BOMB = -3
    CHROMATIC_ORB = -4


class GemFunction(IntEnum):
    """Function attribute for gems.

    Every cell has both a color (GemType 1-6) and a function.
    Standard gems are NEUTRAL. Special gems have a non-zero function
    and retain their color for match participation.
    """

    NEUTRAL = 0
    LINE_BLAST_H = 1
    LINE_BLAST_V = 2
    RADIAL_BOMB = 3
    CHROMATIC_ORB = 4


# Mapping between GemType special identifiers and GemFunction values.
SPECIAL_TO_FUNCTION: dict["GemType", "GemFunction"] = {
    GemType.LINE_BLAST_H: GemFunction.LINE_BLAST_H,
    GemType.LINE_BLAST_V: GemFunction.LINE_BLAST_V,
    GemType.RADIAL_BOMB: GemFunction.RADIAL_BOMB,
    GemType.CHROMATIC_ORB: GemFunction.CHROMATIC_ORB,
}
FUNCTION_TO_SPECIAL: dict["GemFunction", "GemType"] = {
    v: k for k, v in SPECIAL_TO_FUNCTION.items()
}

# --- Mega gem encoding (two specials fused into one cell) ---
# Encoded as funcA * 10 + funcB where funcA <= funcB (canonical order).
MEGA_GEM_VALUES = frozenset({11, 12, 13, 14, 22, 23, 24, 33, 34, 44})


def is_mega_gem(func_value: int) -> bool:
    """Check if a func_grid value represents a mega gem."""
    return func_value in MEGA_GEM_VALUES


def encode_mega_gem(func_a: GemFunction, func_b: GemFunction) -> int:
    """Encode two special functions into a single mega gem value."""
    a, b = int(func_a), int(func_b)
    if a > b:
        a, b = b, a
    return a * 10 + b


def decode_mega_gem(mega_value: int) -> tuple[GemFunction, GemFunction]:
    """Decode a mega gem value into its two component functions."""
    return GemFunction(mega_value // 10), GemFunction(mega_value % 10)


def mega_gem_dominant(mega_value: int) -> GemFunction:
    """Return the dominant (higher-priority) function of a mega gem."""
    a, b = decode_mega_gem(mega_value)
    return max(a, b, key=lambda f: int(f))


@dataclass(frozen=True)
class Position:
    """Zero-indexed board position. Origin (0,0) is top-left."""

    row: int
    col: int

    def __post_init__(self) -> None:
        if self.row < 0 or self.col < 0:
            raise ValueError("Position coordinates must be non-negative")

    def is_adjacent_to(self, other: "Position") -> bool:
        """Check if positions are orthogonally adjacent (not diagonal)."""
        row_diff = abs(self.row - other.row)
        col_diff = abs(self.col - other.col)
        return (row_diff == 1 and col_diff == 0) or (row_diff == 0 and col_diff == 1)


@dataclass(frozen=True)
class Move:
    """A player's move: swap two adjacent gems."""

    from_pos: Position
    to_pos: Position
    timestamp_ms: int  # Client timestamp for replay

    def __post_init__(self) -> None:
        if not self.from_pos.is_adjacent_to(self.to_pos):
            raise ValueError("Move positions must be adjacent")
