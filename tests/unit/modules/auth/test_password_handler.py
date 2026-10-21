"""Unit tests for the password handler.

Tests password hashing, verification, and strength validation.
"""

from __future__ import annotations

import pytest

from src.modules.auth.password_handler import (
    hash_password,
    validate_password_strength,
    verify_password,
)

# ---------------------------------------------------------------------------
# Password Hashing Tests
# ---------------------------------------------------------------------------


class TestHashPassword:
    """Tests for password hashing with bcrypt."""

    def test_produces_bcrypt_hash(self) -> None:
        """Hash output starts with bcrypt prefix ($2b$)."""
        hashed = hash_password("ValidPass1")
        assert hashed.startswith("$2b$")

    def test_different_passwords_different_hashes(self) -> None:
        """Different passwords produce different hashes."""
        hash1 = hash_password("ValidPass1")
        hash2 = hash_password("ValidPass2")
        assert hash1 != hash2

    def test_same_password_different_hashes(self) -> None:
        """Same password hashed twice produces different hashes (unique salts)."""
        hash1 = hash_password("ValidPass1")
        hash2 = hash_password("ValidPass1")
        assert hash1 != hash2

    def test_respects_rounds_parameter(self) -> None:
        """Lower rounds produce faster hashes (still valid)."""
        hashed = hash_password("ValidPass1", rounds=4)
        assert hashed.startswith("$2b$04$")


# ---------------------------------------------------------------------------
# Password Verification Tests
# ---------------------------------------------------------------------------


class TestVerifyPassword:
    """Tests for password verification against bcrypt hash."""

    def test_correct_password_returns_true(self) -> None:
        """Correct password verifies successfully."""
        hashed = hash_password("ValidPass1", rounds=4)
        assert verify_password("ValidPass1", hashed) is True

    def test_incorrect_password_returns_false(self) -> None:
        """Incorrect password fails verification."""
        hashed = hash_password("ValidPass1", rounds=4)
        assert verify_password("WrongPassword1", hashed) is False

    def test_invalid_hash_returns_false(self) -> None:
        """Invalid hash string returns False (no exception)."""
        assert verify_password("ValidPass1", "not-a-valid-hash") is False

    def test_empty_hash_returns_false(self) -> None:
        """Empty hash returns False (no exception)."""
        assert verify_password("ValidPass1", "") is False


# ---------------------------------------------------------------------------
# Password Strength Validation Tests
# ---------------------------------------------------------------------------


class TestValidatePasswordStrength:
    """Tests for password strength validation."""

    def test_valid_password_passes(self) -> None:
        """Password meeting all requirements passes."""
        is_valid, error_msg = validate_password_strength("Str0ngPas5")
        assert is_valid is True
        assert error_msg is None

    def test_too_short_fails(self) -> None:
        """Password below minimum length fails."""
        is_valid, error_msg = validate_password_strength("Ab1", min_length=8)
        assert is_valid is False
        assert "at least 8" in error_msg

    def test_no_uppercase_fails(self) -> None:
        """Password without uppercase letter fails."""
        is_valid, error_msg = validate_password_strength("lowercas1")
        assert is_valid is False
        assert "uppercase" in error_msg

    def test_no_lowercase_fails(self) -> None:
        """Password without lowercase letter fails."""
        is_valid, error_msg = validate_password_strength("UPPERCASE1")
        assert is_valid is False
        assert "lowercase" in error_msg

    def test_no_digit_fails(self) -> None:
        """Password without digit fails."""
        is_valid, error_msg = validate_password_strength("Abcdefghi")
        assert is_valid is False
        assert "digit" in error_msg

    def test_custom_min_length(self) -> None:
        """Custom minimum length is respected."""
        is_valid, error_msg = validate_password_strength("Ab1", min_length=3)
        assert is_valid is True
        assert error_msg is None
