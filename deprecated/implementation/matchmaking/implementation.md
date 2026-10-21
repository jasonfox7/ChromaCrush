# Module Implementation Document: matchmaking

## Header
- **Author:** Coding Agent (matchmaking)
- **Date:** 2026-02-06
- **Version:** 1.0
- **Status:** Implementation Complete

---

## Public Interface

### MatchmakingService

The service class receives all dependencies via `__init__` injection:

```python
class MatchmakingService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        match_service: MatchServiceProtocol,
        player_service: PlayerServiceProtocol,
        matchmaking_queue_repository: MatchmakingQueueRepositoryProtocol,
    ) -> None
```

### Public Methods (all `async def`)

| Method | Signature | Returns |
|--------|-----------|---------|
| `join_queue` | `(player_id, pool_type=MIXED)` | `QueueEntry` |
| `leave_queue` | `(player_id)` | `bool` |
| `get_queue_status` | `(player_id)` | `QueueStatus \| None` |
| `find_match` | `(player_id)` | `MatchmakingResult` |
| `process_queue` | `(pool_type)` | `list[MatchmakingResult]` |
| `cleanup_stale_entries` | `()` | `int` |
| `get_queue_stats` | `(pool_type=None)` | `QueueStats` |

### Private Methods (all `async def`)

| Method | Purpose |
|--------|---------|
| `_maybe_expand_elo_range` | Expand ELO search range based on wait time |
| `_try_create_match` | Atomically remove pair and create match, with compensation |
| `_re_add_to_queue` | Re-add player after failed match creation |
| `_calculate_queue_position` | Calculate 1-indexed queue position |
| `_estimate_wait_time` | Heuristic wait time estimation |

---

## Types

Defined in `src/modules/matchmaking/types.py`:

| Type | Kind | Description |
|------|------|-------------|
| `PoolType` | Enum | HUMAN, BOT, MIXED |
| `MatchmakingStatus` | Enum | MATCHED, SEARCHING, EXPIRED, NOT_IN_QUEUE, ERROR |
| `QueueEntryData` | Dataclass | Raw Redis queue entry data |
| `QueueEntry` | Dataclass | Player's queue entry with position and estimate |
| `QueueStatus` | Dataclass | Current queue status with opponents count |
| `MatchmakingResult` | Dataclass | Result of a matchmaking attempt |
| `QueueStats` | Dataclass | Queue statistics with ELO distribution |

---

## Configuration Keys Used

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `matchmaking.initial_elo_range` | int | 50 | Starting +/- ELO search range |
| `matchmaking.elo_range_expansion` | int | 50 | Range expansion per interval |
| `matchmaking.elo_range_expansion_interval_seconds` | int | 30 | Expansion interval |
| `matchmaking.max_elo_range` | int | 500 | Maximum +/- ELO search range |
| `matchmaking.queue_timeout_seconds` | int | 300 | Seconds before queue removal |
| `matchmaking.min_wait_before_expansion` | int | 10 | Min wait before first expansion |

All config values are cached in `__init__` to avoid repeated lookups.

---

## Error Codes

| Error Code | Error Type | HTTP Status | Trigger |
|------------|------------|-------------|---------|
| `NOT_FOUND_PLAYER` | not_found | 404 | Player ID does not exist |
| `CONFLICT_ALREADY_IN_QUEUE` | conflict | 409 | Player already in a queue |
| `CONFLICT_PLAYER_IN_MATCH` | conflict | 409 | Player has an active match |
| `VALIDATION_NOT_IN_QUEUE` | validation | 400 | Player not in queue (for find_match) |
| `FORBIDDEN_POOL_RESTRICTED` | forbidden | 403 | Player type not allowed in pool |
| `INTERNAL_MATCHMAKING_ERROR` | internal | 500 | Match creation failed after queue removal |

All errors are created through the injected `ErrorServiceProtocol`. The `AppError` class is imported from `src.core.errors` only for `try/except` blocks in `_try_create_match`.

---

## Data Patterns

### Storage: Redis Only (No PostgreSQL)

All matchmaking state is transient and stored in Redis:

**Sorted Sets (one per pool type):**
```
chromacrush:matchmaking:queue:{pool_type}
  Score: player's ELO rating
  Member: player_id (UUID string)
```

**Hashes (one per queued player):**
```
chromacrush:matchmaking:player:{player_id}
  pool_type: string
  elo_rating: int
  joined_at: ISO timestamp
  last_expansion_at: ISO timestamp
  current_min_elo: int
  current_max_elo: int
```

