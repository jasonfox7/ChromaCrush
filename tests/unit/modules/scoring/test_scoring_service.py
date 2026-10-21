"""Unit tests for ScoringService -- pure, synchronous score calculation.

All tests inject mocks for ConfigProtocol, LoggerProtocol, and
ErrorServiceProtocol via ``__init__``. No global state is used.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.errors import AppError
from src.core.types.board import BoardState, MatchGroup, MatchResult
from src.core.types.game import GemType, Move, Position
from src.modules.board.types import CascadeStep, MoveProcessingResult
from src.modules.scoring.service import ScoringService
from src.modules.scoring.types import (
    CascadeStepScore,
    MatchGroupScore,
    MatchScore,
    MoveScore,
    SpecialGemBonus,
)
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
) -> ScoringService:
    return ScoringService(config=config, logger=logger, errors=errors)


# ------------------------------------------------------------------
# Helpers for creating test data
# ------------------------------------------------------------------


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
    special_type: GemType | None = None,
    special_pos: Position | None = None,
) -> MatchResult:
    """Build a MatchResult from match groups."""
    all_positions: set[Position] = set()
    for mg in groups:
        all_positions.update(mg.positions)
    return MatchResult(
        matches=tuple(groups),
        total_gems_matched=len(all_positions),
        creates_special_gem=creates_special,
        special_gem_type=special_type,
        special_gem_position=special_pos,
    )


def _board() -> BoardState:
    """Create a minimal 8x8 board for testing."""
    return BoardState(grid=np.zeros((8, 8), dtype=np.int8))


def _cascade_step(
    step_number: int,
    match_res: MatchResult,
) -> CascadeStep:
    """Build a CascadeStep with minimal fields."""
    board = _board()
    step = CascadeStep(
        step_number=step_number,
        matches=match_res,
        board_after_fill=board,
    )
    return step


def _move_processing_result(
    cascades: list[CascadeStep],
    was_valid: bool = True,
    total_gems: int = 0,
) -> MoveProcessingResult:
    """Build a MoveProcessingResult with minimal fields."""
    board = _board()
    return MoveProcessingResult(
        initial_board=board,
        final_board=board,
        move=Move(Position(0, 0), Position(0, 1), timestamp_ms=0),
        was_valid_match=was_valid,
        cascades=cascades,
        total_matches=len(cascades),
        total_gems_cleared=total_gems,
        chain_count=len(cascades),
    )


# ==================================================================
# 1. Match Score Calculation Tests (~8 tests)
# ==================================================================


class TestCalculateMatchScore:
    def test_single_3_match(self, service: ScoringService) -> None:
        """A 3-gem match at chain step 1: base_points(50) * 3 * 1.0x = 150."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])

        score = service.calculate_match_score(mr)

        assert score.total_points == 150
        assert score.base_points == 150
        assert score.chain_multiplier == 1.0
        assert score.chain_step == 1
        assert len(score.match_breakdown) == 1
        assert score.match_breakdown[0].base_points == 150
        assert score.match_breakdown[0].length_multiplier == 1.0
        assert score.match_breakdown[0].subtotal == 150
        assert score.special_gem_creation_bonus == 0

    def test_4_match_length_multiplier(self, service: ScoringService) -> None:
        """A 4-gem match: 50 * 4 * 2.0x = 400."""
        mg = _match_group([(0, 0), (0, 1), (0, 2), (0, 3)])
        mr = _match_result([mg])

        score = service.calculate_match_score(mr)

        assert score.total_points == 400
        assert score.match_breakdown[0].base_points == 200  # 50 * 4
        assert score.match_breakdown[0].length_multiplier == 2.0
        assert score.match_breakdown[0].subtotal == 400
        assert score.match_breakdown[0].length_bonus_points == 200  # 200 * (2.0 - 1.0)

    def test_5_match_length_multiplier(self, service: ScoringService) -> None:
        """A 5-gem match: 50 * 5 * 3.0x = 750."""
        mg = _match_group([(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)])
        mr = _match_result([mg])

        score = service.calculate_match_score(mr)

        assert score.total_points == 750
        assert score.match_breakdown[0].subtotal == 750

    def test_multiple_match_groups(self, service: ScoringService) -> None:
        """Two 3-gem matches: (150 + 150) * 1.0x = 300."""
        mg1 = _match_group([(0, 0), (0, 1), (0, 2)], gem_type=GemType.RED)
        mg2 = _match_group([(2, 0), (2, 1), (2, 2)], gem_type=GemType.BLUE)
        mr = _match_result([mg1, mg2])

        score = service.calculate_match_score(mr)

        assert score.total_points == 300
        assert len(score.match_breakdown) == 2
        assert score.match_breakdown[0].subtotal == 150
        assert score.match_breakdown[1].subtotal == 150

    def test_chain_step_2_multiplier(self, service: ScoringService) -> None:
        """Chain step 2 applies 1.5x: 150 * 1.5 = 225."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])

        score = service.calculate_match_score(mr, chain_step=2)

        assert score.total_points == 225  # int(150 * 1.5)
        assert score.chain_multiplier == 1.5
        assert score.chain_step == 2

    def test_chain_step_5_plus_capped(self, service: ScoringService) -> None:
        """Chain step 5+ is capped at 3.0x: 150 * 3.0 = 450."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])

        score = service.calculate_match_score(mr, chain_step=5)
        assert score.total_points == 450
        assert score.chain_multiplier == 3.0

        # Chain step 10 should also be capped at 3.0x.
        score_10 = service.calculate_match_score(mr, chain_step=10)
        assert score_10.total_points == 450
        assert score_10.chain_multiplier == 3.0

    def test_special_gem_creation_bonus(self, service: ScoringService) -> None:
        """Creating a special gem adds 100 bonus: 150 + 100 = 250."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result(
            [mg],
            creates_special=True,
            special_type=GemType.RADIAL_BOMB,
            special_pos=Position(0, 1),
        )

        score = service.calculate_match_score(mr)

        assert score.total_points == 250  # 150 + 100
        assert score.special_gem_creation_bonus == 100

    def test_empty_matches_raises_error(self, service: ScoringService) -> None:
        """Empty match result raises VALIDATION_INVALID_INPUT."""
        mr = MatchResult(
            matches=(),
            total_gems_matched=0,
            creates_special_gem=False,
        )

        with pytest.raises(AppError) as exc_info:
            service.calculate_match_score(mr)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_chain_step_zero_raises_error(self, service: ScoringService) -> None:
        """Chain step 0 raises VALIDATION_INVALID_INPUT."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])

        with pytest.raises(AppError) as exc_info:
            service.calculate_match_score(mr, chain_step=0)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_chain_step_negative_raises_error(self, service: ScoringService) -> None:
        """Negative chain step raises VALIDATION_INVALID_INPUT."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])

        with pytest.raises(AppError) as exc_info:
            service.calculate_match_score(mr, chain_step=-1)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ==================================================================
# 2. Move Score Calculation Tests (~5 tests)
# ==================================================================


class TestCalculateMoveScore:
    def test_single_cascade_step(self, service: ScoringService) -> None:
        """A move with one cascade step, 3-match at chain 1 = 150 pts."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])
        cascade = _cascade_step(1, mr)
        move_result = _move_processing_result([cascade], total_gems=3)

        score = service.calculate_move_score(move_result)

        assert score.total_points == 150
        assert score.chain_count == 1
        assert score.total_gems_cleared == 3
        assert score.highest_chain_multiplier == 1.0
        assert len(score.cascade_scores) == 1
        assert score.cascade_scores[0].step_number == 1

    def test_triple_cascade(self, service: ScoringService) -> None:
        """Three cascade steps with chain 1, 2, 3 multipliers."""
        mg1 = _match_group([(0, 0), (0, 1), (0, 2)])
        mr1 = _match_result([mg1])
        mg2 = _match_group([(1, 0), (1, 1), (1, 2)])
        mr2 = _match_result([mg2])
        mg3 = _match_group([(2, 0), (2, 1), (2, 2)])
        mr3 = _match_result([mg3])

        cascades = [
            _cascade_step(1, mr1),
            _cascade_step(2, mr2),
            _cascade_step(3, mr3),
        ]
        move_result = _move_processing_result(cascades, total_gems=9)

        score = service.calculate_move_score(move_result)

        # Chain 1: 150 * 1.0 = 150
        # Chain 2: 150 * 1.5 = 225
        # Chain 3: 150 * 2.0 = 300
        assert score.total_points == 150 + 225 + 300  # 675
        assert score.chain_count == 3
        assert score.total_gems_cleared == 9
        assert score.highest_chain_multiplier == 2.0

    def test_invalid_move_raises_error(self, service: ScoringService) -> None:
        """was_valid_match=False raises VALIDATION_INVALID_INPUT."""
        move_result = _move_processing_result([], was_valid=False)

        with pytest.raises(AppError) as exc_info:
            service.calculate_move_score(move_result)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_total_gems_cleared_accumulated(self, service: ScoringService) -> None:
        """Total gems cleared is summed across cascade steps."""
        mg1 = _match_group([(0, 0), (0, 1), (0, 2)])  # 3 gems
        mr1 = _match_result([mg1])
        mg2 = _match_group([(1, 0), (1, 1), (1, 2), (1, 3)])  # 4 gems
        mr2 = _match_result([mg2])

        cascades = [_cascade_step(1, mr1), _cascade_step(2, mr2)]
        move_result = _move_processing_result(cascades, total_gems=7)

        score = service.calculate_move_score(move_result)

        assert score.total_gems_cleared == 7  # 3 + 4

    def test_highest_chain_multiplier_tracked(self, service: ScoringService) -> None:
        """The highest chain multiplier is tracked across cascade steps."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])

        cascades = [
            _cascade_step(1, mr),
            _cascade_step(2, mr),
            _cascade_step(3, mr),
            _cascade_step(4, mr),
        ]
        move_result = _move_processing_result(cascades, total_gems=12)

        score = service.calculate_move_score(move_result)

        # Chain 4 = 2.5x.
        assert score.highest_chain_multiplier == 2.5

    def test_special_gems_created_counted(self, service: ScoringService) -> None:
        """Special gems created during cascades are counted."""
        mg1 = _match_group([(0, 0), (0, 1), (0, 2)])
        mr1 = _match_result([mg1])
        mg2 = _match_group([(1, 0), (1, 1), (1, 2), (1, 3)])
        mr2 = _match_result(
            [mg2],
            creates_special=True,
            special_type=GemType.LINE_BLAST_H,
            special_pos=Position(1, 1),
        )

        cascades = [_cascade_step(1, mr1), _cascade_step(2, mr2)]
        move_result = _move_processing_result(cascades, total_gems=7)

        score = service.calculate_move_score(move_result)

        assert score.special_gems_created == 1


# ==================================================================
# 3. Special Gem Bonus Tests (~5 tests)
# ==================================================================


class TestCalculateSpecialGemBonus:
    def test_line_blast_h(self, service: ScoringService) -> None:
        """LINE_BLAST_H: 50 + 8 * 25 = 250."""
        bonus = service.calculate_special_gem_bonus(GemType.LINE_BLAST_H, 8)

        assert bonus.gem_type == GemType.LINE_BLAST_H
        assert bonus.base_activation_bonus == 50
        assert bonus.gems_affected == 8
        assert bonus.per_gem_bonus == 25
        assert bonus.total_bonus == 250

    def test_line_blast_v(self, service: ScoringService) -> None:
        """LINE_BLAST_V uses same config as LINE_BLAST_H: 50 + 8 * 25 = 250."""
        bonus = service.calculate_special_gem_bonus(GemType.LINE_BLAST_V, 8)

        assert bonus.gem_type == GemType.LINE_BLAST_V
        assert bonus.total_bonus == 250

    def test_radial_bomb(self, service: ScoringService) -> None:
        """RADIAL_BOMB: 100 + 9 * 30 = 370."""
        bonus = service.calculate_special_gem_bonus(GemType.RADIAL_BOMB, 9)

        assert bonus.gem_type == GemType.RADIAL_BOMB
        assert bonus.base_activation_bonus == 100
        assert bonus.gems_affected == 9
        assert bonus.per_gem_bonus == 30
        assert bonus.total_bonus == 370

    def test_chromatic_orb(self, service: ScoringService) -> None:
        """CHROMATIC_ORB: 200 + 12 * 40 = 680."""
        bonus = service.calculate_special_gem_bonus(GemType.CHROMATIC_ORB, 12)

        assert bonus.gem_type == GemType.CHROMATIC_ORB
        assert bonus.base_activation_bonus == 200
        assert bonus.gems_affected == 12
        assert bonus.per_gem_bonus == 40
        assert bonus.total_bonus == 680

    def test_non_special_gem_raises_error(self, service: ScoringService) -> None:
        """Standard gem type raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            service.calculate_special_gem_bonus(GemType.RED, 5)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_gems_affected_zero_gives_base_only(self, service: ScoringService) -> None:
        """gems_affected=0 returns just the base activation bonus."""
        bonus = service.calculate_special_gem_bonus(GemType.LINE_BLAST_H, 0)

        assert bonus.total_bonus == 50  # just base, no per-gem
        assert bonus.gems_affected == 0

    def test_negative_gems_affected_raises_error(self, service: ScoringService) -> None:
        """Negative gems_affected raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            service.calculate_special_gem_bonus(GemType.RADIAL_BOMB, -1)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_empty_gem_type_raises_error(self, service: ScoringService) -> None:
        """EMPTY gem type raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            service.calculate_special_gem_bonus(GemType.EMPTY, 5)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ==================================================================
