"""SQLAlchemy implementation of VaultArtifactRepositoryProtocol.

All database operations flow through the injected ``DataContextProtocol``,
which provides session management (commit on success, rollback on failure).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.sql.expression import literal_column

from src.data.models.artifact_definition import ArtifactDefinitionModel
from src.data.models.vault_artifact import VaultArtifactModel

if TYPE_CHECKING:
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


@dataclass
class VaultArtifactRecord:
    """Lightweight record returned by the repository.

    The service layer maps this to VaultArtifact DTOs.
    """

    id: UUID
    owner_id: UUID
    artifact_type_id: str
    acquired_at: datetime
    source: str
    source_id: str | None
    created_at: datetime
    # Joined definition fields (optional, populated on joined queries)
    rarity: str | None = None


class SQLAlchemyVaultArtifactRepository:
    """Concrete vault artifact repository backed by PostgreSQL via SQLAlchemy.

    Satisfies ``VaultArtifactRepositoryProtocol``.
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

    async def find_by_id(self, artifact_id: UUID) -> VaultArtifactRecord | None:
        """Find an artifact by UUID."""
        self._logger.debug("Finding vault artifact by id", artifact_id=str(artifact_id))

        async with self._data_ctx.session() as session:
            stmt = select(VaultArtifactModel).where(
                VaultArtifactModel.id == artifact_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_record(model)

    async def find_by_owner(
        self,
        owner_id: UUID,
        rarity: str | None = None,
        artifact_set: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[VaultArtifactRecord], int]:
        """Find artifacts by owner with optional filters. Returns (items, total)."""
        self._logger.debug(
            "Finding artifacts by owner",
            owner_id=str(owner_id),
            rarity=rarity,
            artifact_set=artifact_set,
        )

        async with self._data_ctx.session() as session:
            # Base query with join to definitions for filtering
            base = select(VaultArtifactModel).where(
                VaultArtifactModel.owner_id == owner_id
            )

            # Apply rarity/set filters via join
            if rarity is not None or artifact_set is not None:
                base = base.join(
                    ArtifactDefinitionModel,
                    VaultArtifactModel.artifact_type_id
                    == ArtifactDefinitionModel.type_id,
                )
                if rarity is not None:
                    base = base.where(ArtifactDefinitionModel.rarity == rarity)
                if artifact_set is not None:
                    base = base.where(
                        ArtifactDefinitionModel.artifact_set == artifact_set
                    )

            # Count
            count_stmt = select(func.count()).select_from(base.subquery())
            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            # Data
            data_stmt = (
                base.order_by(VaultArtifactModel.acquired_at.desc())
                .limit(limit)
                .offset(offset)
            )
            data_result = await session.execute(data_stmt)
            models = data_result.scalars().all()

            items = [self._to_record(m) for m in models]

        return items, total

    async def count_by_owner(self, owner_id: UUID) -> int:
        """Count total artifacts owned by a player."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(func.count())
                .select_from(VaultArtifactModel)
                .where(VaultArtifactModel.owner_id == owner_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one()

    async def count_by_owner_and_rarity(self, owner_id: UUID) -> dict[str, int]:
        """Count artifacts grouped by rarity for a player."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(
                    ArtifactDefinitionModel.rarity,
                    func.count().label("cnt"),
                )
                .select_from(VaultArtifactModel)
                .join(
                    ArtifactDefinitionModel,
                    VaultArtifactModel.artifact_type_id
                    == ArtifactDefinitionModel.type_id,
                )
                .where(VaultArtifactModel.owner_id == owner_id)
                .group_by(ArtifactDefinitionModel.rarity)
            )
            result = await session.execute(stmt)
            rows = result.all()

            return {row[0]: row[1] for row in rows}

    async def find_by_owner_and_type(
        self,
        owner_id: UUID,
        artifact_type_id: str,
    ) -> VaultArtifactRecord | None:
        """Find if owner has a specific artifact type."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(VaultArtifactModel)
                .where(VaultArtifactModel.owner_id == owner_id)
                .where(VaultArtifactModel.artifact_type_id == artifact_type_id)
                .limit(1)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_record(model)

    async def list_owned_type_ids(
        self,
        owner_id: UUID,
        artifact_set: str | None = None,
    ) -> list[str]:
        """List all distinct artifact type IDs owned by player."""
        async with self._data_ctx.session() as session:
            stmt = (
                select(VaultArtifactModel.artifact_type_id)
                .where(VaultArtifactModel.owner_id == owner_id)
                .distinct()
            )

            if artifact_set is not None:
                stmt = stmt.join(
                    ArtifactDefinitionModel,
                    VaultArtifactModel.artifact_type_id
                    == ArtifactDefinitionModel.type_id,
                ).where(ArtifactDefinitionModel.artifact_set == artifact_set)

            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    async def create(
        self,
        owner_id: UUID,
        artifact_type_id: str,
        source: str,
        source_id: str | None = None,
    ) -> VaultArtifactRecord:
        """Create a new vault artifact record."""
        self._logger.debug(
            "Creating vault artifact",
            owner_id=str(owner_id),
            artifact_type_id=artifact_type_id,
            source=source,
        )

        model = VaultArtifactModel(
            owner_id=owner_id,
            artifact_type_id=artifact_type_id,
            source=source,
            source_id=source_id,
        )

        async with self._data_ctx.session() as session:
            session.add(model)
            await session.flush()
            record = self._to_record(model)

        self._logger.debug("Vault artifact created", artifact_id=str(record.id))
        return record

    async def update_owner(
        self,
        artifact_id: UUID,
        new_owner_id: UUID,
    ) -> VaultArtifactRecord:
        """Change the owner of an artifact."""
        self._logger.debug(
            "Updating artifact owner",
            artifact_id=str(artifact_id),
            new_owner_id=str(new_owner_id),
        )

        async with self._data_ctx.session() as session:
            stmt = select(VaultArtifactModel).where(
                VaultArtifactModel.id == artifact_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Artifact not found: {artifact_id}",
                    code="NOT_FOUND_ARTIFACT",
                    artifact_id=str(artifact_id),
                )

            model.owner_id = new_owner_id
            await session.flush()
            record = self._to_record(model)

        return record

    async def delete(self, artifact_id: UUID) -> None:
        """Delete an artifact record."""
        self._logger.debug("Deleting vault artifact", artifact_id=str(artifact_id))

        async with self._data_ctx.session() as session:
            stmt = select(VaultArtifactModel).where(
                VaultArtifactModel.id == artifact_id
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                raise self._errors.not_found(
                    f"Artifact not found: {artifact_id}",
                    code="NOT_FOUND_ARTIFACT",
                    artifact_id=str(artifact_id),
                )

            await session.delete(model)

        self._logger.debug("Vault artifact deleted", artifact_id=str(artifact_id))

    async def get_random_artifact(
        self,
        owner_id: UUID,
        exclude_legendary: bool = False,
    ) -> VaultArtifactRecord | None:
        """Get a random artifact from owner's vault.

        Fetches all artifacts and returns one at random (selection logic
        is in the raid engine, so this returns the full list for weighting).
        For the simple repository method, returns a single random row.
        """
        async with self._data_ctx.session() as session:
            stmt = (
                select(
                    VaultArtifactModel,
                    ArtifactDefinitionModel.rarity,
                )
                .join(
                    ArtifactDefinitionModel,
                    VaultArtifactModel.artifact_type_id
                    == ArtifactDefinitionModel.type_id,
                )
                .where(VaultArtifactModel.owner_id == owner_id)
            )

            if exclude_legendary:
                stmt = stmt.where(ArtifactDefinitionModel.rarity != "legendary")

            # Use database random ordering
            stmt = stmt.order_by(func.random()).limit(1)
            result = await session.execute(stmt)
            row = result.first()

            if row is None:
                return None

            model, rarity = row
            record = self._to_record(model)
            record.rarity = rarity
            return record

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_record(model: VaultArtifactModel) -> VaultArtifactRecord:
        """Convert an ORM model to a lightweight record."""
        return VaultArtifactRecord(
            id=model.id,
            owner_id=model.owner_id,
            artifact_type_id=model.artifact_type_id,
            acquired_at=model.acquired_at,
            source=model.source,
            source_id=model.source_id,
            created_at=model.created_at,
        )
