"""CLI commands for the matchmaking module.

Provides Click commands for matchmaking queue management: joining,
leaving, status checking, match finding, queue processing, stale
cleanup, and statistics. Uses ``run_cli_async`` to bridge synchronous
Click commands to the fully async MatchmakingService via
ApplicationContext.

Commands:
    matchmaking join       -- Join the matchmaking queue
    matchmaking leave      -- Leave the matchmaking queue
    matchmaking status     -- Check queue status for a player
    matchmaking find       -- Attempt to find a match for a player
    matchmaking process    -- Process a queue pool (admin)
    matchmaking cleanup    -- Remove stale queue entries (admin)
    matchmaking stats      -- Show queue statistics
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
from src.modules.matchmaking.types import MatchmakingStatus, PoolType

console = Console()


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def matchmaking() -> None:
    """Matchmaking queue management commands."""


# ---------------------------------------------------------------------------
# 1. matchmaking join
# ---------------------------------------------------------------------------


@matchmaking.command("join")
@click.argument("player_username")
@click.option(
    "--pool",
    type=click.Choice(["human", "bot", "mixed"]),
    default="mixed",
    show_default=True,
    help="Queue pool to join.",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def join(player_username: str, pool: str, config_path: str) -> None:
    """Join the matchmaking queue."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            pool_type = PoolType(pool)

            entry = await ctx.matchmaking_service.join_queue(player_id, pool_type)

            estimate_str = (
                f"{entry.estimated_wait_seconds} seconds"
                if entry.estimated_wait_seconds is not None
                else "unknown"
            )

            console.print(
                Panel(
                    f"[bold green]Joined matchmaking queue![/bold green]\n\n"
                    f"  Player:         {entry.player_username} ({entry.player_id})\n"
                    f"  Pool:           {entry.pool_type.value}\n"
                    f"  ELO:            {entry.elo_rating}\n"
                    f"  Search range:   {entry.current_elo_range[0]} - {entry.current_elo_range[1]}\n"
                    f"  Queue position: {entry.position_in_queue}\n"
                    f"  Estimated wait: {estimate_str}",
                    title="Queue Joined",
                )
            )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


# ---------------------------------------------------------------------------
# 2. matchmaking leave
# ---------------------------------------------------------------------------


@matchmaking.command("leave")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def leave(player_username: str, config_path: str) -> None:
    """Leave the matchmaking queue."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            removed = await ctx.matchmaking_service.leave_queue(player_id)

            if removed:
                console.print(
                    f"[bold yellow]{player_username} left the matchmaking queue.[/bold yellow]"
                )
            else:
                console.print(
                    f"[dim]{player_username} was not in any matchmaking queue.[/dim]"
                )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


# ---------------------------------------------------------------------------
# 3. matchmaking status
# ---------------------------------------------------------------------------


@matchmaking.command("status")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def status(player_username: str, config_path: str) -> None:
    """Check queue status for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            queue_status = await ctx.matchmaking_service.get_queue_status(player_id)

            if queue_status is None:
                console.print(
                    f"[dim]{player_username} is not in any matchmaking queue.[/dim]"
                )
                return

            estimate_str = (
                f"{queue_status.estimated_wait_seconds} seconds"
                if queue_status.estimated_wait_seconds is not None
                else "unknown"
            )

            console.print(
                Panel(
                    f"[bold]Queue Status[/bold]\n\n"
                    f"  Player:              {player_username} ({queue_status.player_id})\n"
                    f"  Pool:                {queue_status.pool_type.value}\n"
                    f"  ELO:                 {queue_status.elo_rating}\n"
                    f"  Wait time:           {queue_status.wait_time_seconds} seconds\n"
                    f"  Search range:        {queue_status.current_elo_range[0]} - {queue_status.current_elo_range[1]}\n"
                    f"  Potential opponents: {queue_status.potential_opponents}\n"
                    f"  Queue position:      {queue_status.position_in_queue}\n"
                    f"  Estimated wait:      {estimate_str}",
                    title="Queue Status",
                )
            )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


# ---------------------------------------------------------------------------
# 4. matchmaking find
# ---------------------------------------------------------------------------