# 4. Multiplier Lookup Tests (~6 tests)
# ==================================================================


class TestMultiplierLookups:
    def test_chain_multiplier_step_1(self, service: ScoringService) -> None:
        """Chain step 1 = 1.0x."""
        assert service.get_chain_multiplier(1) == 1.0

    def test_chain_multiplier_step_2(self, service: ScoringService) -> None:
        """Chain step 2 = 1.5x."""
        assert service.get_chain_multiplier(2) == 1.5

    def test_chain_multiplier_step_3(self, service: ScoringService) -> None:
        """Chain step 3 = 2.0x."""
        assert service.get_chain_multiplier(3) == 2.0

    def test_chain_multiplier_step_4(self, service: ScoringService) -> None:
        """Chain step 4 = 2.5x."""
        assert service.get_chain_multiplier(4) == 2.5

    def test_chain_multiplier_step_5(self, service: ScoringService) -> None:
        """Chain step 5 = 3.0x."""
        assert service.get_chain_multiplier(5) == 3.0

    def test_chain_multiplier_step_beyond_cap(self, service: ScoringService) -> None:
        """Chain step > 5 is capped at 3.0x."""
        assert service.get_chain_multiplier(6) == 3.0
        assert service.get_chain_multiplier(100) == 3.0

    def test_chain_multiplier_invalid_raises(self, service: ScoringService) -> None:
        """Chain step < 1 raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            service.get_chain_multiplier(0)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_length_multiplier_3(self, service: ScoringService) -> None:
        """Match length 3 = 1.0x."""
        assert service.get_match_length_multiplier(3) == 1.0

    def test_length_multiplier_4(self, service: ScoringService) -> None:
        """Match length 4 = 2.0x."""
        assert service.get_match_length_multiplier(4) == 2.0

    def test_length_multiplier_5(self, service: ScoringService) -> None:
        """Match length 5 = 3.0x."""
        assert service.get_match_length_multiplier(5) == 3.0

    def test_length_multiplier_6(self, service: ScoringService) -> None:
        """Match length 6 = 4.0x."""
        assert service.get_match_length_multiplier(6) == 4.0

    def test_length_multiplier_7(self, service: ScoringService) -> None:
        """Match length 7 = 5.0x."""
        assert service.get_match_length_multiplier(7) == 5.0

    def test_length_multiplier_beyond_cap(self, service: ScoringService) -> None:
        """Match length > 7 is capped at 5.0x."""
        assert service.get_match_length_multiplier(8) == 5.0
        assert service.get_match_length_multiplier(20) == 5.0

    def test_length_multiplier_invalid_raises(self, service: ScoringService) -> None:
        """Match length < 3 raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            service.get_match_length_multiplier(2)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

        with pytest.raises(AppError):
            service.get_match_length_multiplier(0)


