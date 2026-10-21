"""Match detection and special gem creation logic (mixin for BoardService)."""

from __future__ import annotations

import numpy as np

from src.core.types.board import BoardState, MatchGroup, MatchResult
from src.core.types.game import (
    FUNCTION_TO_SPECIAL,
    SPECIAL_TO_FUNCTION,
    GemFunction,
    GemType,
    Position,
)
from src.modules.board._constants import SENTINEL


class _DetectionMixin:
    """Match detection: run scanning, special gem rules, and flood-fill expansion."""

    def detect_matches(
        self,
        board: BoardState,
        min_length: int = 3,
        *,
        expand: bool = True,
        modifiers: object | None = None,
        cascade_seed: int = 0,
    ) -> MatchResult:
        """Scan the board for horizontal and vertical runs of matching gems.

        Gem colors (> 0) in board.grid are eligible for matching. Empty
        cells (0) are skipped. Colored special gems participate in runs
        of their base color automatically (their function is in func_grid).

        After run detection, contiguous same-coloured tiles adjacent to any
        matched position are included via flood-fill (unless *expand* is
        ``False``).

        Special gem creation rules (evaluated on raw runs before expansion):
        - 4-match horizontal -> LINE_BLAST_H at middle position
        - 4-match vertical   -> LINE_BLAST_V at middle position
        - 5+ match           -> RADIAL_BOMB at centre
        - T/L shape (position in both H and V match) -> CHROMATIC_ORB

        Args:
            board: Board state to analyse.
            min_length: Minimum run length for a match (default 3).
            expand: Flood-fill to contiguous same-coloured tiles (default True).

        Returns:
            A ``MatchResult`` describing all found matches and any
            special gem that should be created.
        """
        matches: list[MatchGroup] = []
        grid = board.grid.tolist()  # Python list — avoids numpy scalar overhead
        h, w = board.height, board.width

        # --- Horizontal runs ---
        for row in range(h):
            grid_row = grid[row]
            run_start = 0
            run_gem = grid_row[0]

            for col in range(1, w + 1):
                current = grid_row[col] if col < w else SENTINEL
                if current == run_gem and 1 <= run_gem <= 6:
                    continue

                run_length = col - run_start
                if run_length >= min_length and 1 <= run_gem <= 6:
                    positions = frozenset(
                        Position(row, c) for c in range(run_start, col)
                    )
                    matches.append(
                        MatchGroup(
                            positions=positions,
                            gem_type=GemType(run_gem),
                            is_horizontal=True,
                        )
                    )

                run_start = col
                run_gem = current

        # --- Vertical runs ---
        for col in range(w):
            run_start = 0
            run_gem = grid[0][col]

            for row in range(1, h + 1):
                current = grid[row][col] if row < h else SENTINEL
                if current == run_gem and 1 <= run_gem <= 6:
                    continue

                run_length = row - run_start
                if run_length >= min_length and 1 <= run_gem <= 6:
                    positions = frozenset(
                        Position(r, col) for r in range(run_start, row)
                    )
                    matches.append(
                        MatchGroup(
                            positions=positions,
                            gem_type=GemType(run_gem),
                            is_horizontal=False,
                        )
                    )

                run_start = row
                run_gem = current

        if not matches:
            return MatchResult(
                matches=(),
                total_gems_matched=0,
                creates_special_gem=False,
                special_gem_type=None,
                special_gem_position=None,
            )

        # --- Special gem detection (on raw runs, before expansion) ---
        special_type, special_pos = self._determine_special_gem(matches)

        # --- Hook 5a: Special type bias — may swap the determined special type ---
        if special_type is not None and modifiers is not None and not modifiers.is_empty:
            bias, _bias_applied = modifiers.get_special_type_bias()
            if bias:
                # Build weighted distribution: default 1.0 per function,
                # bias cards add to their target function's weight.
                all_funcs = [
                    GemFunction.LINE_BLAST_H,
                    GemFunction.LINE_BLAST_V,
                    GemFunction.RADIAL_BOMB,
                    GemFunction.CHROMATIC_ORB,
                ]
                weights = [1.0 + bias.get(int(f), 0.0) for f in all_funcs]
                total_w = sum(weights)
                # Deterministic weighted selection using LCG on cascade_seed.
                roll = ((cascade_seed * 1103515245 + 12345) & 0x7FFFFFFF) % 1000
                cumulative = 0.0
                selected_func = SPECIAL_TO_FUNCTION.get(special_type, all_funcs[0])
                for func, w in zip(all_funcs, weights):
                    cumulative += (w / total_w) * 1000
                    if roll < cumulative:
                        selected_func = func
                        break
                biased_type = FUNCTION_TO_SPECIAL.get(selected_func)
                if biased_type is not None:
                    special_type = biased_type

        # --- Hook 5b: Fortune's Favor — 3-match special creation chance ---
        if special_type is None and modifiers is not None and not modifiers.is_empty:
            # Check if any match is exactly 3 (no special from rules).
            has_three_match = any(mg.length == 3 for mg in matches)
            if has_three_match:
                fortune_func, _fortune_applied = (
                    modifiers.get_three_match_special_chance(cascade_seed)
                )
                if fortune_func is not None:
                    # Pick the first 3-match group as the special position.
                    for mg in matches:
                        if mg.length == 3:
                            # Use middle position of the 3-match.
                            sorted_pos = sorted(
                                mg.positions,
                                key=lambda p: (p.row, p.col),
                            )
                            special_pos = sorted_pos[1]  # middle
                            # Map function value to GemType.
                            try:
                                special_type = FUNCTION_TO_SPECIAL[
                                    GemFunction(fortune_func)
                                ]
                            except (ValueError, KeyError):
                                special_type = None
                                special_pos = None
                            break

        # --- Expand to contiguous same-coloured tiles ---
        final_matches = self._expand_contiguous(board, matches) if expand else matches

        # --- De-duplicate positions for total count ---
        all_positions: set[Position] = set()
        for mg in final_matches:
            all_positions.update(mg.positions)
        total_gems = len(all_positions)

        result = MatchResult(
            matches=tuple(final_matches),
            total_gems_matched=total_gems,
            creates_special_gem=special_type is not None,
            special_gem_type=special_type,
            special_gem_position=special_pos,
        )

        self._logger.debug(
            "board.match_detected",
            match_count=len(matches),
            total_gems=total_gems,
            creates_special=special_type is not None,
        )

        return result

    def _determine_special_gem(
        self, matches: list[MatchGroup]
    ) -> tuple[GemType | None, Position | None]:
        """Decide which special gem (if any) a set of matches creates.

        Delegates to the schema-driven EffectInterpreter which iterates
        special_creation_rules by priority order.

        Returns:
            (special_gem_type, special_gem_position) or (None, None).
        """
        return self._effect_interp.determine_special_gem(matches)

    @staticmethod
    def _expand_contiguous(
        board: BoardState, matches: list[MatchGroup]
    ) -> list[MatchGroup]:
        """Expand match groups by flood-filling to all contiguous same-colored tiles.

        Uses numpy boolean mask dilation for the flood fill: for each matched
        color, build a mask of that color on the grid, seed with matched
        positions, then iteratively dilate (shift N/S/E/W and OR with color
        mask) until no new cells are added.

        Args:
            board: Board state used for adjacency lookups.
            matches: Raw match groups from run detection.

        Returns:
            Expanded match groups (one per colour present in the input).
        """
        grid = board.grid
        h, w = board.height, board.width

        # Collect seed positions per colour.
        color_seeds: dict[int, list[tuple[int, int]]] = {}
        for mg in matches:
            gem_val = int(mg.gem_type)
            seeds = color_seeds.setdefault(gem_val, [])
            for pos in mg.positions:
                seeds.append((pos.row, pos.col))

        expanded_groups: list[MatchGroup] = []

        for gem_val, seeds in color_seeds.items():
            # Boolean mask of cells with this color.
            color_mask = grid == gem_val

            # Seed mask from matched positions.
            reached = np.zeros((h, w), dtype=np.bool_)
            seed_rows = np.array([s[0] for s in seeds], dtype=np.intp)
            seed_cols = np.array([s[1] for s in seeds], dtype=np.intp)
            reached[seed_rows, seed_cols] = True

            # Iterative dilation until stable.
            while True:
                # Dilate: shift in 4 directions, OR together, mask to color.
                dilated = np.zeros((h, w), dtype=np.bool_)
                if h > 1:
                    dilated[1:, :] |= reached[:-1, :]  # shift down
                    dilated[:-1, :] |= reached[1:, :]  # shift up
                if w > 1:
                    dilated[:, 1:] |= reached[:, :-1]  # shift right
                    dilated[:, :-1] |= reached[:, 1:]  # shift left
                new_reached = (reached | dilated) & color_mask
                if np.array_equal(new_reached, reached):
                    break
                reached = new_reached

            # Extract positions from the mask.
            rs, cs = np.where(reached)
            expanded_groups.append(
                MatchGroup(
                    positions=frozenset(
                        Position(int(rs[i]), int(cs[i])) for i in range(len(rs))
                    ),
                    gem_type=GemType(gem_val),
                    is_horizontal=True,  # orientation irrelevant after expansion
                )
            )

        return expanded_groups
