"""Unit tests for the API key generator.

Tests API key generation, hashing, and verification.
"""

from __future__ import annotations

import pytest

from src.modules.auth.api_key_generator import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
)

# ---------------------------------------------------------------------------
# API Key Generation Tests
# ---------------------------------------------------------------------------


class TestGenerateApiKey:
    """Tests for API key generation."""

    def test_key_starts_with_prefix(self) -> None:
        """Generated key starts with the specified prefix."""
        raw_key, _ = generate_api_key(prefix="cc_", key_length=32)
        assert raw_key.startswith("cc_")

    def test_returns_raw_key_and_hash(self) -> None:
        """Returns both raw key and bcrypt hash."""
        raw_key, key_hash = generate_api_key(prefix="cc_", key_length=32)

        assert len(raw_key) > len("cc_")
        assert key_hash.startswith("$2b$")

    def test_unique_keys_each_call(self) -> None:
        """Each call produces a unique key."""
        key1, _ = generate_api_key(prefix="cc_", key_length=32)
        key2, _ = generate_api_key(prefix="cc_", key_length=32)
        assert key1 != key2

    def test_hash_verifies_against_raw_key(self) -> None:
        """The generated hash verifies against the raw key."""
        raw_key, key_hash = generate_api_key(prefix="cc_", key_length=32)
        assert verify_api_key(raw_key, key_hash) is True

    def test_custom_prefix(self) -> None:
        """Custom prefix is used in the generated key."""
        raw_key, _ = generate_api_key(prefix="test_", key_length=16)
        assert raw_key.startswith("test_")


# ---------------------------------------------------------------------------
# API Key Hash & Verify Tests
# ---------------------------------------------------------------------------


class TestHashAndVerifyApiKey:
    """Tests for API key hashing and verification."""

    def test_hash_produces_bcrypt(self) -> None:
        """hash_api_key produces a bcrypt hash."""
        hashed = hash_api_key("cc_test_key_value")
        assert hashed.startswith("$2b$")

    def test_verify_correct_key(self) -> None:
        """Correct key verifies against its hash."""
        key = "cc_abcdef1234567890"
        hashed = hash_api_key(key)
        assert verify_api_key(key, hashed) is True

    def test_verify_wrong_key(self) -> None:
        """Wrong key does not verify."""
        key = "cc_abcdef1234567890"
        hashed = hash_api_key(key)
        assert verify_api_key("cc_wrongkeywrongkey", hashed) is False

    def test_verify_invalid_hash_returns_false(self) -> None:
        """Invalid hash returns False (no exception)."""
        assert verify_api_key("cc_somekey", "not-a-hash") is False
