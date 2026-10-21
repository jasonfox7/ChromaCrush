"""Scoring module types — immutable result dataclasses.

All types are frozen dataclasses for thread safety and clarity.
Scoring types are consumed by dependent modules (special_gems, match)
and by presentation adapters for display formatting.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.types.board import MatchGroup
from src.core.types.game import GemType


@dataclass(frozen=True)
class MatchGroupScore:
    """Score breakdown for a single match group.

    Attributes:
        match_group: The match group being scored.
        base_points: Raw points before length multiplier (base_points * length).
        length_multiplier: Multiplier applied for match length.
        length_bonus_points: Additional points from length multiplier.
        subtotal: Final points for this group (base_points * length_multiplier).
    """

    match_group: MatchGroup
    base_points: int
    length_multiplier: float
    length_bonus_points: int
    subtotal: int


@dataclass(frozen=True)
class MatchScore:
    """Score for a single match detection (may contain multiple match groups).

    Attributes:
        total_points: Final score after chain multiplier and bonuses.
        base_points: Sum of all match group subtotals before chain multiplier.
        chain_multiplier: Multiplier applied for cascade chain step.
        chain_step: Which cascade step this score was calculated for.
        match_breakdown: Per-group score breakdown.
        special_gem_creation_bonus: Bonus points for creating a special gem.
    """

    total_points: int
    base_points: int
    chain_multiplier: float
    chain_step: int
    match_breakdown: tuple[MatchGroupScore, ...]
    special_gem_creation_bonus: int


@dataclass(frozen=True)
class SpecialGemBonus:
    """Bonus points from special gem activation.

    Attributes:
        gem_type: The special gem type that was activated.
        base_activation_bonus: Flat bonus for activating the gem.
        gems_affected: Number of gems cleared by the activation.
        per_gem_bonus: Points awarded per gem affected.
        total_bonus: base_activation_bonus + (gems_affected * per_gem_bonus).
    """

    gem_type: GemType
    base_activation_bonus: int
    gems_affected: int
    per_gem_bonus: int
    total_bonus: int


@dataclass(frozen=True)
class CascadeStepScore:
    """Score for a single cascade step.

    Attributes:
        step_number: 1-based cascade step index.
        match_score: Score from match detection in this step.
        special_gem_bonuses: Bonuses from special gems activated in this step.
    """

    step_number: int
    match_score: MatchScore
    special_gem_bonuses: tuple[SpecialGemBonus, ...]


@dataclass(frozen=True)
class MoveScore:
    """Complete score breakdown for a player's move.

    Attributes:
        total_points: Sum of all cascade step scores.
        cascade_scores: Per-step score breakdown.
        chain_count: Number of cascade steps.
        total_gems_cleared: Total gems cleared across all cascades.
        highest_chain_multiplier: Peak chain multiplier reached.
        special_gems_created: Count of special gems created.
        special_gems_activated: Count of special gems activated.
    """

    total_points: int
    cascade_scores: tuple[CascadeStepScore, ...]
    chain_count: int
    total_gems_cleared: int
    highest_chain_multiplier: float
    special_gems_created: int
    special_gems_activated: int

    def summary(self) -> str:
        """Human-readable summary for UI display."""
        if self.chain_count <= 1:
            chain_text = "Single match"
        elif self.chain_count == 2:
            chain_text = "Double chain"
        elif self.chain_count == 3:
            chain_text = "Triple chain"
        else:
            chain_text = f"{self.chain_count}x chain"

        parts = [f"{chain_text}! +{self.total_points} points"]

        if self.special_gems_created > 0:
            parts.append(f"{self.special_gems_created} special gem(s) created")

        if self.special_gems_activated > 0:
            parts.append(f"{self.special_gems_activated} special gem(s) activated")

        return " | ".join(parts)
