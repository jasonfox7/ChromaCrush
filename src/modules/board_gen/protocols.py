"""Board generation module protocols — typing.Protocol interfaces.

Defines ``BoardGenServiceProtocol`` for dependent modules, and a minimal
``BoardServiceProtocol`` covering only the methods board_gen requires.
"""

from __future__ import annotations

from typing import Protocol

from src.core.types.board import BoardState, MatchResult
from src.modules.board_gen.types import (
    BoardGenOptions,
    GeneratedBoard,
    MatchType,
)


class BoardServiceProtocol(Protocol):
    """Minimal board service interface required by board_gen."""

    def create_board(self, width: int, height: int, seed: int) -> BoardState: ...

    def detect_matches(self, board: BoardState) -> MatchResult: ...

    def validate_board(self, board: BoardState) -> bool: ...

    def has_valid_moves(self, board: BoardState) -> bool: ...


class BoardGenServiceProtocol(Protocol):
    """Protocol for the board generation service.

    Consumed by dependent modules (match) via ``__init__`` injection.
    All methods are synchronous.
    """

    def generate_board(
        self, seed: int, options: BoardGenOptions | None = None
    ) -> GeneratedBoard: ...

    def generate_board_for_match(
        self, seed: int, match_type: MatchType = MatchType.STANDARD
    ) -> GeneratedBoard: ...

    def validate_seed(self, seed: int) -> bool: ...

    def regenerate_from_deadlock(
        self, board: BoardState, seed: int
    ) -> GeneratedBoard: ...

    def calculate_cascade_potential(self, board: BoardState) -> float: ...
