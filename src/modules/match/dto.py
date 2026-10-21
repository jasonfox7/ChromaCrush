"""Data Transfer Objects for the match module.

DTOs for database operations, repository layer, and API serialization.
All DTOs use primitive JSON-serializable types (no domain objects).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.types.pagination import PaginatedResult as PaginatedResult  # noqa: F401


@dataclass
class MatchCreate:
    """Data for creating a new match record.

    All fields required. Board states stored as JSON-serializable lists.
    """

    board_seed: int
    initial_board_state: (
        Any  # [[int]] (legacy) or {"cells": [[int]], "functions": [[int]]}
    )
    match_type: str
    player1_id: UUID
    player1_board_state: Any  # same as above
    player1_moves_remaining: int
    player2_id: UUID
    player2_board_state: Any  # same as above
    player2_moves_remaining: int
    timeout_at: datetime


@dataclass
class MatchUpdate:
    """Optional fields for updating a match record.

    All fields are optional. Only non-None fields will be updated in the
    database. Use this pattern to distinguish "not set" from "set to None".
    """

    status: str | None = None
    player1_board_state: Any | None = (
        None  # [[int]] or {"cells": ..., "functions": ...}
    )
    player1_score: int | None = None
    player1_moves_made: int | None = None
    player1_moves_remaining: int | None = None
    player1_longest_chain: int | None = None
    player1_finished_at: datetime | None = field(default=None)
    player2_board_state: Any | None = (
        None  # [[int]] or {"cells": ..., "functions": ...}
    )
    player2_score: int | None = None
    player2_moves_made: int | None = None
    player2_moves_remaining: int | None = None
    player2_longest_chain: int | None = None
    player2_finished_at: datetime | None = field(default=None)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    winner_id: UUID | None = None
    forfeit_by: UUID | None = None
    raid_data: dict | None = None
    reward_data: dict | None = None


@dataclass
class MoveCreate:
    """Data for creating a move record.

    All fields required. Stores complete move history for replay and analysis.
    """

    match_id: UUID
    player_id: UUID
    move_number: int
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    client_timestamp_ms: int
    board_before: Any  # [[int]] or {"cells": ..., "functions": ...}
    board_after: Any  # [[int]] or {"cells": ..., "functions": ...}
    score_earned: int
    chain_count: int
    gems_cleared: int
    special_gems_created: list  # JSON-serializable list of {row, col, gem_type}
    special_gems_activated: list  # JSON-serializable list of {row, col}
