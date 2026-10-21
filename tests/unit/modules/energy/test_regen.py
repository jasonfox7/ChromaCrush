"""Unit tests for the energy regeneration helpers.

Tests pure functions in ``src.modules.energy.regen`` with no I/O.
All datetimes use UTC.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.modules.energy.regen import (
    calculate_regenerated_hearts,
    calculate_time_to_next_heart,
)

# Default test interval: 30 minutes = 1800 seconds
REGEN_INTERVAL = 1800


class TestCalculateRegeneratedHearts:
    """Tests for ``calculate_regenerated_hearts``."""

    def test_no_regen_when_at_max(self) -> None:
        """No hearts regenerated when already at max."""
        now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        last_regen = now - timedelta(hours=2)

        hearts_added, new_hearts, new_regen_at = calculate_regenerated_hearts(
            current_hearts=5,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )

        assert hearts_added == 0
        assert new_hearts == 5
        assert new_regen_at == last_regen

    def test_one_heart_after_one_interval(self) -> None:
        """Exactly one heart regenerated after one interval."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = last_regen + timedelta(seconds=REGEN_INTERVAL)

        hearts_added, new_hearts, new_regen_at = calculate_regenerated_hearts(
            current_hearts=3,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )

        assert hearts_added == 1
        assert new_hearts == 4
        assert new_regen_at == last_regen + timedelta(seconds=REGEN_INTERVAL)

    def test_three_hearts_after_three_intervals(self) -> None:
        """Three hearts regenerated after three intervals."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = last_regen + timedelta(seconds=REGEN_INTERVAL * 3)

        hearts_added, new_hearts, new_regen_at = calculate_regenerated_hearts(
            current_hearts=2,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )

        assert hearts_added == 3
        assert new_hearts == 5
        assert new_regen_at == last_regen + timedelta(seconds=REGEN_INTERVAL * 3)

    def test_capped_at_max_hearts(self) -> None:
        """Regeneration is capped at max_hearts even if many intervals passed."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = last_regen + timedelta(seconds=REGEN_INTERVAL * 10)  # 10 intervals

        hearts_added, new_hearts, new_regen_at = calculate_regenerated_hearts(
            current_hearts=3,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )

        assert hearts_added == 2  # Can only add 2 (3 + 2 = 5)
        assert new_hearts == 5
        assert new_regen_at == last_regen + timedelta(seconds=REGEN_INTERVAL * 2)

    def test_partial_interval_preserved(self) -> None:
        """Partial interval is preserved in new_last_regen_at."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        # 1.5 intervals = 1 heart + 15 minutes partial
        now = last_regen + timedelta(seconds=int(REGEN_INTERVAL * 1.5))

        hearts_added, new_hearts, new_regen_at = calculate_regenerated_hearts(
            current_hearts=3,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )

        assert hearts_added == 1
        assert new_hearts == 4
        # new_regen_at should advance by exactly 1 interval
        assert new_regen_at == last_regen + timedelta(seconds=REGEN_INTERVAL)
        # Verify partial progress: 15 min still to go
        remaining = (now - new_regen_at).total_seconds()
        assert remaining == REGEN_INTERVAL * 0.5

    def test_no_regen_less_than_one_interval(self) -> None:
        """No hearts if less than one full interval has passed."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = last_regen + timedelta(seconds=REGEN_INTERVAL - 1)

        hearts_added, new_hearts, new_regen_at = calculate_regenerated_hearts(
            current_hearts=3,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )

        assert hearts_added == 0
        assert new_hearts == 3
        assert new_regen_at == last_regen

    def test_zero_current_hearts(self) -> None:
        """Full regeneration from zero hearts."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = last_regen + timedelta(seconds=REGEN_INTERVAL * 5)

        hearts_added, new_hearts, new_regen_at = calculate_regenerated_hearts(
            current_hearts=0,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )

        assert hearts_added == 5
        assert new_hearts == 5

    def test_above_max_hearts_no_regen(self) -> None:
        """No regeneration when hearts exceed max (from bonus overflow)."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = last_regen + timedelta(seconds=REGEN_INTERVAL * 5)

        hearts_added, new_hearts, new_regen_at = calculate_regenerated_hearts(
            current_hearts=7,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )

        assert hearts_added == 0
        assert new_hearts == 7

    def test_negative_elapsed_time(self) -> None:
        """Clock skew (now before last_regen_at) results in no regen."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = last_regen - timedelta(seconds=60)

        hearts_added, new_hearts, new_regen_at = calculate_regenerated_hearts(
            current_hearts=3,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )

        assert hearts_added == 0
        assert new_hearts == 3

    def test_exact_boundary_timing(self) -> None:
        """Exactly on the interval boundary regenerates one heart."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = last_regen + timedelta(seconds=REGEN_INTERVAL)

        hearts_added, new_hearts, _ = calculate_regenerated_hearts(
            current_hearts=4,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )

        assert hearts_added == 1
        assert new_hearts == 5


class TestCalculateTimeToNextHeart:
    """Tests for ``calculate_time_to_next_heart``."""

    def test_none_when_at_max(self) -> None:
        """Returns None when at max hearts."""
        now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = calculate_time_to_next_heart(
            current_hearts=5,
            max_hearts=5,
            last_regen_at=now,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )
        assert result is None

    def test_full_interval_remaining(self) -> None:
        """Full interval remaining when no time has elapsed."""
        now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = calculate_time_to_next_heart(
            current_hearts=3,
            max_hearts=5,
            last_regen_at=now,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )
        assert result == REGEN_INTERVAL

    def test_partial_time_remaining(self) -> None:
        """Correct seconds remaining partway through an interval."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = last_regen + timedelta(seconds=600)  # 10 minutes in

        result = calculate_time_to_next_heart(
            current_hearts=3,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )
        assert result == 1200  # 20 minutes remaining

    def test_just_before_regen(self) -> None:
        """One second remaining before next heart."""
        last_regen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        now = last_regen + timedelta(seconds=REGEN_INTERVAL - 1)

        result = calculate_time_to_next_heart(
            current_hearts=3,
            max_hearts=5,
            last_regen_at=last_regen,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )
        assert result == 1

    def test_none_when_above_max(self) -> None:
        """Returns None when hearts exceed max (bonus overflow)."""
        now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = calculate_time_to_next_heart(
            current_hearts=7,
            max_hearts=5,
            last_regen_at=now,
            now=now,
            regen_interval_seconds=REGEN_INTERVAL,
        )
        assert result is None
