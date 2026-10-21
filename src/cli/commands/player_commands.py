"""CLI commands for the player module.

Provides Click commands for player account management, ELO ratings,
and statistics. Uses ``run_cli_async`` to bridge synchronous Click
commands to the fully async PlayerService via ApplicationContext.

Commands:
    player create   -- Create a new player account
    player get      -- Get player by ID or username
    player list     -- List players with optional filtering
    player stats    -- Show player statistics
    player elo      -- Show player ELO rating
    player calc-elo -- Calculate ELO change for a match outcome
    player energy   -- Show player energy state
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.cli.helpers.async_bridge import resolve_player, run_cli_async
from src.core.composition_root import ApplicationContext
from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.core.types.player import PlayerType

console = Console()


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def player() -> None:
    """Player management commands."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@player.command()
@click.option("--username", required=True, help="Unique username")
@click.option("--is-bot", is_flag=True, help="Create as bot account")
@click.option("--email", default=None, help="Email address (humans only)")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def create(username: str, is_bot: bool, email: str | None, config_path: str) -> None:
    """Create a new player account."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            p_type = PlayerType.BOT if is_bot else PlayerType.HUMAN
            p = await ctx.player_service.create_player(
                username=username,
                player_type=p_type,
                email=email,
            )
            console.print(
                Panel(
                    f"[bold green]Created player:[/bold green] {p.id}\n"
                    f"  Username:  {p.username}\n"
                    f"  Type:      {p.player_type.value}\n"
                    f"  ELO:       {p.elo_rating}\n"
                    f"  Created:   {p.created_at}",
                    title="Player Created",
                )
            )
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@player.command("get")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def get_player(player_username: str, config_path: str) -> None:
    """Get player by username."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            p = await ctx.player_service.get_player(PlayerId(player_id))

            table = Table(title=f"Player {player_username}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="yellow")

            table.add_row("ID", str(p.id))
            table.add_row("Username", p.username)
            table.add_row("Type", p.player_type.value)
            table.add_row("ELO", str(p.elo_rating))
            table.add_row("Created", str(p.created_at))

            console.print(table)
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@player.command("list")
@click.option(
    "--type",
    "player_type_filter",
    type=click.Choice(["human", "bot"], case_sensitive=False),
    default=None,
    help="Filter by player type",
)
@click.option("--limit", default=50, type=int, help="Maximum results")
@click.option("--offset", default=0, type=int, help="Pagination offset")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def list_players(
    player_type_filter: str | None,
    limit: int,
    offset: int,
    config_path: str,
) -> None:
    """List players with optional filtering."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            p_type = None
            if player_type_filter is not None:
                p_type = PlayerType(player_type_filter.lower())

            result = await ctx.player_service.list_players(
                player_type=p_type,
                limit=limit,
                offset=offset,
            )

            table = Table(title=f"Players ({result.total} total)")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Username", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("ELO", justify="right")

            for p in result.items:
                table.add_row(
                    str(p.id)[:8] + "...",
                    p.username,
                    p.player_type.value,
                    str(p.elo_rating),
                )

            console.print(table)
            if result.has_more:
                console.print(
                    f"[dim]Showing {len(result.items)} of {result.total} "
                    f"(offset {result.offset})[/dim]"
                )
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@player.command("stats")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def show_stats(player_username: str, config_path: str) -> None:
    """Show player statistics."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            stats = await ctx.player_service.get_stats(PlayerId(player_id))

            table = Table(title=f"Stats for {player_username}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right", style="yellow")

            table.add_row("Total Matches", str(stats.total_matches))
            table.add_row("Wins", str(stats.wins))
            table.add_row("Losses", str(stats.losses))
            table.add_row("Draws", str(stats.draws))
            table.add_row("Win Rate", f"{stats.win_rate:.1%}")
            table.add_row("Highest Score", str(stats.highest_score))
            table.add_row("Longest Chain", str(stats.longest_chain))
            table.add_row("Total Gems", str(stats.total_gems_matched))

            console.print(table)
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@player.command("elo")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def show_elo(player_username: str, config_path: str) -> None:
    """Show player ELO rating."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            elo = await ctx.player_service.get_elo(PlayerId(player_id))
            console.print(f"ELO for {player_username}: [bold]{elo}[/bold]")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@player.command("calc-elo")
@click.argument("winner_username")
@click.argument("loser_username")
@click.option("--draw", is_flag=True, help="Calculate as draw")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def calc_elo(winner_username: str, loser_username: str, draw: bool, config_path: str) -> None:
    """Calculate ELO change for a match result (does not apply)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            winner_id = await resolve_player(ctx, winner_username)
            loser_id = await resolve_player(ctx, loser_username)
            winner_change, loser_change = await ctx.player_service.calculate_elo_change(
                winner_id=PlayerId(winner_id),
                loser_id=PlayerId(loser_id),
                is_draw=draw,
            )

            if draw:
                console.print("[bold]Draw result:[/bold]")
                console.print(f"  Player 1 change: {winner_change:+d}")
                console.print(f"  Player 2 change: {loser_change:+d}")
            else:
                console.print("[bold]Win/Loss result:[/bold]")
                console.print(f"  Winner change: {winner_change:+d}")
                console.print(f"  Loser change:  {loser_change:+d}")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@player.command("energy")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def show_energy(player_username: str, config_path: str) -> None:
    """Show player energy state."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            energy = await ctx.player_service.get_energy_state(
                PlayerId(player_id)
            )

            table = Table(title=f"Energy for {player_username}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="yellow")

            table.add_row("Hearts", f"{energy.hearts} / {energy.max_hearts}")
            table.add_row("Last Regen", str(energy.last_regen_at))
            table.add_row("Daily Streak", str(energy.daily_streak))
            table.add_row("Last Login", str(energy.last_login_date))

            console.print(table)
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)
