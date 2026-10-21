# Auth Module Implementation Document

**Module:** auth
**Phase:** 2.2
**Author:** Coding Agent
**Date:** 2026-02-05

---

## 1. Summary

The auth module provides dual authentication for ChromaCrush: JWT-based username/password authentication for human players and API key authentication for bot players. It manages session lifecycle (create, validate, refresh, revoke), API key lifecycle (create, list, revoke), rate limiting via Redis, and password hashing/verification via bcrypt.

All public methods are async except `hash_password` and `verify_password`, which are synchronous CPU-bound operations. The module delegates persistence to injected repository protocols (`SessionRepositoryProtocol`, `ApiKeyRepositoryProtocol`) and uses a `PasswordStoreProtocol` to access password hashes without leaking them into the Player domain type. Rate limiting state is stored in Redis using a sliding window counter pattern.

---

## 2. Files Created

### Module Code (`src/modules/auth/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Package init; exports `AuthService`, `AuthServiceProtocol`, `PasswordStoreProtocol`, `AuthResult`, `ApiKeyCreationResult`, `SessionInfo`, `RateLimitStatus`, `TokenPayload` |
| `service.py` | Main `AuthService` class with all business logic for authentication, session management, API key management, rate limiting, and password operations |
| `protocols.py` | Defines `AuthServiceProtocol` (public interface for DI) and `PasswordStoreProtocol` (interface for password hash access) |
| `dto.py` | Data transfer objects: `AuthResult`, `ApiKeyCreationResult`, `SessionInfo`, `RateLimitStatus`, `TokenPayload` |
| `jwt_handler.py` | Internal `JwtHandler` class for JWT creation/decoding using PyJWT; not part of public interface |
| `api_key_generator.py` | Internal functions `generate_api_key`, `hash_api_key`, `verify_api_key` using `secrets` and `bcrypt`; not part of public interface |
| `password_handler.py` | Internal functions `hash_password`, `verify_password`, `validate_password_strength` using `bcrypt`; not part of public interface |

### Data Layer (`src/data/`)

| File | Purpose |
|------|---------|
| `models/session.py` | SQLAlchemy ORM model `SessionModel` for the `sessions` table (player_id, refresh_token_hash, device_info, last_used_at, expires_at, revoked_at) |
| `models/api_key.py` | SQLAlchemy ORM model `ApiKeyModel` for the `api_keys` table (player_id, key_hash, key_prefix, description, last_used_at, revoked_at) |
| `protocols/session_repository.py` | `SessionRepositoryProtocol` (async Protocol) and `SessionRecord` dataclass |
| `protocols/api_key_repository.py` | `ApiKeyRepositoryProtocol` (async Protocol) and `ApiKeyRecord` dataclass |
| `repositories/session_repository.py` | `SQLAlchemySessionRepository` concrete implementation of `SessionRepositoryProtocol` |
| `repositories/api_key_repository.py` | `SQLAlchemyApiKeyRepository` concrete implementation of `ApiKeyRepositoryProtocol` |
| `migrations/versions/003_auth_sessions_and_api_keys.py` | Alembic migration (revision 003, depends on 002) creating `sessions` and `api_keys` tables with partial indexes |

### CLI (`src/cli/commands/`)

| File | Purpose |
|------|---------|
| `auth_commands.py` | Click command group `auth` with 12 commands: `hash-password`, `verify-password`, `show-config`, `login`, `validate-token`, `refresh`, `logout`, `sessions`, `create-key`, `list-keys`, `revoke-key`, `rate-limit`. Uses Rich tables for output formatting. |

### Tests (`tests/unit/modules/auth/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Empty package init |
| `test_jwt_handler.py` | 9 tests across 3 classes (`TestCreateAccessToken`: 2, `TestCreateRefreshToken`: 2, `TestDecodeToken`: 5 covering valid access decode, valid refresh decode, expired token, invalid signature, malformed token) |
| `test_password_handler.py` | 14 tests across 3 classes (`TestHashPassword`: 4, `TestVerifyPassword`: 4, `TestValidatePasswordStrength`: 6 covering valid password, min length, uppercase, lowercase, digit, custom min length) |
| `test_api_key_generator.py` | 9 tests across 2 classes (`TestGenerateApiKey`: 5, `TestHashAndVerifyApiKey`: 4 covering generation, hashing, verification, invalid hash) |
| `test_auth_service.py` | 36 tests across 10 classes (`TestAuthenticate`: 6, `TestValidateToken`: 6, `TestRefreshToken`: 3, `TestLogout`: 2, `TestCreateApiKey`: 4, `TestRevokeApiKey`: 3, `TestListApiKeys`: 2, `TestRateLimiting`: 4, `TestPasswordOperations`: 4, `TestGetActiveSessions`: 2) |

