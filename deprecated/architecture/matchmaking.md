# Module Architecture Report: matchmaking

**Module:** matchmaking
**Build Wave:** 6
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The matchmaking module provides ELO-based player pairing for ChromaCrush's asynchronous versus mode. It uses Redis sorted sets for O(log n) ELO range queries with a three-pool system (HUMAN, BOT, MIXED), progressive ELO range expansion to balance match quality against wait times, FIFO ordering within ELO range, and atomic pairing with compensating transactions. All matchmaking state is transient in Redis with no PostgreSQL persistence. All public methods are **asynchronous** (`async def`). Background queue processing and stale entry cleanup are designed to be called by an external worker (arq task).

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `join_queue` | `(player_id, pool_type=MIXED) -> QueueEntry` | Join matchmaking queue |
| `leave_queue` | `(player_id) -> bool` | Leave queue; returns False if not present |
| `get_queue_status` | `(player_id) -> QueueStatus \| None` | Check current queue status |
| `find_match` | `(player_id) -> MatchmakingResult` | Attempt to find an opponent match |
| `process_queue` | `(pool_type) -> list[MatchmakingResult]` | Process all queued players in a pool |
| `cleanup_stale_entries` | `() -> int` | Remove timed-out queue entries |
| `get_queue_stats` | `(pool_type=None) -> QueueStats` | Get queue statistics |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | ELO range, expansion intervals, queue timeout |
| `logger` | `LoggerProtocol` | Structured logging |
| `errors` | `ErrorServiceProtocol` | Create not_found, conflict, validation, forbidden, internal errors |
| `match_service` | `MatchServiceProtocol` | Create matches via `create_match()`, check active matches via `get_active_matches()` |
| `player_service` | `PlayerServiceProtocol` | Get player info and ELO rating |
| `matchmaking_queue_repository` | `MatchmakingQueueRepositoryProtocol` | Redis-backed queue operations (11 async methods) |

---

## 4. Data Owned

| Key Pattern | Storage | Description |
|-------------|---------|-------------|
| `chromacrush:matchmaking:queue:{pool_type}` | Redis sorted set | Queue per pool; score = ELO, member = player_id |
| `chromacrush:matchmaking:player:{player_id}` | Redis hash | Player queue metadata: pool_type, elo_rating, joined_at, expansion state, ELO range |

All data is transient with TTL (queue_timeout + 60s buffer). No PostgreSQL tables.

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `matchmaking.initial_elo_range` | int | 50 | Starting +/- ELO search range |
| `matchmaking.elo_range_expansion` | int | 50 | Range expansion per interval |
| `matchmaking.elo_range_expansion_interval_seconds` | int | 30 | Seconds between expansions |
| `matchmaking.max_elo_range` | int | 500 | Maximum +/- ELO search range |
| `matchmaking.queue_timeout_seconds` | int | 300 | Seconds before queue entry expires |
| `matchmaking.min_wait_before_expansion` | int | 10 | Minimum wait before first expansion |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `NOT_FOUND_PLAYER` | 404 | Player ID does not exist |
| `CONFLICT_ALREADY_IN_QUEUE` | 409 | Player already in a queue |
| `CONFLICT_PLAYER_IN_MATCH` | 409 | Player has an active match |
| `VALIDATION_NOT_IN_QUEUE` | 400 | Player not in queue (for find_match) |
| `FORBIDDEN_POOL_RESTRICTED` | 403 | Player type not allowed in requested pool |
| `INTERNAL_MATCHMAKING_ERROR` | 500 | Match creation failed after queue removal |

---

## 7. Cross-Module Interactions

**Called by:**
- `api` -- exposes matchmaking endpoints (join, leave, status, find)

**Calls:**
- `match` -- calls `create_match()` when pair found, `get_active_matches()` to check concurrent matches
- `player` -- calls `get_player()` and `get_elo()` for player data and ELO ratings

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `PoolType` | `src/modules/matchmaking/types.py` | Enum: HUMAN, BOT, MIXED |
| `MatchmakingStatus` | `src/modules/matchmaking/types.py` | Enum: MATCHED, SEARCHING, EXPIRED, NOT_IN_QUEUE, ERROR |
| `QueueEntryData` | `src/modules/matchmaking/types.py` | Raw Redis queue entry data |
| `QueueEntry` | `src/modules/matchmaking/types.py` | Player's queue entry with position and wait estimate |
| `QueueStatus` | `src/modules/matchmaking/types.py` | Current queue status with opponent count |
| `MatchmakingResult` | `src/modules/matchmaking/types.py` | Result of matchmaking attempt: status, match_id, opponent, wait_time |
| `QueueStats` | `src/modules/matchmaking/types.py` | Queue statistics with ELO distribution |
| `MatchmakingQueueRepositoryProtocol` | `src/data/protocols/matchmaking_queue_repository.py` | Redis queue protocol with 11 async methods |
