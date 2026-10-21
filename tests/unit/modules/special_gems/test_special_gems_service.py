"""Unit tests for SpecialGemsService -- pure, synchronous effect calculation.

All tests inject mocks for ConfigProtocol, LoggerProtocol,
ErrorServiceProtocol, and ScoringServiceProtocol via ``__init__``.
No global state is used.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.errors import AppError
from src.core.types.board import BoardState, MatchGroup, MatchResult
from src.core.types.game import GemType, Position
from src.modules.scoring.types import SpecialGemBonus
from src.modules.special_gems.service import SpecialGemsService
from src.modules.special_gems.types import (
    SPECIAL_GEM_TYPES,
    FusionEffect,
    FusionType,
    SpecialGemEffect,
)
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ------------------------------------------------------------------
# Mock scoring service
# ------------------------------------------------------------------


class MockScoringService:
    """Mock scoring service that returns predictable SpecialGemBonus results.

    The bonus formula:
        base_activation_bonus = 100 (for all types)
        per_gem_bonus = 10
        total_bonus = 100 + (gems_affected * 10)
    """

    def calculate_special_gem_bonus(
        self, gem_type: GemType, gems_affected: int
    ) -> SpecialGemBonus:
        return SpecialGemBonus(
            gem_type=gem_type,
            base_activation_bonus=100,
            gems_affected=gems_affected,
            per_gem_bonus=10,
            total_bonus=100 + gems_affected * 10,
        )


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
def scoring() -> MockScoringService:
    return MockScoringService()


@pytest.fixture
def service(
    config: MockConfigService,
    logger: MockLogService,
    errors: MockErrorService,
    scoring: MockScoringService,
) -> SpecialGemsService:
    return SpecialGemsService(
        config=config,
        logger=logger,
        errors=errors,
        scoring_service=scoring,
    )


# ------------------------------------------------------------------
# Helpers for creating test data
# ------------------------------------------------------------------


def _make_board(data: list[list[int]]) -> BoardState:
    """Create a BoardState from a 2D list of ints."""
    return BoardState.from_list(data)


def _make_8x8_board() -> BoardState:
    """Create a standard 8x8 board with all RED gems."""
    return _make_board([[1] * 8 for _ in range(8)])


def _make_8x8_board_with_specials() -> BoardState:
    """Create an 8x8 board with some special gems placed.

    Layout (row, col):
      (3, 4) = LINE_BLAST_H (-1)
      (3, 5) = LINE_BLAST_V (-2)
      (4, 4) = RADIAL_BOMB (-3)
      (4, 5) = CHROMATIC_ORB (-4)
      Rest = RED (1)
    """
    data = [[1] * 8 for _ in range(8)]
    data[3][4] = -1  # LINE_BLAST_H
    data[3][5] = -2  # LINE_BLAST_V
    data[4][4] = -3  # RADIAL_BOMB
    data[4][5] = -4  # CHROMATIC_ORB
    return _make_board(data)


def _match_group(
    positions: list[tuple[int, int]],
    gem_type: GemType = GemType.RED,
    is_horizontal: bool = True,
) -> MatchGroup:
    """Build a MatchGroup from position tuples."""
    return MatchGroup(
        positions=frozenset(Position(r, c) for r, c in positions),
        gem_type=gem_type,
        is_horizontal=is_horizontal,
    )


def _match_result(
    groups: list[MatchGroup],
    creates_special: bool = False,
) -> MatchResult:
    """Build a MatchResult from match groups."""
    total = sum(g.length for g in groups)
    return MatchResult(
        matches=tuple(groups),
        total_gems_matched=total,
        creates_special_gem=creates_special,
    )


# ==================================================================
# 1. is_special_gem
# ==================================================================


class TestIsSpecialGem:
    """Tests for is_special_gem method."""

    def test_line_blast_h_is_special(self, service: SpecialGemsService) -> None:
        assert service.is_special_gem(GemType.LINE_BLAST_H) is True

    def test_line_blast_v_is_special(self, service: SpecialGemsService) -> None:
        assert service.is_special_gem(GemType.LINE_BLAST_V) is True

    def test_radial_bomb_is_special(self, service: SpecialGemsService) -> None:
        assert service.is_special_gem(GemType.RADIAL_BOMB) is True

    def test_chromatic_orb_is_special(self, service: SpecialGemsService) -> None:
        assert service.is_special_gem(GemType.CHROMATIC_ORB) is True

    def test_red_not_special(self, service: SpecialGemsService) -> None:
        assert service.is_special_gem(GemType.RED) is False

    def test_empty_not_special(self, service: SpecialGemsService) -> None:
        assert service.is_special_gem(GemType.EMPTY) is False

    def test_blue_not_special(self, service: SpecialGemsService) -> None:
        assert service.is_special_gem(GemType.BLUE) is False

    def test_orange_not_special(self, service: SpecialGemsService) -> None:
        assert service.is_special_gem(GemType.ORANGE) is False


# ==================================================================
# 2. calculate_effect -- each special gem type
# ==================================================================


class TestCalculateEffectLineBlastH:
    """Tests for horizontal line blast activation."""

    def test_clears_entire_row(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(3, 4))

        assert effect.gem_type == GemType.LINE_BLAST_H
        assert effect.source_position == Position(3, 4)
        # Should clear all 8 columns in row 3.
        assert len(effect.affected_positions) == 8
        for col in range(8):
            assert Position(3, col) in effect.affected_positions

    def test_description_mentions_row(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(3, 4))
        assert "row 3" in effect.description

    def test_bonus_score_calculated(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(3, 4))
        assert effect.bonus_score.gems_affected == 8
        assert effect.bonus_score.total_bonus == 100 + 8 * 10

    def test_detects_triggered_specials_in_row(
        self, service: SpecialGemsService
    ) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(3, 4))
        # LINE_BLAST_V at (3,5) is in the same row.
        triggered_positions = effect.triggers_special_gems
        assert Position(3, 5) in triggered_positions


class TestCalculateEffectLineBlastV:
    """Tests for vertical line blast activation."""

    def test_clears_entire_column(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(3, 5))

        assert effect.gem_type == GemType.LINE_BLAST_V
        assert len(effect.affected_positions) == 8
        for row in range(8):
            assert Position(row, 5) in effect.affected_positions

    def test_description_mentions_column(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(3, 5))
        assert "column 5" in effect.description

    def test_detects_triggered_specials_in_column(
        self, service: SpecialGemsService
    ) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(3, 5))
        # CHROMATIC_ORB at (4,5) is in the same column.
        triggered_positions = effect.triggers_special_gems
        assert Position(4, 5) in triggered_positions


class TestCalculateEffectRadialBomb:
    """Tests for radial bomb activation."""

    def test_clears_3x3_area_center(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(4, 4))

        assert effect.gem_type == GemType.RADIAL_BOMB
        # 3x3 area centered at (4,4) = 9 positions.
        assert len(effect.affected_positions) == 9
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                assert Position(4 + dr, 4 + dc) in effect.affected_positions

    def test_description_mentions_3x3(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(4, 4))
        assert "3x3" in effect.description

    def test_radial_bomb_at_corner(self, service: SpecialGemsService) -> None:
        """Radial bomb at (0,0) should only clear valid positions."""
        data = [[1] * 8 for _ in range(8)]
        data[0][0] = -3  # RADIAL_BOMB at corner
        board = _make_board(data)
        effect = service.calculate_effect(board, Position(0, 0))

        # At corner (0,0) with radius=1: only (0,0), (0,1), (1,0), (1,1).
        assert len(effect.affected_positions) == 4
        assert Position(0, 0) in effect.affected_positions
        assert Position(0, 1) in effect.affected_positions
        assert Position(1, 0) in effect.affected_positions
        assert Position(1, 1) in effect.affected_positions

    def test_radial_bomb_at_edge(self, service: SpecialGemsService) -> None:
        """Radial bomb at (0,3) should clip to top edge."""
        data = [[1] * 8 for _ in range(8)]
        data[0][3] = -3
        board = _make_board(data)
        effect = service.calculate_effect(board, Position(0, 3))

        # Positions: (0,2), (0,3), (0,4), (1,2), (1,3), (1,4) = 6
        assert len(effect.affected_positions) == 6

    def test_detects_triggered_specials_in_area(
        self, service: SpecialGemsService
    ) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(4, 4))
        # (3,4)=LBH, (3,5)=LBV, (4,5)=CO are in 3x3 area of (4,4).
        triggered = effect.triggers_special_gems
        assert Position(3, 4) in triggered
        assert Position(3, 5) in triggered
        assert Position(4, 5) in triggered


class TestCalculateEffectChromaticOrb:
    """Tests for chromatic orb activation."""

    def test_clears_all_target_color_gems(self, service: SpecialGemsService) -> None:
        data = [
            [1, 2, 1, 2, 1, 2, 1, 2],
            [2, 1, 2, 1, 2, 1, 2, 1],
            [1, 2, 1, 2, 1, 2, 1, 2],
            [2, 1, 2, 1, -4, 2, 1, 2],  # CHROMATIC_ORB at (3,4)
            [1, 2, 1, 2, 1, 2, 1, 2],
            [2, 1, 2, 1, 2, 1, 2, 1],
            [1, 2, 1, 2, 1, 2, 1, 2],
            [2, 1, 2, 1, 2, 1, 2, 1],
        ]
        board = _make_board(data)
        effect = service.calculate_effect(
            board, Position(3, 4), target_color=GemType.RED
        )

        assert effect.gem_type == GemType.CHROMATIC_ORB
        # Count RED gems + the orb itself.
        red_count = sum(1 for r in data for v in r if v == 1)
        # The orb is at (3,4) which is -4 (not RED), so orb adds 1 extra.
        assert len(effect.affected_positions) == red_count + 1

    def test_orb_itself_included_in_affected(self, service: SpecialGemsService) -> None:
        data = [[2] * 8 for _ in range(8)]
        data[3][4] = -4
        board = _make_board(data)
        # Target BLUE (2) — all cells are BLUE except the orb.
        effect = service.calculate_effect(
            board, Position(3, 4), target_color=GemType.BLUE
        )
        assert Position(3, 4) in effect.affected_positions

    def test_description_mentions_color(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -4
        board = _make_board(data)
        effect = service.calculate_effect(
            board, Position(3, 4), target_color=GemType.RED
        )
        assert "RED" in effect.description


# ==================================================================
# 3. calculate_effect -- edge cases and validation
# ==================================================================


class TestCalculateEffectValidation:
    """Tests for calculate_effect validation and edge cases."""

    def test_out_of_bounds_raises(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board()
        with pytest.raises(AppError) as exc_info:
            service.calculate_effect(board, Position(10, 10))
        assert exc_info.value.code == "VALIDATION_OUT_OF_BOUNDS"

    def test_not_special_gem_raises(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board()  # All RED
        with pytest.raises(AppError) as exc_info:
            service.calculate_effect(board, Position(0, 0))
        assert exc_info.value.code == "VALIDATION_INVALID_GEM_SWAP"

    def test_chromatic_without_target_raises(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        with pytest.raises(AppError) as exc_info:
            service.calculate_effect(board, Position(4, 5))  # CHROMATIC_ORB
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_chromatic_with_invalid_target_raises(
        self, service: SpecialGemsService
    ) -> None:
        board = _make_8x8_board_with_specials()
        with pytest.raises(AppError) as exc_info:
            service.calculate_effect(board, Position(4, 5), target_color=GemType.EMPTY)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_chromatic_with_special_gem_target_raises(
        self, service: SpecialGemsService
    ) -> None:
        board = _make_8x8_board_with_specials()
        with pytest.raises(AppError) as exc_info:
            service.calculate_effect(
                board, Position(4, 5), target_color=GemType.LINE_BLAST_H
            )
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_line_blast_at_row_0(self, service: SpecialGemsService) -> None:
        """Line blast at row 0 should still clear entire row."""
        data = [[1] * 8 for _ in range(8)]
        data[0][3] = -1
        board = _make_board(data)
        effect = service.calculate_effect(board, Position(0, 3))
        assert len(effect.affected_positions) == 8

    def test_line_blast_at_last_column(self, service: SpecialGemsService) -> None:
        """Vertical line blast at last column should clear entire column."""
        data = [[1] * 8 for _ in range(8)]
        data[4][7] = -2
        board = _make_board(data)
        effect = service.calculate_effect(board, Position(4, 7))
        assert len(effect.affected_positions) == 8
        for row in range(8):
            assert Position(row, 7) in effect.affected_positions


# ==================================================================
# 4. calculate_fusion_effect -- all 6 fusion types
# ==================================================================


class TestFusionCrossBlast:
    """Line + Line = Cross Blast."""

    def test_cross_blast_clears_row_and_column(
        self, service: SpecialGemsService
    ) -> None:
        board = _make_8x8_board_with_specials()
        # LBH at (3,4), LBV at (3,5) — adjacent horizontally.
        effect = service.calculate_fusion_effect(board, Position(3, 4), Position(3, 5))

        assert effect.fusion_type == FusionType.CROSS_BLAST
        mid_row = 3
        mid_col = 4  # (4+5)//2 = 4
        # Row 3 (8 positions) + Column 4 (8 positions) - intersection (1).
        assert len(effect.affected_positions) == 15

    def test_cross_blast_description(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_fusion_effect(board, Position(3, 4), Position(3, 5))
        assert "Cross Blast" in effect.description

    def test_cross_blast_same_type(self, service: SpecialGemsService) -> None:
        """Two LINE_BLAST_H gems also produce Cross Blast."""
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -1  # LBH
        data[3][5] = -1  # LBH
        board = _make_board(data)
        effect = service.calculate_fusion_effect(board, Position(3, 4), Position(3, 5))
        assert effect.fusion_type == FusionType.CROSS_BLAST


class TestFusionTripleLine:
    """Line + Radial = Triple Line."""

    def test_triple_line_horizontal(self, service: SpecialGemsService) -> None:
        """LINE_BLAST_H + RADIAL_BOMB = clears 3 rows."""
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -1  # LBH
        data[4][4] = -3  # RADIAL_BOMB
        board = _make_board(data)
        effect = service.calculate_fusion_effect(board, Position(3, 4), Position(4, 4))

        assert effect.fusion_type == FusionType.TRIPLE_LINE
        # Mid row = (3+4)//2 = 3. Clears rows 2, 3, 4.
        # 3 rows x 8 cols = 24 positions.
        assert len(effect.affected_positions) == 24

    def test_triple_line_vertical(self, service: SpecialGemsService) -> None:
        """LINE_BLAST_V + RADIAL_BOMB = clears 3 columns."""
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -2  # LBV
        data[3][5] = -3  # RADIAL_BOMB
        board = _make_board(data)
        effect = service.calculate_fusion_effect(board, Position(3, 4), Position(3, 5))

        assert effect.fusion_type == FusionType.TRIPLE_LINE
        # Mid col = (4+5)//2 = 4. Clears cols 3, 4, 5.
        # 3 cols x 8 rows = 24 positions.
        assert len(effect.affected_positions) == 24

    def test_triple_line_at_edge_clips(self, service: SpecialGemsService) -> None:
        """Triple line at row 0 clips to board bounds."""
        data = [[1] * 8 for _ in range(8)]
        data[0][4] = -1  # LBH
        data[1][4] = -3  # RADIAL_BOMB
        board = _make_board(data)
        effect = service.calculate_fusion_effect(board, Position(0, 4), Position(1, 4))

        assert effect.fusion_type == FusionType.TRIPLE_LINE
        # Mid row = 0. Clears rows -1 (invalid), 0, 1 => only rows 0 and 1.
        # 2 rows x 8 cols = 16.
        assert len(effect.affected_positions) == 16


class TestFusionMegaBomb:
    """Radial + Radial = Mega Bomb."""

    def test_mega_bomb_5x5(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[4][4] = -3  # RADIAL_BOMB
        data[4][5] = -3  # RADIAL_BOMB
        board = _make_board(data)
        effect = service.calculate_fusion_effect(board, Position(4, 4), Position(4, 5))

        assert effect.fusion_type == FusionType.MEGA_BOMB
        # Center = (4, 4). Radius=2 => 5x5 = 25 positions.
        assert len(effect.affected_positions) == 25

    def test_mega_bomb_description(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[4][4] = -3
        data[4][5] = -3
        board = _make_board(data)
        effect = service.calculate_fusion_effect(board, Position(4, 4), Position(4, 5))
        assert "Mega Bomb" in effect.description
        assert "5x5" in effect.description

    def test_mega_bomb_at_corner(self, service: SpecialGemsService) -> None:
        """Mega bomb near corner clips to bounds."""
        data = [[1] * 8 for _ in range(8)]
        data[0][0] = -3
        data[0][1] = -3
        board = _make_board(data)
        effect = service.calculate_fusion_effect(board, Position(0, 0), Position(0, 1))

        assert effect.fusion_type == FusionType.MEGA_BOMB
        # Center = (0, 0). Radius=2 => rows -2..2, cols -2..2.
        # Valid: rows 0..2, cols 0..2 => 3x3 = 9 positions.
        assert len(effect.affected_positions) == 9


class TestFusionColorLineBlast:
    """Line + Chromatic = Color Line Blast."""

    def test_color_line_blast_horizontal(self, service: SpecialGemsService) -> None:
        data = [
            [1, 2, 1, 2, 1, 2, 1, 2],
            [2, 1, 2, 1, 2, 1, 2, 1],
            [1, 2, 1, 2, 1, 2, 1, 2],
            [2, 1, 2, 1, -1, -4, 1, 2],  # LBH at (3,4), CO at (3,5)
            [1, 2, 1, 2, 1, 2, 1, 2],
            [2, 1, 2, 1, 2, 1, 2, 1],
            [1, 2, 1, 2, 1, 2, 1, 2],
            [2, 1, 2, 1, 2, 1, 2, 1],
        ]
        board = _make_board(data)
        effect = service.calculate_fusion_effect(
            board, Position(3, 4), Position(3, 5), target_color=GemType.RED
        )

        assert effect.fusion_type == FusionType.COLOR_LINE_BLAST
        # Each RED gem becomes a horizontal line blast.
        # Secondary effects should exist.
        assert len(effect.secondary_effects) > 0
        assert "Color Line Blast" in effect.description

    def test_color_line_blast_requires_target(
        self, service: SpecialGemsService
    ) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -1  # LBH
        data[3][5] = -4  # CO
        board = _make_board(data)
        with pytest.raises(AppError) as exc_info:
            service.calculate_fusion_effect(board, Position(3, 4), Position(3, 5))
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


class TestFusionColorBomb:
    """Radial + Chromatic = Color Bomb."""

    def test_color_bomb(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[4][4] = -3  # RADIAL_BOMB
        data[4][5] = -4  # CHROMATIC_ORB
        board = _make_board(data)
        effect = service.calculate_fusion_effect(
            board, Position(4, 4), Position(4, 5), target_color=GemType.RED
        )

        assert effect.fusion_type == FusionType.COLOR_BOMB
        assert len(effect.secondary_effects) > 0
        assert "Color Bomb" in effect.description

    def test_color_bomb_requires_target(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[4][4] = -3
        data[4][5] = -4
        board = _make_board(data)
        with pytest.raises(AppError) as exc_info:
            service.calculate_fusion_effect(board, Position(4, 4), Position(4, 5))
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


class TestFusionBoardClear:
    """Chromatic + Chromatic = Board Clear."""

    def test_board_clear(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -4  # CHROMATIC_ORB
        data[3][5] = -4  # CHROMATIC_ORB
        board = _make_board(data)
        effect = service.calculate_fusion_effect(board, Position(3, 4), Position(3, 5))

        assert effect.fusion_type == FusionType.BOARD_CLEAR
        # Entire 8x8 board = 64 positions.
        assert len(effect.affected_positions) == 64

    def test_board_clear_description(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -4
        data[3][5] = -4
        board = _make_board(data)
        effect = service.calculate_fusion_effect(board, Position(3, 4), Position(3, 5))
        assert "Double Chromatic" in effect.description


# ==================================================================
# 5. calculate_fusion_effect -- validation
# ==================================================================


class TestFusionValidation:
    """Tests for fusion validation."""

    def test_not_adjacent_raises(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[0][0] = -1
        data[2][2] = -2
        board = _make_board(data)
        with pytest.raises(AppError) as exc_info:
            service.calculate_fusion_effect(board, Position(0, 0), Position(2, 2))
        assert exc_info.value.code == "VALIDATION_POSITIONS_NOT_ADJACENT"

    def test_first_not_special_raises(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[3][5] = -1  # only second is special
        board = _make_board(data)
        with pytest.raises(AppError) as exc_info:
            service.calculate_fusion_effect(board, Position(3, 4), Position(3, 5))
        assert exc_info.value.code == "VALIDATION_INVALID_GEM_SWAP"

    def test_second_not_special_raises(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -1  # only first is special
        board = _make_board(data)
        with pytest.raises(AppError) as exc_info:
            service.calculate_fusion_effect(board, Position(3, 4), Position(3, 5))
        assert exc_info.value.code == "VALIDATION_INVALID_GEM_SWAP"

    def test_out_of_bounds_raises(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board()
        with pytest.raises(AppError) as exc_info:
            service.calculate_fusion_effect(board, Position(10, 10), Position(10, 11))
        assert exc_info.value.code == "VALIDATION_OUT_OF_BOUNDS"

    def test_fusion_normalizes_order(self, service: SpecialGemsService) -> None:
        """Fusion should produce same result regardless of argument order."""
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -1  # LBH
        data[3][5] = -3  # RADIAL_BOMB
        board = _make_board(data)

        effect_ab = service.calculate_fusion_effect(
            board, Position(3, 4), Position(3, 5)
        )
        effect_ba = service.calculate_fusion_effect(
            board, Position(3, 5), Position(3, 4)
        )

        assert effect_ab.fusion_type == effect_ba.fusion_type
        assert effect_ab.affected_positions == effect_ba.affected_positions


# ==================================================================
# 6. apply_effect
# ==================================================================


class TestApplyEffect:
    """Tests for apply_effect method."""

    def test_apply_special_gem_effect_clears_positions(
        self, service: SpecialGemsService
    ) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(3, 4))  # LBH
        new_board, cleared = service.apply_effect(board, effect)

        # Row 3 should be all EMPTY.
        for col in range(8):
            assert new_board.get(Position(3, col)) == GemType.EMPTY

        # Other rows should be untouched.
        assert new_board.get(Position(0, 0)) == GemType.RED
        assert len(cleared) == 8

    def test_apply_effect_does_not_modify_original(
        self, service: SpecialGemsService
    ) -> None:
        board = _make_8x8_board_with_specials()
        original_grid = board.grid.copy()
        effect = service.calculate_effect(board, Position(3, 4))
        service.apply_effect(board, effect)

        # Original board is unchanged.
        assert np.array_equal(board.grid, original_grid)

    def test_apply_fusion_effect_clears_all(self, service: SpecialGemsService) -> None:
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -4
        data[3][5] = -4
        board = _make_board(data)
        effect = service.calculate_fusion_effect(board, Position(3, 4), Position(3, 5))
        new_board, cleared = service.apply_effect(board, effect)

        # Board clear: entire board should be EMPTY.
        for row in range(8):
            for col in range(8):
                assert new_board.get(Position(row, col)) == GemType.EMPTY

        assert len(cleared) == 64

    def test_apply_effect_with_secondary_effects(
        self, service: SpecialGemsService
    ) -> None:
        """Color Bomb fusion has secondary effects that should also clear."""
        data = [[1] * 8 for _ in range(8)]
        data[4][4] = -3  # RADIAL_BOMB
        data[4][5] = -4  # CHROMATIC_ORB
        board = _make_board(data)
        effect = service.calculate_fusion_effect(
            board, Position(4, 4), Position(4, 5), target_color=GemType.RED
        )
        new_board, cleared = service.apply_effect(board, effect)

        # Many positions should be cleared.
        assert len(cleared) > 0
        # Verify at least some positions are EMPTY.
        for pos in cleared:
            assert new_board.get(pos) == GemType.EMPTY

    def test_apply_radial_bomb_effect(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(4, 4))  # RADIAL_BOMB
        new_board, cleared = service.apply_effect(board, effect)

        # 3x3 area centered at (4,4) should be EMPTY.
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                assert new_board.get(Position(4 + dr, 4 + dc)) == GemType.EMPTY

        assert len(cleared) == 9


# ==================================================================
# 7. get_special_gem_for_match
# ==================================================================


class TestGetSpecialGemForMatch:
    """Tests for get_special_gem_for_match method."""

    def test_3_match_returns_none(self, service: SpecialGemsService) -> None:
        group = _match_group([(0, 0), (0, 1), (0, 2)])
        result = service.get_special_gem_for_match(_match_result([group]))
        assert result is None

    def test_4_horizontal_returns_line_blast_h(
        self, service: SpecialGemsService
    ) -> None:
        group = _match_group([(0, 0), (0, 1), (0, 2), (0, 3)], is_horizontal=True)
        result = service.get_special_gem_for_match(_match_result([group]))
        assert result is not None
        gem_type, pos = result
        assert gem_type == GemType.LINE_BLAST_H
        # Center of sorted [(0,0),(0,1),(0,2),(0,3)] at index 2 = (0,2).
        assert pos == Position(0, 2)

    def test_4_vertical_returns_line_blast_v(self, service: SpecialGemsService) -> None:
        group = _match_group([(0, 0), (1, 0), (2, 0), (3, 0)], is_horizontal=False)
        result = service.get_special_gem_for_match(_match_result([group]))
        assert result is not None
        gem_type, pos = result
        assert gem_type == GemType.LINE_BLAST_V
        # Center of sorted [(0,0),(1,0),(2,0),(3,0)] at index 2 = (2,0).
        assert pos == Position(2, 0)

    def test_5_match_returns_radial_bomb(self, service: SpecialGemsService) -> None:
        group = _match_group([(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)])
        result = service.get_special_gem_for_match(_match_result([group]))
        assert result is not None
        gem_type, pos = result
        assert gem_type == GemType.RADIAL_BOMB
        # Center of 5 sorted positions at index 2 = (0,2).
        assert pos == Position(0, 2)

    def test_6_match_returns_radial_bomb(self, service: SpecialGemsService) -> None:
        group = _match_group([(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5)])
        result = service.get_special_gem_for_match(_match_result([group]))
        assert result is not None
        gem_type, _ = result
        assert gem_type == GemType.RADIAL_BOMB

    def test_t_shape_returns_chromatic_orb(self, service: SpecialGemsService) -> None:
        """T-shape: two matches overlapping at intersection."""
        h_group = _match_group([(2, 1), (2, 2), (2, 3)], is_horizontal=True)
        v_group = _match_group([(1, 2), (2, 2), (3, 2)], is_horizontal=False)
        result = service.get_special_gem_for_match(_match_result([h_group, v_group]))
        assert result is not None
        gem_type, pos = result
        assert gem_type == GemType.CHROMATIC_ORB
        assert pos == Position(2, 2)  # The intersection

    def test_l_shape_returns_chromatic_orb(self, service: SpecialGemsService) -> None:
        """L-shape: two matches overlapping at corner."""
        h_group = _match_group([(2, 0), (2, 1), (2, 2)], is_horizontal=True)
        v_group = _match_group([(0, 0), (1, 0), (2, 0)], is_horizontal=False)
        result = service.get_special_gem_for_match(_match_result([h_group, v_group]))
        assert result is not None
        gem_type, pos = result
        assert gem_type == GemType.CHROMATIC_ORB
        assert pos == Position(2, 0)  # The intersection

    def test_empty_matches_raises(self, service: SpecialGemsService) -> None:
        result = MatchResult(
            matches=(),
            total_gems_matched=0,
            creates_special_gem=False,
        )
        with pytest.raises(AppError) as exc_info:
            service.get_special_gem_for_match(result)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_t_shape_picks_first_overlap_deterministically(
        self, service: SpecialGemsService
    ) -> None:
        """If multiple overlaps, pick the one with smallest (row, col)."""
        h_group = _match_group([(2, 1), (2, 2), (2, 3)], is_horizontal=True)
        v_group1 = _match_group([(1, 1), (2, 1), (3, 1)], is_horizontal=False)
        v_group2 = _match_group([(1, 3), (2, 3), (3, 3)], is_horizontal=False)
        result = service.get_special_gem_for_match(
            _match_result([h_group, v_group1, v_group2])
        )
        assert result is not None
        gem_type, pos = result
        assert gem_type == GemType.CHROMATIC_ORB
        assert pos == Position(2, 1)  # Smallest overlap position


# ==================================================================
# 8. find_triggered_special_gems
# ==================================================================


class TestFindTriggeredSpecialGems:
    """Tests for find_triggered_special_gems method."""

    def test_finds_specials_in_cleared_area(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        cleared = {Position(3, 4), Position(3, 5), Position(4, 4), Position(4, 5)}
        triggered = service.find_triggered_special_gems(board, cleared)

        # All 4 specials are in the cleared area.
        assert Position(3, 4) in triggered  # LBH
        assert Position(3, 5) in triggered  # LBV
        assert Position(4, 4) in triggered  # RB
        assert Position(4, 5) in triggered  # CO

    def test_does_not_find_standard_gems(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board()  # All RED, no specials
        cleared = {Position(0, 0), Position(0, 1), Position(0, 2)}
        triggered = service.find_triggered_special_gems(board, cleared)
        assert triggered == []

    def test_sorted_by_row_col(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        cleared = {Position(4, 5), Position(3, 4), Position(4, 4), Position(3, 5)}
        triggered = service.find_triggered_special_gems(board, cleared)

        # Should be sorted: (3,4), (3,5), (4,4), (4,5).
        assert triggered == [
            Position(3, 4),
            Position(3, 5),
            Position(4, 4),
            Position(4, 5),
        ]

    def test_respects_chain_reaction_disabled(
        self,
        logger: MockLogService,
        errors: MockErrorService,
        scoring: MockScoringService,
    ) -> None:
        config = MockConfigService({"special_gems.chain_reaction_enabled": False})
        svc = SpecialGemsService(
            config=config,
            logger=logger,
            errors=errors,
            scoring_service=scoring,
        )
        board = _make_8x8_board_with_specials()
        cleared = {Position(3, 4), Position(3, 5)}
        triggered = svc.find_triggered_special_gems(board, cleared)
        assert triggered == []

    def test_empty_cleared_set(self, service: SpecialGemsService) -> None:
        board = _make_8x8_board_with_specials()
        triggered = service.find_triggered_special_gems(board, set())
        assert triggered == []

    def test_out_of_bounds_positions_ignored(self, service: SpecialGemsService) -> None:
        """Positions outside the board in cleared_positions should be skipped."""
        board = _make_8x8_board_with_specials()
        cleared = {Position(10, 10), Position(3, 4)}
        triggered = service.find_triggered_special_gems(board, cleared)
        assert Position(3, 4) in triggered


# ==================================================================
# 9. Edge cases and configuration
# ==================================================================


class TestEdgeCases:
    """Additional edge case tests."""

    def test_small_board(
        self,
        logger: MockLogService,
        errors: MockErrorService,
        scoring: MockScoringService,
    ) -> None:
        """Test with a 3x3 board."""
        config = MockConfigService(
            {
                "game.board_width": 3,
                "game.board_height": 3,
            }
        )
        svc = SpecialGemsService(
            config=config, logger=logger, errors=errors, scoring_service=scoring
        )
        data = [
            [1, 1, 1],
            [1, -3, 1],  # RADIAL_BOMB at center
            [1, 1, 1],
        ]
        board = _make_board(data)
        effect = svc.calculate_effect(board, Position(1, 1))

        # Radial bomb radius=1 at center of 3x3 = entire board (9).
        assert len(effect.affected_positions) == 9

    def test_chromatic_orb_no_matching_color(self, service: SpecialGemsService) -> None:
        """Chromatic orb targeting a color not present on board."""
        data = [[1] * 8 for _ in range(8)]
        data[3][4] = -4
        board = _make_board(data)
        # Target BLUE, but board has only RED.
        effect = service.calculate_effect(
            board, Position(3, 4), target_color=GemType.BLUE
        )
        # Only the orb itself is affected.
        assert len(effect.affected_positions) == 1
        assert Position(3, 4) in effect.affected_positions

    def test_line_blast_chain_reaction_disabled(
        self,
        logger: MockLogService,
        errors: MockErrorService,
        scoring: MockScoringService,
    ) -> None:
        """Chain reactions disabled means no triggered specials."""
        config = MockConfigService({"special_gems.chain_reaction_enabled": False})
        svc = SpecialGemsService(
            config=config, logger=logger, errors=errors, scoring_service=scoring
        )
        board = _make_8x8_board_with_specials()
        effect = svc.calculate_effect(board, Position(3, 4))  # LBH
        assert effect.triggers_special_gems == []

    def test_custom_radial_bomb_radius(
        self,
        logger: MockLogService,
        errors: MockErrorService,
        scoring: MockScoringService,
    ) -> None:
        """Custom radial bomb radius from config."""
        config = MockConfigService({"special_gems.radial_bomb_radius": 2})
        svc = SpecialGemsService(
            config=config, logger=logger, errors=errors, scoring_service=scoring
        )
        data = [[1] * 8 for _ in range(8)]
        data[4][4] = -3
        board = _make_board(data)
        effect = svc.calculate_effect(board, Position(4, 4))

        # Radius=2 at (4,4) => 5x5 = 25 positions.
        assert len(effect.affected_positions) == 25

    def test_custom_mega_bomb_radius(
        self,
        logger: MockLogService,
        errors: MockErrorService,
        scoring: MockScoringService,
    ) -> None:
        """Custom mega bomb radius from config."""
        config = MockConfigService({"special_gems.mega_bomb_radius": 3})
        svc = SpecialGemsService(
            config=config, logger=logger, errors=errors, scoring_service=scoring
        )
        data = [[1] * 8 for _ in range(8)]
        data[4][4] = -3
        data[4][5] = -3
        board = _make_board(data)
        effect = svc.calculate_fusion_effect(board, Position(4, 4), Position(4, 5))

        assert effect.fusion_type == FusionType.MEGA_BOMB
        # Center=(4,4), radius=3 => 7x7. But clipped to 8x8 board.
        # Rows 1..7, Cols 1..7 = 7x7 = 49 positions. But actually:
        # Rows: max(0,4-3)=1 to min(7,4+3)=7 => 7 rows
        # Cols: max(0,4-3)=1 to min(7,4+3)=7 => 7 cols
        # = 49 positions.
        assert len(effect.affected_positions) == 49

    def test_custom_triple_line_count(
        self,
        logger: MockLogService,
        errors: MockErrorService,
        scoring: MockScoringService,
    ) -> None:
        """Custom triple line count from config."""
        config = MockConfigService({"special_gems.triple_line_count": 5})
        svc = SpecialGemsService(
            config=config, logger=logger, errors=errors, scoring_service=scoring
        )
        data = [[1] * 8 for _ in range(8)]
        data[4][4] = -1  # LBH
        data[4][5] = -3  # RADIAL_BOMB
        board = _make_board(data)
        effect = svc.calculate_fusion_effect(board, Position(4, 4), Position(4, 5))

        assert effect.fusion_type == FusionType.TRIPLE_LINE
        # Center row = 4, half = 5//2 = 2 => rows 2..6 = 5 rows.
        # 5 rows x 8 cols = 40.
        assert len(effect.affected_positions) == 40

    def test_apply_effect_returns_new_board_state(
        self, service: SpecialGemsService
    ) -> None:
        """Returned board is a new object, not the same reference."""
        board = _make_8x8_board_with_specials()
        effect = service.calculate_effect(board, Position(3, 4))
        new_board, _ = service.apply_effect(board, effect)
        assert new_board is not board

    def test_find_center_even_positions(self, service: SpecialGemsService) -> None:
        """Test _find_center for 4-match (even count)."""
        group = _match_group([(0, 0), (0, 1), (0, 2), (0, 3)], is_horizontal=True)
        result = service.get_special_gem_for_match(_match_result([group]))
        assert result is not None
        _, pos = result
        # Sorted: [(0,0),(0,1),(0,2),(0,3)], index 4//2 = 2 => (0,2).
        assert pos == Position(0, 2)

    def test_find_center_odd_positions(self, service: SpecialGemsService) -> None:
        """Test _find_center for 5-match (odd count)."""
        group = _match_group([(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)])
        result = service.get_special_gem_for_match(_match_result([group]))
        assert result is not None
        _, pos = result
        # Sorted: [(0,0)...(0,4)], index 5//2 = 2 => (0,2).
        assert pos == Position(0, 2)

    def test_fusion_board_clear_on_small_board(
        self,
        logger: MockLogService,
        errors: MockErrorService,
        scoring: MockScoringService,
    ) -> None:
        """Board clear on a 4x4 board."""
        config = MockConfigService(
            {
                "game.board_width": 4,
                "game.board_height": 4,
            }
        )
        svc = SpecialGemsService(
            config=config, logger=logger, errors=errors, scoring_service=scoring
        )
        data = [
            [1, 1, 1, 1],
            [1, -4, -4, 1],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
        ]
        board = _make_board(data)
        effect = svc.calculate_fusion_effect(board, Position(1, 1), Position(1, 2))

        assert effect.fusion_type == FusionType.BOARD_CLEAR
        assert len(effect.affected_positions) == 16

    def test_all_6_standard_colors_are_valid_targets(
        self, service: SpecialGemsService
    ) -> None:
        """Every standard color should be accepted as target_color."""
        data = [[1] * 8 for _ in range(8)]
        data[0][0] = -4  # CHROMATIC_ORB

        for gem_type in [
            GemType.RED,
            GemType.BLUE,
            GemType.GREEN,
            GemType.YELLOW,
            GemType.PURPLE,
            GemType.ORANGE,
        ]:
            board = _make_board(data)
            effect = service.calculate_effect(
                board, Position(0, 0), target_color=gem_type
            )
            assert effect.gem_type == GemType.CHROMATIC_ORB


# ==================================================================
# 10. SPECIAL_GEM_TYPES constant
# ==================================================================


class TestSpecialGemTypesConstant:
    """Tests for the SPECIAL_GEM_TYPES constant."""

    def test_contains_all_special_types(self) -> None:
        assert GemType.LINE_BLAST_H in SPECIAL_GEM_TYPES
        assert GemType.LINE_BLAST_V in SPECIAL_GEM_TYPES
        assert GemType.RADIAL_BOMB in SPECIAL_GEM_TYPES
        assert GemType.CHROMATIC_ORB in SPECIAL_GEM_TYPES

    def test_does_not_contain_standard_types(self) -> None:
        assert GemType.RED not in SPECIAL_GEM_TYPES
        assert GemType.EMPTY not in SPECIAL_GEM_TYPES

    def test_exactly_four_types(self) -> None:
        assert len(SPECIAL_GEM_TYPES) == 4