### Repository: RedisMatchmakingQueueRepository

Located at `src/data/repositories/matchmaking_queue_repository.py`. Constructor takes `DataContext` and accesses Redis via `data_ctx.redis`.

Key operations use Redis pipelines for atomicity:
- `add_to_queue`: ZADD + HSET + EXPIRE in pipeline
- `remove_from_queue`: ZREM + DELETE in pipeline
- `atomic_remove_pair`: Double ZREM + double DELETE in pipeline
- `find_opponents_in_range`: ZRANGEBYSCORE with score filtering
- `remove_stale_entries`: Iterates all pools, removes entries with `joined_at < cutoff`

TTL strategy: Player hashes have TTL of 360 seconds (queue_timeout + 60s buffer).

### Protocol: MatchmakingQueueRepositoryProtocol

Located at `src/data/protocols/matchmaking_queue_repository.py`. Defines 11 async methods matching the concrete implementation.

---

## CLI Commands

Located at `src/cli/commands/matchmaking_commands.py`:

| Command | Arguments | Options | Description |
|---------|-----------|---------|-------------|
| `matchmaking join` | `player_username` | `--pool`, `--config` | Join matchmaking queue |
| `matchmaking leave` | `player_username` | `--config` | Leave matchmaking queue |
| `matchmaking status` | `player_username` | `--config` | Check queue status |
| `matchmaking find` | `player_username` | `--config` | Attempt to find a match |
| `matchmaking process` | - | `--pool`, `--config` | Process queue pool(s) |
| `matchmaking cleanup` | - | `--config` | Remove stale entries |
| `matchmaking stats` | - | `--pool`, `--config` | Show queue statistics |
| `matchmaking list` | - | `--pool`, `--limit`, `--config` | List queue contents |

The CLI uses `_build_services(ctx)` to wire `MatchmakingService` with all dependencies from `ApplicationContext`, and `_run_async` to bridge Click sync commands to async service methods.

---

## Deviations from Artifact

### 1. `get_active_matches` instead of `find_active_by_player`

The artifact references `match_service.find_active_by_player()` but the actual `MatchServiceProtocol` exposes `get_active_matches()`. The implementation uses `get_active_matches()` as instructed.

### 2. Config key name alignment

The artifact uses config keys like `matchmaking.initial_elo_range` and `matchmaking.elo_range_expansion`. The `MockConfigService` defaults use slightly different names (`elo_range_initial`, `elo_expansion_step`). The service implementation uses the artifact's key names and tests override the config accordingly.

### 3. QueueStats fields

`matches_created_last_hour` and `average_elo_difference` in `QueueStats` return default values (0) since tracking these metrics would require a separate persistent counter, which is outside the scope of the Redis-only transient data model for matchmaking.

### 4. Simplified wait time estimation

The `_estimate_wait_time` method uses a simple heuristic based on queue size rather than historical match data. A more sophisticated model would require persistent storage of match creation events.

---

## Test Coverage

Tests are located in `tests/unit/modules/matchmaking/test_matchmaking_service.py`.

**Test classes and coverage:**

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestJoinQueue` | 11 | Pool validation, conflicts, player not found, logging |
| `TestLeaveQueue` | 4 | Success, not in queue, logging |
| `TestGetQueueStatus` | 3 | In queue, not in queue, wait time |
| `TestFindMatch` | 9 | Success, not in queue, timeout, no opponents, opponent taken, multiple opponents, compensation, logging |
| `TestProcessQueue` | 5 | Empty, single player, two players, four players, logging |
| `TestCleanupStaleEntries` | 5 | No stale, removal, logging, cutoff calculation |
| `TestGetQueueStats` | 4 | Specific pool, all pools, empty queue, wait times |
| `TestEloRangeExpansion` | 5 | Min wait, interval, trigger, max range, logging |
| `TestConfiguration` | 2 | Custom initial range, custom timeout |
| `TestQueuePositionAndEstimation` | 4 | Position, estimation |
| `TestErrorPropagation` | 4 | NOT_FOUND, FORBIDDEN context, CONFLICT context, INTERNAL context |
| `TestEdgeCases` | 7 | EC-2, EC-3, EC-4, EC-6, EC-8, idempotent leave, removed between ops |

**Total: 63 tests**

All tests use `AsyncMock` for async dependencies and `MockConfigService`, `MockLogService`, `MockErrorService` from `tests/mocks/services.py`.
