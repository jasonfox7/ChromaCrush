# Auth Module Artifact

> **Module:** auth
> **Author:** Scout Agent
> **Date:** 2026-02-05
> **Version:** 1.0
> **Status:** Draft
> **Build Wave:** 2 (depends on player)

---

## Dependencies

### Module Dependencies

| Module | Dependency Type | What is Used |
|--------|-----------------|--------------|
| `player` | Read | Player entity lookup, credential validation, bot/human distinction |

### Core Service Dependencies

| Service | Injected Via | Usage |
|---------|--------------|-------|
| `ConfigProtocol` | `__init__` | JWT secret, token expiry, API key prefix, rate limit settings |
| `LoggerProtocol` | `__init__` | Authentication events, token operations, security events |
| `ErrorServiceProtocol` | `__init__` | Auth errors, validation errors, rate limit errors |
| `DataContext` | `__init__` | Database session management for session/API key persistence |

### Repository Dependencies

| Repository | Ownership | Access Type |
|------------|-----------|-------------|
| `SessionRepository` | Owns | Read/Write |
| `ApiKeyRepository` | Owns | Read/Write |
| `PlayerRepository` | Reads (via player service) | Read-only |

---

## 1. Purpose

The auth module manages authentication for ChromaCrush's dual-population system: human players authenticating via username/password (JWT tokens) and bot players authenticating via API keys. Per Key Decision #5 in STATE.md, this hybrid approach is chosen because different auth flows suit different client types.

The module provides:

1. **Human Authentication** - Username/password login returning JWT access + refresh tokens
2. **Bot Authentication** - API key validation for stateless bot API access
3. **Token Lifecycle** - Access token validation, refresh token rotation, session management
4. **API Key Management** - Creation, listing, and revocation of bot API keys
5. **Session Management** - Active session tracking for humans, revocation capability
6. **Rate Limiting Support** - Per-API-key rate limit tracking (actual enforcement in API layer)

The module does NOT handle:
- Password hashing (done during registration via player module)
- User registration (player module)
- Authorization/permissions (handled by consuming modules like match, vault)

---

## 2. Public Interface

### 2.1 AuthService Protocol

