"""SQLAlchemy implementation of EnergyStateRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from src.core.types.game import PlayerId
from src.core.types.player import EnergyState
from src.data.models.energy_state import EnergyStateModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


class SQLAlchemyEnergyStateRepository:
    """Concrete energy state repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``EnergyStateRepositoryProtocol``. Created in the composition root
    and injected into services that need energy state data access.
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
    # Public API (matches EnergyStateRepositoryProtocol)
    # ------------------------------------------------------------------

    async def find_by_player_id(self, player_id: UUID) -> EnergyState | None:
        """Find energy state by player UUID.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The ``EnergyState`` domain object, or ``None`` if not found.
        """
        self._logger.debug(
            "Finding energy state by player_id", player_id=str(player_id)
        )

        async with self._data_ctx.session() as session:
            stmt = select(EnergyStateModel).where(
                EnergyStateModel.player_id == player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                self._logger.debug("Energy state not found", player_id=str(player_id))
                return None

            return self._to_domain(model)

    async def create(
        self,
        player_id: UUID,
        hearts: int,
        max_hearts: int,
    ) -> EnergyState:
        """Create a new energy state record.

        Args:
            player_id: The player's unique identifier.
            hearts: Initial hearts count.
            max_hearts: Maximum hearts capacity.

        Returns:
            The newly created ``EnergyState`` domain object.
        """
        self._logger.debug(
            "Creating energy state",
            player_id=str(player_id),
            hearts=hearts,
            max_hearts=max_hearts,
        )

        model = EnergyStateModel(
            player_id=player_id,
            hearts=hearts,
            max_hearts=max_hearts,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            energy_state = self._to_domain(model)

        self._logger.debug("Energy state created", player_id=str(player_id))

        return energy_state

    async def update(self, player_id: UUID, **changes: object) -> EnergyState:
        """Update an existing player's energy state.

        Args:
            player_id: The player's unique identifier.
            **changes: Keyword arguments of field names and new values.

        Returns:
            The updated ``EnergyState`` domain object.

        Raises:
            AppError (NOT_FOUND_PLAYER): If the energy state does not exist.
        """
        self._logger.debug(
            "Updating energy state",
            player_id=str(player_id),
            changes=str(list(changes.keys())),
        )

        async with self._data_ctx.session() as session:
            stmt = select(EnergyStateModel).where(
                EnergyStateModel.player_id == player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Energy state not found: {player_id}",
                    code="NOT_FOUND_PLAYER",
                    player_id=str(player_id),
                )

            for key, value in changes.items():
                if not hasattr(model, key):
                    raise self._errors.validation(
                        f"Invalid energy state attribute: {key}",
                        code="VALIDATION_INVALID_ATTRIBUTE",
                        attribute=key,
                    )
                setattr(model, key, value)

            await session.flush()
            energy_state = self._to_domain(model)

        self._logger.debug("Energy state updated", player_id=str(player_id))

        return energy_state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(model: EnergyStateModel) -> EnergyState:
        """Convert an ``EnergyStateModel`` ORM instance to an ``EnergyState`` domain object.

        Args:
            model: The SQLAlchemy ORM model instance.

        Returns:
            An ``EnergyState`` dataclass with values copied from the model.
        """
        return EnergyState(
            player_id=PlayerId(model.player_id),
            hearts=model.hearts,
            max_hearts=model.max_hearts,
            last_regen_at=model.last_regen_at,
            daily_streak=model.daily_streak,
            last_login_date=model.last_login_date,
        )
