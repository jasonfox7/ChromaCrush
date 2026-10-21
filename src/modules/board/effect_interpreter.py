"""Schema-driven effect interpreter for board rules.

Replaces hardcoded if/elif trees in detection.py, special_gems.py,
and mega_gems.py with lookup-driven logic from config/board_rules.json.

Loaded once at BoardService.__init__.
"""

from __future__ import annotations

from collections import Counter

from src.core.types.board import BoardState, MatchGroup
from src.core.types.game import GemType, Position


class EffectInterpreter:
    """Interprets board_rules.json to drive special creation, effects, and mega combos."""

    def __init__(self, schema: dict) -> None:
        self._board: dict = schema["board"]
        self._creation_rules: list[dict] = sorted(
            schema["match_detection"]["special_creation_rules"],
            key=lambda r: r["priority"],
        )
        self._functions: dict[str, dict] = schema["special_gems"]["functions"]
        self._chain: dict = schema["special_gems"].get("chain_reaction", {})
        self._combos: dict[str, dict] = schema["mega_gems"]["combos"]
        self._attractions: dict = schema["mega_gems"]["attractions"]
        self._obstacles: dict = schema.get("obstacles", {})

        self._validate_spawn_refs()

    def _validate_spawn_refs(self) -> None:
        """Ensure spawn_effect_at_each references resolve and aren't circular."""
        for combo_id, combo_def in self._combos.items():
            ref = combo_def.get("effect", {}).get("spawn_effect_at_each")
            if ref is None:
                continue
            ref_str = str(ref)
            if ref_str not in self._functions:
                raise ValueError(
                    f"mega_gems.combos.{combo_id}: spawn_effect_at_each "
                    f"references unknown function '{ref}'"
                )
            spawned = self._functions[ref_str]
            if spawned.get("effect", {}).get("spawn_effect_at_each") is not None:
                raise ValueError(
                    f"mega_gems.combos.{combo_id}: circular spawn reference "
                    f"(function '{ref}' also has spawn_effect_at_each)"
                )

    # -------------------------------------------------------------------------
    # Special gem creation (replaces detection.py:_determine_special_gem)
    # -------------------------------------------------------------------------

    def determine_special_gem(
        self,
        matches: list[MatchGroup],
    ) -> tuple[GemType | None, Position | None]:
        """Decide which special gem a set of matches creates.

        Iterates special_creation_rules by priority order.
        Returns (special_gem_type, position) or (None, None).
        """
        h_matches = [m for m in matches if m.is_horizontal]
        v_matches = [m for m in matches if not m.is_horizontal]

        for rule in self._creation_rules:
            result = self._try_creation_rule(rule, matches, h_matches, v_matches)
            if result[0] is not None:
                return result

        return None, None

    def _try_creation_rule(
        self,
        rule: dict,
        all_matches: list[MatchGroup],
        h_matches: list[MatchGroup],
        v_matches: list[MatchGroup],
    ) -> tuple[GemType | None, Position | None]:
        """Evaluate a single creation rule against current matches."""
        pattern = rule["pattern"]
        func_id = rule["result_function"]
        placement = rule["placement"]

        if pattern == "t_or_l_shape":
            return self._try_tl_shape(h_matches, v_matches, func_id)
        if pattern == "straight_match":
            return self._try_straight_match(rule, all_matches, func_id, placement)
        return None, None

    @staticmethod
    def _try_tl_shape(
        h_matches: list[MatchGroup],
        v_matches: list[MatchGroup],
        func_id: int,
    ) -> tuple[GemType | None, Position | None]:
        """Check T/L shape: position in both a horizontal and vertical match."""
        for hm in h_matches:
            for vm in v_matches:
                intersection = hm.positions & vm.positions
                if intersection:
                    return GemType(-func_id), next(iter(intersection))
        return None, None

    @staticmethod
    def _try_straight_match(
        rule: dict,
        all_matches: list[MatchGroup],
        func_id: int,
        placement: str,
    ) -> tuple[GemType | None, Position | None]:
        """Check for straight match meeting length and orientation criteria."""
        min_length = rule.get("min_length", 4)
        orientation = rule.get("orientation")  # None, "horizontal", or "vertical"

        if orientation == "horizontal":
            candidates = [m for m in all_matches if m.is_horizontal]
        elif orientation == "vertical":
            candidates = [m for m in all_matches if not m.is_horizontal]
        else:
            candidates = all_matches

        if not candidates:
            return None, None

        longest = max(candidates, key=lambda m: m.length)
        if longest.length < min_length:
            return None, None

        sorted_positions = sorted(longest.positions, key=lambda p: (p.row, p.col))
        pos = sorted_positions[len(sorted_positions) // 2]
        return GemType(-func_id), pos

    # -------------------------------------------------------------------------
    # Effect area calculation (replaces special_gems.py + mega_gems.py)
    # -------------------------------------------------------------------------

    def calculate_effect_positions(
        self,
        board: BoardState,
        position: Position,
        func_value: int,
        trigger_color: GemType | None = None,
        overrides: dict | None = None,
    ) -> set[Position]:
        """Positions cleared by a special gem (func 1-4).

        Replaces _calculate_special_effect_positions.
        Source position always included.

        Args:
            board: Current board state.
            position: Position of the special gem being activated.
            func_value: The GemFunction value (1-4).
            trigger_color: Color of the gem that triggered the special.
            overrides: Optional parameter overrides from card effects (Hook 2).
                Supports ``radius_bonus`` to extend radial blast range.
        """
        func_def = self._functions.get(str(func_value))
        if func_def is None:
            return {position}
        effect = func_def["effect"]
        if overrides and "radius_bonus" in overrides:
            # Copy effect dict and add bonus to radius.
            effect = dict(effect)
            effect["radius"] = effect.get("radius", 1) + overrides["radius_bonus"]
        return self._execute_select(board, effect, position, trigger_color)

    def calculate_mega_effect_positions(
        self,
        board: BoardState,
        position: Position,
        mega_value: int,
        trigger_color: GemType | None = None,
    ) -> set[Position]:
        """Positions cleared by a mega gem (value 11-44).

        Replaces _calculate_mega_gem_effect_positions.
        Source position always included.
        """
        combo_def = self._combos.get(str(mega_value))
        if combo_def is None:
            return {position}
        return self._execute_select(board, combo_def["effect"], position, trigger_color)

    # -------------------------------------------------------------------------
    # Select strategy dispatch
    # -------------------------------------------------------------------------

    def _execute_select(
        self,
        board: BoardState,
        effect: dict,
        position: Position,
        trigger_color: GemType | None,
    ) -> set[Position]:
        """Compute affected positions for an effect definition."""
        select = effect["select"]
        h, w = board.height, board.width
        affected: set[Position] = {position}

        if select == "row":
            self._select_rows(affected, position, h, w, effect)
        elif select == "column":
            self._select_columns(affected, position, h, w, effect)
        elif select == "radius":
            self._select_radius(affected, position, h, w, effect)
        elif select == "color_match":
            self._select_color_match(affected, board, trigger_color, effect)
        elif select == "cross":
            self._select_cross(affected, position, h, w)
        elif select == "entire_board":
            self._select_entire_board(affected, board)

        return affected

    @staticmethod
    def _select_rows(
        affected: set[Position],
        position: Position,
        h: int,
        w: int,
        effect: dict,
    ) -> None:
        """Full rows. count > 1 + centered = multiple rows centered on position."""
        count = effect.get("count", 1)
        if count > 1 and effect.get("centered", False):
            half = count // 2
            for dr in range(-half, half + 1):
                r = position.row + dr
                if 0 <= r < h:
                    for c in range(w):
                        affected.add(Position(r, c))
        else:
            for c in range(w):
                affected.add(Position(position.row, c))

    @staticmethod
    def _select_columns(
        affected: set[Position],
        position: Position,
        h: int,
        w: int,
        effect: dict,
    ) -> None:
        """Full columns. count > 1 + centered = multiple columns centered on position."""
        count = effect.get("count", 1)
        if count > 1 and effect.get("centered", False):
            half = count // 2
            for dc in range(-half, half + 1):
                c = position.col + dc
                if 0 <= c < w:
                    for r in range(h):
                        affected.add(Position(r, c))
        else:
            for r in range(h):
                affected.add(Position(r, position.col))

    @staticmethod
    def _select_radius(
        affected: set[Position],
        position: Position,
        h: int,
        w: int,
        effect: dict,
    ) -> None:
        """Square area with given radius."""
        radius = effect.get("radius", 1)
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                r, c = position.row + dr, position.col + dc
                if 0 <= r < h and 0 <= c < w:
                    affected.add(Position(r, c))

    def _select_color_match(
        self,
        affected: set[Position],
        board: BoardState,
        trigger_color: GemType | None,
        effect: dict,
    ) -> None:
        """All gems matching target color. Optionally spawn sub-effects at each."""
        target = self._resolve_color_target(
            board, trigger_color, effect.get("fallback")
        )
        if target is None:
            return

        target_val = int(target)
        grid_list = board.grid.tolist()
        h, w = board.height, board.width
        spawn_ref = effect.get("spawn_effect_at_each")

        if spawn_ref is not None:
            spawned_effect = self._functions[str(spawn_ref)]["effect"]
            for r in range(h):
                for c in range(w):
                    if grid_list[r][c] == target_val:
                        pos = Position(r, c)
                        affected.add(pos)
                        affected |= self._execute_select(
                            board,
                            spawned_effect,
                            pos,
                            trigger_color,
                        )
        else:
            for r in range(h):
                for c in range(w):
                    if grid_list[r][c] == target_val:
                        affected.add(Position(r, c))

    @staticmethod
    def _select_cross(
        affected: set[Position],
        position: Position,
        h: int,
        w: int,
    ) -> None:
        """Entire row + entire column (cross blast)."""
        for c in range(w):
            affected.add(Position(position.row, c))
        for r in range(h):
            affected.add(Position(r, position.col))

    @staticmethod
    def _select_entire_board(affected: set[Position], board: BoardState) -> None:
        """All non-empty cells."""
        grid_list = board.grid.tolist()
        h, w = board.height, board.width
        for r in range(h):
            for c in range(w):
                if grid_list[r][c] > 0:
                    affected.add(Position(r, c))

    # -------------------------------------------------------------------------
    # Color resolution (replaces _resolve_orb_target / _resolve_orb_target_fast)
    # -------------------------------------------------------------------------

    @staticmethod
    def _resolve_color_target(
        board: BoardState,
        trigger_color: GemType | None,
        fallback: str | None,
    ) -> GemType | None:
        """Resolve target color: trigger_color if valid, else most_common fallback."""
        if trigger_color is not None and int(trigger_color) > 0:
            return trigger_color

        if fallback == "most_common":
            grid_list = board.grid.tolist()
            h, w = board.height, board.width
            vals = [
                grid_list[r][c]
                for r in range(h)
                for c in range(w)
                if 1 <= grid_list[r][c] <= 6
            ]
            if vals:
                return GemType(Counter(vals).most_common(1)[0][0])

        return None

    # -------------------------------------------------------------------------
    # Config accessors
    # -------------------------------------------------------------------------

    def get_attraction_config(self) -> dict:
        """Mega gem attraction rules (distance, greedy, scan_directions, etc.)."""
        return self._attractions

    def get_chain_config(self) -> dict:
        """Chain reaction config (max_waves, directions)."""
        return self._chain

    def get_board_config(self) -> dict:
        """Board dimensions and rules (width, height, gem_types, etc.)."""
        return self._board

    def get_obstacle_config(self) -> dict:
        """Obstacle configuration (color_value, anchored, clearing_rules, etc.)."""
        return self._obstacles
