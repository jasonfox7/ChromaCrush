"""CLI commands for the match module.

Provides Click commands for match lifecycle management: creation,
move submission, board display, match history, forfeits, stale
match cleanup, and data purging.

Match commands are ASYNC (they hit the database). Uses ``run_cli_async``
from the shared async bridge to manage ``ApplicationContext`` lifecycle.
All services are pre-wired on the context -- no manual construction needed.

Commands:
    match create          -- Create a new versus match
    match submit-move     -- Submit a move in a match
    match show            -- Show full match state
    match board           -- Show a player's board
    match active          -- List active matches for a player
    match history         -- Show match history for a player
    match moves           -- Show move history for a match
    match forfeit         -- Forfeit a match
    match abandon-stale   -- Abandon timed-out matches
    match cleanup         -- Purge data from old completed matches
"""

from __future__ import annotations

import time
from uuid import UUID

import click
from rich.panel import Panel
from rich.table import Table

from src.cli.helpers.async_bridge import resolve_player, run_cli_async
from src.cli.helpers.display import console, render_board, render_move_result
from src.core.composition_root import ApplicationContext
from src.core.errors import AppError
from src.core.types.game import MatchId, Move, PlayerId, Position
from src.modules.match.types import MatchType


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def match() -> None:
    """Match management commands."""


# ---------------------------------------------------------------------------
# 1. match create
# ---------------------------------------------------------------------------