**Total test count: 68 test functions across 4 test files.**

---

## 3. Deviations from Artifact

Not assessed -- document produced from code examination only.

---

## 4. Public Interface

### `AuthService` (in `service.py`)

```python
class AuthService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        session_repo: SessionRepositoryProtocol,
        api_key_repo: ApiKeyRepositoryProtocol,
        password_store: PasswordStoreProtocol,
        redis: Any,
    ) -> None

    # Human Authentication
    async def authenticate(self, username: str, password: str) -> AuthResult
    async def validate_token(self, token: str) -> AuthToken
    async def refresh_token(self, refresh_token: str) -> AuthResult
    async def logout(self, player_id: PlayerId, session_id: UUID | None = None) -> None
    async def get_active_sessions(self, player_id: PlayerId) -> list[SessionInfo]

    # API Key Management (Bots)
    async def create_api_key(self, player_id: PlayerId, description: str | None = None) -> ApiKeyCreationResult
    async def revoke_api_key(self, key_id: UUID, player_id: PlayerId) -> None
    async def list_api_keys(self, player_id: PlayerId, include_revoked: bool = False) -> list[ApiKeyInfo]

    # Rate Limiting
    async def check_rate_limit(self, key_id: UUID) -> RateLimitStatus
    async def record_api_request(self, key_id: UUID) -> RateLimitStatus

    # Password Operations (sync)
    def hash_password(self, password: str) -> str
    def verify_password(self, password: str, password_hash: str) -> bool
```

### `AuthServiceProtocol` (in `protocols.py`)

Mirrors all public methods of `AuthService` exactly. Defined as `typing.Protocol` for dependency injection.

### `PasswordStoreProtocol` (in `protocols.py`)

```python
class PasswordStoreProtocol(Protocol):
    async def get_password_hash(self, player_id: UUID) -> str | None
    async def set_password_hash(self, player_id: UUID, password_hash: str) -> None
```

### DTOs (in `dto.py`)

```python
@dataclass
class AuthResult:
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    @property
    def authorization_header(self) -> str

@dataclass
class ApiKeyCreationResult:
    key_info: ApiKeyInfo
    raw_key: str

@dataclass
class SessionInfo:
    session_id: UUID
    player_id: UUID
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    device_info: str | None = None

@dataclass
class RateLimitStatus:
    key_id: UUID
    requests_remaining: int
    requests_limit: int
    window_seconds: int
    reset_at: datetime
    is_exceeded: bool  # computed in __post_init__, True when requests_remaining <= 0

@dataclass
class TokenPayload:
    player_id: UUID
    session_id: UUID
    token_type: str
    issued_at: datetime
    expires_at: datetime
```

### Internal `JwtHandler` (in `jwt_handler.py`)

```python
class JwtHandler:
    def __init__(self, secret: str, algorithm: str = "HS256") -> None
    def create_access_token(self, player_id: UUID, session_id: UUID, expiry_minutes: int) -> str
    def create_refresh_token(self, player_id: UUID, session_id: UUID, expiry_days: int) -> str
    def decode_token(self, token: str) -> TokenPayload
```

### Internal Functions (in `api_key_generator.py`)

```python
def generate_api_key(prefix: str, key_length: int = 32) -> tuple[str, str]
def hash_api_key(key: str) -> str
def verify_api_key(key: str, key_hash: str) -> bool
```

### Internal Functions (in `password_handler.py`)

```python
def hash_password(password: str, rounds: int = 12) -> str
def verify_password(password: str, password_hash: str) -> bool
def validate_password_strength(password: str, min_length: int = 8) -> tuple[bool, str | None]
```

---

## 5. Dependencies Injected

### `AuthService.__init__`

