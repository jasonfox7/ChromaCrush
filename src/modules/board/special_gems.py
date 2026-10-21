"""Special gem effect calculation and clearing logic (mixin for BoardService).

Chain-reaction triggering is now handled by _drain_clear_queue in cascade.py.
This mixin retains: effect calculation, batch clearing.
"""

from __future__ import annotations

import numpy as np

from src.core.types.board import BoardState
from src.core.types.game import GemType, Position


class _SpecialGemsMixin:
    """Special gem effect calculation and board clearing operations."""

    def _calculate_special_effect_positions(
        self,
        board: BoardState,
        position: Position,
        gem_type: GemType,
        trigger_color: GemType | None = None,
        overrides: dict | None = None,
    ) -> set[Position]:
        """Return the set of positions cleared by activating a special gem.

        Delegates to the schema-driven EffectInterpreter.
        The source position is always included.

        Args:
            board: Current board state.
            position: Position of the special gem being activated.
            gem_type: The special gem type (negative GemType value).
            trigger_color: Color of the gem that triggered the special.
            overrides: Optional parameter overrides from card effects (Hook 2).
        """
        func_value = abs(int(gem_type))
        return self._effect_interp.calculate_effect_positions(
            board,
            position,
            func_value,
            trigger_color,
            overrides=overrides,
        )

    @staticmethod
    def _clear_positions_inplace(board: BoardState, positions: set[Position]) -> None:
        """Zero out grid and func_grid at the given positions in place.

        Uses numpy fancy indexing for batch zeroing when the set is large enough.
        """
        if not positions:
            return
        h, w = board.height, board.width
        # Filter in-bounds and build coordinate arrays.
        rows = np.empty(len(positions), dtype=np.intp)
        cols = np.empty(len(positions), dtype=np.intp)
        n = 0
        for pos in positions:
            if 0 <= pos.row < h and 0 <= pos.col < w:
                rows[n] = pos.row
                cols[n] = pos.col
                n += 1
        if n > 0:
            r = rows[:n]
            c = cols[:n]
            board.grid[r, c] = 0
            board.func_grid[r, c] = 0  # type: ignore[index]

    @staticmethod
    def _clear_matches_inplace(board: BoardState, matches: "MatchResult") -> None:  # type: ignore[name-defined]  # noqa: F821
        """Zero all matched positions in both grids in place."""
        # Collect all positions, then batch-zero with fancy indexing.
        all_pos: list[Position] = []
        for mg in matches.matches:
            all_pos.extend(mg.positions)
        if not all_pos:
            return
        rows = np.array([p.row for p in all_pos], dtype=np.intp)
        cols = np.array([p.col for p in all_pos], dtype=np.intp)
        board.grid[rows, cols] = 0
        board.func_grid[rows, cols] = 0  # type: ignore[index]
