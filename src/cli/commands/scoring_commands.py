"""CLI commands for the scoring module.

Provides development and debugging commands for score calculation.
Uses Click for command parsing and Rich for coloured terminal output.

The scoring module is fully synchronous, so no async bridge is needed.
Uses ``build_sync_services()`` to create all sync services from config.
"""

from __future__ import annotations

import json

import click
from rich.table import Table

from src.cli.helpers.display import console
from src.cli.helpers.service_factory import build_sync_services
from src.core.errors import AppError
from src.core.types.board import BoardState
from src.core.types.game import GemType


# ------------------------------------------------------------------
# Click group
# ------------------------------------------------------------------


@click.group("scoring")
def scoring() -> None:
    """Scoring module -- score calculation commands."""


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------


@scoring.command("calculate-match")
@click.option("--board", "board_json", required=True, help="Board as JSON 2D array.")
@click.option(
    "--chain-step",
    type=int,
    default=1,
    help="Chain step for multiplier (default 1).",
    show_default=True,
)
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def calculate_match(board_json: str, chain_step: int, config_path: str) -> None:
    """Detect matches on a board and calculate score."""
    board_svc, scoring_svc, _special_svc, _gen_svc = build_sync_services(config_path)

    try:
        data: list[list[int]] = json.loads(board_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    board = BoardState.from_list(data)
    match_result = board_svc.detect_matches(board)

    if not match_result.matches:
        console.print("[yellow]No matches found on the board.[/yellow]")
        return

    try:
        score = scoring_svc.calculate_match_score(match_result, chain_step=chain_step)
    except AppError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        return

    console.print("[bold]Match Score:[/bold]")
    console.print(f"  Chain Step: {score.chain_step}")
    console.print(f"  Chain Multiplier: {score.chain_multiplier}x")
    console.print(f"  Matches Found: {len(score.match_breakdown)}")

    for i, mg_score in enumerate(score.match_breakdown, 1):
        mg = mg_score.match_group
        console.print(
            f"    Match {i}: {mg.gem_type.name}, length={mg.length}, "
            f"base={mg_score.base_points}, length_mult={mg_score.length_multiplier}x, "
            f"subtotal={mg_score.subtotal}"
        )

    console.print(f"  Base Total: {score.base_points}")
    console.print(f"  After Chain: {int(score.base_points * score.chain_multiplier)}")
    console.print(f"  Special Bonus: {score.special_gem_creation_bonus}")
    console.print(f"  Total: {score.total_points} points")


@scoring.command("show-multipliers")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def show_multipliers(config_path: str) -> None:
    """Display current scoring configuration."""
    _board_svc, scoring_svc, _special_svc, _gen_svc = build_sync_services(config_path)

    cfg = scoring_svc.get_scoring_config()

    console.print("[bold]Scoring Configuration:[/bold]")
    console.print(f"  Base Points: {cfg['base_points']} per gem")
    console.print()

    # Chain multipliers table.
    chain_multipliers: tuple[float, ...] = cfg["chain_multipliers"]  # type: ignore[assignment]
    chain_table = Table(title="Chain Multipliers", show_header=True)
    chain_table.add_column("Chain Step", style="cyan")
    chain_table.add_column("Multiplier", style="yellow")

    for i, mult in enumerate(chain_multipliers, start=1):
        label = f"Chain {i}" if i < len(chain_multipliers) else f"Chain {i}+"
        chain_table.add_row(label, f"{mult}x")

    console.print(chain_table)
    console.print()

    # Length multipliers table.
    length_multipliers: tuple[float, ...] = cfg["length_multipliers"]  # type: ignore[assignment]
    length_table = Table(title="Length Multipliers", show_header=True)
    length_table.add_column("Match Length", style="cyan")
    length_table.add_column("Multiplier", style="yellow")

    for i, mult in enumerate(length_multipliers):
        length = i + 3
        label = (
            f"{length}-match" if i < len(length_multipliers) - 1 else f"{length}+-match"
        )
        length_table.add_row(label, f"{mult}x")

    console.print(length_table)
    console.print()

    # Special gem bonuses.
    special_table = Table(title="Special Gem Bonuses", show_header=True)
    special_table.add_column("Type", style="cyan")
    special_table.add_column("Base Bonus", style="green")
    special_table.add_column("Per Gem", style="yellow")

    special_table.add_row("Creation", f"+{cfg['special_gem_creation_bonus']}", "-")
    special_table.add_row(
        "LINE_BLAST",
        str(cfg["line_blast_activation_bonus"]),
        f"+{cfg['line_blast_per_gem']}/gem",
    )
    special_table.add_row(
        "RADIAL_BOMB",
        str(cfg["radial_bomb_activation_bonus"]),
        f"+{cfg['radial_bomb_per_gem']}/gem",
    )
    special_table.add_row(
        "CHROMATIC_ORB",
        str(cfg["chromatic_orb_activation_bonus"]),
        f"+{cfg['chromatic_orb_per_gem']}/gem",
    )

    console.print(special_table)


@scoring.command("special-gem-bonus")
@click.option(
    "--gem-type",
    required=True,
    type=click.Choice(
        ["LINE_BLAST_H", "LINE_BLAST_V", "RADIAL_BOMB", "CHROMATIC_ORB"],
        case_sensitive=False,
    ),
    help="Special gem type.",
)
@click.option(
    "--gems-affected",
    type=int,
    required=True,
    help="Number of gems cleared by the special gem.",
)
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def special_gem_bonus(gem_type: str, gems_affected: int, config_path: str) -> None:
    """Calculate special gem activation bonus."""
    _board_svc, scoring_svc, _special_svc, _gen_svc = build_sync_services(config_path)

    gem_type_map = {
        "LINE_BLAST_H": GemType.LINE_BLAST_H,
        "LINE_BLAST_V": GemType.LINE_BLAST_V,
        "RADIAL_BOMB": GemType.RADIAL_BOMB,
        "CHROMATIC_ORB": GemType.CHROMATIC_ORB,
    }

    gem = gem_type_map[gem_type.upper()]

    try:
        bonus = scoring_svc.calculate_special_gem_bonus(gem, gems_affected)
    except AppError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        return

    console.print("[bold]Special Gem Bonus:[/bold]")
    console.print(f"  Type: {bonus.gem_type.name}")
    console.print(f"  Base Activation: {bonus.base_activation_bonus}")
    console.print(f"  Gems Affected: {bonus.gems_affected}")
    console.print(f"  Per-Gem Bonus: {bonus.per_gem_bonus}")
    console.print(f"  Total: {bonus.total_bonus} points")
