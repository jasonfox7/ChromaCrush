"""Unit tests for API adapters.

Tests the ResponseAdapter and BotHintGenerator, which are presentation-layer
adapters with no external dependencies (pure functions over data).
"""

from __future__ import annotations

import pytest

from src.modules.api.adapters.bot_hints import (
    BoardAnalysis,
    BotHintGenerator,
    MatchBotHints,
    RankedMove,
    StrategicContext,
    ValidMoveHint,
)
from src.modules.api.adapters.response import ResponseAdapter

# ---------------------------------------------------------------------------
# ResponseAdapter Tests
# ---------------------------------------------------------------------------


class TestResponseAdapter:
    """Tests for the standard API response envelope adapter."""

    @pytest.fixture
    def adapter(self) -> ResponseAdapter:
        return ResponseAdapter()

    def test_success_returns_correct_envelope_structure(
        self,
        adapter: ResponseAdapter,
    ) -> None:
        """success() produces the standard envelope with success=True."""
        result = adapter.success(
            data={"player_id": "abc"},
            correlation_id="cc_test_id",
        )

        assert result["success"] is True
        assert result["data"] == {"player_id": "abc"}
        assert result["error"] is None
        assert result["meta"]["correlation_id"] == "cc_test_id"

    def test_success_meta_includes_timestamp(
        self,
        adapter: ResponseAdapter,
    ) -> None:
        """success() meta includes a valid ISO timestamp."""
        result = adapter.success(data={}, correlation_id="cc_1")

        assert "timestamp" in result["meta"]
        # Should be a valid ISO 8601 string
        assert "T" in result["meta"]["timestamp"]

    def test_success_meta_includes_version(
        self,
        adapter: ResponseAdapter,
    ) -> None:
        """success() meta includes a version field."""
        result = adapter.success(data={}, correlation_id="cc_1")

        assert "version" in result["meta"]

    def test_success_with_none_data(
        self,
        adapter: ResponseAdapter,
    ) -> None:
        """success() accepts None as data."""
        result = adapter.success(data=None, correlation_id="cc_1")
        assert result["success"] is True
        assert result["data"] is None

    def test_success_with_complex_data(
        self,
        adapter: ResponseAdapter,
    ) -> None:
        """success() serialises complex nested data."""
        result = adapter.success(
            data={"items": [{"id": 1}, {"id": 2}], "total": 2},
            correlation_id="cc_1",
        )
        assert result["data"]["items"][0]["id"] == 1
        assert result["data"]["total"] == 2

    def test_error_returns_correct_envelope_structure(
        self,
        adapter: ResponseAdapter,
    ) -> None:
        """error() produces the standard envelope with success=False."""
        result = adapter.error(
            code="VALIDATION_INVALID",
            message="Bad input",
            correlation_id="cc_err_id",
        )

        assert result["success"] is False
        assert result["data"] is None
        assert result["error"]["code"] == "VALIDATION_INVALID"
        assert result["error"]["message"] == "Bad input"
        assert result["meta"]["correlation_id"] == "cc_err_id"

    def test_error_with_details(
        self,
        adapter: ResponseAdapter,
    ) -> None:
        """error() includes details when provided."""
        result = adapter.error(
            code="VALIDATION_FIELD",
            message="Field invalid",
            correlation_id="cc_1",
            details={"field": "username", "reason": "too short"},
        )

        assert result["error"]["details"]["field"] == "username"
        assert result["error"]["details"]["reason"] == "too short"

    def test_error_without_details(
        self,
        adapter: ResponseAdapter,
    ) -> None:
        """error() sets details to None when not provided."""
        result = adapter.error(
            code="AUTH_TOKEN_INVALID",
            message="Token expired",
            correlation_id="cc_1",
        )

        assert result["error"]["details"] is None

    def test_correlation_id_is_included_in_meta(
        self,
        adapter: ResponseAdapter,
    ) -> None:
        """Both success and error responses include the correlation_id in meta."""
        success_result = adapter.success(data={}, correlation_id="corr-123")
        error_result = adapter.error(
            code="ERR",
            message="err",
            correlation_id="corr-456",
        )

        assert success_result["meta"]["correlation_id"] == "corr-123"
        assert error_result["meta"]["correlation_id"] == "corr-456"