| Parameter | Protocol Type | Purpose |
|-----------|--------------|---------|
| `config` | `ConfigProtocol` | Read auth configuration values |
| `logger` | `LoggerProtocol` | Structured logging (info, warn, debug) |
| `errors` | `ErrorServiceProtocol` | Error factory (unauthorized, forbidden, not_found, validation, rate_limited) |
| `player_service` | `PlayerServiceProtocol` | Player lookups by ID and username |
| `session_repo` | `SessionRepositoryProtocol` | Session CRUD and lifecycle operations |
| `api_key_repo` | `ApiKeyRepositoryProtocol` | API key CRUD and lifecycle operations |
| `password_store` | `PasswordStoreProtocol` | Get/set password hashes without exposing them through the Player type |
| `redis` | `Any` (typed as generic Redis client) | Rate limiting counter storage |

### `SQLAlchemySessionRepository.__init__`

| Parameter | Protocol Type | Purpose |
|-----------|--------------|---------|
| `data_ctx` | `DataContextProtocol` | Database session management |
| `logger` | `LoggerProtocol` | Structured logging |
| `errors` | `ErrorServiceProtocol` | Error factory |

### `SQLAlchemyApiKeyRepository.__init__`

| Parameter | Protocol Type | Purpose |
|-----------|--------------|---------|
| `data_ctx` | `DataContextProtocol` | Database session management |
| `logger` | `LoggerProtocol` | Structured logging |
| `errors` | `ErrorServiceProtocol` | Error factory |

---

## 6. Configuration Keys Used

All keys are read in `AuthService.__init__` and cached as instance attributes.

| Key | Default | Stored As |
|-----|---------|-----------|
| `auth.jwt_secret` | *(required, no default -- uses `config.require()`)* | Used to construct `JwtHandler` |
| `auth.jwt_algorithm` | `"HS256"` | `self._jwt_algorithm` |
| `auth.access_token_expiry_minutes` | `60` | `self._access_token_expiry_minutes` |
| `auth.refresh_token_expiry_days` | `30` | `self._refresh_token_expiry_days` |
| `auth.api_key_prefix` | `"cc_"` | `self._api_key_prefix` |
| `auth.api_key_length` | `32` | `self._api_key_length` |
| `auth.bcrypt_rounds` | `12` | `self._bcrypt_rounds` |
| `auth.password_min_length` | `8` | `self._password_min_length` |
| `auth.rate_limit_requests` | `100` | `self._rate_limit_requests` |
| `auth.rate_limit_window_seconds` | `60` | `self._rate_limit_window_seconds` |
| `auth.max_sessions_per_player` | `5` | `self._max_sessions_per_player` |

---

## 7. Error Codes Used

| Code | Method(s) | Error Factory Method |
|------|-----------|---------------------|
| `AUTH_INVALID_CREDENTIALS` | `authenticate` (player not found, bot attempting password auth, no password set, wrong password) | `errors.unauthorized()` |
| `AUTH_TOKEN_INVALID` | `validate_token` (revoked session), `refresh_token` (wrong token type, session not found, token already used) | `errors.unauthorized()` |
| `AUTH_TOKEN_EXPIRED` | `JwtHandler.decode_token` (expired JWT) | Raised directly as `AppError(code="AUTH_TOKEN_EXPIRED", http_status=401)` |
| `AUTH_TOKEN_INVALID` | `JwtHandler.decode_token` (invalid signature, malformed JWT) | Raised directly as `AppError(code="AUTH_TOKEN_INVALID", http_status=401)` |
| `AUTH_API_KEY_REVOKED` | `_validate_api_key` (key found but revoked) | `errors.unauthorized()` |
| `AUTH_API_KEY_INVALID` | `_validate_api_key` (no matching key found) | `errors.unauthorized()` |
| `FORBIDDEN_NOT_BOT` | `create_api_key` (human player trying to create API key) | `errors.forbidden()` |
| `FORBIDDEN_NOT_KEY_OWNER` | `revoke_api_key` (player does not own the key) | `errors.forbidden()` |
| `NOT_FOUND_API_KEY` | `revoke_api_key`, `check_rate_limit`, `record_api_request` (key_id not found) | `errors.not_found()` |
| `VALIDATION_INVALID_INPUT` | `create_api_key` (description exceeds 255 characters) | `errors.validation()` |
| `VALIDATION_WEAK_PASSWORD` | `hash_password` (password fails strength validation) | `errors.validation()` |
| `RATE_LIMIT_API_KEY` | `record_api_request` (rate limit exceeded) | `errors.rate_limited()` |

Note: `JwtHandler` raises `AppError` directly (imported from `src.core.errors`) rather than using the injected error service, since it is an internal helper without access to the error service.

---

## 8. Async Behavior

