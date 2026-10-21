"""Streak calculation helpers for the energy module.

Pure functions with no I/O. Used by EnergyService to compute daily
login streak updates and associated rewards.
"""

from __future__ import annotations

from datetime import date


def calculate_streak_update(
    last_login_date: date | None,
    current_streak: int,
    today: date,
) -> tuple[int, bool, bool]:
    """Calculate streak update based on login date comparison.

    Returns:
        Tuple of (new_streak, streak_continued, streak_broken).
        - ``streak_continued`` is True when the streak incremented
          (consecutive day login).
        - ``streak_broken`` is True when the streak was reset because
          the player missed one or more days.
        - On same-day repeat login both flags are False and the streak
          is unchanged.
    """
    if last_login_date is None:
        # First ever login
        return 1, False, False

    days_since_login = (today - last_login_date).days

    if days_since_login == 0:
        # Same day, no change
        return current_streak, False, False
    elif days_since_login == 1:
        # Consecutive day, increment streak
        return current_streak + 1, True, False
    else:
        # Streak broken, reset to 1
        return 1, False, True


def calculate_streak_reward(
    streak_day: int,
    threshold_7: int,
    threshold_14: int,
    threshold_30: int,
    repeat_interval: int,
) -> int:
    """Calculate bonus hearts for a given streak day.

    Rewards are granted at days 7, 14, 30, and then every
    *repeat_interval* days after 30.

    Returns:
        Bonus hearts to grant (0 if no reward at this streak day).
    """
    if streak_day == 7:
        return threshold_7
    elif streak_day == 14:
        return threshold_14
    elif streak_day == 30:
        return threshold_30
    elif streak_day > 30 and (streak_day - 30) % repeat_interval == 0:
        return threshold_30  # Repeat the 30-day reward amount
    else:
        return 0


def calculate_next_reward_threshold(
    current_streak: int,
) -> tuple[int, int]:
    """Calculate next streak reward threshold.

    Returns:
        Tuple of (threshold_day, days_until_reward).
    """
    if current_streak < 7:
        return 7, 7 - current_streak
    elif current_streak < 14:
        return 14, 14 - current_streak
    elif current_streak < 30:
        return 30, 30 - current_streak
    else:
        # After 30, rewards every 7 days
        days_since_30 = current_streak - 30
        days_into_cycle = days_since_30 % 7
        days_until = 7 - days_into_cycle if days_into_cycle > 0 else 7
        return current_streak + days_until, days_until
