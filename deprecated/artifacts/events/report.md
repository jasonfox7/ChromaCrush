# Module Report: events

## Header
- **Author:** Scout Agent (events)
- **Date:** 2026-02-05

---

## Summary

The events module has been designed to manage time-limited competitive events in ChromaCrush. Key outcomes:

1. **Three Event Types Defined:**
   - Flash events (2-4 hours) for urgent, high-intensity competition
   - Weekly events (7 days) for sustained engagement
   - Seasonal events (2-4 weeks) for major themed content drops

2. **Comprehensive Scoring System:**
   - Four scoring types supported: total_score, best_match, matches_played, average_score
   - Configurable scoring multipliers and bonus conditions
   - Real-time leaderboard via Redis sorted sets

3. **Flexible Reward System:**
   - Tiered rewards based on rank or percentile
   - Multiple reward types: artifacts (via vault), energy (via energy module), ELO bonuses
   - Configurable minimum match requirements for reward eligibility

4. **Entry Management:**
   - Optional requirements: level, ELO range, player type restrictions
   - Optional energy cost for entry
   - Capacity limits with atomic join handling

5. **Automated Lifecycle:**
   - Background job handles scheduled activation/deactivation
   - Auto-finalization with configurable delay
   - Graceful handling of in-progress matches at event end

6. **Module Integration:**
   - Clean integration with vault module for artifact rewards
   - Clean integration with energy module for entry costs and energy rewards
   - Read-only access to match module for match verification
   - Read-only access to player module for participant data

---

## Alternatives Considered

### Alternative 1: Single Leaderboard per Event vs. Multiple Boards

**Considered:** Having separate leaderboards for different player segments (human-only, bot-only, mixed).

**Rejected:** Adds significant complexity. The GDD doesn't specify segmented event leaderboards (unlike global ELO leaderboards). Can be added later as a `rules.leaderboard_segments` configuration if needed.

---

### Alternative 2: Real-Time vs. Batch Leaderboard Updates

**Considered:** Batch leaderboard updates every N minutes instead of real-time Redis updates.

**Rejected:** Real-time feedback is critical for event engagement. Players want to see their rank change immediately after a match. Redis sorted sets handle this efficiently at our expected scale.

---

### Alternative 3: Storing Full Match History vs. Summary Stats

**Considered:** Only storing summary statistics (total_score, matches_played) without individual match records.

**Rejected:** Match-level granularity needed for:
- Detecting suspicious patterns (anti-cheat)
- Displaying match history to players
- Accurate average_score calculation
- Debugging and support

The `event_matches` table adds storage but provides essential traceability.

---

### Alternative 4: Synchronous vs. Asynchronous Reward Distribution

**Considered:** Distributing rewards via background job rather than inline during finalization.

**Rejected:** Finalization is already a batch operation. Inline distribution ensures atomicity - if any reward fails, the whole finalization rolls back. Background distribution would require complex recovery logic for partial failures.

---

### Alternative 5: Event-Specific Match Creation vs. Recording Existing Matches

**Considered:** Events creating their own matches with special rules.

**Rejected:** Matches should be created through the match module. Events only *record* match results. This maintains proper separation of concerns. Event-specific rules (like special board seeds) are passed to match creation by the caller (API layer or matchmaking), not by the events module.

---

## Risks

### Risk 1: Leaderboard Consistency Under Load

**Risk:** During high-participation flash events, Redis leaderboard could become a bottleneck or get out of sync with database.

**Likelihood:** Medium
**Impact:** Medium

**Mitigation:**
- Periodic sync job (every 5 minutes) keeps DB in sync
- Forced sync before finalization
- Rebuild capability if Redis data lost
- Leaderboard read timeout falls back to DB query

---

### Risk 2: Event Finalization at Scale

**Risk:** Finalizing an event with 50,000 participants and distributing rewards could timeout or fail.

**Likelihood:** Medium (for seasonal events)
**Impact:** High

**Mitigation:**
- Transaction batching (process rewards in batches of 100)
- Idempotent reward grants (via idempotency keys)
- Manual retry capability for failed finalizations
- Monitoring and alerting on finalization duration

---

### Risk 3: Entry Requirement Gaming

**Risk:** Players could game entry requirements (e.g., tank ELO to enter "beginner" events).

**Likelihood:** Low-Medium
**Impact:** Low

**Mitigation:**
- Entry requirements are optional per event
- Can add cooldown-based requirements (ELO at time of event creation)
- Deferred: This is a game design decision, not a technical blocker

---

### Risk 4: Clock Skew in Scheduled Activation

**Risk:** Server clock differences could cause events to activate at wrong times.

**Likelihood:** Low
**Impact:** Medium

