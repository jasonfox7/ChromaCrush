"""Cascade loop helpers (mixin for BoardService).

Queue-based clear pipeline: all clears + chain reactions processed in a single
FIFO drain loop, followed by gravity → attraction check → fill.
"""

from __future__ import annotations

from collections import deque

from src.core.types.board import BoardState, MatchResult
from src.core.types.game import (
    FUNCTION_TO_SPECIAL,
    SPECIAL_TO_FUNCTION,
    GemFunction,
    GemType,
    Move,
    Position,
    decode_mega_gem,
    encode_mega_gem,
    is_mega_gem,
)
from src.modules.board._constants import MAX_CASCADE_STEPS, OBSTACLE_COLOR
from src.modules.board.types import (
    CascadeContext,
    CascadeStep,
    SpecialActivation,
    SpecialAttraction,
)


def _obstacle_satisfied(obstacle_func: int, blast_func: int) -> bool:
    """Check whether a blast can damage an obstacle.

    Args:
        obstacle_func: The func_grid value of the obstacle (its required special).
            0 = basic glass (any special clears), 1-4 = requires matching special.
        blast_func: The function of the special that enqueued this position.
            0 = from a regular match (not a special blast).

    Returns:
        True if the obstacle should take damage.
    """
    if blast_func == 0:
        # Regular match seed — cannot damage obstacles.
        return False
    if obstacle_func == 0:
        # Basic glass — any special clears it.
        return True
    if is_mega_gem(blast_func):
        a, b = decode_mega_gem(blast_func)
        return int(a) == obstacle_func or int(b) == obstacle_func
    return blast_func == obstacle_func


