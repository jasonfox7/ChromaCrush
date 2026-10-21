"""CLI commands for the energy module.

Provides Click commands for energy/hearts management, regeneration,
daily login streaks, and bonus heart grants. Uses ``run_cli_async``
to bridge synchronous Click commands to the fully async EnergyService
via ApplicationContext.

Commands:
    energy get          -- Get player's current energy state
    energy consume      -- Consume hearts
    energy can-play     -- Check if player can play
    energy regen        -- Apply pending regeneration
    energy time-to-heart -- Show time to next heart
    energy login        -- Record a login
    energy streak       -- Show streak info
    energy grant        -- Grant bonus hearts
    energy refund       -- Refund hearts
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
from src.modules.energy.dto import BonusSource

console = Console()


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def energy() -> None:
    """Energy/hearts management commands."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@energy.command("get")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def get_energy(player_username: str, config_path: str) -> None:
    """Get player's current energy state."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            info = await ctx.energy_service.get_energy(PlayerId(player_id))

            table = Table(title=f"Energy for {player_username}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="yellow")

            table.add_row("Hearts", f"{info.current_hearts}/{info.max_hearts}")
            if info.seconds_to_next_heart is not None:
                mins, secs = divmod(info.seconds_to_next_heart, 60)
                table.add_row("Next heart in", f"{mins}m {secs}s")
            else:
                table.add_row("Status", "FULL")
            table.add_row("Daily streak", f"{info.daily_streak} days")
            table.add_row("Last login", str(info.last_login_date))

            console.print(table)
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@energy.command("consume")
@click.argument("player_username")
@click.option("--amount", default=1, type=int, help="Hearts to consume")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def consume_heart(player_username: str, amount: int, config_path: str) -> None:
    """Consume hearts (e.g., to start a match)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.energy_service.consume_heart(
                PlayerId(player_id),
                amount=amount,
            )
            console.print(
                f"[bold green]Consumed {result.hearts_consumed} heart(s)[/bold green]"
            )
            console.print(f"  Remaining: {result.hearts_remaining}")
            if result.hearts_regenerated_before_consume > 0:
                console.print(
                    f"  (Regenerated {result.hearts_regenerated_before_consume} first)"
                )
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@energy.command("can-play")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def can_play(player_username: str, config_path: str) -> None:
    """Check if player has enough hearts to play."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.energy_service.can_play(PlayerId(player_id))
            if result:
                console.print("[bold green]Player can play[/bold green]")
            else:
                console.print(
                    "[bold red]Player cannot play (insufficient hearts)[/bold red]"
                )
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@energy.command("regen")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def apply_regen(player_username: str, config_path: str) -> None:
    """Apply pending heart regeneration."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.energy_service.apply_pending_regeneration(
                PlayerId(player_id)
            )
            if result.hearts_added > 0:
                console.print(
                    f"[bold green]Regenerated {result.hearts_added} heart(s)"
                    f"[/bold green]"
                )
            else:
                console.print("[dim]No hearts to regenerate[/dim]")
            console.print(
                f"  Hearts: {result.hearts_before} -> {result.hearts_after}"
            )
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@energy.command("time-to-heart")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def time_to_heart(player_username: str, config_path: str) -> None:
    """Show time until next heart regenerates."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.energy_service.get_time_to_next_heart(
                PlayerId(player_id)
            )
            if result.is_full:
                console.print(
                    f"[bold green]Hearts full "
                    f"({result.current_hearts}/{result.max_hearts})[/bold green]"
                )
            else:
                mins, secs = divmod(result.seconds_remaining, 60)
                console.print(f"Next heart in: [bold]{mins}m {secs}s[/bold]")
                console.print(
                    f"  Hearts: {result.current_hearts}/{result.max_hearts}"
                )
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@energy.command("login")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def record_login(player_username: str, config_path: str) -> None:
    """Record a login for streak tracking."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.energy_service.record_login(
                PlayerId(player_id)
            )

            console.print(
                f"[bold]Login recorded for player {player_username}[/bold]"
            )
            console.print(f"  Streak day: {result.streak_day}")
            if result.streak_continued:
                console.print("  [green]Streak continued![/green]")
            elif result.streak_broken:
                console.print("  [red]Streak broken - reset to day 1[/red]")
            else:
                console.print("  [dim]Same-day login[/dim]")

            if result.bonus_hearts_granted > 0:
                console.print(
                    f"  [bold yellow]BONUS: "
                    f"+{result.bonus_hearts_granted} hearts![/bold yellow]"
                )
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@energy.command("streak")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def get_streak(player_username: str, config_path: str) -> None:
    """Get player's streak information."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            info = await ctx.energy_service.get_streak(PlayerId(player_id))

            table = Table(title=f"Streak for {player_username}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="yellow")

            table.add_row("Current streak", f"{info.current_streak} days")
            table.add_row("Last login", str(info.last_login_date))
            table.add_row("Streak started", str(info.streak_started_at))
            table.add_row("Next reward at", f"day {info.next_reward_threshold}")
            table.add_row("Days until reward", str(info.days_until_reward))
            table.add_row("Reward amount", f"+{info.reward_hearts} hearts")

            console.print(table)
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@energy.command("grant")
@click.argument("player_username")
@click.option("--amount", required=True, type=int, help="Hearts to grant")
@click.option(
    "--source",
    required=True,
    type=click.Choice(
        [
            "ad_reward",
            "streak_bonus",
            "event_reward",
            "referral",
            "compensation",
            "promotion",
        ],
        case_sensitive=False,
    ),
    help="Source of bonus hearts",
)
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def grant_bonus(player_username: str, amount: int, source: str, config_path: str) -> None:
    """Grant bonus hearts to a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.energy_service.grant_bonus_hearts(
                PlayerId(player_id),
                amount=amount,
                source=BonusSource(source),
            )

            if result.already_claimed:
                console.print("[yellow]Bonus already claimed[/yellow]")
            else:
                console.print(
                    f"[bold green]Granted {result.hearts_granted} "
                    f"bonus heart(s)[/bold green]"
                )
            console.print(f"  Source: {result.source.value}")
            console.print(
                f"  Hearts: {result.hearts_before} -> {result.hearts_after}"
            )
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@energy.command("refund")
@click.argument("player_username")
@click.option("--amount", default=1, type=int, help="Hearts to refund")
@click.option("--reason", default="match_cancelled", help="Reason for refund")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def refund_heart(
    player_username: str, amount: int, reason: str, config_path: str
) -> None:
    """Refund hearts to a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            info = await ctx.energy_service.refund_heart(
                PlayerId(player_id),
                amount=amount,
                reason=reason,
            )
            console.print(f"[bold green]Refunded {amount} heart(s)[/bold green]")
            console.print(f"  Hearts: {info.current_hearts}/{info.max_hearts}")
            console.print(f"  Reason: {reason}")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)
