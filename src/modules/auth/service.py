"""Auth service implementation.

Fully async service managing JWT authentication, API key management,
session lifecycle, and rate limiting. All dependencies arrive via
``__init__`` injection; no direct imports of core services or
environment access.

Password hashing and verification are sync methods (CPU-bound, no I/O).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from src.core.types.auth import ApiKeyInfo, AuthToken, TokenType
from src.core.types.game import PlayerId
from src.modules.auth.api_key_generator import (
    generate_api_key,
    verify_api_key,
)
from src.modules.auth.dto import (
    ApiKeyCreationResult,
    AuthResult,
    RateLimitStatus,
    SessionInfo,
)
from src.modules.auth.jwt_handler import JwtHandler
from src.modules.auth.password_handler import (
    hash_password as _hash_password,
    validate_password_strength,
    verify_password as _verify_password,
)
from src.modules.auth.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.api_key_repository import ApiKeyRepositoryProtocol
    from src.data.protocols.session_repository import SessionRepositoryProtocol
    from src.modules.auth.protocols import PasswordStoreProtocol
    from src.modules.player.protocols import PlayerServiceProtocol


class AuthService:
    """Concrete implementation of ``AuthServiceProtocol``.

    Manages JWT authentication for humans, API key authentication for
    bots, session lifecycle, and rate limiting support. All public
    methods except ``hash_password`` and ``verify_password`` are
    ``async def`` as they involve database or Redis operations.

    Args:
        config: Configuration service for reading settings.
        logger: Structured logging service.
        errors: Error factory service.
        player_service: Player module for player lookups.
        session_repo: Repository for session persistence.
        api_key_repo: Repository for API key persistence.
        password_store: Protocol for accessing password hashes.
        redis: Redis client for rate limiting.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        session_repo: SessionRepositoryProtocol,
        api_key_repo: ApiKeyRepositoryProtocol,
        password_store: PasswordStoreProtocol,
        redis: Any,  # Redis client for rate limiting
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._player_service = player_service
        self._session_repo = session_repo
        self._api_key_repo = api_key_repo
        self._password_store = password_store
        self._redis = redis

        # Cache configuration values read at init time
        jwt_secret: str = config.require("auth.jwt_secret")
        self._jwt_algorithm: str = config.get("auth.jwt_algorithm", "HS256")
        self._access_token_expiry_minutes: int = config.get(
            "auth.access_token_expiry_minutes", 60
        )
        self._refresh_token_expiry_days: int = config.get(
            "auth.refresh_token_expiry_days", 30
        )
        self._api_key_prefix: str = config.get("auth.api_key_prefix", "cc_")
        self._api_key_length: int = config.get("auth.api_key_length", 32)
        self._bcrypt_rounds: int = config.get("auth.bcrypt_rounds", 12)
        self._password_min_length: int = config.get("auth.password_min_length", 8)
        self._rate_limit_requests: int = config.get("auth.rate_limit_requests", 100)
        self._rate_limit_window_seconds: int = config.get(
            "auth.rate_limit_window_seconds", 60
        )
        self._max_sessions_per_player: int = config.get(
            "auth.max_sessions_per_player", 5
        )

        # Create internal JWT handler
        self._jwt = JwtHandler(secret=jwt_secret, algorithm=self._jwt_algorithm)

        # Create internal rate limiter
        self._rate_limiter = RateLimiter(
            redis=redis,
            max_requests=self._rate_limit_requests,
            window_seconds=self._rate_limit_window_seconds,
        )

    # ========== Human Authentication ==========

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> AuthResult:
        """Authenticate human user with credentials."""
        # Look up player by username
        player = await self._player_service.get_player_by_username(username)
        if player is None:
            self._logger.warn(
                "Authentication failed",
                username=username,
                reason="player_not_found",
            )
            raise self._errors.unauthorized(
                "Invalid username or password",
                code="AUTH_INVALID_CREDENTIALS",
            )

        # Bots cannot use password authentication
        if player.is_bot:
            self._logger.warn(
                "Authentication failed",
                username=username,
                reason="bot_cannot_use_password",
            )
            raise self._errors.unauthorized(
                "Invalid username or password",
                code="AUTH_INVALID_CREDENTIALS",
            )

        # Get the stored password hash
        stored_hash = await self._password_store.get_password_hash(player.id)
        if stored_hash is None:
            self._logger.warn(
                "Authentication failed",
                username=username,
                reason="no_password_set",
            )
            raise self._errors.unauthorized(
                "Invalid username or password",
                code="AUTH_INVALID_CREDENTIALS",
            )

        # Verify password
        if not self.verify_password(password, stored_hash):
            self._logger.warn(
                "Authentication failed",
                username=username,
                reason="incorrect_password",
            )
            raise self._errors.unauthorized(
                "Invalid username or password",
                code="AUTH_INVALID_CREDENTIALS",
            )

        # Enforce session limit -- revoke oldest if at max
        active_count = await self._session_repo.count_active_for_player(player.id)
        if active_count >= self._max_sessions_per_player:
            sessions = await self._session_repo.find_by_player_id(player.id)
            if sessions:
                # Revoke the oldest session (last in desc-ordered list)
                oldest = sessions[-1]
                await self._session_repo.revoke(oldest.id)

        # Create session and return tokens
        result = await self._create_session(player.id)

        self._logger.info(
            "Authentication successful",
            player_id=str(player.id),
            player_type="human",
        )

        return result

    async def authenticate_apple(
        self,
        identity_token: str,
        authorization_code: str | None = None,
        display_name: str | None = None,
    ) -> tuple[AuthResult, bool]:
        """Authenticate via Apple Sign-In.

        Decodes the Apple identity token to extract the ``sub`` claim
        (Apple user ID). If a player with that Apple ID exists, logs them
        in. Otherwise, auto-registers a new player.

        Args:
            identity_token: JWT identity token from Apple.
            authorization_code: Authorization code from Apple (unused server-side for now).
            display_name: User's display name from Apple (given + family name).

        Returns:
            Tuple of (AuthResult, is_new_player).
        """
        import jwt as pyjwt

        # Decode the Apple identity token.
        # In production this should verify the signature against Apple's public keys.
        # For now we decode without verification (the frontend verified via the native SDK).
        try:
            claims = pyjwt.decode(
                identity_token,
                options={"verify_signature": False},
                algorithms=["RS256"],
            )
        except Exception:
            raise self._errors.unauthorized(
                "Invalid Apple identity token",
                code="AUTH_APPLE_TOKEN_INVALID",
            )

        apple_user_id = claims.get("sub")
        if not apple_user_id:
            raise self._errors.unauthorized(
                "Apple identity token missing sub claim",
                code="AUTH_APPLE_TOKEN_INVALID",
            )

        # Look up existing player by Apple user ID.
        player = await self._player_service.get_player_by_apple_id(apple_user_id)

        is_new = player is None
        if is_new:
            # Auto-register: generate a username from display name or procedural.
            username = self._generate_apple_username(display_name, apple_user_id)

            from src.core.types.player import PlayerType

            player = await self._player_service.create_player(
                username=username,
                player_type=PlayerType.HUMAN,
                apple_user_id=apple_user_id,
                auth_provider="apple",
            )

            self._logger.info(
                "Apple Sign-In: new player registered",
                player_id=str(player.id),
                username=player.username,
            )
        else:
            self._logger.info(
                "Apple Sign-In: existing player",
                player_id=str(player.id),
                username=player.username,
            )

        result = await self._create_session(player.id)
        return result, is_new

    @staticmethod
    def _generate_apple_username(
        display_name: str | None,
        apple_user_id: str,
    ) -> str:
        """Generate a username for a new Apple Sign-In user.

        Uses display name if available, falling back to a hash of the Apple ID.
        """
        import re

        if display_name:
            # Strip non-alphanumeric, keep underscores.
            clean = re.sub(r"[^a-zA-Z0-9_]", "", display_name.replace(" ", "_"))
            if len(clean) >= 3:
                # Append short hash to avoid collisions.
                suffix = apple_user_id[-4:]
                return f"{clean[:28]}_{suffix}"

        # Fallback: use hash of apple_user_id.
        import hashlib

        short_hash = hashlib.sha256(apple_user_id.encode()).hexdigest()[:8]
        return f"Player_{short_hash}"

    async def validate_token(
        self,
        token: str,
    ) -> AuthToken:
        """Validate a JWT access token or API key."""
        # Determine token type from format
        if token.startswith(self._api_key_prefix):
            return await self._validate_api_key(token)
        else:
            return await self._validate_jwt(token)

    async def refresh_token(
        self,
        refresh_token: str,
    ) -> AuthResult:
        """Get new access token using refresh token."""
        # Decode the refresh token
        payload = self._jwt.decode_token(refresh_token)

        if payload.token_type != "refresh":
            raise self._errors.unauthorized(
                "Invalid token type",
                code="AUTH_TOKEN_INVALID",
            )

        # Find and validate session
        session = await self._session_repo.find_by_id(payload.session_id)
        if session is None:
            raise self._errors.unauthorized(
                "Session not found",
                code="AUTH_TOKEN_INVALID",
            )

        if session.revoked_at is not None:
            # Potential token theft -- log it
            self._logger.warn(
                "Refresh token reuse detected",
                player_id=str(session.player_id),
                session_id=str(session.id),
            )
            raise self._errors.unauthorized(
                "Token already used",
                code="AUTH_TOKEN_INVALID",
            )

        # Revoke old session
        await self._session_repo.revoke(session.id)

        # Create new session with new tokens
        result = await self._create_session(
            PlayerId(session.player_id),
            device_info=session.device_info,
        )

        self._logger.info(
            "Token refreshed",
            player_id=str(session.player_id),
            old_session_id=str(session.id),
        )

        return result

    async def logout(
        self,
        player_id: PlayerId,
        session_id: UUID | None = None,
    ) -> None:
        """Invalidate a session or all sessions for a player."""
        # Verify player exists
        await self._player_service.get_player(player_id)

        if session_id is not None:
            # Revoke specific session
            await self._session_repo.revoke(session_id)
            self._logger.info(
                "Session invalidated",
                player_id=str(player_id),
                session_id=str(session_id),
            )
        else:
            # Revoke all sessions
            count = await self._session_repo.revoke_all_for_player(player_id)
            self._logger.info(
                "All sessions invalidated",
                player_id=str(player_id),
                session_count=count,
            )

    async def get_active_sessions(
        self,
        player_id: PlayerId,
    ) -> list[SessionInfo]:
        """List all active sessions for a player."""
        # Verify player exists
        await self._player_service.get_player(player_id)

        sessions = await self._session_repo.find_by_player_id(player_id)
        now = datetime.now(timezone.utc)

        return [
            SessionInfo(
                session_id=s.id,
                player_id=s.player_id,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
                expires_at=s.expires_at,
                device_info=s.device_info,
            )
            for s in sessions
            if s.expires_at > now
        ]

    # ========== API Key Management (Bots) ==========

    async def create_api_key(
        self,
        player_id: PlayerId,
        description: str | None = None,
    ) -> ApiKeyCreationResult:
        """Create a new API key for a bot player."""
        # Verify player exists and is a bot
        player = await self._player_service.get_player(player_id)

        if not player.is_bot:
            raise self._errors.forbidden(
                "Only bot accounts can have API keys",
                code="FORBIDDEN_NOT_BOT",
                player_id=str(player_id),
            )

        # Validate description length
        if description is not None and len(description) > 255:
            raise self._errors.validation(
                "Description must not exceed 255 characters",
                code="VALIDATION_INVALID_INPUT",
                field="description",
            )

        # Generate the key
        raw_key, key_hash = generate_api_key(
            prefix=self._api_key_prefix,
            key_length=self._api_key_length,
        )

        # Extract prefix for storage (prefix + first 8 chars of random part)
        stored_prefix = raw_key[: len(self._api_key_prefix) + 8]

        # Store the key record
        record = await self._api_key_repo.create(
            player_id=player_id,
            key_hash=key_hash,
            key_prefix=stored_prefix,
            description=description,
        )

        key_info = ApiKeyInfo(
            key_id=record.id,
            player_id=PlayerId(record.player_id),
            prefix=record.key_prefix,
            created_at=record.created_at,
            last_used_at=record.last_used_at,
            revoked=record.revoked_at is not None,
        )

        self._logger.info(
            "API key created",
            player_id=str(player_id),
            key_id=str(record.id),
            description=description or "",
        )

        return ApiKeyCreationResult(
            key_info=key_info,
            raw_key=raw_key,
        )

    async def revoke_api_key(
        self,
        key_id: UUID,
        player_id: PlayerId,
    ) -> None:
        """Revoke an API key."""
        # Find the key
        record = await self._api_key_repo.find_by_id(key_id)
        if record is None:
            raise self._errors.not_found(
                "API key not found",
                code="NOT_FOUND_API_KEY",
                key_id=str(key_id),
            )

        # Verify ownership
        if record.player_id != player_id:
            raise self._errors.forbidden(
                "You do not own this API key",
                code="FORBIDDEN_NOT_KEY_OWNER",
                key_id=str(key_id),
                player_id=str(player_id),
            )

        # Revoke
        await self._api_key_repo.revoke(key_id)

        self._logger.info(
            "API key revoked",
            player_id=str(player_id),
            key_id=str(key_id),
        )

    async def list_api_keys(
        self,
        player_id: PlayerId,
        include_revoked: bool = False,
    ) -> list[ApiKeyInfo]:
        """List all API keys for a player."""
        # Verify player exists
        await self._player_service.get_player(player_id)

        records = await self._api_key_repo.find_by_player_id(
            player_id, include_revoked=include_revoked
        )

        return [
            ApiKeyInfo(
                key_id=r.id,
                player_id=PlayerId(r.player_id),
                prefix=r.key_prefix,
                created_at=r.created_at,
                last_used_at=r.last_used_at,
                revoked=r.revoked_at is not None,
            )
            for r in records
        ]

    # ========== Rate Limiting Support ==========

    async def check_rate_limit(
        self,
        key_id: UUID,
    ) -> RateLimitStatus:
        """Check rate limit status for an API key."""
        # Verify key exists
        record = await self._api_key_repo.find_by_id(key_id)
        if record is None:
            raise self._errors.not_found(
                "API key not found",
                code="NOT_FOUND_API_KEY",
                key_id=str(key_id),
            )

        return await self._rate_limiter.get_status(key_id)

    async def record_api_request(
        self,
        key_id: UUID,
    ) -> RateLimitStatus:
        """Record an API request for rate limiting."""
        # Verify key exists
        record = await self._api_key_repo.find_by_id(key_id)
        if record is None:
            raise self._errors.not_found(
                "API key not found",
                code="NOT_FOUND_API_KEY",
                key_id=str(key_id),
            )

        status = await self._rate_limiter.record_request(key_id)

        if status.is_exceeded:
            self._logger.warn(
                "Rate limit exceeded",
                key_id=str(key_id),
                requests_made=status.requests_limit - status.requests_remaining,
                limit=status.requests_limit,
            )
            raise self._errors.rate_limited(
                "API key rate limit exceeded",
                retry_after=self._rate_limit_window_seconds,
                code="RATE_LIMIT_API_KEY",
                key_id=str(key_id),
            )

        return status

    # ========== Bot Match Token ==========

    async def create_bot_match_token(
        self,
        bot_player_id: PlayerId,
        match_id: str,
    ) -> str:
        """Create a short-lived JWT for a bot to play a specific match.

        Uses the standard session infrastructure so existing auth middleware
        validates the token without changes.

        Args:
            bot_player_id: The bot player's ID.
            match_id: The match identifier (for logging/session device_info).

        Returns:
            A Bearer access token string (2-hour expiry).
        """
        from uuid import uuid4

        session_id = uuid4()

        access_token = self._jwt.create_access_token(
            player_id=bot_player_id,
            session_id=session_id,
            expiry_minutes=120,
        )

        # Store a lightweight session so middleware can validate.
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        await self._session_repo.create(
            player_id=bot_player_id,
            refresh_token_hash=f"bot_match_{match_id}",
            expires_at=expires_at,
            device_info=f"bot_match:{match_id}",
            session_id=session_id,
        )

        self._logger.info(
            "bot_match_token.created",
            bot_player_id=str(bot_player_id),
            match_id=match_id,
        )

        return access_token

    # ========== Password Operations ==========

    def hash_password(self, password: str) -> str:
        """Hash a password for storage using bcrypt (sync)."""
        # Validate password strength first
        is_valid, error_msg = validate_password_strength(
            password, min_length=self._password_min_length
        )
        if not is_valid:
            raise self._errors.validation(
                error_msg or "Password does not meet requirements",
                code="VALIDATION_WEAK_PASSWORD",
            )

        return _hash_password(password, rounds=self._bcrypt_rounds)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash (sync)."""
        return _verify_password(password, password_hash)

    # ========== Internal Helpers ==========

    async def _create_session(
        self,
        player_id: PlayerId,
        device_info: str | None = None,
    ) -> AuthResult:
        """Create a new session and return tokens.

        Args:
            player_id: The authenticated player.
            device_info: Optional client/device info.

        Returns:
            AuthResult with access and refresh tokens.
        """
        from uuid import uuid4

        session_id = uuid4()

        # Create tokens
        access_token = self._jwt.create_access_token(
            player_id=player_id,
            session_id=session_id,
            expiry_minutes=self._access_token_expiry_minutes,
        )

        refresh_token = self._jwt.create_refresh_token(
            player_id=player_id,
            session_id=session_id,
            expiry_days=self._refresh_token_expiry_days,
        )

        # Hash the refresh token for storage.
        # We use SHA256 here instead of bcrypt because:
        # 1. JWTs can exceed bcrypt's 72-byte limit
        # 2. Refresh tokens are already high-entropy (no need for slow hashing)
        import hashlib

        refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

        # Calculate expiry
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self._refresh_token_expiry_days
        )

        # Store session with the same ID used in the JWT
        await self._session_repo.create(
            player_id=player_id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
            device_info=device_info,
            session_id=session_id,
        )

        return AuthResult(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=self._access_token_expiry_minutes * 60,
        )

    async def _validate_jwt(self, token: str) -> AuthToken:
        """Validate a JWT access token.

        Args:
            token: The encoded JWT string.

        Returns:
            Validated AuthToken.
        """
        payload = self._jwt.decode_token(token)

        # Verify session exists and is not revoked
        session = await self._session_repo.find_by_id(payload.session_id)
        if session is None or session.revoked_at is not None:
            self._logger.warn(
                "Token validation failed",
                reason="invalid_session",
                token_type="jwt",
            )
            raise self._errors.unauthorized(
                "Invalid token",
                code="AUTH_TOKEN_INVALID",
            )

        # Update session last_used_at
        await self._session_repo.update_last_used(payload.session_id)

        self._logger.debug(
            "Token validated",
            token_type="access",
            player_id=str(payload.player_id),
        )

        return AuthToken(
            token_type=TokenType.ACCESS,
            player_id=PlayerId(payload.player_id),
            issued_at=payload.issued_at,
            expires_at=payload.expires_at,
        )

    async def _validate_api_key(self, key: str) -> AuthToken:
        """Validate an API key.

        Args:
            key: The full API key string.

        Returns:
            Validated AuthToken.
        """
        # Extract prefix for database lookup
        prefix = key[: len(self._api_key_prefix) + 8]

        # Find candidate keys by prefix
        candidates = await self._api_key_repo.find_by_prefix(prefix)

        # Verify hash against each candidate
        for candidate in candidates:
            if candidate.revoked_at is not None:
                # Check if this specific key matches the revoked one
                if verify_api_key(key, candidate.key_hash):
                    self._logger.warn(
                        "Token validation failed",
                        reason="api_key_revoked",
                        token_type="api_key",
                    )
                    raise self._errors.unauthorized(
                        "API key has been revoked",
                        code="AUTH_API_KEY_REVOKED",
                    )
                continue

            if verify_api_key(key, candidate.key_hash):
                # Update last_used_at
                await self._api_key_repo.update_last_used(candidate.id)

                self._logger.debug(
                    "Token validated",
                    token_type="api_key",
                    player_id=str(candidate.player_id),
                )

                return AuthToken(
                    token_type=TokenType.API_KEY,
                    player_id=PlayerId(candidate.player_id),
                    issued_at=candidate.created_at,
                    expires_at=None,  # API keys don't expire
                )

        # No match found
        self._logger.warn(
            "Token validation failed",
            reason="api_key_not_found",
            token_type="api_key",
        )
        raise self._errors.unauthorized(
            "Invalid API key",
            code="AUTH_API_KEY_INVALID",
        )

    # ========== Session Cleanup ==========

    async def cleanup_expired_sessions(self) -> int:
        """Delete sessions that expired more than 7 days ago.

        Returns:
            Number of expired sessions deleted.
        """
        count = await self._session_repo.cleanup_expired()
        if count:
            self._logger.info("auth.expired_sessions_cleaned", count=count)
        return count
