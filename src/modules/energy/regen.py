"""Regeneration calculation helpers for the energy module.

Pure functions with no I/O. All time calculations use UTC datetimes.
These helpers are used by EnergyService to compute heart regeneration
without persisting state.
"""

from __future__ import annotations

from datetime import datetime, timedelta


def calculate_regenerated_hearts(
    current_hearts: int,
    max_hearts: int,
    last_regen_at: datetime,
    now: datetime,
    regen_interval_seconds: int,
) -> tuple[int, int, datetime]:
    """Calculate hearts regenerated since last_regen_at.

    Returns:
        Tuple of (hearts_to_add, new_heart_count, new_last_regen_at).
        ``new_last_regen_at`` is advanced by exactly the number of
        consumed intervals so that partial progress toward the next
        heart is preserved.
    """
    if current_hearts >= max_hearts:
        return 0, current_hearts, last_regen_at

    elapsed_seconds = (now - last_regen_at).total_seconds()
    if elapsed_seconds < 0:
        return 0, current_hearts, last_regen_at

    hearts_can_regen = max_hearts - current_hearts

    # How many full intervals have passed?
    intervals_passed = int(elapsed_seconds // regen_interval_seconds)
    hearts_to_add = min(intervals_passed, hearts_can_regen)

    new_hearts = current_hearts + hearts_to_add

    # Update last_regen_at to account for used intervals only.
    # This preserves partial progress toward the next heart.
    if hearts_to_add > 0:
        new_last_regen_at = last_regen_at + timedelta(
            seconds=hearts_to_add * regen_interval_seconds,
        )
    else:
        new_last_regen_at = last_regen_at

    return hearts_to_add, new_hearts, new_last_regen_at


def calculate_time_to_next_heart(
    current_hearts: int,
    max_hearts: int,
    last_regen_at: datetime,
    now: datetime,
    regen_interval_seconds: int,
) -> int | None:
    """Calculate seconds until next heart regenerates.

    Returns:
        Seconds until the next heart, or ``None`` if already at max.
    """
    if current_hearts >= max_hearts:
        return None

    elapsed = (now - last_regen_at).total_seconds()
    if elapsed < 0:
        # Clock skew -- treat as full interval remaining.
        return regen_interval_seconds

    seconds_into_current_interval = elapsed % regen_interval_seconds
    seconds_remaining = regen_interval_seconds - seconds_into_current_interval

    return int(seconds_remaining)
