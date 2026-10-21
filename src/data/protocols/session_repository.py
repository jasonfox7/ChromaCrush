"""Repository protocol for session data access.

Modules depend on this protocol interface; the concrete SQLAlchemy
implementation lives in ``src.data.repositories.session_repository``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass
class SessionRecord:
    """Represents a session record in the database."""

    id: UUID
    player_id: UUID
    refresh_token_hash: str
    device_info: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


class SessionRepositoryProtocol(Protocol):
    """Async repository interface for session persistence.

    All methods are ``async`` and work with the ``SessionRecord`` type.
    The implementation manages its own session lifecycle through the
    injected ``DataContextProtocol``.
    """

    async def create(
        self,
        player_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        device_info: str | None = None,
        session_id: UUID | None = None,
    ) -> SessionRecord:
        """Create a new session.

        Args:
            player_id: The player's unique identifier.
            refresh_token_hash: Hash of the refresh token.
            expires_at: When the session expires.
            device_info: Optional client/device identifier.
            session_id: Optional explicit session ID. If None, the
                repository generates one.

        Returns:
            The newly created ``SessionRecord``.
        """
        ...

    async def find_by_id(self, session_id: UUID) -> SessionRecord | None:
        """Find session by ID (includes revoked for validation).

        Args:
            session_id: The session's unique identifier.

        Returns:
            The ``SessionRecord``, or ``None`` if not found.
        """
        ...

    async def find_by_player_id(
        self,
        player_id: UUID,
        include_revoked: bool = False,
    ) -> list[SessionRecord]:
        """Find all sessions for a player.

        Args:
            player_id: The player's unique identifier.
            include_revoked: Whether to include revoked sessions.

        Returns:
            List of ``SessionRecord`` instances.
        """
        ...

    async def update_last_used(self, session_id: UUID) -> None:
        """Update the last_used_at timestamp for a session.

        Args:
            session_id: The session to update.
        """
        ...

    async def revoke(self, session_id: UUID) -> None:
        """Revoke a session (soft delete by setting revoked_at).

        Args:
            session_id: The session to revoke.
        """
        ...

    async def revoke_all_for_player(self, player_id: UUID) -> int:
        """Revoke all active sessions for a player.

        Args:
            player_id: The player whose sessions to revoke.

        Returns:
            Count of sessions revoked.
        """
        ...

    async def count_active_for_player(self, player_id: UUID) -> int:
        """Count active (non-revoked, non-expired) sessions for a player.

        Args:
            player_id: The player to count sessions for.

        Returns:
            Number of active sessions.
        """
        ...

    async def cleanup_expired(self) -> int:
        """Delete sessions expired more than 7 days ago.

        Returns:
            Count of sessions deleted.
        """
        ...
