"""Repository protocol for campaign attempt data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.campaign_attempt_repository``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass
class CampaignAttemptRecord:
    """Lightweight record returned by the campaign attempt repository."""

    id: UUID
    player_id: UUID
    level_number: int
    board_seed: int
    board_state: dict | None
    moves_remaining: int
    obstacles_remaining: int
    status: str
    score: int


class CampaignAttemptRepositoryProtocol(Protocol):
    """Async repository interface for campaign attempt persistence."""

    async def create(
        self,
        player_id: UUID,
        level_number: int,
        board_seed: int,
        board_state: dict,
        moves_remaining: int,
        obstacles_remaining: int,
    ) -> CampaignAttemptRecord:
        """Create a new campaign attempt.

        Args:
            player_id: The player starting the attempt.
            level_number: Campaign level being attempted.
            board_seed: RNG seed for board generation.
            board_state: Initial board state (cells + functions).
            moves_remaining: Starting move budget.
            obstacles_remaining: Number of obstacles on the board.

        Returns:
            The newly created attempt record.
        """
        ...

    async def find_by_id(self, attempt_id: UUID) -> CampaignAttemptRecord | None:
        """Find an attempt by its UUID.

        Args:
            attempt_id: The attempt's unique identifier.

        Returns:
            The record, or ``None`` if not found.
        """
        ...

    async def find_active_by_player(
        self, player_id: UUID
    ) -> CampaignAttemptRecord | None:
        """Find the player's current in-progress attempt (if any).

        Args:
            player_id: The player's unique identifier.

        Returns:
            The active attempt, or ``None`` if none in progress.
        """
        ...

    async def update(
        self,
        attempt_id: UUID,
        *,
        board_state: dict | None = None,
        moves_remaining: int | None = None,
        obstacles_remaining: int | None = None,
        status: str | None = None,
        score: int | None = None,
    ) -> CampaignAttemptRecord:
        """Update fields on an existing attempt.

        Args:
            attempt_id: The attempt to update.
            board_state: New board state (if changed).
            moves_remaining: New moves remaining (if changed).
            obstacles_remaining: New obstacle count (if changed).
            status: New status (if changed).
            score: New cumulative score (if changed).

        Returns:
            The updated record.

        Raises:
            AppError (NOT_FOUND): If attempt not found.
        """
        ...

    async def find_stale_attempts(self, cutoff: datetime) -> list[UUID]:
        """Find in-progress attempts started before *cutoff*.

        Args:
            cutoff: Attempts with ``started_at`` before this are stale.

        Returns:
            List of stale attempt UUIDs.
        """
        ...

    async def bulk_abandon(self, attempt_ids: list[UUID]) -> int:
        """Mark multiple attempts as abandoned.

        Args:
            attempt_ids: Attempt UUIDs to abandon.

        Returns:
            Number of rows updated.
        """
        ...
