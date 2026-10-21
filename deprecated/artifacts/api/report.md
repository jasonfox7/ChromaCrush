# Module Report: API

## Header
- **Author:** Scout Agent
- **Date:** 2026-02-05

---

## Summary

The API module artifact has been designed as the **terminal node** (Wave 9) of ChromaCrush, providing a REST API that exposes all game functionality to both human web clients and bot players (LLMs).

### Key Outcomes

1. **Complete Route Coverage** - Designed 50+ endpoints across 11 route groups covering all 10 dependent modules plus health checks.

2. **Bot-First Design** - Structured responses with optional `bot_hints` field for API key authenticated requests, providing strategic guidance for LLM decision-making.

3. **Dual Authentication** - JWT for human sessions, API keys for bots, with clear precedence rules and middleware design.

4. **Rate Limiting** - Per-key rate limiting integrated via auth service, with appropriate skip rules for health checks and rate-limited match endpoints.

5. **Consistent Response Structure** - All responses wrapped in `ApiResponse` envelope with correlation ID, timestamp, and structured error details.

6. **OpenAPI Documentation** - FastAPI auto-generates OpenAPI/Swagger docs, with CLI command to export schema.

---

## Alternatives Considered

### 1. GraphQL vs REST

**Considered:** GraphQL for flexible querying, especially for bot clients that might want specific data subsets.

**Rejected:**
- REST is simpler to document and understand for bot developers
- Match state responses are relatively uniform; no need for flexible field selection
- OpenAPI generation is more mature for REST
- Rate limiting is simpler per-endpoint rather than per-query-complexity

### 2. WebSocket vs Polling for Match State

**Considered:** WebSocket connections for real-time match state updates.

**Rejected for MVP:**
- Adds significant complexity to bot client implementations
- Polling with bot hints is sufficient for turn-based gameplay
- Can be added in future version without breaking existing API

**Note:** The artifact design allows for future WebSocket addition via `/api/v1/ws/match/{match_id}` without restructuring.

### 3. Separate Bot API vs Unified API

**Considered:** Separate `/api/v1/bot/*` endpoints with different response schemas.

**Rejected:**
- Duplicates route logic
- Harder to maintain parity
- Bot hints as optional field is cleaner
- Auth type (JWT vs API key) naturally distinguishes clients

### 4. Bot Hint Computation Location

**Considered:**
- (A) Generate hints in match service
- (B) Generate hints in API layer
- (C) Separate hint service

**Chose (B):**
- Hints are presentation-layer concern
- Match service returns raw data; API layer adds bot-specific formatting
- Keeps match service clean and reusable
- Avoids coupling business logic to bot requirements

---

## Risks

### 1. Bot Hint Performance

**Risk:** Bot hint generation adds latency to match state responses.

**Mitigation:**
- Hints are generated synchronously but are lightweight (board scanning, no DB calls)
- Top 5 moves only, not exhaustive search
- Config flag to disable hints if needed
- Monitoring via `DEBUG: "Bot hints generated"` log with duration

**Severity:** Low - design keeps hints simple

### 2. Rate Limiting Fairness

**Risk:** Aggressive bot players could still impact server resources even within rate limits.

**Mitigation:**
- Rate limits are per API key, not per account
- Match-related endpoints have separate consideration
- Burst allowance prevents legitimate use cases from failing
- Can adjust limits per key if abuse detected

**Severity:** Low - standard rate limiting patterns

### 3. API Version Migration

**Risk:** Future API versions may require breaking changes.

**Mitigation:**
- `/api/v1/` prefix allows `/api/v2/` parallel deployment
- Response envelope version field enables gradual migration
- OpenAPI schema export enables contract testing

**Severity:** Low - standard versioning approach

### 4. Correlation ID Collision

**Risk:** Correlation ID format `cc_{timestamp_hex}_{random_hex}` could theoretically collide.

**Mitigation:**
- 4-byte timestamp + 4-byte random = effectively unique
- Collision impact is limited (logging confusion only)
- Can extend random portion if needed

**Severity:** Very Low - statistically negligible

---

## Dependencies & Sequencing Notes

### Direct Dependencies (All 10 Modules)

| Module | Wave | Dependency Type | Status |
|--------|------|-----------------|--------|
| auth | 3 | Service calls | Artifact complete |
| player | 1 | Service calls | Artifact complete |
| energy | 2 | Service calls | Artifact complete |
| matchmaking | 4 | Service calls | Artifact complete |
| match | 5 | Service calls | Artifact complete |
| vault | 6 | Service calls | Artifact complete |
| events | 7 | Service calls | Artifact complete |
| ads | 7 | Service calls | Artifact complete |
| payments | 7 | Service calls | Artifact complete |
| bot_earnings | 8 | Service calls | Artifact complete |

### Build Order Position

The API module is the **terminal node** (Wave 9). It must be implemented last because:

1. It depends on ALL other modules' public interfaces
2. It cannot be tested without functioning services
3. It integrates all error types from all modules

### Implementation Blockers

None. All dependent module artifacts are complete with:
- Public interface protocols defined
- Error codes enumerated
- Async behavior documented
- Config keys specified

### Integration Testing Requirements

The API module requires special integration testing:

1. **End-to-end flow tests** - Register, login, play match, check earnings
2. **Bot simulation tests** - API key auth through full match lifecycle
3. **Rate limit tests** - Verify limits are enforced correctly
4. **Error propagation tests** - Verify all module errors map to correct HTTP status

---

## Coordination Notes

### With Auth Module

- API uses `AuthServiceProtocol.validate_token()` and `validate_api_key()` in middleware
- API uses `AuthServiceProtocol.check_rate_limit()` and `record_api_request()` for rate limiting
- Auth module must expose these methods (confirmed in auth artifact)

### With Match Module

- Bot hints require access to valid moves and board state
- Match service must return enough data for hint generation
- `MatchServiceProtocol.get_valid_moves()` must include `estimated_score` (confirmed in match artifact)

### With All Modules

- Every module's error codes must be in the error taxonomy
- Every module's config keys must be in the config schema
- Verified all error codes exist in interface-contracts.md

---

## Artifact Completeness Checklist

- [x] Purpose documented
- [x] Public interface (route groups, schemas)
- [x] Error cases enumerated
- [x] Async behavior documented
- [x] Configuration keys listed
- [x] Logging events specified
- [x] Data access (none - pure presentation)
- [x] Presentation boundary (this IS presentation)
- [x] Internal design with component diagram
- [x] CLI surface documented
- [x] Edge cases and decisions
- [x] No open questions

---

## Recommendations for Implementation

1. **Start with health endpoints** - Validates FastAPI setup and middleware chain.

2. **Implement auth routes second** - Enables testing of authenticated endpoints.

3. **Add match routes third** - Most complex, includes bot hints.

4. **Use dependency injection via FastAPI Depends()** - Clean integration with composition root.

5. **Write OpenAPI tests** - Validate schema matches artifact specification.

6. **Add request/response logging early** - Aids debugging during implementation.

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial report | Scout Agent |
