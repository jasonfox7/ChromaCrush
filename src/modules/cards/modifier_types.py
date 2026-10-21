"""Card modifier type definitions for the card effect system.

Defines the pure data structures used by CardModifierEngine to represent
card effects, applied modifiers, injection actions, and score modifiers.
These are frozen dataclasses with no I/O or side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CardModifierDef:
    """A single equipped card's effect-relevant fields.

    Extracted from CardDefinition at move-processing time so the engine
    operates on a minimal, immutable snapshot.

    Attributes:
        card_id: Card definition ID from the catalog.
        name: Human-readable card name.
        trigger: When the card's effect fires.
        effect: What the card's effect does.
        effect_params: Parameters specific to this effect.
        trigger_condition: Optional conditions that must be met for the trigger.
        tags: Card tags for set bonuses and filtering.
    """

    card_id: int
    name: str
    trigger: str  # "passive", "on_special_created", "on_cascade_step",
    # "on_match_detected", "on_move_start", "on_move_complete",
    # "on_raid", "periodic"
    effect: str  # "spawn_bias", "special_type_bias", "score_multiplier",
    # "override_special", "override_special_mega",
    # "effect_param_override", "inject_special",
    # "inject_and_fire", "special_creation_chance",
    # "lucky_rabbit", "grant_energy",
    # "opponent_score_reduction", "board_shuffle",
    # "raid_block", "raid_protection"
    effect_params: dict
    trigger_condition: dict | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppliedModifier:
    """Record of a card modifier that proc'd during move processing.

    Collected by the engine and returned alongside results so the caller
    can include them in the move response for frontend display.

    Attributes:
        card_id: Card definition ID that produced this modifier.
        card_name: Human-readable card name for display.
        hook: Which engine hook produced this modifier.
        description: Human-readable description of what happened.
        details: Additional hook-specific details.
    """

    card_id: int
    card_name: str
    hook: str  # "special_override", "effect_param", "spawn_bias",
    # "score_modifier", "cascade_injection",
    # "special_creation_chance", "win_condition",
    # "energy_grant"
    description: str
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class InjectionAction:
    """Describes a special gem to inject after fill.

    Used by the cascade injection hook to insert special gems
    into the board mid-cascade.

    Attributes:
        function: GemFunction value (1-4), mega value (11, 22), or 0 for random.
        is_mega: Whether this is a mega gem injection.
        fire_immediately: Whether the injected special should fire on the same step.
    """

    function: int  # GemFunction value (1-4) or mega value (11, 22), or 0 for random
    is_mega: bool = False
    fire_immediately: bool = True


@dataclass(frozen=True)
class ScoreModifiers:
    """Aggregated scoring modifier params from all equipped cards.

    The scoring service reads these to adjust point calculations.
    All multipliers default to neutral values (1.0 or 0).

    Attributes:
        cascade_multiplier: Multiplier for cascade chain scoring.
        special_multiplier: Multiplier for special gem activation scoring.
        big_match_multiplier: Multiplier for matches of 5+ gems.
        min_match_size: Minimum match size for big match bonus (default 4).
        all_multiplier: Global multiplier applied to all scoring.
        first_step_multiplier: Multiplier for chain_step == 0 (Opening Gambit).
        cascade_depth_bonus: Per-chain-step cumulative bonus.
        chain_reaction_multiplier: Multiplier for chain reaction scoring.
        opponent_score_reduction: Fraction to reduce opponent's score (0.0-1.0).
    """

    cascade_multiplier: float = 1.0
    special_multiplier: float = 1.0
    big_match_multiplier: float = 1.0
    min_match_size: int = 4
    all_multiplier: float = 1.0
    first_step_multiplier: float = 1.0
    cascade_depth_bonus: float = 0.0
    chain_reaction_multiplier: float = 1.0
    opponent_score_reduction: float = 0.0
