"""Unit tests for the ELO calculation module.

Tests the pure synchronous ELO calculation functions against known
expected values for the standard ELO formula.
"""

from __future__ import annotations

from src.modules.player.elo import calculate_elo_change, calculate_expected_score


class TestCalculateExpectedScore:
    """Tests for ``calculate_expected_score``."""

    def test_equal_ratings(self) -> None:
        """Equal ratings produce expected score of 0.5."""
        result = calculate_expected_score(1000, 1000)
        assert result == 0.5

    def test_higher_rated_has_higher_expected(self) -> None:
        """Higher-rated player has expected score > 0.5."""
        result = calculate_expected_score(1200, 1000)
        assert result > 0.5

    def test_lower_rated_has_lower_expected(self) -> None:
        """Lower-rated player has expected score < 0.5."""
        result = calculate_expected_score(1000, 1200)
        assert result < 0.5

    def test_expected_scores_sum_to_one(self) -> None:
        """Expected scores for both players sum to 1.0."""
        e_a = calculate_expected_score(1200, 1000)
        e_b = calculate_expected_score(1000, 1200)
        assert abs(e_a + e_b - 1.0) < 1e-10

    def test_large_rating_gap(self) -> None:
        """Very high-rated player has expected score near 1.0."""
        result = calculate_expected_score(2000, 1000)
        assert result > 0.99


class TestCalculateEloChange:
    """Tests for ``calculate_elo_change``."""

    def test_equal_ratings_win(self) -> None:
        """Equal ratings: winner gets +16, loser gets -16 (k=32)."""
        winner_change, loser_change = calculate_elo_change(
            winner_rating=1000,
            loser_rating=1000,
            k_factor=32,
            is_draw=False,
        )
        assert winner_change == 16
        assert loser_change == -16

    def test_equal_ratings_draw(self) -> None:
        """Equal ratings draw: both get 0 change."""
        winner_change, loser_change = calculate_elo_change(
            winner_rating=1000,
            loser_rating=1000,
            k_factor=32,
            is_draw=True,
        )
        assert winner_change == 0
        assert loser_change == 0

    def test_higher_rated_wins_less(self) -> None:
        """Higher-rated winner gains less than half K-factor."""
        winner_change, loser_change = calculate_elo_change(
            winner_rating=1200,
            loser_rating=1000,
            k_factor=32,
            is_draw=False,
        )
        # Higher rated was expected to win, so gains less
        assert winner_change < 16
        assert winner_change > 0
        assert loser_change > -16
        assert loser_change < 0

    def test_lower_rated_wins_more(self) -> None:
        """Underdog winner gains more than half K-factor."""
        winner_change, loser_change = calculate_elo_change(
            winner_rating=1000,
            loser_rating=1200,
            k_factor=32,
            is_draw=False,
        )
        # Lower rated was underdog, so gains more for upset
        assert winner_change > 16
        assert loser_change < -16

    def test_changes_sum_to_zero(self) -> None:
        """Total ELO change sums to zero (conservation)."""
        winner_change, loser_change = calculate_elo_change(
            winner_rating=1300,
            loser_rating=1100,
            k_factor=32,
            is_draw=False,
        )
        assert winner_change + loser_change == 0

    def test_draw_changes_sum_to_zero(self) -> None:
        """Draw ELO changes sum to zero."""
        winner_change, loser_change = calculate_elo_change(
            winner_rating=1300,
            loser_rating=1100,
            k_factor=32,
            is_draw=True,
        )
        assert winner_change + loser_change == 0

    def test_draw_higher_rated_loses_points(self) -> None:
        """In a draw, higher-rated player loses points."""
        winner_change, loser_change = calculate_elo_change(
            winner_rating=1300,
            loser_rating=1100,
            k_factor=32,
            is_draw=True,
        )
        # winner_rating (1300) is higher, draw is below expected, so they lose
        assert winner_change < 0
        # loser_rating (1100) is lower, draw is above expected, so they gain
        assert loser_change > 0

    def test_different_k_factor(self) -> None:
        """Different K-factor scales the changes proportionally."""
        change_k16_w, change_k16_l = calculate_elo_change(1000, 1000, k_factor=16)
        change_k32_w, change_k32_l = calculate_elo_change(1000, 1000, k_factor=32)

        assert change_k32_w == 2 * change_k16_w
        assert change_k32_l == 2 * change_k16_l