# ==================================================================
# 5. Configuration Tests (~3 tests)
# ==================================================================


class TestConfiguration:
    def test_custom_base_points(
        self, logger: MockLogService, errors: MockErrorService
    ) -> None:
        """Custom base_points value is used for calculations."""
        config = MockConfigService({"scoring.base_points": 100})
        svc = ScoringService(config=config, logger=logger, errors=errors)

        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])

        score = svc.calculate_match_score(mr)
        assert score.total_points == 300  # 100 * 3 * 1.0

    def test_custom_chain_multipliers(
        self, logger: MockLogService, errors: MockErrorService
    ) -> None:
        """Custom chain multipliers list is used."""
        config = MockConfigService(
            {
                "scoring.chain_multipliers": [1.0, 2.0, 4.0],
            }
        )
        svc = ScoringService(config=config, logger=logger, errors=errors)

        assert svc.get_chain_multiplier(1) == 1.0
        assert svc.get_chain_multiplier(2) == 2.0
        assert svc.get_chain_multiplier(3) == 4.0
        assert svc.get_chain_multiplier(4) == 4.0  # capped at last

    def test_custom_length_multipliers(
        self, logger: MockLogService, errors: MockErrorService
    ) -> None:
        """Custom length multipliers list is used."""
        config = MockConfigService(
            {
                "scoring.length_multipliers": [1.0, 1.5, 2.0],
            }
        )
        svc = ScoringService(config=config, logger=logger, errors=errors)

        assert svc.get_match_length_multiplier(3) == 1.0
        assert svc.get_match_length_multiplier(4) == 1.5
        assert svc.get_match_length_multiplier(5) == 2.0
        assert svc.get_match_length_multiplier(6) == 2.0  # capped at last

    def test_negative_base_points_falls_back_to_default(
        self, logger: MockLogService, errors: MockErrorService
    ) -> None:
        """Negative config values fall back to defaults with warning."""
        config = MockConfigService({"scoring.base_points": -10})
        svc = ScoringService(config=config, logger=logger, errors=errors)

        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])

        score = svc.calculate_match_score(mr)
        assert score.total_points == 150  # default 50 * 3 * 1.0

        # Verify warning was logged.
        logger.assert_logged("WARN", "scoring.config_invalid")

    def test_zero_base_points_falls_back_to_default(
        self, logger: MockLogService, errors: MockErrorService
    ) -> None:
        """Zero config values fall back to defaults with warning."""
        config = MockConfigService({"scoring.base_points": 0})
        svc = ScoringService(config=config, logger=logger, errors=errors)

        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])

        score = svc.calculate_match_score(mr)
        assert score.total_points == 150  # default 50 * 3 * 1.0

    def test_custom_special_gem_config(
        self, logger: MockLogService, errors: MockErrorService
    ) -> None:
        """Custom special gem bonus config values are used."""
        config = MockConfigService(
            {
                "scoring.line_blast_activation_bonus": 75,
                "scoring.line_blast_per_gem": 35,
            }
        )
        svc = ScoringService(config=config, logger=logger, errors=errors)

        bonus = svc.calculate_special_gem_bonus(GemType.LINE_BLAST_H, 4)
        assert bonus.base_activation_bonus == 75
        assert bonus.per_gem_bonus == 35
        assert bonus.total_bonus == 75 + 4 * 35  # 215


