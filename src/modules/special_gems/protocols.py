"""Special gems module protocols -- typing.Protocol interfaces.

Defines the ``SpecialGemsServiceProtocol`` used by dependent modules
(board_gen, match) to interact with special gem logic without coupling
to the concrete implementation.

Also defines a minimal ``ScoringServiceProtocol`` covering only the
method required by the special_gems module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from src.core.types.board import BoardState, MatchResult
from src.core.types.game import GemType, Position
from src.modules.scoring.types import SpecialGemBonus
from src.modules.special_gems.types import FusionEffect, SpecialGemEffect

if TYPE_CHECKING:
    pass


class ScoringServiceProtocol(Protocol):
    """Minimal scoring service interface required by special_gems.

    Only ``calculate_special_gem_bonus`` is used.
    """

    def calculate_special_gem_bonus(
        self, gem_type: GemType, gems_affected: int
    ) -> SpecialGemBonus:
        """Calculate bonus points from special gem activation."""
        ...


class SpecialGemsServiceProtocol(Protocol):
    """Protocol for the special gems service.

    Consumed by dependent modules (board_gen, match) via ``__init__``
    injection. All methods are synchronous.
    """

    def calculate_effect(
        self,
        board: BoardState,
        position: Position,
        target_color: GemType | None = None,
    ) -> SpecialGemEffect:
        """Calculate the effect of activating a special gem.

        Args:
            board: Current board state.
            position: Position of the special gem to activate.
            target_color: Required for CHROMATIC_ORB (standard gem 1-6).

        Returns:
            A ``SpecialGemEffect`` describing the activation.

        Raises:
            AppError: VALIDATION_OUT_OF_BOUNDS, VALIDATION_INVALID_GEM_SWAP,
                or VALIDATION_INVALID_INPUT.
        """
        ...

    def calculate_fusion_effect(
        self,
        board: BoardState,
        pos_a: Position,
        pos_b: Position,
        target_color: GemType | None = None,
    ) -> FusionEffect:
        """Calculate the effect of fusing two special gems.

        Args:
            board: Current board state.
            pos_a: Position of first special gem.
            pos_b: Position of second special gem (must be adjacent).
            target_color: Required if either gem is CHROMATIC_ORB.

        Returns:
            A ``FusionEffect`` describing the fusion.

        Raises:
            AppError: VALIDATION_OUT_OF_BOUNDS, VALIDATION_INVALID_GEM_SWAP,
                VALIDATION_POSITIONS_NOT_ADJACENT, or VALIDATION_INVALID_INPUT.
        """
        ...

    def apply_effect(
        self,
        board: BoardState,
        effect: SpecialGemEffect | FusionEffect,
    ) -> tuple[BoardState, list[Position]]:
        """Apply a calculated effect to the board.

        Args:
            board: Current board state.
            effect: The effect to apply.

        Returns:
            Tuple of (new BoardState, list of cleared positions).
        """
        ...

    def is_special_gem(self, gem_type: GemType) -> bool:
        """Check if a gem type is a special gem.

        Returns:
            True if gem_type is LINE_BLAST_H, LINE_BLAST_V,
            RADIAL_BOMB, or CHROMATIC_ORB.
        """
        ...

    def get_special_gem_for_match(
        self, match_result: MatchResult
    ) -> tuple[GemType, Position] | None:
        """Determine which special gem should be created from a match.

        Args:
            match_result: Match detection result from the board module.

        Returns:
            Tuple of (special gem type, placement position) or None for
            3-matches that don't create special gems.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if matches are empty.
        """
        ...

    def find_triggered_special_gems(
        self, board: BoardState, cleared_positions: set[Position]
    ) -> list[Position]:
        """Find special gems that should be triggered by cleared positions.

        Args:
            board: Current board state.
            cleared_positions: Positions being cleared.

        Returns:
            Sorted list of positions containing special gems in the
            cleared area (deterministic row, col ordering).
        """
        ...
