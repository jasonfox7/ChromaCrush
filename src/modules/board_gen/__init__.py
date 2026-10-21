"""Board generation module — procedural, deterministic board creation."""

from src.modules.board_gen.protocols import BoardGenServiceProtocol
from src.modules.board_gen.service import BoardGenService
from src.modules.board_gen.types import (
    BoardGenOptions,
    GeneratedBoard,
    GenerationMetadata,
    MatchType,
    StartingSpecial,
)

__all__ = [
    "BoardGenService",
    "BoardGenServiceProtocol",
    "BoardGenOptions",
    "GeneratedBoard",
    "GenerationMetadata",
    "MatchType",
    "StartingSpecial",
]
