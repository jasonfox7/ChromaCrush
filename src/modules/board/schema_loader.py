"""Load and validate board rules schema from JSON.

The schema defines special gem creation rules, effect areas,
mega gem combos, attraction rules, and board parameters.
BoardService loads this once at init.
"""

from __future__ import annotations

import json
from pathlib import Path

# Default schema path relative to project root.
_DEFAULT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "board_rules.json"
)

# Required top-level keys.
_REQUIRED_SECTIONS = {
    "version",
    "board",
    "match_detection",
    "special_gems",
    "mega_gems",
}

# Valid selection strategies for effects.
_VALID_SELECTS = {
    "row",
    "column",
    "radius",
    "color_match",
    "cross",
    "entire_board",
    "diagonal",
}

# Valid match patterns for special creation rules.
_VALID_PATTERNS = {"t_or_l_shape", "straight_match"}

# Valid placements for special creation rules.
_VALID_PLACEMENTS = {"intersection", "center", "middle"}


def load_board_rules(path: str | Path | None = None) -> dict:
    """Load board rules schema from JSON file.

    Args:
        path: Path to JSON file. Uses config/board_rules.json if None.

    Returns:
        Parsed and validated schema dict.

    Raises:
        FileNotFoundError: If the schema file doesn't exist.
        ValueError: If the schema fails validation.
    """
    schema_path = Path(path) if path else _DEFAULT_SCHEMA_PATH

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    errors = validate_board_rules(schema)
    if errors:
        raise ValueError(
            f"Board rules schema validation failed ({len(errors)} errors):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    return schema


def validate_board_rules(schema: dict) -> list[str]:
    """Validate a board rules schema dict.

    Returns:
        List of error strings. Empty list means valid.
    """
    errors: list[str] = []

    # Check top-level sections exist.
    for key in _REQUIRED_SECTIONS:
        if key not in schema:
            errors.append(f"Missing required section: {key}")

    if errors:
        return errors  # Can't validate further without required sections.

    _validate_board(schema.get("board", {}), errors)
    _validate_match_detection(schema.get("match_detection", {}), errors)
    functions = _validate_special_gems(schema.get("special_gems", {}), errors)
    _validate_mega_gems(schema.get("mega_gems", {}), functions, errors)

    return errors


def _validate_board(board: dict, errors: list[str]) -> None:
    """Validate the board section."""
    for key in (
        "width",
        "height",
        "gem_types",
        "max_cascade_steps",
        "min_match_length",
    ):
        val = board.get(key)
        if val is None:
            errors.append(f"board.{key} is required")
        elif not isinstance(val, int) or val < 1:
            errors.append(f"board.{key} must be a positive integer, got {val}")

    w = board.get("width", 8)
    h = board.get("height", 8)
    if isinstance(w, int) and isinstance(h, int):
        if w > 64 or h > 64:
            errors.append(f"Board dimensions too large: {w}x{h} (max 64x64)")


def _validate_match_detection(detection: dict, errors: list[str]) -> None:
    """Validate match detection rules."""
    rules = detection.get("special_creation_rules", [])
    if not isinstance(rules, list):
        errors.append("match_detection.special_creation_rules must be a list")
        return

    priorities_seen: set[int] = set()
    for i, rule in enumerate(rules):
        prefix = f"special_creation_rules[{i}]"

        priority = rule.get("priority")
        if priority is None:
            errors.append(f"{prefix}: missing priority")
        elif priority in priorities_seen:
            errors.append(f"{prefix}: duplicate priority {priority}")
        else:
            priorities_seen.add(priority)

        pattern = rule.get("pattern")
        if pattern not in _VALID_PATTERNS:
            errors.append(
                f"{prefix}: invalid pattern '{pattern}', must be one of {_VALID_PATTERNS}"
            )

        result_func = rule.get("result_function")
        if result_func is None or not isinstance(result_func, int):
            errors.append(f"{prefix}: result_function must be an integer")

        placement = rule.get("placement")
        if placement not in _VALID_PLACEMENTS:
            errors.append(
                f"{prefix}: invalid placement '{placement}', must be one of {_VALID_PLACEMENTS}"
            )


def _validate_special_gems(special_gems: dict, errors: list[str]) -> set[str]:
    """Validate special gems section. Returns set of valid function IDs."""
    functions = special_gems.get("functions", {})
    if not isinstance(functions, dict):
        errors.append("special_gems.functions must be a dict")
        return set()

    valid_ids: set[str] = set()
    for func_id, func_def in functions.items():
        prefix = f"special_gems.functions.{func_id}"
        valid_ids.add(func_id)

        if "name" not in func_def:
            errors.append(f"{prefix}: missing name")

        effect = func_def.get("effect")
        if not effect:
            errors.append(f"{prefix}: missing effect definition")
            continue

        _validate_effect(effect, prefix, errors)

    # Validate chain_reaction section.
    chain = special_gems.get("chain_reaction", {})
    max_waves = chain.get("max_waves")
    if max_waves is not None and (not isinstance(max_waves, int) or max_waves < 1):
        errors.append(
            f"special_gems.chain_reaction.max_waves must be a positive integer"
        )

    return valid_ids


def _validate_mega_gems(
    mega_gems: dict, valid_function_ids: set[str], errors: list[str]
) -> None:
    """Validate mega gems section."""
    # Validate attractions.
    attractions = mega_gems.get("attractions", {})
    dist = attractions.get("distance")
    if dist is not None and (not isinstance(dist, int) or dist < 1):
        errors.append("mega_gems.attractions.distance must be a positive integer")

    # Validate combos.
    combos = mega_gems.get("combos", {})
    if not isinstance(combos, dict):
        errors.append("mega_gems.combos must be a dict")
        return

    for combo_id, combo_def in combos.items():
        prefix = f"mega_gems.combos.{combo_id}"

        # Validate combo ID is a valid mega gem encoding.
        try:
            val = int(combo_id)
            a, b = val // 10, val % 10
            if a < 1 or a > b or b > 9:
                errors.append(
                    f"{prefix}: invalid mega gem encoding (must be AB where 1<=A<=B)"
                )
        except ValueError:
            errors.append(f"{prefix}: combo ID must be a numeric string")

        effect = combo_def.get("effect")
        if not effect:
            errors.append(f"{prefix}: missing effect definition")
            continue

        _validate_effect(effect, prefix, errors, valid_function_ids)


def _validate_effect(
    effect: dict,
    prefix: str,
    errors: list[str],
    valid_function_ids: set[str] | None = None,
) -> None:
    """Validate a single effect definition."""
    select = effect.get("select")
    if select not in _VALID_SELECTS:
        errors.append(
            f"{prefix}.effect: invalid select '{select}', must be one of {_VALID_SELECTS}"
        )

    # Validate radius if present.
    radius = effect.get("radius")
    if radius is not None:
        if not isinstance(radius, int) or radius < 0:
            errors.append(f"{prefix}.effect: radius must be a non-negative integer")
        elif radius > 32:
            errors.append(f"{prefix}.effect: radius too large ({radius}, max 32)")

    # Validate count if present.
    count = effect.get("count")
    if count is not None:
        if not isinstance(count, int) or count < 1:
            errors.append(f"{prefix}.effect: count must be a positive integer")

    # Validate spawn_effect_at_each reference.
    spawn_ref = effect.get("spawn_effect_at_each")
    if spawn_ref is not None and valid_function_ids is not None:
        if str(spawn_ref) not in valid_function_ids:
            errors.append(
                f"{prefix}.effect: spawn_effect_at_each references unknown function '{spawn_ref}'"
            )
