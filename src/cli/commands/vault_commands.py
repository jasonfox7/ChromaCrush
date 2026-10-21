"""CLI commands for the vault module.

Provides Click commands for artifact management, shield operations,
raids, and collection tracking. Uses ``run_cli_async`` to bridge
synchronous Click commands to the fully async VaultService via
ApplicationContext.

Commands:
    vault list             -- List artifacts in a player's vault
    vault summary          -- Get vault summary for a player
    vault add              -- Add an artifact to a player's vault
    vault get              -- Get a specific artifact by ID
    vault catalog          -- List artifact definitions
    vault shield-status    -- Check shield status
    vault shield-activate  -- Activate shield protection
    vault raid             -- Attempt to raid another player's vault
    vault can-raid         -- Check if a raid is possible
    vault raid-history     -- Get raid history for a player
"""

from __future__ import annotations

from uuid import UUID

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.cli.helpers.async_bridge import resolve_player, run_cli_async
from src.core.composition_root import ApplicationContext
from src.core.errors import AppError
from src.core.types.game import ArtifactId, PlayerId
from src.modules.vault.dto import ArtifactRarity

console = Console()


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def vault() -> None:
    """Vault and artifact management commands."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@vault.command("list")
@click.argument("player_username")
@click.option(
    "--rarity",
    type=click.Choice(["common", "rare", "epic", "legendary"], case_sensitive=False),
    default=None,
    help="Filter by artifact rarity",
)
@click.option("--set", "artifact_set", default=None, help="Filter by artifact set")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def list_artifacts(
    player_username: str, rarity: str | None, artifact_set: str | None, config_path: str
) -> None:
    """List artifacts in a player's vault."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            rarity_enum = ArtifactRarity(rarity) if rarity else None
            result = await ctx.vault_service.get_player_artifacts(
                player_id=PlayerId(player_id),
                rarity=rarity_enum,
                artifact_set=artifact_set,
            )

            table = Table(
                title=f"Vault contents for {player_username} ({result.total} total)"
            )
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="green")
            table.add_column("Rarity", style="yellow")
            table.add_column("Set", style="magenta")
            table.add_column("Source", style="dim")

            for artifact in result.items:
                table.add_row(
                    str(artifact.id)[:8] + "...",
                    artifact.definition.name,
                    artifact.definition.rarity.value,
                    artifact.definition.artifact_set,
                    artifact.source,
                )

            console.print(table)
            if result.has_more:
                console.print(
                    f"[dim]Showing {len(result.items)} of {result.total} "
                    f"(offset {result.offset})[/dim]"
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


@vault.command("summary")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def summary(player_username: str, config_path: str) -> None:
    """Get vault summary for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            s = await ctx.vault_service.get_vault_summary(PlayerId(player_id))

            table = Table(title=f"Vault summary for {player_username}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right", style="yellow")

            table.add_row("Total artifacts", str(s.total_artifacts))

            for rarity_enum, count in s.by_rarity.items():
                table.add_row(f"  {rarity_enum.value}", str(count))

            table.add_row("Total value", str(s.total_value))
            table.add_row("Complete sets", ", ".join(s.complete_sets) or "None")
            table.add_row("Sets in progress", ", ".join(s.sets_in_progress) or "None")

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


@vault.command("add")
@click.argument("player_username")
@click.argument("artifact_type_id")
@click.option(
    "--source", required=True, help="How acquired (match_reward, event_reward, etc.)"
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def add_artifact(
    player_username: str, artifact_type_id: str, source: str, config_path: str
) -> None:
    """Add an artifact to a player's vault."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            artifact = await ctx.vault_service.add_artifact(
                player_id=PlayerId(player_id),
                artifact_type_id=artifact_type_id,
                source=source,
            )
            console.print(f"[bold green]Artifact added:[/bold green] {artifact.id}")
            console.print(f"  Name:   {artifact.definition.name}")
            console.print(f"  Rarity: {artifact.definition.rarity.value}")
            console.print(f"  Set:    {artifact.definition.artifact_set}")
            console.print(f"  Source: {artifact.source}")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


@vault.command("get")
@click.argument("artifact_id")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def get_artifact(artifact_id: str, config_path: str) -> None:
    """Get a specific artifact by ID."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            artifact = await ctx.vault_service.get_artifact(
                ArtifactId(UUID(artifact_id))
            )

            table = Table(title=f"Artifact {artifact_id[:8]}...")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="yellow")

            table.add_row("ID", str(artifact.id))
            table.add_row("Owner", str(artifact.owner_id))
            table.add_row("Type", artifact.artifact_type_id)
            table.add_row("Name", artifact.definition.name)
            table.add_row("Rarity", artifact.definition.rarity.value)
            table.add_row("Set", artifact.definition.artifact_set)
            table.add_row("Value", str(artifact.definition.base_value))
            table.add_row("Acquired", str(artifact.acquired_at))
            table.add_row("Source", artifact.source)

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


@vault.command("catalog")
@click.option(
    "--rarity",
    type=click.Choice(["common", "rare", "epic", "legendary"], case_sensitive=False),
    default=None,
    help="Filter by rarity",
)
@click.option("--set", "artifact_set", default=None, help="Filter by set")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def catalog(rarity: str | None, artifact_set: str | None, config_path: str) -> None:
    """List artifact definitions from the catalog."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            rarity_enum = ArtifactRarity(rarity) if rarity else None
            definitions = await ctx.vault_service.list_artifact_definitions(
                rarity=rarity_enum,
                artifact_set=artifact_set,
            )

            table = Table(title="Artifact Catalog")
            table.add_column("Type ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Rarity", style="yellow")
            table.add_column("Set", style="magenta")
            table.add_column("Value", justify="right")

            for d in definitions:
                table.add_row(
                    d.type_id,
                    d.name,
                    d.rarity.value,
                    d.artifact_set,
                    str(d.base_value),
                )

            console.print(table)
            console.print(f"[dim]{len(definitions)} definitions found[/dim]")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


