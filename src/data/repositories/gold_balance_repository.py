"""SQLAlchemy implementation of GoldBalanceRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from src.data.models.gold_balance import GoldBalanceModel
from src.data.protocols.gold_balance_repository import GoldBalanceRecord

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


class SQLAlchemyGoldBalanceRepository:
    """Concrete gold balance repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``GoldBalanceRepositoryProtocol``. Created in the composition
    root and injected into the economy service.
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
    # Public API (matches GoldBalanceRepositoryProtocol)
    # ------------------------------------------------------------------

    async def find_by_player_id(self, player_id: UUID) -> GoldBalanceRecord | None:
        """Find gold balance by player UUID."""
        self._logger.debug(
            "Finding gold balance by player_id", player_id=str(player_id)
        )

        async with self._data_ctx.session() as session:
            stmt = select(GoldBalanceModel).where(
                GoldBalanceModel.player_id == player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                self._logger.debug("Gold balance not found", player_id=str(player_id))
                return None

            return self._to_record(model)

    async def create(self, player_id: UUID) -> GoldBalanceRecord:
        """Create a new gold balance record with zero balance."""
        self._logger.debug("Creating gold balance", player_id=str(player_id))

        model = GoldBalanceModel(
            player_id=player_id,
            balance=0,
            lifetime_earned=0,
            lifetime_spent=0,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            record = self._to_record(model)

        self._logger.debug("Gold balance created", player_id=str(player_id))
        return record

    async def credit(self, player_id: UUID, amount: int) -> GoldBalanceRecord:
        """Add gold to a player's balance."""
        self._logger.debug(
            "Crediting gold",
            player_id=str(player_id),
            amount=amount,
        )

        async with self._data_ctx.session() as session:
            stmt = select(GoldBalanceModel).where(
                GoldBalanceModel.player_id == player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Gold balance not found: {player_id}",
                    code="NOT_FOUND_ECONOMY",
                    player_id=str(player_id),
                )

            model.balance += amount
            model.lifetime_earned += amount
            await session.flush()
            record = self._to_record(model)

        self._logger.debug(
            "Gold credited",
            player_id=str(player_id),
            amount=amount,
            new_balance=record.balance,
        )
        return record

    async def debit(self, player_id: UUID, amount: int) -> GoldBalanceRecord:
        """Remove gold from a player's balance."""
        self._logger.debug(
            "Debiting gold",
            player_id=str(player_id),
            amount=amount,
        )

        async with self._data_ctx.session() as session:
            stmt = select(GoldBalanceModel).where(
                GoldBalanceModel.player_id == player_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Gold balance not found: {player_id}",
                    code="NOT_FOUND_ECONOMY",
                    player_id=str(player_id),
                )

            if model.balance < amount:
                raise self._errors.forbidden(
                    f"Insufficient gold: have {model.balance}, need {amount}",
                    code="INSUFFICIENT_GOLD",
                    player_id=str(player_id),
                    balance=model.balance,
                    required=amount,
                )

            model.balance -= amount
            model.lifetime_spent += amount
            await session.flush()
            record = self._to_record(model)

        self._logger.debug(
            "Gold debited",
            player_id=str(player_id),
            amount=amount,
            new_balance=record.balance,
        )
        return record

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_record(model: GoldBalanceModel) -> GoldBalanceRecord:
        """Convert an ORM model to a lightweight record."""
        return GoldBalanceRecord(
            player_id=model.player_id,
            balance=model.balance,
            lifetime_earned=model.lifetime_earned,
            lifetime_spent=model.lifetime_spent,
        )
