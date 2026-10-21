# Module Architecture Report: auth

**Module:** auth
**Build Wave:** 2
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The auth module provides dual authentication for ChromaCrush: JWT-based username/password authentication for human players and API key authentication for bot players. It manages session lifecycle (create, validate, refresh, revoke), API key lifecycle (create, list, revoke), Redis-backed per-API-key rate limiting, and password hashing/verification via bcrypt. All public methods are **asynchronous** (`async def`) except `hash_password` and `verify_password`, which are synchronous CPU-bound operations. The module uses refresh token rotation with single-use semantics and stores refresh token hashes as SHA-256 (not bcrypt, due to JWT length exceeding bcrypt's 72-byte limit).

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `authenticate` | `(username: str, password: str) -> AuthResult` | Authenticate human user with credentials |
| `validate_token` | `(token: str) -> AuthToken` | Validate JWT access token or API key |
| `refresh_token` | `(refresh_token: str) -> AuthResult` | Get new token pair using refresh token |
| `logout` | `(player_id, session_id=None) -> None` | Invalidate session(s) |
| `get_active_sessions` | `(player_id) -> list[SessionInfo]` | List active sessions |
| `create_api_key` | `(player_id, description=None) -> ApiKeyCreationResult` | Create API key for bot player |
| `revoke_api_key` | `(key_id, player_id) -> None` | Revoke an API key |
| `list_api_keys` | `(player_id, include_revoked=False) -> list[ApiKeyInfo]` | List API keys for player |
| `check_rate_limit` | `(key_id) -> RateLimitStatus` | Check rate limit for API key |
| `record_api_request` | `(key_id) -> RateLimitStatus` | Record request for rate limiting |
| `hash_password` | `(password: str) -> str` | Hash password with bcrypt (sync) |
| `verify_password` | `(password: str, password_hash: str) -> bool` | Verify password against hash (sync) |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | JWT secret, token expiry, bcrypt rounds, rate limits |
| `logger` | `LoggerProtocol` | Structured logging (info, warn, debug) |
| `errors` | `ErrorServiceProtocol` | Create unauthorized, forbidden, not_found, validation, rate_limited errors |
| `player_service` | `PlayerServiceProtocol` | Player lookups by ID and username |
| `session_repo` | `SessionRepositoryProtocol` | Session CRUD and lifecycle |
| `api_key_repo` | `ApiKeyRepositoryProtocol` | API key CRUD and lifecycle |
| `password_store` | `PasswordStoreProtocol` | Get/set password hashes (separate from Player type) |
| `redis` | Redis client | Rate limiting counter storage |

---

## 4. Data Owned

| Table/Key | Storage | Description |
|-----------|---------|-------------|
| `sessions` | PostgreSQL | Session records: player_id, refresh_token_hash, device_info, last_used_at, expires_at, revoked_at |
| `api_keys` | PostgreSQL | API key records: player_id, key_hash, key_prefix, description, last_used_at, revoked_at |
| `chromacrush:ratelimit:{key_id}` | Redis | Rate limit counter with TTL-based sliding window |

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `auth.jwt_secret` | string | *(required)* | JWT signing secret |
| `auth.jwt_algorithm` | string | HS256 | JWT signing algorithm |
| `auth.access_token_expiry_minutes` | int | 60 | Access token lifetime |
| `auth.refresh_token_expiry_days` | int | 30 | Refresh token lifetime |
| `auth.api_key_prefix` | string | cc_ | API key prefix for bots |
| `auth.api_key_length` | int | 32 | Generated API key length |
| `auth.bcrypt_rounds` | int | 12 | Bcrypt hashing work factor |
| `auth.password_min_length` | int | 8 | Minimum password length |
| `auth.rate_limit_requests` | int | 100 | API key rate limit (requests per window) |
| `auth.rate_limit_window_seconds` | int | 60 | Rate limit window duration |
| `auth.max_sessions_per_player` | int | 5 | Max concurrent sessions |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `AUTH_INVALID_CREDENTIALS` | 401 | Player not found, bot attempting password auth, wrong password |
| `AUTH_TOKEN_INVALID` | 401 | Invalid JWT signature, malformed JWT, revoked session, wrong token type |
| `AUTH_TOKEN_EXPIRED` | 401 | JWT past expiry |
| `AUTH_API_KEY_INVALID` | 401 | No matching API key found |
| `AUTH_API_KEY_REVOKED` | 401 | Revoked API key used |
| `FORBIDDEN_NOT_BOT` | 403 | Human trying to create API key |
| `FORBIDDEN_NOT_KEY_OWNER` | 403 | Non-owner managing API key |
| `NOT_FOUND_API_KEY` | 404 | API key ID not found |
| `VALIDATION_INVALID_INPUT` | 400 | Description exceeds 255 characters |
| `VALIDATION_WEAK_PASSWORD` | 400 | Password fails strength requirements |
| `RATE_LIMIT_API_KEY` | 429 | Rate limit exceeded |

---

## 7. Cross-Module Interactions

**Called by:**
- `match` -- extracts `player_id` from validated `AuthToken`
- `api` -- authentication middleware calls `validate_token()`, rate limit middleware calls `record_api_request()`

**Calls:**
- `player` -- calls `get_player_by_username()`, `get_player()` for credential verification and player type checks

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `AuthResult` | `src/modules/auth/dto.py` | Result of authentication: access_token, refresh_token, expires_in |
| `ApiKeyCreationResult` | `src/modules/auth/dto.py` | Created key info + raw key (returned once) |
| `SessionInfo` | `src/modules/auth/dto.py` | Active session details |
| `RateLimitStatus` | `src/modules/auth/dto.py` | Rate limit state: remaining, limit, reset_at, is_exceeded |
| `TokenPayload` | `src/modules/auth/dto.py` | Decoded JWT payload (internal use) |
| `AuthServiceProtocol` | `src/modules/auth/protocols.py` | Protocol mirroring all 12 public methods for DI |
| `PasswordStoreProtocol` | `src/modules/auth/protocols.py` | Protocol for password hash access without leaking into Player type |