# ---------------------------------------------------------------------------
# BotHintGenerator Tests
# ---------------------------------------------------------------------------


class TestBotHintGenerator:
    """Tests for bot strategic hint generation."""

    @pytest.fixture
    def generator(self) -> BotHintGenerator:
        return BotHintGenerator()

    @pytest.fixture
    def simple_board(self) -> list[list[int]]:
        """An 8x8 board with known gem distribution."""
        return [
            [1, 2, 3, 4, 5, 6, 1, 2],
            [2, 3, 4, 5, 6, 1, 2, 3],
            [3, 4, 5, 6, 1, 2, 3, 4],
            [4, 5, 6, 1, 2, 3, 4, 5],
            [5, 6, 1, 2, 3, 4, 5, 6],
            [6, 1, 2, 3, 4, 5, 6, 1],
            [1, 2, 3, 4, 5, 6, 1, 2],
            [2, 3, 4, 5, 6, 1, 2, 3],
        ]

    @pytest.fixture
    def sample_moves(self) -> list[ValidMoveHint]:
        """A set of sample valid moves with varying estimated scores."""
        return [
            ValidMoveHint(
                from_row=0, from_col=0, to_row=0, to_col=1, estimated_score=100
            ),
            ValidMoveHint(
                from_row=1, from_col=1, to_row=1, to_col=2, estimated_score=200
            ),
            ValidMoveHint(
                from_row=2, from_col=2, to_row=2, to_col=3, estimated_score=50
            ),
        ]

    def test_generate_match_hints_returns_correct_structure(
        self,
        generator: BotHintGenerator,
        simple_board: list[list[int]],
        sample_moves: list[ValidMoveHint],
    ) -> None:
        """generate_match_hints returns MatchBotHints with all three sections."""
        hints = generator.generate_match_hints(
            board=simple_board,
            valid_moves=sample_moves,
            my_score=500,
            opponent_score=400,
            turns_remaining=15,
        )

        assert isinstance(hints, MatchBotHints)
        assert isinstance(hints.board_analysis, BoardAnalysis)
        assert isinstance(hints.strategic_context, StrategicContext)
        assert isinstance(hints.best_moves, list)

    def test_board_analysis_counts_gem_distribution(
        self,
        generator: BotHintGenerator,
    ) -> None:
        """Board analysis counts each gem type in the board."""
        board = [
            [1, 1, 1, 2],
            [2, 2, 3, 3],
        ]

        analysis = generator._analyze_board(board)

        assert analysis.gem_distribution["1"] == 3
        assert analysis.gem_distribution["2"] == 3
        assert analysis.gem_distribution["3"] == 2

    def test_board_analysis_counts_special_gems(
        self,
        generator: BotHintGenerator,
    ) -> None:
        """Board analysis counts negative gem values as special gems."""
        board = [
            [-1, 1, 2, 3],
            [4, -2, 5, 6],
        ]

        analysis = generator._analyze_board(board)

        assert analysis.special_gems_available == 2

    def test_board_analysis_volatility_stable(
        self,
        generator: BotHintGenerator,
    ) -> None:
        """Board with few chain opportunities is 'stable'."""
        # Board with no adjacent same-colour pairs
        board = [
            [1, 2, 1, 2],
            [2, 1, 2, 1],
        ]

        analysis = generator._analyze_board(board)
        assert analysis.board_volatility == "stable"

    def test_board_analysis_volatility_volatile(
        self,
        generator: BotHintGenerator,
    ) -> None:
        """Board with many chain opportunities is 'volatile'."""
        # Board with many adjacent same-colour pairs
        board = [
            [1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1, 1],
        ]

        analysis = generator._analyze_board(board)
        assert analysis.board_volatility == "volatile"

    def test_move_ranking_sorts_by_expected_score(
        self,
        generator: BotHintGenerator,
        simple_board: list[list[int]],
        sample_moves: list[ValidMoveHint],
    ) -> None:
        """Ranked moves are sorted by expected_score descending."""
        ranked = generator._rank_moves(simple_board, sample_moves)

        for i in range(len(ranked) - 1):
            assert ranked[i].expected_score >= ranked[i + 1].expected_score

    def test_move_ranking_returns_ranked_move_instances(
        self,
        generator: BotHintGenerator,
        simple_board: list[list[int]],
        sample_moves: list[ValidMoveHint],
    ) -> None:
        """Each element in the ranked list is a RankedMove."""
        ranked = generator._rank_moves(simple_board, sample_moves)

        for rm in ranked:
            assert isinstance(rm, RankedMove)
            assert rm.cascade_potential in ("low", "medium", "high")
            assert 0.0 <= rm.special_gem_chance <= 1.0

    def test_best_moves_limited_to_top_five(
        self,
        generator: BotHintGenerator,
    ) -> None:
        """generate_match_hints caps best_moves at 5."""
        board = [[1, 2, 3, 4]] * 4
        moves = [
            ValidMoveHint(
                from_row=0, from_col=i, to_row=0, to_col=i + 1, estimated_score=i * 10
            )
            for i in range(3)  # Only 3 moves available -- should be fine
        ] * 3  # Repeat to get > 5 total

        hints = generator.generate_match_hints(
            board=board,
            valid_moves=moves,
            my_score=0,
            opponent_score=0,
            turns_remaining=20,
        )

        assert len(hints.best_moves) <= 5

    def test_strategic_context_large_deficit_late_game_aggressive(
        self,
        generator: BotHintGenerator,
        simple_board: list[list[int]],
    ) -> None:
        """Large deficit in late game recommends aggressive strategy."""
        hints = generator.generate_match_hints(
            board=simple_board,
            valid_moves=[],
            my_score=0,
            opponent_score=200,
            turns_remaining=3,
        )

        assert hints.strategic_context.recommended_strategy == "aggressive"
        assert hints.strategic_context.risk_tolerance == "high"
        assert hints.strategic_context.game_phase == "late"

    def test_strategic_context_large_lead_defensive(
        self,
        generator: BotHintGenerator,
        simple_board: list[list[int]],
    ) -> None:
        """Large lead recommends defensive strategy."""
        hints = generator.generate_match_hints(
            board=simple_board,
            valid_moves=[],
            my_score=500,
            opponent_score=100,
            turns_remaining=10,
        )

        assert hints.strategic_context.recommended_strategy == "defensive"
        assert hints.strategic_context.risk_tolerance == "low"

    def test_strategic_context_even_score_balanced(
        self,
        generator: BotHintGenerator,
        simple_board: list[list[int]],
    ) -> None:
        """Even scores recommend balanced strategy."""
        hints = generator.generate_match_hints(
            board=simple_board,
            valid_moves=[],
            my_score=300,
            opponent_score=300,
            turns_remaining=10,
        )

        assert hints.strategic_context.recommended_strategy == "balanced"
        assert hints.strategic_context.risk_tolerance == "medium"

    def test_strategic_context_early_game_phase(
        self,
        generator: BotHintGenerator,
        simple_board: list[list[int]],
    ) -> None:
        """High turns remaining gives early game phase."""
        hints = generator.generate_match_hints(
            board=simple_board,
            valid_moves=[],
            my_score=0,
            opponent_score=0,
            turns_remaining=25,
        )

        assert hints.strategic_context.game_phase == "early"

    def test_strategic_context_none_turns_remaining_mid_phase(
        self,
        generator: BotHintGenerator,
        simple_board: list[list[int]],
    ) -> None:
        """None turns_remaining defaults to 'mid' game phase."""
        hints = generator.generate_match_hints(
            board=simple_board,
            valid_moves=[],
            my_score=0,
            opponent_score=0,
            turns_remaining=None,
        )

        assert hints.strategic_context.game_phase == "mid"

    def test_score_differential_calculated_correctly(
        self,
        generator: BotHintGenerator,
        simple_board: list[list[int]],
    ) -> None:
        """Strategic context has correct score_differential."""
        hints = generator.generate_match_hints(
            board=simple_board,
            valid_moves=[],
            my_score=750,
            opponent_score=500,
            turns_remaining=10,
        )

        assert hints.strategic_context.score_differential == 250

    def test_empty_valid_moves_returns_empty_best_moves(
        self,
        generator: BotHintGenerator,
        simple_board: list[list[int]],
    ) -> None:
        """When no valid moves provided, best_moves is empty."""
        hints = generator.generate_match_hints(
            board=simple_board,
            valid_moves=[],
            my_score=0,
            opponent_score=0,
            turns_remaining=10,
        )

        assert hints.best_moves == []
