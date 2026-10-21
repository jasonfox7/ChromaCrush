"""Match module — asynchronous versus match coordination.

Coordinates two-player asynchronous matches, handling move submission,
board state synchronization, scoring, and match lifecycle management.
"""

from src.modules.match.protocols import MatchServiceProtocol
from src.modules.match.types import (
    MatchState,
    MatchStatus,
    MatchSummary,
    MatchType,
    MoveRecord,
    MoveSubmissionResult,
    PlayerBoardState,
    PlayerMatchState,
)

from src.modules.match.service import MatchRepositoryBundle, MatchService

__all__ = [
    "MatchRepositoryBundle",
    "MatchService",
    "MatchServiceProtocol",
    "MatchState",
    "MatchStatus",
    "MatchSummary",
    "MatchType",
    "MoveRecord",
    "MoveSubmissionResult",
    "PlayerBoardState",
    "PlayerMatchState",
]