class _CascadeMixin:
    """Cascade step execution: queue-based drain, swap activation, and cascade steps."""

    def _create_activation(
        self,
        board: BoardState,
        position: Position,
        raw_func: int,
        trigger_color: GemType | None,
        overrides: dict | None = None,
    ) -> tuple[SpecialActivation, set[Position]]:
        """Build a SpecialActivation record and compute the effect area.

        Handles both single-function specials and mega gems.
        """
        if is_mega_gem(raw_func):
            effect = self._calculate_mega_gem_effect_positions(
                board,
                position,
                raw_func,
                trigger_color,
            )
            dominant = max(decode_mega_gem(raw_func), key=lambda f: int(f))
            sp_type = FUNCTION_TO_SPECIAL[dominant]
            activation = SpecialActivation(
                position,
                sp_type,
                frozenset(effect),
                mega_func_value=raw_func,
            )
        else:
            func_val = GemFunction(raw_func)
            sp_type = FUNCTION_TO_SPECIAL[func_val]
            effect = self._calculate_special_effect_positions(
                board,
                position,
                sp_type,
                trigger_color,
                overrides=overrides,
            )
            activation = SpecialActivation(position, sp_type, frozenset(effect))
        return activation, effect

    # ------------------------------------------------------------------
    # Queue-based clear drain
    # ------------------------------------------------------------------

    def _drain_clear_queue(
        self,
        board: BoardState,
        initial_positions: set[Position],
        inert_megas: set[Position],
        trigger_color: GemType | None,
        modifiers: object | None = None,
        initial_blast_func: int = 0,
    ) -> tuple[set[Position], list[SpecialActivation], list[Position], list[tuple[Position, int, int]]]:
        """Process all clears and chain reactions in a single FIFO loop.

        1. Seed the queue with initial matched positions.
        2. For each position: read its func_grid value BEFORE clearing.
        3. If the position is an obstacle, check satisfaction rules.
        4. Clear the position on both grids (lock step).
        5. If it had a special/mega func and is not inert: compute blast,
           enqueue new blast positions.
        6. Check orthogonal neighbors of each cleared position for specials/megas
           not yet in the queue — if found and not inert, enqueue their blast.
        7. Repeat until queue empty.

        Queue entries are ``(position, blast_func)`` where blast_func is the
        function value of the special that enqueued this position (0 for
        initial match positions).

        Returns (all_cleared_positions, activations, obstacle_clearings, obstacle_transmutations).
        """
        h, w = board.height, board.width
        grid = board.grid
        func = board.func_grid  # type: ignore[union-attr]
        activations: list[SpecialActivation] = []
        all_cleared: set[Position] = set()
        obstacle_clearings: list[Position] = []
        obstacle_transmutations: list[tuple[Position, int, int]] = []
        processed_specials: set[Position] = set()
        # Track positions already enqueued to avoid duplicates.
        enqueued: set[Position] = set(initial_positions)

        # Queue carries (position, blast_func): blast_func=0 for match seeds,
        # or the special's func value for special/mega activations.
        queue: deque[tuple[Position, int]] = deque(
            (p, initial_blast_func)
            for p in sorted(initial_positions, key=lambda p: (p.row, p.col))
        )

        safety = 0
        max_iterations = MAX_CASCADE_STEPS * 64  # Board is 8x8=64 cells max.

        while queue and safety < max_iterations:
            safety += 1
            pos, blast_func = queue.popleft()

            if not (0 <= pos.row < h and 0 <= pos.col < w):
                continue

            # Read func value BEFORE clearing.
            raw_func = int(func[pos.row, pos.col])
            grid_val = int(grid[pos.row, pos.col])

            # --- Obstacle handling ---
            if grid_val == OBSTACLE_COLOR:
                obstacle_func = raw_func
                if _obstacle_satisfied(obstacle_func, blast_func):
                    if obstacle_func > 0:
                        # Transmute: decrement HP, don't clear, don't chain.
                        new_func = obstacle_func - 1
                        func[pos.row, pos.col] = new_func
                        obstacle_transmutations.append((pos, obstacle_func, new_func))
                    else:
                        # Basic glass (func=0): destroy.
                        grid[pos.row, pos.col] = 0
                        func[pos.row, pos.col] = 0
                        all_cleared.add(pos)
                        obstacle_clearings.append(pos)
                # Whether satisfied or not, obstacles absorb — skip normal flow.
                continue

            # Clear this position on both grids (lock step).
            grid[pos.row, pos.col] = 0
            func[pos.row, pos.col] = 0
            all_cleared.add(pos)

            # If this position had a special/mega, fire it (unless inert).
            if (
                raw_func != 0
                and pos not in processed_specials
                and pos not in inert_megas
            ):
                processed_specials.add(pos)

                # Hook 2: effect param overrides from card system.
                overrides = None
                if (
                    modifiers is not None
                    and not modifiers.is_empty
                    and not is_mega_gem(raw_func)
                ):
                    overrides, _mods = modifiers.get_effect_param_overrides(raw_func)

                activation, effect = self._create_activation(
                    board,
                    pos,
                    raw_func,
                    trigger_color,
                    overrides=overrides,
                )
                activations.append(activation)

                # Enqueue blast positions with this special's function.
                for ep in sorted(effect, key=lambda p: (p.row, p.col)):
                    if ep not in enqueued and 0 <= ep.row < h and 0 <= ep.col < w:
                        enqueued.add(ep)
                        queue.append((ep, raw_func))

            # Check orthogonal neighbors for specials/megas to chain-react.
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = pos.row + dr, pos.col + dc
                if not (0 <= nr < h and 0 <= nc < w):
                    continue
                npos = Position(nr, nc)
                if npos in processed_specials or npos in inert_megas:
                    continue
                # Skip obstacle neighbors — they don't chain-react.
                if int(grid[nr, nc]) == OBSTACLE_COLOR:
                    continue
                nfunc = int(func[nr, nc])
                if nfunc != 0:
                    processed_specials.add(npos)

                    # Hook 2: effect param overrides.
                    overrides = None
                    if (
                        modifiers is not None
                        and not modifiers.is_empty
                        and not is_mega_gem(nfunc)
                    ):
                        overrides, _mods = modifiers.get_effect_param_overrides(nfunc)

                    activation, effect = self._create_activation(
                        board,
                        npos,
                        nfunc,
                        trigger_color,
                        overrides=overrides,
                    )
                    activations.append(activation)

                    # Clear the neighbor special itself.
                    grid[nr, nc] = 0
                    func[nr, nc] = 0
                    all_cleared.add(npos)
                    enqueued.add(npos)

                    # Enqueue its blast positions with this neighbor's function.
                    for ep in sorted(effect, key=lambda p: (p.row, p.col)):
                        if ep not in enqueued and 0 <= ep.row < h and 0 <= ep.col < w:
                            enqueued.add(ep)
                            queue.append((ep, nfunc))

        return all_cleared, activations, obstacle_clearings, obstacle_transmutations

    # ------------------------------------------------------------------
    # Swap-to-activate
    # ------------------------------------------------------------------

    def _execute_swap_activation(
        self,
        board: BoardState,
        move: Move,
        from_func: int,
        to_func: int,
        seed: int,
        inert_megas: set[Position] | None = None,
        modifiers: object | None = None,
    ) -> CascadeStep:
        """Handle swap-to-activate: one swapped gem is a special, no normal match.

        When both swapped gems are specials, delegates to
        ``_execute_fusion_activation`` which produces a mega gem effect.
        Otherwise activates the single special via the drain queue,
        then applies gravity, attraction check, and fill.
        """
        if inert_megas is None:
            inert_megas = set()

        # Fusion: both gems are specials — produce mega gem blast.
        if from_func != 0 and to_func != 0:
            return self._execute_fusion_activation(
                board,
                move,
                from_func,
                to_func,
                seed,
                inert_megas,
                modifiers=modifiers,
            )

        sp_pos = move.from_pos if from_func != 0 else move.to_pos
        sp_raw = from_func if from_func != 0 else to_func
        other_pos = move.to_pos if sp_pos == move.from_pos else move.from_pos
        trigger_color = GemType(int(board.grid[other_pos.row, other_pos.col]))

        # Work on a single mutable copy.
        work = board.copy()

        # Compute activation effect and seed the drain queue.
        activation, effect = self._create_activation(
            work,
            sp_pos,
            sp_raw,
            trigger_color,
        )

        # Drain: clears + chain reactions.
        all_cleared, chain_activations, obs_clearings, obs_transmutations = (
            self._drain_clear_queue(
                work,
                effect,
                inert_megas,
                trigger_color,
                modifiers=modifiers,
                initial_blast_func=sp_raw,
            )
        )
        all_activations = [activation] + chain_activations

        # Gravity.
        drops = self.apply_gravity_inplace(work)

        # Rebuild inert mega positions after gravity.
        self._rebuild_inert_megas(work, inert_megas)

        # Post-gravity attraction check.
        post_grav_pairs = self._check_special_attractions(work)
        grav_attractions: list[SpecialAttraction] = []
        if post_grav_pairs:
            grav_attractions = self._process_attractions_inplace(work, post_grav_pairs)
            for att in grav_attractions:
                inert_megas.add(att.center_pos)

        # Fill.
        fill_seed = self._advance_seed(seed)
        spawns = self.fill_empty_inplace(work, fill_seed)

        return CascadeStep(
            step_number=0,
            matches=MatchResult(
                matches=(),
                total_gems_matched=0,
                creates_special_gem=False,
            ),
            gems_dropped=drops,
            gems_spawned=spawns,
            board_after_fill=work,
            special_activations=all_activations,
            special_attractions=grav_attractions,
            obstacle_clearings=obs_clearings,
            obstacle_transmutations=obs_transmutations,
        )

    def _execute_fusion_activation(
        self,
        board: BoardState,
        move: Move,
        from_func: int,
        to_func: int,
        seed: int,
        inert_megas: set[Position] | None = None,
        modifiers: object | None = None,
    ) -> CascadeStep:
        """Handle fusion: both swapped gems are specials.

        Encodes the two functions as a mega gem value and computes the
        combined blast effect centered on ``move.from_pos``.
        """
        if inert_megas is None:
            inert_megas = set()

        mega_value = encode_mega_gem(GemFunction(from_func), GemFunction(to_func))
        trigger_color = GemType(int(board.grid[move.from_pos.row, move.from_pos.col]))

        # Work on a single mutable copy.
        work = board.copy()

        effect = self._calculate_mega_gem_effect_positions(
            work,
            move.from_pos,
            mega_value,
            trigger_color,
        )
        dominant = max(decode_mega_gem(mega_value), key=lambda f: int(f))
        sp_type = FUNCTION_TO_SPECIAL[dominant]
        activation = SpecialActivation(
            move.from_pos,
            sp_type,
            frozenset(effect),
            mega_func_value=mega_value,
        )

        # Drain: clears + chain reactions.
        all_cleared, chain_activations, obs_clearings, obs_transmutations = (
            self._drain_clear_queue(
                work,
                effect,
                inert_megas,
                trigger_color,
                modifiers=modifiers,
                initial_blast_func=mega_value,
            )
        )
        all_activations = [activation] + chain_activations

        # Gravity.
        drops = self.apply_gravity_inplace(work)

        # Rebuild inert mega positions after gravity.
        self._rebuild_inert_megas(work, inert_megas)

        # Post-gravity attraction check.
        post_grav_pairs = self._check_special_attractions(work)
        grav_attractions: list[SpecialAttraction] = []
        if post_grav_pairs:
            grav_attractions = self._process_attractions_inplace(work, post_grav_pairs)
            for att in grav_attractions:
                inert_megas.add(att.center_pos)

        # Fill.
        fill_seed = self._advance_seed(seed)
        spawns = self.fill_empty_inplace(work, fill_seed)

        return CascadeStep(
            step_number=0,
            matches=MatchResult(
                matches=(),
                total_gems_matched=0,
                creates_special_gem=False,
            ),
            gems_dropped=drops,
            gems_spawned=spawns,
            board_after_fill=work,
            special_activations=all_activations,
            special_attractions=grav_attractions,
            obstacle_clearings=obs_clearings,
            obstacle_transmutations=obs_transmutations,
        )

    # ------------------------------------------------------------------
    # Attraction-only step (no matches, just func_grid mutation)
    # ------------------------------------------------------------------

    def _try_attraction_only_step_inplace(
        self,
        board: BoardState,
        chain: int,
        inert_megas: set[Position] | None = None,
    ) -> CascadeStep | None:
        """Check for special gem attractions when no matches exist.

        If attraction pairs are found, process them in place into a cascade
        step with no gravity or fill (only func_grid mutation).

        Mutates *board* directly. Returns a CascadeStep or None.
        """
        if inert_megas is None:
            inert_megas = set()

        pairs = self._check_special_attractions(board)
        if not pairs:
            return None
        attractions = self._process_attractions_inplace(board, pairs)
        for att in attractions:
            inert_megas.add(att.center_pos)
        return CascadeStep(
            step_number=chain,
            matches=MatchResult(
                matches=(),
                total_gems_matched=0,
                creates_special_gem=False,
            ),
            board_after_fill=board,
            special_attractions=attractions,
        )

    # ------------------------------------------------------------------
    # Main cascade step
    # ------------------------------------------------------------------

    def _run_cascade_step_inplace(
        self,
        board: BoardState,
        matches: MatchResult,
        chain: int,
        cascade_seed: int,
        modifiers: object | None = None,
        inert_megas: set[Position] | None = None,
    ) -> tuple[CascadeStep, int, list[tuple[Position, GemType]], int, list]:
        """Process one cascade step where matches were found.

        Queue-based pipeline:
          1. Drain clear queue (matches + chain reactions)
          2. Place special gem from match (after drain — survives this step)
          3. Gravity
          4. Rebuild inert mega positions
          5. Attraction check (single point, post-gravity)
          6. Fill
          7. Card injection (post-fill)

        Mutates *board* directly. Returns:
            ``(cascade_step, gems_cleared, new_specials, next_seed, applied_modifiers)``
        """
        if inert_megas is None:
            inert_megas = set()

        ctx = CascadeContext(
            board=board,
            matches=matches,
            chain=chain,
            seed=cascade_seed,
            modifiers=modifiers,
            inert_megas=inert_megas,
        )

        # Record special gem creation from matches.
        self._phase_record_special(ctx)

        # Collect all matched positions as the initial drain set.
        initial_positions: set[Position] = set()
        for mg in matches.matches:
            initial_positions.update(mg.positions)
        trigger_color = matches.matches[0].gem_type if matches.matches else None

        # 1. Drain clear queue: matches + chain reactions.
        all_cleared, activations, obs_clearings, obs_transmutations = (
            self._drain_clear_queue(
                board,
                initial_positions,
                inert_megas,
                trigger_color,
                modifiers=modifiers,
            )
        )
        ctx.all_cleared = all_cleared
        ctx.all_activations = activations
        ctx.obstacle_clearings = obs_clearings
        ctx.obstacle_transmutations = obs_transmutations

        # 2. Place special gem from match (after drain — survives this step).
        self._phase_place_new_special(ctx)

        # 3. Gravity.
        ctx.gems_dropped = self.apply_gravity_inplace(board)

        # 4. Rebuild inert mega positions after gravity.
        self._rebuild_inert_megas(board, inert_megas)

        # 5. Attraction check (single point, post-gravity).
        pairs = self._check_special_attractions(board)
        if pairs:
            attractions = self._process_attractions_inplace(board, pairs)
            ctx.all_attractions.extend(attractions)
            for att in attractions:
                inert_megas.add(att.center_pos)

        # 6. Fill.
        self._phase_fill(ctx)

        # 7. Card injection (post-fill).
        self._phase_post_fill_injection(ctx)

        self._logger.trace(
            "board.cascade_step",
            step=chain,
            matches_found=len(matches.matches),
            gems_cleared=ctx.total_cleared(),
            special_activations=len(ctx.all_activations),
        )

        return (
            ctx.build_step(),
            ctx.total_cleared(),
            ctx.new_specials,
            ctx.next_seed,
            ctx.applied_modifiers,
        )

    # ------------------------------------------------------------------
    # Cascade step sub-phases (retained)
    # ------------------------------------------------------------------

    @staticmethod
    def _phase_record_special(ctx: CascadeContext) -> None:
        """Record special gem creation from matches + apply card override (Hook 1)."""
        if (
            ctx.matches.creates_special_gem
            and ctx.matches.special_gem_position is not None
        ):
            ctx.new_specials.append(
                (ctx.matches.special_gem_position, ctx.matches.special_gem_type)  # type: ignore[arg-type]
            )
            # Hook 1: Card override of special type.
            if ctx.modifiers is not None and not ctx.modifiers.is_empty:
                original_func = int(
                    SPECIAL_TO_FUNCTION[ctx.matches.special_gem_type]  # type: ignore[index]
                )
                overridden_func, mods = ctx.modifiers.apply_special_override(
                    original_func
                )
                if overridden_func != original_func:
                    ctx.special_override_func = overridden_func
                    ctx.applied_modifiers.extend(mods)

    def _phase_place_new_special(self, ctx: CascadeContext) -> None:
        """Place newly-created special gem on the board (after drain)."""
        if ctx.special_override_func is not None:
            # Card override: place overridden function instead of the normal one.
            pos = ctx.matches.special_gem_position
            if pos is not None:
                board = ctx.board
                match_color = (
                    int(ctx.matches.matches[0].gem_type) if ctx.matches.matches else 1
                )
                color_at_pos = int(board.grid[pos.row, pos.col])
                color = color_at_pos if color_at_pos > 0 else match_color
                board.grid[pos.row, pos.col] = color
                board.func_grid[pos.row, pos.col] = ctx.special_override_func  # type: ignore[index]
            return
        # Original behavior.
        self._place_special_gem_inplace(ctx.board, ctx.matches)

    def _phase_fill(self, ctx: CascadeContext) -> None:
        """Fill empty cells with new random gems (Hook 4 for spawn weights)."""
        ctx.next_seed = self._advance_seed(ctx.seed)
        spawn_weights = None
        if ctx.modifiers is not None and not ctx.modifiers.is_empty:
            spawn_weights = ctx.modifiers.get_spawn_weights(self._gem_types)
        ctx.gems_spawned = self.fill_empty_inplace(
            ctx.board,
            ctx.next_seed,
            spawn_weights=spawn_weights,
        )

    def _phase_post_fill_injection(self, ctx: CascadeContext) -> None:
        """Card injection -- place special gems after fill (Hook 3)."""
        if ctx.modifiers is None or ctx.modifiers.is_empty:
            return
        injection, mods = ctx.modifiers.get_cascade_injection(ctx.chain, ctx.next_seed)
        if injection is None:
            return
        ctx.applied_modifiers.extend(mods)

        # Find neutral gem positions (func_grid == 0, grid > 0).
        import numpy as np

        grid = ctx.board.grid
        func = ctx.board.func_grid
        neutral_mask = (grid >= 1) & (grid <= 6) & (func == 0)
        rows, cols = np.where(neutral_mask)
        if len(rows) == 0:
            return

        # Pick random position using seeded RNG.
        # XOR nanosecond timestamp for per-invocation entropy — the game seed
        # alone doesn't vary enough within a cascade (score hasn't changed yet).
        import time
        injection_seed = ctx.next_seed ^ time.time_ns()
        rng = np.random.default_rng(injection_seed)
        idx = rng.integers(0, len(rows))
        pos = Position(int(rows[idx]), int(cols[idx]))

        # Place the special function.
        func[pos.row, pos.col] = injection.function

        # Record the injection for frontend animation.
        ctx.injected_special = (pos, injection.function)

        if injection.fire_immediately:
            # Get overrides from card system (Hook 2) if applicable.
            overrides = None
            if not ctx.modifiers.is_empty:
                overrides, _ep_mods = ctx.modifiers.get_effect_param_overrides(
                    injection.function,
                )
            # Fire the special and collect cleared positions via drain queue
            # so obstacles are handled correctly.
            trigger_color = GemType(int(grid[pos.row, pos.col]))
            activation, effect = self._create_activation(
                ctx.board,
                pos,
                injection.function,
                trigger_color,
                overrides=overrides,
            )
            # Clear the injection position's function BEFORE draining so the
            # drain queue doesn't re-fire it as a chain reaction (double-fire bug).
            func[pos.row, pos.col] = 0
            inj_cleared, inj_chain, inj_obs, inj_trans = self._drain_clear_queue(
                ctx.board,
                effect,
                ctx.inert_megas,
                trigger_color,
                modifiers=ctx.modifiers,
                initial_blast_func=injection.function,
            )
            ctx.all_activations.extend(inj_chain)
            ctx.obstacle_clearings.extend(inj_obs)
            ctx.obstacle_transmutations.extend(inj_trans)
            ctx.injected_activation = activation
            # Gravity + fill to prevent gaps — separate fields for animation.
            ctx.injected_drops = self.apply_gravity_inplace(ctx.board)
            ctx.next_seed = self._advance_seed(ctx.next_seed)
            ctx.injected_spawns = self.fill_empty_inplace(ctx.board, ctx.next_seed)

    # ------------------------------------------------------------------
    # Inert mega tracking
    # ------------------------------------------------------------------

    @staticmethod
    def _rebuild_inert_megas(board: BoardState, inert_megas: set[Position]) -> None:
        """Re-scan func_grid after gravity to update inert mega positions.

        Mega gem values (11-44) are distinctive. After gravity moves gems
        to new rows, we rebuild the inert set from current positions.
        """
        if not inert_megas:
            return
        # Collect all current mega positions on the board.
        current_megas: set[Position] = set()
        func_list = board.func_grid.tolist()  # type: ignore[union-attr]
        h, w = board.height, board.width
        for r in range(h):
            for c in range(w):
                if is_mega_gem(func_list[r][c]):
                    current_megas.add(Position(r, c))
        # Keep only positions that still exist as megas.
        inert_megas.clear()
        inert_megas.update(current_megas)
