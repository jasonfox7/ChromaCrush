"""CLI commands for the board_gen module.

Provides commands for board generation, match-type presets,
board analysis, seed validation, and deadlock reshuffling.

The board_gen module is fully synchronous, so no async bridge is needed.
Uses ``build_sync_services()`` to create all sync services from config.
"""

from __future__ import annotations

import json
import random

import click

from src.cli.helpers.display import console, render_board
from src.cli.helpers.service_factory import build_sync_services
from src.core.types.board import BoardState


@click.group("board-gen")
def board_gen() -> None:
    """Board generation commands."""


@board_gen.command()
@click.option(
    "--seed", type=int, default=None, help="RNG seed (random if not provided)."
)
@click.option(
    "--cascade-potential",
    type=float,
    default=None,
    help="Cascade potential target (0.0-1.0).",
)
@click.option(
    "--near-miss-factor", type=float, default=None, help="Near-miss factor (0.0-1.0)."
)
@click.option(
    "--no-functions",
    is_flag=True,
    default=False,
    help="Disable function overlay in board display.",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def generate(
    seed: int | None,
    cascade_potential: float | None,
    near_miss_factor: float | None,
    no_functions: bool,
    config_path: str,
) -> None:
    """Generate a new board."""
    from src.modules.board_gen.types import BoardGenOptions

    _board_svc, _scoring_svc, _special_svc, board_gen_svc = build_sync_services(
        config_path
    )

    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    options = None
    if cascade_potential is not None or near_miss_factor is not None:
        options = BoardGenOptions(
            cascade_potential=cascade_potential,
            near_miss_factor=near_miss_factor,
        )

    result = board_gen_svc.generate_board(seed, options)
    meta = result.generation_metadata

    console.print("[bold]Board generated:[/bold]")
    console.print(f"  Seed: {result.seed}")
    console.print(
        f"  Cascade potential: {meta.cascade_potential_actual:.2f} "
        f"(target: {meta.cascade_potential_target:.2f})"
    )
    console.print(f"  Near-misses: {meta.near_miss_count}")
    console.print(f"  Valid moves: {meta.valid_moves_count}")
    console.print(f"  Generation time: {meta.generation_time_ms:.1f}ms")
    console.print(f"  Attempts: {meta.generation_attempts}")
    console.print()
    render_board(result.board_state, show_functions=not no_functions)


@board_gen.command("for-match")
@click.option("--seed", type=int, required=True, help="RNG seed.")
@click.option(
    "--match-type",
    type=click.Choice(["standard", "competitive", "casual", "tutorial"]),
    default="standard",
)
@click.option(
    "--no-functions",
    is_flag=True,
    default=False,
    help="Disable function overlay in board display.",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def for_match(seed: int, match_type: str, no_functions: bool, config_path: str) -> None:
    """Generate a board using match-type presets."""
    from src.modules.board_gen.types import MatchType

    _board_svc, _scoring_svc, _special_svc, board_gen_svc = build_sync_services(
        config_path
    )

    mt = MatchType(match_type)
    result = board_gen_svc.generate_board_for_match(seed, mt)
    meta = result.generation_metadata

    console.print(f"[bold]Board generated ({match_type} match):[/bold]")
    console.print(f"  Seed: {result.seed}")
    console.print(
        f"  Cascade potential: {meta.cascade_potential_actual:.2f} "
        f"(target: {meta.cascade_potential_target:.2f})"
    )
    if meta.starting_specials_placed:
        for pos, gem in meta.starting_specials_placed:
            console.print(f"  Starting special: {gem.name} at ({pos.row},{pos.col})")
    console.print(f"  Valid moves: {meta.valid_moves_count}")
    console.print()
    render_board(result.board_state, show_functions=not no_functions)


@board_gen.command()
@click.option("--board", "board_json", required=True, help="Board as JSON 2D array.")
@click.option(
    "--no-functions",
    is_flag=True,
    default=False,
    help="Disable function overlay in board display.",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def analyze(board_json: str, no_functions: bool, config_path: str) -> None:
    """Analyse an existing board's generation characteristics."""
    _board_svc, _scoring_svc, _special_svc, board_gen_svc = build_sync_services(
        config_path
    )

    try:
        data = json.loads(board_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    board_state = BoardState.from_list(data)
    potential = board_gen_svc.calculate_cascade_potential(board_state)

    console.print("[bold]Board Analysis:[/bold]")
    console.print(f"  Cascade potential: {potential:.3f}")
    console.print(f"  Dimensions: {board_state.width}x{board_state.height}")
    render_board(board_state, show_functions=not no_functions)


@board_gen.command("validate-seed")
@click.option("--seed", type=int, required=True, help="Seed to validate.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def validate_seed(seed: int, config_path: str) -> None:
    """Check if a seed produces a valid board."""
    _board_svc, _scoring_svc, _special_svc, board_gen_svc = build_sync_services(
        config_path
    )

    valid = board_gen_svc.validate_seed(seed)

    if valid:
        console.print(f"Seed {seed}: [green]VALID[/green]")
    else:
        console.print(f"Seed {seed}: [red]INVALID[/red]")


@board_gen.command()
@click.option("--board", "board_json", required=True, help="Board as JSON 2D array.")
@click.option("--seed", type=int, required=True, help="RNG seed for shuffle.")
@click.option(
    "--no-functions",
    is_flag=True,
    default=False,
    help="Disable function overlay in board display.",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def reshuffle(board_json: str, seed: int, no_functions: bool, config_path: str) -> None:
    """Reshuffle a deadlocked board."""
    _board_svc, _scoring_svc, _special_svc, board_gen_svc = build_sync_services(
        config_path
    )

    try:
        data = json.loads(board_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    board_state = BoardState.from_list(data)
    result = board_gen_svc.regenerate_from_deadlock(board_state, seed)
    meta = result.generation_metadata

    console.print("[bold]Reshuffled board:[/bold]")
    console.print(f"  Preserved specials: {len(meta.starting_specials_placed)}")
    console.print(f"  Valid moves: {meta.valid_moves_count}")
    console.print(f"  Reshuffle attempts: {meta.generation_attempts}")
    console.print()
    render_board(result.board_state, show_functions=not no_functions)
