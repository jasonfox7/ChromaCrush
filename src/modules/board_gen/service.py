"""Board generation service — deterministic, seeded board creation.

Generates fair, playable game boards with configurable cascade potential,
near-miss psychology tuning, and optional starting special gems.
All methods are synchronous. Board state is immutable — every operation
returns a new BoardState without modifying the input.

Dependencies are injected via ``__init__``. No direct imports from
``src.core`` concrete implementations.

Cascade analysis is delegated to ``cascade_analyzer`` and board
transformation algorithms to ``tuning_engine``.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np

from src.core.types.board import BoardState
from src.core.types.game import GemType, Position
from src.modules.board_gen.cascade_analyzer import (
    calculate_cascade_potential as _analyze_cascade_potential,
)
from src.modules.board_gen.tuning_engine import (
    apply_cascade_tuning,
    apply_near_miss_tuning,
)
from src.modules.board._constants import OBSTACLE_COLOR
from src.modules.board_gen.types import (
    BoardGenOptions,
    GeneratedBoard,
    GenerationMetadata,
    MatchType,
    StartingSpecial,
)

if TYPE_CHECKING:
    from numpy.random import Generator

    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.board_gen.protocols import BoardServiceProtocol
    from src.modules.special_gems.protocols import SpecialGemsServiceProtocol

# Special gem type values for fast checks.
_SPECIAL_GEM_VALUES = frozenset(
    {
        int(GemType.LINE_BLAST_H),
        int(GemType.LINE_BLAST_V),
        int(GemType.RADIAL_BOMB),
        int(GemType.CHROMATIC_ORB),
    }
)

_SPECIAL_PLACEMENT_MAX_TRIES = 200


class BoardGenService:
    """Procedural, deterministic board generation.

    All methods are regular ``def`` (fully synchronous). The service
    operates on in-memory NumPy arrays and never performs I/O.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        board_service: BoardServiceProtocol,
        special_gems_service: SpecialGemsServiceProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._board_service = board_service
        self._special_gems_service = special_gems_service

        # Cache configuration.
        self._board_width: int = config.get("game.board_width", 8)
        self._board_height: int = config.get("game.board_height", 8)
        self._gem_types: int = config.get("game.gem_types", 6)
        self._default_cascade: float = config.get(
            "board_gen.default_cascade_potential", 0.5
        )
        self._default_near_miss: float = config.get(
            "board_gen.default_near_miss_factor", 0.3
        )
        self._max_attempts: int = config.get("board_gen.max_generation_attempts", 100)
        self._max_starting_specials: int = config.get(
            "board_gen.max_starting_specials", 3
        )
        self._enable_near_miss: bool = config.get("board_gen.enable_near_miss", True)
        self._competitive_cascade: float = config.get(
            "board_gen.competitive_cascade_potential", 0.4
        )
        self._casual_cascade: float = config.get(
            "board_gen.casual_cascade_potential", 0.6
        )
        self._tutorial_cascade: float = config.get(
            "board_gen.tutorial_cascade_potential", 0.7
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_board(
        self, seed: int, options: BoardGenOptions | None = None
    ) -> GeneratedBoard:
        """Generate a new board with no initial matches.

        Args:
            seed: RNG seed for deterministic generation.
            options: Optional generation parameters (``None`` uses defaults).

        Returns:
            A ``GeneratedBoard`` with board state, seed, and metadata.

        Raises:
            AppError: VALIDATION_INVALID_INPUT for bad parameters.
            AppError: INTERNAL_UNEXPECTED if max attempts exceeded.
        """
        start = time.perf_counter()

        # Resolve options with config defaults.
        width, height, cascade_target, near_miss_factor, specials, gem_weights = (
            self._resolve_options(options)
        )

        # Validate resolved options.
        self._validate_options(
            width, height, cascade_target, near_miss_factor, specials, gem_weights
        )

        self._logger.debug(
            "board_gen.generation_started",
            seed=seed,
            width=width,
            height=height,
            cascade_target=cascade_target,
            near_miss_factor=near_miss_factor,
        )

        # Generation loop with retry on invalid boards.
        current_seed = seed
        for attempt in range(1, self._max_attempts + 1):
            rng = np.random.default_rng(current_seed)

            # 1. Generate base board (no initial matches).
            board = self._generate_base_board(width, height, rng, gem_weights)

            # 2. Apply cascade potential tuning.
            board = self._apply_cascade_tuning(board, cascade_target, rng)

            # 3. Apply near-miss tuning.
            near_miss_count = 0
            if self._enable_near_miss and near_miss_factor > 0:
                board, near_miss_count = self._apply_near_miss_tuning(
                    board, near_miss_factor, rng
                )

            # 4. Place starting specials.
            specials_placed: list[tuple[Position, GemType]] = []
            if specials:
                board, specials_placed = self._place_starting_specials(
                    board, specials, rng
                )

            # 5. Validate: no matches and has valid moves.
            match_result = self._board_service.detect_matches(board)
            has_moves = self._board_service.has_valid_moves(board)

            if not match_result.matches and has_moves:
                elapsed_ms = (time.perf_counter() - start) * 1000
                actual_cascade = self.calculate_cascade_potential(board)
                valid_moves = self._count_valid_moves(board)

                self._logger.debug(
                    "board_gen.generation_complete",
                    seed=seed,
                    attempts=attempt,
                    time_ms=round(elapsed_ms, 2),
                    cascade_potential=round(actual_cascade, 3),
                    valid_moves=valid_moves,
                )

                return GeneratedBoard(
                    board_state=board,
                    seed=seed,
                    generation_metadata=GenerationMetadata(
                        width=width,
                        height=height,
                        cascade_potential_target=cascade_target,
                        cascade_potential_actual=round(actual_cascade, 4),
                        near_miss_factor=near_miss_factor,
                        near_miss_count=near_miss_count,
                        starting_specials_placed=specials_placed,
                        valid_moves_count=valid_moves,
                        generation_attempts=attempt,
                        generation_time_ms=round(elapsed_ms, 3),
                    ),
                )

            # Retry with evolved seed.
            self._logger.debug(
                "board_gen.generation_retry",
                seed=current_seed,
                attempt=attempt,
                reason="matches_or_deadlock",
            )
            current_seed = self._evolve_seed(current_seed)

        # All attempts exhausted.
        self._logger.error(
            "board_gen.generation_failed",
            seed=seed,
            attempts=self._max_attempts,
        )
        raise self._errors.internal(
            f"Failed to generate valid board after {self._max_attempts} attempts",
            code="INTERNAL_UNEXPECTED",
            seed=seed,
            attempts=self._max_attempts,
        )

    def generate_board_for_match(
        self, seed: int, match_type: MatchType = MatchType.STANDARD
    ) -> GeneratedBoard:
        """Generate a board using match-type presets.

        Args:
            seed: RNG seed for deterministic generation.
            match_type: Preset type controlling generation parameters.

        Returns:
            A ``GeneratedBoard`` configured for the match type.
        """
        options = self._get_match_type_preset(match_type)
        return self.generate_board(seed, options)

    def validate_seed(self, seed: int) -> bool:
        """Check whether a seed produces a valid, playable board.

        Args:
            seed: Seed value to test.

        Returns:
            ``True`` if the seed produces a valid board, ``False`` otherwise.
        """
        try:
            self.generate_board(seed)
            return True
        except Exception:
            return False

    def regenerate_from_deadlock(self, board: BoardState, seed: int) -> GeneratedBoard:
        """Reshuffle a deadlocked board while preserving special gems.

        Args:
            board: Current deadlocked board.
            seed: RNG seed for deterministic shuffle.

        Returns:
            A ``GeneratedBoard`` with reshuffled standard gems.

        Raises:
            AppError: INTERNAL_UNEXPECTED if reshuffle fails.
        """
        start = time.perf_counter()

        # Separate special gems from standard gems.
        specials: list[tuple[Position, GemType]] = []
        standard_positions: list[Position] = []
        standard_gems: list[int] = []

        for row in range(board.height):
            for col in range(board.width):
                pos = Position(row, col)
                gem_val = int(board.grid[row, col])
                if gem_val in _SPECIAL_GEM_VALUES or gem_val == OBSTACLE_COLOR:
                    specials.append((pos, GemType(gem_val)))
                else:
                    standard_positions.append(pos)
                    standard_gems.append(gem_val)

        self._logger.info(
            "board_gen.deadlock_reshuffle",
            seed=seed,
            specials_preserved=len(specials),
        )

        current_seed = seed
        for attempt in range(1, self._max_attempts + 1):
            rng = np.random.default_rng(current_seed)

            # Shuffle standard gems.
            shuffled = standard_gems.copy()
            rng.shuffle(shuffled)

            # Build new grid.
            new_grid = board.grid.copy()
            for pos, gem_val in zip(standard_positions, shuffled):
                new_grid[pos.row, pos.col] = gem_val

            new_board = BoardState(grid=new_grid)

            # Validate.
            match_result = self._board_service.detect_matches(new_board)
            has_moves = self._board_service.has_valid_moves(new_board)

            if not match_result.matches and has_moves:
                elapsed_ms = (time.perf_counter() - start) * 1000
                actual_cascade = self.calculate_cascade_potential(new_board)
                valid_moves = self._count_valid_moves(new_board)

                return GeneratedBoard(
                    board_state=new_board,
                    seed=seed,
                    generation_metadata=GenerationMetadata(
                        width=board.width,
                        height=board.height,
                        cascade_potential_target=0.0,
                        cascade_potential_actual=round(actual_cascade, 4),
                        near_miss_factor=0.0,
                        near_miss_count=0,
                        starting_specials_placed=specials,
                        valid_moves_count=valid_moves,
                        generation_attempts=attempt,
                        generation_time_ms=round(elapsed_ms, 3),
                    ),
                )

            current_seed = self._evolve_seed(current_seed)

        raise self._errors.internal(
            f"Failed to reshuffle deadlocked board after {self._max_attempts} attempts",
            code="INTERNAL_UNEXPECTED",
            seed=seed,
            attempts=self._max_attempts,
        )

    def calculate_cascade_potential(self, board: BoardState) -> float:
        """Analyse a board and return a cascade potential score (0.0-1.0).

        Delegates to ``cascade_analyzer.calculate_cascade_potential``.

        Args:
            board: Board to analyse.

        Returns:
            A float between 0.0 and 1.0.
        """
        return _analyze_cascade_potential(board, self._count_valid_moves)

    # ------------------------------------------------------------------
    # Options resolution and validation
    # ------------------------------------------------------------------

    def _resolve_options(
        self, options: BoardGenOptions | None
    ) -> tuple[
        int, int, float, float, list[StartingSpecial] | None, dict[int, float] | None
    ]:
        """Merge user options with config defaults."""
        if options is None:
            return (
                self._board_width,
                self._board_height,
                self._default_cascade,
                self._default_near_miss,
                None,
                None,
            )
        return (
            options.width if options.width is not None else self._board_width,
            options.height if options.height is not None else self._board_height,
            (
                options.cascade_potential
                if options.cascade_potential is not None
                else self._default_cascade
            ),
            (
                options.near_miss_factor
                if options.near_miss_factor is not None
                else self._default_near_miss
            ),
            options.starting_specials,
            options.gem_distribution,
        )

    def _validate_options(
        self,
        width: int,
        height: int,
        cascade_potential: float,
        near_miss_factor: float,
        specials: list[StartingSpecial] | None,
        gem_weights: dict[int, float] | None,
    ) -> None:
        """Validate resolved generation options."""
        if not (0.0 <= cascade_potential <= 1.0):
            raise self._errors.validation(
                "Cascade potential must be between 0.0 and 1.0",
                code="VALIDATION_INVALID_INPUT",
                field="cascade_potential",
                value=cascade_potential,
            )

        if not (0.0 <= near_miss_factor <= 1.0):
            raise self._errors.validation(
                "Near-miss factor must be between 0.0 and 1.0",
                code="VALIDATION_INVALID_INPUT",
                field="near_miss_factor",
                value=near_miss_factor,
            )

        if width < 3 or height < 3:
            raise self._errors.validation(
                "Board dimensions must be at least 3x3",
                code="VALIDATION_INVALID_INPUT",
                field="dimensions",
                width=width,
                height=height,
            )

        if specials is not None:
            if len(specials) > self._max_starting_specials:
                raise self._errors.validation(
                    f"Too many starting specials: {len(specials)} > {self._max_starting_specials}",
                    code="VALIDATION_INVALID_INPUT",
                    field="starting_specials",
                    count=len(specials),
                    max_allowed=self._max_starting_specials,
                )

            for spec in specials:
                if not self._special_gems_service.is_special_gem(spec.gem_type):
                    raise self._errors.validation(
                        f"Starting special must be a special gem type, got {spec.gem_type}",
                        code="VALIDATION_INVALID_INPUT",
                        field="gem_type",
                        value=str(spec.gem_type),
                    )
                if spec.position is not None:
                    if not (
                        0 <= spec.position.row < height
                        and 0 <= spec.position.col < width
                    ):
                        raise self._errors.validation(
                            f"Starting special position out of bounds: {spec.position}",
                            code="VALIDATION_OUT_OF_BOUNDS",
                            position=str(spec.position),
                            board_width=width,
                            board_height=height,
                        )

            # Check no two specials placed adjacent.
            explicit_positions = [
                s.position for s in specials if s.position is not None
            ]
            for i, pos_a in enumerate(explicit_positions):
                for pos_b in explicit_positions[i + 1 :]:
                    if abs(pos_a.row - pos_b.row) + abs(pos_a.col - pos_b.col) == 1:
                        raise self._errors.validation(
                            "Starting specials cannot be adjacent to each other",
                            code="VALIDATION_INVALID_INPUT",
                            field="starting_specials",
                            position_a=str(pos_a),
                            position_b=str(pos_b),
                        )

        if gem_weights is not None:
            total = sum(gem_weights.values())
            if total <= 0:
                raise self._errors.validation(
                    "Gem distribution weights must sum to a positive value",
                    code="VALIDATION_INVALID_INPUT",
                    field="gem_distribution",
                )

    # ------------------------------------------------------------------
    # Board generation internals
    # ------------------------------------------------------------------

    def _generate_base_board(
        self,
        width: int,
        height: int,
        rng: Generator,
        gem_weights: dict[int, float] | None,
    ) -> BoardState:
        """Generate a board with no initial matches using cell-by-cell fill.

        With 6 gem types and at most 2 exclusions per cell, at least 4
        colours are always available, so the algorithm always succeeds.
        """
        grid = np.zeros((height, width), dtype=np.int8)

        # Build base gem list and weights.
        all_gems = list(range(1, self._gem_types + 1))
        if gem_weights is not None:
            base_weights = {g: gem_weights.get(g, 1.0) for g in all_gems}
        else:
            base_weights = {g: 1.0 for g in all_gems}

        for row in range(height):
            for col in range(width):
                excluded: set[int] = set()

                # Exclude gem that would create horizontal 3-in-a-row.
                if (
                    col >= 2
                    and grid[row, col - 1] == grid[row, col - 2]
                    and grid[row, col - 1] != 0
                ):
                    excluded.add(int(grid[row, col - 1]))

                # Exclude gem that would create vertical 3-in-a-row.
                if (
                    row >= 2
                    and grid[row - 1, col] == grid[row - 2, col]
                    and grid[row - 1, col] != 0
                ):
                    excluded.add(int(grid[row - 1, col]))

                # Build available gems and weights.
                available = [g for g in all_gems if g not in excluded]
                weights = np.array(
                    [base_weights[g] for g in available], dtype=np.float64
                )
                weights /= weights.sum()

                grid[row, col] = rng.choice(available, p=weights)

        return BoardState(grid=grid)

    def _apply_cascade_tuning(
        self, board: BoardState, target: float, rng: Generator
    ) -> BoardState:
        """Iteratively adjust board toward target cascade potential.

        Delegates to ``tuning_engine.apply_cascade_tuning``.
        """
        return apply_cascade_tuning(
            board,
            target,
            rng,
            gem_types=self._gem_types,
            special_gem_values=_SPECIAL_GEM_VALUES,
            calculate_cascade_potential=self.calculate_cascade_potential,
        )

    def _apply_near_miss_tuning(
        self, board: BoardState, factor: float, rng: Generator
    ) -> tuple[BoardState, int]:
        """Place near-miss patterns on the board.

        Delegates to ``tuning_engine.apply_near_miss_tuning``.
        """
        return apply_near_miss_tuning(
            board,
            factor,
            rng,
            special_gem_values=_SPECIAL_GEM_VALUES,
        )

    def _place_starting_specials(
        self,
        board: BoardState,
        specials: list[StartingSpecial],
        rng: Generator,
    ) -> tuple[BoardState, list[tuple[Position, GemType]]]:
        """Place starting special gems on the board."""
        grid = board.grid.copy()
        placed: list[tuple[Position, GemType]] = []
        occupied: set[tuple[int, int]] = set()

        for spec in specials:
            if spec.position is not None:
                pos = spec.position
            else:
                # Random placement avoiding edges for bombs, central for lines.
                pos = self._find_random_special_position(
                    board.height, board.width, spec.gem_type, occupied, rng
                )

            grid[pos.row, pos.col] = int(spec.gem_type)
            placed.append((pos, spec.gem_type))
            occupied.add((pos.row, pos.col))

            self._logger.debug(
                "board_gen.starting_special_placed",
                gem_type=str(spec.gem_type),
                position=f"({pos.row},{pos.col})",
            )

        return BoardState(grid=grid), placed

    def _find_random_special_position(
        self,
        height: int,
        width: int,
        gem_type: GemType,
        occupied: set[tuple[int, int]],
        rng: Generator,
    ) -> Position:
        """Find a random position suitable for a special gem."""
        # Bombs: at least 1 cell from edge. Lines: inner area.
        if gem_type in (GemType.LINE_BLAST_H, GemType.LINE_BLAST_V):
            min_r, max_r = 1, height - 2
            min_c, max_c = 1, width - 2
        elif gem_type == GemType.RADIAL_BOMB:
            min_r, max_r = 1, height - 2
            min_c, max_c = 1, width - 2
        else:
            min_r, max_r = 0, height - 1
            min_c, max_c = 0, width - 1

        # Clamp ranges for small boards.
        min_r = max(0, min_r)
        min_c = max(0, min_c)
        max_r = min(height - 1, max_r)
        max_c = min(width - 1, max_c)

        for _ in range(_SPECIAL_PLACEMENT_MAX_TRIES):
            row = int(rng.integers(min_r, max_r + 1))
            col = int(rng.integers(min_c, max_c + 1))
            if (row, col) not in occupied:
                # Check not adjacent to another special.
                adjacent_ok = True
                for occ_r, occ_c in occupied:
                    if abs(row - occ_r) + abs(col - occ_c) == 1:
                        adjacent_ok = False
                        break
                if adjacent_ok:
                    return Position(row, col)

        # Fallback: any unoccupied position.
        for row in range(height):
            for col in range(width):
                if (row, col) not in occupied:
                    return Position(row, col)

        return Position(0, 0)  # Should never reach here on a valid board.

    # ------------------------------------------------------------------
    # Match-type presets
    # ------------------------------------------------------------------

    def _get_match_type_preset(self, match_type: MatchType) -> BoardGenOptions:
        """Map a MatchType to generation options."""
        if match_type == MatchType.COMPETITIVE:
            return BoardGenOptions(
                cascade_potential=self._competitive_cascade,
                near_miss_factor=0.1,
            )
        elif match_type == MatchType.CASUAL:
            return BoardGenOptions(
                cascade_potential=self._casual_cascade,
                near_miss_factor=0.4,
                starting_specials=[StartingSpecial(GemType.RADIAL_BOMB)],
            )
        elif match_type == MatchType.TUTORIAL:
            return BoardGenOptions(
                cascade_potential=self._tutorial_cascade,
                near_miss_factor=0.0,
                gem_distribution={1: 0.2, 2: 0.2, 3: 0.2, 4: 0.2, 5: 0.1, 6: 0.1},
            )
        else:
            # STANDARD
            return BoardGenOptions(
                cascade_potential=self._default_cascade,
                near_miss_factor=self._default_near_miss,
            )

    def _count_valid_moves(self, board: BoardState) -> int:
        """Count the number of valid moves on the board."""
        count = 0
        grid = board.grid

        for row in range(board.height):
            for col in range(board.width):
                # Check right swap.
                if col < board.width - 1:
                    # Swap.
                    grid[row, col], grid[row, col + 1] = (
                        grid[row, col + 1],
                        grid[row, col],
                    )
                    test_board = BoardState(grid=grid.copy())
                    if self._board_service.detect_matches(test_board).matches:
                        count += 1
                    # Swap back.
                    grid[row, col], grid[row, col + 1] = (
                        grid[row, col + 1],
                        grid[row, col],
                    )

                # Check down swap.
                if row < board.height - 1:
                    grid[row, col], grid[row + 1, col] = (
                        grid[row + 1, col],
                        grid[row, col],
                    )
                    test_board = BoardState(grid=grid.copy())
                    if self._board_service.detect_matches(test_board).matches:
                        count += 1
                    grid[row, col], grid[row + 1, col] = (
                        grid[row + 1, col],
                        grid[row, col],
                    )

        return count

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _evolve_seed(seed: int) -> int:
        """Linear Congruential Generator for deterministic seed evolution."""
        return (seed * 1103515245 + 12345) & 0x7FFFFFFF
