"""Board module — core match-3 grid logic."""

from src.modules.board.service import BoardService
from src.modules.board.types import CascadeStep, GemDrop, GemSpawn, MoveProcessingResult

__all__ = ["BoardService", "CascadeStep", "GemDrop", "GemSpawn", "MoveProcessingResult"]
