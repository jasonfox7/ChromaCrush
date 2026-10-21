"""Bonus and refund calculation helpers for the energy module.

Pure functions with no I/O. These helpers are used by EnergyService
to compute bonus heart grants (with overflow caps) and refunds
without persisting state. Idempotency key formatting is also
centralised here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

# Idempotency key TTL for bonus heart grants (24 hours in seconds).
IDEMPOTENCY_TTL_SECONDS: int = 86400


def validate_bonus_amount(amount: int) -> bool:
    """Check whether a bonus amount is valid (at least 1).

    Returns:
        True if valid, False otherwise.
    """
    return amount >= 1


def build_idempotency_redis_key(
    player_id: UUID | str,
    idempotency_key: str,
) -> str:
    """Build the Redis key used for bonus grant idempotency.

    Returns:
        Fully-qualified Redis key string.
    """
    return f"chromacrush:energy:bonus:{player_id}:{idempotency_key}"


def calculate_bonus_hearts(
    current_hearts: int,
    amount: int,
    max_hearts: int,
    overflow_limit: int,
) -> tuple[int, int]:
    """Compute new heart count after granting bonus hearts.

    Bonus hearts may push the count above ``max_hearts`` up to
    ``max_hearts + overflow_limit``.

    Returns:
        Tuple of (new_heart_count, actual_granted).
    """
    cap = max_hearts + overflow_limit
    new_hearts = min(current_hearts + amount, cap)
    actual_granted = new_hearts - current_hearts
    return new_hearts, actual_granted


def calculate_refund_hearts(
    current_hearts: int,
    amount: int,
    max_hearts: int,
) -> int:
    """Compute new heart count after a refund.

    Refunds are capped at ``max_hearts`` (no overflow).

    Returns:
        New heart count after refund.
    """
    return min(current_hearts + amount, max_hearts)
