"""CLI commands for the board module.

Provides development and debugging commands for the match-3 grid engine.
Uses Click for command parsing and Rich for coloured terminal output.

The board module is fully synchronous, so no async bridge is needed.
Uses ``build_sync_services()`` to create all sync services from config.

Includes an ``interactive`` REPL for exploring seeded boards move-by-move
and exporting tutorial scripts as JSON.

Known good test boards (for quick debugging):
  seed=1, move (4,2)->(5,2), cascade_seed=31  → 5+ steps (8 with cards)
    board: [[4,5,1,4,2,2,5,3],[6,5,5,4,2,5,2,3],[1,1,2,2,5,2,3,6],
            [6,5,4,2,1,1,4,6],[4,5,4,6,6,4,3,1],[4,6,6,2,6,6,3,6],
            [1,5,5,4,2,6,2,1],[6,6,5,3,2,1,2,5]]
    With --cards 103 (Cross Fire): 8 steps, injections on steps 2,4,6,8
"""

from __future__ import annotations

import json
import time

import click

from src.cli.helpers.display import console, render_board, render_move_result
from src.cli.helpers.service_factory import build_sync_services
from src.core.errors import AppError
from src.core.types.board import BoardState
from src.core.types.game import Move, Position


def _build_modifiers_from_ids(card_ids_str: str) -> object | None:
    """Build a CardModifierEngine from comma-separated card IDs.

    Loads definitions directly from JSON — no database needed.
    Returns None and prints an error if any card ID is invalid.
    """
    from pathlib import Path

    from src.modules.cards.modifier_engine import CardModifierEngine
    from src.modules.cards.modifier_types import CardModifierDef

    defs_path = Path("config/card_definitions.json")
    with open(defs_path, encoding="utf-8") as f:
        raw = json.load(f)
    cards_dict = raw.get("cards", raw)

    card_defs: list[CardModifierDef] = []
    for id_str in card_ids_str.split(","):
        card_id = id_str.strip()
        defn = cards_dict.get(card_id)
        if defn is None:
            console.print(f"[red]Unknown card ID: {card_id}[/red]")
            return None
        if not defn.get("effect"):
            console.print(f"[yellow]Card {card_id} ({defn['name']}) has no effect, skipping.[/yellow]")
            continue
        card_defs.append(
            CardModifierDef(
                card_id=int(card_id),
                name=defn["name"],
                trigger=defn["trigger"],
                effect=defn["effect"],
                effect_params=dict(defn.get("effect_params", {})),
                trigger_condition=(
                    dict(defn["trigger_condition"])
                    if defn.get("trigger_condition")
                    else None
                ),
                tags=list(defn.get("tags", [])),
            )
        )

    engine = CardModifierEngine(card_defs)
    console.print(f"[dim]Card modifiers: {', '.join(d.name for d in card_defs)}[/dim]")
    return engine


# ------------------------------------------------------------------
# Click group
# ------------------------------------------------------------------


@click.group("board")
def board() -> None:
    """Board module -- match-3 grid commands."""


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------


@board.command("generate")
@click.option("--seed", type=int, default=None, help="RNG seed (random if omitted).")
@click.option("--width", type=int, default=None, help="Board width override.")
@click.option("--height", type=int, default=None, help="Board height override.")
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
def generate(
    seed: int | None,
    width: int | None,
    height: int | None,
    no_functions: bool,
    config_path: str,
) -> None:
    """Generate and display a new board."""
    import random as _random

    board_svc, _scoring_svc, _special_svc, _gen_svc = build_sync_services(config_path)

    actual_seed = seed if seed is not None else _random.randint(0, 2**31 - 1)
    # BoardService exposes board dimensions only as private attrs.
    # TODO: add public board_width/board_height properties to BoardService.
    actual_width = width if width is not None else board_svc._board_width
    actual_height = height if height is not None else board_svc._board_height

    t0 = time.perf_counter()
    board_state = board_svc.create_board(actual_width, actual_height, actual_seed)
    elapsed = (time.perf_counter() - t0) * 1000

    console.print(f"[bold]Board generated[/bold] (seed={actual_seed}, {elapsed:.1f}ms)")
    render_board(board_state, show_functions=not no_functions)
    console.print(f"Has valid moves: {board_svc.has_valid_moves(board_state)}")


