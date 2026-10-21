"""Username validation helpers.

Pure synchronous functions for validating player usernames against
configurable constraints. No side effects, no service dependencies.
"""

from __future__ import annotations

import re


def validate_username(
    username: str,
    min_length: int,
    max_length: int,
    pattern: str,
) -> tuple[bool, str | None]:
    """Validate username format against constraints.

    Args:
        username: The username string to validate.
        min_length: Minimum allowed length.
        max_length: Maximum allowed length.
        pattern: Regular expression pattern the username must match.

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    if len(username) < min_length:
        return False, f"Username must be at least {min_length} characters"

    if len(username) > max_length:
        return False, f"Username must be at most {max_length} characters"

    if not re.match(pattern, username):
        return False, "Username can only contain letters, numbers, and underscores"

    return True, None
