"""Board state types for ChromaCrush.

Defines the board grid, board state snapshot, match groups, and match results.
Uses NumPy for efficient board representation.
"""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from src.core.types.game import GemType, Position

# Type alias for the board grid — shape: (height, width), dtype: int8
BoardGrid = NDArray[np.int8]


@dataclass
class BoardState:
    """Immutable snapshot of the board at a point in time.

    Every cell has two attributes stored in parallel grids:
    - ``grid``: color values (0 = empty, 1-6 = standard gem colors).
    - ``func_grid``: function values (0 = NEUTRAL, 1-4 = special abilities).

    Use BoardState.copy() before mutation operations.
    """

    grid: BoardGrid
    func_grid: BoardGrid | None = None
    width: int = field(init=False)
    height: int = field(init=False)

    def __post_init__(self) -> None:
        self.height, self.width = self.grid.shape
        if self.func_grid is None:
            self.func_grid = np.zeros_like(self.grid)

    def get(self, pos: Position) -> GemType:
        """Get gem color at position."""
        return GemType(self.grid[pos.row, pos.col])

    def copy(self) -> "BoardState":
        """Create a mutable copy (both grids)."""
        return BoardState(
            grid=self.grid.copy(),
            func_grid=self.func_grid.copy(),  # type: ignore[union-attr]
        )

    def to_list(self) -> list[list[int]]:
        """Convert color grid to JSON-serializable list (legacy compat)."""
        return self.grid.tolist()

    def to_dict(self) -> dict[str, list[list[int]]]:
        """Convert both grids to JSON-serializable dict."""
        return {
            "cells": self.grid.tolist(),
            "functions": self.func_grid.tolist(),  # type: ignore[union-attr]
        }

    @classmethod
    def from_list(cls, data: list | dict) -> "BoardState":
        """Create from JSON data.

        Accepts both legacy format (plain ``[[int]]`` — func_grid defaults
        to NEUTRAL) and new format (``{"cells": ..., "functions": ...}``).
        """
        if isinstance(data, dict):
            return cls.from_dict(data)
        return cls(grid=np.array(data, dtype=np.int8))

    @classmethod
    def from_dict(cls, data: dict[str, list[list[int]]]) -> "BoardState":
        """Create from JSON dict with both grids."""
        return cls(
            grid=np.array(data["cells"], dtype=np.int8),
            func_grid=np.array(data["functions"], dtype=np.int8),
        )


@dataclass(frozen=True)
class MatchGroup:
    """A group of matched gems (3+ in a row/column)."""

    positions: frozenset[Position]
    gem_type: GemType
    is_horizontal: bool
    length: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "length", len(self.positions))


@dataclass(frozen=True)
class MatchResult:
    """Result of match detection on a board."""

    matches: tuple[MatchGroup, ...]
    total_gems_matched: int
    creates_special_gem: bool
    special_gem_type: GemType | None = None
    special_gem_position: Position | None = None
