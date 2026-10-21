"""CLI commands for the special_gems module.

Provides development and debugging commands for special gem activation,
fusion calculation, match analysis, and board simulation.

The special_gems module is fully synchronous, so no async bridge is needed.
Uses ``build_sync_services()`` to create all sync services from config.
"""

from __future__ import annotations

import json

import click

from src.cli.helpers.display import console, render_board
from src.cli.helpers.service_factory import build_sync_services
from src.core.errors import AppError
from src.core.types.board import BoardState, MatchGroup, MatchResult
from src.core.types.game import GemType, Position


# ------------------------------------------------------------------
# Parsing helpers
# ------------------------------------------------------------------


def _parse_position(value: str) -> Position:
    """Parse a 'row,col' string into a Position."""
    parts = value.split(",")
    if len(parts) != 2:
        raise click.BadParameter(
            f"Position must be in 'row,col' format, got: {value!r}"
        )
    try:
        row, col = int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        raise click.BadParameter(
            f"Position coordinates must be integers, got: {value!r}"
        )
    return Position(row, col)


def _parse_gem_type(value: str) -> GemType:
    """Parse a gem type name (e.g. 'RED') into a GemType."""
    gem_map = {
        "RED": GemType.RED,
        "BLUE": GemType.BLUE,
        "GREEN": GemType.GREEN,
        "YELLOW": GemType.YELLOW,
        "PURPLE": GemType.PURPLE,
        "ORANGE": GemType.ORANGE,
    }
    upper = value.upper()
    if upper not in gem_map:
        raise click.BadParameter(
            f"Target color must be one of {list(gem_map.keys())}, got: {value!r}"
        )
    return gem_map[upper]


# ------------------------------------------------------------------
# Click group
# ------------------------------------------------------------------


@click.group("special-gems")
def special_gems() -> None:
    """Special gems module -- activation, fusion, and analysis commands."""


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------


