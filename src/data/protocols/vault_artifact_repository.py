"""Repository protocol for vault artifact data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.vault_artifact_repository``.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class VaultArtifactRepositoryProtocol(Protocol):
    """Async repository interface for vault artifact persistence.

    All methods are ``async`` and return lightweight record dicts or
    domain-adjacent objects. The service maps them to DTOs.
    """

    async def find_by_id(self, artifact_id: UUID) -> Any | None:
        """Find an artifact by UUID.

        Returns:
            A record-like object with id, owner_id, artifact_type_id,
            acquired_at, source, source_id fields, or None.
        """
        ...

    async def find_by_owner(
        self,
        owner_id: UUID,
        rarity: str | None = None,
        artifact_set: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """Find artifacts owned by a player with optional filters.

        Returns:
            Tuple of (items, total_count).
        """
        ...

    async def count_by_owner(self, owner_id: UUID) -> int:
        """Count total artifacts owned by a player."""
        ...

    async def count_by_owner_and_rarity(self, owner_id: UUID) -> dict[str, int]:
        """Count artifacts grouped by rarity for a player."""
        ...

    async def find_by_owner_and_type(
        self,
        owner_id: UUID,
        artifact_type_id: str,
    ) -> Any | None:
        """Find if owner has a specific artifact type."""
        ...

    async def list_owned_type_ids(
        self,
        owner_id: UUID,
        artifact_set: str | None = None,
    ) -> list[str]:
        """List all artifact type IDs owned by player, optionally filtered by set."""
        ...

    async def create(
        self,
        owner_id: UUID,
        artifact_type_id: str,
        source: str,
        source_id: str | None = None,
    ) -> Any:
        """Create a new vault artifact record.

        Returns:
            The created record.
        """
        ...

    async def update_owner(
        self,
        artifact_id: UUID,
        new_owner_id: UUID,
    ) -> Any:
        """Change the owner of an artifact.

        Returns:
            The updated record.
        """
        ...

    async def delete(self, artifact_id: UUID) -> None:
        """Delete an artifact record."""
        ...

    async def get_random_artifact(
        self,
        owner_id: UUID,
        exclude_legendary: bool = False,
    ) -> Any | None:
        """Get a random artifact from an owner's vault.

        Returns:
            A record-like object, or None if vault is empty.
        """
        ...
