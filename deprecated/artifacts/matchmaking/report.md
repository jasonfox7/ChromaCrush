# Module Report: matchmaking

## Header
- **Author:** Scout Agent (matchmaking)
- **Date:** 2026-02-05

---

## Summary

The matchmaking module has been designed to provide ELO-based player pairing for ChromaCrush's asynchronous versus mode. Key design outcomes:

1. **Redis-based Queue Architecture** - Chose Redis sorted sets over PostgreSQL for queue management. Sorted sets enable O(log n) ELO range queries, essential for efficient matchmaking at scale.

2. **Three-Pool System** - Implemented `HUMAN`, `BOT`, and `MIXED` pools with strict enforcement. Players can only join pools matching their type (humans can't join bot-only, bots can't join human-only).

3. **Progressive Range Expansion** - ELO search range starts narrow (default +/- 50) and expands over time (default +50 every 30 seconds) up to a maximum (default +/- 500). This balances match quality against wait times.

4. **FIFO with ELO Priority** - Within an acceptable ELO range, matches are created FIFO (first-in-first-served). This prevents skilled players from always being matched first.

5. **Atomic Pairing with Compensation** - Uses Redis WATCH/MULTI for atomic removal of both players from queue, with compensating transaction to re-add if match creation fails.

6. **No PostgreSQL State** - All matchmaking state is transient in Redis. This simplifies the architecture and enables horizontal scaling of matchmaking workers.

---

## Alternatives Considered

### Alternative 1: PostgreSQL-Based Queue

**Approach:** Store queue entries in PostgreSQL with ELO-indexed queries.

**Why Rejected:**
- Higher latency for frequent queue operations (join, leave, scan)
- More complex locking for atomic pairing
- PostgreSQL is optimized for ACID transactions, not real-time queue patterns
- Redis sorted sets are purpose-built for this use case

### Alternative 2: In-Memory Queue (Application State)

**Approach:** Keep queue in application memory, persist snapshots periodically.

**Why Rejected:**
- Doesn't scale horizontally (multiple matchmaking workers)
- Loss of queue state on restart
- Complexity of distributed coordination

### Alternative 3: Separate Queues Per ELO Bucket

**Approach:** Bucket players by ELO (e.g., 900-1000, 1000-1100) and only match within bucket.

**Why Rejected:**
- Rigid boundaries create poor matches at bucket edges
- Range expansion would require moving players between buckets
- Current design with sorted set range queries is more flexible

### Alternative 4: Real-Time Matching (WebSocket)

**Approach:** Push match notifications immediately when found.

**Why Rejected:**
- Out of scope for this module (notification is a separate concern)
- Module returns `MatchmakingResult` which can trigger notifications upstream
- Keeps matchmaking logic pure and testable

### Alternative 5: Skill-Based Matchmaking (Beyond ELO)

**Approach:** Consider factors beyond ELO (play style, win streaks, time of day).

**Why Rejected:**
- Adds complexity without clear benefit at launch
- GDD specifies ELO-based matching
- Can be added later as enhancement to `find_opponents_in_range`

---

## Risks

### Risk 1: Redis Availability

**Description:** Matchmaking depends entirely on Redis. Redis downtime = no matchmaking.

**Mitigation:**
- Redis Sentinel or Cluster for high availability (infrastructure decision)
- Graceful degradation: return "matchmaking unavailable" error rather than crashing
- Operations can retry when Redis recovers

**Severity:** Medium (temporary unavailability is acceptable for a game)

### Risk 2: Race Conditions in Pairing

**Description:** Multiple matchmaking workers could select the same opponent simultaneously.

**Mitigation:**
- `atomic_remove_pair` uses Redis WATCH for optimistic locking
- Failed removals (opponent already taken) trigger retry with next candidate
- Design tested with concurrent access patterns

**Severity:** Low (handled by design)

### Risk 3: Queue Starvation for Extreme ELOs

**Description:** Players with very high or very low ELO may wait a long time or never find a match.

**Mitigation:**
- Range expansion eventually reaches +/- 500, a wide net
- Timeout prevents infinite waiting
- Mixed pool provides more opponent options
- Future: Consider bot opponents as fallback for extreme cases

**Severity:** Medium (affects small population at extremes)

### Risk 4: Match Creation Failure Compensation

**Description:** If match creation fails after queue removal, re-adding players might fail or create inconsistent state.

**Mitigation:**
- Compensation is best-effort with error logging
- Players can re-join queue manually if needed
- Match creation failures should be rare (validation happens before queue removal)

**Severity:** Low (rare scenario with manual recovery path)

### Risk 5: Clock Skew in Wait Time Calculation

**Description:** If Redis server clock differs from application server clock, wait times could be inaccurate.

**Mitigation:**
- Use Redis server time for all timestamp comparisons (REDIS TIME command)
- Alternatively, store timestamps as relative to Redis server
- In practice, servers should be NTP-synchronized

**Severity:** Low (operational concern)

