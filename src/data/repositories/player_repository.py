"""SQLAlchemy implementation of PlayerRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select

from src.core.types.game import PlayerId
from src.core.types.player import Player, PlayerType
from src.data.models.player import PlayerModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


class SQLAlchemyPlayerRepository:
    """Concrete player repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``PlayerRepositoryProtocol``. Created in the composition root
    and injected into services that need player data access.
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
    # Public API (matches PlayerRepositoryProtocol)
    # ------------------------------------------------------------------

    async def find_by_id(self, player_id: UUID) -> Player | None:
        """Find a player by their UUID.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The ``Player`` domain object, or ``None`` if not found.
        """
        self._logger.debug("Finding player by id", player_id=str(player_id))

        async with self._data_ctx.session() as session:
            stmt = select(PlayerModel).where(PlayerModel.id == player_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                self._logger.debug("Player not found by id", player_id=str(player_id))
                return None

            return self._to_domain(model)

    async def find_by_username(self, username: str) -> Player | None:
        """Find a player by their unique username.

        Args:
            username: The player's display name.

        Returns:
            The ``Player`` domain object, or ``None`` if not found.
        """
        self._logger.debug("Finding player by username", username=username)

        async with self._data_ctx.session() as session:
            stmt = select(PlayerModel).where(PlayerModel.username == username)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                self._logger.debug("Player not found by username", username=username)
                return None

            return self._to_domain(model)

    async def find_by_apple_user_id(self, apple_user_id: str) -> Player | None:
        """Find a player by their Apple user ID.

        Args:
            apple_user_id: The Apple ``sub`` claim.

        Returns:
            The ``Player`` domain object, or ``None`` if not found.
        """
        self._logger.debug("Finding player by apple_user_id")

        async with self._data_ctx.session() as session:
            stmt = select(PlayerModel).where(
                PlayerModel.apple_user_id == apple_user_id,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_domain(model)

    async def create(
        self,
        username: str,
        player_type: PlayerType,
        password_hash: str | None = None,
        apple_user_id: str | None = None,
        auth_provider: str | None = None,
    ) -> Player:
        """Create a new player.

        Args:
            username: Unique display name for the player.
            player_type: ``PlayerType.HUMAN`` or ``PlayerType.BOT``.
            password_hash: Bcrypt hash (optional for bots).
            apple_user_id: Apple Sign-In ``sub`` claim (optional).
            auth_provider: Authentication method (``"password"``, ``"apple"``).

        Returns:
            The newly created ``Player`` domain object.
        """
        self._logger.debug(
            "Creating player",
            username=username,
            player_type=player_type.value,
        )

        model = PlayerModel(
            username=username,
            username_lower=username.lower(),
            player_type=player_type.value,
            password_hash=password_hash,
            apple_user_id=apple_user_id,
            auth_provider=auth_provider or "password",
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()  # Populate defaults (id, created_at)

            player = self._to_domain(model)

        self._logger.debug(
            "Player created",
            player_id=str(player.id),
            username=player.username,
        )

        return player

    async def update(self, player_id: UUID, **changes: Any) -> Player:
        """Update an existing player's attributes.

        Args:
            player_id: The player's unique identifier.
            **changes: Keyword arguments of column names and new values.

        Returns:
            The updated ``Player`` domain object.

        Raises:
            AppError (NOT_FOUND_RESOURCE): If the player does not exist.
        """
        self._logger.debug(
            "Updating player",
            player_id=str(player_id),
            changes=str(list(changes.keys())),
        )

        async with self._data_ctx.session() as session:
            stmt = select(PlayerModel).where(PlayerModel.id == player_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Player not found: {player_id}",
                    code="NOT_FOUND_PLAYER",
                    player_id=str(player_id),
                )

            # Apply each change to the model.
            for key, value in changes.items():
                if not hasattr(model, key):
                    raise self._errors.validation(
                        f"Invalid player attribute: {key}",
                        code="VALIDATION_INVALID_ATTRIBUTE",
                        attribute=key,
                    )
                setattr(model, key, value)

            await session.flush()
            player = self._to_domain(model)

        self._logger.debug(
            "Player updated",
            player_id=str(player.id),
        )

        return player

    async def delete(self, player_id: UUID) -> None:
        """Delete a player by their UUID.

        Args:
            player_id: The player's unique identifier.

        Raises:
            AppError (NOT_FOUND_RESOURCE): If the player does not exist.
        """
        self._logger.debug("Deleting player", player_id=str(player_id))

        async with self._data_ctx.session() as session:
            stmt = select(PlayerModel).where(PlayerModel.id == player_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Player not found: {player_id}",
                    code="NOT_FOUND_PLAYER",
                    player_id=str(player_id),
                )

            await session.delete(model)

        self._logger.debug(
            "Player deleted",
            player_id=str(player_id),
        )

    async def list_players(
        self,
        player_type: PlayerType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Player], int]:
        """List players with optional type filtering and pagination.

        Args:
            player_type: Filter by ``PlayerType.HUMAN`` or ``PlayerType.BOT``
                (``None`` for all).
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            Tuple of (items, total_count).
        """
        self._logger.debug(
            "Listing players",
            player_type=player_type.value if player_type else "all",
            limit=limit,
            offset=offset,
        )

        async with self._data_ctx.session() as session:
            # Build base query — exclude soft-deleted players
            base_filter = PlayerModel.deleted_at.is_(None)

            if player_type is not None:
                base_filter = base_filter & (
                    PlayerModel.player_type == player_type.value
                )

            # Count query
            count_stmt = (
                select(func.count()).select_from(PlayerModel).where(base_filter)
            )
            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            # Data query
            data_stmt = (
                select(PlayerModel)
                .where(base_filter)
                .order_by(PlayerModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            data_result = await session.execute(data_stmt)
            models = data_result.scalars().all()

            items = [self._to_domain(m) for m in models]

        return items, total

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(model: PlayerModel) -> Player:
        """Convert a ``PlayerModel`` ORM instance to a ``Player`` domain object.

        Args:
            model: The SQLAlchemy ORM model instance.

        Returns:
            A ``Player`` dataclass with values copied from the model.
        """
        return Player(
            id=PlayerId(model.id),
            username=model.username,
            player_type=PlayerType(model.player_type),
            elo_rating=model.elo_rating,
            campaign_level=model.campaign_level,
            created_at=model.created_at,
        )