@vault.command("shield-status")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def shield_status(player_username: str, config_path: str) -> None:
    """Check shield status for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            shield = await ctx.vault_service.get_shield_status(
                PlayerId(player_id)
            )

            if shield is None:
                console.print(f"Player {player_username} has no active shield.")
            else:
                table = Table(title=f"Shield for {player_username}")
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="yellow")

                table.add_row("Active", str(shield.is_active))
                table.add_row("Activated", str(shield.activated_at))
                table.add_row("Expires", str(shield.expires_at))
                table.add_row("Duration", f"{shield.duration_hours} hours")

                remaining = shield.remaining_seconds
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                table.add_row("Remaining", f"{hours}h {minutes}m")

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


@vault.command("shield-activate")
@click.argument("player_username")
@click.option(
    "--hours",
    type=int,
    default=None,
    help="Duration in hours (uses config default if not specified)",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def shield_activate(player_username: str, hours: int | None, config_path: str) -> None:
    """Activate shield protection for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            shield = await ctx.vault_service.activate_shield(
                player_id=PlayerId(player_id),
                duration_hours=hours,
            )

            console.print(
                f"[bold green]Shield activated for {player_username}[/bold green]"
            )
            console.print(f"  Expires:  {shield.expires_at}")
            console.print(f"  Duration: {shield.duration_hours} hours")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


@vault.command("raid")
@click.argument("attacker_username")
@click.argument("defender_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def raid(attacker_username: str, defender_username: str, config_path: str) -> None:
    """Attempt to raid another player's vault."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            attacker_id = await resolve_player(ctx, attacker_username)
            defender_id = await resolve_player(ctx, defender_username)
            result = await ctx.vault_service.attempt_raid(
                attacker_id=PlayerId(attacker_id),
                defender_id=PlayerId(defender_id),
            )

            if result.success:
                console.print("[bold green]Raid successful![/bold green]")
            else:
                console.print("[bold red]Raid failed.[/bold red]")

            console.print(f"  Message: {result.message}")

            if result.stolen_artifact:
                console.print(
                    f"  Stolen:  {result.stolen_artifact.definition.name}"
                )
                console.print(
                    f"  Rarity:  {result.stolen_artifact.definition.rarity.value}"
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


@vault.command("can-raid")
@click.argument("attacker_username")
@click.argument("defender_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def can_raid(attacker_username: str, defender_username: str, config_path: str) -> None:
    """Check if a raid is possible."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            attacker_id = await resolve_player(ctx, attacker_username)
            defender_id = await resolve_player(ctx, defender_username)
            eligibility = await ctx.vault_service.can_raid(
                attacker_id=PlayerId(attacker_id),
                defender_id=PlayerId(defender_id),
            )

            if eligibility.can_raid:
                console.print("[bold green]Raid is possible.[/bold green]")
            else:
                console.print("[bold red]Raid is not possible.[/bold red]")
                console.print(f"  Reason: {eligibility.reason}")
                if eligibility.cooldown_expires_at:
                    console.print(
                        f"  Cooldown expires: {eligibility.cooldown_expires_at}"
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


@vault.command("raid-history")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def raid_history(player_username: str, config_path: str) -> None:
    """Get raid history for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.vault_service.get_raid_history(
                PlayerId(player_id)
            )

            table = Table(
                title=f"Raid history for {player_username} ({result.total} total)"
            )
            table.add_column("Raid ID", style="cyan", no_wrap=True)
            table.add_column("Role", style="yellow")
            table.add_column("Opponent", style="green")
            table.add_column("Success", style="bold")
            table.add_column("Artifact", style="magenta")
            table.add_column("Time", style="dim")

            pid = player_id
            for log in result.items:
                role = "Attacker" if log.attacker_id == pid else "Defender"
                opponent = str(
                    log.defender_id if log.attacker_id == pid else log.attacker_id
                )
                success_str = (
                    "[green]Yes[/green]" if log.success else "[red]No[/red]"
                )
                artifact_str = log.artifact_type_id or "-"

                table.add_row(
                    str(log.raid_id)[:8] + "...",
                    role,
                    opponent[:8] + "...",
                    success_str,
                    artifact_str,
                    str(log.timestamp),
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
