"""CLI commands for the events module.

Provides Click commands for event lifecycle management: creation, joining,
match recording, leaderboard display, finalization, and background processing.
Uses ``run_cli_async`` to bridge synchronous Click commands to the fully async
EventService via ApplicationContext.

Commands:
    events create            -- Create a new event
    events get               -- Show event details
    events list              -- List events with optional filters
    events active            -- List currently active events
    events join              -- Join an event
    events leave             -- Leave an event
    events record-match      -- Record match score for event
    events leaderboard       -- Show event leaderboard
    events rank              -- Show player rank in event
    events player-events     -- Show events for a player
    events finalize          -- Finalize event and distribute rewards
    events cancel            -- Cancel an event
    events update            -- Update event details
    events process-scheduled -- Run scheduled event processing
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.cli.helpers.async_bridge import resolve_player, run_cli_async
from src.core.composition_root import ApplicationContext
from src.core.errors import AppError
from src.core.types.game import EventId, MatchId, PlayerId
from src.modules.events.dto import EventCreate, EventUpdate
from src.modules.events.types import (
    EventStatus,
    EventType,
    MatchEventStats,
)

console = Console()


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def events() -> None:
    """Event management commands."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@events.command("create")
@click.option("--name", required=True, help="Event name.")
@click.option(
    "--type",
    "event_type",
    type=click.Choice(["flash", "weekly", "seasonal"]),
    required=True,
)
@click.option("--start", "start_at", required=True, help="Start time (ISO 8601).")
@click.option("--end", "end_at", required=True, help="End time (ISO 8601).")
@click.option(
    "--scoring",
    type=click.Choice(["total_score", "best_match", "matches_played", "average_score"]),
    default="total_score",
)
@click.option("--description", default="", help="Event description.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def create(
    name: str,
    event_type: str,
    start_at: str,
    end_at: str,
    scoring: str,
    description: str,
    config_path: str,
) -> None:
    """Create a new event."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            data = EventCreate(
                name=name,
                description=description,
                event_type=event_type,
                scoring_type=scoring,
                start_at=datetime.fromisoformat(start_at),
                end_at=datetime.fromisoformat(end_at),
                entry_requirements={},
                reward_tiers=[],
                rules={},
            )
            event = await ctx.event_service.create_event(data)
            console.print(
                Panel(
                    f"[bold green]Event created![/bold green]\n\n"
                    f"  ID:      {event.id}\n"
                    f"  Name:    {event.name}\n"
                    f"  Type:    {event.event_type.value}\n"
                    f"  Status:  {event.status.value}\n"
                    f"  Starts:  {event.start_at}\n"
                    f"  Ends:    {event.end_at}",
                    title="New Event",
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


@events.command("get")
@click.argument("event_id")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def get(event_id: str, config_path: str) -> None:
    """Show event details."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            eid = EventId(UUID(event_id))
            event = await ctx.event_service.get_event(eid)
            console.print(
                Panel(
                    f"[bold]{event.name}[/bold]\n\n"
                    f"  ID:            {event.id}\n"
                    f"  Type:          {event.event_type.value}\n"
                    f"  Status:        {event.status.value}\n"
                    f"  Scoring:       {event.scoring_type.value}\n"
                    f"  Participants:  {event.participant_count}\n"
                    f"  Max:           {event.max_participants or 'unlimited'}\n"
                    f"  Starts:        {event.start_at}\n"
                    f"  Ends:          {event.end_at}\n"
                    f"  Activated:     {event.activated_at or 'N/A'}\n"
                    f"  Finalized:     {event.finalized_at or 'N/A'}",
                    title="Event Details",
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


@events.command("list")
@click.option(
    "--status",
    type=click.Choice(["scheduled", "active", "ended", "finalized", "cancelled"]),
    default=None,
)
@click.option(
    "--type",
    "event_type",
    type=click.Choice(["flash", "weekly", "seasonal"]),
    default=None,
)
@click.option("--limit", default=20, type=int)
@click.option("--offset", default=0, type=int)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def list_cmd(
    status: str | None,
    event_type: str | None,
    limit: int,
    offset: int,
    config_path: str,
) -> None:
    """List events."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            s = EventStatus(status) if status else None
            t = EventType(event_type) if event_type else None
            result = await ctx.event_service.list_events(
                status=s, event_type=t, limit=limit, offset=offset
            )
            if not result.items:
                console.print("No events found.")
                return
            table = Table(title="Events")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("Status", style="green")
            table.add_column("Participants", justify="right")
            table.add_column("Starts")
            table.add_column("Ends")
            for e in result.items:
                table.add_row(
                    str(e.id)[:8] + "...",
                    e.name,
                    e.event_type.value,
                    e.status.value,
                    str(e.participant_count),
                    str(e.start_at),
                    str(e.end_at),
                )
            console.print(table)
            console.print(
                f"\nShowing {offset + 1}-{offset + len(result.items)} of {result.total}"
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


@events.command("active")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def active(config_path: str) -> None:
    """List currently active events."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            evts = await ctx.event_service.get_active_events()
            if not evts:
                console.print("No active events.")
                return
            table = Table(title="Active Events")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("Participants", justify="right")
            table.add_column("Ends")
            for e in evts:
                table.add_row(
                    str(e.id)[:8] + "...",
                    e.name,
                    e.event_type.value,
                    str(e.participant_count),
                    str(e.end_at),
                )
            console.print(table)
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


@events.command("join")
@click.argument("event_id")
@click.option("--player", required=True, help="Player username.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def join(event_id: str, player: str, config_path: str) -> None:
    """Join an event."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            eid = EventId(UUID(event_id))
            pid = PlayerId(await resolve_player(ctx, player))
            p = await ctx.event_service.join_event(eid, pid)
            console.print(
                Panel(
                    f"[bold green]Joined event![/bold green]\n\n"
                    f"  Player:  {p.player_username}\n"
                    f"  Rank:    {p.current_rank}",
                    title="Join Result",
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


@events.command("leave")
@click.argument("event_id")
@click.option("--player", required=True, help="Player username.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def leave(event_id: str, player: str, config_path: str) -> None:
    """Leave an event."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            eid = EventId(UUID(event_id))
            pid = PlayerId(await resolve_player(ctx, player))
            await ctx.event_service.leave_event(eid, pid)
            console.print("[bold yellow]Left event.[/bold yellow]")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


@events.command("record-match")
@click.argument("event_id")
@click.option("--player", required=True, help="Player username.")
@click.option("--match", "match_id", required=True, help="Match ID (UUID).")
@click.option("--score", required=True, type=int, help="Score achieved.")
@click.option("--chains", default=0, type=int, help="Chain count.")
@click.option("--gems", default=0, type=int, help="Gems cleared.")
@click.option("--specials", default=0, type=int, help="Special gems activated.")
@click.option("--duration", default=0, type=int, help="Match duration in seconds.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def record_match(
    event_id: str,
    player: str,
    match_id: str,
    score: int,
    chains: int,
    gems: int,
    specials: int,
    duration: int,
    config_path: str,
) -> None:
    """Record match score for event."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            eid = EventId(UUID(event_id))
            pid = PlayerId(await resolve_player(ctx, player))
            mid = MatchId(UUID(match_id))
            stats = MatchEventStats(
                chain_count=chains,
                gems_cleared=gems,
                special_gems_activated=specials,
                match_duration_seconds=duration,
            )
            p = await ctx.event_service.record_event_match(eid, pid, mid, score, stats)
            console.print(
                Panel(
                    f"[bold green]Match recorded![/bold green]\n\n"
                    f"  Score:        {score}\n"
                    f"  Total Score:  {p.total_score}\n"
                    f"  Matches:      {p.matches_played}\n"
                    f"  Rank:         {p.current_rank}",
                    title="Match Result",
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


@events.command("leaderboard")
@click.argument("event_id")
@click.option("--limit", default=100, type=int)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def leaderboard(event_id: str, limit: int, config_path: str) -> None:
    """Show event leaderboard."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            eid = EventId(UUID(event_id))
            lb = await ctx.event_service.get_leaderboard(eid, limit=limit)
            console.print(f"\n[bold]Leaderboard: {lb.event_name}[/bold]")
            console.print(f"  Status: {lb.event_status.value}")
            console.print(f"  Participants: {lb.total_participants}\n")
            table = Table()
            table.add_column("Rank", justify="right", style="bold")
            table.add_column("Player", style="cyan")
            table.add_column("Score", justify="right")
            table.add_column("Matches", justify="right")
            for e in lb.entries:
                table.add_row(
                    str(e.rank), e.player_username, str(e.score), str(e.matches_played)
                )
            console.print(table)
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


@events.command("rank")
@click.argument("event_id")
@click.option("--player", required=True, help="Player username.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def rank(event_id: str, player: str, config_path: str) -> None:
    """Show player rank in event."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            eid = EventId(UUID(event_id))
            pid = PlayerId(await resolve_player(ctx, player))
            r = await ctx.event_service.get_player_rank(eid, pid)
            console.print(
                Panel(
                    f"  Rank:         {r.rank} / {r.total_participants}\n"
                    f"  Percentile:   Top {100 - r.percentile:.1f}%\n"
                    f"  Score:        {r.score}\n"
                    f"  Matches:      {r.matches_played}\n"
                    f"  Reward Tier:  {r.reward_tier or 'None'}",
                    title="Player Rank",
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


@events.command("player-events")
@click.argument("player_username")
@click.option("--include-past", is_flag=True, default=False)
@click.option("--limit", default=20, type=int)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def player_events(
    player_username: str, include_past: bool, limit: int, config_path: str
) -> None:
    """Show events for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            result = await ctx.event_service.get_player_events(
                pid, include_past=include_past, limit=limit
            )
            if not result.items:
                console.print("No events found for this player.")
                return
            table = Table(title="Player Events")
            table.add_column("Event", style="cyan")
            table.add_column("Type")
            table.add_column("Status")
            table.add_column("Rank", justify="right")
            table.add_column("Score", justify="right")
            table.add_column("Matches", justify="right")
            for s in result.items:
                table.add_row(
                    s.event_name,
                    s.event_type.value,
                    s.event_status.value,
                    str(s.player_rank or "-"),
                    str(s.player_score),
                    str(s.matches_played),
                )
            console.print(table)
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


@events.command("finalize")
@click.argument("event_id")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def finalize(event_id: str, config_path: str) -> None:
    """Finalize event and distribute rewards."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            eid = EventId(UUID(event_id))
            result = await ctx.event_service.finalize_event(eid)
            lines = [
                f"[bold green]Event finalized![/bold green]\n",
                f"  Total Participants:  {result.total_participants}",
                f"  Rewards Distributed: {result.rewards_distributed}",
                f"  Summary:",
            ]
            for tier, count in result.reward_summary.items():
                lines.append(f"    {tier}: {count}")
            if result.top_players:
                lines.append(f"  Top Players:")
                for p in result.top_players[:3]:
                    lines.append(f"    {p.rank}. {p.player_username} ({p.score})")
            console.print(Panel("\n".join(lines), title="Finalization Result"))
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


@events.command("cancel")
@click.argument("event_id")
@click.option("--reason", required=True, help="Cancellation reason.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def cancel(event_id: str, reason: str, config_path: str) -> None:
    """Cancel an event."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            eid = EventId(UUID(event_id))
            event = await ctx.event_service.cancel_event(eid, reason)
            console.print(
                Panel(
                    f"[bold yellow]Event cancelled[/bold yellow]\n\n"
                    f"  ID:      {event.id}\n"
                    f"  Status:  {event.status.value}",
                    title="Cancellation Result",
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


@events.command("update")
@click.argument("event_id")
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def update(
    event_id: str, name: str | None, description: str | None, config_path: str
) -> None:
    """Update event details."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            eid = EventId(UUID(event_id))
            updates = EventUpdate(name=name, description=description)
            event = await ctx.event_service.update_event(eid, updates)
            console.print(
                Panel(
                    f"[bold green]Event updated![/bold green]\n\n"
                    f"  Name:  {event.name}\n"
                    f"  Status: {event.status.value}",
                    title="Update Result",
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


@events.command("process-scheduled")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def process_scheduled(config_path: str) -> None:
    """Run scheduled event processing."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            result = await ctx.event_service.process_scheduled_events()
            lines = [
                f"  Activated:   {len(result.activated)}",
                f"  Deactivated: {len(result.deactivated)}",
                f"  Finalized:   {len(result.finalized)}",
                f"  Processed:   {result.processed_at}",
            ]
            console.print(Panel("\n".join(lines), title="Scheduled Processing"))
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)
