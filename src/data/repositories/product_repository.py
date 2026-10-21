"""SQLAlchemy implementation of product repository."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.data.models.product import ProductModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


class SQLAlchemyProductRepository:
    """Concrete product repository backed by PostgreSQL."""

    def __init__(
        self,
        data_ctx: DataContextProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> None:
        self._data_ctx = data_ctx
        self._logger = logger
        self._errors = errors

    async def find_by_id(self, product_id: str) -> ProductModel | None:
        async with self._data_ctx.session() as session:
            stmt = select(ProductModel).where(ProductModel.id == product_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def find_all_active(self) -> list[ProductModel]:
        async with self._data_ctx.session() as session:
            stmt = (
                select(ProductModel)
                .where(
                    ProductModel.is_active.is_(True),
                )
                .order_by(ProductModel.name)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
