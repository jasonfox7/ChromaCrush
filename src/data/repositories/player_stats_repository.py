"""SQLAlchemy implementation of PlayerStatsRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select

from src.core.types.game import PlayerId
from src.core.types.player import PlayerStats
from src.data.models.player import PlayerModel
from src.data.models.player_stats import PlayerStatsModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


class SQLAlchemyPlayerStatsRepository:
    """Concrete player statistics repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``PlayerStatsRepositoryProtocol``. Created in the composition root
    and injected into services that need player statistics data access.
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
    # Public API (matches PlayerStatsRepositoryProtocol)
    # ------------------------------------------------------------------

    async def find_by_player_id(self, player_id: UUID) -> PlayerStats | None:
        """Find player statistics by player UUID.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The ``PlayerStats`` domain object, or ``None`` if not found.
        """
        self._logger.debug(
            "Finding player stats by player_id", player_id=str(player_id)
        )

        async with self._data_ctx.session() as session:
            stmt = select(PlayerStatsModel).where(
                PlayerStatsModel.player_id == player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                self._logger.debug("Player stats not found", player_id=str(player_id))
                return None

            return self._to_domain(model)

    async def create(self, player_id: UUID) -> PlayerStats:
        """Create a new player statistics record with default values.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The newly created ``PlayerStats`` domain object.
        """
        self._logger.debug("Creating player stats", player_id=str(player_id))

        model = PlayerStatsModel(player_id=player_id)

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            stats = self._to_domain(model)

        self._logger.debug("Player stats created", player_id=str(player_id))

        return stats

    async def update(self, player_id: UUID, **changes: object) -> PlayerStats:
        """Update an existing player's statistics.

        Args:
            player_id: The player's unique identifier.
            **changes: Keyword arguments of field names and new values.

        Returns:
            The updated ``PlayerStats`` domain object.

        Raises:
            AppError (NOT_FOUND_PLAYER): If the player stats do not exist.
        """
        self._logger.debug(
            "Updating player stats",
            player_id=str(player_id),
            changes=str(list(changes.keys())),
        )

        async with self._data_ctx.session() as session:
            stmt = select(PlayerStatsModel).where(
                PlayerStatsModel.player_id == player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Player stats not found: {player_id}",
                    code="NOT_FOUND_PLAYER",
                    player_id=str(player_id),
                )

            for key, value in changes.items():
                if not hasattr(model, key):
                    raise self._errors.validation(
                        f"Invalid player stats attribute: {key}",
                        code="VALIDATION_INVALID_ATTRIBUTE",
                        attribute=key,
                    )
                setattr(model, key, value)

            await session.flush()
            stats = self._to_domain(model)

        self._logger.debug("Player stats updated", player_id=str(player_id))

        return stats

    async def list_by_highest_score(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[tuple[PlayerStats, str, int]], int]:
        """List players ranked by highest_score descending.

        Returns:
            Tuple of (list of (PlayerStats, username, elo_rating), total_count).
        """
        async with self._data_ctx.session() as session:
            base_filter = PlayerModel.deleted_at.is_(None)

            count_stmt = (
                select(func.count())
                .select_from(PlayerStatsModel)
                .join(PlayerModel, PlayerModel.id == PlayerStatsModel.player_id)
                .where(base_filter)
            )
            total = (await session.execute(count_stmt)).scalar_one()

            stmt = (
                select(PlayerStatsModel, PlayerModel.username, PlayerModel.elo_rating)
                .join(PlayerModel, PlayerModel.id == PlayerStatsModel.player_id)
                .where(base_filter)
                .order_by(PlayerStatsModel.highest_score.desc())
                .limit(limit)
                .offset(offset)
            )
            rows = (await session.execute(stmt)).all()

            items = [
                (self._to_domain(row[0]), row[1], row[2]) for row in rows
            ]

        return items, total

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(model: PlayerStatsModel) -> PlayerStats:
        """Convert a ``PlayerStatsModel`` ORM instance to a ``PlayerStats`` domain object.

        Args:
            model: The SQLAlchemy ORM model instance.

        Returns:
            A ``PlayerStats`` dataclass with values copied from the model.
        """
        return PlayerStats(
            player_id=PlayerId(model.player_id),
            total_matches=model.total_matches,
            wins=model.wins,
            losses=model.losses,
            draws=model.draws,
            highest_score=model.highest_score,
            longest_chain=model.longest_chain,
            total_gems_matched=model.total_gems_matched,
        )