@match.command("create")
@click.argument("player1_username")
@click.argument("player2_username")
@click.option(
    "--seed", type=int, default=None, help="Board generation seed (random if omitted)."
)
@click.option(
    "--match-type",
    type=click.Choice(["standard", "competitive", "casual", "tutorial"]),
    default="standard",
    show_default=True,
    help="Match rule-set variant.",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def create(
    player1_username: str,
    player2_username: str,
    seed: int | None,
    match_type: str,
    config_path: str,
) -> None:
    """Create a new versus match between two players."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            p1_id = await resolve_player(ctx, player1_username)
            p2_id = await resolve_player(ctx, player2_username)

            mt = MatchType(match_type)
            state = await ctx.match_service.create_match(
                p1_id, p2_id, board_seed=seed, match_type=mt
            )

            console.print(
                Panel(
                    f"[bold green]Match created![/bold green]\n\n"
                    f"  Match ID:    {state.match_id}\n"
                    f"  Status:      {state.status.value}\n"
                    f"  Player 1:    {state.player1.player_username}\n"
                    f"  Player 2:    {state.player2.player_username}\n"
                    f"  Match Type:  {state.match_type.value}\n"
                    f"  Seed:        {state.board_seed}\n"
                    f"  Timeout:     {state.timeout_at}",
                    title="New Match",
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
# 2. match submit-move
# ---------------------------------------------------------------------------


@match.command("submit-move")
@click.argument("match_id")
@click.argument("player_username")
@click.argument("from_row", type=int)
@click.argument("from_col", type=int)
@click.argument("to_row", type=int)
@click.argument("to_col", type=int)
@click.option(
    "--timestamp", type=int, default=None, help="Client timestamp in ms (default: now)."
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed cascade output with position lists.",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def submit_move(
    match_id: str,
    player_username: str,
    from_row: int,
    from_col: int,
    to_row: int,
    to_col: int,
    timestamp: int | None,
    verbose: bool,
    config_path: str,
) -> None:
    """Submit a move for a player in an active match."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            mid = MatchId(UUID(match_id))

            ts = timestamp if timestamp is not None else int(time.time() * 1000)
            move = Move(
                from_pos=Position(from_row, from_col),
                to_pos=Position(to_row, to_col),
                timestamp_ms=ts,
            )

            result = await ctx.match_service.submit_move(mid, player_id, move)

            lines = [
                "[bold green]Move submitted![/bold green]\n",
                f"  Points earned:     {result.points_earned}",
                f"  Moves remaining:   {result.moves_remaining}",
                f"  Chain count:       {result.move_result.chain_count}",
                f"  Gems cleared:      {result.move_result.total_gems_cleared}",
                f"  Move number:       {result.move_number}",
                f"  Player finished:   {result.player_finished}",
                f"  Match completed:   {result.match_completed}",
            ]

            if result.match_completed and result.winner_id is not None:
                lines.append(f"  Winner:            {result.winner_id}")
            elif result.match_completed:
                lines.append("  Result:            Draw")

            console.print(
                Panel(
                    "\n".join(lines),
                    title="Move Result",
                )
            )

            # Show detailed cascade output if verbose.
            if verbose:
                render_move_result(result.move_result, verbose=True)

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
# 3. match show
# ---------------------------------------------------------------------------


@match.command("show")
@click.argument("match_id")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def show(match_id: str, config_path: str) -> None:
    """Show full match state."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            mid = MatchId(UUID(match_id))
            state = await ctx.match_service.get_match(mid)

            p1 = state.player1
            p2 = state.player2

            winner_str = "N/A"
            if state.winner_id is not None:
                if state.winner_id == p1.player_id:
                    winner_str = p1.player_username
                elif state.winner_id == p2.player_id:
                    winner_str = p2.player_username
                else:
                    winner_str = str(state.winner_id)

            forfeit_str = "N/A"
            if state.forfeit_by is not None:
                if state.forfeit_by == p1.player_id:
                    forfeit_str = p1.player_username
                elif state.forfeit_by == p2.player_id:
                    forfeit_str = p2.player_username

            lines = [
                f"[bold]Match {state.match_id}[/bold]\n",
                f"  Status:       {state.status.value}",
                f"  Type:         {state.match_type.value}",
                f"  Seed:         {state.board_seed}",
                f"  Created:      {state.created_at}",
                f"  Started:      {state.started_at or 'N/A'}",
                f"  Completed:    {state.completed_at or 'N/A'}",
                f"  Timeout:      {state.timeout_at or 'N/A'}",
                f"  Winner:       {winner_str}",
                f"  Forfeit by:   {forfeit_str}",
                "",
                f"  [cyan]Player 1: {p1.player_username}[/cyan]",
                f"    Score:           {p1.score}",
                f"    Moves made:      {p1.moves_made}",
                f"    Moves remaining: {p1.moves_remaining}",
                f"    Longest chain:   {p1.longest_chain}",
                f"    Finished at:     {p1.finished_at or 'N/A'}",
                "",
                f"  [cyan]Player 2: {p2.player_username}[/cyan]",
                f"    Score:           {p2.score}",
                f"    Moves made:      {p2.moves_made}",
                f"    Moves remaining: {p2.moves_remaining}",
                f"    Longest chain:   {p2.longest_chain}",
                f"    Finished at:     {p2.finished_at or 'N/A'}",
            ]

            console.print(
                Panel(
                    "\n".join(lines),
                    title="Match State",
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
# 4. match board
# ---------------------------------------------------------------------------


@match.command("board")
@click.argument("match_id")
@click.argument("player_username")
@click.option(
    "--no-functions",
    is_flag=True,
    default=False,
    help="Disable function overlay in board display.",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def board(
    match_id: str, player_username: str, no_functions: bool, config_path: str
) -> None:
    """Show a player's current board in a match."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            mid = MatchId(UUID(match_id))

            board_state = await ctx.match_service.get_player_board(mid, player_id)

            console.print(
                f"\n[bold]Board for {player_username} in match {match_id[:8]}...[/bold]"
            )
            console.print(f"  Score:           {board_state.score}")
            console.print(f"  Moves made:      {board_state.moves_made}")
            console.print(f"  Moves remaining: {board_state.moves_remaining}")
            console.print(f"  Has valid moves: {board_state.has_valid_moves}")
            console.print()
            render_board(board_state.board, show_functions=not no_functions)
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
# 5. match active
# ---------------------------------------------------------------------------


@match.command("active")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def active(player_username: str, config_path: str) -> None:
    """List active matches for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            matches = await ctx.match_service.get_active_matches(player_id)

            if not matches:
                console.print(f"No active matches for {player_username}.")
                return

            table = Table(title=f"Active Matches for {player_username}")
            table.add_column("Match ID", style="cyan", no_wrap=True)
            table.add_column("Status", style="green")
            table.add_column("Type")
            table.add_column("Opponent")
            table.add_column("Your Score", justify="right")
            table.add_column("Opp Score", justify="right")
            table.add_column("Moves Left", justify="right")
            table.add_column("Created")

            for m in matches:
                # Determine which player we are.
                if m.player1.player_id == player_id:
                    my_state = m.player1
                    opp_state = m.player2
                else:
                    my_state = m.player2
                    opp_state = m.player1

                table.add_row(
                    str(m.match_id)[:8] + "...",
                    m.status.value,
                    m.match_type.value,
                    opp_state.player_username,
                    str(my_state.score),
                    str(opp_state.score),
                    str(my_state.moves_remaining),
                    str(m.created_at),
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


# ---------------------------------------------------------------------------
# 6. match history
# ---------------------------------------------------------------------------


@match.command("history")
@click.argument("player_username")
@click.option("--limit", default=20, type=int, show_default=True, help="Max results.")
@click.option(
    "--offset", default=0, type=int, show_default=True, help="Pagination offset."
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def history(player_username: str, limit: int, offset: int, config_path: str) -> None:
    """Show match history for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.match_service.get_match_history(
                player_id, limit=limit, offset=offset
            )

            if not result.items:
                console.print(f"No match history for {player_username}.")
                return

            table = Table(title=f"Match History for {player_username}")
            table.add_column("Match ID", style="cyan", no_wrap=True)
            table.add_column("Status", style="green")
            table.add_column("Type")
            table.add_column("Opponent")
            table.add_column("Score", justify="right")
            table.add_column("Opp Score", justify="right")
            table.add_column("Result")
            table.add_column("Date")

            for s in result.items:
                if s.won is True:
                    result_str = "[green]WIN[/green]"
                elif s.won is False:
                    result_str = "[red]LOSS[/red]"
                elif s.status.value == "completed":
                    result_str = "[yellow]DRAW[/yellow]"
                else:
                    result_str = "[dim]--[/dim]"

                table.add_row(
                    str(s.match_id)[:8] + "...",
                    s.status.value,
                    s.match_type.value,
                    s.opponent_username,
                    str(s.player_score),
                    str(s.opponent_score),
                    result_str,
                    str(s.created_at),
                )

            console.print(table)
            console.print(
                f"\nShowing {offset + 1}-{offset + len(result.items)} of {result.total} "
                f"(has more: {result.has_more})"
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
# 7. match moves
# ---------------------------------------------------------------------------


@match.command("moves")
@click.argument("match_id")
@click.option(
    "--player", "player_username", default=None, help="Filter by player username."
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def moves(match_id: str, player_username: str | None, config_path: str) -> None:
    """Show move history for a match."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            mid = MatchId(UUID(match_id))

            filter_player_id: PlayerId | None = None
            if player_username is not None:
                filter_player_id = await resolve_player(ctx, player_username)

            move_records = await ctx.match_service.get_move_history(
                mid, player_id=filter_player_id
            )

            if not move_records:
                console.print(f"No moves recorded for match {match_id[:8]}...")
                return

            table = Table(title=f"Move History for {match_id[:8]}...")
            table.add_column("#", style="bold", justify="right")
            table.add_column("Player", style="cyan")
            table.add_column("From", justify="center")
            table.add_column("To", justify="center")
            table.add_column("Score", justify="right", style="green")
            table.add_column("Chain", justify="right")
            table.add_column("Cleared", justify="right")
            table.add_column("Timestamp")

            for mr in move_records:
                table.add_row(
                    str(mr.move_number),
                    str(mr.player_id)[:8] + "...",
                    f"({mr.move.from_pos.row},{mr.move.from_pos.col})",
                    f"({mr.move.to_pos.row},{mr.move.to_pos.col})",
                    str(mr.score_earned),
                    str(mr.chain_count),
                    str(mr.gems_cleared),
                    str(mr.timestamp),
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


# ---------------------------------------------------------------------------
# 8. match forfeit
# ---------------------------------------------------------------------------


@match.command("forfeit")
@click.argument("match_id")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def forfeit(match_id: str, player_username: str, config_path: str) -> None:
    """Forfeit a match, declaring the opponent as winner."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            mid = MatchId(UUID(match_id))

            state = await ctx.match_service.forfeit_match(mid, player_id)

            winner_name = "N/A"
            if state.winner_id is not None:
                if state.winner_id == state.player1.player_id:
                    winner_name = state.player1.player_username
                elif state.winner_id == state.player2.player_id:
                    winner_name = state.player2.player_username

            console.print(
                Panel(
                    f"[bold yellow]Match forfeited[/bold yellow]\n\n"
                    f"  Match ID:  {state.match_id}\n"
                    f"  Status:    {state.status.value}\n"
                    f"  Winner:    {winner_name}\n"
                    f"  Forfeit:   {player_username}",
                    title="Forfeit Result",
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
# 9. match abandon-stale
# ---------------------------------------------------------------------------


@match.command("abandon-stale")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def abandon_stale(config_path: str) -> None:
    """Abandon matches that have exceeded their timeout."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            count = await ctx.match_service.abandon_stale_matches()

            if count > 0:
                console.print(
                    f"[bold yellow]Abandoned {count} stale match(es).[/bold yellow]"
                )
            else:
                console.print("[dim]No stale matches to abandon.[/dim]")
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
# 10. match cleanup
# ---------------------------------------------------------------------------


@match.command("cleanup")
@click.option(
    "--older-than",
    type=int,
    default=1,
    show_default=True,
    help="Only clean matches completed more than this many hours ago.",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def cleanup(older_than: int, config_path: str) -> None:
    """Clean up board states, moves, and raid data from completed matches.

    Removes heavy data (board states, move records, raid data) from
    completed and abandoned matches while preserving metadata (scores,
    winner, timestamps) for match history. Useful as a fallback when
    the automatic deferred cleanup was missed (e.g., server restart).
    """

    async def _do(ctx: ApplicationContext) -> None:
        try:
            count = await ctx.match_service.cleanup_completed_matches(
                older_than_hours=older_than,
            )

            if count > 0:
                console.print(f"[bold green]Cleaned up {count} match(es).[/bold green]")
            else:
                console.print("[dim]No matches to clean up.[/dim]")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)
