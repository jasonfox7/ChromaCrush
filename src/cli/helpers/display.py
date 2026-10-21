"""Shared Rich-based board display for CLI commands.

Provides rendering functions for the two-grid board model (color + function),
cascade step summaries, and move processing result overviews.

All output uses Rich console markup for colored, formatted terminal output.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from src.core.types.board import BoardState
from src.core.types.game import GemFunction, is_mega_gem, decode_mega_gem
from src.modules.board.types import CascadeStep, MoveProcessingResult

console = Console()

# ---------------------------------------------------------------------------
# Display constants
# ---------------------------------------------------------------------------

_COLORS: dict[int, str] = {
    0: "dim",
    1: "bold bright_red",
    2: "bold bright_blue",
    3: "bold bright_green",
    4: "bold bright_yellow",
    5: "bold bright_magenta",
    6: "bold dark_orange",
}

_FUNC_SYMBOLS: dict[int, str | None] = {
    0: None,
    1: "\u2501",   # ━  LINE_BLAST_H
    2: "\u2503",   # ┃  LINE_BLAST_V
    3: "\u25c9",   # ◉  RADIAL_BOMB
    4: "\u25c6",   # ◆  CHROMATIC_ORB
}

_COLOR_LABELS: dict[int, str] = {
    1: "R",
    2: "B",
    3: "G",
    4: "Y",
    5: "P",
    6: "O",
}

_FUNC_NAMES: dict[int, str] = {
    0: "NEUTRAL",
    1: "LINE_BLAST_H",
    2: "LINE_BLAST_V",
    3: "RADIAL_BOMB",
    4: "CHROMATIC_ORB",
}


# ---------------------------------------------------------------------------
# Board rendering
# ---------------------------------------------------------------------------


def render_board(board: BoardState, show_functions: bool = True) -> None:
    """Print the board with Rich, showing both color and function grids.

    When *show_functions* is True and a gem has a non-NEUTRAL function,
    the function symbol is displayed instead of the color letter, but
    still rendered in the gem's color.  Mega gems (func 11-44) show
    ``M`` in bright_white.

    Args:
        board: The board state to render.
        show_functions: If True, overlay function symbols on colored gems.
    """
    table = Table(
        show_header=True,
        header_style="bold",
        show_lines=True,
        padding=(0, 1),
        title="Board",
    )

    # Column headers: col indices
    table.add_column("", style="dim", width=2)  # row label
    for col in range(board.width):
        table.add_column(str(col), justify="center", width=3)

    for row in range(board.height):
        cells: list[Text] = []
        for col in range(board.width):
            color_val = int(board.grid[row, col])
            func_val = int(board.func_grid[row, col])  # type: ignore[index]

            if color_val == 0:
                # Empty cell
                cells.append(Text("\u00b7", style="dim"))  # middle dot
                continue

            rich_color = _COLORS.get(color_val, "white")

            if show_functions and is_mega_gem(func_val):
                # Mega gem -- show M in bright_white
                cells.append(Text("M", style="bright_white bold"))
            elif show_functions and func_val != 0:
                # Special gem -- show function symbol in gem color
                symbol = _FUNC_SYMBOLS.get(func_val, "?")
                cells.append(Text(symbol or "?", style=f"{rich_color} bold"))
            else:
                # Normal gem -- show color letter
                label = _COLOR_LABELS.get(color_val, "?")
                cells.append(Text(label, style=rich_color))

        table.add_row(str(row), *cells)

    console.print(table)


# ---------------------------------------------------------------------------
# Cascade step rendering
# ---------------------------------------------------------------------------


def render_cascade_step(
    step: CascadeStep, step_number: int, verbose: bool = False
) -> None:
    """Print a summary of a single cascade step.

    Shows counts of removals, drops, spawns, special activations,
    attractions, and specials created.  When *verbose* is True, full
    position lists are included.

    Args:
        step: The cascade step to render.
        step_number: 1-based step index (for display).
        verbose: If True, include detailed position lists.
    """
    removals = step.matches.total_gems_matched
    drops = len(step.gems_dropped)
    spawns = len(step.gems_spawned)
    activations = len(step.special_activations)
    attractions = len(step.special_attractions)
    specials_created = 1 if step.matches.creates_special_gem else 0
    # Also count injected specials from card system
    if step.injected_special is not None:
        specials_created += 1

    console.print(
        f"  [bold cyan]Step {step_number}[/bold cyan]  "
        f"removed=[yellow]{removals}[/yellow]  "
        f"drops=[blue]{drops}[/blue]  "
        f"spawns=[green]{spawns}[/green]  "
        f"activations=[red]{activations}[/red]  "
        f"attractions=[magenta]{attractions}[/magenta]  "
        f"specials_created=[bright_white]{specials_created}[/bright_white]"
    )

    if verbose:
        # Match positions
        for mg in step.matches.matches:
            positions_str = ", ".join(
                f"({p.row},{p.col})" for p in sorted(mg.positions, key=lambda p: (p.row, p.col))
            )
            color_name = mg.gem_type.name if hasattr(mg.gem_type, "name") else str(mg.gem_type)
            direction = "H" if mg.is_horizontal else "V"
            console.print(
                f"    match: {color_name} {direction} len={mg.length} @ [{positions_str}]"
            )

        # Drops
        for drop in step.gems_dropped:
            console.print(
                f"    drop: ({drop.from_pos.row},{drop.from_pos.col}) -> "
                f"({drop.to_pos.row},{drop.to_pos.col}) dist={drop.distance}"
            )

        # Spawns
        for spawn in step.gems_spawned:
            gem_name = spawn.gem_type.name if hasattr(spawn.gem_type, "name") else str(spawn.gem_type)
            console.print(
                f"    spawn: {gem_name} @ ({spawn.position.row},{spawn.position.col}) col={spawn.column}"
            )

        # Special activations
        for act in step.special_activations:
            gem_name = act.gem_type.name if hasattr(act.gem_type, "name") else str(act.gem_type)
            affected_str = ", ".join(
                f"({p.row},{p.col})" for p in sorted(act.affected_positions, key=lambda p: (p.row, p.col))
            )
            mega_tag = f" mega={act.mega_func_value}" if act.mega_func_value else ""
            console.print(
                f"    activation: {gem_name} @ ({act.position.row},{act.position.col})"
                f" cleared={len(act.affected_positions)}{mega_tag} [{affected_str}]"
            )

        # Special attractions
        for attr in step.special_attractions:
            func_a_name = _FUNC_NAMES.get(int(attr.func_a), str(attr.func_a))
            func_b_name = _FUNC_NAMES.get(int(attr.func_b), str(attr.func_b))
            console.print(
                f"    attraction: ({attr.pos_a.row},{attr.pos_a.col}) {func_a_name} + "
                f"({attr.pos_b.row},{attr.pos_b.col}) {func_b_name} -> "
                f"mega@({attr.center_pos.row},{attr.center_pos.col}) func={attr.mega_func}"
            )

        # Injected special (card system)
        if step.injected_special is not None:
            pos, func_value = step.injected_special
            func_name = _FUNC_NAMES.get(func_value, str(func_value))
            console.print(
                f"    injected_special: {func_name} @ ({pos.row},{pos.col})"
            )


# ---------------------------------------------------------------------------
# Move result rendering
# ---------------------------------------------------------------------------


def render_move_result(result: MoveProcessingResult, verbose: bool = False) -> None:
    """Print a summary of a full move processing result.

    Shows validity, chain count, total gems cleared, specials created,
    then renders each cascade step.

    Args:
        result: The move processing result to display.
        verbose: If True, pass through to cascade step rendering.
    """
    valid_style = "green" if result.was_valid_match else "red"
    valid_text = "YES" if result.was_valid_match else "NO"

    console.print(f"\n[bold]Move Result[/bold]")
    console.print(
        f"  valid=[{valid_style}]{valid_text}[/{valid_style}]  "
        f"chains=[cyan]{result.chain_count}[/cyan]  "
        f"gems_cleared=[yellow]{result.total_gems_cleared}[/yellow]  "
        f"specials_created=[bright_white]{len(result.special_gems_created)}[/bright_white]"
    )

    if result.special_gems_created:
        for pos, gem_type in result.special_gems_created:
            gem_name = gem_type.name if hasattr(gem_type, "name") else str(gem_type)
            console.print(
                f"    + special: {gem_name} @ ({pos.row},{pos.col})"
            )

    if result.cascades:
        console.print(f"\n  [bold]Cascade Steps ({len(result.cascades)}):[/bold]")
        for step in result.cascades:
            render_cascade_step(step, step.step_number, verbose=verbose)

    console.print()