```python
# src/modules/auth/protocols.py
from typing import Protocol
from uuid import UUID
from datetime import datetime

from src.core.types.game import PlayerId
from src.core.types.auth import AuthToken, ApiKeyInfo, TokenType


class AuthServiceProtocol(Protocol):
    """Public interface for the auth module."""

    # ========== Human Authentication ==========

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> "AuthResult":
        """
        Authenticate human user with credentials.

        Validates username/password against stored credentials via player service.
        On success, creates a new session and returns JWT tokens.

        Args:
            username: Player's username (case-insensitive lookup).
            password: Plain-text password to verify against stored hash.

        Returns:
            AuthResult containing access_token, refresh_token, expiry info.

        Raises:
            AUTH_INVALID_CREDENTIALS: If username not found or password incorrect.
            AUTH_INVALID_CREDENTIALS: If player is a bot (bots use API keys).

        Logs:
            INFO: "Authentication successful" with player_id, session_id.
            WARN: "Authentication failed" with username, reason (no sensitive data).
        """
        ...

    async def validate_token(
        self,
        token: str,
    ) -> AuthToken:
        """
        Validate a JWT access token or API key.

        Determines token type from format:
        - Tokens starting with config api_key_prefix (default "cc_") are API keys
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

        Side Effects:
            For API keys: Updates last_used_at timestamp.

        Logs:
            DEBUG: "Token validated" with token_type, player_id.
            WARN: "Token validation failed" with reason (no token content).
        """
        ...

    async def refresh_token(
        self,
        refresh_token: str,
    ) -> "AuthResult":
        """
        Get new access token using refresh token.

        Validates the refresh token, invalidates it (single-use), and issues
        a new access/refresh token pair. This implements refresh token rotation
        for security.

        Args:
            refresh_token: Valid refresh token from previous authentication.

        Returns:
            New AuthResult with fresh access_token and refresh_token.

        Raises:
            AUTH_TOKEN_INVALID: If refresh token format invalid.
            AUTH_TOKEN_EXPIRED: If refresh token has expired.
            AUTH_TOKEN_INVALID: If refresh token already used (rotation violation).

        Logs:
            INFO: "Token refreshed" with player_id, new_session_id.
            WARN: "Refresh token reuse detected" with player_id (potential theft).
        """
        ...

    async def logout(
        self,
        player_id: PlayerId,
        session_id: UUID | None = None,
    ) -> None:
        """
        Invalidate a session or all sessions for a player.

        Args:
            player_id: The player logging out.
            session_id: Specific session to invalidate. If None, invalidates all.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.

        Logs:
            INFO: "Session invalidated" or "All sessions invalidated" with player_id.
        """
        ...

    async def get_active_sessions(
        self,
        player_id: PlayerId,
    ) -> list["SessionInfo"]:
        """
        List all active sessions for a player.

        Args:
            player_id: The player to list sessions for.

        Returns:
            List of SessionInfo with session_id, created_at, last_used_at, device_info.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== API Key Management (Bots) ==========

    async def create_api_key(
        self,
        player_id: PlayerId,
        description: str | None = None,
    ) -> "ApiKeyCreationResult":
        """
        Create a new API key for a bot player.

        Generates a cryptographically secure API key with format:
        {prefix}{random_bytes_base64} (e.g., "cc_a1b2c3d4e5f6...")

        Only the hash is stored; the raw key is returned once and never again.

        Args:
            player_id: The bot player's ID.
            description: Optional description for the key (e.g., "Production bot v2").

        Returns:
            ApiKeyCreationResult containing key_info and raw_key (only returned once).

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            FORBIDDEN_NOT_BOT: If player is not a bot (humans use passwords).
            VALIDATION_INVALID_INPUT: If description exceeds 255 characters.

        Logs:
            INFO: "API key created" with player_id, key_id, description.
        """
        ...

    async def revoke_api_key(
        self,
        key_id: UUID,
        player_id: PlayerId,
    ) -> None:
        """
        Revoke an API key.

        Revoked keys immediately become invalid for authentication.
        Revocation is soft-delete; the key record is retained for audit.

        Args:
            key_id: The key to revoke.
            player_id: Owner of the key (for authorization check).

        Raises:
            NOT_FOUND_API_KEY: If key doesn't exist.
            FORBIDDEN_NOT_KEY_OWNER: If player_id doesn't own the key.

        Logs:
            INFO: "API key revoked" with player_id, key_id.
        """
        ...

    async def list_api_keys(
        self,
        player_id: PlayerId,
        include_revoked: bool = False,
    ) -> list[ApiKeyInfo]:
        """
        List all API keys for a player.

        Args:
            player_id: The player (must be a bot).
            include_revoked: Whether to include revoked keys in results.

        Returns:
            List of ApiKeyInfo (key_id, prefix, created_at, last_used_at, revoked).
            Does NOT include the actual key (not stored).

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Rate Limiting Support ==========

    async def check_rate_limit(
        self,
        key_id: UUID,
    ) -> "RateLimitStatus":
        """
        Check rate limit status for an API key.

        This provides data for rate limiting; actual enforcement is in the API layer.

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
    ) -> "RateLimitStatus":
        """
        Record an API request for rate limiting.

        Increments the request counter for the current window.

        Args:
            key_id: The API key making the request.

        Returns:
            Updated RateLimitStatus after recording the request.

        Raises:
            NOT_FOUND_API_KEY: If key doesn't exist.
            RATE_LIMIT_API_KEY: If rate limit exceeded (returns retry_after).
        """
        ...

    # ========== Password Operations ==========

    def hash_password(
        self,
        password: str,
    ) -> str:
        """
        Hash a password for storage.

        Uses bcrypt with configurable work factor.
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
        """
        Verify a password against its hash.

        Uses constant-time comparison to prevent timing attacks.
        This is a sync method (CPU-bound, no I/O).

        Args:
            password: Plain-text password to verify.
            password_hash: Stored bcrypt hash.

        Returns:
            True if password matches, False otherwise.
        """
        ...
```

