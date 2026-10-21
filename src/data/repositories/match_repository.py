"""SQLAlchemy implementations of match repository protocols.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, or_, select, text
from sqlalchemy import update as sa_update

from src.data.models.match import MatchModel
from src.data.models.match_move import MatchMoveModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.match.dto import MatchCreate, MatchUpdate, MoveCreate


class SQLAlchemyMatchRepository:
    """Concrete match repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``MatchRepositoryProtocol``. Created in the composition root
    and injected into services that need match data access.
    """

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    # ------------------------------------------------------------------
    # Public API (matches MatchRepositoryProtocol)
    # ------------------------------------------------------------------

    async def create(self, data: MatchCreate) -> MatchModel:
        """Create a new match.

        Args:
            data: MatchCreate DTO with match initialization data.

        Returns:
            The newly created ``MatchModel`` ORM instance.
        """
        self._logger.debug(
            "Creating match",
            player1_id=str(data.player1_id),
            player2_id=str(data.player2_id),
            match_type=data.match_type,
        )

        model = MatchModel(
            board_seed=data.board_seed,
            initial_board_state=data.initial_board_state,
            match_type=data.match_type,
            player1_id=data.player1_id,
            player1_board_state=data.player1_board_state,
            player1_moves_remaining=data.player1_moves_remaining,
            player2_id=data.player2_id,
            player2_board_state=data.player2_board_state,
            player2_moves_remaining=data.player2_moves_remaining,
            timeout_at=data.timeout_at,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()  # Populate defaults (id, created_at)

        self._logger.debug(
            "Match created",
            match_id=str(model.id),
        )

        return model

    async def find_by_id(self, match_id: UUID) -> MatchModel | None:
        """Find a match by its UUID.

        Args:
            match_id: The match's unique identifier.

        Returns:
            The ``MatchModel`` ORM instance, or ``None`` if not found.
        """
        self._logger.debug("Finding match by id", match_id=str(match_id))

        async with self._data_ctx.session() as session:
            stmt = select(MatchModel).where(MatchModel.id == match_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                self._logger.debug("Match not found by id", match_id=str(match_id))
                return None

            return model

    async def update(self, match_id: UUID, changes: MatchUpdate) -> MatchModel:
        """Update an existing match's attributes.

        Args:
            match_id: The match's unique identifier.
            changes: MatchUpdate DTO with fields to update.

        Returns:
            The updated ``MatchModel`` ORM instance.

        Raises:
            AppError (NOT_FOUND_RESOURCE): If the match does not exist.
        """
        self._logger.debug(
            "Updating match",
            match_id=str(match_id),
        )

        async with self._data_ctx.session() as session:
            stmt = select(MatchModel).where(MatchModel.id == match_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Match not found: {match_id}",
                    code="NOT_FOUND_MATCH",
                    match_id=str(match_id),
                )

            # Apply non-None changes from the DTO
            for f in dataclasses.fields(changes):
                value = getattr(changes, f.name)
                if value is not None and hasattr(model, f.name):
                    setattr(model, f.name, value)

            await session.flush()

        self._logger.debug(
            "Match updated",
            match_id=str(model.id),
        )

        return model

    async def find_active_by_player(self, player_id: UUID) -> list[MatchModel]:
        """Find all active matches for a player.

        Returns matches where status is 'pending' or 'in_progress' and
        the player is either player1 or player2.

        Args:
            player_id: The player's unique identifier.

        Returns:
            List of active ``MatchModel`` instances (may be empty).
        """
        self._logger.debug(
            "Finding active matches for player", player_id=str(player_id)
        )

        async with self._data_ctx.session() as session:
            stmt = (
                select(MatchModel)
                .where(
                    or_(
                        MatchModel.player1_id == player_id,
                        MatchModel.player2_id == player_id,
                    )
                )
                .where(MatchModel.status.in_(["pending", "in_progress"]))
            )
            result = await session.execute(stmt)
            models = result.scalars().all()

        self._logger.debug(
            "Found active matches",
            player_id=str(player_id),
            count=len(models),
        )

        return list(models)

    async def find_by_player(
        self,
        player_id: UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[MatchModel], int]:
        """Find matches involving a player with optional status filter and pagination.

        Args:
            player_id: The player's unique identifier.
            status: Optional status filter (e.g., "completed", "abandoned").
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            Tuple of (items, total_count).
        """
        self._logger.debug(
            "Finding matches for player",
            player_id=str(player_id),
            status=status,
            limit=limit,
            offset=offset,
        )

        async with self._data_ctx.session() as session:
            # Build base filter
            base_filter = or_(
                MatchModel.player1_id == player_id,
                MatchModel.player2_id == player_id,
            )

            if status is not None:
                base_filter = base_filter & (MatchModel.status == status)

            # Count query
            count_stmt = select(func.count()).select_from(MatchModel).where(base_filter)
            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            # Data query
            data_stmt = (
                select(MatchModel)
                .where(base_filter)
                .order_by(MatchModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            data_result = await session.execute(data_stmt)
            models = data_result.scalars().all()

        return list(models), total

    async def find_stale_matches(self, cutoff: datetime) -> list[MatchModel]:
        """Find matches that are in-progress but have exceeded their timeout deadline.

        Args:
            cutoff: Timestamp threshold -- matches with timeout_at < cutoff are stale.

        Returns:
            List of stale ``MatchModel`` instances.
        """
        self._logger.debug("Finding stale matches", cutoff=cutoff.isoformat())

        async with self._data_ctx.session() as session:
            stmt = (
                select(MatchModel)
                .where(MatchModel.status == "in_progress")
                .where(MatchModel.timeout_at < cutoff)
            )
            result = await session.execute(stmt)
            models = result.scalars().all()

        self._logger.debug(
            "Found stale matches",
            count=len(models),
        )

        return list(models)

    async def bulk_abandon(self, match_ids: list[UUID]) -> int:
        """Mark multiple matches as abandoned.

        Updates the status to 'abandoned' for all provided match IDs.

        Args:
            match_ids: List of match UUIDs to abandon.

        Returns:
            Number of matches updated.
        """
        if not match_ids:
            return 0

        self._logger.debug(
            "Bulk abandoning matches",
            count=len(match_ids),
        )

        async with self._data_ctx.session() as session:
            stmt = (
                sa_update(MatchModel)
                .where(MatchModel.id.in_(match_ids))
                .values(status="abandoned")
            )
            result = await session.execute(stmt)
            rowcount = result.rowcount or 0

        self._logger.debug(
            "Bulk abandon complete",
            updated_count=rowcount,
        )

        return rowcount

    async def cleanup_match_data(self, match_id: UUID) -> None:
        """NULL out board states and raid data for a completed match.

        Called after the final match state has been served to the client.
        Preserves metadata (scores, winner, timestamps) for match history.

        Args:
            match_id: The match to clean up.
        """
        self._logger.debug("Cleaning up match data", match_id=str(match_id))

        async with self._data_ctx.session() as session:
            await session.execute(
                text(
                    "UPDATE matches SET "
                    "initial_board_state = NULL, "
                    "player1_board_state = NULL, "
                    "player2_board_state = NULL, "
                    "raid_data = NULL, "
                    "reward_data = NULL "
                    "WHERE id = :mid"
                ),
                {"mid": str(match_id)},
            )

        self._logger.debug("Match data cleaned up", match_id=str(match_id))


class SQLAlchemyMatchMoveRepository:
    """Concrete match move repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``MatchMoveRepositoryProtocol``. Created in the composition root
    and injected into services that need match move data access.
    """

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    # ------------------------------------------------------------------
    # Public API (matches MatchMoveRepositoryProtocol)
    # ------------------------------------------------------------------

    async def create(self, data: MoveCreate) -> MatchMoveModel:
        """Record a new move in a match.

        Args:
            data: MoveCreate DTO with move details.

        Returns:
            The newly created ``MatchMoveModel`` ORM instance.
        """
        self._logger.debug(
            "Creating match move",
            match_id=str(data.match_id),
            player_id=str(data.player_id),
            move_number=data.move_number,
        )

        model = MatchMoveModel(
            match_id=data.match_id,
            player_id=data.player_id,
            move_number=data.move_number,
            from_row=data.from_row,
            from_col=data.from_col,
            to_row=data.to_row,
            to_col=data.to_col,
            client_timestamp_ms=data.client_timestamp_ms,
            board_before=data.board_before,
            board_after=data.board_after,
            score_earned=data.score_earned,
            chain_count=data.chain_count,
            gems_cleared=data.gems_cleared,
            special_gems_created=data.special_gems_created,
            special_gems_activated=data.special_gems_activated,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()

        self._logger.debug(
            "Match move created",
            move_id=str(model.id),
        )

        return model

    async def find_by_match(
        self,
        match_id: UUID,
        player_id: UUID | None = None,
    ) -> list[MatchMoveModel]:
        """Find all moves for a match, optionally filtered by player.

        Results are ordered by move_number ascending.

        Args:
            match_id: The match's unique identifier.
            player_id: Optional player filter -- if provided, only return moves by this player.

        Returns:
            List of ``MatchMoveModel`` instances (may be empty).
        """
        self._logger.debug(
            "Finding moves for match",
            match_id=str(match_id),
            player_id=str(player_id) if player_id else None,
        )

        async with self._data_ctx.session() as session:
            stmt = select(MatchMoveModel).where(MatchMoveModel.match_id == match_id)

            if player_id is not None:
                stmt = stmt.where(MatchMoveModel.player_id == player_id)

            stmt = stmt.order_by(MatchMoveModel.move_number.asc())

            result = await session.execute(stmt)
            models = result.scalars().all()

        return list(models)

    async def count_by_player(self, match_id: UUID, player_id: UUID) -> int:
        """Count the number of moves a player has made in a match.

        Args:
            match_id: The match's unique identifier.
            player_id: The player's unique identifier.

        Returns:
            Move count for the player in this match.
        """
        self._logger.debug(
            "Counting moves for player in match",
            match_id=str(match_id),
            player_id=str(player_id),
        )

        async with self._data_ctx.session() as session:
            stmt = (
                select(func.count())
                .select_from(MatchMoveModel)
                .where(MatchMoveModel.match_id == match_id)
                .where(MatchMoveModel.player_id == player_id)
            )
            result = await session.execute(stmt)
            count = result.scalar_one()

        return count

    async def delete_by_match_id(self, match_id: UUID) -> int:
        """Delete all move records for a match.

        Called during post-match cleanup to reclaim storage.

        Args:
            match_id: The match whose moves should be deleted.

        Returns:
            Number of move records deleted.
        """
        self._logger.debug("Deleting moves for match", match_id=str(match_id))

        async with self._data_ctx.session() as session:
            stmt = sa_delete(MatchMoveModel).where(MatchMoveModel.match_id == match_id)
            result = await session.execute(stmt)
            rowcount = result.rowcount or 0

        self._logger.debug(
            "Moves deleted",
            match_id=str(match_id),
            count=rowcount,
        )

        return rowcount
