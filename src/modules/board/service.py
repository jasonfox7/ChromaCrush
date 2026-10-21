"""Board module service — core match-3 grid engine.

Implements board creation, gem swapping, match detection, gravity,
empty-cell filling, and full move processing with cascade loops.
All methods are synchronous. Board state is immutable — every operation
returns a new BoardState without modifying the input.

Dependencies are injected via ``__init__``. No direct imports from
``src.core`` concrete implementations.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.core.protocols.config import ConfigProtocol
from src.core.protocols.error_service import ErrorServiceProtocol
from src.core.protocols.logger import LoggerProtocol
from src.core.types.board import BoardState, MatchResult
from src.core.types.game import (
    SPECIAL_TO_FUNCTION,
    GemType,
    Move,
    Position,
)
from src.modules.board._constants import (
    LCG_INCREMENT,
    LCG_MASK,
    LCG_MULTIPLIER,
    MAX_CASCADE_STEPS,
    OBSTACLE_COLOR,
)
from src.modules.board.cascade import _CascadeMixin
from src.modules.board.detection import _DetectionMixin
from src.modules.board.effect_interpreter import EffectInterpreter
from src.modules.board.mega_gems import _MegaGemsMixin
from src.modules.board.schema_loader import load_board_rules
from src.modules.board.special_gems import _SpecialGemsMixin
from src.modules.board.types import (
    CascadeStep,
    GemDrop,
    GemSpawn,
    MoveProcessingResult,
    SpecialActivation,
)


class BoardService(
    _CascadeMixin,
    _DetectionMixin,
    _SpecialGemsMixin,
    _MegaGemsMixin,
):
    """Core match-3 grid logic.

    All methods are regular ``def`` (fully synchronous). The service
    operates on in-memory NumPy arrays and never performs I/O.

    Args:
        config: Configuration service for board dimensions and gem count.
        logger: Structured logger for diagnostic events.
        errors: Error factory for creating typed application errors.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        *,
        debug_logger: Any = None,
        schema_path: str | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._debug = debug_logger

        # Load board rules schema and create effect interpreter.
        schema = load_board_rules(schema_path)
        self._effect_interp = EffectInterpreter(schema)
        board_cfg = self._effect_interp.get_board_config()

        # Board dimensions from schema, with app.toml as override.
        self._board_width: int = config.get("game.board_width", board_cfg["width"])
        self._board_height: int = config.get("game.board_height", board_cfg["height"])
        self._gem_types: int = config.get("game.gem_types", board_cfg["gem_types"])
        self._min_match_length: int = config.get(
            "game.min_match_length", board_cfg["min_match_length"]
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_board(self, width: int, height: int, seed: int) -> BoardState:
        """Generate a new board with no initial 3-in-a-row matches.

        Uses a cell-by-cell fill strategy that excludes colours which
        would create a horizontal or vertical run of 3. With 6 gem types
        and at most 2 exclusions per cell, at least 4 colours are always
        available, so the algorithm is guaranteed to succeed.

        Args:
            width: Board width in columns.
            height: Board height in rows.
            seed: RNG seed for deterministic generation.

        Returns:
            A new ``BoardState`` populated with standard gems only.
        """
        rng = np.random.default_rng(seed)
        grid = np.zeros((height, width), dtype=np.int8)

        for row in range(height):
            for col in range(width):
                available = list(range(1, self._gem_types + 1))

                # Exclude the colour that would extend a horizontal run to 3.
                if col >= 2:
                    left1 = int(grid[row, col - 1])
                    left2 = int(grid[row, col - 2])
                    if left1 == left2 and left1 != 0 and left1 in available:
                        available.remove(left1)

                # Exclude the colour that would extend a vertical run to 3.
                if row >= 2:
                    up1 = int(grid[row - 1, col])
                    up2 = int(grid[row - 2, col])
                    if up1 == up2 and up1 != 0 and up1 in available:
                        available.remove(up1)

                grid[row, col] = rng.choice(available)

        board = BoardState(grid=grid)

        self._logger.debug(
            "board.created",
            seed=seed,
            width=width,
            height=height,
            has_valid_moves=self.has_valid_moves(board),
        )

        return board

    def create_board_with_obstacles(
        self,
        width: int,
        height: int,
        seed: int,
        obstacles: list[dict],
        gem_colors: int = 6,
    ) -> BoardState:
        """Generate a board with pre-placed obstacles and no initial matches.

        Mirrors ``create_board`` but places obstacles first, then fills
        remaining cells with the same no-match-3 cell-by-cell strategy.

        Args:
            width: Board width in columns.
            height: Board height in rows.
            seed: RNG seed for deterministic generation.
            obstacles: List of ``{"row": r, "col": c, "func": f}`` dicts.
            gem_colors: Number of gem colors to use (default 6, allows
                reduced palettes at higher campaign levels).

        Returns:
            A new ``BoardState`` with obstacles placed and remaining cells
            filled with standard gems.
        """
        rng = np.random.default_rng(seed)
        grid = np.zeros((height, width), dtype=np.int8)
        func_grid = np.zeros((height, width), dtype=np.int8)

        # Place obstacles first.
        for obs in obstacles:
            r, c, f = obs["row"], obs["col"], obs["func"]
            grid[r, c] = OBSTACLE_COLOR
            func_grid[r, c] = f

        # Fill remaining cells (same no-match-3 logic as create_board).
        for row in range(height):
            for col in range(width):
                if grid[row, col] == OBSTACLE_COLOR:
                    continue  # Don't overwrite obstacles.

                available = list(range(1, gem_colors + 1))

                # Exclude the colour that would extend a horizontal run to 3.
                if col >= 2:
                    left1 = int(grid[row, col - 1])
                    left2 = int(grid[row, col - 2])
                    if (
                        left1 == left2
                        and 1 <= left1 <= 6
                        and left1 in available
                    ):
                        available.remove(left1)

                # Exclude the colour that would extend a vertical run to 3.
                if row >= 2:
                    up1 = int(grid[row - 1, col])
                    up2 = int(grid[row - 2, col])
                    if (
                        up1 == up2
                        and 1 <= up1 <= 6
                        and up1 in available
                    ):
                        available.remove(up1)

                grid[row, col] = rng.choice(available)

        board = BoardState(grid=grid, func_grid=func_grid)

        self._logger.debug(
            "board.created_with_obstacles",
            seed=seed,
            width=width,
            height=height,
            obstacle_count=len(obstacles),
        )

        return board

    def swap_gems(self, board: BoardState, move: Move) -> BoardState:
        """Swap two adjacent gems, returning a new board.

        Validates that both positions are in-bounds, orthogonally adjacent,
        and neither cell is empty. Does **not** check whether the swap
        creates a match — callers should use ``detect_matches`` for that.

        Args:
            board: Current board state (unmodified).
            move: The swap to execute.

        Returns:
            A new ``BoardState`` with the two positions exchanged.

        Raises:
            AppError: VALIDATION_OUT_OF_BOUNDS, VALIDATION_POSITIONS_NOT_ADJACENT,
                or VALIDATION_INVALID_GEM_SWAP.
        """
        self._validate_position(move.from_pos, board)
        self._validate_position(move.to_pos, board)

        if not move.from_pos.is_adjacent_to(move.to_pos):
            raise self._errors.validation(
                "Positions are not orthogonally adjacent",
                code="VALIDATION_POSITIONS_NOT_ADJACENT",
                from_pos=str(move.from_pos),
                to_pos=str(move.to_pos),
            )

        from_gem = board.get(move.from_pos)
        to_gem = board.get(move.to_pos)

        if from_gem == GemType.EMPTY or to_gem == GemType.EMPTY:
            raise self._errors.validation(
                "Cannot swap empty cell",
                code="VALIDATION_INVALID_GEM_SWAP",
                from_gem=int(from_gem),
                to_gem=int(to_gem),
                reason="Cannot swap empty cell",
            )

        new_board = board.copy()
        fr, fc = move.from_pos.row, move.from_pos.col
        tr, tc = move.to_pos.row, move.to_pos.col
        # Swap colors.
        new_board.grid[fr, fc], new_board.grid[tr, tc] = (
            new_board.grid[tr, tc],
            new_board.grid[fr, fc],
        )
        # Swap functions.
        new_board.func_grid[fr, fc], new_board.func_grid[tr, tc] = (  # type: ignore[index]
            new_board.func_grid[tr, tc],  # type: ignore[index]
            new_board.func_grid[fr, fc],  # type: ignore[index]
        )
        return new_board

    def clear_matches(self, board: BoardState, matches: MatchResult) -> BoardState:
        """Set all matched positions to EMPTY, returning a new board.

        Args:
            board: Current board state (unmodified).
            matches: The match result whose positions should be cleared.

        Returns:
            A new ``BoardState`` with matched cells set to ``GemType.EMPTY``.
        """
        new_board = board.copy()
        for mg in matches.matches:
            for pos in mg.positions:
                new_board.grid[pos.row, pos.col] = 0
                new_board.func_grid[pos.row, pos.col] = 0  # type: ignore[index]
        return new_board

    def apply_gravity(self, board: BoardState) -> tuple[BoardState, list[GemDrop]]:
        """Drop gems down to fill empty spaces within each column.

        Obstacle cells (grid == OBSTACLE_COLOR) are immovable walls that
        partition columns into independently-compacting segments.

        Args:
            board: Board with empty cells after match clearing.

        Returns:
            Tuple of (new BoardState, list of GemDrop records).
        """
        new_grid = board.grid.copy()
        new_func = board.func_grid.copy()  # type: ignore[union-attr]
        drops: list[GemDrop] = []

        for col in range(board.width):
            column = new_grid[:, col].copy()
            func_column = new_func[:, col].copy()
            obstacle_rows = set(int(r) for r in np.where(column == OBSTACLE_COLOR)[0])

            if not obstacle_rows:
                # No obstacles — original fast path.
                non_empty_mask = column != 0
                non_empty_gems = column[non_empty_mask]
                non_empty_funcs = func_column[non_empty_mask]
                empty_count = board.height - len(non_empty_gems)

                if empty_count == 0:
                    continue

                original_rows = np.where(non_empty_mask)[0]
                for i, orig_row in enumerate(original_rows):
                    new_row = empty_count + i
                    if orig_row != new_row:
                        drops.append(
                            GemDrop(
                                gem_type=GemType(int(non_empty_gems[i])),
                                from_pos=Position(int(orig_row), col),
                                to_pos=Position(int(new_row), col),
                                distance=int(new_row - orig_row),
                            )
                        )

                zeros = np.zeros(empty_count, dtype=np.int8)
                new_grid[:, col] = np.concatenate([zeros, non_empty_gems])
                new_func[:, col] = np.concatenate([zeros, non_empty_funcs])
                continue

            # Segment the column at obstacle positions.
            boundaries = sorted(obstacle_rows)
            segments: list[tuple[int, int]] = []
            prev = 0
            for obs_row in boundaries:
                if obs_row > prev:
                    segments.append((prev, obs_row - 1))
                prev = obs_row + 1
            if prev < board.height:
                segments.append((prev, board.height - 1))

            # Compact each segment independently.
            for seg_start, seg_end in segments:
                seg_len = seg_end - seg_start + 1
                seg_colors = column[seg_start : seg_end + 1].copy()
                seg_funcs = func_column[seg_start : seg_end + 1].copy()
                non_empty = seg_colors != 0
                gems = seg_colors[non_empty]
                gem_funcs = seg_funcs[non_empty]
                empty_count = seg_len - len(gems)

                if empty_count == 0:
                    continue

                original_offsets = np.where(non_empty)[0]
                for i, orig_offset in enumerate(original_offsets):
                    new_offset = empty_count + i
                    if orig_offset != new_offset:
                        drops.append(
                            GemDrop(
                                gem_type=GemType(int(gems[i])),
                                from_pos=Position(seg_start + int(orig_offset), col),
                                to_pos=Position(seg_start + int(new_offset), col),
                                distance=int(new_offset - orig_offset),
                            )
                        )

                zeros = np.zeros(empty_count, dtype=np.int8)
                new_grid[seg_start : seg_end + 1, col] = np.concatenate([zeros, gems])
                new_func[seg_start : seg_end + 1, col] = np.concatenate(
                    [zeros, gem_funcs]
                )

        return BoardState(grid=new_grid, func_grid=new_func), drops

    def fill_empty(
        self, board: BoardState, seed: int
    ) -> tuple[BoardState, list[GemSpawn]]:
        """Fill empty cells with new random standard gems.

        Iterates column-major (col then row) so that deterministic seed
        ordering is consistent across platforms.

        Args:
            board: Board with empty cells (typically after gravity).
            seed: RNG seed for reproducible gem generation.

        Returns:
            Tuple of (new BoardState, list of GemSpawn records).
        """
        rng = np.random.default_rng(seed)
        new_grid = board.grid.copy()
        new_func = board.func_grid.copy()  # type: ignore[union-attr]

        # Find all empty positions.
        empty_rows, empty_cols = np.where(new_grid == 0)
        empty_count = len(empty_rows)

        if empty_count == 0:
            return BoardState(grid=new_grid, func_grid=new_func), []

        # Sort in column-major order (col first, row within col) to match
        # the original sequential iteration order for deterministic RNG.
        sort_idx = np.lexsort((empty_rows, empty_cols))
        empty_rows = empty_rows[sort_idx]
        empty_cols = empty_cols[sort_idx]

        # Batch-generate all random gem values at once.
        values = rng.integers(
            1,
            self._gem_types + 1,
            size=empty_count,
            dtype=np.int8,
        )

        # Assign all values in one vectorized operation.
        new_grid[empty_rows, empty_cols] = values
        new_func[empty_rows, empty_cols] = 0  # NEUTRAL

        # Build spawn records.
        spawns: list[GemSpawn] = [
            GemSpawn(
                gem_type=GemType(int(values[i])),
                position=Position(int(empty_rows[i]), int(empty_cols[i])),
                column=int(empty_cols[i]),
            )
            for i in range(empty_count)
        ]

        return BoardState(grid=new_grid, func_grid=new_func), spawns

    def apply_gravity_inplace(
        self,
        board: BoardState,
    ) -> list[GemDrop]:
        """Drop gems down to fill empty spaces, mutating *board* in place.

        Obstacle cells (grid == OBSTACLE_COLOR) are immovable walls that
        partition columns into independently-compacting segments.

        Returns list of GemDrop records. Modifies board.grid and
        board.func_grid directly.
        """
        grid = board.grid
        func = board.func_grid  # type: ignore[union-attr]
        drops: list[GemDrop] = []

        for col in range(board.width):
            column = grid[:, col].copy()
            func_column = func[:, col].copy()
            obstacle_rows = set(int(r) for r in np.where(column == OBSTACLE_COLOR)[0])

            if not obstacle_rows:
                # No obstacles — original fast path.
                non_empty_mask = column != 0
                non_empty_gems = column[non_empty_mask]
                non_empty_funcs = func_column[non_empty_mask]
                empty_count = board.height - len(non_empty_gems)

                if empty_count == 0:
                    continue

                original_rows = np.where(non_empty_mask)[0]
                for i, orig_row in enumerate(original_rows):
                    new_row = empty_count + i
                    if orig_row != new_row:
                        drops.append(
                            GemDrop(
                                gem_type=GemType(int(non_empty_gems[i])),
                                from_pos=Position(int(orig_row), col),
                                to_pos=Position(int(new_row), col),
                                distance=int(new_row - orig_row),
                            )
                        )

                zeros = np.zeros(empty_count, dtype=np.int8)
                grid[:, col] = np.concatenate([zeros, non_empty_gems])
                func[:, col] = np.concatenate([zeros, non_empty_funcs])
                continue

            # Segment the column at obstacle positions.
            boundaries = sorted(obstacle_rows)
            segments: list[tuple[int, int]] = []
            prev = 0
            for obs_row in boundaries:
                if obs_row > prev:
                    segments.append((prev, obs_row - 1))
                prev = obs_row + 1
            if prev < board.height:
                segments.append((prev, board.height - 1))

            # Compact each segment independently.
            for seg_start, seg_end in segments:
                seg_len = seg_end - seg_start + 1
                seg_colors = column[seg_start : seg_end + 1].copy()
                seg_funcs = func_column[seg_start : seg_end + 1].copy()
                non_empty = seg_colors != 0
                gems = seg_colors[non_empty]
                gem_funcs = seg_funcs[non_empty]
                empty_count = seg_len - len(gems)

                if empty_count == 0:
                    continue

                original_offsets = np.where(non_empty)[0]
                for i, orig_offset in enumerate(original_offsets):
                    new_offset = empty_count + i
                    if orig_offset != new_offset:
                        drops.append(
                            GemDrop(
                                gem_type=GemType(int(gems[i])),
                                from_pos=Position(seg_start + int(orig_offset), col),
                                to_pos=Position(seg_start + int(new_offset), col),
                                distance=int(new_offset - orig_offset),
                            )
                        )

                zeros = np.zeros(empty_count, dtype=np.int8)
                grid[seg_start : seg_end + 1, col] = np.concatenate([zeros, gems])
                func[seg_start : seg_end + 1, col] = np.concatenate(
                    [zeros, gem_funcs]
                )

        return drops

    def fill_empty_inplace(
        self,
        board: BoardState,
        seed: int,
        spawn_weights: list[float] | None = None,
    ) -> list[GemSpawn]:
        """Fill empty cells with new random gems, mutating *board* in place.

        Args:
            board: Board state to fill (mutated in place).
            seed: RNG seed for deterministic generation.
            spawn_weights: Optional probability weights for gem colors 1..gem_types.
                When provided, biases spawned gem colors accordingly.

        Returns list of GemSpawn records. Modifies board.grid and
        board.func_grid directly.
        """
        rng = np.random.default_rng(seed)
        grid = board.grid
        func = board.func_grid  # type: ignore[union-attr]

        empty_rows, empty_cols = np.where(grid == 0)
        empty_count = len(empty_rows)

        if empty_count == 0:
            return []

        sort_idx = np.lexsort((empty_rows, empty_cols))
        empty_rows = empty_rows[sort_idx]
        empty_cols = empty_cols[sort_idx]

        if spawn_weights is not None:
            # Weighted spawn using rng.choice for determinism.
            choices = np.arange(1, self._gem_types + 1)
            values = rng.choice(
                choices,
                size=empty_count,
                p=spawn_weights,
            ).astype(np.int8)
        else:
            values = rng.integers(
                1,
                self._gem_types + 1,
                size=empty_count,
                dtype=np.int8,
            )

        grid[empty_rows, empty_cols] = values
        func[empty_rows, empty_cols] = 0

        return [
            GemSpawn(
                gem_type=GemType(int(values[i])),
                position=Position(int(empty_rows[i]), int(empty_cols[i])),
                column=int(empty_cols[i]),
            )
            for i in range(empty_count)
        ]

    @staticmethod
    def _place_special_gem_inplace(
        board: BoardState,
        matches: MatchResult,
    ) -> Position | None:
        """Place a newly-created special gem on the board in place.

        Mutates board.grid and board.func_grid directly.
        Returns the protected position, or None if no special was created.
        """
        if not matches.creates_special_gem or matches.special_gem_position is None:
            return None

        sp = matches.special_gem_position
        match_color = matches.matches[0].gem_type
        board.grid[sp.row, sp.col] = int(match_color)
        board.func_grid[sp.row, sp.col] = int(  # type: ignore[index]
            SPECIAL_TO_FUNCTION[matches.special_gem_type]  # type: ignore[index]
        )
        return sp

    # ------------------------------------------------------------------
    # process_move helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _advance_seed(seed: int) -> int:
        """Evolve the LCG seed one step (deterministic cascade RNG)."""
        return (seed * LCG_MULTIPLIER + LCG_INCREMENT) & LCG_MASK

    @staticmethod
    def _place_special_gem(
        board: BoardState,
        matches: MatchResult,
    ) -> tuple[BoardState, Position | None]:
        """Place a newly-created special gem on the board.

        If the match result requests a special gem, this sets the grid cell
        to the match colour and the func_grid cell to the special ability.

        Returns:
            ``(updated_board, protected_position)`` — position is ``None``
            when no special was created.
        """
        if not matches.creates_special_gem or matches.special_gem_position is None:
            return board, None

        sp = matches.special_gem_position
        new_grid = board.grid.copy()
        new_func = board.func_grid.copy()  # type: ignore[union-attr]
        match_color = matches.matches[0].gem_type
        new_grid[sp.row, sp.col] = int(match_color)
        new_func[sp.row, sp.col] = int(
            SPECIAL_TO_FUNCTION[matches.special_gem_type]  # type: ignore[index]
        )
        return BoardState(grid=new_grid, func_grid=new_func), sp

    def process_move(
        self,
        board: BoardState,
        move: Move,
        seed: int,
        modifiers: object | None = None,
    ) -> MoveProcessingResult:
        """Process a full player move: swap, detect, cascade loop.

        1. Execute the swap.
        2. Detect matches — if none, try swap-to-activate or revert.
        3. Cascade loop: clear -> attract -> trigger -> gravity -> fill -> detect.
        4. Return the complete cascade history.

        Seed evolves per cascade step via ``_advance_seed`` (LCG) to ensure
        deterministic behaviour for replay.

        Args:
            board: Current board state.
            move: The swap to execute.
            seed: RNG seed for deterministic cascade behaviour.
            modifiers: Optional CardModifierEngine for card effects (default None).
        """
        # Debug: log board before swap
        if self._debug:
            self._debug.log_board_state("before_swap", board.to_list())
            self._debug.log_move_attempt(
                match_id="",
                player_id="",
                from_row=move.from_pos.row,
                from_col=move.from_pos.col,
                to_row=move.to_pos.row,
                to_col=move.to_pos.col,
                board_before=board.to_list(),
            )

        # Reject moves involving obstacle cells.
        from_val = int(board.grid[move.from_pos.row, move.from_pos.col])
        to_val = int(board.grid[move.to_pos.row, move.to_pos.col])
        if from_val == OBSTACLE_COLOR or to_val == OBSTACLE_COLOR:
            if self._debug:
                self._debug.log_move_result(
                    valid=False,
                    chain_count=0,
                    total_cleared=0,
                    board_after=None,
                    error="Cannot swap obstacle cell",
                )
            return MoveProcessingResult(
                initial_board=board,
                final_board=board,
                move=move,
                was_valid_match=False,
                cascades=[],
                total_matches=0,
                total_gems_cleared=0,
                chain_count=0,
                special_gems_created=[],
            )

        swapped = self.swap_gems(board, move)
        if self._debug:
            self._debug.log_post_swap_board(swapped.to_list())

        initial_matches = self.detect_matches(swapped)

        if self._debug:
            self._debug.log_match_detection(
                matches_found=len(initial_matches.matches),
                total_gems=initial_matches.total_gems_matched,
                match_details=[
                    {
                        "gem_type": int(mg.gem_type),
                        "horizontal": mg.is_horizontal,
                        "length": mg.length,
                        "positions": [
                            (p.row, p.col)
                            for p in sorted(mg.positions, key=lambda p: (p.row, p.col))
                        ],
                    }
                    for mg in initial_matches.matches
                ],
                board=swapped.to_list(),
            )

        # ------------------------------------------------------------------
        # Move-wide inert mega set: megas formed this move don't activate.
        # ------------------------------------------------------------------
        inert_megas: set[Position] = set()

        # ------------------------------------------------------------------
        # Post-swap attraction check (before match detection).
        # ------------------------------------------------------------------
        post_swap_attraction_step: CascadeStep | None = None
        swap_attraction_pairs = self._check_special_attractions(swapped)
        if swap_attraction_pairs:
            post_swap_attractions = self._process_attractions_inplace(
                swapped,
                swap_attraction_pairs,
            )
            for att in post_swap_attractions:
                inert_megas.add(att.center_pos)
            post_swap_attraction_step = CascadeStep(
                step_number=0,
                matches=MatchResult(
                    matches=(),
                    total_gems_matched=0,
                    creates_special_gem=False,
                ),
                board_after_fill=swapped,
                special_attractions=post_swap_attractions,
            )

        # ------------------------------------------------------------------
        # Swap-to-activate: no normal matches but one gem is a special.
        # ------------------------------------------------------------------
        swap_activation_step: CascadeStep | None = None

        if not initial_matches.matches:
            # Post-swap attraction already formed a mega — move is valid
            # even without a color match. Fall through to cascade loop.
            if post_swap_attraction_step is not None:
                self._logger.debug(
                    "board.swap_to_attract",
                    attraction_count=len(swap_attraction_pairs),
                )
            else:
                # Read func values from the pre-attraction board would be ideal,
                # but attractions already mutated func_grid. Use the swapped board
                # directly — func values are post-attraction (specials zeroed out,
                # center has mega). For swap-to-activate we need the original funcs.
                from_func = int(swapped.func_grid[move.from_pos.row, move.from_pos.col])  # type: ignore[index]
                to_func = int(swapped.func_grid[move.to_pos.row, move.to_pos.col])  # type: ignore[index]

                # Both specials → direct fusion (swap activation handles this).
                if from_func != 0 and to_func != 0:
                    swap_activation_step = self._execute_swap_activation(
                        swapped,
                        move,
                        from_func,
                        to_func,
                        seed,
                        inert_megas=inert_megas,
                        modifiers=modifiers,
                    )
                elif from_func != 0 or to_func != 0:
                    # One gem is special but no attraction formed — reject.
                    if self._debug:
                        self._debug.log_move_result(
                            valid=False,
                            chain_count=0,
                            total_cleared=0,
                            board_after=None,
                            error="No matches or fusion after swap",
                        )
                    return MoveProcessingResult(
                        initial_board=board,
                        final_board=board,
                        move=move,
                        was_valid_match=False,
                        cascades=[],
                        total_matches=0,
                        total_gems_cleared=0,
                        chain_count=0,
                        special_gems_created=[],
                    )
                else:
                    # Neither gem is special — invalid move.
                    if self._debug:
                        self._debug.log_move_result(
                            valid=False,
                            chain_count=0,
                            total_cleared=0,
                            board_after=None,
                            error="No matches after swap",
                        )
                    return MoveProcessingResult(
                        initial_board=board,
                        final_board=board,
                        move=move,
                        was_valid_match=False,
                        cascades=[],
                        total_matches=0,
                        total_gems_cleared=0,
                        chain_count=0,
                        special_gems_created=[],
                    )

        # ------------------------------------------------------------------
        # Cascade loop setup.
        # ------------------------------------------------------------------
        cascades: list[CascadeStep] = []
        if post_swap_attraction_step is not None:
            cascades.append(post_swap_attraction_step)
        if swap_activation_step is not None:
            cascades.append(swap_activation_step)
            # The swap activation step's board_after_fill is already a
            # mutable working copy — use it directly for the cascade loop.
            current_board = swap_activation_step.board_after_fill
            cascade_seed = self._advance_seed(self._advance_seed(seed))
            total_cleared = len(
                swap_activation_step.special_activations[0].affected_positions
            )
        else:
            # Copy the swapped board once — all cascade steps mutate this copy.
            current_board = swapped.copy()
            cascade_seed = seed
            total_cleared = 0
        special_gems: list[tuple[Position, GemType]] = []
        all_applied_modifiers: list = []
        all_obstacle_clearings: list[Position] = []
        all_obstacle_transmutations: list[tuple[Position, int, int]] = []

        # ------------------------------------------------------------------
        # Cascade loop (in-place mutation).
        # ------------------------------------------------------------------
        for chain in range(1, MAX_CASCADE_STEPS + 1):
            matches = self.detect_matches(
                current_board,
                modifiers=modifiers,
                cascade_seed=cascade_seed,
            )

            if not matches.matches:
                step = self._try_attraction_only_step_inplace(
                    current_board,
                    chain,
                    inert_megas=inert_megas,
                )
                if step is None:
                    break  # Cascade truly done.
                cascades.append(step)
                # current_board was mutated in place, no reassignment needed.
                continue

            step, step_cleared, new_specials, cascade_seed, step_mods = (
                self._run_cascade_step_inplace(
                    current_board,
                    matches,
                    chain,
                    cascade_seed,
                    modifiers=modifiers,
                    inert_megas=inert_megas,
                )
            )
            cascades.append(step)
            total_cleared += step_cleared
            special_gems.extend(new_specials)
            all_applied_modifiers.extend(step_mods)
            all_obstacle_clearings.extend(step.obstacle_clearings)
            all_obstacle_transmutations.extend(step.obstacle_transmutations)
            # current_board was mutated in place, no reassignment needed.

            if chain == MAX_CASCADE_STEPS:
                self._logger.warn(
                    "board.max_cascade_reached",
                    steps=MAX_CASCADE_STEPS,
                )

        # ------------------------------------------------------------------
        # Result.
        # ------------------------------------------------------------------
        self._logger.debug(
            "board.move_processed",
            was_valid=True,
            chain_count=len(cascades),
            total_cleared=total_cleared,
        )
        if self._debug:
            self._debug.log_move_result(
                valid=True,
                chain_count=len(cascades),
                total_cleared=total_cleared,
                board_after=current_board.to_list(),
            )

        return MoveProcessingResult(
            initial_board=board,
            final_board=current_board,
            move=move,
            was_valid_match=True,
            cascades=cascades,
            total_matches=sum(len(step.matches.matches) for step in cascades),
            total_gems_cleared=total_cleared,
            chain_count=len(cascades),
            special_gems_created=special_gems,
            obstacle_clearings=all_obstacle_clearings,
            obstacle_transmutations=all_obstacle_transmutations,
            applied_modifiers=all_applied_modifiers,
        )

    def process_mega_activation(
        self,
        board: BoardState,
        mega_value: int,
        seed: int,
        modifiers: object | None = None,
    ) -> MoveProcessingResult:
        """Place a mega gem at a random position, fire it, and run cascades.

        Used for tap-to-activate banked mega gems. Places the mega at a random
        non-special cell, fires its effect, then runs the standard cascade loop.

        Args:
            board: Current board state.
            mega_value: Mega gem value to place (14, 24, 34, or 44).
            seed: RNG seed for determinism.
            modifiers: Optional CardModifierEngine.

        Returns:
            MoveProcessingResult with cascades, final board, etc.
        """
        from src.core.types.game import FUNCTION_TO_SPECIAL, decode_mega_gem

        # 1. Copy the board once — all work mutates this copy.
        work = board.copy()

        # 2. Pick a random non-special, non-empty cell via LCG.
        grid_list = work.grid.tolist()
        func_list = work.func_grid.tolist()  # type: ignore[union-attr]
        candidates = [
            (r, c)
            for r in range(work.height)
            for c in range(work.width)
            if func_list[r][c] == 0 and 1 <= grid_list[r][c] <= 6
        ]
        if not candidates:
            # No valid position — return empty result.
            dummy_move = Move(
                from_pos=Position(0, 0),
                to_pos=Position(0, 1),
                timestamp_ms=0,
            )
            return MoveProcessingResult(
                initial_board=board,
                final_board=work,
                move=dummy_move,
                was_valid_match=True,
                cascades=[],
                total_matches=0,
                total_gems_cleared=0,
                chain_count=0,
                special_gems_created=[],
            )

        pick_seed = (seed * LCG_MULTIPLIER + LCG_INCREMENT) & LCG_MASK
        target = candidates[pick_seed % len(candidates)]

        # 3. Place the mega gem on the board.
        work.func_grid[target[0], target[1]] = mega_value  # type: ignore[index]

        # 4. Get trigger color from the cell's existing color.
        trigger_color = GemType(int(work.grid[target[0], target[1]]))
        pos = Position(row=target[0], col=target[1])

        # 5. Create activation by computing the mega effect.
        effect = self._calculate_mega_gem_effect_positions(
            work,
            pos,
            mega_value,
            trigger_color,
        )
        dominant = max(decode_mega_gem(mega_value), key=lambda f: int(f))
        sp_type = FUNCTION_TO_SPECIAL[dominant]
        activation = SpecialActivation(
            pos,
            sp_type,
            frozenset(effect),
            mega_func_value=mega_value,
        )

        # 6. Clear affected positions via drain queue, gravity, attraction, fill.
        inert_megas: set[Position] = set()
        all_cleared, chain_activations, init_obs_clearings, init_obs_transmutations = (
            self._drain_clear_queue(
                work,
                effect,
                inert_megas,
                trigger_color,
                modifiers=modifiers,
                initial_blast_func=mega_value,
            )
        )
        all_activations = [activation] + chain_activations

        drops = self.apply_gravity_inplace(work)

        # Rebuild inert mega positions after gravity.
        self._rebuild_inert_megas(work, inert_megas)

        # Post-gravity attraction check.
        post_grav_pairs = self._check_special_attractions(work)
        grav_attractions: list = []
        if post_grav_pairs:
            grav_attractions = self._process_attractions_inplace(work, post_grav_pairs)
            for att in grav_attractions:
                inert_megas.add(att.center_pos)

        fill_seed = self._advance_seed(seed)
        spawns = self.fill_empty_inplace(work, fill_seed)

        initial_step = CascadeStep(
            step_number=0,
            matches=MatchResult(
                matches=(),
                total_gems_matched=0,
                creates_special_gem=False,
            ),
            gems_dropped=drops,
            gems_spawned=spawns,
            board_after_fill=work,
            special_activations=all_activations,
            special_attractions=grav_attractions,
        )

        # 7. Run standard cascade loop until no more matches.
        cascades: list[CascadeStep] = [initial_step]
        cascade_seed = self._advance_seed(self._advance_seed(seed))
        total_cleared = len(effect)
        special_gems: list[tuple[Position, GemType]] = []
        all_applied_modifiers: list = []
        all_obstacle_clearings: list[Position] = list(init_obs_clearings)
        all_obstacle_transmutations: list[tuple[Position, int, int]] = list(init_obs_transmutations)

        for chain in range(1, MAX_CASCADE_STEPS + 1):
            matches = self.detect_matches(
                work,
                modifiers=modifiers,
                cascade_seed=cascade_seed,
            )

            if not matches.matches:
                step = self._try_attraction_only_step_inplace(
                    work,
                    chain,
                    inert_megas=inert_megas,
                )
                if step is None:
                    break
                cascades.append(step)
                continue

            step, step_cleared, new_specials, cascade_seed, step_mods = (
                self._run_cascade_step_inplace(
                    work,
                    matches,
                    chain,
                    cascade_seed,
                    modifiers=modifiers,
                    inert_megas=inert_megas,
                )
            )
            cascades.append(step)
            total_cleared += step_cleared
            special_gems.extend(new_specials)
            all_applied_modifiers.extend(step_mods)
            all_obstacle_clearings.extend(step.obstacle_clearings)
            all_obstacle_transmutations.extend(step.obstacle_transmutations)

            if chain == MAX_CASCADE_STEPS:
                self._logger.warn(
                    "board.max_cascade_reached",
                    steps=MAX_CASCADE_STEPS,
                )

        # Build a dummy Move for the result (mega activation has no swap).
        # Move.__post_init__ requires adjacent positions, so offset col by 1.
        adj_col = target[1] + 1 if target[1] < work.width - 1 else target[1] - 1
        dummy_move = Move(
            from_pos=Position(target[0], target[1]),
            to_pos=Position(target[0], adj_col),
            timestamp_ms=0,
        )

        return MoveProcessingResult(
            initial_board=board,
            final_board=work,
            move=dummy_move,
            was_valid_match=True,
            cascades=cascades,
            total_matches=sum(len(step.matches.matches) for step in cascades),
            total_gems_cleared=total_cleared,
            chain_count=len(cascades),
            special_gems_created=special_gems,
            obstacle_clearings=all_obstacle_clearings,
            obstacle_transmutations=all_obstacle_transmutations,
            applied_modifiers=all_applied_modifiers,
        )

    def shuffle_board(self, board: BoardState, seed: int) -> BoardState:
        """Shuffle both grid and func_grid arrays preserving gem counts and specials.

        Uses Fisher-Yates shuffle with seeded RNG for determinism.
        Ensures no pre-existing matches after shuffle (re-shuffles if needed,
        max 10 attempts).

        Args:
            board: The board state to shuffle.
            seed: RNG seed for deterministic shuffling.

        Returns:
            A new BoardState with shuffled gem positions.
        """
        import copy

        rng = np.random.default_rng(seed)

        for _attempt in range(10):
            shuffled = copy.deepcopy(board)
            h, w = shuffled.height, shuffled.width

            # Flatten, shuffle, reshape — excluding obstacles.
            flat_grid = shuffled.grid.flatten()
            flat_func = shuffled.func_grid.flatten()

            # Identify non-obstacle positions.
            obstacle_mask = flat_grid == OBSTACLE_COLOR
            non_obs_indices = np.where(~obstacle_mask)[0]

            # Shuffle only non-obstacle values.
            non_obs_grid = flat_grid[non_obs_indices].copy()
            non_obs_func = flat_func[non_obs_indices].copy()
            perm = rng.permutation(len(non_obs_indices))
            flat_grid[non_obs_indices] = non_obs_grid[perm]
            flat_func[non_obs_indices] = non_obs_func[perm]

            shuffled.grid[:] = flat_grid.reshape(h, w)
            shuffled.func_grid[:] = flat_func.reshape(h, w)

            # Check for pre-existing matches.
            matches = self.detect_matches(shuffled, expand=False)
            if not matches.matches:
                return shuffled

        # After 10 attempts, return best effort.
        return shuffled

    def validate_board(self, board: BoardState) -> bool:
        """Check whether a board has valid dimensions and gem values.

        Compares the board's dimensions against the configured width/height
        and ensures every cell contains a recognised ``GemType`` value.

        Args:
            board: The board to validate.

        Returns:
            ``True`` if valid, ``False`` otherwise.
        """
        if board.height != self._board_height or board.width != self._board_width:
            self._logger.warn(
                "board.validation_failed",
                reason="dimensions_mismatch",
                expected_width=self._board_width,
                expected_height=self._board_height,
                actual_width=board.width,
                actual_height=board.height,
            )
            return False

        valid_values = {int(gt) for gt in GemType}
        for row in range(board.height):
            for col in range(board.width):
                val = int(board.grid[row, col])
                if val not in valid_values:
                    self._logger.warn(
                        "board.validation_failed",
                        reason="invalid_gem_value",
                        position=f"({row},{col})",
                        value=val,
                    )
                    return False

        return True

    def has_valid_moves(self, board: BoardState) -> bool:
        """Check whether at least one adjacent swap produces a match.

        Uses local pattern checks instead of brute-force swap + detect.
        For each possible swap, checks 8 patterns (4 per swapped position)
        to determine if a match-3 would be created.

        Args:
            board: Board to check for deadlock.

        Returns:
            ``True`` if at least one valid move exists, ``False`` if deadlocked.
        """
        grid = board.grid.tolist()
        func = board.func_grid.tolist()  # type: ignore[union-attr]
        h, w = board.height, board.width

        for r in range(h):
            for c in range(w):
                # Any swap involving a special gem is valid (swap-to-activate).
                if func[r][c] != 0:
                    return True

                a = grid[r][c]
                if a == 0:
                    continue

                # --- Horizontal swap: (r, c) <-> (r, c+1) ---
                if c + 1 < w:
                    if func[r][c + 1] != 0:
                        return True
                    b = grid[r][c + 1]
                    if a != b and b != 0:
                        # Check if B at (r, c) creates a match.
                        # Horizontal left: grid[r][c-1] == b and grid[r][c-2] == b
                        if c >= 2 and grid[r][c - 1] == b and grid[r][c - 2] == b:
                            return True
                        # Vertical up: grid[r-1][c] == b and grid[r-2][c] == b
                        if r >= 2 and grid[r - 1][c] == b and grid[r - 2][c] == b:
                            return True
                        # Vertical down: grid[r+1][c] == b and grid[r+2][c] == b
                        if r + 2 < h and grid[r + 1][c] == b and grid[r + 2][c] == b:
                            return True
                        # Vertical sandwich: grid[r-1][c] == b and grid[r+1][c] == b
                        if (
                            r >= 1
                            and r + 1 < h
                            and grid[r - 1][c] == b
                            and grid[r + 1][c] == b
                        ):
                            return True
                        # Check if A at (r, c+1) creates a match.
                        # Horizontal right: grid[r][c+2] == a and grid[r][c+3] == a
                        if c + 3 < w and grid[r][c + 2] == a and grid[r][c + 3] == a:
                            return True
                        # Vertical up: grid[r-1][c+1] == a and grid[r-2][c+1] == a
                        if (
                            r >= 2
                            and grid[r - 1][c + 1] == a
                            and grid[r - 2][c + 1] == a
                        ):
                            return True
                        # Vertical down: grid[r+1][c+1] == a and grid[r+2][c+1] == a
                        if (
                            r + 2 < h
                            and grid[r + 1][c + 1] == a
                            and grid[r + 2][c + 1] == a
                        ):
                            return True
                        # Vertical sandwich: grid[r-1][c+1] == a and grid[r+1][c+1] == a
                        if (
                            r >= 1
                            and r + 1 < h
                            and grid[r - 1][c + 1] == a
                            and grid[r + 1][c + 1] == a
                        ):
                            return True

                # --- Vertical swap: (r, c) <-> (r+1, c) ---
                if r + 1 < h:
                    if func[r + 1][c] != 0:
                        return True
                    b = grid[r + 1][c]
                    if a != b and b != 0:
                        # Check if B at (r, c) creates a match.
                        # Vertical up: grid[r-1][c] == b and grid[r-2][c] == b
                        if r >= 2 and grid[r - 1][c] == b and grid[r - 2][c] == b:
                            return True
                        # Horizontal left: grid[r][c-1] == b and grid[r][c-2] == b
                        if c >= 2 and grid[r][c - 1] == b and grid[r][c - 2] == b:
                            return True
                        # Horizontal right: grid[r][c+1] == b and grid[r][c+2] == b
                        if c + 2 < w and grid[r][c + 1] == b and grid[r][c + 2] == b:
                            return True
                        # Horizontal sandwich: grid[r][c-1] == b and grid[r][c+1] == b
                        if (
                            c >= 1
                            and c + 1 < w
                            and grid[r][c - 1] == b
                            and grid[r][c + 1] == b
                        ):
                            return True
                        # Check if A at (r+1, c) creates a match.
                        # Vertical down: grid[r+2][c] == a and grid[r+3][c] == a
                        if r + 3 < h and grid[r + 2][c] == a and grid[r + 3][c] == a:
                            return True
                        # Horizontal left: grid[r+1][c-1] == a and grid[r+1][c-2] == a
                        if (
                            c >= 2
                            and grid[r + 1][c - 1] == a
                            and grid[r + 1][c - 2] == a
                        ):
                            return True
                        # Horizontal right: grid[r+1][c+1] == a and grid[r+1][c+2] == a
                        if (
                            c + 2 < w
                            and grid[r + 1][c + 1] == a
                            and grid[r + 1][c + 2] == a
                        ):
                            return True
                        # Horizontal sandwich: grid[r+1][c-1] == a and grid[r+1][c+1] == a
                        if (
                            c >= 1
                            and c + 1 < w
                            and grid[r + 1][c - 1] == a
                            and grid[r + 1][c + 1] == a
                        ):
                            return True

        self._logger.warn(
            "board.deadlock_detected",
            board_hash=hash(board.grid.tobytes()),
        )
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_position(self, pos: Position, board: BoardState) -> None:
        """Raise VALIDATION_OUT_OF_BOUNDS if *pos* is outside the grid."""
        if (
            pos.row < 0
            or pos.row >= board.height
            or pos.col < 0
            or pos.col >= board.width
        ):
            raise self._errors.validation(
                "Position out of bounds",
                code="VALIDATION_OUT_OF_BOUNDS",
                position=str(pos),
                board_width=board.width,
                board_height=board.height,
            )

    def _swap_positions(
        self, board: BoardState, a: Position, b: Position
    ) -> BoardState:
        """Swap two positions on a copy of the board (no validation)."""
        new_board = board.copy()
        # Swap colors.
        new_board.grid[a.row, a.col], new_board.grid[b.row, b.col] = (
            new_board.grid[b.row, b.col],
            new_board.grid[a.row, a.col],
        )
        # Swap functions.
        new_board.func_grid[a.row, a.col], new_board.func_grid[b.row, b.col] = (  # type: ignore[index]
            new_board.func_grid[b.row, b.col],  # type: ignore[index]
            new_board.func_grid[a.row, a.col],  # type: ignore[index]
        )
        return new_board
