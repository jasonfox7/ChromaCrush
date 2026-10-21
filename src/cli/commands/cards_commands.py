"""CLI commands for the cards module.

Provides Click commands for card definition browsing, player card
collection management, equip/unequip operations, merge, starter packs,
and modifier engine inspection.

Commands:
    cards list-definitions   -- List card definitions with optional rarity filter
    cards get-definition     -- Get a single card definition by ID
    cards player-cards       -- List cards owned by a player
    cards equipped           -- Show a player's equipped loadout
    cards grant              -- Grant a card to a player
    cards equip              -- Equip a card into a slot
    cards unequip            -- Unequip a card from its slot
    cards reorder            -- Move a card to a new position
    cards merge              -- Merge 3 equipped cards into a higher-tier card
    cards grant-starter      -- Grant a 15-card starter pack
    cards show-modifiers     -- Show active card modifier hooks for a player
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

console = Console()


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group("cards")
def cards() -> None:
    """Card definition and player card management commands."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@cards.command("list-definitions")
@click.option(
    "--rarity",
    type=click.Choice(["common", "rare", "epic", "legendary"], case_sensitive=False),
    default=None,
    help="Filter by card rarity",
)
@click.option("--limit", default=50, type=int, help="Max results to show")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def list_definitions(rarity: str | None, limit: int, config_path: str) -> None:
    """List card definitions with optional rarity filter."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            definitions = await ctx.card_service.list_card_definitions(rarity=rarity)
            shown = definitions[:limit]

            table = Table(title=f"Card Definitions ({len(definitions)} total)")
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Name", style="green")
            table.add_column("Rarity", style="yellow")
            table.add_column("Set", style="magenta")
            table.add_column("Pos", justify="right")
            table.add_column("Value", justify="right")
            table.add_column("Effect", style="dim")

            for d in shown:
                table.add_row(
                    str(d.card_id),
                    d.name,
                    d.rarity,
                    d.card_set,
                    str(d.set_position),
                    str(d.base_value),
                    d.effect or "-",
                )

            console.print(table)
            if len(definitions) > limit:
                console.print(
                    f"[dim]Showing {limit} of {len(definitions)} definitions[/dim]"
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


@cards.command("get-definition")
@click.argument("card_id", type=int)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def get_definition(card_id: int, config_path: str) -> None:
    """Get a single card definition by ID."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            d = await ctx.card_service.get_card_definition(card_id)

            table = Table(title=f"Card Definition #{d.card_id}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="yellow")

            table.add_row("ID", str(d.card_id))
            table.add_row("Name", d.name)
            table.add_row("Description", d.description or "-")
            table.add_row("Rarity", d.rarity)
            table.add_row("Set", d.card_set)
            table.add_row("Set Position", str(d.set_position))
            table.add_row("Base Value", str(d.base_value))
            table.add_row("Tags", ", ".join(d.tags) if d.tags else "-")
            table.add_row("Trigger", d.trigger)
            table.add_row("Effect", d.effect or "-")
            table.add_row(
                "Effect Params",
                str(d.effect_params) if d.effect_params else "-",
            )
            table.add_row(
                "Trigger Condition",
                str(d.trigger_condition) if d.trigger_condition else "-",
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


@cards.command("player-cards")
@click.argument("player_username")
@click.option("--equipped-only", is_flag=True, default=False, help="Show only equipped cards")
@click.option(
    "--rarity",
    type=click.Choice(["common", "rare", "epic", "legendary"], case_sensitive=False),
    default=None,
    help="Filter by rarity",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def player_cards(
    player_username: str,
    equipped_only: bool,
    rarity: str | None,
    config_path: str,
) -> None:
    """List cards owned by a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)

            if equipped_only:
                loadout = await ctx.card_service.get_equipped_cards(player_id)
                all_cards = loadout.cards
            else:
                result = await ctx.card_service.get_player_cards(player_id)
                all_cards = result.items

            # Apply client-side rarity filter if specified.
            if rarity is not None:
                all_cards = [c for c in all_cards if c.definition.rarity == rarity]

            table = Table(
                title=f"Cards for {player_username} ({len(all_cards)} shown)"
            )
            table.add_column("Instance ID", style="cyan", no_wrap=True)
            table.add_column("Card ID", justify="right")
            table.add_column("Name", style="green")
            table.add_column("Rarity", style="yellow")
            table.add_column("Pos", justify="right")
            table.add_column("Slot", style="magenta")
            table.add_column("Level", justify="right")
            table.add_column("Source", style="dim")

            for c in all_cards:
                slot_label = (
                    f"Equip {c.position}" if c.position <= 3 else "Vault"
                )
                table.add_row(
                    str(c.id)[:8] + "...",
                    str(c.card_id),
                    c.definition.name,
                    c.definition.rarity,
                    str(c.position),
                    slot_label,
                    str(c.level),
                    c.source,
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


@cards.command("equipped")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def equipped(player_username: str, config_path: str) -> None:
    """Show a player's equipped card loadout (slots 1-3)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            loadout = await ctx.card_service.get_equipped_cards(player_id)

            if not loadout.cards:
                console.print(
                    f"[dim]{player_username} has no equipped cards.[/dim]"
                )
                return

            table = Table(title=f"Equipped Loadout for {player_username}")
            table.add_column("Slot", justify="center", style="bold")
            table.add_column("Instance ID", style="cyan", no_wrap=True)
            table.add_column("Card ID", justify="right")
            table.add_column("Name", style="green")
            table.add_column("Rarity", style="yellow")
            table.add_column("Effect", style="magenta")
            table.add_column("Value", justify="right")

            for c in sorted(loadout.cards, key=lambda x: x.position):
                table.add_row(
                    str(c.position),
                    str(c.id)[:8] + "...",
                    str(c.card_id),
                    c.definition.name,
                    c.definition.rarity,
                    c.definition.effect or "-",
                    str(c.definition.base_value),
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


@cards.command("grant")
@click.argument("player_username")
@click.argument("card_id", type=int)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def grant(player_username: str, card_id: int, config_path: str) -> None:
    """Grant a card to a player (source: cli_grant)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            card = await ctx.card_service.grant_card(
                player_id, card_id, source="cli_grant"
            )

            console.print(
                Panel(
                    f"[bold green]Card granted![/bold green]\n\n"
                    f"  Instance ID: {card.id}\n"
                    f"  Card:        #{card.card_id} {card.definition.name}\n"
                    f"  Rarity:      {card.definition.rarity}\n"
                    f"  Position:    {card.position}"
                    f" ({'Equip slot' if card.position <= 3 else 'Vault'})",
                    title=f"Grant to {player_username}",
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


@cards.command("equip")
@click.argument("player_username")
@click.argument("card_instance_id")
@click.argument("position", type=int)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def equip(
    player_username: str, card_instance_id: str, position: int, config_path: str
) -> None:
    """Equip a card into a specific slot (1-3)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            loadout = await ctx.card_service.equip_card(
                player_id, UUID(card_instance_id), position
            )

            console.print(
                f"[bold green]Card equipped into slot {position}![/bold green]"
            )
            console.print(f"  Equipped cards now:")
            for c in sorted(loadout.cards, key=lambda x: x.position):
                console.print(
                    f"    Slot {c.position}: #{c.card_id} {c.definition.name} "
                    f"({c.definition.rarity})"
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


@cards.command("unequip")
@click.argument("player_username")
@click.argument("card_instance_id")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def unequip(player_username: str, card_instance_id: str, config_path: str) -> None:
    """Unequip a card from its slot back to the vault."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            loadout = await ctx.card_service.unequip_card(
                player_id, UUID(card_instance_id)
            )

            console.print(
                f"[bold green]Card unequipped![/bold green]"
            )
            if loadout.cards:
                console.print(f"  Remaining equipped:")
                for c in sorted(loadout.cards, key=lambda x: x.position):
                    console.print(
                        f"    Slot {c.position}: #{c.card_id} {c.definition.name}"
                    )
            else:
                console.print(f"  [dim]No cards equipped.[/dim]")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)


@cards.command("reorder")
@click.argument("player_username")
@click.argument("card_instance_id")
@click.argument("new_position", type=int)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def reorder(
    player_username: str, card_instance_id: str, new_position: int, config_path: str
) -> None:
    """Move a card to a new position."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            card = await ctx.card_service.reorder_card(
                player_id, UUID(card_instance_id), new_position
            )

            console.print(
                f"[bold green]Card reordered![/bold green]\n"
                f"  #{card.card_id} {card.definition.name} -> position {card.position}"
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


@cards.command("merge")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def merge(player_username: str, config_path: str) -> None:
    """Merge all 3 equipped cards into a random higher-tier card."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.card_service.merge_equipped(player_id)

            console.print(
                Panel(
                    f"[bold green]Merge successful![/bold green]\n\n"
                    f"  Source rarity: {result.source_rarity}\n"
                    f"  Target rarity: {result.target_rarity}\n"
                    f"  Cards consumed: {len(result.consumed_card_ids)}\n"
                    f"  New card:       #{result.new_card.card_id} "
                    f"{result.new_card.definition.name}\n"
                    f"  New card rarity: {result.new_card.definition.rarity}\n"
                    f"  Instance ID:    {result.new_card.id}",
                    title=f"Merge Result for {player_username}",
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


@cards.command("grant-starter")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def grant_starter(player_username: str, config_path: str) -> None:
    """Grant a 15-card starter pack to a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            granted = await ctx.card_service.grant_starter_pack(player_id)

            if not granted:
                console.print("[yellow]No cards were granted (no definitions found).[/yellow]")
                return

            table = Table(title=f"Starter Pack for {player_username} ({len(granted)} cards)")
            table.add_column("#", justify="right", style="dim")
            table.add_column("Card ID", justify="right")
            table.add_column("Name", style="green")
            table.add_column("Rarity", style="yellow")
            table.add_column("Position", justify="right")
            table.add_column("Slot", style="magenta")

            for i, c in enumerate(granted, 1):
                slot_label = (
                    f"Equip {c.position}" if c.position <= 3 else "Vault"
                )
                table.add_row(
                    str(i),
                    str(c.card_id),
                    c.definition.name,
                    c.definition.rarity,
                    str(c.position),
                    slot_label,
                )

            console.print(table)
            console.print(
                f"[bold green]Granted {len(granted)} cards to {player_username}[/bold green]"
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


@cards.command("show-modifiers")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def show_modifiers(player_username: str, config_path: str) -> None:
    """Show active card modifier hooks for a player's equipped loadout."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            engine = await ctx.card_service.build_modifier_engine(player_id)

            if engine.is_empty:
                console.print(
                    f"[dim]{player_username} has no active card modifiers.[/dim]"
                )
                return

            # The engine exposes _by_effect: dict[str, list[CardModifierDef]]
            by_effect: dict = engine._by_effect

            table = Table(title=f"Active Card Modifiers for {player_username}")
            table.add_column("Effect", style="cyan")
            table.add_column("Card ID", justify="right")
            table.add_column("Card Name", style="green")
            table.add_column("Trigger", style="yellow")
            table.add_column("Params", style="dim")
            table.add_column("Tags", style="magenta")

            for effect_name, card_defs in sorted(by_effect.items()):
                for cdef in card_defs:
                    params_str = (
                        ", ".join(f"{k}={v}" for k, v in cdef.effect_params.items())
                        if cdef.effect_params
                        else "-"
                    )
                    tags_str = ", ".join(cdef.tags) if cdef.tags else "-"
                    table.add_row(
                        effect_name,
                        str(cdef.card_id),
                        cdef.name,
                        cdef.trigger,
                        params_str,
                        tags_str,
                    )

            console.print(table)

            # Summary of which hooks are active.
            hook_map = {
                "override_special": "Hook 1: Special Override",
                "override_special_mega": "Hook 1: Special Override (Mega)",
                "effect_param_override": "Hook 2: Effect Param Override",
                "inject_special": "Hook 3: Cascade Injection",
                "inject_and_fire": "Hook 3: Cascade Injection (Fire)",
                "spawn_bias": "Hook 4: Spawn Weights",
                "special_type_bias": "Hook 5a: Special Type Bias",
                "special_creation_chance": "Hook 5b: 3-Match Special Chance",
                "score_multiplier": "Hook 6: Score Multiplier",
                "opponent_score_reduction": "Hook 6: Opponent Score Reduction",
                "lucky_rabbit": "Hook 7: Lucky Rabbit (Instant Win)",
                "grant_energy": "Hook 8: Energy Grant",
                "raid_protection": "Hook 10: Raid Protection",
                "raid_block": "Hook 10: Raid Block",
            }

            active_hooks = []
            for effect_name in by_effect:
                label = hook_map.get(effect_name, f"Unknown: {effect_name}")
                active_hooks.append(label)

            if active_hooks:
                console.print(
                    Panel(
                        "\n".join(f"  {h}" for h in sorted(active_hooks)),
                        title="Active Hooks",
                        border_style="green",
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
