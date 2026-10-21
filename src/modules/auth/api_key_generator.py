"""API key generation and verification helper.

Provides functions for generating cryptographically secure API keys
and verifying them against stored bcrypt hashes. Used internally by
AuthService; not part of the public module interface.
"""

from __future__ import annotations

import base64
import secrets

import bcrypt


def generate_api_key(prefix: str, key_length: int = 32) -> tuple[str, str]:
    """Generate a new API key with a prefix.

    Creates a cryptographically secure random key, then hashes it with
    bcrypt for storage. Only the hash should be persisted; the raw key
    is returned once and never stored.

    Args:
        prefix: The prefix to prepend (e.g., "cc\_").
        key_length: Number of random bytes to generate (default 32).

    Returns:
        Tuple of (raw_key, key_hash) where raw_key includes the prefix
        and key_hash is a bcrypt hash of the full raw_key.
    """
    # Generate random bytes and encode as base64url (no padding)
    random_bytes = secrets.token_bytes(key_length)
    random_part = base64.urlsafe_b64encode(random_bytes).rstrip(b"=").decode("ascii")

    raw_key = f"{prefix}{random_part}"
    key_hash = hash_api_key(raw_key)

    return raw_key, key_hash


def hash_api_key(key: str) -> str:
    """Hash an API key using bcrypt.

    Args:
        key: The full API key string to hash.

    Returns:
        Bcrypt hash string.
    """
    return bcrypt.hashpw(key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify an API key against its bcrypt hash.

    Uses bcrypt's constant-time comparison to prevent timing attacks.

    Args:
        key: The full API key string to verify.
        key_hash: The stored bcrypt hash.

    Returns:
        True if the key matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(key.encode("utf-8"), key_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False
