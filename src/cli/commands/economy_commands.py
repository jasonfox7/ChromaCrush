"""CLI commands for the economy module.

Provides Click commands for gold balance queries, selling equipped cards
for gold, buying marketplace items, and browsing the marketplace catalog.

Commands:
    economy gold          -- Show player's gold balance
    economy sell          -- Sell all 3 equipped cards for gold
    economy buy           -- Buy a marketplace item with gold
    economy marketplace   -- List all marketplace items
"""

from __future__ import annotations

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


@click.group("economy")
def economy() -> None:
    """Gold economy management commands."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@economy.command("gold")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def gold(player_username: str, config_path: str) -> None:
    """Show player's current gold balance."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            info = await ctx.economy_service.get_gold(player_id)

            table = Table(title=f"Gold Balance for {player_username}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", justify="right", style="yellow")

            table.add_row("Balance", f"{info.balance:,}")
            table.add_row("Lifetime Earned", f"{info.lifetime_earned:,}")
            table.add_row("Lifetime Spent", f"{info.lifetime_spent:,}")

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


@economy.command("sell")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def sell(player_username: str, config_path: str) -> None:
    """Sell all 3 equipped cards for gold (40% of base_value each)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.economy_service.sell_equipped_cards(player_id)

            card_breakdown = "\n".join(
                f"    Card {i + 1}: {v:,} gold"
                for i, v in enumerate(result.card_values)
            )

            console.print(
                Panel(
                    f"[bold green]Cards sold![/bold green]\n\n"
                    f"  Cards sold:    {result.cards_sold}\n"
                    f"  Gold earned:   {result.gold_earned:,}\n"
                    f"  Breakdown:\n{card_breakdown}\n"
                    f"  New balance:   {result.new_balance:,}",
                    title=f"Sell Result for {player_username}",
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


@economy.command("buy")
@click.argument("player_username")
@click.argument("item_id")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def buy(player_username: str, item_id: str, config_path: str) -> None:
    """Buy an item from the marketplace with gold."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.economy_service.buy_item(player_id, item_id)

            console.print(
                Panel(
                    f"[bold green]Purchase complete![/bold green]\n\n"
                    f"  Item:           {result.item_name} ({result.item_id})\n"
                    f"  Gold spent:     {result.gold_spent:,}\n"
                    f"  Quantity:       {result.quantity_granted}\n"
                    f"  New balance:    {result.new_balance:,}",
                    title=f"Buy Result for {player_username}",
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


@economy.command("marketplace")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def marketplace(config_path: str) -> None:
    """List all available marketplace items."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            items = await ctx.economy_service.get_marketplace()

            if not items:
                console.print("[dim]No marketplace items available.[/dim]")
                return

            # Group by category for readability.
            categories: dict[str, list] = {}
            for item in items:
                categories.setdefault(item.category, []).append(item)

            for category, cat_items in categories.items():
                table = Table(
                    title=f"Marketplace: {category.replace('_', ' ').title()}"
                )
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Price", justify="right", style="yellow")
                table.add_column("Qty", justify="right")
                table.add_column("Type", style="magenta")
                table.add_column("Description", style="dim")

                for item in cat_items:
                    # Gold IAP packs show price in cents; others in gold.
                    if item.item_type == "gold_iap":
                        price_str = f"${item.price / 100:.2f}"
                    else:
                        price_str = f"{item.price:,} gold"

                    table.add_row(
                        item.item_id,
                        item.name,
                        price_str,
                        str(item.quantity),
                        item.item_type,
                        item.description,
                    )

                console.print(table)
                console.print()

            console.print(f"[dim]{len(items)} items total[/dim]")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    run_cli_async(_do, config_path)