- **Async methods** (all involving database or Redis I/O): `authenticate`, `validate_token`, `refresh_token`, `logout`, `get_active_sessions`, `create_api_key`, `revoke_api_key`, `list_api_keys`, `check_rate_limit`, `record_api_request`, and all private helpers (`_create_session`, `_validate_jwt`, `_validate_api_key`, `_get_rate_limit_status`).
- **Sync methods** (CPU-bound, no I/O): `hash_password`, `verify_password`.
- The CLI commands bridge sync Click to async service methods using `asyncio.run()` via the `_run_async` helper.
- All repository methods (`SessionRepositoryProtocol`, `ApiKeyRepositoryProtocol`) are async.
- Redis operations (`get`, `set`) are awaited as async calls.

---

## 9. Internal Design Notes

### JWT Structure
- JWT payloads use short claim names per JWT convention: `sub` (player_id), `sid` (session_id), `typ` ("access" or "refresh"), `iat` (issued at, Unix timestamp), `exp` (expires at, Unix timestamp).
- `JwtHandler` is instantiated once in `AuthService.__init__` with the secret and algorithm.
- Access tokens have minute-based expiry; refresh tokens have day-based expiry.

### Refresh Token Rotation
- On refresh, the old session is revoked and a new session is created with new tokens.
- Reuse of a revoked refresh token is detected and logged as potential token theft (logged as a warn-level event).
- Refresh tokens are stored as SHA-256 hashes (not bcrypt) because JWTs can exceed bcrypt's 72-byte limit and are already high-entropy.

### Session Management
- Sessions have a configurable per-player maximum (`max_sessions_per_player`, default 5). When the limit is reached, the oldest session is revoked before creating a new one.
- Session validity checks verify both existence and non-revocation.
- `get_active_sessions` filters out expired sessions in application code after querying the repository.

### API Key Design
- Keys are generated with `secrets.token_bytes` + base64url encoding, prefixed with a configurable prefix (default `"cc_"`).
- The stored `key_prefix` is the configured prefix plus the first 8 characters of the random part, used for efficient database lookup during validation.
- API key hashes use bcrypt (via `api_key_generator.hash_api_key`).
- Validation performs a prefix-based database lookup then iterates candidates, checking each against the bcrypt hash. Revoked keys are checked to provide a specific "revoked" error rather than "invalid".
- API keys do not expire (AuthToken.expires_at is None for API_KEY type).

### Rate Limiting
- Uses Redis with key pattern `chromacrush:ratelimit:{key_id}`.
- Simple counter with TTL-based window: first request sets the key with TTL, subsequent requests increment and reset TTL.
- When the counter exceeds the limit, `errors.rate_limited()` is raised with a `retry_after` parameter.
- Note: The current implementation resets TTL on every request (`ex=self._rate_limit_window_seconds`), which creates a rolling window rather than a fixed window.

### Password Handling
- Passwords are hashed with bcrypt using a configurable work factor (`bcrypt_rounds`, default 12).
- Password strength validation requires: minimum length (configurable, default 8), at least one uppercase letter, at least one lowercase letter, at least one digit.
- `verify_password` and `verify_api_key` both catch `ValueError`/`TypeError` exceptions and return `False` to handle invalid hash strings gracefully.

### CLI Architecture
- The `_run_async` helper creates a full `ApplicationContext`, builds the `AuthService` via `_build_auth_service`, runs the coroutine, and ensures proper shutdown.
- `_build_auth_service` constructs all dependencies including repositories, a `PlayerService`, and an inline `_PasswordStore` class that directly queries the `PlayerModel` for password hashes.
- Three commands (`hash-password`, `verify-password`, `show-config`) are synchronous and do not require a database connection.
- Nine commands (`login`, `validate-token`, `refresh`, `logout`, `sessions`, `create-key`, `list-keys`, `revoke-key`, `rate-limit`) are async and use the `_run_async` bridge.
- Output is formatted using Rich (`Console`, `Table`) for structured terminal display.

### Notable Import Patterns
- `service.py` uses `TYPE_CHECKING` guards for all protocol imports, keeping them as type-only dependencies.
- `jwt_handler.py` imports `AppError` directly from `src.core.errors` (the only direct core import in the module) because it is an internal helper that does not receive the error service via injection.
- Core types (`AuthToken`, `TokenType`, `ApiKeyInfo`, `PlayerId`) are imported at runtime from `src.core.types.*`.
