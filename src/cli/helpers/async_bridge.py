"""Shared async bridge for CLI commands.

Provides ``run_cli_async`` which handles ``ApplicationContext`` lifecycle
(creation + guaranteed shutdown) so individual command files don't repeat
the boilerplate.

Also provides ``resolve_player`` for username → UUID resolution, used by
virtually every async command that takes a player argument.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import click

from src.core.composition_root import (
    ApplicationContext,
    create_application_context,
    shutdown_application_context,
)


def run_cli_async(
    coro_factory: Any,
    config_path: str = "config/app.toml",
) -> None:
    """Bridge sync Click commands to async code with application context.

    Creates an ``ApplicationContext``, passes it to *coro_factory*, and
    ensures proper shutdown regardless of outcome.

    Args:
        coro_factory: An async callable that receives ``ApplicationContext``.
        config_path: Path to the TOML configuration file.
    """

    async def _inner() -> None:
        ctx = await create_application_context(config_path)
        try:
            await coro_factory(ctx)
        finally:
            await shutdown_application_context(ctx)

    asyncio.run(_inner())


async def resolve_player(ctx: ApplicationContext, username: str) -> UUID:
    """Resolve a username to a player UUID, raising ClickException on failure."""
    player = await ctx.player_service.get_player_by_username(username)
    if player is None:
        raise click.ClickException(f"Player not found: {username}")
    return player.id
