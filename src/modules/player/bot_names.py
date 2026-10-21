"""Procedural bot name generator.

Generates CamelCase names from adjective+noun pairs.
Names pass the existing username validation pattern ``^[a-zA-Z0-9_]+$``.
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.player.service import PlayerService

_ADJECTIVES = [
    "Crimson",
    "Neon",
    "Shadow",
    "Crystal",
    "Iron",
    "Azure",
    "Phantom",
    "Solar",
    "Storm",
    "Ember",
    "Frost",
    "Cosmic",
    "Silent",
    "Nova",
    "Prism",
    "Volt",
    "Obsidian",
    "Lunar",
    "Blazing",
    "Mystic",
    "Vivid",
    "Echo",
    "Radiant",
    "Onyx",
    "Spectral",
    "Inferno",
    "Arctic",
    "Rogue",
    "Golden",
    "Scarlet",
    "Thunder",
    "Dusk",
    "Twilight",
    "Jade",
    "Ruby",
    "Sapphire",
    "Copper",
    "Violet",
    "Ashen",
    "Sterling",
    "Molten",
    "Wicked",
    "Feral",
    "Hollow",
    "Cerulean",
    "Gilded",
    "Verdant",
    "Nimble",
    "Brutal",
    "Ancient",
    "Chaos",
    "Astral",
    "Velvet",
    "Glacial",
]

_NOUNS = [
    "Vortex",
    "Phoenix",
    "Titan",
    "Raven",
    "Serpent",
    "Falcon",
    "Wraith",
    "Knight",
    "Hunter",
    "Oracle",
    "Cipher",
    "Reaper",
    "Striker",
    "Guardian",
    "Spark",
    "Blade",
    "Forge",
    "Shard",
    "Tempest",
    "Sentinel",
    "Prowler",
    "Pulse",
    "Crusader",
    "Nexus",
    "Fury",
    "Spirit",
    "Wave",
    "Enigma",
    "Harbinger",
    "Catalyst",
    "Surge",
    "Fang",
    "Crown",
    "Bolt",
    "Specter",
    "Talon",
    "Anvil",
    "Moth",
    "Mirage",
    "Comet",
    "Drake",
    "Wolf",
    "Lynx",
    "Hawk",
    "Jackal",
    "Mantis",
    "Cobra",
    "Gryphon",
    "Warden",
    "Golem",
    "Sage",
    "Rune",
    "Pyre",
    "Dagger",
]


def generate_bot_name() -> str:
    """Generate a bot name like 'CrimsonVortex' or 'NeonPhantom'."""
    return random.choice(_ADJECTIVES) + random.choice(_NOUNS)


async def generate_unique_bot_name(player_service: PlayerService) -> str:
    """Generate a unique bot name that doesn't conflict with existing usernames.

    Args:
        player_service: Player service for username existence checks.

    Returns:
        A unique CamelCase bot name.
    """
    for _ in range(100):
        name = generate_bot_name()
        existing = await player_service.get_player_by_username(name)
        if existing is None:
            return name
    # Fallback: append timestamp digits to avoid collision.
    return generate_bot_name() + str(int(time.time()) % 10000)