### 2.2 Data Transfer Objects

```python
# src/modules/auth/dto.py
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


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
    key_info: "ApiKeyInfo"  # Metadata about the key
    raw_key: str  # The actual key - only returned once, never stored


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
```

---

## 3. Mandatory Service Usage

### 3.1 Configuration Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `auth.jwt_secret` | string | **REQUIRED** | Secret key for JWT signing (HS256). Must be set via environment. |
| `auth.jwt_algorithm` | string | `"HS256"` | JWT signing algorithm |
| `auth.access_token_expiry_minutes` | int | `60` | Access token lifetime |
| `auth.refresh_token_expiry_days` | int | `30` | Refresh token lifetime |
| `auth.api_key_prefix` | string | `"cc_"` | Prefix for generated API keys |
| `auth.api_key_length` | int | `32` | Length of random bytes in API key |
| `auth.bcrypt_rounds` | int | `12` | Bcrypt work factor for password hashing |
| `auth.password_min_length` | int | `8` | Minimum password length |
| `auth.rate_limit_requests` | int | `100` | API requests per window per key |
| `auth.rate_limit_window_seconds` | int | `60` | Rate limit window duration |
| `auth.max_sessions_per_player` | int | `5` | Maximum concurrent sessions |

### 3.2 Logging Events

| Level | Event | Context Fields | When |
|-------|-------|----------------|------|
| INFO | "Authentication successful" | `player_id`, `session_id`, `player_type` | After successful login |
| INFO | "Token refreshed" | `player_id`, `old_session_id`, `new_session_id` | After token refresh |
| INFO | "Session invalidated" | `player_id`, `session_id` | After logout (single) |
| INFO | "All sessions invalidated" | `player_id`, `session_count` | After logout (all) |
| INFO | "API key created" | `player_id`, `key_id`, `description` | After key creation |
| INFO | "API key revoked" | `player_id`, `key_id` | After key revocation |
| DEBUG | "Token validated" | `token_type`, `player_id` | After successful validation |
| WARN | "Authentication failed" | `username`, `reason` | On failed login (no password logged) |
| WARN | "Token validation failed" | `reason`, `token_type` | On invalid/expired token |
| WARN | "Refresh token reuse detected" | `player_id`, `session_id` | Potential token theft |
| WARN | "Rate limit exceeded" | `key_id`, `requests_made`, `limit` | API key rate limited |
| ERROR | "JWT signing failed" | `error` | Internal error during token creation |

### 3.3 Error Types Used

| Error Code | HTTP | When Raised |
|------------|------|-------------|
| `AUTH_INVALID_CREDENTIALS` | 401 | Username not found, password incorrect, or bot trying password auth |
| `AUTH_TOKEN_INVALID` | 401 | JWT malformed, signature invalid, or refresh token reused |
| `AUTH_TOKEN_EXPIRED` | 401 | JWT or refresh token past expiry |
| `AUTH_API_KEY_INVALID` | 401 | API key not found in database |
| `AUTH_API_KEY_REVOKED` | 401 | API key has been revoked |
| `RATE_LIMIT_API_KEY` | 429 | API key exceeded rate limit |
| `NOT_FOUND_PLAYER` | 404 | Player ID doesn't exist |
| `NOT_FOUND_API_KEY` | 404 | API key ID doesn't exist |
| `FORBIDDEN_NOT_BOT` | 403 | Attempted API key creation for non-bot player |
| `FORBIDDEN_NOT_KEY_OWNER` | 403 | Attempted key revocation by non-owner |
| `VALIDATION_WEAK_PASSWORD` | 400 | Password doesn't meet requirements |
| `VALIDATION_INVALID_INPUT` | 400 | Description too long, invalid token format |

