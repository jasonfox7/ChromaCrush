"""Unit tests for BoardService — the core match-3 grid engine.

All tests inject mocks for ConfigProtocol, LoggerProtocol, and
ErrorServiceProtocol via ``__init__``. No global state is used.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.errors import AppError
from src.core.types.board import BoardState, MatchResult
from src.core.types.game import GemType, Move, Position
from src.modules.board.service import BoardService
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def config() -> MockConfigService:
    return MockConfigService()


@pytest.fixture
def logger() -> MockLogService:
    return MockLogService()


@pytest.fixture
def errors(logger: MockLogService) -> MockErrorService:
    return MockErrorService(logger)


@pytest.fixture
def service(
    config: MockConfigService,
    logger: MockLogService,
    errors: MockErrorService,
) -> BoardService:
    return BoardService(config=config, logger=logger, errors=errors)


# ------------------------------------------------------------------
# Helper to build boards from 2-D Python lists
# ------------------------------------------------------------------


def _board(rows: list[list[int]]) -> BoardState:
    """Convenience wrapper around ``BoardState.from_list``."""
    return BoardState.from_list(rows)


# ------------------------------------------------------------------
# create_board tests
# ------------------------------------------------------------------


class TestCreateBoard:
    def test_create_board_dimensions(self, service: BoardService) -> None:
        """Generated board has the requested 8x8 shape."""
        board = service.create_board(8, 8, seed=42)
        assert board.width == 8
        assert board.height == 8
        assert board.grid.shape == (8, 8)

    def test_create_board_no_initial_matches(self, service: BoardService) -> None:
        """A freshly generated board contains no 3-in-a-row matches."""
        board = service.create_board(8, 8, seed=42)
        result = service.detect_matches(board)
        assert len(result.matches) == 0

    def test_create_board_deterministic(self, service: BoardService) -> None:
        """Same seed produces the exact same board."""
        board_a = service.create_board(8, 8, seed=12345)
        board_b = service.create_board(8, 8, seed=12345)
        np.testing.assert_array_equal(board_a.grid, board_b.grid)

    def test_create_board_different_seeds(self, service: BoardService) -> None:
        """Different seeds produce different boards."""
        board_a = service.create_board(8, 8, seed=1)
        board_b = service.create_board(8, 8, seed=2)
        assert not np.array_equal(board_a.grid, board_b.grid)

    def test_create_board_only_standard_gems(self, service: BoardService) -> None:
        """Every cell contains a standard gem value (1-6)."""
        board = service.create_board(8, 8, seed=99)
        assert (board.grid >= 1).all()
        assert (board.grid <= 6).all()

    def test_create_board_no_matches_multiple_seeds(
        self, service: BoardService
    ) -> None:
        """Verify no initial matches across many different seeds."""
        for seed in range(50):
            board = service.create_board(8, 8, seed=seed)
            result = service.detect_matches(board)
            assert len(result.matches) == 0, f"Seed {seed} produced initial matches"


# ------------------------------------------------------------------
# swap_gems tests
# ------------------------------------------------------------------


class TestSwapGems:
    def test_swap_gems_basic(self, service: BoardService) -> None:
        """Swapping two adjacent gems exchanges their values."""
        board = _board(
            [
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        result = service.swap_gems(board, move)

        # Values are exchanged.
        assert result.get(Position(0, 0)) == GemType.BLUE  # was 1 (RED)
        assert result.get(Position(0, 1)) == GemType.RED  # was 2 (BLUE)

        # Original board is unchanged (immutability).
        assert board.get(Position(0, 0)) == GemType.RED
        assert board.get(Position(0, 1)) == GemType.BLUE

    def test_swap_gems_out_of_bounds(self, service: BoardService) -> None:
        """Swapping with an out-of-bounds position raises VALIDATION_OUT_OF_BOUNDS."""
        board = _board(
            [
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        # Position (0, 8) is out of bounds for an 8-wide board.
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        # We cannot construct Move with non-adjacent positions easily,
        # so test via the validation helper directly.
        with pytest.raises(AppError) as exc_info:
            service._validate_position(Position(0, 8), board)
        assert exc_info.value.code == "VALIDATION_OUT_OF_BOUNDS"

    def test_swap_gems_not_adjacent(self, service: BoardService) -> None:
        """Swapping non-adjacent positions raises VALIDATION_POSITIONS_NOT_ADJACENT.

        We bypass the Move constructor validation by testing swap_gems
        with positions that are in-bounds but not adjacent.
        """
        board = _board(
            [
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        # Move constructor rejects non-adjacent; use object.__new__ to bypass.
        move = object.__new__(Move)
        object.__setattr__(move, "from_pos", Position(0, 0))
        object.__setattr__(move, "to_pos", Position(0, 2))
        object.__setattr__(move, "timestamp_ms", 0)

        with pytest.raises(AppError) as exc_info:
            service.swap_gems(board, move)
        assert exc_info.value.code == "VALIDATION_POSITIONS_NOT_ADJACENT"

    def test_swap_gems_empty_cell(self, service: BoardService) -> None:
        """Swapping an empty cell raises VALIDATION_INVALID_GEM_SWAP."""
        board = _board(
            [
                [0, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        with pytest.raises(AppError) as exc_info:
            service.swap_gems(board, move)
        assert exc_info.value.code == "VALIDATION_INVALID_GEM_SWAP"


# ------------------------------------------------------------------
# detect_matches tests
# ------------------------------------------------------------------


class TestDetectMatches:
    def test_detect_matches_horizontal_3(self, service: BoardService) -> None:
        """Detects a horizontal run of 3 identical gems."""
        board = _board(
            [
                [1, 1, 1, 4, 5, 6, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        result = service.detect_matches(board)
        assert len(result.matches) == 1
        mg = result.matches[0]
        assert mg.is_horizontal
        assert mg.gem_type == GemType.RED
        assert mg.length == 3
        expected = frozenset({Position(0, 0), Position(0, 1), Position(0, 2)})
        assert mg.positions == expected

    def test_detect_matches_vertical_3(self, service: BoardService) -> None:
        """Detects a vertical run of 3 identical gems."""
        board = _board(
            [
                [1, 2, 3, 4, 5, 6, 2, 3],
                [1, 4, 5, 6, 2, 3, 4, 5],
                [1, 6, 2, 3, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        result = service.detect_matches(board)
        assert len(result.matches) >= 1
        # Find the match group that contains the vertical positions in column 0.
        # After flood-fill expansion, match groups are merged by colour so
        # we look for the RED group containing all three positions.
        expected_positions = {Position(0, 0), Position(1, 0), Position(2, 0)}
        red_match = [
            m
            for m in result.matches
            if m.gem_type == GemType.RED and expected_positions <= m.positions
        ]
        assert len(red_match) == 1
        assert red_match[0].length >= 3

    def test_detect_matches_no_matches(self, service: BoardService) -> None:
        """Returns empty MatchResult when no 3-in-a-row exists."""
        # A board with no matches (alternating pattern).
        board = _board(
            [
                [1, 2, 1, 2, 1, 2, 1, 2],
                [2, 1, 2, 1, 2, 1, 2, 1],
                [1, 2, 1, 2, 1, 2, 1, 2],
                [2, 1, 2, 1, 2, 1, 2, 1],
                [1, 2, 1, 2, 1, 2, 1, 2],
                [2, 1, 2, 1, 2, 1, 2, 1],
                [1, 2, 1, 2, 1, 2, 1, 2],
                [2, 1, 2, 1, 2, 1, 2, 1],
            ]
        )
        result = service.detect_matches(board)
        assert len(result.matches) == 0
        assert result.total_gems_matched == 0
        assert not result.creates_special_gem

    def test_detect_matches_four_creates_special(self, service: BoardService) -> None:
        """A horizontal 4-match creates LINE_BLAST_H."""
        board = _board(
            [
                [1, 1, 1, 1, 5, 6, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 2, 3, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 2, 3, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        result = service.detect_matches(board)
        assert result.creates_special_gem
        assert result.special_gem_type == GemType.LINE_BLAST_H

    def test_detect_matches_five_creates_radial(self, service: BoardService) -> None:
        """A 5-match creates RADIAL_BOMB."""
        board = _board(
            [
                [1, 1, 1, 1, 1, 6, 2, 3],
                [3, 4, 5, 6, 2, 3, 4, 5],
                [5, 6, 2, 3, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 2, 3, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        result = service.detect_matches(board)
        assert result.creates_special_gem
        assert result.special_gem_type == GemType.RADIAL_BOMB

    def test_detect_matches_t_shape_creates_chromatic_orb(
        self, service: BoardService
    ) -> None:
        """A T/L shape (overlapping H and V) creates CHROMATIC_ORB."""
        # Build a T shape at position (2,2): horizontal 1,1,1 at row 2, cols 1-3
        # and vertical 1,1,1 at col 2, rows 0-2.
        board = _board(
            [
                [2, 3, 1, 4, 5, 6, 2, 3],
                [3, 4, 1, 6, 2, 3, 4, 5],
                [5, 1, 1, 1, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 2, 3, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        result = service.detect_matches(board)
        assert result.creates_special_gem
        assert result.special_gem_type == GemType.CHROMATIC_ORB
        # The intersection point is (2, 2).
        assert result.special_gem_position == Position(2, 2)

    def test_detect_matches_only_standard_gems(self, service: BoardService) -> None:
        """Special gems (negative values) are not included in match runs."""
        board = _board(
            [
                [-1, -1, -1, 4, 5, 6, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        result = service.detect_matches(board)
        # No match should include the special gems.
        for mg in result.matches:
            assert mg.gem_type.value > 0

    def test_detect_matches_vertical_four(self, service: BoardService) -> None:
        """A vertical 4-match creates LINE_BLAST_V."""
        board = _board(
            [
                [1, 2, 3, 4, 5, 6, 2, 3],
                [1, 4, 5, 6, 2, 3, 4, 5],
                [1, 6, 2, 3, 4, 5, 6, 2],
                [1, 3, 4, 5, 6, 2, 3, 4],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 2, 3, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        result = service.detect_matches(board)
        assert result.creates_special_gem
        assert result.special_gem_type == GemType.LINE_BLAST_V


# ------------------------------------------------------------------
# clear_matches tests
# ------------------------------------------------------------------


class TestClearMatches:
    def test_clear_matches_sets_empty(self, service: BoardService) -> None:
        """Clearing matches sets all matched positions to GemType.EMPTY."""
        board = _board(
            [
                [1, 1, 1, 4, 5, 6, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        result = service.detect_matches(board)
        cleared = service.clear_matches(board, result)

        # Matched positions should now be EMPTY.
        for mg in result.matches:
            for pos in mg.positions:
                assert cleared.get(pos) == GemType.EMPTY

        # Original board is unchanged.
        assert board.get(Position(0, 0)) == GemType.RED


# ------------------------------------------------------------------
# apply_gravity tests
# ------------------------------------------------------------------


class TestApplyGravity:
    def test_apply_gravity_drops_gems(self, service: BoardService) -> None:
        """Gems fall to fill empty spaces; empties collect at top."""
        # Column 0 has empties in the MIDDLE so gems above must drop.
        board = _board(
            [
                [1, 2, 3, 4, 5, 6, 1, 2],
                [2, 4, 5, 6, 1, 2, 3, 4],
                [0, 6, 1, 2, 3, 4, 5, 6],
                [0, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        new_board, drops = service.apply_gravity(board)

        # Column 0: original was [1,2,0,0,3,5,1,3].
        # After gravity: empties rise to top -> [0,0,1,2,3,5,1,3].
        assert new_board.grid[0, 0] == 0
        assert new_board.grid[1, 0] == 0
        # Non-empty gems should be at the bottom.
        col_0 = new_board.grid[:, 0].tolist()
        non_empty = [v for v in col_0 if v != 0]
        assert non_empty == [1, 2, 3, 5, 1, 3]

        # Gems at rows 0-1 must have dropped by 2 positions.
        assert len(drops) > 0
        # Verify at least the gem that was at (0, 0)=1 dropped to (2, 0).
        drop_from_00 = [d for d in drops if d.from_pos == Position(0, 0)]
        assert len(drop_from_00) == 1
        assert drop_from_00[0].to_pos == Position(2, 0)
        assert drop_from_00[0].distance == 2

    def test_apply_gravity_no_change(self, service: BoardService) -> None:
        """A board with no empty cells produces no drops."""
        board = _board(
            [
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        new_board, drops = service.apply_gravity(board)
        assert len(drops) == 0
        np.testing.assert_array_equal(new_board.grid, board.grid)


# ------------------------------------------------------------------
# fill_empty tests
# ------------------------------------------------------------------


class TestFillEmpty:
    def test_fill_empty_fills_gaps(self, service: BoardService) -> None:
        """All empty cells are filled with standard gems (1-6)."""
        board = _board(
            [
                [0, 0, 0, 4, 5, 6, 1, 2],
                [0, 0, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        filled, spawns = service.fill_empty(board, seed=42)

        # No empty cells remain.
        assert (filled.grid != 0).all()
        # All values are valid standard gems.
        assert (filled.grid >= 1).all()
        assert (filled.grid <= 6).all()

        # Number of spawns equals number of originally empty cells.
        assert len(spawns) == 5  # 3 in row 0 + 2 in row 1

    def test_fill_empty_deterministic(self, service: BoardService) -> None:
        """Same board and seed produce the same fill."""
        board = _board(
            [
                [0, 0, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        filled_a, _ = service.fill_empty(board, seed=100)
        filled_b, _ = service.fill_empty(board, seed=100)
        np.testing.assert_array_equal(filled_a.grid, filled_b.grid)


# ------------------------------------------------------------------
# process_move tests
# ------------------------------------------------------------------


class TestProcessMove:
    def test_process_move_valid(self, service: BoardService) -> None:
        """A valid move that creates matches produces cascades."""
        # Set up a board where swapping (0,0) and (0,1) creates a horizontal
        # match of 3 RED gems in row 0.
        board = _board(
            [
                [2, 1, 1, 4, 5, 6, 3, 2],
                [1, 4, 5, 6, 2, 3, 4, 5],
                [5, 6, 2, 3, 4, 5, 6, 3],
                [2, 3, 4, 5, 6, 1, 2, 4],
                [3, 4, 5, 6, 1, 2, 3, 5],
                [5, 6, 2, 3, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        # Swap (0,0)=2 with (1,0)=1 -> row 0 becomes [1, 1, 1, ...] = match!
        move = Move(from_pos=Position(0, 0), to_pos=Position(1, 0), timestamp_ms=0)
        result = service.process_move(board, move, seed=42)

        assert result.was_valid_match
        assert result.chain_count >= 1
        assert result.total_gems_cleared >= 3

    def test_process_move_no_match(self, service: BoardService) -> None:
        """A swap that creates no matches returns was_valid_match=False."""
        board = _board(
            [
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
                [5, 6, 1, 2, 3, 4, 5, 6],
                [1, 2, 3, 4, 5, 6, 1, 2],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(0, 1), timestamp_ms=0)
        result = service.process_move(board, move, seed=42)

        assert not result.was_valid_match
        assert result.chain_count == 0
        assert result.total_gems_cleared == 0
        # Board should be unchanged (swap reverted).
        np.testing.assert_array_equal(result.final_board.grid, board.grid)

    def test_process_move_deterministic(self, service: BoardService) -> None:
        """Same inputs produce identical cascade outcomes."""
        board = _board(
            [
                [2, 1, 1, 4, 5, 6, 3, 2],
                [1, 4, 5, 6, 2, 3, 4, 5],
                [5, 6, 2, 3, 4, 5, 6, 3],
                [2, 3, 4, 5, 6, 1, 2, 4],
                [3, 4, 5, 6, 1, 2, 3, 5],
                [5, 6, 2, 3, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        move = Move(from_pos=Position(0, 0), to_pos=Position(1, 0), timestamp_ms=0)

        result_a = service.process_move(board, move, seed=42)
        result_b = service.process_move(board, move, seed=42)

        np.testing.assert_array_equal(
            result_a.final_board.grid, result_b.final_board.grid
        )
        assert result_a.chain_count == result_b.chain_count
        assert result_a.total_gems_cleared == result_b.total_gems_cleared

    def test_process_move_board_immutability(self, service: BoardService) -> None:
        """process_move does not modify the input board."""
        board = _board(
            [
                [2, 1, 1, 4, 5, 6, 3, 2],
                [1, 4, 5, 6, 2, 3, 4, 5],
                [5, 6, 2, 3, 4, 5, 6, 3],
                [2, 3, 4, 5, 6, 1, 2, 4],
                [3, 4, 5, 6, 1, 2, 3, 5],
                [5, 6, 2, 3, 4, 5, 6, 2],
                [2, 3, 4, 5, 6, 1, 2, 3],
                [3, 4, 5, 6, 1, 2, 3, 4],
            ]
        )
        original_grid = board.grid.copy()
        move = Move(from_pos=Position(0, 0), to_pos=Position(1, 0), timestamp_ms=0)
        service.process_move(board, move, seed=42)
        np.testing.assert_array_equal(board.grid, original_grid)


# ------------------------------------------------------------------
# validate_board tests
# ------------------------------------------------------------------


class TestValidateBoard:
    def test_validate_board_valid(self, service: BoardService) -> None:
        """A well-formed 8x8 board with standard gems validates True."""
        board = service.create_board(8, 8, seed=42)
        assert service.validate_board(board) is True

    def test_validate_board_invalid_dimensions(self, service: BoardService) -> None:
        """A board with wrong dimensions validates False."""
        # Config expects 8x8 but we build a 4x4 board.
        board = _board(
            [
                [1, 2, 3, 4],
                [5, 6, 1, 2],
                [3, 4, 5, 6],
                [1, 2, 3, 4],
            ]
        )
        assert service.validate_board(board) is False

    def test_validate_board_invalid_gem_value(self, service: BoardService) -> None:
        """A board with an unrecognised gem value validates False."""
        grid = np.ones((8, 8), dtype=np.int8)
        grid[3, 3] = 99  # Not a valid GemType.
        board = BoardState(grid=grid)
        assert service.validate_board(board) is False


# ------------------------------------------------------------------
# has_valid_moves tests
# ------------------------------------------------------------------


class TestHasValidMoves:
    def test_has_valid_moves_with_moves(self, service: BoardService) -> None:
        """A normal generated board should have valid moves."""
        board = service.create_board(8, 8, seed=42)
        assert service.has_valid_moves(board) is True

    def test_has_valid_moves_deadlock(self, service: BoardService) -> None:
        """A 3-colour cyclic board with row-shift-by-1 is a deadlock.

        Pattern: cell(r, c) = 1 + ((r + c) % 3).
        No adjacent swap can produce 3-in-a-row because every cell
        differs from its neighbour in both directions and the cyclic
        distance prevents triples after any single swap.
        """
        rows: list[list[int]] = []
        for r in range(8):
            row: list[int] = []
            for c in range(8):
                row.append(1 + (r + c) % 3)
            rows.append(row)
        board = _board(rows)
        assert service.has_valid_moves(board) is False