@matchmaking.command("find")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def find(player_username: str, config_path: str) -> None:
    """Attempt to find a match for a queued player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.matchmaking_service.find_match(player_id)

            if result.status == MatchmakingStatus.MATCHED:
                console.print(
                    Panel(
                        f"[bold green]Match found![/bold green]\n\n"
                        f"  Match ID:        {result.match_id}\n"
                        f"  Opponent:        {result.opponent_id}\n"
                        f"  ELO difference:  {result.elo_difference}\n"
                        f"  Wait time:       {result.wait_time_seconds} seconds",
                        title="Match Found",
                    )
                )
            elif result.status == MatchmakingStatus.SEARCHING:
                console.print(
                    Panel(
                        f"[bold yellow]Still searching...[/bold yellow]\n\n"
                        f"  {result.message}\n"
                        f"  Wait time: {result.wait_time_seconds} seconds",
                        title="Searching",
                    )
                )
            elif result.status == MatchmakingStatus.EXPIRED:
                console.print(
                    Panel(
                        f"[bold red]Queue timeout[/bold red]\n\n"
                        f"  {result.message}\n"
                        f"  Total wait: {result.wait_time_seconds} seconds",
                        title="Expired",
                        border_style="red",
                    )
                )
            else:
                console.print(
                    Panel(
                        f"[bold]{result.message}[/bold]\n\n"
                        f"  Status: {result.status.value}",
                        title="Result",
                    )
                )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


# ---------------------------------------------------------------------------
# 5. matchmaking process
# ---------------------------------------------------------------------------


@matchmaking.command("process")
@click.option(
    "--pool",
    type=click.Choice(["human", "bot", "mixed", "all"]),
    default="all",
    show_default=True,
    help="Queue pool to process.",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def process(pool: str, config_path: str) -> None:
    """Process a queue pool to create matches (admin)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            if pool == "all":
                pools = list(PoolType)
            else:
                pools = [PoolType(pool)]

            total_matches = 0
            lines = ["[bold]Processing queues...[/bold]\n"]

            for pt in pools:
                results = await ctx.matchmaking_service.process_queue(pt)
                matches_created = sum(
                    1 for r in results if r.status == MatchmakingStatus.MATCHED
                )
                total_matches += matches_created
                lines.append(f"  {pt.value}: {matches_created} matches created")

            lines.append(f"\nTotal: {total_matches} matches created")

            console.print(
                Panel(
                    "\n".join(lines),
                    title="Queue Processing",
                )
            )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


# ---------------------------------------------------------------------------
# 6. matchmaking cleanup
# ---------------------------------------------------------------------------


@matchmaking.command("cleanup")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def cleanup(config_path: str) -> None:
    """Remove stale queue entries (admin)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            count = await ctx.matchmaking_service.cleanup_stale_entries()

            if count > 0:
                console.print(
                    f"[bold yellow]Removed {count} stale queue entry(ies).[/bold yellow]"
                )
            else:
                console.print("[dim]No stale entries to clean up.[/dim]")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


# ---------------------------------------------------------------------------
# 7. matchmaking stats
# ---------------------------------------------------------------------------


@matchmaking.command("stats")
@click.option(
    "--pool",
    type=click.Choice(["human", "bot", "mixed"]),
    default=None,
    help="Filter by pool type (default: all).",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def stats(pool: str | None, config_path: str) -> None:
    """Show queue statistics."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            pool_type = PoolType(pool) if pool else None
            queue_stats = await ctx.matchmaking_service.get_queue_stats(pool_type)

            pool_label = pool_type.value if pool_type else "all"

            lines = [
                f"[bold]Queue Statistics ({pool_label}):[/bold]\n",
                f"  Total players:      {queue_stats.total_players}",
            ]

            if queue_stats.players_by_elo_bucket:
                lines.append("  ELO distribution:")
                for bucket, count in sorted(queue_stats.players_by_elo_bucket.items()):
                    lines.append(f"    {bucket}: {count} players")

            lines.extend(
                [
                    f"  Average wait:       {queue_stats.average_wait_seconds:.1f} seconds",
                    f"  Longest wait:       {queue_stats.longest_wait_seconds} seconds",
                    f"  Matches (last hr):  {queue_stats.matches_created_last_hour}",
                    f"  Avg ELO diff:       {queue_stats.average_elo_difference:.1f}",
                ]
            )

            console.print(
                Panel(
                    "\n".join(lines),
                    title="Queue Statistics",
                )
            )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)
