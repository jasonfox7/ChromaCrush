"""Data Transfer Objects for the auth module.

These DTOs carry structured data between the service layer and its
callers. They are not ORM models and have no database awareness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.core.types.auth import ApiKeyInfo


@dataclass
class AuthResult:
    """Result of successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # seconds until access token expires

    @property
    def authorization_header(self) -> str:
        """Format for Authorization header."""
        return f"{self.token_type} {self.access_token}"


@dataclass
class ApiKeyCreationResult:
    """Result of creating an API key."""

    key_info: ApiKeyInfo  # Metadata about the key
    raw_key: str  # The actual key -- only returned once, never stored


@dataclass
class SessionInfo:
    """Information about an active session."""

    session_id: UUID
    player_id: UUID
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    device_info: str | None = None  # User-agent or client identifier


@dataclass
class RateLimitStatus:
    """Rate limit status for an API key."""

    key_id: UUID
    requests_remaining: int
    requests_limit: int
    window_seconds: int
    reset_at: datetime
    is_exceeded: bool = field(init=False)

    def __post_init__(self) -> None:
        self.is_exceeded = self.requests_remaining <= 0


@dataclass
class TokenPayload:
    """Decoded JWT token payload (internal use)."""

    player_id: UUID
    session_id: UUID
    token_type: str  # "access" or "refresh"
    issued_at: datetime
    expires_at: datetime
