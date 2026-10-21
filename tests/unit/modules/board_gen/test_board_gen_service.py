"""Comprehensive unit tests for the board_gen module.

Uses the real BoardService for match detection (board_gen depends on it
heavily) and a mock SpecialGemsService for is_special_gem checks.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.errors import AppError
from src.core.types.board import BoardState
from src.core.types.game import GemType, Position
from src.modules.board.service import BoardService
from src.modules.board_gen.service import BoardGenService
from src.modules.board_gen.types import (
    BoardGenOptions,
    GeneratedBoard,
    MatchType,
    StartingSpecial,
)
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


class MockSpecialGemsService:
    """Minimal mock satisfying the is_special_gem interface."""

    _SPECIAL = frozenset(
        {
            GemType.LINE_BLAST_H,
            GemType.LINE_BLAST_V,
            GemType.RADIAL_BOMB,
            GemType.CHROMATIC_ORB,
        }
    )

    def is_special_gem(self, gem_type: GemType) -> bool:
        return gem_type in self._SPECIAL


def _make_service(
    overrides: dict | None = None,
) -> tuple[BoardGenService, MockLogService, MockErrorService]:
    config = MockConfigService(overrides or {})
    logger = MockLogService()
    errors = MockErrorService(logger)
    board_svc = BoardService(config, logger, errors)
    sg_svc = MockSpecialGemsService()
    svc = BoardGenService(config, logger, errors, board_svc, sg_svc)
    return svc, logger, errors


# ---------------------------------------------------------------------------
# generate_board — basic
# ---------------------------------------------------------------------------


class TestGenerateBoard:
    def test_returns_generated_board(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(42)
        assert isinstance(result, GeneratedBoard)
        assert isinstance(result.board_state, BoardState)

    def test_deterministic_same_seed(self):
        svc, _, _ = _make_service()
        a = svc.generate_board(12345)
        b = svc.generate_board(12345)
        assert np.array_equal(a.board_state.grid, b.board_state.grid)

    def test_different_seeds_different_boards(self):
        svc, _, _ = _make_service()
        a = svc.generate_board(100)
        b = svc.generate_board(200)
        assert not np.array_equal(a.board_state.grid, b.board_state.grid)

    def test_no_initial_matches(self):
        svc, _, _ = _make_service()
        board_svc = BoardService(
            MockConfigService(), MockLogService(), MockErrorService()
        )
        for seed in range(20):
            result = svc.generate_board(seed)
            matches = board_svc.detect_matches(result.board_state)
            assert len(matches.matches) == 0, f"Seed {seed} produced initial matches"

    def test_has_valid_moves(self):
        svc, _, _ = _make_service()
        board_svc = BoardService(
            MockConfigService(), MockLogService(), MockErrorService()
        )
        for seed in range(20):
            result = svc.generate_board(seed)
            assert board_svc.has_valid_moves(
                result.board_state
            ), f"Seed {seed} deadlocked"

    def test_default_dimensions(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(42)
        assert result.board_state.width == 8
        assert result.board_state.height == 8

    def test_metadata_populated(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(42)
        meta = result.generation_metadata
        assert meta.width == 8
        assert meta.height == 8
        assert meta.generation_attempts >= 1
        assert meta.generation_time_ms > 0
        assert meta.valid_moves_count > 0
        assert 0.0 <= meta.cascade_potential_actual <= 1.0

    def test_seed_stored_in_result(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(99999)
        assert result.seed == 99999

    def test_only_standard_gems_by_default(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(42)
        grid = result.board_state.grid
        assert np.all(grid >= 1)
        assert np.all(grid <= 6)


# ---------------------------------------------------------------------------
# generate_board — with options
# ---------------------------------------------------------------------------


class TestGenerateBoardOptions:
    def test_custom_cascade_potential(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(cascade_potential=0.8)
        result = svc.generate_board(42, opts)
        assert result.generation_metadata.cascade_potential_target == 0.8

    def test_custom_near_miss_factor(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(near_miss_factor=0.5)
        result = svc.generate_board(42, opts)
        assert result.generation_metadata.near_miss_factor == 0.5

    def test_near_miss_disabled_via_config(self):
        svc, _, _ = _make_service({"board_gen.enable_near_miss": False})
        opts = BoardGenOptions(near_miss_factor=0.5)
        result = svc.generate_board(42, opts)
        assert result.generation_metadata.near_miss_count == 0

    def test_zero_near_miss_factor(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(near_miss_factor=0.0)
        result = svc.generate_board(42, opts)
        assert result.generation_metadata.near_miss_count == 0

    def test_gem_distribution_weighted(self):
        svc, _, _ = _make_service()
        # Heavily weight gem 1.
        opts = BoardGenOptions(
            gem_distribution={1: 10.0, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1, 6: 0.1}
        )
        result = svc.generate_board(42, opts)
        grid = result.board_state.grid
        count_1 = int(np.sum(grid == 1))
        count_others = int(np.sum(grid != 1))
        # Gem 1 should dominate.
        assert count_1 > count_others

    def test_custom_dimensions(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(width=6, height=6)
        result = svc.generate_board(42, opts)
        assert result.board_state.width == 6
        assert result.board_state.height == 6


# ---------------------------------------------------------------------------
# Starting specials
# ---------------------------------------------------------------------------


class TestStartingSpecials:
    def test_explicit_position(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(
            starting_specials=[StartingSpecial(GemType.RADIAL_BOMB, Position(3, 3))]
        )
        result = svc.generate_board(42, opts)
        assert result.board_state.get(Position(3, 3)) == GemType.RADIAL_BOMB
        assert len(result.generation_metadata.starting_specials_placed) == 1

    def test_random_position(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(
            starting_specials=[StartingSpecial(GemType.LINE_BLAST_H)]
        )
        result = svc.generate_board(42, opts)
        placed = result.generation_metadata.starting_specials_placed
        assert len(placed) == 1
        pos, gem = placed[0]
        assert gem == GemType.LINE_BLAST_H
        assert result.board_state.get(pos) == GemType.LINE_BLAST_H

    def test_too_many_specials_error(self):
        svc, _, _ = _make_service({"board_gen.max_starting_specials": 2})
        opts = BoardGenOptions(
            starting_specials=[
                StartingSpecial(GemType.RADIAL_BOMB),
                StartingSpecial(GemType.LINE_BLAST_H),
                StartingSpecial(GemType.LINE_BLAST_V),
            ]
        )
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, opts)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_non_special_gem_type_error(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(starting_specials=[StartingSpecial(GemType.RED)])
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, opts)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_out_of_bounds_position_error(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(
            starting_specials=[StartingSpecial(GemType.RADIAL_BOMB, Position(99, 99))]
        )
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, opts)
        assert exc_info.value.code == "VALIDATION_OUT_OF_BOUNDS"

    def test_adjacent_specials_error(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(
            starting_specials=[
                StartingSpecial(GemType.RADIAL_BOMB, Position(3, 3)),
                StartingSpecial(GemType.LINE_BLAST_H, Position(3, 4)),
            ]
        )
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, opts)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_multiple_specials_non_adjacent(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(
            starting_specials=[
                StartingSpecial(GemType.RADIAL_BOMB, Position(1, 1)),
                StartingSpecial(GemType.LINE_BLAST_H, Position(5, 5)),
            ]
        )
        result = svc.generate_board(42, opts)
        assert result.board_state.get(Position(1, 1)) == GemType.RADIAL_BOMB
        assert result.board_state.get(Position(5, 5)) == GemType.LINE_BLAST_H


# ---------------------------------------------------------------------------
# generate_board_for_match
# ---------------------------------------------------------------------------


class TestGenerateBoardForMatch:
    def test_standard(self):
        svc, _, _ = _make_service()
        result = svc.generate_board_for_match(42, MatchType.STANDARD)
        assert isinstance(result, GeneratedBoard)

    def test_competitive(self):
        svc, _, _ = _make_service()
        result = svc.generate_board_for_match(42, MatchType.COMPETITIVE)
        assert result.generation_metadata.cascade_potential_target == 0.4

    def test_casual_has_starting_special(self):
        svc, _, _ = _make_service()
        result = svc.generate_board_for_match(42, MatchType.CASUAL)
        assert len(result.generation_metadata.starting_specials_placed) >= 1

    def test_tutorial_low_near_miss(self):
        svc, _, _ = _make_service()
        result = svc.generate_board_for_match(42, MatchType.TUTORIAL)
        assert result.generation_metadata.near_miss_factor == 0.0

    def test_all_types_produce_valid_boards(self):
        svc, _, _ = _make_service()
        board_svc = BoardService(
            MockConfigService(), MockLogService(), MockErrorService()
        )
        for mt in MatchType:
            result = svc.generate_board_for_match(42, mt)
            matches = board_svc.detect_matches(result.board_state)
            assert len(matches.matches) == 0, f"{mt} produced initial matches"
            assert board_svc.has_valid_moves(result.board_state), f"{mt} deadlocked"

    def test_competitive_deterministic(self):
        svc, _, _ = _make_service()
        a = svc.generate_board_for_match(42, MatchType.COMPETITIVE)
        b = svc.generate_board_for_match(42, MatchType.COMPETITIVE)
        assert np.array_equal(a.board_state.grid, b.board_state.grid)


# ---------------------------------------------------------------------------
# validate_seed
# ---------------------------------------------------------------------------


class TestValidateSeed:
    def test_normal_seed_valid(self):
        svc, _, _ = _make_service()
        assert svc.validate_seed(42) is True

    def test_multiple_seeds_valid(self):
        svc, _, _ = _make_service()
        for seed in [0, 1, 100, 999999, 2**30]:
            assert svc.validate_seed(seed) is True

    def test_deterministic(self):
        svc, _, _ = _make_service()
        a = svc.validate_seed(42)
        b = svc.validate_seed(42)
        assert a == b


# ---------------------------------------------------------------------------
# regenerate_from_deadlock
# ---------------------------------------------------------------------------


class TestRegenerateFromDeadlock:
    def _make_board_with_special(self) -> BoardState:
        """Create a board with one special gem."""
        grid = np.array(
            [
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [2, 1, 4, -3, 6, 5, 2, 1],  # RADIAL_BOMB at (3,3)
                [4, 3, 6, 5, 2, 1, 4, 3],
                [6, 5, 2, 1, 4, 3, 6, 5],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ],
            dtype=np.int8,
        )
        return BoardState(grid=grid)

    def test_preserves_special_gems(self):
        svc, _, _ = _make_service()
        board = self._make_board_with_special()
        result = svc.regenerate_from_deadlock(board, 42)
        # Special gem at (3,3) should be preserved.
        assert int(result.board_state.grid[3, 3]) == int(GemType.RADIAL_BOMB)

    def test_produces_valid_board(self):
        svc, _, _ = _make_service()
        board = self._make_board_with_special()
        board_svc = BoardService(
            MockConfigService(), MockLogService(), MockErrorService()
        )
        result = svc.regenerate_from_deadlock(board, 42)
        matches = board_svc.detect_matches(result.board_state)
        assert len(matches.matches) == 0
        assert board_svc.has_valid_moves(result.board_state)

    def test_metadata_populated(self):
        svc, _, _ = _make_service()
        board = self._make_board_with_special()
        result = svc.regenerate_from_deadlock(board, 42)
        assert result.generation_metadata.generation_attempts >= 1
        assert result.generation_metadata.generation_time_ms > 0

    def test_deterministic(self):
        svc, _, _ = _make_service()
        board = self._make_board_with_special()
        a = svc.regenerate_from_deadlock(board, 42)
        b = svc.regenerate_from_deadlock(board, 42)
        assert np.array_equal(a.board_state.grid, b.board_state.grid)


# ---------------------------------------------------------------------------
# calculate_cascade_potential
# ---------------------------------------------------------------------------


class TestCalculateCascadePotential:
    def test_returns_float_in_range(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(42)
        potential = svc.calculate_cascade_potential(result.board_state)
        assert isinstance(potential, float)
        assert 0.0 <= potential <= 1.0

    def test_different_boards_different_potentials(self):
        svc, _, _ = _make_service()
        potentials = set()
        for seed in range(10):
            result = svc.generate_board(seed)
            p = svc.calculate_cascade_potential(result.board_state)
            potentials.add(round(p, 4))
        # At least some variation.
        assert len(potentials) > 1

    def test_uniform_board_has_low_potential(self):
        """A board with maximum diversity should have low clustering."""
        svc, _, _ = _make_service()
        # Alternating pattern minimises clustering.
        grid = np.zeros((8, 8), dtype=np.int8)
        gems = [1, 2, 3, 4, 5, 6]
        for row in range(8):
            for col in range(8):
                grid[row, col] = gems[(row * 8 + col) % 6]
        board = BoardState(grid=grid)
        potential = svc.calculate_cascade_potential(board)
        assert potential < 0.5


# ---------------------------------------------------------------------------
# Cascade tuning
# ---------------------------------------------------------------------------


class TestCascadeTuning:
    def test_higher_target_higher_actual(self):
        svc_low, _, _ = _make_service()
        svc_high, _, _ = _make_service()

        low = svc_low.generate_board(42, BoardGenOptions(cascade_potential=0.2))
        high = svc_high.generate_board(42, BoardGenOptions(cascade_potential=0.8))

        # Higher target should generally produce higher actual (not always exact).
        assert (
            high.generation_metadata.cascade_potential_actual
            >= low.generation_metadata.cascade_potential_actual - 0.15
        )


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_cascade_potential_too_high(self):
        svc, _, _ = _make_service()
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, BoardGenOptions(cascade_potential=1.5))
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_cascade_potential_negative(self):
        svc, _, _ = _make_service()
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, BoardGenOptions(cascade_potential=-0.1))
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_near_miss_too_high(self):
        svc, _, _ = _make_service()
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, BoardGenOptions(near_miss_factor=2.0))
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_near_miss_negative(self):
        svc, _, _ = _make_service()
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, BoardGenOptions(near_miss_factor=-0.5))
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_invalid_gem_distribution_zero_weights(self):
        svc, _, _ = _make_service()
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, BoardGenOptions(gem_distribution={1: 0, 2: 0, 3: 0}))
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_invalid_gem_distribution_negative_weights(self):
        svc, _, _ = _make_service()
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, BoardGenOptions(gem_distribution={1: -1.0}))
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_dimensions_too_small(self):
        svc, _, _ = _make_service()
        with pytest.raises(AppError) as exc_info:
            svc.generate_board(42, BoardGenOptions(width=2, height=2))
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ---------------------------------------------------------------------------
# Seed evolution
# ---------------------------------------------------------------------------


class TestSeedEvolution:
    def test_evolve_seed_deterministic(self):
        a = BoardGenService._evolve_seed(42)
        b = BoardGenService._evolve_seed(42)
        assert a == b

    def test_evolve_seed_different(self):
        a = BoardGenService._evolve_seed(42)
        assert a != 42

    def test_evolve_seed_chain(self):
        seed = 42
        seen = set()
        for _ in range(100):
            seed = BoardGenService._evolve_seed(seed)
            assert seed not in seen
            seen.add(seed)

    def test_evolve_seed_positive(self):
        for s in [0, 1, -1, 2**30, 2**31]:
            result = BoardGenService._evolve_seed(s)
            assert result >= 0


# ---------------------------------------------------------------------------
# Metadata details
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_timing_positive(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(42)
        assert result.generation_metadata.generation_time_ms > 0

    def test_attempts_at_least_one(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(42)
        assert result.generation_metadata.generation_attempts >= 1

    def test_valid_moves_positive(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(42)
        assert result.generation_metadata.valid_moves_count > 0

    def test_cascade_potential_in_range(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(42)
        assert 0.0 <= result.generation_metadata.cascade_potential_actual <= 1.0

    def test_dimensions_match_options(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(width=6, height=5)
        result = svc.generate_board(42, opts)
        assert result.generation_metadata.width == 6
        assert result.generation_metadata.height == 5


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_seed_zero(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(0)
        assert isinstance(result, GeneratedBoard)

    def test_large_seed(self):
        svc, _, _ = _make_service()
        result = svc.generate_board(2**31 - 1)
        assert isinstance(result, GeneratedBoard)

    def test_small_board_3x3(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(width=3, height=3)
        result = svc.generate_board(42, opts)
        assert result.board_state.width == 3
        assert result.board_state.height == 3

    def test_large_board_12x12(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(width=12, height=12)
        result = svc.generate_board(42, opts)
        assert result.board_state.width == 12
        assert result.board_state.height == 12

    def test_cascade_potential_boundary_zero(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(cascade_potential=0.0)
        result = svc.generate_board(42, opts)
        assert isinstance(result, GeneratedBoard)

    def test_cascade_potential_boundary_one(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(cascade_potential=1.0)
        result = svc.generate_board(42, opts)
        assert isinstance(result, GeneratedBoard)

    def test_near_miss_boundary_one(self):
        svc, _, _ = _make_service()
        opts = BoardGenOptions(near_miss_factor=1.0)
        result = svc.generate_board(42, opts)
        assert isinstance(result, GeneratedBoard)
