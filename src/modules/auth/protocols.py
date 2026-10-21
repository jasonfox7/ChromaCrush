"""Auth service protocol.

Defines the public interface for the auth module. All methods except
``hash_password`` and ``verify_password`` are ``async def`` because
they involve database or Redis operations.

Other modules and the presentation layer depend on this protocol
interface; the concrete ``AuthService`` implementation lives in
``src.modules.auth.service``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from src.core.types.auth import ApiKeyInfo, AuthToken
from src.core.types.game import PlayerId

if TYPE_CHECKING:
    from src.modules.auth.dto import (
        ApiKeyCreationResult,
        AuthResult,
        RateLimitStatus,
        SessionInfo,
    )


class AuthServiceProtocol(Protocol):
    """Public interface for the auth module."""

    # ========== Human Authentication ==========

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> AuthResult:
        """Authenticate human user with credentials.

        Args:
            username: Player's username (case-insensitive lookup).
            password: Plain-text password to verify against stored hash.

        Returns:
            AuthResult containing access_token, refresh_token, expiry info.

        Raises:
            AUTH_INVALID_CREDENTIALS: If username not found or password incorrect.
            AUTH_INVALID_CREDENTIALS: If player is a bot (bots use API keys).
        """
        ...

    async def authenticate_apple(
        self,
        identity_token: str,
        authorization_code: str | None = None,
        display_name: str | None = None,
    ) -> tuple[AuthResult, bool]:
        """Authenticate via Apple Sign-In.

        Args:
            identity_token: JWT identity token from Apple.
            authorization_code: Authorization code from Apple.
            display_name: User's display name from Apple.

        Returns:
            Tuple of (AuthResult, is_new_player).
        """
        ...

    async def validate_token(
        self,
        token: str,
    ) -> AuthToken:
        """Validate a JWT access token or API key.

        Determines token type from format:
        - Tokens starting with config api_key_prefix are API keys
        - Other tokens are treated as JWTs

        Args:
            token: The token string (JWT or API key).

        Returns:
            Validated AuthToken with player_id, token_type, expiry info.

        Raises:
            AUTH_TOKEN_INVALID: If JWT signature invalid or malformed.
            AUTH_TOKEN_EXPIRED: If JWT has expired.
            AUTH_API_KEY_INVALID: If API key not found in database.
            AUTH_API_KEY_REVOKED: If API key has been revoked.
        """
        ...

    async def refresh_token(
        self,
        refresh_token: str,
    ) -> AuthResult:
        """Get new access token using refresh token.

        Validates the refresh token, invalidates it (single-use), and issues
        a new access/refresh token pair (refresh token rotation).

        Args:
            refresh_token: Valid refresh token from previous authentication.

        Returns:
            New AuthResult with fresh access_token and refresh_token.

        Raises:
            AUTH_TOKEN_INVALID: If refresh token format invalid or already used.
            AUTH_TOKEN_EXPIRED: If refresh token has expired.
        """
        ...

    async def logout(
        self,
        player_id: PlayerId,
        session_id: UUID | None = None,
    ) -> None:
        """Invalidate a session or all sessions for a player.

        Args:
            player_id: The player logging out.
            session_id: Specific session to invalidate. If None, invalidates all.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def get_active_sessions(
        self,
        player_id: PlayerId,
    ) -> list[SessionInfo]:
        """List all active sessions for a player.

        Args:
            player_id: The player to list sessions for.

        Returns:
            List of SessionInfo with session details.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== API Key Management (Bots) ==========

    async def create_api_key(
        self,
        player_id: PlayerId,
        description: str | None = None,
    ) -> ApiKeyCreationResult:
        """Create a new API key for a bot player.

        Args:
            player_id: The bot player's ID.
            description: Optional description for the key.

        Returns:
            ApiKeyCreationResult containing key_info and raw_key.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            FORBIDDEN_NOT_BOT: If player is not a bot.
            VALIDATION_INVALID_INPUT: If description exceeds 255 characters.
        """
        ...

    async def revoke_api_key(
        self,
        key_id: UUID,
        player_id: PlayerId,
    ) -> None:
        """Revoke an API key.

        Args:
            key_id: The key to revoke.
            player_id: Owner of the key (for authorization check).

        Raises:
            NOT_FOUND_API_KEY: If key doesn't exist.
            FORBIDDEN_NOT_KEY_OWNER: If player_id doesn't own the key.
        """
        ...

    async def list_api_keys(
        self,
        player_id: PlayerId,
        include_revoked: bool = False,
    ) -> list[ApiKeyInfo]:
        """List all API keys for a player.

        Args:
            player_id: The player (must be a bot).
            include_revoked: Whether to include revoked keys in results.

        Returns:
            List of ApiKeyInfo (metadata only, no actual keys).

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Rate Limiting Support ==========

    async def check_rate_limit(
        self,
        key_id: UUID,
    ) -> RateLimitStatus:
        """Check rate limit status for an API key.

        Args:
            key_id: The API key to check.

        Returns:
            RateLimitStatus with remaining requests, reset_at, limit.

        Raises:
            NOT_FOUND_API_KEY: If key doesn't exist.
        """
        ...

    async def record_api_request(
        self,
        key_id: UUID,
    ) -> RateLimitStatus:
        """Record an API request for rate limiting.

        Args:
            key_id: The API key making the request.

        Returns:
            Updated RateLimitStatus after recording the request.

        Raises:
            NOT_FOUND_API_KEY: If key doesn't exist.
            RATE_LIMIT_API_KEY: If rate limit exceeded.
        """
        ...

    # ========== Bot Match Token ==========

    async def create_bot_match_token(
        self,
        bot_player_id: PlayerId,
        match_id: str,
    ) -> str:
        """Create a short-lived JWT for a bot to play a specific match.

        Args:
            bot_player_id: The bot player's ID.
            match_id: The match identifier.

        Returns:
            A Bearer access token string (2-hour expiry).
        """
        ...

    # ========== Session Cleanup ==========

    async def cleanup_expired_sessions(self) -> int:
        """Delete sessions that expired more than 7 days ago.

        Returns:
            Number of expired sessions deleted.
        """
        ...

    # ========== Password Operations ==========

    def hash_password(
        self,
        password: str,
    ) -> str:
        """Hash a password for storage using bcrypt.

        This is a sync method (CPU-bound, no I/O).

        Args:
            password: Plain-text password.

        Returns:
            Bcrypt hash string.

        Raises:
            VALIDATION_WEAK_PASSWORD: If password doesn't meet requirements.
        """
        ...

    def verify_password(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        """Verify a password against its hash.

        Uses constant-time comparison to prevent timing attacks.
        This is a sync method (CPU-bound, no I/O).

        Args:
            password: Plain-text password to verify.
            password_hash: Stored bcrypt hash.

        Returns:
            True if password matches, False otherwise.
        """
        ...


class PasswordStoreProtocol(Protocol):
    """Protocol for accessing password hashes.

    The Player domain type does not include password_hash. This protocol
    provides a clean way for the auth service to access password data
    without leaking password hashes into the Player type.

    Implemented in the composition root by querying the PlayerModel
    directly for the password_hash column.
    """

    async def get_password_hash(self, player_id: UUID) -> str | None:
        """Get the stored password hash for a player.

        Args:
            player_id: The player's unique identifier.

        Returns:
            The bcrypt password hash, or None if not set (bots).
        """
        ...

    async def set_password_hash(self, player_id: UUID, password_hash: str) -> None:
        """Set the password hash for a player.

        Args:
            player_id: The player's unique identifier.
            password_hash: The new bcrypt password hash.
        """
        ...
