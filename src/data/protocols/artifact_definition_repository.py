"""Repository protocol for artifact definition data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.artifact_definition_repository``.
"""

from __future__ import annotations

from typing import Any, Protocol


class ArtifactDefinitionRepositoryProtocol(Protocol):
    """Async repository interface for the artifact catalog."""

    async def find_by_type_id(self, type_id: str) -> Any | None:
        """Find an artifact definition by its type_id.

        Returns:
            A record-like object with type_id, name, description, rarity,
            artifact_set, set_position, base_value, image_url fields,
            or None.
        """
        ...

    async def list_all(
        self,
        rarity: str | None = None,
        artifact_set: str | None = None,
    ) -> list[Any]:
        """List all definitions with optional filters.

        Returns:
            List of record-like objects.
        """
        ...

    async def list_by_set(self, artifact_set: str) -> list[Any]:
        """List all definitions in a specific artifact set."""
        ...

    async def get_set_type_ids(self, artifact_set: str) -> list[str]:
        """Get all type IDs belonging to a set."""
        ...

    async def list_all_sets(self) -> list[str]:
        """List all unique artifact set names."""
        ...
