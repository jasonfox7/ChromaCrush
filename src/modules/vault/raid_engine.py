"""Raid probability and selection logic.

Pure functions for raid mechanics. No database access, no service
dependencies -- these can be tested without any mocks.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

# Weights for weighted random artifact selection during raids.
# Lower-rarity artifacts are more likely to be targeted.
RARITY_WEIGHTS: dict[str, int] = {
    "common": 4,
    "rare": 3,
    "epic": 2,
    "legendary": 1,
}


def calculate_raid_success(
    base_chance: float,
    target_artifact_rarity: str,
    legendary_modifier: float,
) -> bool:
    """Determine if a raid attempt succeeds.

    Legendary items have a reduced success chance, controlled by the
    ``legendary_modifier`` multiplier.

    Args:
        base_chance: Base success probability (0.0-1.0) from config.
        target_artifact_rarity: Rarity string of the selected artifact.
        legendary_modifier: Multiplier applied when targeting legendary items.

    Returns:
        True if raid succeeds.
    """
    effective_chance = base_chance
    if target_artifact_rarity == "legendary":
        effective_chance *= legendary_modifier

    return random.random() < effective_chance


def select_raid_target_artifact(
    artifacts: list[object],
    rng: random.Random | None = None,
) -> object | None:
    """Select which artifact the raider will attempt to steal.

    Uses weighted random selection favouring lower-rarity items so that
    legendary theft is rare and exciting.

    Weights:
        common=4, rare=3, epic=2, legendary=1.

    Args:
        artifacts: Available artifacts in the defender's vault. Each must
            have a ``rarity`` attribute (string).
        rng: Optional seeded RNG for deterministic testing.

    Returns:
        Selected artifact, or None if the list is empty.
    """
    if not artifacts:
        return None

    if rng is None:
        rng = random.Random()

    weighted: list[object] = []
    for artifact in artifacts:
        rarity = getattr(artifact, "rarity", "common")
        weight = RARITY_WEIGHTS.get(rarity, 1)
        weighted.extend([artifact] * weight)

    return rng.choice(weighted)


def is_raid_on_cooldown(
    last_raid_timestamp: datetime | None,
    cooldown_hours: int,
) -> tuple[bool, datetime | None]:
    """Check if the raid cooldown is still active.

    Args:
        last_raid_timestamp: When the last raid between these players occurred.
        cooldown_hours: Cooldown duration in hours from config.

    Returns:
        Tuple of ``(is_on_cooldown, cooldown_expires_at_or_None)``.
    """
    if last_raid_timestamp is None:
        return False, None

    cooldown_expires = last_raid_timestamp + timedelta(hours=cooldown_hours)
    now = datetime.now(timezone.utc)

    if now < cooldown_expires:
        return True, cooldown_expires

    return False, None
