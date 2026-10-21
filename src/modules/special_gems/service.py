"""Special gems module service -- pure, synchronous effect calculation.

Handles creation, activation, and fusion of special gem types in
ChromaCrush. Calculates affected positions, bonus scores, and chain
reaction triggers.

All methods are synchronous ``def`` (not ``async def``). The service
performs pure computation on in-memory data with no I/O.

Dependencies are injected via ``__init__``. No direct imports from
``src.core`` concrete implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.types.board import BoardState, MatchResult
from src.core.types.game import GemType, Position
from src.modules.special_gems.fusion_service import FusionService
from src.modules.special_gems.types import (
    SPECIAL_GEM_TYPES,
    STANDARD_GEM_TYPES,
    FusionEffect,
    SpecialGemEffect,
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.special_gems.protocols import ScoringServiceProtocol


class SpecialGemsService:
    """Pure special gem effect calculation engine.

    All methods are regular ``def`` (fully synchronous). The service
    operates on in-memory data structures and never performs I/O.

    Args:
        config: Configuration service for special gem parameters.
        logger: Structured logger for diagnostic events.
        errors: Error factory for creating typed application errors.
        scoring_service: Scoring service for bonus point calculation.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        scoring_service: ScoringServiceProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._scoring = scoring_service

        # Cache configuration values read once at init.
        self._board_width: int = int(config.get("game.board_width", 8))
        self._board_height: int = int(config.get("game.board_height", 8))
        self._radial_bomb_radius: int = int(
            config.get("special_gems.radial_bomb_radius", 1)
        )
        self._mega_bomb_radius: int = int(
            config.get("special_gems.mega_bomb_radius", 2)
        )
        self._triple_line_count: int = int(
            config.get("special_gems.triple_line_count", 3)
        )
        self._chain_reaction_enabled: bool = bool(
            config.get("special_gems.chain_reaction_enabled", True)
        )

        self._fusion = FusionService(
            logger=logger,
            errors=errors,
            scoring_service=scoring_service,
            mega_bomb_radius=self._mega_bomb_radius,
            radial_bomb_radius=self._radial_bomb_radius,
            triple_line_count=self._triple_line_count,
            chain_reaction_enabled=self._chain_reaction_enabled,
        )

        self._logger.debug(
            "special_gems.service_initialized",
            board_width=self._board_width,
            board_height=self._board_height,
            radial_bomb_radius=self._radial_bomb_radius,
            mega_bomb_radius=self._mega_bomb_radius,
            triple_line_count=self._triple_line_count,
            chain_reaction_enabled=self._chain_reaction_enabled,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_special_gem(self, gem_type: GemType) -> bool:
        """Check if a gem type is a special gem.

        Args:
            gem_type: The gem type to check.

        Returns:
            True if gem_type is LINE_BLAST_H, LINE_BLAST_V,
            RADIAL_BOMB, or CHROMATIC_ORB.
        """
        return gem_type in SPECIAL_GEM_TYPES

    def calculate_effect(
        self,
        board: BoardState,
        position: Position,
        target_color: GemType | None = None,
    ) -> SpecialGemEffect:
        """Calculate the effect of activating a special gem at the given position.

        Args:
            board: Current board state.
            position: Position of the special gem to activate.
            target_color: Target color for Chromatic Orb (required if
                gem is CHROMATIC_ORB, must be standard gem 1-6).

        Returns:
            A ``SpecialGemEffect`` describing the activation.

        Raises:
            AppError: VALIDATION_OUT_OF_BOUNDS if position is outside grid.
            AppError: VALIDATION_INVALID_GEM_SWAP if position is not a special gem.
            AppError: VALIDATION_INVALID_INPUT if Chromatic Orb lacks target color
                or target color is invalid.
        """
        self._validate_position(board, position)

        gem_type = board.get(position)
        if not self.is_special_gem(gem_type):
            self._logger.warn(
                "special_gems.validation_failed",
                reason="Not a special gem",
                position=str(position),
            )
            raise self._errors.validation(
                "Position does not contain a special gem",
                code="VALIDATION_INVALID_GEM_SWAP",
                position=str(position),
                gem_type=gem_type.name,
                reason="Not a special gem",
            )

        if gem_type == GemType.CHROMATIC_ORB:
            self._validate_target_color(target_color)

        # Dispatch to specific calculation method.
        if gem_type == GemType.LINE_BLAST_H:
            effect = self._calculate_line_blast(board, position, is_horizontal=True)
        elif gem_type == GemType.LINE_BLAST_V:
            effect = self._calculate_line_blast(board, position, is_horizontal=False)
        elif gem_type == GemType.RADIAL_BOMB:
            effect = self._calculate_radial_bomb(
                board, position, self._radial_bomb_radius
            )
        else:
            # CHROMATIC_ORB — target_color is validated above.
            assert target_color is not None
            effect = self._calculate_chromatic_orb(board, position, target_color)

        self._logger.debug(
            "special_gems.effect_calculated",
            gem_type=gem_type.name,
            position=str(position),
            affected_count=len(effect.affected_positions),
        )

        return effect

    def calculate_fusion_effect(
        self,
        board: BoardState,
        pos_a: Position,
        pos_b: Position,
        target_color: GemType | None = None,
    ) -> FusionEffect:
        """Calculate the effect of fusing two special gems.

        Delegates to the internal ``FusionService``.

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
        return self._fusion.calculate_fusion_effect(board, pos_a, pos_b, target_color)

    def apply_effect(
        self,
        board: BoardState,
        effect: SpecialGemEffect | FusionEffect,
    ) -> tuple[BoardState, list[Position]]:
        """Apply a calculated effect to the board.

        Creates a copy of the board grid, sets all affected positions
        to EMPTY, and for ``FusionEffect`` also applies secondary effects.

        Args:
            board: Current board state (not modified).
            effect: The effect to apply.

        Returns:
            Tuple of (new BoardState with cleared gems, list of cleared positions).
        """
        new_grid = board.grid.copy()
        cleared: list[Position] = []

        for pos in effect.affected_positions:
            if 0 <= pos.row < board.height and 0 <= pos.col < board.width:
                new_grid[pos.row, pos.col] = GemType.EMPTY.value
                cleared.append(pos)

        # For fusion effects, also apply secondary effects.
        if isinstance(effect, FusionEffect):
            for secondary in effect.secondary_effects:
                for pos in secondary.affected_positions:
                    if (
                        0 <= pos.row < board.height
                        and 0 <= pos.col < board.width
                        and new_grid[pos.row, pos.col] != GemType.EMPTY.value
                    ):
                        new_grid[pos.row, pos.col] = GemType.EMPTY.value
                        cleared.append(pos)

        new_board = BoardState(grid=new_grid)

        self._logger.debug(
            "special_gems.effect_applied",
            cleared_count=len(cleared),
            triggered_specials=len(effect.triggers_special_gems),
        )

        return new_board, cleared

    def get_special_gem_for_match(
        self, match_result: MatchResult
    ) -> tuple[GemType, Position] | None:
        """Determine which special gem should be created from a match result.

        Rules:
        - T-shape or L-shape (overlapping matches): CHROMATIC_ORB at intersection
        - 5+ straight match: RADIAL_BOMB at center
        - 4-match horizontal: LINE_BLAST_H at center
        - 4-match vertical: LINE_BLAST_V at center
        - 3-match: None (no special gem)

        Args:
            match_result: Match detection result from the board module.

        Returns:
            Tuple of (special gem type, placement position) or None.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if matches are empty.
        """
        if not match_result.matches:
            self._logger.warn(
                "special_gems.validation_failed",
                reason="No matches to analyze",
            )
            raise self._errors.validation(
                "No matches to analyze",
                code="VALIDATION_INVALID_INPUT",
                field="match_result",
                reason="No matches to analyze",
            )

        # Check for overlapping positions across matches (T/L shape).
        all_positions: set[Position] = set()
        overlaps: set[Position] = set()
        for match in match_result.matches:
            for pos in match.positions:
                if pos in all_positions:
                    overlaps.add(pos)
                all_positions.add(pos)

        if overlaps and len(match_result.matches) >= 2:
            # CHROMATIC_ORB at the first overlap (deterministic via sorting).
            intersection = sorted(overlaps, key=lambda p: (p.row, p.col))[0]

            self._logger.debug(
                "special_gems.match_creates_special",
                match_pattern="T/L-shape",
                special_type="CHROMATIC_ORB",
                position=str(intersection),
            )

            return (GemType.CHROMATIC_ORB, intersection)

        # Single match analysis — check for longest match first.
        for match in match_result.matches:
            if match.length >= 5:
                center_pos = self._find_center(match.positions)

                self._logger.debug(
                    "special_gems.match_creates_special",
                    match_pattern=f"{match.length}-match",
                    special_type="RADIAL_BOMB",
                    position=str(center_pos),
                )

                return (GemType.RADIAL_BOMB, center_pos)

            if match.length == 4:
                center_pos = self._find_center(match.positions)
                gem_type = (
                    GemType.LINE_BLAST_H
                    if match.is_horizontal
                    else GemType.LINE_BLAST_V
                )

                self._logger.debug(
                    "special_gems.match_creates_special",
                    match_pattern=f"4-match {'horizontal' if match.is_horizontal else 'vertical'}",
                    special_type=gem_type.name,
                    position=str(center_pos),
                )

                return (gem_type, center_pos)

        # 3-match: no special gem created.
        return None

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
        if not self._chain_reaction_enabled:
            return []

        triggered: list[Position] = []

        for pos in cleared_positions:
            if (
                0 <= pos.row < board.height
                and 0 <= pos.col < board.width
                and self.is_special_gem(board.get(pos))
            ):
                triggered.append(pos)

        # Sort for deterministic ordering (top-to-bottom, left-to-right).
        triggered.sort(key=lambda p: (p.row, p.col))

        if triggered:
            self._logger.debug(
                "special_gems.chain_triggered",
                triggering_position=str(cleared_positions),
                triggered_positions=[str(p) for p in triggered],
            )

        return triggered

    # ------------------------------------------------------------------
    # Internal: Validation helpers
    # ------------------------------------------------------------------

    def _validate_position(self, board: BoardState, position: Position) -> None:
        """Validate that a position is within board bounds.

        Raises:
            AppError: VALIDATION_OUT_OF_BOUNDS if position is outside grid.
        """
        if (
            position.row < 0
            or position.row >= board.height
            or position.col < 0
            or position.col >= board.width
        ):
            self._logger.warn(
                "special_gems.validation_failed",
                reason="Position out of bounds",
                position=str(position),
            )
            raise self._errors.validation(
                "Position out of bounds",
                code="VALIDATION_OUT_OF_BOUNDS",
                position=str(position),
                board_width=board.width,
                board_height=board.height,
            )

    def _validate_target_color(self, target_color: GemType | None) -> None:
        """Validate target color for Chromatic Orb activations.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if target_color is None
                or not a standard gem (1-6).
        """
        if target_color is None:
            self._logger.warn(
                "special_gems.validation_failed",
                reason="Chromatic Orb requires target color",
            )
            raise self._errors.validation(
                "Chromatic Orb requires target color",
                code="VALIDATION_INVALID_INPUT",
                field="target_color",
                reason="Chromatic Orb requires target color",
            )

        if target_color not in STANDARD_GEM_TYPES:
            self._logger.warn(
                "special_gems.validation_failed",
                reason="Must be a standard gem color (1-6)",
                value=str(target_color),
            )
            raise self._errors.validation(
                "Target color must be a standard gem (1-6)",
                code="VALIDATION_INVALID_INPUT",
                field="target_color",
                value=int(target_color),
                reason="Must be a standard gem color (1-6)",
            )

    # ------------------------------------------------------------------
    # Internal: Effect calculations
    # ------------------------------------------------------------------

    def _calculate_line_blast(
        self,
        board: BoardState,
        position: Position,
        is_horizontal: bool,
    ) -> SpecialGemEffect:
        """Calculate positions affected by Line Blast.

        Horizontal: clears entire row. Vertical: clears entire column.
        """
        affected: set[Position] = set()
        width, height = board.width, board.height

        if is_horizontal:
            for col in range(width):
                affected.add(Position(position.row, col))
            description = f"Line Blast clears row {position.row}"
        else:
            for row in range(height):
                affected.add(Position(row, position.col))
            description = f"Line Blast clears column {position.col}"

        gem_type = GemType.LINE_BLAST_H if is_horizontal else GemType.LINE_BLAST_V

        triggered = self._find_triggered_specials(board, affected, exclude={position})

        bonus = self._scoring.calculate_special_gem_bonus(gem_type, len(affected))

        return SpecialGemEffect(
            gem_type=gem_type,
            source_position=position,
            affected_positions=frozenset(affected),
            bonus_score=bonus,
            triggers_special_gems=triggered,
            description=description,
        )

    def _calculate_radial_bomb(
        self,
        board: BoardState,
        position: Position,
        radius: int,
    ) -> SpecialGemEffect:
        """Calculate positions affected by Radial Bomb.

        For radius=1: 3x3 area. For radius=2: 5x5 area.
        """
        affected: set[Position] = set()
        width, height = board.width, board.height

        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                row = position.row + dr
                col = position.col + dc
                if 0 <= row < height and 0 <= col < width:
                    affected.add(Position(row, col))

        size = 2 * radius + 1
        description = (
            f"Radial Bomb explodes {size}x{size} at "
            f"({position.row}, {position.col})"
        )

        triggered = self._find_triggered_specials(board, affected, exclude={position})

        bonus = self._scoring.calculate_special_gem_bonus(
            GemType.RADIAL_BOMB, len(affected)
        )

        return SpecialGemEffect(
            gem_type=GemType.RADIAL_BOMB,
            source_position=position,
            affected_positions=frozenset(affected),
            bonus_score=bonus,
            triggers_special_gems=triggered,
            description=description,
        )

    def _calculate_chromatic_orb(
        self,
        board: BoardState,
        position: Position,
        target_color: GemType,
    ) -> SpecialGemEffect:
        """Calculate positions affected by Chromatic Orb.

        Clears all gems of the target color plus the orb itself.
        """
        affected: set[Position] = set()
        width, height = board.width, board.height

        for row in range(height):
            for col in range(width):
                pos = Position(row, col)
                if board.get(pos) == target_color:
                    affected.add(pos)

        # Also include the orb itself.
        affected.add(position)

        color_name = GemType(target_color).name
        description = (
            f"Chromatic Orb clears all {color_name} gems ({len(affected)} total)"
        )

        triggered = self._find_triggered_specials(board, affected, exclude={position})

        bonus = self._scoring.calculate_special_gem_bonus(
            GemType.CHROMATIC_ORB, len(affected)
        )

        return SpecialGemEffect(
            gem_type=GemType.CHROMATIC_ORB,
            source_position=position,
            affected_positions=frozenset(affected),
            bonus_score=bonus,
            triggers_special_gems=triggered,
            description=description,
        )

    # ------------------------------------------------------------------
    # Internal: Chain reaction helper
    # ------------------------------------------------------------------

    def _find_triggered_specials(
        self,
        board: BoardState,
        affected: set[Position],
        exclude: set[Position],
    ) -> list[Position]:
        """Find special gems in affected area that should chain-trigger.

        Args:
            board: Current board state.
            affected: Positions that will be cleared.
            exclude: Positions to exclude (the source special gems).

        Returns:
            Sorted list of triggered special gem positions.
        """
        if not self._chain_reaction_enabled:
            return []

        triggered: list[Position] = []

        for pos in affected:
            if pos in exclude:
                continue
            if (
                0 <= pos.row < board.height
                and 0 <= pos.col < board.width
                and self.is_special_gem(board.get(pos))
            ):
                triggered.append(pos)

        # Sort for deterministic ordering.
        triggered.sort(key=lambda p: (p.row, p.col))

        return triggered

    # ------------------------------------------------------------------
    # Internal: Position helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_center(positions: frozenset[Position]) -> Position:
        """Find the center position of a set of positions.

        Sorts positions by (row, col) and returns the middle element.
        """
        sorted_positions = sorted(positions, key=lambda p: (p.row, p.col))
        mid_index = len(sorted_positions) // 2
        return sorted_positions[mid_index]
