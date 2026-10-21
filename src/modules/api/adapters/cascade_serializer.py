"""Shared cascade step serialization for move responses.

Extracts the ~130-line cascade animation buffer construction used by
both match and campaign move endpoints into a reusable function.
"""

from __future__ import annotations

from typing import Any


def serialize_cascade_steps(cascades: list) -> list[dict[str, Any]]:
    """Serialize cascade steps into the frontend animation buffer format.

    Args:
        cascades: List of CascadeStep objects from MoveProcessingResult.

    Returns:
        List of dicts matching the cascade_steps JSON contract.
    """
    cascade_steps: list[dict[str, Any]] = []

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


def serialize_applied_modifiers(move_result: object) -> list[dict[str, Any]]:
    """Serialize applied card modifiers from a move result.

    Args:
        move_result: MoveProcessingResult with optional applied_modifiers.

    Returns:
        List of modifier dicts.
    """
    return [
        {
            "card_id": m.card_id,
            "card_name": m.card_name,
            "hook": m.hook,
            "description": m.description,
        }
        for m in (
            move_result.applied_modifiers  # type: ignore[attr-defined]
            if hasattr(move_result, "applied_modifiers")
            else []
        )
    ]
