"""Card modifier engine — pure logic, no I/O.

Constructed once per move submission with the player's equipped card
definitions. Each hook method returns a "no change" default until the
corresponding card effect is implemented in later phases.

The engine is intentionally stateless beyond the card definitions
passed at construction time. It never touches the database, network,
or filesystem.
"""

from __future__ import annotations

from dataclasses import replace

from src.modules.cards.modifier_types import (
    AppliedModifier,
    CardModifierDef,
    InjectionAction,
    ScoreModifiers,
)


class CardModifierEngine:
    """Pure card modifier engine. No I/O. Constructed once per move submission.

    All hook methods return neutral/"no change" defaults. Implementations
    will be filled in during Phase B (per-hook implementation).

    Args:
        card_defs: List of equipped card modifier definitions for this move.
    """

    def __init__(self, card_defs: list[CardModifierDef]) -> None:
        self._cards = card_defs
        self._by_trigger: dict[str, list[CardModifierDef]] = {}
        self._by_effect: dict[str, list[CardModifierDef]] = {}
        for card in card_defs:
            self._by_trigger.setdefault(card.trigger, []).append(card)
            self._by_effect.setdefault(card.effect, []).append(card)

    @property
    def is_empty(self) -> bool:
        """Return True if no card modifiers are loaded."""
        return len(self._cards) == 0

    def apply_special_override(
        self,
        original_func: int,
    ) -> tuple[int, list[AppliedModifier]]:
        """Hook 1: Override special creation type.

        Called when a special gem is about to be created. Cards with
        ``effect="override_special"`` can change the function value,
        and cards with ``effect="override_special_mega"`` can upgrade
        to a mega gem value.

        Args:
            original_func: The GemFunction value that would be created.

        Returns:
            Tuple of (possibly-overridden func value, list of applied modifiers).
        """
        applied: list[AppliedModifier] = []
        func = original_func

        for card in self._by_effect.get("override_special", []):
            target = card.effect_params.get("target_function")
            if target is not None:
                func = int(target)
                applied.append(
                    AppliedModifier(
                        card_id=card.card_id,
                        card_name=card.name,
                        hook="special_override",
                        description=f"{card.name}: override to func {func}",
                    )
                )

        for card in self._by_effect.get("override_special_mega", []):
            target = card.effect_params.get("mega_func")
            if target is not None:
                func = int(target)
                applied.append(
                    AppliedModifier(
                        card_id=card.card_id,
                        card_name=card.name,
                        hook="special_override",
                        description=f"{card.name}: override to mega {func}",
                    )
                )

        return func, applied

    def get_effect_param_overrides(
        self,
        func_value: int,
    ) -> tuple[dict, list[AppliedModifier]]:
        """Hook 2: Get parameter overrides for effect calculation.

        Called before executing a special gem's effect. Cards with
        ``effect="effect_param_override"`` can alter radius, range, etc.

        Args:
            func_value: The GemFunction value being activated.

        Returns:
            Tuple of (override dict, list of applied modifiers).
        """
        override_cards = self._by_effect.get("effect_param_override", [])
        if not override_cards:
            return {}, []
        applied: list[AppliedModifier] = []
        overrides: dict = {}
        for card in override_cards:
            # Card data uses "function" or "target_function" for the filter.
            target_func = card.effect_params.get(
                "target_function"
            ) or card.effect_params.get("function")
            # Apply if targeting this func or targeting all (None)
            if target_func is not None and int(target_func) != func_value:
                continue
            radius_bonus = card.effect_params.get("radius_bonus")
            if radius_bonus is not None:
                overrides["radius_bonus"] = overrides.get("radius_bonus", 0) + int(
                    radius_bonus
                )
            applied.append(
                AppliedModifier(
                    card_id=card.card_id,
                    card_name=card.name,
                    hook="effect_param",
                    description=(
                        f"{card.name}: radius +{radius_bonus}"
                        if radius_bonus
                        else f"{card.name}: effect override"
                    ),
                )
            )
        return overrides, applied

    def get_cascade_injection(
        self,
        step_number: int,
        seed: int,
    ) -> tuple[InjectionAction | None, list[AppliedModifier]]:
        """Hook 3: Check if a special should be injected after fill.

        Called after each cascade step's fill phase. Cards with
        ``effect="inject_special"`` or ``effect="inject_and_fire"``
        can place specials on the board.

        Args:
            step_number: Current cascade step number (0-based).
            seed: RNG seed for deterministic randomness.

        Returns:
            Tuple of (InjectionAction or None, list of applied modifiers).
        """
        inject_cards = self._by_effect.get("inject_special", []) + self._by_effect.get(
            "inject_and_fire", []
        )
        if not inject_cards:
            return None, []
        for card in inject_cards:
            # Check trigger condition — cards use "every_n" in either
            # trigger_condition or effect_params.
            interval = 1
            if card.trigger_condition:
                interval = card.trigger_condition.get("every_n", 1)
            elif "every_n" in card.effect_params:
                interval = int(card.effect_params["every_n"])
            if interval > 1 and step_number % interval != 0:
                continue

            # Determine function value — "random" picks 1-4 via seed,
            # "mega_func" sets a mega gem value directly.
            raw_func = card.effect_params.get("function")
            mega_func = card.effect_params.get("mega_func")
            is_mega = card.effect_params.get("is_mega", False)
            fire = card.effect == "inject_and_fire"

            if mega_func is not None:
                func = int(mega_func)
                is_mega = True
            elif raw_func is None or raw_func == "random":
                # Pick random function 1-4 using deterministic LCG.
                roll = (seed * 1103515245 + 12345) & 0x7FFFFFFF
                func = (roll % 4) + 1
            else:
                func = int(raw_func)

            return InjectionAction(
                function=func,
                is_mega=bool(is_mega),
                fire_immediately=fire,
            ), [
                AppliedModifier(
                    card_id=card.card_id,
                    card_name=card.name,
                    hook="cascade_injection",
                    description=f"{card.name}: injected func {func}{' (mega)' if is_mega else ''}",
                )
            ]
        return None, []

    def get_spawn_weights(self, gem_types: int) -> list[float] | None:
        """Hook 4: Get weighted spawn probabilities.

        Called during board fill to bias which gem colors appear.
        Cards with ``effect="spawn_bias"`` provide color weights.

        Args:
            gem_types: Number of gem color types on the board (typically 6).

        Returns:
            List of weights (length = gem_types) or None for uniform distribution.
        """
        bias_cards = self._by_effect.get("spawn_bias", [])
        if not bias_cards:
            return None
        # Start with uniform weights.
        weights = [1.0] * gem_types
        for card in bias_cards:
            color = card.effect_params.get("gem_color", 1)
            boost = card.effect_params.get("weight_bonus", 0.1)
            if 1 <= color <= gem_types:
                weights[color - 1] += boost
        # Normalize to sum to 1.0.
        total = sum(weights)
        return [w / total for w in weights]

    def get_special_type_bias(
        self,
    ) -> tuple[dict[int, float], list[AppliedModifier]]:
        """Hook 5a: Get bias for special type selection.

        Called when deciding which special type to create from a match.
        Cards with ``effect="special_type_bias"`` can shift probabilities.

        Returns:
            Tuple of ({func_id: bias_weight}, list of applied modifiers).
        """
        bias_cards = self._by_effect.get("special_type_bias", [])
        if not bias_cards:
            return {}, []
        applied: list[AppliedModifier] = []
        bias: dict[int, float] = {}
        for card in bias_cards:
            func_id = card.effect_params.get("function")
            weight = float(card.effect_params.get("bias_bonus", 0.1))
            if func_id is not None:
                # Accumulate bias multiplicatively.
                bias[func_id] = bias.get(func_id, 1.0) + weight
                applied.append(
                    AppliedModifier(
                        card_id=card.card_id,
                        card_name=card.name,
                        hook="special_type_bias",
                        description=f"{card.name}: func {func_id} +{weight}",
                    )
                )
        return bias, applied

    def get_three_match_special_chance(
        self,
        seed: int,
    ) -> tuple[int | None, list[AppliedModifier]]:
        """Hook 5b: Check if 3-match creates special (Fortune's Favor).

        Called when a 3-gem match is detected. Cards with
        ``effect="special_creation_chance"`` can grant a chance for
        the match to produce a special gem anyway.

        Args:
            seed: RNG seed for deterministic randomness.

        Returns:
            Tuple of (GemFunction value or None, list of applied modifiers).
        """
        chance_cards = self._by_effect.get("special_creation_chance", [])
        if not chance_cards:
            return None, []
        for card in chance_cards:
            chance = float(card.effect_params.get("three_match_special_chance", 0.1))
            # Deterministic roll using LCG on the seed.
            roll = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            if (roll % 1000) < int(chance * 1000):
                # Default to LINE_BLAST_H (func 1) for 3-match special.
                func = 1
                return func, [
                    AppliedModifier(
                        card_id=card.card_id,
                        card_name=card.name,
                        hook="special_creation_chance",
                        description=f"{card.name}: 3-match created special func {func}",
                    )
                ]
        return None, []

    def get_score_modifiers(
        self,
    ) -> tuple[ScoreModifiers, list[AppliedModifier]]:
        """Hook 6: Collect all scoring modifier parameters.

        Called at move-scoring time to aggregate all equipped cards'
        scoring effects into a single ScoreModifiers instance.

        Returns:
            Tuple of (ScoreModifiers with defaults, list of applied modifiers).
        """
        applied: list[AppliedModifier] = []
        mods = ScoreModifiers()

        # score_multiplier cards — each param key maps to a ScoreModifiers field.
        _MULT_FIELDS = {
            "cascade_multiplier",
            "special_multiplier",
            "big_match_multiplier",
            "all_multiplier",
            "first_step_multiplier",
            "chain_reaction_multiplier",
        }
        for card in self._by_effect.get("score_multiplier", []):
            params = card.effect_params
            parts: list[str] = []
            replacements: dict[str, object] = {}
            for key in _MULT_FIELDS:
                if key in params:
                    val = float(params[key])
                    old = getattr(mods, key)
                    replacements[key] = old * val
                    parts.append(f"{key}={val}")
            if "cascade_depth_bonus" in params:
                val = float(params["cascade_depth_bonus"])
                replacements["cascade_depth_bonus"] = mods.cascade_depth_bonus + val
                parts.append(f"cascade_depth_bonus=+{val}")
            if "min_match_size" in params:
                replacements["min_match_size"] = int(params["min_match_size"])
            if replacements:
                mods = replace(mods, **replacements)
                applied.append(
                    AppliedModifier(
                        card_id=card.card_id,
                        card_name=card.name,
                        hook="score_modifier",
                        description=f"{card.name}: {', '.join(parts)}",
                    )
                )

        # opponent_score_reduction cards — additive.
        for card in self._by_effect.get("opponent_score_reduction", []):
            reduction = float(card.effect_params.get("reduction", 0.05))
            mods = replace(
                mods, opponent_score_reduction=mods.opponent_score_reduction + reduction
            )
            applied.append(
                AppliedModifier(
                    card_id=card.card_id,
                    card_name=card.name,
                    hook="score_modifier",
                    description=f"{card.name}: opponent -{reduction * 100:.0f}%",
                )
            )

        # Non-score_multiplier cards that carry scoring side-effects
        # (e.g. Lucky Rabbit zeros all scoring via all_multiplier: 0.0).
        for card in self._by_effect.get("lucky_rabbit", []):
            params = card.effect_params
            replacements: dict[str, object] = {}
            parts: list[str] = []
            for key in _MULT_FIELDS:
                if key in params:
                    val = float(params[key])
                    old = getattr(mods, key)
                    replacements[key] = old * val
                    parts.append(f"{key}={val}")
            if replacements:
                mods = replace(mods, **replacements)
                applied.append(
                    AppliedModifier(
                        card_id=card.card_id,
                        card_name=card.name,
                        hook="score_modifier",
                        description=f"{card.name}: {', '.join(parts)}",
                    )
                )

        return mods, applied

    def check_win_condition(
        self,
        cascades: list,
    ) -> tuple[bool, list[AppliedModifier]]:
        """Hook 7: Check for instant win (Lucky Rabbit O+O).

        Called after cascades complete. Cards with ``effect="lucky_rabbit"``
        can trigger an instant win under specific conditions.

        Args:
            cascades: List of cascade steps from the move.

        Returns:
            Tuple of (instant_win flag, list of applied modifiers).
        """
        rabbit_cards = self._by_effect.get("lucky_rabbit", [])
        if not rabbit_cards:
            return False, []
        # Check cascades for mega combo matching the card's win_on_mega value.
        for card in rabbit_cards:
            target_mega = int(card.effect_params.get("win_on_mega", 44))
            for step in cascades:
                if hasattr(step, "special_activations"):
                    for act in step.special_activations:
                        if (
                            hasattr(act, "mega_func_value")
                            and act.mega_func_value == target_mega
                        ):
                            return True, [
                                AppliedModifier(
                                    card_id=card.card_id,
                                    card_name=card.name,
                                    hook="win_condition",
                                    description=f"{card.name}: mega {target_mega} triggered instant win!",
                                )
                            ]
        return False, []

    def check_energy_grant(
        self,
        chain_count: int,
    ) -> tuple[int, list[AppliedModifier]]:
        """Hook 8: Check energy grant (Heart of Fire).

        Called after cascades complete. Cards with ``effect="grant_energy"``
        can award extra hearts based on chain performance.

        Args:
            chain_count: Number of cascade steps in this move.

        Returns:
            Tuple of (hearts to grant, list of applied modifiers).
        """
        energy_cards = self._by_effect.get("grant_energy", [])
        if not energy_cards:
            return 0, []
        total_hearts = 0
        applied: list[AppliedModifier] = []
        for card in energy_cards:
            # min_chain can be in trigger_condition or effect_params.
            min_chain = 3
            if card.trigger_condition and "min_chain" in card.trigger_condition:
                min_chain = int(card.trigger_condition["min_chain"])
            elif "min_chain" in card.effect_params:
                min_chain = int(card.effect_params["min_chain"])
            hearts = card.effect_params.get("hearts", 1)
            if chain_count >= min_chain:
                total_hearts += hearts
                applied.append(
                    AppliedModifier(
                        card_id=card.card_id,
                        card_name=card.name,
                        hook="energy_grant",
                        description=f"{card.name}: +{hearts} heart(s) (chain {chain_count})",
                    )
                )
        return total_hearts, applied

    def check_raid_protection(
        self,
        seed: int = 0,
    ) -> tuple[bool, list[AppliedModifier]]:
        """Hook 10: Check if equipped cards block an incoming raid.

        Called before a raid resolves against this player. Cards with
        ``effect="raid_protection"`` grant full immunity, while cards
        with ``effect="raid_block"`` grant a probabilistic block.

        Args:
            seed: RNG seed for deterministic block-chance rolls.

        Returns:
            Tuple of (raid_blocked flag, list of applied modifiers).
        """
        # Full protection (Eternal Guardian) — always blocks.
        for card in self._by_effect.get("raid_protection", []):
            return True, [
                AppliedModifier(
                    card_id=card.card_id,
                    card_name=card.name,
                    hook="raid_protection",
                    description=f"{card.name}: full raid protection",
                )
            ]

        # Probabilistic block (Resilient Shield) — chance-based.
        for card in self._by_effect.get("raid_block", []):
            chance = float(card.effect_params.get("block_chance", 0.5))
            roll = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            if (roll % 1000) < int(chance * 1000):
                return True, [
                    AppliedModifier(
                        card_id=card.card_id,
                        card_name=card.name,
                        hook="raid_protection",
                        description=f"{card.name}: blocked raid ({chance * 100:.0f}% chance)",
                    )
                ]

        return False, []
