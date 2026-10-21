"""Seed the database with 20 bot players and full card loadouts.

Usage (from repo root):
    python -m scripts.seed_bots

Requires the database and Redis to be running. Uses the application's
composition root to bootstrap services, so all business rules (unique
names, card definitions, equip logic) are enforced.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `src.*` imports resolve.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.core.composition_root import (
    create_application_context,
    shutdown_application_context,
)
from src.core.types.player import PlayerType
from src.modules.player.bot_names import generate_unique_bot_name

BOT_COUNT = 20


async def main() -> None:
    ctx = await create_application_context()
    try:
        player_service = ctx.player_service
        card_service = ctx.card_service
        logger = ctx.logger

        created = 0
        for i in range(BOT_COUNT):
            try:
                name = await generate_unique_bot_name(player_service)
                bot = await player_service.create_player(
                    username=name,
                    player_type=PlayerType.BOT,
                )
                await card_service.grant_bot_full_loadout(bot.id)
                created += 1
                logger.info(
                    "seed_bot.created",
                    bot_name=name,
                    bot_id=str(bot.id),
                    index=i + 1,
                )
            except Exception as exc:
                logger.warning(
                    "seed_bot.failed",
                    index=i + 1,
                    error=str(exc),
                )

        print(f"Seeded {created}/{BOT_COUNT} bots successfully.")
    finally:
        await shutdown_application_context(ctx)


if __name__ == "__main__":
    asyncio.run(main())
