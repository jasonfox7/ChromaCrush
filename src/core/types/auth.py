"""Authentication types for ChromaCrush.

Defines token types, validated auth tokens, and API key metadata.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from src.core.types.game import PlayerId


class TokenType(Enum):
    """Type of authentication credential."""

    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


@dataclass
class AuthToken:
    """Validated authentication token."""

    token_type: TokenType
    player_id: PlayerId
    issued_at: datetime
    expires_at: datetime | None  # None for API keys (no expiry)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class ApiKeyInfo:
    """API key metadata (does not contain the actual key)."""

    key_id: UUID
    player_id: PlayerId
    prefix: str  # First 8 chars for identification
    created_at: datetime
    last_used_at: datetime | None = None
    revoked: bool = False
