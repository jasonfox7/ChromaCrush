"""Consumption calculation helpers for the energy module.

Pure functions with no I/O. These helpers are used by EnergyService
to validate and compute heart consumption without persisting state.
"""

from __future__ import annotations


def validate_consume_amount(amount: int) -> bool:
    """Check whether a consume amount is valid (at least 1).

    Returns:
        True if valid, False otherwise.
    """
    return amount >= 1


def check_can_play(
    effective_hearts: int,
    hearts_required: int,
) -> bool:
    """Check if a player has enough (effective) hearts to play.

    ``effective_hearts`` should already include any pending
    regeneration so that a lazy-regen read is sufficient.

    Returns:
        True if the player can afford the action.
    """
    return effective_hearts >= hearts_required


def calculate_hearts_after_consume(
    effective_hearts: int,
    amount: int,
) -> int:
    """Compute the new heart count after consuming *amount* hearts.

    The caller is responsible for ensuring the player has enough
    hearts before calling this function (see :func:`check_can_play`).

    Returns:
        New heart count after deduction.
    """
    return effective_hearts - amount