@special_gems.command("check")
@click.option("--board", "board_json", required=True, help="Board as JSON 2D array.")
@click.option("--position", required=True, help="Position as 'row,col'.")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def check_special_gem(board_json: str, position: str, config_path: str) -> None:
    """Check if a position contains a special gem."""
    _board_svc, _scoring_svc, special_svc, _gen_svc = build_sync_services(config_path)

    try:
        data: list[list[int]] = json.loads(board_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    board = BoardState.from_list(data)

    try:
        pos = _parse_position(position)
    except click.BadParameter as exc:
        console.print(f"[red]{exc}[/red]")
        return

    try:
        gem_type = board.get(pos)
    except (IndexError, ValueError) as exc:
        console.print(f"[red]Error: {exc}[/red]")
        return

    is_special = special_svc.is_special_gem(gem_type)

    console.print(f"[bold]Position ({pos.row}, {pos.col}):[/bold]")
    console.print(f"  Gem Type: {gem_type.name}")
    console.print(f"  Is Special: {'Yes' if is_special else 'No'}")


@special_gems.command("activate")
@click.option("--board", "board_json", required=True, help="Board as JSON 2D array.")
@click.option("--position", required=True, help="Position as 'row,col'.")
@click.option(
    "--target-color",
    default=None,
    help="Target color for Chromatic Orb (e.g. RED, BLUE).",
)
@click.option(
    "--no-functions",
    is_flag=True,
    default=False,
    help="Disable function overlay in board display.",
)
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def activate_special_gem(
    board_json: str,
    position: str,
    target_color: str | None,
    no_functions: bool,
    config_path: str,
) -> None:
    """Calculate the activation effect of a special gem."""
    _board_svc, _scoring_svc, special_svc, _gen_svc = build_sync_services(config_path)

    try:
        data: list[list[int]] = json.loads(board_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    board = BoardState.from_list(data)

    try:
        pos = _parse_position(position)
    except click.BadParameter as exc:
        console.print(f"[red]{exc}[/red]")
        return

    color: GemType | None = None
    if target_color is not None:
        try:
            color = _parse_gem_type(target_color)
        except click.BadParameter as exc:
            console.print(f"[red]{exc}[/red]")
            return

    try:
        effect = special_svc.calculate_effect(board, pos, target_color=color)
    except AppError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        return

    console.print("[bold]Special Gem Effect:[/bold]")
    console.print(f"  Type: {effect.gem_type.name}")
    console.print(
        f"  Position: ({effect.source_position.row}, {effect.source_position.col})"
    )
    console.print(f"  Affected: {len(effect.affected_positions)} positions")
    console.print(f"  Bonus Score: {effect.bonus_score.total_bonus} points")
    console.print(f"  Chain Triggers: {len(effect.triggers_special_gems)}")
    if effect.triggers_special_gems:
        for t_pos in effect.triggers_special_gems:
            t_gem = board.get(t_pos)
            console.print(f"    - {t_gem.name} at ({t_pos.row}, {t_pos.col})")
    console.print(f"  Description: {effect.description}")

    # Show the board for context.
    console.print()
    console.print("[bold]Board:[/bold]")
    render_board(board, show_functions=not no_functions)


@special_gems.command("fuse")
@click.option("--board", "board_json", required=True, help="Board as JSON 2D array.")
@click.option("--pos-a", required=True, help="First position as 'row,col'.")
@click.option("--pos-b", required=True, help="Second position as 'row,col'.")
@click.option(
    "--target-color",
    default=None,
    help="Target color for Chromatic fusions (e.g. RED, BLUE).",
)
@click.option(
    "--no-functions",
    is_flag=True,
    default=False,
    help="Disable function overlay in board display.",
)
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def fuse_special_gems(
    board_json: str,
    pos_a: str,
    pos_b: str,
    target_color: str | None,
    no_functions: bool,
    config_path: str,
) -> None:
    """Calculate the fusion effect of two special gems."""
    _board_svc, _scoring_svc, special_svc, _gen_svc = build_sync_services(config_path)

    try:
        data: list[list[int]] = json.loads(board_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    board = BoardState.from_list(data)

    try:
        p_a = _parse_position(pos_a)
        p_b = _parse_position(pos_b)
    except click.BadParameter as exc:
        console.print(f"[red]{exc}[/red]")
        return

    color: GemType | None = None
    if target_color is not None:
        try:
            color = _parse_gem_type(target_color)
        except click.BadParameter as exc:
            console.print(f"[red]{exc}[/red]")
            return

    try:
        effect = special_svc.calculate_fusion_effect(board, p_a, p_b, target_color=color)
    except AppError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        return

    console.print("[bold]Fusion Effect:[/bold]")
    console.print(
        f"  Gem A: {effect.gem_a_type.name} at "
        f"({effect.source_positions[0].row}, {effect.source_positions[0].col})"
    )
    console.print(
        f"  Gem B: {effect.gem_b_type.name} at "
        f"({effect.source_positions[1].row}, {effect.source_positions[1].col})"
    )
    console.print(f"  Fusion Type: {effect.fusion_type.value}")
    console.print(f"  Affected: {len(effect.affected_positions)} positions")
    console.print(f"  Bonus Score: {effect.bonus_score.total_bonus} points")
    console.print(f"  Chain Triggers: {len(effect.triggers_special_gems)}")
    if effect.triggers_special_gems:
        for t_pos in effect.triggers_special_gems:
            t_gem = board.get(t_pos)
            console.print(f"    - {t_gem.name} at ({t_pos.row}, {t_pos.col})")
    if effect.secondary_effects:
        console.print(f"  Secondary Effects: {len(effect.secondary_effects)}")
        for sec in effect.secondary_effects:
            console.print(
                f"    - {sec.gem_type.name} at "
                f"({sec.source_position.row}, {sec.source_position.col})"
            )
    console.print(f"  Description: {effect.description}")

    # Show the board for context.
    console.print()
    console.print("[bold]Board:[/bold]")
    render_board(board, show_functions=not no_functions)


@special_gems.command("from-match")
@click.option(
    "--match-result-json",
    required=True,
    help=(
        "Match result as JSON: "
        '{"matches": [{"positions": [[r,c],...], "gem_type": N, "is_horizontal": true}], ...}'
    ),
)
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def from_match(match_result_json: str, config_path: str) -> None:
    """Determine what special gem a match result creates."""
    _board_svc, _scoring_svc, special_svc, _gen_svc = build_sync_services(config_path)

    try:
        raw = json.loads(match_result_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    # Build MatchResult from JSON.
    try:
        matches: list[MatchGroup] = []
        for m in raw.get("matches", []):
            positions = frozenset(Position(p[0], p[1]) for p in m["positions"])
            matches.append(
                MatchGroup(
                    positions=positions,
                    gem_type=GemType(m["gem_type"]),
                    is_horizontal=m.get("is_horizontal", True),
                )
            )

        total_gems = raw.get("total_gems_matched", sum(m.length for m in matches))
        creates_special = raw.get("creates_special_gem", False)

        match_result = MatchResult(
            matches=tuple(matches),
            total_gems_matched=total_gems,
            creates_special_gem=creates_special,
        )
    except (KeyError, TypeError, ValueError) as exc:
        console.print(f"[red]Error parsing match result: {exc}[/red]")
        return

    try:
        result = special_svc.get_special_gem_for_match(match_result)
    except AppError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        return

    console.print("[bold]Match Analysis:[/bold]")
    if result is None:
        console.print("  Creates: No special gem (3-match)")
    else:
        gem_type, pos = result
        console.print(f"  Creates: {gem_type.name}")
        console.print(f"  Placement: ({pos.row}, {pos.col})")


@special_gems.command("simulate")
@click.option("--board", "board_json", required=True, help="Board as JSON 2D array.")
@click.option("--position", required=True, help="Position as 'row,col'.")
@click.option(
    "--target-color",
    default=None,
    help="Target color for Chromatic Orb (e.g. RED, BLUE).",
)
@click.option(
    "--apply",
    "apply_effect",
    is_flag=True,
    default=False,
    help="Show resulting board after applying the effect.",
)
@click.option(
    "--no-functions",
    is_flag=True,
    default=False,
    help="Disable function overlay in board display.",
)
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def simulate(
    board_json: str,
    position: str,
    target_color: str | None,
    apply_effect: bool,
    no_functions: bool,
    config_path: str,
) -> None:
    """Simulate a special gem activation and optionally show resulting board."""
    _board_svc, _scoring_svc, special_svc, _gen_svc = build_sync_services(config_path)

    try:
        data: list[list[int]] = json.loads(board_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    board = BoardState.from_list(data)

    try:
        pos = _parse_position(position)
    except click.BadParameter as exc:
        console.print(f"[red]{exc}[/red]")
        return

    color: GemType | None = None
    if target_color is not None:
        try:
            color = _parse_gem_type(target_color)
        except click.BadParameter as exc:
            console.print(f"[red]{exc}[/red]")
            return

    try:
        effect = special_svc.calculate_effect(board, pos, target_color=color)
    except AppError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        return

    console.print("[bold]Simulation:[/bold]")
    console.print(f"  Type: {effect.gem_type.name}")
    console.print(f"  Affected: {len(effect.affected_positions)} positions")
    console.print(f"  Description: {effect.description}")
    console.print(f"  Chain Triggers: {len(effect.triggers_special_gems)}")

    if effect.triggers_special_gems:
        for t_pos in effect.triggers_special_gems:
            t_gem = board.get(t_pos)
            console.print(f"    - {t_gem.name} at ({t_pos.row}, {t_pos.col})")

    show_funcs = not no_functions

    if apply_effect:
        new_board, cleared = special_svc.apply_effect(board, effect)

        console.print()
        console.print("[bold]Before:[/bold]")
        render_board(board, show_functions=show_funcs)

        console.print()
        console.print(f"[bold]After ({len(cleared)} gems cleared):[/bold]")
        render_board(new_board, show_functions=show_funcs)