---

## 4. Data Access

### 4.1 Owned Data

The auth module owns these database tables:

#### `sessions` Table
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES players(id),
    refresh_token_hash VARCHAR(255) NOT NULL,  -- bcrypt hash of refresh token
    device_info VARCHAR(255),  -- User-agent or client identifier
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ  -- NULL if active
);

CREATE INDEX idx_sessions_player ON sessions(player_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_sessions_expires ON sessions(expires_at) WHERE revoked_at IS NULL;
```

#### `api_keys` Table
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES players(id),
    key_hash VARCHAR(255) NOT NULL,  -- bcrypt hash of full API key
    key_prefix VARCHAR(16) NOT NULL,  -- First chars for identification (e.g., "cc_a1b2")
    description VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ  -- NULL if active
);

CREATE INDEX idx_api_keys_player ON api_keys(player_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
```

#### `api_key_rate_limits` Table (Redis-backed)
```
Key pattern: chromacrush:ratelimit:{key_id}
Type: String (counter)
TTL: auth.rate_limit_window_seconds

Value: Current request count in window
```

### 4.2 Repository Interfaces

```python
# src/data/protocols/session_repository.py
from typing import Protocol
from uuid import UUID
from datetime import datetime


class SessionRepository(Protocol):
    """Repository interface for session data."""

    async def create(
        self,
        player_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        device_info: str | None = None,
    ) -> "SessionRecord":
        """Create a new session."""
        ...

    async def find_by_id(self, session_id: UUID) -> "SessionRecord | None":
        """Find session by ID (excludes revoked)."""
        ...

    async def find_by_player_id(
        self,
        player_id: UUID,
        include_revoked: bool = False,
    ) -> list["SessionRecord"]:
        """Find all sessions for a player."""
        ...

    async def update_last_used(self, session_id: UUID) -> None:
        """Update last_used_at timestamp."""
        ...

    async def revoke(self, session_id: UUID) -> None:
        """Revoke a session (soft delete)."""
        ...

    async def revoke_all_for_player(self, player_id: UUID) -> int:
        """Revoke all sessions for a player. Returns count revoked."""
        ...

    async def count_active_for_player(self, player_id: UUID) -> int:
        """Count active (non-revoked, non-expired) sessions."""
        ...

    async def cleanup_expired(self) -> int:
        """Delete sessions expired more than 7 days ago. Returns count deleted."""
        ...


# src/data/protocols/api_key_repository.py
class ApiKeyRepository(Protocol):
    """Repository interface for API key data."""

    async def create(
        self,
        player_id: UUID,
        key_hash: str,
        key_prefix: str,
        description: str | None = None,
    ) -> "ApiKeyRecord":
        """Create a new API key record."""
        ...

    async def find_by_id(self, key_id: UUID) -> "ApiKeyRecord | None":
        """Find key by ID (includes revoked for audit)."""
        ...

    async def find_by_prefix(self, prefix: str) -> list["ApiKeyRecord"]:
        """Find keys by prefix (for lookup during validation)."""
        ...

    async def find_by_player_id(
        self,
        player_id: UUID,
        include_revoked: bool = False,
    ) -> list["ApiKeyRecord"]:
        """Find all keys for a player."""
        ...

    async def update_last_used(self, key_id: UUID) -> None:
        """Update last_used_at timestamp."""
        ...

    async def revoke(self, key_id: UUID) -> None:
        """Revoke a key (soft delete)."""
        ...

    async def count_active_for_player(self, player_id: UUID) -> int:
        """Count active (non-revoked) keys for a player."""
        ...
```

### 4.3 Data Read from Other Modules

| Data | Source Module | Access Method | Purpose |
|------|---------------|---------------|---------|
| Player entity | `player` | `PlayerServiceProtocol.get_player()` | Verify player exists |
| Player by username | `player` | `PlayerServiceProtocol.get_player_by_username()` | Login lookup |
| Player type | `player` | `Player.player_type` | Enforce bot/human auth paths |
| Password hash | `player` | `Player` entity (internal field) | Credential verification |

### 4.4 Transaction Requirements

| Operation | Transaction Scope | Notes |
|-----------|-------------------|-------|
| `authenticate` | Single transaction | Creates session atomically |
| `refresh_token` | Single transaction | Revokes old session, creates new session atomically |
| `logout` (single) | Single transaction | Revokes specific session |
| `logout` (all) | Single transaction | Revokes all sessions atomically |
| `create_api_key` | Single transaction | Creates key record |
| `revoke_api_key` | Single transaction | Updates revoked_at |
| `record_api_request` | Redis atomic increment | Uses Redis INCR with TTL |

---

## 5. Presentation Boundary

### 5.1 What This Module Returns

The auth module returns domain objects (`AuthToken`, `ApiKeyInfo`, `SessionInfo`) and DTOs (`AuthResult`, `ApiKeyCreationResult`, `RateLimitStatus`). It does NOT return:
- HTTP responses or status codes
- JSON objects or formatted strings
- Authorization headers (though `AuthResult.authorization_header` provides a helper)

### 5.2 Presentation Layer Responsibility

The presentation layer (`src/presentation/adapters/auth_adapter.py`) handles:
- Converting `AuthResult` to `AuthResponse` (API response model)
- Setting HTTP-only cookies for refresh tokens (if using cookie-based refresh)
- Adding `WWW-Authenticate` headers on 401 responses
- Rate limit headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- Formatting `ApiKeyInfo` list for API response (hiding internal fields)

### 5.3 Example Boundary

```python
# Module returns domain object
auth_result = await auth_service.authenticate(username, password)
# auth_result is AuthResult dataclass

# Adapter converts for API
response = auth_adapter.to_response(auth_result)
# response is AuthResponse Pydantic model for JSON serialization

# Rate limit info for headers
rate_status = await auth_service.check_rate_limit(key_id)
# Presentation layer adds X-RateLimit-* headers from rate_status
```

---

## 6. Internal Design

### 6.1 Service Implementation Structure

```
src/modules/auth/
    __init__.py           # Exports AuthService, protocols
    service.py            # AuthService implementation
    protocols.py          # AuthServiceProtocol
    dto.py                # AuthResult, ApiKeyCreationResult, SessionInfo, etc.
    jwt_handler.py        # JWT encoding/decoding helpers
    api_key_generator.py  # API key generation helpers
    password_handler.py   # Password hashing/verification
    constants.py          # Auth-related constants
```

### 6.2 Component Diagram

```
                      AuthService
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
  JwtHandler       ApiKeyGenerator     PasswordHandler
        │                  │                  │
        │                  │                  │
        │                  └────────┬─────────┘
        │                           │
        │                           ▼
        │                      (bcrypt lib)
        │
        ▼
   (PyJWT lib)

                      AuthService
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
  SessionRepository  ApiKeyRepository   PlayerService
        │                  │                  │ (injected)
        └──────────────────┼──────────────────┘
                           │
                           ▼
                      DataContext
                     (PostgreSQL)

                      AuthService
                           │
                           ▼
                    RedisContext
                  (Rate Limiting)
```

### 6.3 JWT Token Structure

#### Access Token Payload
```json
{
    "sub": "550e8400-e29b-41d4-a716-446655440000",  // player_id
    "sid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  // session_id
    "typ": "access",
    "iat": 1706745600,  // issued at (Unix timestamp)
    "exp": 1706749200   // expires at (Unix timestamp)
}
```

#### Refresh Token Payload
```json
{
    "sub": "550e8400-e29b-41d4-a716-446655440000",  // player_id
    "sid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  // session_id
    "typ": "refresh",
    "iat": 1706745600,
    "exp": 1709337600  // 30 days later
}
```

### 6.4 API Key Format

```
Format: {prefix}{random_base64url}
Example: cc_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6

Components:
- prefix: Configurable, default "cc_" (ChromaCrush)
- random: 32 bytes of cryptographic randomness, base64url encoded

Storage:
- Only bcrypt hash of full key is stored
- Prefix stored separately for identification in UI/logs
- Full key shown only once at creation time
```

### 6.5 Token Validation Flow

```python
async def validate_token(self, token: str) -> AuthToken:
    # 1. Determine token type from format
    if token.startswith(self._api_key_prefix):
        return await self._validate_api_key(token)
    else:
        return await self._validate_jwt(token)

async def _validate_jwt(self, token: str) -> AuthToken:
    # 1. Decode and verify signature
    try:
        payload = jwt.decode(token, self._jwt_secret, algorithms=[self._jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise self._errors.unauthorized("Token has expired", code="AUTH_TOKEN_EXPIRED")
    except jwt.InvalidTokenError as e:
        raise self._errors.unauthorized("Invalid token", code="AUTH_TOKEN_INVALID", reason=str(e))

    # 2. Verify session exists and is not revoked
    session = await self._session_repo.find_by_id(payload["sid"])
    if session is None or session.revoked_at is not None:
        raise self._errors.unauthorized("Invalid token", code="AUTH_TOKEN_INVALID")

    # 3. Build and return AuthToken
    return AuthToken(
        token_type=TokenType.ACCESS,
        player_id=PlayerId(UUID(payload["sub"])),
        issued_at=datetime.fromtimestamp(payload["iat"]),
        expires_at=datetime.fromtimestamp(payload["exp"]),
    )

async def _validate_api_key(self, key: str) -> AuthToken:
    # 1. Extract prefix for database lookup
    prefix = key[:len(self._api_key_prefix) + 8]  # prefix + first 8 chars of random

    # 2. Find candidate keys by prefix
    candidates = await self._api_key_repo.find_by_prefix(prefix)

    # 3. Verify hash against each candidate (usually just 1)
    for candidate in candidates:
        if candidate.revoked_at is not None:
            continue
        if self._verify_api_key_hash(key, candidate.key_hash):
            # 4. Update last_used_at
            await self._api_key_repo.update_last_used(candidate.id)

            return AuthToken(
                token_type=TokenType.API_KEY,
                player_id=PlayerId(candidate.player_id),
                issued_at=candidate.created_at,
                expires_at=None,  # API keys don't expire
            )

    # No match found
    raise self._errors.unauthorized("Invalid API key", code="AUTH_API_KEY_INVALID")
```

### 6.6 Refresh Token Rotation

The module implements refresh token rotation for security:

1. Each refresh token is single-use
2. Using a refresh token invalidates the old session and creates a new one
3. Reuse of an already-used refresh token is logged as potential theft
4. All tokens for a session become invalid when the session is revoked

```python
async def refresh_token(self, refresh_token: str) -> AuthResult:
    # 1. Decode refresh token
    payload = self._decode_jwt(refresh_token)
    if payload["typ"] != "refresh":
        raise self._errors.unauthorized("Invalid token type", code="AUTH_TOKEN_INVALID")

    # 2. Find and validate session
    session = await self._session_repo.find_by_id(payload["sid"])
    if session is None:
        raise self._errors.unauthorized("Session not found", code="AUTH_TOKEN_INVALID")

    if session.revoked_at is not None:
        # This could indicate token theft - log it
        self._logger.warn("Refresh token reuse detected", player_id=session.player_id)
        raise self._errors.unauthorized("Token already used", code="AUTH_TOKEN_INVALID")

    # 3. Revoke old session
    await self._session_repo.revoke(session.id)

    # 4. Create new session with new tokens
    return await self._create_session(session.player_id, session.device_info)
```

---

## 7. CLI Surface

### 7.1 Commands

```bash
# Authentication
chromacrush auth login --username <name> --password <password>
chromacrush auth validate-token <token>
chromacrush auth refresh --refresh-token <token>
chromacrush auth logout <player-id> [--session-id <id>] [--all]

# Session management
chromacrush auth sessions <player-id>

# API key management (for bots)
chromacrush auth create-key <player-id> [--description <desc>]
chromacrush auth list-keys <player-id> [--include-revoked]
chromacrush auth revoke-key <key-id> --player-id <player-id>

# Password utilities
chromacrush auth hash-password <password>
chromacrush auth verify-password <password> <hash>

# Rate limit info
chromacrush auth rate-limit <key-id>
```

### 7.2 CLI Command Implementation

```python
# src/cli/commands/auth_commands.py
import click
from uuid import UUID

@click.group()
def auth():
    """Authentication management commands."""
    pass

@auth.command()
@click.option("--username", required=True, help="Player username")
@click.option("--password", required=True, help="Player password")
@click.pass_context
async def login(ctx, username: str, password: str):
    """Authenticate and get tokens."""
    auth_service = ctx.obj["auth_service"]

    result = await auth_service.authenticate(username, password)

    click.echo(f"Authentication successful!")
    click.echo(f"  Access Token: {result.access_token[:20]}...")
    click.echo(f"  Refresh Token: {result.refresh_token[:20]}...")
    click.echo(f"  Expires In: {result.expires_in} seconds")
    click.echo(f"  Token Type: {result.token_type}")

@auth.command("validate-token")
@click.argument("token")
@click.pass_context
async def validate_token(ctx, token: str):
    """Validate a JWT or API key."""
    auth_service = ctx.obj["auth_service"]

    auth_token = await auth_service.validate_token(token)

    click.echo(f"Token valid!")
    click.echo(f"  Type: {auth_token.token_type.value}")
    click.echo(f"  Player ID: {auth_token.player_id}")
    click.echo(f"  Issued At: {auth_token.issued_at}")
    if auth_token.expires_at:
        click.echo(f"  Expires At: {auth_token.expires_at}")
    else:
        click.echo(f"  Expires At: Never (API key)")

@auth.command("create-key")
@click.argument("player_id")
@click.option("--description", help="Key description")
@click.pass_context
async def create_key(ctx, player_id: str, description: str | None):
    """Create an API key for a bot player."""
    auth_service = ctx.obj["auth_service"]

    result = await auth_service.create_api_key(
        PlayerId(UUID(player_id)),
        description=description,
    )

    click.echo(f"API key created!")
    click.echo(f"  Key ID: {result.key_info.key_id}")
    click.echo(f"  Prefix: {result.key_info.prefix}")
    click.echo(f"")
    click.echo(f"  IMPORTANT: Save this key now. It will not be shown again:")
    click.echo(f"  {result.raw_key}")

@auth.command("list-keys")
@click.argument("player_id")
@click.option("--include-revoked", is_flag=True, help="Include revoked keys")
@click.pass_context
async def list_keys(ctx, player_id: str, include_revoked: bool):
    """List API keys for a player."""
    auth_service = ctx.obj["auth_service"]

    keys = await auth_service.list_api_keys(
        PlayerId(UUID(player_id)),
        include_revoked=include_revoked,
    )

    if not keys:
        click.echo("No API keys found.")
        return

    click.echo(f"API keys for player {player_id}:")
    for key in keys:
        status = "[REVOKED]" if key.revoked else "[ACTIVE]"
        last_used = key.last_used_at.isoformat() if key.last_used_at else "Never"
        click.echo(f"  {status} {key.key_id}")
        click.echo(f"    Prefix: {key.prefix}")
        click.echo(f"    Created: {key.created_at.isoformat()}")
        click.echo(f"    Last Used: {last_used}")

@auth.command("sessions")
@click.argument("player_id")
@click.pass_context
async def sessions(ctx, player_id: str):
    """List active sessions for a player."""
    auth_service = ctx.obj["auth_service"]

    sessions = await auth_service.get_active_sessions(PlayerId(UUID(player_id)))

    if not sessions:
        click.echo("No active sessions.")
        return

    click.echo(f"Active sessions for player {player_id}:")
    for session in sessions:
        click.echo(f"  Session: {session.session_id}")
        click.echo(f"    Created: {session.created_at.isoformat()}")
        click.echo(f"    Last Used: {session.last_used_at.isoformat()}")
        click.echo(f"    Expires: {session.expires_at.isoformat()}")
        if session.device_info:
            click.echo(f"    Device: {session.device_info}")
```

---

## 8. Edge Cases & Decisions

### 8.1 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| JWT vs session-based auth | JWT for access, DB sessions for refresh | JWTs are stateless for API scalability; session DB enables revocation |
| Refresh token rotation | Single-use with rotation | Prevents token theft; reuse detection alerts to compromise |
| API key format | Prefix + random bytes | Prefix enables UI display and log safety; random provides security |
| API key storage | bcrypt hash only | Raw key never stored; only way to validate is hash comparison |
| Bot/human separation | Strict path separation | Bots cannot use password auth; humans cannot use API keys |
| Rate limiting storage | Redis | Fast atomic operations; automatic TTL for window reset |
| Password hashing | bcrypt with configurable rounds | Industry standard; rounds can be increased over time |
| Session cleanup | Background job | Expired sessions cleaned up periodically, not on every request |
| Multiple sessions | Allowed with configurable limit | Users may have multiple devices; limit prevents abuse |

### 8.2 Edge Cases

| Scenario | Handling |
|----------|----------|
| Human tries to create API key | Reject with `FORBIDDEN_NOT_BOT` |
| Bot tries password authentication | Reject with `AUTH_INVALID_CREDENTIALS` (treated same as wrong password) |
| Refresh token reused | Reject, log as potential theft, revoke original session |
| API key used after revocation | Reject with `AUTH_API_KEY_REVOKED` |
| Session limit exceeded | Revoke oldest session when creating new one |
| Expired session with valid access token | Access token still valid until its expiry (stateless) |
| Rate limit exceeded | Return `RATE_LIMIT_API_KEY` with `retry_after` in context |
| Password verification timing attack | Use constant-time bcrypt comparison |
| JWT with unknown session_id | Reject with `AUTH_TOKEN_INVALID` |
| Concurrent refresh attempts | First succeeds, second sees revoked session and fails |
| API key prefix collision | Hash comparison resolves; prefix is convenience, not uniqueness |

### 8.3 Security Considerations

| Consideration | Implementation |
|---------------|----------------|
| JWT secret storage | Required via environment variable, never in code/config files |
| Password in logs | Never logged; only username on failed attempts |
| API key in logs | Only prefix logged, never full key |
| Timing attacks | Constant-time password comparison via bcrypt |
| Token in URL | Tokens should be in Authorization header, not URL parameters |
| Refresh token storage | Should use HTTP-only cookie on web clients |
| Session fixation | New session ID on every login and refresh |

### 8.4 Escalation Required

None. All edge cases are covered by existing error taxonomy and guidance documents.

---

## 9. Open Questions

None. All design decisions have been resolved based on:
- Key Decision #5 in STATE.md (JWT + API keys hybrid)
- Interface contracts guidance (AuthToken, ApiKeyInfo types, error taxonomy)
- Configuration guidance (auth namespace config keys)
- Data layer guidance (repository pattern, Redis for rate limiting)
- Best practices guidance (injection patterns, async contract)
- Player module artifact (dependency for credential storage)

---

## Async Behavior Summary

All public methods except `hash_password` and `verify_password` are `async def` because they involve database or Redis operations. The password methods are sync because they are CPU-bound (bcrypt) with no I/O.

This module follows the async contract:
- All repository calls are awaited
- All Redis operations are awaited
- No fire-and-forget operations
- Transaction boundaries managed via DataContext
- Errors propagate correctly through async chain

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent |
