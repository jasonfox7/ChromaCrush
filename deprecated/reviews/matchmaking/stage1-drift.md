# Stage 1 Drift Report: matchmaking

**Reviewer:** Document Reviewer (Karen Compliance Sweep)
**Date:** 2026-02-06
**Artifact:** docs/artifacts/matchmaking/report.md + artifact.md
**Implementation Doc:** docs/implementation/matchmaking/implementation.md

---

## Method Count Comparison

Artifact defines 7 public methods:
1. `join_queue(player_id, pool_type) -> QueueEntry`
2. `leave_queue(player_id) -> bool`
3. `get_queue_status(player_id) -> QueueStatus | None`
4. `find_match(player_id) -> MatchmakingResult`
5. `process_queue(pool_type) -> list[MatchmakingResult]`
6. `cleanup_stale_entries() -> int`
7. `get_queue_stats(pool_type) -> QueueStats`

Implementation doc documents 7 public methods with matching signatures.

**Result:** Method counts match. No undocumented public methods.

Implementation doc also documents 5 private methods (`_maybe_expand_elo_range`, `_try_create_match`, `_re_add_to_queue`, `_calculate_queue_position`, `_estimate_wait_time`). These align with the artifact's internal design algorithms.

---

## Error Handling Comparison

Artifact error cases:
- `NOT_FOUND_PLAYER` (player doesn't exist)
- `CONFLICT_ALREADY_IN_QUEUE` (already queued)
- `CONFLICT_PLAYER_IN_MATCH` (in active match)
- `VALIDATION_NOT_IN_QUEUE` (not in queue for find_match)
- `VALIDATION_INVALID_INPUT` (invalid pool type)
- `FORBIDDEN_POOL_RESTRICTED` (player type not allowed in pool)
- `INTERNAL_MATCHMAKING_ERROR` (match creation failed)
- `INTERNAL_CACHE_ERROR` (Redis operation failed)

Implementation doc error codes:
- `NOT_FOUND_PLAYER`
- `CONFLICT_ALREADY_IN_QUEUE`
- `CONFLICT_PLAYER_IN_MATCH`
- `VALIDATION_NOT_IN_QUEUE`
- `FORBIDDEN_POOL_RESTRICTED`
- `INTERNAL_MATCHMAKING_ERROR`

[DRIFT] Artifact specifies `VALIDATION_INVALID_INPUT` for invalid pool type -> Implementation doc does not list this error code. Pool type validation may be handled by the enum type itself rather than as an explicit error.

[DRIFT] Artifact specifies `INTERNAL_CACHE_ERROR` for Redis operation failures -> Implementation doc does not list this error code. Redis errors may propagate uncaught or be wrapped differently.

---

## Public Interface Shape

Types comparison:

Artifact defines:
- `QueueEntry` with fields: player_id, player_username, elo_rating, pool_type, joined_at, current_elo_range (tuple), estimated_wait_seconds, position_in_queue

Implementation doc `QueueEntry` -- matches artifact.

Artifact defines:
- `QueueStatus` with fields: player_id, pool_type, elo_rating, joined_at, wait_time_seconds, current_elo_range, potential_opponents, position_in_queue, estimated_wait_seconds

Implementation doc `QueueStatus` -- matches artifact.

Artifact defines:
- `MatchmakingResult` with fields: status, player_id, opponent_id, match_id, wait_time_seconds, elo_difference, pool_type, message

Implementation doc `MatchmakingResult` -- matches artifact.

Artifact defines:
- `QueueStats` with fields: pool_type, total_players, players_by_elo_bucket, average_wait_seconds, longest_wait_seconds, matches_created_last_hour, average_elo_difference

Implementation doc `QueueStats` -- matches artifact.

**Result:** All type shapes match.

---

## Configuration Keys

Artifact defines 9 config keys (including `elo_initial`, `elo_k_factor`, `process_interval_seconds`).

Implementation doc documents 6 config keys (omitting `elo_initial`, `elo_k_factor`, `process_interval_seconds`).

[DRIFT] Artifact lists `matchmaking.elo_initial`, `matchmaking.elo_k_factor`, and `matchmaking.process_interval_seconds` as config keys -> Implementation doc omits these three keys. `elo_initial` and `elo_k_factor` are noted in the artifact as "already exist in config schema" (informational), but `process_interval_seconds` is used by the background worker which is outside the module. This may be intentional omission of informational/infrastructure keys.

---

## Async Behavior

Artifact: all public methods async. Impl doc: all public methods async. Match.

---

## Deviations Section

Implementation doc documents 4 explicit deviations:

1. `get_active_matches` instead of `find_active_by_player` -- the match service protocol uses a different method name than what the artifact references
2. Config key name alignment -- artifact names vs test mock names differ
3. `QueueStats.matches_created_last_hour` and `average_elo_difference` return default values (0)
4. Simplified wait time estimation

[DRIFT] Artifact's `QueueStats` specifies `matches_created_last_hour` and `average_elo_difference` as meaningful fields -> Implementation doc documents these as returning default values (0) because tracking them requires persistent storage outside the Redis-only model. This is a functional gap -- the artifact promises data these fields cannot deliver.

[DRIFT] Artifact references `match_service.find_active_by_player()` -> Implementation uses `match_service.get_active_matches()`. The artifact's dependency table says the matchmaking module calls `find_active_by_player` on the match service, but the actual match service protocol exposes `get_active_matches` instead. This was caught and documented by the implementation team.

---

## CLI Commands

Artifact specifies 8 CLI commands: join, leave, status, find, process, cleanup, stats, list.

Implementation doc documents 8 CLI commands matching the artifact.

**Result:** CLI surface matches.

---

## Repository Protocol

Artifact defines `MatchmakingQueueRepositoryProtocol` with 11 async methods.

Implementation doc states the protocol has 11 async methods.

**Result:** Repository protocol method count matches.

---

## Document Thickness

Implementation doc is 206 lines. This is adequate but on the thinner side for a module with Redis data patterns, 7 public methods, and complex queue logic.

---

## Findings Summary

```
[DRIFT] Artifact specifies VALIDATION_INVALID_INPUT for invalid pool type -> Implementation doc does not list this error code
[DRIFT] Artifact specifies INTERNAL_CACHE_ERROR for Redis failures -> Implementation doc does not list this error code
[DRIFT] Artifact lists matchmaking.elo_initial, matchmaking.elo_k_factor, matchmaking.process_interval_seconds as config keys -> Implementation doc omits these three
[DRIFT] Artifact's QueueStats specifies matches_created_last_hour and average_elo_difference as meaningful fields -> Implementation doc documents these as always returning 0 (functional gap)
[DRIFT] Artifact references match_service.find_active_by_player() -> Implementation uses match_service.get_active_matches() (documented deviation)
```