---

## Dependencies & Sequencing Notes

### Build Order Position

This module is **Wave 6** in the dependency graph:
- **Depends on:** `match` (Wave 5), `player` (Wave 1)
- **Depended on by:** `api` (Wave 9)

### Implementation Prerequisites

Before this module can be implemented:
1. `player` module must be complete (for `get_player`, `get_elo`)
2. `match` module must be complete (for `create_match`, `find_active_by_player`)
3. Redis infrastructure must be available in `src/data/redis/`
4. `MatchmakingQueueRepositoryProtocol` concrete implementation in `src/data/repositories/`

### Interface Dependencies

| Dependency | Interface Used | Notes |
|------------|----------------|-------|
| `PlayerServiceProtocol` | `get_player()`, `get_elo()` | Read-only access to player data |
| `MatchServiceProtocol` | `create_match()`, `find_active_by_player()` | Creates matches, checks active matches |

### New Error Types Required

The following error codes should be added to the Interface Agent's error taxonomy before implementation:

| Code | HTTP | Category |
|------|------|----------|
| `VALIDATION_NOT_IN_QUEUE` | 400 | validation |
| `CONFLICT_ALREADY_IN_QUEUE` | 409 | conflict |
| `FORBIDDEN_POOL_RESTRICTED` | 403 | forbidden |
| `INTERNAL_MATCHMAKING_ERROR` | 500 | internal |

### Configuration Keys Required

The following configuration keys should be added to the Configuration Agent's schema:

```toml
[matchmaking]
initial_elo_range = 50
elo_range_expansion = 50
elo_range_expansion_interval_seconds = 30
max_elo_range = 500
queue_timeout_seconds = 300
process_interval_seconds = 5
min_wait_before_expansion = 10
```

Note: `elo_initial` and `elo_k_factor` already exist in the config schema.

### Background Worker Requirement

The `process_queue` and `cleanup_stale_entries` methods are designed to be called by a background worker (arq task). This is an infrastructure concern, not a module concern, but the worker must be configured with:

- Process interval: `matchmaking.process_interval_seconds`
- Process all three pools per cycle
- Cleanup runs less frequently (e.g., every 60 seconds)

---

## Coordination Notes

### Match Module Interface

The matchmaking module calls `match_service.create_match()` but does not specify `board_seed` - this is generated by the match module. If matchmaking should influence board generation (e.g., for tournament modes), an additional parameter would be needed.

Current assumption: **matchmaking does not influence board generation**. This aligns with the GDD's async fairness model.

### Player Module Interface

The `find_active_by_player` check prevents players from queuing while in a match. This may need coordination with the match module:
- Currently assumed to be exposed via `MatchServiceProtocol`
- If not, may need to be added to match module's public interface

### API Integration

The API layer will need to:
1. Call `join_queue` when player requests matchmaking
2. Poll `get_queue_status` or `find_match` for status updates
3. Consider WebSocket/SSE for real-time notifications (separate concern)

---

## Testing Considerations

### Unit Test Scenarios

1. **Join queue validation** - player exists, pool type matches, not already queued, not in match
2. **Leave queue** - removes entry, returns false if not present
3. **ELO range expansion** - expands at correct intervals, stops at max
4. **Opponent finding** - returns players in range, excludes self, respects limit
5. **Atomic pairing** - handles concurrent access, compensates on failure
6. **Timeout handling** - removes expired entries, returns correct status

### Integration Test Scenarios

1. **Full matchmaking flow** - join, search, match, verify both removed from queue
2. **Cross-pool enforcement** - bot cannot join human pool, vice versa
3. **Concurrent matching** - multiple players searching simultaneously
4. **Match creation failure** - verify compensation re-adds players

### Load Test Considerations

- Simulate 1000+ concurrent queued players
- Measure pairing latency at scale
- Test Redis performance under load
- Verify no memory leaks in long-running queue processing

---

## Future Enhancements (Out of Scope)

These features are explicitly out of scope for v1.0 but could be added later:

1. **Priority Queue** - Premium players get faster matches
2. **Skill-Based Factors** - Consider win streaks, play patterns
3. **Geographic Matching** - Match players in same region
4. **Bot Fallback** - Auto-match with bot if no human found
5. **Party Matchmaking** - Groups of players finding opponents
6. **Tournament Mode** - Bracket-based matchmaking
7. **Rematch Option** - Quick rematch with same opponent

---

## Conclusion

The matchmaking module provides a robust, scalable foundation for player pairing in ChromaCrush. The Redis-based architecture enables efficient ELO-range queries while the progressive range expansion balances match quality against wait times. The design handles edge cases around concurrent access and failure compensation, ensuring fair and reliable matchmaking.

Key strengths:
- O(log n) pairing with Redis sorted sets
- Configurable behavior via config keys
- Clean separation from match creation logic
- Comprehensive error handling and logging

The module is ready for implementation once its dependencies (player, match) are complete.
