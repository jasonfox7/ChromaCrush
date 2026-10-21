"""Board module types for cascade tracking and move processing results.

Defines the internal data structures used by BoardService to track
gem movements, spawn events, cascade steps, and full move outcomes.
These types are part of the board module's public interface for
consumption by dependent modules (scoring, match, board_gen).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.types.board import BoardState, MatchResult
from src.core.types.game import GemFunction, GemType, Move, Position


@dataclass(frozen=True)
class GemDrop:
    """Record of a gem falling due to gravity.

    Attributes:
        gem_type: The type of gem that fell.
        from_pos: Original position before gravity.
        to_pos: Final position after gravity.
        distance: Number of cells the gem dropped.
    """

    gem_type: GemType
    from_pos: Position
    to_pos: Position
    distance: int


@dataclass(frozen=True)
class GemSpawn:
    """Record of a new gem spawned to fill an empty cell.

    Attributes:
        gem_type: The type of gem spawned.
        position: Where the gem was placed on the board.
        column: Which column the gem entered from (for animation).
    """

    gem_type: GemType
    position: Position
    column: int


@dataclass(frozen=True)
class SpecialActivation:
    """Record of a special gem being triggered during a cascade step.

    Attributes:
        position: Where the special gem was on the board.
        gem_type: The type of special gem activated.
        affected_positions: All positions cleared by the activation effect.
        mega_func_value: If this activation is from a mega gem, the encoded value (11-44).
    """

    position: Position
    gem_type: GemType
    affected_positions: frozenset[Position]
    mega_func_value: int | None = None


@dataclass(frozen=True)
class SpecialAttraction:
    """Record of two special gems attracting toward a center gem.

    The center gem becomes a mega gem inheriting both functions.
    The two source specials lose their function but keep their color.
    No gems are removed — only func_grid mutates.

    Attributes:
        pos_a: First special gem position (loses function).
        pos_b: Second special gem position (loses function).
        center_pos: Regular gem between them (becomes mega).
        func_a: Function that pos_a had.
        func_b: Function that pos_b had.
        mega_func: Encoded mega gem value (11-44).
    """

    pos_a: Position
    pos_b: Position
    center_pos: Position
    func_a: GemFunction
    func_b: GemFunction
    mega_func: int


@dataclass
class CascadeContext:
    """Mutable context accumulating state across phases of a single cascade step.

    Replaces the pile of locals in _run_cascade_step_inplace. Each phase
    method reads/writes this context instead of passing values through locals.
    """

    board: BoardState
    matches: MatchResult
    chain: int
    seed: int

    # Accumulated during cascade step.
    all_activations: list[SpecialActivation] = field(default_factory=list)
    all_attractions: list[SpecialAttraction] = field(default_factory=list)
    new_specials: list[tuple[Position, GemType]] = field(default_factory=list)
    all_cleared: set[Position] = field(default_factory=set)
    gems_dropped: list[GemDrop] = field(default_factory=list)
    gems_spawned: list[GemSpawn] = field(default_factory=list)
    next_seed: int = 0

    # Move-wide inert set: mega gems formed during this move don't activate.
    inert_megas: set[Position] = field(default_factory=set)

    # Obstacle tracking (Campaign mode).
    obstacle_clearings: list[Position] = field(default_factory=list)
    obstacle_transmutations: list[tuple[Position, int, int]] = field(
        default_factory=list
    )  # (pos, from_func, to_func)

    # Card injection tracking (Hook 3).
    injected_special: tuple[Position, int] | None = None  # (position, function_value)
    injected_activation: SpecialActivation | None = None  # fire_immediately activation
    injected_drops: list[GemDrop] = field(default_factory=list)
    injected_spawns: list[GemSpawn] = field(default_factory=list)

    # Card modifier system fields (Phase A).
    modifiers: object | None = (
        None  # CardModifierEngine (typed as object to avoid import)
    )
    applied_modifiers: list = field(default_factory=list)  # list[AppliedModifier]
    special_override_func: int | None = None

    def total_cleared(self) -> int:
        """Count total distinct positions cleared in this step."""
        activation_cleared: set[Position] = set()
        for act in self.all_activations:
            activation_cleared.update(act.affected_positions)
        return len(self.all_cleared | activation_cleared)

    def build_step(self) -> CascadeStep:
        """Build the immutable CascadeStep from accumulated state."""
        return CascadeStep(
            step_number=self.chain,
            matches=self.matches,
            gems_dropped=self.gems_dropped,
            gems_spawned=self.gems_spawned,
            board_after_fill=self.board,
            special_activations=self.all_activations,
            special_attractions=self.all_attractions,
            injected_special=self.injected_special,
            injected_activation=self.injected_activation,
            injected_drops=self.injected_drops,
            injected_spawns=self.injected_spawns,
            obstacle_clearings=self.obstacle_clearings,
            obstacle_transmutations=self.obstacle_transmutations,
        )


@dataclass
class CascadeStep:
    """One step in the cascade loop after a move.

    Each cascade step represents: detect matches -> clear -> gravity -> fill.
    Not frozen because it contains mutable list fields.

    Attributes:
        step_number: 1-based index of this cascade step.
        matches: The matches detected at the start of this step.
        gems_dropped: List of gem drop events from gravity.
        gems_spawned: List of newly spawned gems.
        board_after_fill: Board state after filling empty cells.
    """

    step_number: int
    matches: MatchResult
    gems_dropped: list[GemDrop] = field(default_factory=list)
    gems_spawned: list[GemSpawn] = field(default_factory=list)
    board_after_fill: BoardState | None = None
    special_activations: list[SpecialActivation] = field(default_factory=list)
    special_attractions: list[SpecialAttraction] = field(default_factory=list)
    injected_special: tuple[Position, int] | None = None
    injected_activation: SpecialActivation | None = None
    injected_drops: list[GemDrop] = field(default_factory=list)
    injected_spawns: list[GemSpawn] = field(default_factory=list)
    obstacle_clearings: list[Position] = field(default_factory=list)
    obstacle_transmutations: list[tuple[Position, int, int]] = field(
        default_factory=list
    )


@dataclass
class MoveProcessingResult:
    """Complete result of processing a player's move.

    Includes the full cascade history, special gem creation records,
    and aggregate statistics. Not frozen because it contains mutable
    list fields.

    Attributes:
        initial_board: Board state before the move.
        final_board: Board state after all cascades complete.
        move: The move that was processed.
        was_valid_match: False if the swap created no matches (swap reverted).
        cascades: Ordered list of cascade steps.
        total_matches: Total number of distinct match events across cascades.
        total_gems_cleared: Total gems cleared across all cascades.
        chain_count: Number of cascade steps (for chain multiplier).
        special_gems_created: List of (position, gem_type) for created specials.
    """

    initial_board: BoardState
    final_board: BoardState
    move: Move
    was_valid_match: bool
    cascades: list[CascadeStep] = field(default_factory=list)
    total_matches: int = 0
    total_gems_cleared: int = 0
    chain_count: int = 0
    special_gems_created: list[tuple[Position, GemType]] = field(default_factory=list)

    # Obstacle tracking (Campaign mode).
    obstacle_clearings: list[Position] = field(default_factory=list)
    obstacle_transmutations: list[tuple[Position, int, int]] = field(
        default_factory=list
    )

    # Card modifier system fields (Phase A).
    applied_modifiers: list = field(default_factory=list)  # list[AppliedModifier]
