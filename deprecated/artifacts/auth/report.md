# Auth Module Report

> **Module:** auth
> **Author:** Scout Agent
> **Date:** 2026-02-05
> **Build Wave:** 2

---

## Summary

The auth module artifact has been designed to handle ChromaCrush's dual-authentication system for human players (JWT tokens) and bot players (API keys), as specified in Key Decision #5.

### Key Outcomes

1. **Dual Auth System Designed** - Complete separation between human (password/JWT) and bot (API key) authentication paths, with no crossover allowed.

2. **Security-First Approach** - Refresh token rotation, bcrypt hashing for both passwords and API keys, constant-time comparisons, and comprehensive audit logging.

3. **Rate Limiting Foundation** - Redis-backed per-API-key rate limiting designed to support the API layer's enforcement of bot request limits.

4. **Session Management** - Full session lifecycle management including multi-device support with configurable limits, revocation capability, and expired session cleanup.

5. **Clean Dependency Graph** - Single module dependency (player) for credential storage and player type verification. No circular dependencies.

---

## Alternatives Considered

### 1. OAuth2/OIDC Instead of Custom JWT

**Considered:** Using a full OAuth2 implementation with authorization server.

**Rejected because:**
- Adds significant complexity for a game with simple auth needs
- ChromaCrush has only two client types (human web app, bot API) with predictable flows
- No third-party identity providers needed initially
- Custom JWT gives full control over token structure and claims

**Future option:** OAuth2 could be added later for third-party integrations without breaking existing auth.

### 2. Stateless Refresh Tokens

**Considered:** Making refresh tokens fully stateless (like access tokens) to avoid session table.

**Rejected because:**
- Prevents revocation capability (critical for security)
- Prevents refresh token rotation (single-use pattern)
- Cannot detect token reuse (potential theft indicator)
- Session table overhead is minimal with proper indexing

### 3. API Keys Without Hash Storage

**Considered:** Storing API keys in plaintext for simpler validation.

**Rejected because:**
- Security best practice requires hashed storage
- Database breach would expose all API keys
- Bcrypt overhead is acceptable for API key validation (less frequent than JWT)

### 4. Single Token Type for Both Humans and Bots

**Considered:** Using JWT for both human and bot authentication.

**Rejected because:**
- Bots need long-lived, stateless authentication (no refresh cycle)
- Human sessions need revocation and rotation for security
- API keys are simpler for bot operators to manage
- Clear separation prevents accidental misuse

### 5. Rate Limiting in Auth Module (Enforcement)

**Considered:** Having auth module enforce rate limits directly.

**Rejected because:**
- Rate limiting is a cross-cutting concern better handled at API gateway level
- Auth module provides rate limit data; API layer enforces
- Keeps auth module focused on authentication responsibility
- More flexible for different rate limit policies per endpoint

---

## Risks

### 1. JWT Secret Management

**Risk:** JWT secret exposure would allow token forgery for any user.

**Mitigation:**
- Secret required via environment variable (never in code/config)
- Documentation will emphasize secure secret generation and rotation
- Secret rotation procedure should be documented in operations guide

### 2. Bcrypt Performance Under Load

**Risk:** Password/API key verification is CPU-intensive; could slow down auth under heavy load.

**Mitigation:**
- Bcrypt rounds configurable (can reduce for development, increase for production)
- API key validation happens less frequently than JWT validation
- Consider async bcrypt wrapper if profiling shows bottleneck
- API keys indexed by prefix to minimize hash comparisons

### 3. Session Table Growth

**Risk:** Sessions table could grow unboundedly with active usage.

**Mitigation:**
- Background cleanup job removes expired sessions (7+ days old)
- Index on `expires_at` for efficient cleanup queries
- Monitor table size in production

### 4. Refresh Token Theft Window

**Risk:** Between refresh token issuance and rotation, stolen token could be used.

**Mitigation:**
- Short refresh window (reuse detected on second use)
- Suspicious reuse logged for security monitoring
- All sessions for user can be revoked if compromise detected

### 5. Redis Dependency for Rate Limiting

**Risk:** Redis unavailability could prevent rate limit checking.

**Mitigation:**
- Fail-open strategy: if Redis is down, allow requests (log warning)
- Rate limiting is protection, not core functionality
- Redis is already required for other features (leaderboards, matchmaking queue)

---

## Dependencies & Sequencing Notes

### Build Order Position

- **Wave:** 2
- **Depends on:** `player` (Wave 1)
- **Depended on by:** `match`, `api` (Wave 5+)

### Pre-Implementation Requirements

1. **Player module must be implemented first** - Auth depends on `PlayerServiceProtocol` for:
   - `get_player_by_username()` for login
   - `Player.player_type` for bot/human enforcement
   - `Player.password_hash` for credential verification

2. **Core services must exist:**
   - ConfigService with auth namespace populated
   - ErrorService with auth error types registered
   - DataContext for PostgreSQL sessions
   - RedisContext for rate limiting

3. **Repository implementations needed:**
   - `SessionRepository` (PostgreSQL)
   - `ApiKeyRepository` (PostgreSQL)
   - Rate limit operations (Redis)

### Migration Sequence

Auth tables should be created after player tables (foreign key dependency):

```
001_players.py          # Player module
002_player_stats.py     # Player module
003_energy_states.py    # Player module
004_sessions.py         # Auth module (FK to players)
005_api_keys.py         # Auth module (FK to players)
```

### Integration Points

| Consumer | Integration | Notes |
|----------|-------------|-------|
| API layer | Token validation middleware | Every authenticated request calls `validate_token()` |
| API layer | Rate limit middleware | Bot requests call `record_api_request()` |
| Match module | Player ID from token | `AuthToken.player_id` identifies authenticated player |
| All modules | Error propagation | Auth errors bubble up with proper HTTP status |

### Testing Considerations

- Auth service tests need mock `PlayerService` for credential lookup
- JWT tests should use test-only secret key
- API key tests should verify bcrypt hashing works correctly
- Rate limit tests need mock Redis or test Redis instance
- Session tests should cover rotation and reuse detection

---

## Coordination Notes for Other Modules

### For API Module (Wave 9)

The auth module provides the authentication foundation. The API module will need to:

1. Create authentication middleware using `validate_token()`
2. Create rate limiting middleware using `record_api_request()`
3. Handle auth errors and return proper WWW-Authenticate headers
4. Implement refresh token endpoint
5. Consider cookie-based refresh for web clients

### For Match Module (Wave 5)

The match module should:

1. Extract `player_id` from validated `AuthToken`
2. Not re-validate authentication (already done by middleware)
3. Use `player_id` for authorization checks (is this player in this match?)

### For Orchestrator

1. **Config schema update needed:** Add auth namespace keys to `docs/guidance/configuration.md` if not already present
2. **Migration coordination:** Auth tables depend on player tables
3. **Redis required:** Confirm Redis infrastructure for rate limiting

---

## Complexity Assessment

| Component | Complexity | Notes |
|-----------|------------|-------|
| JWT handling | Medium | Standard library usage, but rotation logic adds complexity |
| API key system | Medium | Hash-based lookup, prefix indexing for performance |
| Session management | Low | Standard CRUD with soft delete |
| Rate limiting | Low | Redis INCR with TTL |
| Password hashing | Low | bcrypt library usage |
| **Overall** | **Medium** | Most complexity is in security-conscious design, not algorithmic |

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial report | Scout Agent |
