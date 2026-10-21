"""Click CLI entry point for ChromaCrush.

Provides development and administration commands. Uses the same
composition root as the FastAPI application for consistency.

Run with:
    python -m src.cli.cli_entry
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from src.core.composition_root import load_config

console = Console()


# ---------------------------------------------------------------------------
# CLI root group
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """ChromaCrush -- Match-3 puzzle game CLI."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def version(config_path: str) -> None:
    """Print the application name and version."""
    config = load_config(config_path)
    name: str = config.get("app.name", "ChromaCrush")
    ver: str = config.get("app.version", "unknown")
    console.print(f"[bold]{name}[/bold] v{ver}")


@cli.command("show-config")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def show_config(config_path: str) -> None:
    """Display key configuration values in a table."""
    config = load_config(config_path)

    table = Table(title="ChromaCrush Configuration", show_header=True)
    table.add_column("Section", style="cyan", no_wrap=True)
    table.add_column("Key", style="green")
    table.add_column("Value", style="yellow")

    rows: list[tuple[str, str, str]] = [
        ("app", "name", str(config.get("app.name", ""))),
        ("app", "version", str(config.get("app.version", ""))),
        ("app", "environment", str(config.get("app.environment", ""))),
        ("database", "host", str(config.get("database.host", ""))),
        ("database", "port", str(config.get("database.port", ""))),
        ("database", "name", str(config.get("database.name", ""))),
        ("redis", "host", str(config.get("redis.host", ""))),
        ("redis", "port", str(config.get("redis.port", ""))),
        ("logging", "level", str(config.get("logging.level", ""))),
    ]

    for section, key, value in rows:
        table.add_row(section, key, value)

    console.print(table)


# ---------------------------------------------------------------------------
# Subcommand groups
# ---------------------------------------------------------------------------

from src.cli.commands.player_commands import player  # noqa: E402
from src.cli.commands.auth_commands import auth  # noqa: E402
from src.cli.commands.scoring_commands import scoring  # noqa: E402
from src.cli.commands.energy_commands import energy  # noqa: E402
from src.cli.commands.special_gems_commands import special_gems  # noqa: E402
from src.cli.commands.vault_commands import vault  # noqa: E402
from src.cli.commands.board_commands import board  # noqa: E402
from src.cli.commands.board_gen_commands import board_gen  # noqa: E402
from src.cli.commands.match_commands import match  # noqa: E402
from src.cli.commands.matchmaking_commands import matchmaking  # noqa: E402
from src.cli.commands.events_commands import events  # noqa: E402
from src.cli.commands.ads_commands import ads  # noqa: E402
from src.cli.commands.payments_commands import payments  # noqa: E402
from src.cli.commands.bot_earnings_commands import bot_earnings  # noqa: E402
from src.cli.commands.api_commands import api  # noqa: E402

cli.add_command(player)
cli.add_command(auth)
cli.add_command(scoring)
cli.add_command(energy)
cli.add_command(special_gems)
cli.add_command(vault)
cli.add_command(board)
cli.add_command(board_gen)
cli.add_command(match)
cli.add_command(matchmaking)
cli.add_command(events)
cli.add_command(ads)
cli.add_command(payments)
cli.add_command(bot_earnings)
cli.add_command(api)

# Phase 4 command groups -- guarded imports since files may not exist yet.
try:
    from src.cli.commands.cards_commands import cards as cards_group  # noqa: E402

    cli.add_command(cards_group)
except ImportError:
    pass

try:
    from src.cli.commands.economy_commands import economy as economy_group  # noqa: E402

    cli.add_command(economy_group)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    cli()
