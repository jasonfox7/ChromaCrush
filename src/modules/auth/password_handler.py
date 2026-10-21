"""Password hashing and verification helper.

Provides functions for hashing passwords with bcrypt and validating
password strength. Used internally by AuthService; not part of the
public module interface.
"""

from __future__ import annotations

import bcrypt


def hash_password(password: str, rounds: int = 12) -> str:
    """Hash a password using bcrypt.

    Args:
        password: The plain-text password to hash.
        rounds: Bcrypt work factor (default 12). Higher values are slower
            but more secure against brute-force attacks.

    Returns:
        Bcrypt hash string.
    """
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash.

    Uses bcrypt's constant-time comparison to prevent timing attacks.

    Args:
        password: The plain-text password to verify.
        password_hash: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def validate_password_strength(
    password: str,
    min_length: int = 8,
) -> tuple[bool, str | None]:
    """Validate that a password meets minimum strength requirements.

    Args:
        password: The plain-text password to validate.
        min_length: Minimum required length (default 8).

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    return True, None