# ==================================================================
# 6. get_base_points Tests (~3 tests)
# ==================================================================


class TestGetBasePoints:
    def test_standard_gem_returns_base_points(self, service: ScoringService) -> None:
        """All standard gem types return the configured base points."""
        for gem_type in [
            GemType.RED,
            GemType.BLUE,
            GemType.GREEN,
            GemType.YELLOW,
            GemType.PURPLE,
            GemType.ORANGE,
        ]:
            assert service.get_base_points(gem_type) == 50

    def test_empty_gem_type_raises_error(self, service: ScoringService) -> None:
        """EMPTY gem type raises VALIDATION_INVALID_INPUT."""
        with pytest.raises(AppError) as exc_info:
            service.get_base_points(GemType.EMPTY)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    def test_special_gem_type_raises_error(self, service: ScoringService) -> None:
        """Special gem types raise VALIDATION_INVALID_INPUT."""
        for gem_type in [
            GemType.LINE_BLAST_H,
            GemType.LINE_BLAST_V,
            GemType.RADIAL_BOMB,
            GemType.CHROMATIC_ORB,
        ]:
            with pytest.raises(AppError) as exc_info:
                service.get_base_points(gem_type)
            assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ==================================================================
# 7. MoveScore.summary() Tests
# ==================================================================


