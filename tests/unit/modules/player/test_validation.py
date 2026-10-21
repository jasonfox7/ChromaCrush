"""Unit tests for username validation.

Tests the pure synchronous username validation function against
various valid and invalid inputs.
"""

from __future__ import annotations

from src.modules.player.validation import validate_username

# Default constraints matching artifact spec
DEFAULT_MIN = 3
DEFAULT_MAX = 32
DEFAULT_PATTERN = r"^[a-zA-Z0-9_]+$"


class TestValidateUsername:
    """Tests for ``validate_username``."""

    def test_valid_username(self) -> None:
        """Standard valid username passes validation."""
        is_valid, error = validate_username(
            "player1", DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is True
        assert error is None

    def test_valid_with_underscores(self) -> None:
        """Username with underscores is valid."""
        is_valid, error = validate_username(
            "cool_player_99", DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is True
        assert error is None

    def test_valid_minimum_length(self) -> None:
        """Username at minimum length boundary is valid."""
        is_valid, error = validate_username(
            "abc", DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is True
        assert error is None

    def test_valid_maximum_length(self) -> None:
        """Username at maximum length boundary is valid."""
        long_name = "a" * 32
        is_valid, error = validate_username(
            long_name, DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is True
        assert error is None

    def test_too_short(self) -> None:
        """Username shorter than minimum length is rejected."""
        is_valid, error = validate_username(
            "ab", DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is False
        assert error is not None
        assert "at least 3" in error

    def test_too_long(self) -> None:
        """Username longer than maximum length is rejected."""
        long_name = "a" * 33
        is_valid, error = validate_username(
            long_name, DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is False
        assert error is not None
        assert "at most 32" in error

    def test_invalid_chars_spaces(self) -> None:
        """Username with spaces is rejected."""
        is_valid, error = validate_username(
            "player one", DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is False
        assert error is not None
        assert "letters, numbers, and underscores" in error

    def test_invalid_chars_special(self) -> None:
        """Username with special characters is rejected."""
        is_valid, error = validate_username(
            "player!@#", DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is False
        assert error is not None

    def test_invalid_chars_hyphen(self) -> None:
        """Username with hyphens is rejected by default pattern."""
        is_valid, error = validate_username(
            "player-one", DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is False
        assert error is not None

    def test_empty_string(self) -> None:
        """Empty string is rejected (too short)."""
        is_valid, error = validate_username(
            "", DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is False
        assert error is not None

    def test_all_numbers(self) -> None:
        """Username with only numbers is valid."""
        is_valid, error = validate_username(
            "123456", DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is True
        assert error is None

    def test_all_underscores(self) -> None:
        """Username with only underscores is valid per pattern."""
        is_valid, error = validate_username(
            "___", DEFAULT_MIN, DEFAULT_MAX, DEFAULT_PATTERN
        )
        assert is_valid is True
        assert error is None

    def test_custom_constraints(self) -> None:
        """Custom min/max constraints are honoured."""
        is_valid, error = validate_username("ab", 2, 5, DEFAULT_PATTERN)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_username("toolong", 2, 5, DEFAULT_PATTERN)
        assert is_valid is False
        assert error is not None