@board.command("detect-matches")
@click.option("--board", "board_json", required=True, help="Board as JSON 2D array.")
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
def detect_matches(board_json: str, no_functions: bool, config_path: str) -> None:
    """Find matches on a given board."""
    board_svc, _scoring_svc, _special_svc, _gen_svc = build_sync_services(config_path)

    try:
        data: list[list[int]] = json.loads(board_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    board_state = BoardState.from_list(data)
    result = board_svc.detect_matches(board_state)

    if not result.matches:
        console.print("[yellow]No matches found.[/yellow]")
        return

    console.print(f"[bold]Matches found: {len(result.matches)}[/bold]")
    for i, mg in enumerate(result.matches, 1):
        orientation = "HORIZONTAL" if mg.is_horizontal else "VERTICAL"
        positions_str = ", ".join(
            f"({p.row},{p.col})"
            for p in sorted(mg.positions, key=lambda p: (p.row, p.col))
        )
        console.print(
            f"  Match {i}: {orientation}, gem_type={mg.gem_type.name}, "
            f"positions=[{positions_str}]"
        )

    console.print(f"Total gems matched: {result.total_gems_matched}")
    if result.creates_special_gem:
        console.print(
            f"Creates special gem: {result.special_gem_type.name} "  # type: ignore[union-attr]
            f"at ({result.special_gem_position.row},{result.special_gem_position.col})"  # type: ignore[union-attr]
        )
    else:
        console.print("Creates special gem: No")


@board.command("process-move")
@click.option("--board", "board_json", required=True, help="Board as JSON 2D array.")
@click.option(
    "--from",
    "from_pos",
    required=True,
    help="Source position as ROW,COL.",
)
@click.option(
    "--to",
    "to_pos",
    required=True,
    help="Target position as ROW,COL.",
)
@click.option("--seed", type=int, required=True, help="RNG seed for cascades.")
@click.option(
    "--cards",
    "card_ids",
    default=None,
    help="Comma-separated card IDs to equip (e.g. 103,42).",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed cascade output with position lists.",
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
def process_move(
    board_json: str,
    from_pos: str,
    to_pos: str,
    seed: int,
    card_ids: str | None,
    verbose: bool,
    no_functions: bool,
    config_path: str,
) -> None:
    """Process a complete move with cascades."""
    board_svc, _scoring_svc, _special_svc, _gen_svc = build_sync_services(config_path)

    # Build card modifier engine from card IDs if provided.
    modifiers = None
    if card_ids:
        modifiers = _build_modifiers_from_ids(card_ids)
        if modifiers is None:
            return  # Error already printed.

    try:
        data: list[list[int]] = json.loads(board_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    board_state = BoardState.from_list(data)

    try:
        fr, fc = (int(x) for x in from_pos.split(","))
        tr, tc = (int(x) for x in to_pos.split(","))
    except ValueError:
        console.print("[red]Positions must be in ROW,COL format with integers.[/red]")
        return

    move = Move(
        from_pos=Position(fr, fc),
        to_pos=Position(tr, tc),
        timestamp_ms=0,
    )

    try:
        result = board_svc.process_move(board_state, move, seed, modifiers=modifiers)
    except AppError as exc:
        console.print(f"[red]Error: {exc.message}[/red]")
        return

    render_move_result(result, verbose=verbose)

    console.print("[bold]Final board:[/bold]")
    render_board(result.final_board, show_functions=not no_functions)


@board.command("has-moves")
@click.option("--board", "board_json", required=True, help="Board as JSON 2D array.")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def has_moves(board_json: str, config_path: str) -> None:
    """Check if any valid moves exist (deadlock detection)."""
    board_svc, _scoring_svc, _special_svc, _gen_svc = build_sync_services(config_path)

    try:
        data: list[list[int]] = json.loads(board_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON: {exc}[/red]")
        return

    board_state = BoardState.from_list(data)

    result = board_svc.has_valid_moves(board_state)
    if result:
        console.print("[green]Valid moves exist.[/green]")
    else:
        console.print("[red]DEADLOCK -- no valid moves.[/red]")


# ------------------------------------------------------------------
# Enrich tutorial script with cascade data
# ------------------------------------------------------------------


def _serialize_cascade_steps(cascades: list) -> list[dict]:
    """Convert backend CascadeStep objects to frontend-compatible JSON dicts.

    Mirrors the serialization logic in ``matches.py`` so that the output
    can be parsed directly by ``CascadeStepResponse.fromJson()`` on the
    Dart side.
    """
    cascade_steps = []
    for step in cascades:
        protected = {
            (att.center_pos.row, att.center_pos.col)
            for att in step.special_attractions
        }
        removals = []
        for match_group in step.matches.matches:
            for pos in match_group.positions:
                if (pos.row, pos.col) not in protected:
                    removals.append({"row": pos.row, "col": pos.col})

        drops = [
            {
                "gem_type": int(d.gem_type),
                "from_row": d.from_pos.row,
                "from_col": d.from_pos.col,
                "to_row": d.to_pos.row,
                "to_col": d.to_pos.col,
            }
            for d in step.gems_dropped
        ]

        spawns = [
            {
                "gem_type": int(s.gem_type),
                "row": s.position.row,
                "col": s.position.col,
            }
            for s in step.gems_spawned
        ]

        special = None
        if step.matches.creates_special_gem and step.matches.special_gem_position:
            sp = step.matches.special_gem_position
            special = {
                "row": sp.row,
                "col": sp.col,
                "gem_type": int(step.matches.special_gem_type),
                "color": (
                    int(step.matches.matches[0].gem_type)
                    if step.matches.matches
                    else 0
                ),
            }

        activations = [
            {
                "gem_type": int(act.gem_type),
                "row": act.position.row,
                "col": act.position.col,
                "affected": [
                    {"row": p.row, "col": p.col}
                    for p in sorted(
                        act.affected_positions, key=lambda p: (p.row, p.col)
                    )
                ],
                "is_mega": act.mega_func_value is not None,
                "mega_func": act.mega_func_value,
            }
            for act in step.special_activations
        ]

        attractions = [
            {
                "pos_a_row": att.pos_a.row,
                "pos_a_col": att.pos_a.col,
                "pos_b_row": att.pos_b.row,
                "pos_b_col": att.pos_b.col,
                "center_row": att.center_pos.row,
                "center_col": att.center_pos.col,
                "func_a": int(att.func_a),
                "func_b": int(att.func_b),
                "mega_func": att.mega_func,
            }
            for att in step.special_attractions
        ]

        injected = None
        if step.injected_special is not None:
            inj_pos, inj_func = step.injected_special
            injected = {
                "row": inj_pos.row,
                "col": inj_pos.col,
                "function": inj_func,
            }

        injected_act = None
        if step.injected_activation is not None:
            act = step.injected_activation
            injected_act = {
                "gem_type": int(act.gem_type),
                "row": act.position.row,
                "col": act.position.col,
                "affected": [
                    {"row": p.row, "col": p.col}
                    for p in sorted(
                        act.affected_positions, key=lambda p: (p.row, p.col)
                    )
                ],
                "is_mega": act.mega_func_value is not None,
                "mega_func": act.mega_func_value,
            }

        injected_drops = [
            {
                "gem_type": int(d.gem_type),
                "from_row": d.from_pos.row,
                "from_col": d.from_pos.col,
                "to_row": d.to_pos.row,
                "to_col": d.to_pos.col,
            }
            for d in step.injected_drops
        ]

        injected_spawns = [
            {
                "gem_type": int(s.gem_type),
                "row": s.position.row,
                "col": s.position.col,
            }
            for s in step.injected_spawns
        ]

        cascade_steps.append(
            {
                "step_number": step.step_number,
                "removals": removals,
                "drops": drops,
                "spawns": spawns,
                "special_gem_created": special,
                "special_activations": activations,
                "special_attractions": attractions,
                "injected_special": injected,
                "injected_activation": injected_act,
                "injected_drops": injected_drops,
                "injected_spawns": injected_spawns,
            }
        )
    return cascade_steps


@board.command("enrich-tutorial")
@click.option(
    "--input",
    "input_path",
    required=True,
    help="Path to the raw tutorial_script.json.",
)
@click.option(
    "--output",
    "output_path",
    required=True,
    help="Path for the enriched output JSON.",
)
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def enrich_tutorial(input_path: str, output_path: str, config_path: str) -> None:
    """Enrich a tutorial script with full cascade step data.

    Reads an existing tutorial JSON (produced by ``board interactive``),
    re-processes each move through the board engine, and serializes the
    detailed cascade step data that ``AnimationSequencer`` needs for
    full cascade animations.

    The output JSON can be loaded directly by the Flutter frontend's
    ``MoveResultResponse.fromJson()`` and ``BoardStateResponse.fromJson()``.
    """
    board_svc, _scoring_svc, _special_svc, _gen_svc = build_sync_services(config_path)

    try:
        with open(input_path, "r") as f:
            script = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        console.print(f"[red]Error reading input: {exc}[/red]")
        return

    seed = script["seed"]
    steps = script["steps"]

    console.print(
        f"[bold cyan]Enriching tutorial script[/bold cyan]  "
        f"seed={seed}, {len(steps)} steps"
    )

    enriched_steps = []
    for step_data in steps:
        step_num = step_data["step"]
        move_info = step_data["move"]

        # Reconstruct board state from board_before.
        board_state = BoardState.from_list(step_data["board_before"])

        # Construct the move.
        move = Move(
            from_pos=Position(move_info["from_row"], move_info["from_col"]),
            to_pos=Position(move_info["to_row"], move_info["to_col"]),
            timestamp_ms=0,
        )

        # Re-process the move through the engine.
        try:
            result = board_svc.process_move(board_state, move, seed)
        except AppError as exc:
            console.print(
                f"[red]Step {step_num}: Error processing move: {exc.message}[/red]"
            )
            return

        if not result.was_valid_match:
            console.print(f"[red]Step {step_num}: Move produced no match![/red]")
            return

        # Serialize cascade steps.
        cascade_steps = _serialize_cascade_steps(result.cascades)

        # Build new_board in BoardStateResponse format (synthetic metadata).
        new_board = {
            "cells": result.final_board.grid.tolist(),
            "functions": result.final_board.func_grid.tolist(),
            "size": result.final_board.width,
            "moves_made": step_num,
            "moves_remaining": 99,
            "score": 0,
            "has_valid_moves": True,
        }

        # Build board_before / board_after in BoardStateResponse format.
        board_before_resp = {
            "cells": step_data["board_before"]["cells"],
            "functions": step_data["board_before"]["functions"],
            "size": 8,
            "moves_made": step_num - 1,
            "moves_remaining": 99,
            "score": 0,
            "has_valid_moves": True,
        }
        board_after_resp = {
            "cells": step_data["board_after"]["cells"],
            "functions": step_data["board_after"]["functions"],
            "size": 8,
            "moves_made": step_num,
            "moves_remaining": 99,
            "score": 0,
            "has_valid_moves": True,
        }

        # Build move_result in MoveResultResponse format.
        move_result = {
            "valid": True,
            "score_gained": 0,
            "new_board": new_board,
            "matches_found": result.total_matches,
            "cascades": result.chain_count,
            "special_gems_created": len(result.special_gems_created),
            "match_completed": False,
            "match_status": "active",
            "moves_remaining": 99,
            "move_number": step_num,
            "cascade_steps": cascade_steps,
            "applied_modifiers": [],
            "raid_result": None,
            "reward_result": None,
        }

        # Build enriched step (preserve coach_text, add move_result).
        enriched_step = {
            "step": step_num,
            "move": move_info,
            "coach_text": step_data.get("coach_text", ""),
            "board_before": board_before_resp,
            "board_after": board_after_resp,
            "move_result": move_result,
            "was_valid_match": step_data.get("was_valid_match", True),
            "total_gems_cleared": result.total_gems_cleared,
            "chain_count": result.chain_count,
            "special_gems_created": [
                {
                    "row": pos.row,
                    "col": pos.col,
                    "gem_type": gt.name if hasattr(gt, "name") else str(gt),
                }
                for pos, gt in result.special_gems_created
            ],
            "cascade_count": len(result.cascades),
        }

        enriched_steps.append(enriched_step)

        # Summary per step.
        total_removals = sum(len(cs["removals"]) for cs in cascade_steps)
        total_activations = sum(len(cs["special_activations"]) for cs in cascade_steps)
        total_attractions = sum(len(cs["special_attractions"]) for cs in cascade_steps)
        console.print(
            f"  Step {step_num}: {len(cascade_steps)} cascade steps, "
            f"{total_removals} removals, {total_activations} activations, "
            f"{total_attractions} attractions"
        )

    # Build initial_board in BoardStateResponse format.
    initial_board_resp = {
        "cells": script["initial_board"]["cells"],
        "functions": script["initial_board"]["functions"],
        "size": 8,
        "moves_made": 0,
        "moves_remaining": 99,
        "score": 0,
        "has_valid_moves": True,
    }

    enriched_script = {
        "seed": seed,
        "initial_board": initial_board_resp,
        "steps": enriched_steps,
    }

    with open(output_path, "w") as f:
        json.dump(enriched_script, f, indent=2)

    console.print(
        f"\n[bold green]Enriched tutorial script written:[/bold green] "
        f"{output_path} ({len(enriched_steps)} steps)"
    )


# ------------------------------------------------------------------
# Interactive REPL
# ------------------------------------------------------------------


@board.command("interactive")
@click.option("--seed", type=int, default=None, help="RNG seed (random if omitted).")
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed cascade output after each move.",
)
@click.option(
    "--output",
    "output_path",
    default="tutorial_script.json",
    help="File path for exported tutorial script.",
    show_default=True,
)
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def interactive(
    seed: int | None,
    verbose: bool,
    output_path: str,
    config_path: str,
) -> None:
    """Interactive board REPL for exploring moves and exporting tutorial scripts.

    Generates a board, then enters a loop where you can make moves, see
    results, and build up a tutorial script.  Type 'help' for commands.
    """
    import random as _random

    from src.modules.api.adapters.bot_hints import BotHintGenerator

    board_svc, _scoring_svc, _special_svc, board_gen_svc = build_sync_services(
        config_path
    )

    actual_seed = seed if seed is not None else _random.randint(0, 2**31 - 1)
    board_state = board_svc.create_board(
        board_svc._board_width, board_svc._board_height, actual_seed
    )

    # Tutorial script accumulator
    script_steps: list[dict] = []
    initial_board_dict = board_state.to_dict()
    move_number = 0

    console.print(
        f"[bold cyan]Interactive Board REPL[/bold cyan]  seed={actual_seed}\n"
        f"Type [bold]help[/bold] for commands.\n"
    )
    render_board(board_state)

    while True:
        try:
            raw = console.input("[bold green]> [/bold green]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Exiting.[/dim]")
            break

        if not raw:
            continue

        parts = raw.lower().split()
        cmd = parts[0]

        # ----- help -----
        if cmd == "help":
            console.print(
                "[bold]Commands:[/bold]\n"
                "  [cyan]r1,c1 r2,c2[/cyan]        Make a move (e.g. 3,2 3,3)\n"
                "  [cyan]moves[/cyan]              Show all valid moves\n"
                "  [cyan]board[/cyan]              Re-display the current board\n"
                "  [cyan]undo[/cyan]               Undo the last move\n"
                "  [cyan]annotate TEXT[/cyan]      Add coach text to the last move\n"
                "  [cyan]script[/cyan]             Show the current tutorial script summary\n"
                "  [cyan]export[/cyan]             Export tutorial script to JSON and quit\n"
                "  [cyan]quit[/cyan]               Quit without exporting\n"
            )

        # ----- quit -----
        elif cmd in ("quit", "exit", "q"):
            if script_steps:
                console.print(
                    f"[yellow]Discarding {len(script_steps)} recorded moves.[/yellow]"
                )
            break

        # ----- board -----
        elif cmd == "board":
            render_board(board_state)

        # ----- moves -----
        elif cmd == "moves":
            from src.cli.helpers.display import _COLORS, _COLOR_LABELS

            hints = BotHintGenerator.find_valid_moves(board_state.grid.tolist())
            if not hints:
                console.print("[red]No valid moves (deadlock).[/red]")
            else:
                console.print(f"[bold]{len(hints)} valid moves:[/bold]")
                for h in sorted(hints, key=lambda h: -h.estimated_score):
                    fc = int(board_state.grid[h.from_row, h.from_col])
                    tc = int(board_state.grid[h.to_row, h.to_col])
                    fl = _COLOR_LABELS.get(fc, "?")
                    tl = _COLOR_LABELS.get(tc, "?")
                    fs = _COLORS.get(fc, "white")
                    ts = _COLORS.get(tc, "white")
                    console.print(
                        f"  ({h.from_row},{h.from_col})[{fs}]{fl}[/{fs}]"
                        f" <-> "
                        f"({h.to_row},{h.to_col})[{ts}]{tl}[/{ts}]"
                        f"  score~{h.estimated_score}"
                    )

        # ----- undo -----
        elif cmd == "undo":
            if not script_steps:
                console.print("[yellow]Nothing to undo.[/yellow]")
            else:
                removed = script_steps.pop()
                board_state = BoardState.from_list(removed["board_before"])
                move_number -= 1
                console.print(
                    f"[green]Undone move {move_number + 1}. "
                    f"Back to {len(script_steps)} recorded moves.[/green]"
                )
                render_board(board_state)

        # ----- annotate -----
        elif cmd == "annotate":
            text = raw[len("annotate"):].strip()
            if not script_steps:
                console.print("[yellow]No moves to annotate.[/yellow]")
            elif not text:
                console.print("[yellow]Usage: annotate <coach text>[/yellow]")
            else:
                script_steps[-1]["coach_text"] = text
                console.print(
                    f"[green]Move {len(script_steps)} annotated:[/green] {text}"
                )

        # ----- script -----
        elif cmd == "script":
            if not script_steps:
                console.print("[dim]No moves recorded yet.[/dim]")
            else:
                console.print(
                    f"[bold]Tutorial script: {len(script_steps)} moves "
                    f"(seed={actual_seed})[/bold]"
                )
                for i, step in enumerate(script_steps, 1):
                    m = step["move"]
                    text = step.get("coach_text", "")
                    tag = f'  "{text}"' if text else ""
                    console.print(
                        f"  {i}. ({m['from_row']},{m['from_col']}) -> "
                        f"({m['to_row']},{m['to_col']})"
                        f"  cleared={step['total_gems_cleared']}"
                        f"  chains={step['chain_count']}{tag}"
                    )

        # ----- export -----
        elif cmd == "export":
            if not script_steps:
                console.print("[yellow]No moves to export.[/yellow]")
                continue

            tutorial_data = {
                "seed": actual_seed,
                "initial_board": initial_board_dict,
                "steps": script_steps,
            }
            with open(output_path, "w") as f:
                json.dump(tutorial_data, f, indent=2)
            console.print(
                f"[bold green]Tutorial script exported:[/bold green] "
                f"{output_path} ({len(script_steps)} moves)"
            )
            break

        # ----- move: [move] r1,c1 r2,c2 -----
        else:
            try:
                move_raw = raw
                # Strip optional "move" prefix
                if move_raw.lower().startswith("move "):
                    move_raw = move_raw[5:]
                tokens = move_raw.replace(",", " ").split()
                if len(tokens) != 4:
                    raise ValueError("Expected 4 integers")
                fr, fc, tr, tc = (int(t) for t in tokens)
            except ValueError:
                console.print(
                    "[red]Invalid input. Move format: r1,c1 r2,c2 "
                    "(e.g. 3,2 3,3)[/red]"
                )
                continue

            move = Move(
                from_pos=Position(fr, fc),
                to_pos=Position(tr, tc),
                timestamp_ms=0,
            )

            try:
                result = board_svc.process_move(board_state, move, actual_seed)
            except AppError as exc:
                console.print(f"[red]Error: {exc.message}[/red]")
                continue

            if not result.was_valid_match:
                console.print("[yellow]Invalid move (no match). Try again.[/yellow]")
                continue

            move_number += 1
            render_move_result(result, verbose=verbose)

            # Record the step
            step_record = {
                "step": move_number,
                "move": {
                    "from_row": fr,
                    "from_col": fc,
                    "to_row": tr,
                    "to_col": tc,
                },
                "coach_text": "",
                "board_before": board_state.to_dict(),
                "board_after": result.final_board.to_dict(),
                "was_valid_match": result.was_valid_match,
                "total_gems_cleared": result.total_gems_cleared,
                "chain_count": result.chain_count,
                "special_gems_created": [
                    {
                        "row": pos.row,
                        "col": pos.col,
                        "gem_type": gt.name if hasattr(gt, "name") else str(gt),
                    }
                    for pos, gt in result.special_gems_created
                ],
                "cascade_count": len(result.cascades),
            }
            script_steps.append(step_record)

            # Advance board state
            board_state = result.final_board

            console.print(f"\n[bold]Board after move {move_number}:[/bold]")
            render_board(board_state)
            console.print(
                f"[dim]({len(script_steps)} moves recorded. "
                f"Type 'annotate <text>' to add coach text.)[/dim]"
            )
