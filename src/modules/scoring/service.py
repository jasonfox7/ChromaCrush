"""Scoring module service -- pure, synchronous score calculation.

Calculates points earned from match-3 actions. Takes match results from
the board module and computes scores based on base points, match length
bonuses, chain multipliers, and special gem bonuses.

All methods are synchronous ``def`` (not ``async def``). The service
performs pure arithmetic on in-memory data with no I/O.

Dependencies are injected via ``__init__``. No direct imports from
``src.core`` concrete implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.types.board import MatchResult
from src.core.types.game import GemType
from src.modules.board.types import MoveProcessingResult
from src.modules.scoring.types import (
    CascadeStepScore,
    MatchGroupScore,
    MatchScore,
    MoveScore,
    SpecialGemBonus,
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol

# Special gem types for validation.
_SPECIAL_GEM_TYPES = frozenset(
    {
        GemType.LINE_BLAST_H,
        GemType.LINE_BLAST_V,
        GemType.RADIAL_BOMB,
        GemType.CHROMATIC_ORB,
    }
)

# Standard gem types for validation (1-6).
_STANDARD_GEM_TYPES = frozenset(
    {
        GemType.RED,
        GemType.BLUE,
        GemType.GREEN,
        GemType.YELLOW,
        GemType.PURPLE,
        GemType.ORANGE,
    }
)


class ScoringService:
    """Pure score calculation engine.

    All methods are regular ``def`` (fully synchronous). The service
    operates on in-memory data structures and never performs I/O.

    Args:
        config: Configuration service for scoring parameters.
        logger: Structured logger for diagnostic events.
        errors: Error factory for creating typed application errors.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors

        # Cache configuration values read once at init.
        self._base_points: int = self._validate_positive_int(
            config.get("scoring.base_points", 50),
            "scoring.base_points",
            50,
        )
        self._chain_multipliers: tuple[float, ...] = self._validate_multiplier_list(
            config.get("scoring.chain_multipliers", [1.0, 1.5, 2.0, 2.5, 3.0]),
            "scoring.chain_multipliers",
            (1.0, 1.5, 2.0, 2.5, 3.0),
        )
        self._length_multipliers: tuple[float, ...] = self._validate_multiplier_list(
            config.get("scoring.length_multipliers", [1.0, 2.0, 3.0, 4.0, 5.0]),
            "scoring.length_multipliers",
            (1.0, 2.0, 3.0, 4.0, 5.0),
        )
        self._special_gem_creation_bonus: int = self._validate_positive_int(
            config.get("scoring.special_gem_creation_bonus", 100),
            "scoring.special_gem_creation_bonus",
            100,
        )
        self._line_blast_activation_bonus: int = self._validate_positive_int(
            config.get("scoring.line_blast_activation_bonus", 50),
            "scoring.line_blast_activation_bonus",
            50,
        )
        self._line_blast_per_gem: int = self._validate_positive_int(
            config.get("scoring.line_blast_per_gem", 25),
            "scoring.line_blast_per_gem",
            25,
        )
        self._radial_bomb_activation_bonus: int = self._validate_positive_int(
            config.get("scoring.radial_bomb_activation_bonus", 100),
            "scoring.radial_bomb_activation_bonus",
            100,
        )
        self._radial_bomb_per_gem: int = self._validate_positive_int(
            config.get("scoring.radial_bomb_per_gem", 30),
            "scoring.radial_bomb_per_gem",
            30,
        )
        self._chromatic_orb_activation_bonus: int = self._validate_positive_int(
            config.get("scoring.chromatic_orb_activation_bonus", 200),
            "scoring.chromatic_orb_activation_bonus",
            200,
        )
        self._chromatic_orb_per_gem: int = self._validate_positive_int(
            config.get("scoring.chromatic_orb_per_gem", 40),
            "scoring.chromatic_orb_per_gem",
            40,
        )
        self._cascade_combo_threshold: int = self._validate_positive_int(
            config.get("scoring.cascade_combo_threshold", 4),
            "scoring.cascade_combo_threshold",
            4,
        )
        self._cascade_combo_points_per_chain: int = self._validate_positive_int(
            config.get("scoring.cascade_combo_points_per_chain", 1000),
            "scoring.cascade_combo_points_per_chain",
            1000,
        )

        self._logger.debug(
            "scoring.service_initialized",
            base_points=self._base_points,
            chain_multipliers=str(self._chain_multipliers),
            length_multipliers=str(self._length_multipliers),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_match_score(
        self, match_result: MatchResult, chain_step: int = 1
    ) -> MatchScore:
        """Calculate score for a single match detection result.

        Args:
            match_result: Match detection result from the board module.
                Must contain at least one match.
            chain_step: Current cascade step (1 = initial match, 2+ = cascade).
                Must be >= 1.

        Returns:
            A ``MatchScore`` with detailed breakdown.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if matches are empty or
                chain_step < 1.
        """
        # Validate inputs.
        if not match_result.matches:
            self._logger.warn(
                "scoring.validation_failed",
                reason="No matches to score",
                field="match_result",
            )
            raise self._errors.validation(
                "No matches to score",
                code="VALIDATION_INVALID_INPUT",
                field="match_result",
                reason="No matches to score",
            )

        if chain_step < 1:
            self._logger.warn(
                "scoring.validation_failed",
                reason="Chain step must be >= 1",
                field="chain_step",
                value=chain_step,
            )
            raise self._errors.validation(
                "Chain step must be >= 1",
                code="VALIDATION_INVALID_INPUT",
                field="chain_step",
                value=chain_step,
                reason="Chain step must be >= 1",
            )

        chain_multiplier = self.get_chain_multiplier(chain_step)

        # Score each match group.
        match_breakdown: list[MatchGroupScore] = []
        total_base = 0

        for match_group in match_result.matches:
            # Base points for gems in this match.
            group_base = self._base_points * match_group.length

            # Length multiplier.
            length_mult = self.get_match_length_multiplier(match_group.length)
            length_bonus = int(group_base * (length_mult - 1.0))

            # Subtotal before chain multiplier.
            subtotal = int(group_base * length_mult)

            match_breakdown.append(
                MatchGroupScore(
                    match_group=match_group,
                    base_points=group_base,
                    length_multiplier=length_mult,
                    length_bonus_points=length_bonus,
                    subtotal=subtotal,
                )
            )

            total_base += subtotal

            self._logger.trace(
                "scoring.length_multiplier_applied",
                match_length=match_group.length,
                multiplier=length_mult,
            )

        # Special gem creation bonus.
        special_bonus = 0
        if match_result.creates_special_gem:
            special_bonus = self._special_gem_creation_bonus

        # Apply chain multiplier to base total, add special bonus.
        total = int(total_base * chain_multiplier) + special_bonus

        self._logger.trace(
            "scoring.chain_multiplier_applied",
            chain_step=chain_step,
            multiplier=chain_multiplier,
        )

        result = MatchScore(
            total_points=total,
            base_points=total_base,
            chain_multiplier=chain_multiplier,
            chain_step=chain_step,
            match_breakdown=tuple(match_breakdown),
            special_gem_creation_bonus=special_bonus,
        )

        self._logger.debug(
            "scoring.match_scored",
            chain_step=chain_step,
            total_points=total,
            match_count=len(match_result.matches),
            creates_special=match_result.creates_special_gem,
        )

        return result

    def calculate_move_score(
        self,
        move_result: MoveProcessingResult,
        score_modifiers: object | None = None,
    ) -> MoveScore:
        """Calculate complete score for a player's move.

        Iterates through all cascade steps, scoring each with its chain
        step multiplier, and aggregates totals.

        Args:
            move_result: Complete move processing result from the board module.
                Must have ``was_valid_match=True``.
            score_modifiers: Optional ScoreModifiers from card system.

        Returns:
            A ``MoveScore`` with detailed cascade breakdown.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if move was not valid.
        """
        if not move_result.was_valid_match:
            self._logger.warn(
                "scoring.validation_failed",
                reason="Cannot score invalid move",
                field="move_result",
            )
            raise self._errors.validation(
                "Cannot score invalid move",
                code="VALIDATION_INVALID_INPUT",
                field="move_result",
                reason="Cannot score invalid move",
            )

        cascade_scores: list[CascadeStepScore] = []
        total_points = 0
        total_gems = 0
        special_created = 0
        special_activated = 0
        highest_mult = 1.0

        for i, cascade_step in enumerate(move_result.cascades, start=1):
            # Attraction-only steps (e.g. fusion-enabling swaps) have no
            # color matches — score them as zero rather than raising.
            if not cascade_step.matches.matches:
                match_score = MatchScore(
                    total_points=0,
                    base_points=0,
                    chain_multiplier=1.0,
                    chain_step=i,
                    match_breakdown=(),
                    special_gem_creation_bonus=0,
                )
            else:
                match_score = self.calculate_match_score(
                    cascade_step.matches,
                    chain_step=i,
                )

            # Score special gem activations in this cascade step.
            step_bonuses: list[SpecialGemBonus] = []
            for activation in cascade_step.special_activations:
                bonus = self.calculate_special_gem_bonus(
                    activation.gem_type,
                    len(activation.affected_positions),
                )
                step_bonuses.append(bonus)
                special_activated += 1
            special_bonuses = tuple(step_bonuses)

            cascade_scores.append(
                CascadeStepScore(
                    step_number=i,
                    match_score=match_score,
                    special_gem_bonuses=special_bonuses,
                )
            )

            total_points += match_score.total_points
            total_points += sum(b.total_bonus for b in special_bonuses)
            total_gems += cascade_step.matches.total_gems_matched
            highest_mult = max(highest_mult, match_score.chain_multiplier)

            if cascade_step.matches.creates_special_gem:
                special_created += 1

        # Cascade combo bonus: flat bonus when chain count meets threshold.
        cascade_combo_bonus = 0
        if len(cascade_scores) >= self._cascade_combo_threshold:
            cascade_combo_bonus = (
                len(cascade_scores) * self._cascade_combo_points_per_chain
            )
            total_points += cascade_combo_bonus
            self._logger.debug(
                "scoring.cascade_combo_bonus",
                chain_count=len(cascade_scores),
                bonus=cascade_combo_bonus,
            )

        # ---- Card modifier score adjustments (Hook 6) ----
        if score_modifiers is not None:
            sm = score_modifiers
            # Apply per-step multipliers retroactively to cascade scores.
            if sm.first_step_multiplier != 1.0 and cascade_scores:
                first = cascade_scores[0]
                bonus = int(
                    first.match_score.total_points * (sm.first_step_multiplier - 1.0)
                )
                total_points += bonus
            if sm.cascade_multiplier != 1.0:
                total_points = int(total_points * sm.cascade_multiplier)
            if sm.chain_reaction_multiplier != 1.0 and len(cascade_scores) >= 2:
                # Chain reaction bonus scales with cascade depth.
                chain_bonus = int(total_points * (sm.chain_reaction_multiplier - 1.0))
                total_points += chain_bonus
            if sm.special_multiplier != 1.0 and special_activated > 0:
                special_pts = sum(
                    b.total_bonus
                    for cs in cascade_scores
                    for b in cs.special_gem_bonuses
                )
                total_points += int(special_pts * (sm.special_multiplier - 1.0))
            if sm.cascade_depth_bonus > 0 and len(cascade_scores) > 1:
                depth_bonus = int(sm.cascade_depth_bonus * (len(cascade_scores) - 1))
                total_points += depth_bonus
            # Apply all_multiplier last — global multiplier on the entire total.
            if sm.all_multiplier != 1.0:
                total_points = int(total_points * sm.all_multiplier)

        result = MoveScore(
            total_points=total_points,
            cascade_scores=tuple(cascade_scores),
            chain_count=len(cascade_scores),
            total_gems_cleared=total_gems,
            highest_chain_multiplier=highest_mult,
            special_gems_created=special_created,
            special_gems_activated=special_activated,
        )

        self._logger.debug(
            "scoring.move_scored",
            total_points=total_points,
            chain_count=len(cascade_scores),
            gems_cleared=total_gems,
        )

        return result

    def calculate_special_gem_bonus(
        self, gem_type: GemType, gems_affected: int
    ) -> SpecialGemBonus:
        """Calculate bonus points from special gem activation.

        Args:
            gem_type: The special gem type that was activated. Must be a
                special gem type (negative value).
            gems_affected: Number of gems cleared by the special gem.
                Must be >= 0.

        Returns:
            A ``SpecialGemBonus`` with detailed breakdown.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if gem_type is not special
                or gems_affected < 0.
        """
        if gem_type not in _SPECIAL_GEM_TYPES:
            self._logger.warn(
                "scoring.validation_failed",
                reason="Not a special gem type",
                field="gem_type",
                value=int(gem_type),
            )
            raise self._errors.validation(
                "Not a special gem type",
                code="VALIDATION_INVALID_INPUT",
                field="gem_type",
                value=int(gem_type),
                reason="Not a special gem type",
            )

        if gems_affected < 0:
            self._logger.warn(
                "scoring.validation_failed",
                reason="Gems affected must be >= 0",
                field="gems_affected",
                value=gems_affected,
            )
            raise self._errors.validation(
                "Gems affected must be >= 0",
                code="VALIDATION_INVALID_INPUT",
                field="gems_affected",
                value=gems_affected,
                reason="Gems affected must be >= 0",
            )

        if gem_type in (GemType.LINE_BLAST_H, GemType.LINE_BLAST_V):
            base_bonus = self._line_blast_activation_bonus
            per_gem = self._line_blast_per_gem
        elif gem_type == GemType.RADIAL_BOMB:
            base_bonus = self._radial_bomb_activation_bonus
            per_gem = self._radial_bomb_per_gem
        elif gem_type == GemType.CHROMATIC_ORB:
            base_bonus = self._chromatic_orb_activation_bonus
            per_gem = self._chromatic_orb_per_gem
        else:
            # Should not reach here due to validation above.
            base_bonus = 0
            per_gem = 0

        total = base_bonus + (gems_affected * per_gem)

        result = SpecialGemBonus(
            gem_type=gem_type,
            base_activation_bonus=base_bonus,
            gems_affected=gems_affected,
            per_gem_bonus=per_gem,
            total_bonus=total,
        )

        self._logger.debug(
            "scoring.special_gem_bonus",
            gem_type=gem_type.name,
            gems_affected=gems_affected,
            bonus_points=total,
        )

        return result

    def get_chain_multiplier(self, chain_step: int) -> float:
        """Look up the chain multiplier for a given cascade step.

        Args:
            chain_step: The cascade step number. Must be >= 1.

        Returns:
            The chain multiplier (e.g. 1.0 for step 1, 1.5 for step 2).

        Raises:
            AppError: VALIDATION_INVALID_INPUT if chain_step < 1.
        """
        if chain_step < 1:
            self._logger.warn(
                "scoring.validation_failed",
                reason="Chain step must be >= 1",
                field="chain_step",
                value=chain_step,
            )
            raise self._errors.validation(
                "Chain step must be >= 1",
                code="VALIDATION_INVALID_INPUT",
                field="chain_step",
                value=chain_step,
                reason="Chain step must be >= 1",
            )

        index = min(chain_step - 1, len(self._chain_multipliers) - 1)
        return self._chain_multipliers[index]

    def get_match_length_multiplier(self, match_length: int) -> float:
        """Look up the length multiplier for a given match length.

        Args:
            match_length: Number of gems in the match. Must be >= 3.

        Returns:
            The length multiplier (e.g. 1.0 for 3-match, 2.0 for 4-match).

        Raises:
            AppError: VALIDATION_INVALID_INPUT if match_length < 3.
        """
        if match_length < 3:
            self._logger.warn(
                "scoring.validation_failed",
                reason="Match length must be >= 3",
                field="match_length",
                value=match_length,
            )
            raise self._errors.validation(
                "Match length must be >= 3",
                code="VALIDATION_INVALID_INPUT",
                field="match_length",
                value=match_length,
                reason="Match length must be >= 3",
            )

        index = min(match_length - 3, len(self._length_multipliers) - 1)
        return self._length_multipliers[index]

    def get_base_points(self, gem_type: GemType) -> int:
        """Get the base points value for a standard gem type.

        Args:
            gem_type: The gem type to query. Must be a standard gem (1-6).

        Returns:
            The base points value (configurable, default 50).

        Raises:
            AppError: VALIDATION_INVALID_INPUT if gem_type is not standard.
        """
        if gem_type not in _STANDARD_GEM_TYPES:
            self._logger.warn(
                "scoring.validation_failed",
                reason="Not a standard gem type",
                field="gem_type",
                value=int(gem_type),
            )
            raise self._errors.validation(
                "Not a standard gem type",
                code="VALIDATION_INVALID_INPUT",
                field="gem_type",
                value=int(gem_type),
                reason="Not a standard gem type",
            )

        return self._base_points

    def get_scoring_config(self) -> dict[str, object]:
        """Return all scoring configuration values as a dictionary.

        Returns:
            A dict with keys: base_points, chain_multipliers,
            length_multipliers, special_gem_creation_bonus,
            line_blast_activation_bonus, line_blast_per_gem,
            radial_bomb_activation_bonus, radial_bomb_per_gem,
            chromatic_orb_activation_bonus, chromatic_orb_per_gem.
        """
        return {
            "base_points": self._base_points,
            "chain_multipliers": self._chain_multipliers,
            "length_multipliers": self._length_multipliers,
            "special_gem_creation_bonus": self._special_gem_creation_bonus,
            "line_blast_activation_bonus": self._line_blast_activation_bonus,
            "line_blast_per_gem": self._line_blast_per_gem,
            "radial_bomb_activation_bonus": self._radial_bomb_activation_bonus,
            "radial_bomb_per_gem": self._radial_bomb_per_gem,
            "chromatic_orb_activation_bonus": self._chromatic_orb_activation_bonus,
            "chromatic_orb_per_gem": self._chromatic_orb_per_gem,
            "cascade_combo_threshold": self._cascade_combo_threshold,
            "cascade_combo_points_per_chain": self._cascade_combo_points_per_chain,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_positive_int(self, value: object, key: str, default: int) -> int:
        """Validate that a config value is a positive integer.

        Returns the value if valid, or the default if invalid (with a
        warning logged).
        """
        try:
            int_value = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            self._logger.warn(
                "scoring.config_invalid",
                key=key,
                value=str(value),
                reason="Not a valid integer, using default",
                default=default,
            )
            return default

        if int_value <= 0:
            self._logger.warn(
                "scoring.config_invalid",
                key=key,
                value=int_value,
                reason="Value must be positive, using default",
                default=default,
            )
            return default

        return int_value

    def _validate_multiplier_list(
        self,
        value: object,
        key: str,
        default: tuple[float, ...],
    ) -> tuple[float, ...]:
        """Validate that a config value is a list of positive floats.

        Returns a tuple of floats if valid, or the default if invalid
        (with a warning logged).
        """
        if not isinstance(value, (list, tuple)):
            self._logger.warn(
                "scoring.config_invalid",
                key=key,
                value=str(value),
                reason="Not a list, using default",
                default=str(default),
            )
            return default

        if not value:
            self._logger.warn(
                "scoring.config_invalid",
                key=key,
                value=str(value),
                reason="Empty list, using default",
                default=str(default),
            )
            return default

        try:
            floats = tuple(float(v) for v in value)
        except (TypeError, ValueError):
            self._logger.warn(
                "scoring.config_invalid",
                key=key,
                value=str(value),
                reason="Contains non-numeric values, using default",
                default=str(default),
            )
            return default

        if any(f <= 0 for f in floats):
            self._logger.warn(
                "scoring.config_invalid",
                key=key,
                value=str(value),
                reason="Contains non-positive values, using default",
                default=str(default),
            )
            return default

        return floats
