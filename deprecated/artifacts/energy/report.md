# Energy Module Report

> **Module:** energy
> **Author:** Scout Agent
> **Date:** 2026-02-05

---

## Summary

The energy module has been designed to implement the hearts/energy system for ChromaCrush. Key design outcomes:

1. **Real-time regeneration model** - Hearts are calculated on-demand using elapsed time since last regeneration, avoiding the need for scheduled background jobs while ensuring accuracy even after server downtime.

2. **Shared data ownership pattern** - The player module owns the `energy_states` table (Wave 1), while the energy module owns all business logic (Wave 2). This clean separation prevents circular dependencies.

3. **Atomic consumption** - Heart consumption uses database transactions to prevent race conditions where concurrent requests could overdraw hearts.

4. **Flexible bonus system** - Bonus hearts from ads, streaks, and events can exceed the normal max_hearts cap, with idempotency protection via Redis.

5. **GDD-compliant streak system** - Daily login streaks with configurable reward thresholds at 7/14/30 days, implementing the "sunk cost + identity" psychological hooks described in the GDD.

---

## Alternatives Considered

### 1. Background Job Regeneration vs. Real-Time Calculation

**Considered:** Using arq/Celery to run scheduled jobs that increment hearts every 30 minutes.

**Rejected because:**
- Requires additional infrastructure complexity
- Hearts would be "wrong" if job was delayed or server was down
- Race conditions between job execution and user requests
- Higher operational cost (more Redis/worker resources)

**Chosen:** Real-time calculation on every read. Hearts are computed as `stored_hearts + floor(elapsed_time / regen_interval)`, capped at max. Persisted lazily when consumed.

### 2. Separate energy_states Table vs. Player Table Column

**Considered:** Adding hearts/streak columns directly to the `players` table.

**Rejected because:**
- Energy state changes frequently (every 30 min effectively)
- Player table is read-heavy from many modules
- Separation allows independent scaling/caching strategies

**Chosen:** Separate `energy_states` table owned by player module, with energy module owning the business logic. This matches the data layer guidance for clean ownership.

### 3. Redis-Only Storage vs. PostgreSQL + Redis Cache

**Considered:** Storing energy state entirely in Redis for speed.

**Rejected because:**
- Data loss on Redis failure would lose player hearts/streaks
- GDPR compliance requires durable player data storage
- PostgreSQL is authoritative; Redis is cache/optimization only

**Chosen:** PostgreSQL as source of truth, Redis for idempotency keys and optional caching of next-regen timestamps.

### 4. Per-User Timezone vs. UTC for Streak Calculation

**Considered:** Using player's local timezone to determine "same day" for streaks.

**Rejected because:**
- Complexity of storing and updating user timezones
- Edge cases with timezone changes (travel, DST)
- Potential for exploitation by changing timezone

**Chosen:** UTC midnight for all streak calculations. Simple, consistent, and auditable.

---

## Risks

### 1. Race Condition on Concurrent Consume

**Risk:** Two requests to start a match arrive simultaneously, both pass the hearts check, both decrement, resulting in negative hearts.

**Mitigation:** Atomic transaction using SELECT FOR UPDATE or optimistic locking. The artifact specifies this requirement; implementation must honor it.

**Residual risk:** Low, if implementation follows the atomic pattern.

### 2. Redis Unavailability for Idempotency

**Risk:** If Redis is down, duplicate bonus grants could occur (e.g., player watches ad, network retry, gets 2 hearts).

**Mitigation:**
- Fall back to "best effort" with logging
- Short idempotency windows (24h) limit blast radius
- Business impact is low (extra free hearts, not money)

**Residual risk:** Low. Operational monitoring should catch Redis issues.

### 3. Clock Skew Between Servers

**Risk:** If servers have different clocks, regeneration calculations could be inconsistent.

**Mitigation:**
- Use `datetime.now(timezone.utc)` consistently
- Require NTP synchronization in deployment
- Regeneration is relative to stored `last_regen_at`, so skew only affects the "now" comparison

**Residual risk:** Very low with proper infrastructure.

### 4. GDD Discrepancy: 20 min vs 30 min Regeneration

**Risk:** GDD page 4 says "regenerate 1/20 min" but configuration guidance says 30 min default.

**Mitigation:** The value is configurable via `energy.regen_interval_minutes`. The design supports either value; final tuning is a business decision.

**Residual risk:** None (configuration resolves it).

---

## Dependencies & Sequencing Notes

### Build Order Position

- **Wave 2** - Depends on `player` module (Wave 1)
- Can be developed in parallel with `auth`, `scoring` (other Wave 2 modules)
- Must complete before `match` module (Wave 5), which depends on energy checks

### Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| `player` module | Required | Artifact complete |
| `src/core/` services | Required | Phase 2.0 |
| Redis context | Required | Phase 2.0 |
| `EnergyState` type | Required | Defined in interface-contracts.md |

### Dependents

| Module | Dependency Type | Usage |
|--------|-----------------|-------|
| `match` | Required | Check/consume hearts before match start |
| `events` | Optional | Grant bonus hearts as rewards |
| `ads` | Optional | Grant bonus hearts for rewarded ads |
| `api` | Required | Expose energy endpoints |

### Coordination Notes

1. **Player module must expose `get_energy_state` and `update_energy_state`** - These methods are already specified in the player artifact. Energy module depends on this interface.

2. **Match module will need to handle consume failures** - When `consume_heart` raises `FORBIDDEN_INSUFFICIENT_ENERGY`, match creation should return a user-friendly error with energy state.

3. **Ads module idempotency keys** - The ads module should generate unique `ad_session_id` values for each rewarded ad view to use as idempotency keys.

4. **Events module reward grants** - Events should use `event:{event_id}:player:{player_id}` format for idempotency keys to prevent duplicate event rewards.

---

## Open Items for Orchestrator

None. All design decisions have been resolved based on existing guidance documents.

---

## Metrics for Success (Phase 2 Verification)

Karen should verify:

1. All methods are `async def` as specified
2. No direct `os.environ` or `os.getenv` calls
3. No bare `raise Exception` - all errors through error service
4. No direct database access - all through player service
5. Redis access through injected `RedisContext` protocol
6. Atomic transaction pattern in `consume_heart`
7. Configuration keys match those in artifact
8. CLI commands exercise all public interface methods

---

*End of Report*
