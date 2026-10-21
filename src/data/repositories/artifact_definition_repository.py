"""SQLAlchemy implementation of ArtifactDefinitionRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select

from src.data.models.artifact_definition import ArtifactDefinitionModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


@dataclass
class ArtifactDefinitionRecord:
    """Lightweight record returned by the repository."""

    type_id: str
    name: str
    description: str | None
    rarity: str
    artifact_set: str
    set_position: int
    base_value: int
    image_url: str | None
    created_at: datetime


class SQLAlchemyArtifactDefinitionRepository:
    """Concrete artifact definition repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``ArtifactDefinitionRepositoryProtocol``.
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
    # Public API
    # ------------------------------------------------------------------

    async def find_by_type_id(self, type_id: str) -> ArtifactDefinitionRecord | None:
        """Find an artifact definition by its type_id."""
        self._logger.debug("Finding artifact definition", type_id=type_id)

        async with self._data_ctx.session() as session:
            stmt = select(ArtifactDefinitionModel).where(
                ArtifactDefinitionModel.type_id == type_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_record(model)

    async def list_all(
        self,
        rarity: str | None = None,
        artifact_set: str | None = None,
    ) -> list[ArtifactDefinitionRecord]:
        """List all definitions with optional filters."""
        self._logger.debug(
            "Listing artifact definitions",
            rarity=rarity,
            artifact_set=artifact_set,
        )

        async with self._data_ctx.session() as session:
            stmt = select(ArtifactDefinitionModel)

            if rarity is not None:
                stmt = stmt.where(ArtifactDefinitionModel.rarity == rarity)
            if artifact_set is not None:
                stmt = stmt.where(ArtifactDefinitionModel.artifact_set == artifact_set)

            stmt = stmt.order_by(
                ArtifactDefinitionModel.artifact_set,
                ArtifactDefinitionModel.set_position,
            )

            result = await session.execute(stmt)
            models = result.scalars().all()

            return [self._to_record(m) for m in models]

    async def list_by_set(self, artifact_set: str) -> list[ArtifactDefinitionRecord]:
        """List all definitions in a specific artifact set."""
        return await self.list_all(artifact_set=artifact_set)

    async def get_set_type_ids(self, artifact_set: str) -> list[str]:
        """Get all type IDs belonging to a set."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(ArtifactDefinitionModel.type_id)
                .where(ArtifactDefinitionModel.artifact_set == artifact_set)
                .order_by(ArtifactDefinitionModel.set_position)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    async def list_all_sets(self) -> list[str]:
        """List all unique artifact set names."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(ArtifactDefinitionModel.artifact_set)
                .distinct()
                .order_by(ArtifactDefinitionModel.artifact_set)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_record(model: ArtifactDefinitionModel) -> ArtifactDefinitionRecord:
        """Convert an ORM model to a lightweight record."""
        return ArtifactDefinitionRecord(
            type_id=model.type_id,
            name=model.name,
            description=model.description,
            rarity=model.rarity,
            artifact_set=model.artifact_set,
            set_position=model.set_position,
            base_value=model.base_value,
            image_url=model.image_url,
            created_at=model.created_at,
        )
