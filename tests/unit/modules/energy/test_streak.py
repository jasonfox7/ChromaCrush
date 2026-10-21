"""Unit tests for the energy streak helpers.

Tests pure functions in ``src.modules.energy.streak`` with no I/O.
"""

from __future__ import annotations

from datetime import date, timedelta

from src.modules.energy.streak import (
    calculate_next_reward_threshold,
    calculate_streak_reward,
    calculate_streak_update,
)


class TestCalculateStreakUpdate:
    """Tests for ``calculate_streak_update``."""

    def test_first_login(self) -> None:
        """First ever login: streak=1, not continued, not broken."""
        new_streak, continued, broken = calculate_streak_update(
            last_login_date=None,
            current_streak=0,
            today=date(2026, 1, 15),
        )
        assert new_streak == 1
        assert continued is False
        assert broken is False

    def test_same_day_no_change(self) -> None:
        """Same-day login: no change to streak."""
        today = date(2026, 1, 15)
        new_streak, continued, broken = calculate_streak_update(
            last_login_date=today,
            current_streak=5,
            today=today,
        )
        assert new_streak == 5
        assert continued is False
        assert broken is False

    def test_consecutive_day_increments(self) -> None:
        """Consecutive day login: streak incremented."""
        yesterday = date(2026, 1, 14)
        today = date(2026, 1, 15)
        new_streak, continued, broken = calculate_streak_update(
            last_login_date=yesterday,
            current_streak=5,
            today=today,
        )
        assert new_streak == 6
        assert continued is True
        assert broken is False

    def test_two_days_missed_breaks_streak(self) -> None:
        """Two days since last login: streak broken, reset to 1."""
        last_login = date(2026, 1, 13)
        today = date(2026, 1, 15)
        new_streak, continued, broken = calculate_streak_update(
            last_login_date=last_login,
            current_streak=10,
            today=today,
        )
        assert new_streak == 1
        assert continued is False
        assert broken is True

    def test_many_days_missed_breaks_streak(self) -> None:
        """Many days since last login: streak broken."""
        last_login = date(2026, 1, 1)
        today = date(2026, 2, 1)
        new_streak, continued, broken = calculate_streak_update(
            last_login_date=last_login,
            current_streak=30,
            today=today,
        )
        assert new_streak == 1
        assert continued is False
        assert broken is True

    def test_streak_increment_from_one(self) -> None:
        """Streak increments from 1 to 2 on consecutive day."""
        yesterday = date(2026, 1, 14)
        today = date(2026, 1, 15)
        new_streak, continued, broken = calculate_streak_update(
            last_login_date=yesterday,
            current_streak=1,
            today=today,
        )
        assert new_streak == 2
        assert continued is True


class TestCalculateStreakReward:
    """Tests for ``calculate_streak_reward``."""

    def test_no_reward_at_day_1(self) -> None:
        """No reward at day 1."""
        assert calculate_streak_reward(1, 1, 2, 3, 7) == 0

    def test_no_reward_at_day_6(self) -> None:
        """No reward at day 6."""
        assert calculate_streak_reward(6, 1, 2, 3, 7) == 0

    def test_reward_at_day_7(self) -> None:
        """Reward at 7-day threshold."""
        assert calculate_streak_reward(7, 1, 2, 3, 7) == 1

    def test_reward_at_day_14(self) -> None:
        """Reward at 14-day threshold."""
        assert calculate_streak_reward(14, 1, 2, 3, 7) == 2

    def test_reward_at_day_30(self) -> None:
        """Reward at 30-day threshold."""
        assert calculate_streak_reward(30, 1, 2, 3, 7) == 3

    def test_no_reward_at_day_31(self) -> None:
        """No reward at day 31 (first day after 30 cycle)."""
        assert calculate_streak_reward(31, 1, 2, 3, 7) == 0

    def test_repeat_reward_at_day_37(self) -> None:
        """Repeat reward at day 37 (30 + 7)."""
        assert calculate_streak_reward(37, 1, 2, 3, 7) == 3

    def test_repeat_reward_at_day_44(self) -> None:
        """Repeat reward at day 44 (30 + 14)."""
        assert calculate_streak_reward(44, 1, 2, 3, 7) == 3

    def test_no_reward_between_repeats(self) -> None:
        """No reward between repeat intervals."""
        assert calculate_streak_reward(35, 1, 2, 3, 7) == 0

    def test_custom_thresholds(self) -> None:
        """Custom threshold values are used correctly."""
        assert calculate_streak_reward(7, 5, 10, 15, 7) == 5
        assert calculate_streak_reward(14, 5, 10, 15, 7) == 10
        assert calculate_streak_reward(30, 5, 10, 15, 7) == 15


class TestCalculateNextRewardThreshold:
    """Tests for ``calculate_next_reward_threshold``."""

    def test_streak_0(self) -> None:
        """At streak 0, next reward is day 7, 7 days away."""
        threshold, days_until = calculate_next_reward_threshold(0)
        assert threshold == 7
        assert days_until == 7

    def test_streak_3(self) -> None:
        """At streak 3, next reward is day 7, 4 days away."""
        threshold, days_until = calculate_next_reward_threshold(3)
        assert threshold == 7
        assert days_until == 4

    def test_streak_7(self) -> None:
        """At streak 7, next reward is day 14, 7 days away."""
        threshold, days_until = calculate_next_reward_threshold(7)
        assert threshold == 14
        assert days_until == 7

    def test_streak_10(self) -> None:
        """At streak 10, next reward is day 14, 4 days away."""
        threshold, days_until = calculate_next_reward_threshold(10)
        assert threshold == 14
        assert days_until == 4

    def test_streak_14(self) -> None:
        """At streak 14, next reward is day 30, 16 days away."""
        threshold, days_until = calculate_next_reward_threshold(14)
        assert threshold == 30
        assert days_until == 16

    def test_streak_20(self) -> None:
        """At streak 20, next reward is day 30, 10 days away."""
        threshold, days_until = calculate_next_reward_threshold(20)
        assert threshold == 30
        assert days_until == 10

    def test_streak_30(self) -> None:
        """At streak 30, next reward is day 37, 7 days away."""
        threshold, days_until = calculate_next_reward_threshold(30)
        assert threshold == 37
        assert days_until == 7

    def test_streak_37(self) -> None:
        """At streak 37, next reward is day 44, 7 days away."""
        threshold, days_until = calculate_next_reward_threshold(37)
        assert threshold == 44
        assert days_until == 7

    def test_streak_35(self) -> None:
        """At streak 35, next reward is day 37, 2 days away."""
        threshold, days_until = calculate_next_reward_threshold(35)
        assert threshold == 37
        assert days_until == 2