**Mitigation:**
- All timestamps in UTC
- Single background worker handles scheduling
- Grace periods on start/end times
- NTP synchronization on production servers

---

### Risk 5: Complex Reward Tier Logic

**Risk:** Percentile-based reward tiers with edge cases (ties, exactly-at-threshold players) could cause unexpected reward assignments.

**Likelihood:** Medium
**Impact:** Low

**Mitigation:**
- Clear tier assignment priority (rank-based checked before percentile-based)
- Comprehensive unit tests for tier assignment edge cases
- Admin can review assignments before finalization becomes irreversible

---

## Dependencies & Sequencing Notes

### Build Order Position

Events is Wave 6 in the dependency graph. It must be built after:
- Wave 1: `board`, `player`
- Wave 2: `scoring`, `auth`, `energy`
- Wave 3: `special_gems`, `vault`
- Wave 4: `board_gen`
- Wave 5: `match`

### Dependencies on Other Modules

| Module | Dependency Type | Must Be Complete By |
|--------|-----------------|---------------------|
| `player` | Runtime | Before events implementation |
| `energy` | Runtime | Before events implementation |
| `vault` | Runtime | Before events implementation |
| `match` | Runtime | Before events implementation |

### Dependent Modules

| Module | Depends On Events For |
|--------|----------------------|
| `ads` | Event-triggered ad opportunities (optional integration) |

### Coordination Notes

1. **Energy Module:** Events consumes hearts via `EnergyServiceProtocol.consume_heart()` and grants bonus hearts via `grant_bonus_hearts()`. Energy module must support the `EVENT_REWARD` bonus source.

2. **Vault Module:** Events grants artifacts via `VaultServiceProtocol.add_artifact()` with `source="event_reward"`. Vault module must accept this source value.

3. **Match Module:** Events verifies match completion via `MatchServiceProtocol.get_match_state()`. No writes to match module.

4. **Player Module:** Events reads player data via `PlayerServiceProtocol.get_player()` and `get_stats()`. Updates ELO via `update_elo()` for ELO bonus rewards.

5. **Redis Infrastructure:** Events module requires Redis sorted sets for real-time leaderboards. Redis configuration must be available in config schema.

### Background Worker Requirements

The events module requires a background worker (arq) to run `process_scheduled_events()` periodically. This should be configured in the arq worker setup:

```python
# arq worker configuration
async def process_events(ctx):
    event_service = ctx["event_service"]
    result = await event_service.process_scheduled_events()
    return result

class WorkerSettings:
    cron_jobs = [
        cron(process_events, minute={0, 15, 30, 45})  # Every 15 minutes
    ]
```

### Config Schema Additions Required

The following config keys must be added to the config schema by the Configuration Agent:

```toml
[events]
flash_duration_hours = 4
weekly_duration_days = 7
seasonal_duration_days = 28
entry_energy_cost = 0
match_energy_cost = 1
max_participants_flash = 10000
max_participants_weekly = 50000
max_participants_seasonal = 0
leaderboard_cache_ttl_seconds = 30
auto_finalize_delay_minutes = 15
min_matches_for_rewards = 3
allow_leave_after_match = false
```

### Error Taxonomy Additions Required

The following error codes must be added to the error taxonomy by the Interface Agent:

- `NOT_FOUND_EVENT`
- `CONFLICT_EVENT_NOT_ACTIVE`
- `CONFLICT_EVENT_ALREADY_FINALIZED`
- `CONFLICT_ALREADY_PARTICIPANT`
- `FORBIDDEN_NOT_EVENT_PARTICIPANT`
- `FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET`
- `CONFLICT_EVENT_AT_CAPACITY`
- `FORBIDDEN_CANNOT_LEAVE_EVENT`
- `CONFLICT_MAX_MATCHES_REACHED`

### Type Registry Additions Required

The following types should be added to the type registry by the Interface Agent:

```python
# src/core/types/game.py
EventId = NewType("EventId", UUID)
```

---

## Implementation Notes for Coder

1. **Leaderboard Repository:** The `EventLeaderboardRepository` is Redis-backed but implements a Protocol. The coder should implement this in `src/data/redis/event_leaderboard.py`, not in the module itself.

2. **Scoring Calculations:** Keep scoring logic in dedicated helper functions in `src/modules/events/scoring.py` for testability.

3. **Reward Granting:** The `_grant_reward` internal method delegates to other services. Handle errors from those services gracefully with proper logging.

4. **Background Job:** The `process_scheduled_events` method should be idempotent - calling it twice in quick succession should not cause problems.

5. **Testing:** Redis leaderboard operations should be tested with a real Redis instance in integration tests. Unit tests can mock the leaderboard repository.

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial report | Scout Agent (events) |
