"""Mega gem attraction and effect logic (mixin for BoardService)."""

from __future__ import annotations

import numpy as np

from src.core.types.board import BoardState
from src.core.types.game import (
    GemFunction,
    GemType,
    Position,
    encode_mega_gem,
    is_mega_gem,
)
from src.modules.board.types import SpecialAttraction


class _MegaGemsMixin:
    """Mega gem attraction detection, processing, and effect calculation."""

    @staticmethod
    def _check_special_attractions(
        board: BoardState,
    ) -> list[tuple[Position, Position, Position]]:
        """Find pairs of specials exactly 2 cells apart with a regular gem between.

        Scans right (+2 col) and down (+2 row) to avoid double-counting.
        Greedy: each gem participates in at most one attraction per call.

        Returns list of (posA, posB, centerPos) triples.
        """
        fg = board.func_grid  # type: ignore[union-attr]

        # Fast exit: need at least 2 specials for any attraction.
        if np.count_nonzero(fg) < 2:
            return []

        func_list = fg.tolist()  # type: ignore[union-attr]
        grid_list = board.grid.tolist()
        h, w = board.height, board.width
        used: set[tuple[int, int]] = set()
        results: list[tuple[Position, Position, Position]] = []

        for r in range(h):
            func_row = func_list[r]
            for c in range(w):
                fv = func_row[c]
                if not (1 <= fv <= 4):
                    # Only single specials (1-4) participate in attraction.
                    # Skip neutral (0), megas (11-44), and walls (10+).
                    continue
                if (r, c) in used:
                    continue

                # Check right (+2 col).
                if c + 2 < w:
                    mid_fv = func_row[c + 1]
                    right_fv = func_row[c + 2]
                    if (
                        1 <= right_fv <= 4
                        and mid_fv == 0
                        and 1 <= grid_list[r][c + 1] <= 6
                        and (r, c + 1) not in used
                        and (r, c + 2) not in used
                    ):
                        results.append(
                            (
                                Position(r, c),
                                Position(r, c + 2),
                                Position(r, c + 1),
                            )
                        )
                        used.update({(r, c), (r, c + 1), (r, c + 2)})
                        continue  # This gem is consumed.

                # Check down (+2 row).
                if r + 2 < h:
                    mid_fv = func_list[r + 1][c]
                    down_fv = func_list[r + 2][c]
                    if (
                        1 <= down_fv <= 4
                        and mid_fv == 0
                        and 1 <= grid_list[r + 1][c] <= 6
                        and (r + 1, c) not in used
                        and (r + 2, c) not in used
                    ):
                        results.append(
                            (
                                Position(r, c),
                                Position(r + 2, c),
                                Position(r + 1, c),
                            )
                        )
                        used.update({(r, c), (r + 1, c), (r + 2, c)})

        return results

    @staticmethod
    def _process_attractions(
        board: BoardState,
        triples: list[tuple[Position, Position, Position]],
    ) -> tuple[BoardState, list[SpecialAttraction]]:
        """Apply attraction merges: source specials lose function, center becomes mega.

        No gems are removed. Only func_grid mutates. Color grid is unchanged.

        Returns updated board and list of SpecialAttraction records.
        """
        new_func = board.func_grid.copy()  # type: ignore[union-attr]
        attractions: list[SpecialAttraction] = []

        for pos_a, pos_b, center in triples:
            func_a = GemFunction(int(new_func[pos_a.row, pos_a.col]))
            func_b = GemFunction(int(new_func[pos_b.row, pos_b.col]))
            mega = encode_mega_gem(func_a, func_b)

            new_func[pos_a.row, pos_a.col] = 0
            new_func[pos_b.row, pos_b.col] = 0
            new_func[center.row, center.col] = mega

            attractions.append(
                SpecialAttraction(
                    pos_a=pos_a,
                    pos_b=pos_b,
                    center_pos=center,
                    func_a=func_a,
                    func_b=func_b,
                    mega_func=mega,
                )
            )

        return BoardState(grid=board.grid.copy(), func_grid=new_func), attractions

    @staticmethod
    def _process_attractions_inplace(
        board: BoardState,
        triples: list[tuple[Position, Position, Position]],
    ) -> list[SpecialAttraction]:
        """Apply attraction merges in place: source specials lose function, center becomes mega.

        Mutates board.func_grid directly. Color grid is unchanged.
        Returns list of SpecialAttraction records.
        """
        func = board.func_grid  # type: ignore[union-attr]
        attractions: list[SpecialAttraction] = []

        for pos_a, pos_b, center in triples:
            func_a = GemFunction(int(func[pos_a.row, pos_a.col]))
            func_b = GemFunction(int(func[pos_b.row, pos_b.col]))
            mega = encode_mega_gem(func_a, func_b)

            func[pos_a.row, pos_a.col] = 0
            func[pos_b.row, pos_b.col] = 0
            func[center.row, center.col] = mega

            attractions.append(
                SpecialAttraction(
                    pos_a=pos_a,
                    pos_b=pos_b,
                    center_pos=center,
                    func_a=func_a,
                    func_b=func_b,
                    mega_func=mega,
                )
            )

        return attractions

    def _calculate_mega_gem_effect_positions(
        self,
        board: BoardState,
        position: Position,
        mega_value: int,
        trigger_color: GemType | None = None,
    ) -> set[Position]:
        """Return positions cleared by activating a mega gem.

        Delegates to the schema-driven EffectInterpreter.
        Source position always included.
        """
        return self._effect_interp.calculate_mega_effect_positions(
            board,
            position,
            mega_value,
            trigger_color,
        )
