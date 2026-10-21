"""Scoring module -- pure, synchronous score calculation."""

from src.modules.scoring.service import ScoringService
from src.modules.scoring.types import (
    CascadeStepScore,
    MatchGroupScore,
    MatchScore,
    MoveScore,
    SpecialGemBonus,
)

__all__ = [
    "ScoringService",
    "CascadeStepScore",
    "MatchGroupScore",
    "MatchScore",
    "MoveScore",
    "SpecialGemBonus",
]