class TestMoveScoreSummary:
    def test_summary_single_match(self, service: ScoringService) -> None:
        """Single match summary reads 'Single match! +N points'."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])
        cascade = _cascade_step(1, mr)
        move_result = _move_processing_result([cascade], total_gems=3)

        score = service.calculate_move_score(move_result)
        summary = score.summary()

        assert "Single match" in summary
        assert "+150 points" in summary

    def test_summary_double_chain(self, service: ScoringService) -> None:
        """Double chain summary reads 'Double chain! +N points'."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])
        cascades = [_cascade_step(1, mr), _cascade_step(2, mr)]
        move_result = _move_processing_result(cascades, total_gems=6)

        score = service.calculate_move_score(move_result)
        summary = score.summary()

        assert "Double chain" in summary

    def test_summary_triple_chain(self, service: ScoringService) -> None:
        """Triple chain summary reads 'Triple chain! +N points'."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])
        cascades = [_cascade_step(1, mr), _cascade_step(2, mr), _cascade_step(3, mr)]
        move_result = _move_processing_result(cascades, total_gems=9)

        score = service.calculate_move_score(move_result)
        summary = score.summary()

        assert "Triple chain" in summary

    def test_summary_with_special_gems(self, service: ScoringService) -> None:
        """Summary includes special gem creation count."""
        mg = _match_group([(0, 0), (0, 1), (0, 2), (0, 3)])
        mr = _match_result(
            [mg],
            creates_special=True,
            special_type=GemType.LINE_BLAST_H,
            special_pos=Position(0, 1),
        )
        cascade = _cascade_step(1, mr)
        move_result = _move_processing_result([cascade], total_gems=4)

        score = service.calculate_move_score(move_result)
        summary = score.summary()

        assert "special gem(s) created" in summary


# ==================================================================
# 8. Combined / Integration-like Tests
# ==================================================================


class TestCombinedScoring:
    def test_4_match_chain_2_with_special(self, service: ScoringService) -> None:
        """4-match at chain step 2 with special gem creation.

        Base: 50 * 4 = 200, length mult 2.0x = 400
        Chain 1.5x: int(400 * 1.5) = 600
        Special bonus: +100
        Total: 700
        """
        mg = _match_group([(0, 0), (0, 1), (0, 2), (0, 3)])
        mr = _match_result(
            [mg],
            creates_special=True,
            special_type=GemType.LINE_BLAST_H,
            special_pos=Position(0, 1),
        )

        score = service.calculate_match_score(mr, chain_step=2)

        assert score.total_points == 700
        assert score.base_points == 400
        assert score.chain_multiplier == 1.5
        assert score.special_gem_creation_bonus == 100

    def test_two_groups_different_lengths(self, service: ScoringService) -> None:
        """A 3-match and a 5-match in the same detection.

        3-match: 50*3*1.0 = 150
        5-match: 50*5*3.0 = 750
        Total base: 900
        Chain 1: 900 * 1.0 = 900
        """
        mg1 = _match_group([(0, 0), (0, 1), (0, 2)])
        mg2 = _match_group(
            [(2, 0), (2, 1), (2, 2), (2, 3), (2, 4)],
            gem_type=GemType.GREEN,
        )
        mr = _match_result([mg1, mg2])

        score = service.calculate_match_score(mr)

        assert score.match_breakdown[0].subtotal == 150
        assert score.match_breakdown[1].subtotal == 750
        assert score.total_points == 900

    def test_frozen_types_immutable(self, service: ScoringService) -> None:
        """All scoring types are frozen (immutable)."""
        mg = _match_group([(0, 0), (0, 1), (0, 2)])
        mr = _match_result([mg])

        score = service.calculate_match_score(mr)

        with pytest.raises(AttributeError):
            score.total_points = 999  # type: ignore[misc]

        bonus = service.calculate_special_gem_bonus(GemType.RADIAL_BOMB, 5)
        with pytest.raises(AttributeError):
            bonus.total_bonus = 999  # type: ignore[misc]
