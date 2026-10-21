"""Repository protocol for API key data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.api_key_repository``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass
class ApiKeyRecord:
    """Represents an API key record in the database."""

    id: UUID
    player_id: UUID
    key_hash: str
    key_prefix: str
    description: str | None
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiKeyRepositoryProtocol(Protocol):
    """Async repository interface for API key persistence.

    All methods are ``async`` and work with the ``ApiKeyRecord`` type.
    The implementation manages its own session lifecycle through the
    injected ``DataContextProtocol``.
    """

    async def create(
        self,
        player_id: UUID,
        key_hash: str,
        key_prefix: str,
        description: str | None = None,
    ) -> ApiKeyRecord:
        """Create a new API key record.

        Args:
            player_id: The player's unique identifier.
            key_hash: Bcrypt hash of the full API key.
            key_prefix: First characters for identification.
            description: Optional description of the key's purpose.

        Returns:
            The newly created ``ApiKeyRecord``.
        """
        ...

    async def find_by_id(self, key_id: UUID) -> ApiKeyRecord | None:
        """Find key by ID (includes revoked for audit).

        Args:
            key_id: The key's unique identifier.

        Returns:
            The ``ApiKeyRecord``, or ``None`` if not found.
        """
        ...

    async def find_by_prefix(self, prefix: str) -> list[ApiKeyRecord]:
        """Find keys by prefix (for lookup during validation).

        Args:
            prefix: The key prefix to search for.

        Returns:
            List of matching ``ApiKeyRecord`` instances.
        """
        ...

    async def find_by_player_id(
        self,
        player_id: UUID,
        include_revoked: bool = False,
    ) -> list[ApiKeyRecord]:
        """Find all keys for a player.

        Args:
            player_id: The player's unique identifier.
            include_revoked: Whether to include revoked keys.

        Returns:
            List of ``ApiKeyRecord`` instances.
        """
        ...

    async def update_last_used(self, key_id: UUID) -> None:
        """Update the last_used_at timestamp for a key.

        Args:
            key_id: The key to update.
        """
        ...

    async def revoke(self, key_id: UUID) -> None:
        """Revoke a key (soft delete by setting revoked_at).

        Args:
            key_id: The key to revoke.
        """
        ...

    async def count_active_for_player(self, player_id: UUID) -> int:
        """Count active (non-revoked) keys for a player.

        Args:
            player_id: The player to count keys for.

        Returns:
            Number of active keys.
        """
        ...
