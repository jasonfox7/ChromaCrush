"""Fusion subsystem -- calculates effects of fusing two special gems.

Internal implementation detail of the special_gems module. Not exported
from ``__init__.py``. Created and owned by ``SpecialGemsService``.

All methods are synchronous ``def`` (not ``async def``). The service
performs pure computation on in-memory data with no I/O.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.types.board import BoardState
from src.core.types.game import GemType, Position
from src.modules.special_gems.types import (
    SPECIAL_GEM_TYPES,
    STANDARD_GEM_TYPES,
    FusionEffect,
    FusionType,
    SpecialGemEffect,
)

if TYPE_CHECKING:
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.special_gems.protocols import ScoringServiceProtocol


class FusionService:
    """Pure fusion effect calculation engine.

    Handles all six fusion types produced when two special gems are
    swapped into each other. Created internally by ``SpecialGemsService``
    and not exposed outside the module.

    Args:
        logger: Structured logger for diagnostic events.
        errors: Error factory for creating typed application errors.
        scoring_service: Scoring service for bonus point calculation.
        mega_bomb_radius: Radius for Mega Bomb fusion (default 2).
        radial_bomb_radius: Radius for Radial Bomb in Color Bomb fusion.
        triple_line_count: Number of rows/columns for Triple Line fusion.
        chain_reaction_enabled: Whether chain reactions trigger specials.
    """

    def __init__(
        self,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        scoring_service: ScoringServiceProtocol,
        *,
        mega_bomb_radius: int,
        radial_bomb_radius: int,
        triple_line_count: int,
        chain_reaction_enabled: bool,
    ) -> None:
        self._logger = logger
        self._errors = errors
        self._scoring = scoring_service
        self._mega_bomb_radius = mega_bomb_radius
        self._radial_bomb_radius = radial_bomb_radius
        self._triple_line_count = triple_line_count
        self._chain_reaction_enabled = chain_reaction_enabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
        self._validate_position(board, pos_a)
        self._validate_position(board, pos_b)

        gem_a = board.get(pos_a)
        gem_b = board.get(pos_b)

        if not self._is_special_gem(gem_a):
            self._logger.warn(
                "special_gems.validation_failed",
                reason="Not a special gem",
                position=str(pos_a),
            )
            raise self._errors.validation(
                "Position does not contain a special gem",
                code="VALIDATION_INVALID_GEM_SWAP",
                position=str(pos_a),
                gem_type=gem_a.name,
                reason="Not a special gem",
            )

        if not self._is_special_gem(gem_b):
            self._logger.warn(
                "special_gems.validation_failed",
                reason="Not a special gem",
                position=str(pos_b),
            )
            raise self._errors.validation(
                "Position does not contain a special gem",
                code="VALIDATION_INVALID_GEM_SWAP",
                position=str(pos_b),
                gem_type=gem_b.name,
                reason="Not a special gem",
            )

        if not pos_a.is_adjacent_to(pos_b):
            self._logger.warn(
                "special_gems.validation_failed",
                reason="Positions not adjacent",
                pos_a=str(pos_a),
                pos_b=str(pos_b),
            )
            raise self._errors.validation(
                "Fusion positions must be adjacent",
                code="VALIDATION_POSITIONS_NOT_ADJACENT",
                pos_a=str(pos_a),
                pos_b=str(pos_b),
            )

        # Normalize order: sort by gem type value so lower value is gem_a.
        if gem_a.value > gem_b.value:
            gem_a, gem_b = gem_b, gem_a
            pos_a, pos_b = pos_b, pos_a

        # Determine fusion type and calculate effect.
        fusion_type, affected, secondary, description = self._calculate_fusion(
            board, gem_a, gem_b, pos_a, pos_b, target_color
        )

        # Find triggered special gems (excluding the fusion sources).
        triggered = self._find_triggered_specials(
            board, affected, exclude={pos_a, pos_b}
        )

        # Calculate combined bonus: primary + secondary affected counts.
        total_affected = len(affected)
        for sec_effect in secondary:
            total_affected += len(sec_effect.affected_positions)

        bonus = self._scoring.calculate_special_gem_bonus(gem_a, total_affected)

        result = FusionEffect(
            gem_a_type=gem_a,
            gem_b_type=gem_b,
            fusion_type=fusion_type,
            source_positions=(pos_a, pos_b),
            affected_positions=frozenset(affected),
            bonus_score=bonus,
            triggers_special_gems=triggered,
            secondary_effects=secondary,
            description=description,
        )

        self._logger.debug(
            "special_gems.fusion_calculated",
            gem_a=gem_a.name,
            gem_b=gem_b.name,
            fusion_type=fusion_type.value,
            affected_count=len(affected),
        )

        return result

    # ------------------------------------------------------------------
    # Internal: Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_special_gem(gem_type: GemType) -> bool:
        """Check if a gem type is a special gem."""
        return gem_type in SPECIAL_GEM_TYPES

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
        """Validate target color for Chromatic Orb fusions.

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
                and self._is_special_gem(board.get(pos))
            ):
                triggered.append(pos)

        # Sort for deterministic ordering.
        triggered.sort(key=lambda p: (p.row, p.col))

        return triggered

    # ------------------------------------------------------------------
    # Internal: Fusion dispatch
    # ------------------------------------------------------------------

    def _calculate_fusion(
        self,
        board: BoardState,
        gem_a: GemType,
        gem_b: GemType,
        pos_a: Position,
        pos_b: Position,
        target_color: GemType | None,
    ) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
        """Internal fusion calculation dispatch.

        Gem types are already normalized so gem_a.value <= gem_b.value.
        Since special gems have negative values (LINE_BLAST_H=-1,
        LINE_BLAST_V=-2, RADIAL_BOMB=-3, CHROMATIC_ORB=-4), the
        normalization means gem_a has the MORE NEGATIVE value (lower).
        So gem_a is the "stronger" gem: CHROMATIC < RADIAL < LINE_V < LINE_H.
        """
        line_types = {GemType.LINE_BLAST_H, GemType.LINE_BLAST_V}

        # Chromatic + Chromatic = Board Clear
        if gem_a == GemType.CHROMATIC_ORB and gem_b == GemType.CHROMATIC_ORB:
            return self._fusion_board_clear(board, pos_a, pos_b)

        # Chromatic + Radial = Color Bomb  (gem_a=CHROMATIC(-4), gem_b=RADIAL(-3))
        if gem_a == GemType.CHROMATIC_ORB and gem_b == GemType.RADIAL_BOMB:
            return self._fusion_color_bomb(board, pos_a, pos_b, target_color)

        # Chromatic + Line = Color Line Blast  (gem_a=CHROMATIC(-4), gem_b=LINE)
        if gem_a == GemType.CHROMATIC_ORB and gem_b in line_types:
            return self._fusion_color_line_blast(
                board, pos_a, pos_b, target_color, gem_b
            )

        # Radial + Radial = Mega Bomb
        if gem_a == GemType.RADIAL_BOMB and gem_b == GemType.RADIAL_BOMB:
            return self._fusion_mega_bomb(board, pos_a, pos_b)

        # Radial + Line = Triple Line  (gem_a=RADIAL(-3), gem_b=LINE)
        if gem_a == GemType.RADIAL_BOMB and gem_b in line_types:
            return self._fusion_triple_line(board, pos_a, pos_b, gem_b)

        # Line + Line = Cross Blast  (gem_a=LINE_V(-2), gem_b=LINE_H(-1) or same)
        if gem_a in line_types and gem_b in line_types:
            return self._fusion_cross_blast(board, pos_a, pos_b)

        # Should not reach here if validation is correct.
        raise self._errors.validation(
            "Unknown fusion combination",
            code="VALIDATION_INVALID_INPUT",
            gem_a=gem_a.name,
            gem_b=gem_b.name,
        )

    # ------------------------------------------------------------------
    # Internal: Fusion implementations
    # ------------------------------------------------------------------

    def _fusion_cross_blast(
        self,
        board: BoardState,
        pos_a: Position,
        pos_b: Position,
    ) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
        """Line + Line = clears both row AND column at midpoint."""
        affected: set[Position] = set()
        width, height = board.width, board.height

        mid_row = (pos_a.row + pos_b.row) // 2
        mid_col = (pos_a.col + pos_b.col) // 2

        # Clear entire row.
        for col in range(width):
            affected.add(Position(mid_row, col))

        # Clear entire column.
        for row in range(height):
            affected.add(Position(row, mid_col))

        description = f"Cross Blast clears row {mid_row} and column {mid_col}"

        return (FusionType.CROSS_BLAST, affected, [], description)

    def _fusion_mega_bomb(
        self,
        board: BoardState,
        pos_a: Position,
        pos_b: Position,
    ) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
        """Radial + Radial = larger explosion (5x5 by default)."""
        affected: set[Position] = set()
        width, height = board.width, board.height
        radius = self._mega_bomb_radius

        center_row = (pos_a.row + pos_b.row) // 2
        center_col = (pos_a.col + pos_b.col) // 2

        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                row = center_row + dr
                col = center_col + dc
                if 0 <= row < height and 0 <= col < width:
                    affected.add(Position(row, col))

        size = 2 * radius + 1
        description = f"Mega Bomb! {size}x{size} explosion!"

        return (FusionType.MEGA_BOMB, affected, [], description)

    def _fusion_triple_line(
        self,
        board: BoardState,
        pos_a: Position,
        pos_b: Position,
        line_type: GemType,
    ) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
        """Line + Radial = 3 adjacent rows or columns."""
        affected: set[Position] = set()
        width, height = board.width, board.height
        count = self._triple_line_count

        center_row = (pos_a.row + pos_b.row) // 2
        center_col = (pos_a.col + pos_b.col) // 2

        half = count // 2

        if line_type == GemType.LINE_BLAST_H:
            # Clear multiple rows.
            for r_offset in range(-half, half + 1):
                row = center_row + r_offset
                if 0 <= row < height:
                    for col in range(width):
                        affected.add(Position(row, col))
            description = (
                f"Triple Line clears rows "
                f"{center_row - half} to {center_row + half}"
            )
        else:
            # Clear multiple columns.
            for c_offset in range(-half, half + 1):
                col = center_col + c_offset
                if 0 <= col < width:
                    for row in range(height):
                        affected.add(Position(row, col))
            description = (
                f"Triple Line clears columns "
                f"{center_col - half} to {center_col + half}"
            )

        return (FusionType.TRIPLE_LINE, affected, [], description)

    def _fusion_color_line_blast(
        self,
        board: BoardState,
        pos_a: Position,
        pos_b: Position,
        target_color: GemType | None,
        line_type: GemType,
    ) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
        """Line + Chromatic = All gems of color become Line Blasts and activate."""
        self._validate_target_color(target_color)
        assert target_color is not None

        width, height = board.width, board.height
        affected: set[Position] = set()
        secondary_effects: list[SpecialGemEffect] = []

        # Find all gems of target color.
        color_positions: list[Position] = []
        for row in range(height):
            for col in range(width):
                pos = Position(row, col)
                if board.get(pos) == target_color:
                    color_positions.append(pos)

        # Each becomes a Line Blast and activates.
        for pos in color_positions:
            if line_type == GemType.LINE_BLAST_H:
                for col in range(width):
                    affected.add(Position(pos.row, col))
            else:
                for row in range(height):
                    affected.add(Position(row, pos.col))

            line_count = width if line_type == GemType.LINE_BLAST_H else height
            secondary_effects.append(
                SpecialGemEffect(
                    gem_type=line_type,
                    source_position=pos,
                    affected_positions=frozenset(),
                    bonus_score=self._scoring.calculate_special_gem_bonus(
                        line_type, line_count
                    ),
                    triggers_special_gems=[],
                    description=f"Line Blast at ({pos.row}, {pos.col})",
                )
            )

        color_name = GemType(target_color).name
        description = (
            f"Color Line Blast! All {color_name} gems become "
            f"Line Blasts ({len(color_positions)} total)"
        )

        return (FusionType.COLOR_LINE_BLAST, affected, secondary_effects, description)

    def _fusion_color_bomb(
        self,
        board: BoardState,
        pos_a: Position,
        pos_b: Position,
        target_color: GemType | None,
    ) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
        """Radial + Chromatic = All gems of color become Radial Bombs and activate."""
        self._validate_target_color(target_color)
        assert target_color is not None

        width, height = board.width, board.height
        radius = self._radial_bomb_radius
        affected: set[Position] = set()
        secondary_effects: list[SpecialGemEffect] = []

        # Find all gems of target color.
        color_positions: list[Position] = []
        for row in range(height):
            for col in range(width):
                pos = Position(row, col)
                if board.get(pos) == target_color:
                    color_positions.append(pos)

        # Each becomes a Radial Bomb and activates.
        for pos in color_positions:
            bomb_affected: set[Position] = set()
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    r = pos.row + dr
                    c = pos.col + dc
                    if 0 <= r < height and 0 <= c < width:
                        affected.add(Position(r, c))
                        bomb_affected.add(Position(r, c))

            secondary_effects.append(
                SpecialGemEffect(
                    gem_type=GemType.RADIAL_BOMB,
                    source_position=pos,
                    affected_positions=frozenset(bomb_affected),
                    bonus_score=self._scoring.calculate_special_gem_bonus(
                        GemType.RADIAL_BOMB, len(bomb_affected)
                    ),
                    triggers_special_gems=[],
                    description=f"Radial Bomb at ({pos.row}, {pos.col})",
                )
            )

        color_name = GemType(target_color).name
        description = (
            f"Color Bomb! All {color_name} gems become "
            f"Radial Bombs ({len(color_positions)} total)"
        )

        return (FusionType.COLOR_BOMB, affected, secondary_effects, description)

    def _fusion_board_clear(
        self,
        board: BoardState,
        pos_a: Position,
        pos_b: Position,
    ) -> tuple[FusionType, set[Position], list[SpecialGemEffect], str]:
        """Chromatic + Chromatic = clears entire board."""
        affected: set[Position] = set()
        width, height = board.width, board.height

        for row in range(height):
            for col in range(width):
                affected.add(Position(row, col))

        description = "Double Chromatic! Entire board cleared!"

        return (FusionType.BOARD_CLEAR, affected, [], description)
