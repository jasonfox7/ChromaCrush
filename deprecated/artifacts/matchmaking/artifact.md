# Module Artifact: matchmaking

## Header
- **Author:** Scout Agent (matchmaking)
- **Date:** 2026-02-05
- **Version:** 1.0
- **Status:** Final
- **Dependencies:** `match` (Wave 5), `player` (Wave 1)
- **Dependents:** `api`

---

## Purpose

The **matchmaking** module pairs players for competitive matches in ChromaCrush. It manages real-time matchmaking queues using Redis sorted sets, implementing ELO-based pairing with progressive range expansion to balance match quality against wait times.

Core responsibilities:
- **Queue Management** - Players join/leave matchmaking queues with their current ELO rating
- **ELO-Based Pairing** - Match players within acceptable rating ranges for fair competition
- **Pool Separation** - Maintain separate queues for human-only, bot-only, and mixed play
- **Range Expansion** - Progressively widen ELO search range as wait time increases
- **Queue Timeout** - Remove players who have waited too long without finding a match
- **Match Triggering** - Create matches via the match module when suitable pairs are found
- **Queue Status** - Provide players with their queue position and estimated wait time

The module uses **Redis sorted sets** for efficient ELO-range queries, enabling O(log n) pairing operations. This is an **async** module - all public methods that interact with Redis or other modules are `async def`.

---

## Public Interface

### Class: `MatchmakingService`

The matchmaking module exposes a single service class that receives dependencies via `__init__` injection.

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
    ) -> None:
        ...
```

---

### Inputs

#### `join_queue(player_id: PlayerId, pool_type: PoolType = PoolType.MIXED) -> QueueEntry`

Add a player to the matchmaking queue.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player joining the queue | Must exist, must not already be in queue, must not be in active match |
| `pool_type` | `PoolType` | Which queue pool to join | Must be valid PoolType |

---

#### `leave_queue(player_id: PlayerId) -> bool`

Remove a player from the matchmaking queue.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player leaving the queue | None (no-op if not in queue) |

---

#### `get_queue_status(player_id: PlayerId) -> QueueStatus | None`

Get the current queue status for a player.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player to check | None |

---

#### `find_match(player_id: PlayerId) -> MatchmakingResult`

Attempt to find and create a match for a queued player.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player seeking a match | Must be in queue |

---

#### `process_queue(pool_type: PoolType) -> list[MatchmakingResult]`

Background operation to process all pending matches in a queue pool.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `pool_type` | `PoolType` | Which pool to process | Must be valid PoolType |

---

#### `cleanup_stale_entries() -> int`

Background operation to remove players who have exceeded queue timeout.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| (none) | - | - | - |

Returns count of entries removed.

---

#### `get_queue_stats(pool_type: PoolType | None = None) -> QueueStats`

Get statistics about queue status (admin/monitoring).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `pool_type` | `PoolType \| None` | Filter to specific pool (None for all) | If provided, must be valid |

---

### Outputs

#### `join_queue` returns `QueueEntry`

```python
@dataclass
class QueueEntry:
    """A player's entry in the matchmaking queue."""
    player_id: PlayerId
    player_username: str
    elo_rating: int
    pool_type: PoolType
    joined_at: datetime
    current_elo_range: tuple[int, int]  # (min_elo, max_elo) being searched
    estimated_wait_seconds: int | None
    position_in_queue: int  # 1-indexed position
```

---

#### `leave_queue` returns `bool`

Returns `True` if player was removed from queue, `False` if they weren't in queue.

---

#### `get_queue_status` returns `QueueStatus | None`

```python
@dataclass
class QueueStatus:
    """Current queue status for a player."""
    player_id: PlayerId
    pool_type: PoolType
    elo_rating: int
    joined_at: datetime
    wait_time_seconds: int
    current_elo_range: tuple[int, int]
    potential_opponents: int  # Players in range
    position_in_queue: int
    estimated_wait_seconds: int | None
```

Returns `None` if player is not in any queue.

---

#### `find_match` returns `MatchmakingResult`

```python
@dataclass
class MatchmakingResult:
    """Result of a matchmaking attempt."""
    status: MatchmakingStatus
    player_id: PlayerId
    opponent_id: PlayerId | None
    match_id: MatchId | None
    wait_time_seconds: int
    elo_difference: int | None
    pool_type: PoolType
    message: str


class MatchmakingStatus(Enum):
    MATCHED = "matched"         # Found opponent, match created
    SEARCHING = "searching"     # Still in queue, no opponent found
    EXPIRED = "expired"         # Queue timeout exceeded
    NOT_IN_QUEUE = "not_in_queue"  # Player not in queue
    ERROR = "error"             # Match creation failed
```

---

#### `process_queue` returns `list[MatchmakingResult]`

Returns a list of all matchmaking results from the queue processing cycle.

---

#### `cleanup_stale_entries` returns `int`

Returns the count of stale entries removed.

---

#### `get_queue_stats` returns `QueueStats`

```python
@dataclass
class QueueStats:
    """Statistics about matchmaking queues."""
    pool_type: PoolType | None  # None = aggregate
    total_players: int
    players_by_elo_bucket: dict[str, int]  # "800-900": 5, "900-1000": 12, etc.
    average_wait_seconds: float
    longest_wait_seconds: int
    matches_created_last_hour: int
    average_elo_difference: float
```

---

### Error Cases

| Condition | Error Code | Error Type | Context Fields |
|-----------|------------|------------|----------------|
| Player not found | `NOT_FOUND_PLAYER` | not_found | `player_id` |
| Player already in queue | `CONFLICT_ALREADY_IN_QUEUE` | conflict | `player_id`, `pool_type`, `joined_at` |
| Player in active match | `CONFLICT_PLAYER_IN_MATCH` | conflict | `player_id`, `active_match_id` |
| Player not in queue (for find_match) | `VALIDATION_NOT_IN_QUEUE` | validation | `player_id` |
| Invalid pool type | `VALIDATION_INVALID_INPUT` | validation | `field="pool_type"`, `value` |
| Bot attempting human-only queue | `FORBIDDEN_POOL_RESTRICTED` | forbidden | `player_id`, `pool_type`, `player_type` |
| Human attempting bot-only queue | `FORBIDDEN_POOL_RESTRICTED` | forbidden | `player_id`, `pool_type`, `player_type` |
| Match creation failed | `INTERNAL_MATCHMAKING_ERROR` | internal | `player_id`, `opponent_id`, `original_error` |

---

### Async Behavior

**This module is fully asynchronous.**

All public methods are `async def` because they involve:
- Redis operations via `MatchmakingQueueRepository` (all async)
- Cross-module service calls to `player_service.get_player()`, `player_service.get_elo()`
- Match creation via `match_service.create_match()`

**Async operations:**
- `join_queue` - Reads player, checks active matches, adds to Redis sorted set
- `leave_queue` - Removes from Redis sorted set
- `get_queue_status` - Reads from Redis, calculates statistics
- `find_match` - Queries Redis range, potentially creates match
- `process_queue` - Batch Redis operations, multiple match creations
- `cleanup_stale_entries` - Batch Redis operations

**Error propagation:** All errors are raised through the injected `ErrorServiceProtocol`. Redis errors are caught and wrapped in `INTERNAL_CACHE_ERROR`. Cross-module errors (`NOT_FOUND_PLAYER`, `CONFLICT_PLAYER_IN_MATCH`) propagate unchanged.

**Concurrency considerations:**
- Redis operations are atomic at the command level
- Match creation uses optimistic concurrency - if opponent is taken, retry pairing
- `process_queue` uses Redis WATCH for multi-key operations

---

## Mandatory Service Usage

### Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `matchmaking.elo_initial` | int | 1000 | Initial ELO for new players (used for display) |
| `matchmaking.elo_k_factor` | int | 32 | ELO K-factor (informational) |
| `matchmaking.initial_elo_range` | int | 50 | Starting +/- ELO search range |
| `matchmaking.elo_range_expansion` | int | 50 | How much to expand range per interval |
| `matchmaking.elo_range_expansion_interval_seconds` | int | 30 | How often to expand range |
| `matchmaking.max_elo_range` | int | 500 | Maximum +/- ELO search range |
| `matchmaking.queue_timeout_seconds` | int | 300 | Seconds before player removed from queue |
| `matchmaking.process_interval_seconds` | int | 5 | How often to run queue processing |
| `matchmaking.min_wait_before_expansion` | int | 10 | Minimum seconds before first range expansion |

---

### Logging Events

| Event | Severity | Trigger | Context |
|-------|----------|---------|---------|
| `matchmaking.player_joined` | INFO | Player joins queue | `player_id`, `pool_type`, `elo_rating` |
| `matchmaking.player_left` | INFO | Player leaves queue | `player_id`, `pool_type`, `wait_time_seconds` |
| `matchmaking.match_found` | INFO | Match created | `player1_id`, `player2_id`, `match_id`, `elo_difference`, `wait_time_seconds` |
| `matchmaking.range_expanded` | DEBUG | ELO range expanded | `player_id`, `old_range`, `new_range` |
| `matchmaking.queue_timeout` | INFO | Player timed out | `player_id`, `pool_type`, `wait_time_seconds` |
| `matchmaking.no_opponent` | DEBUG | No suitable opponent found | `player_id`, `elo_rating`, `elo_range`, `potential_count` |
| `matchmaking.opponent_taken` | DEBUG | Selected opponent already matched | `player_id`, `opponent_id` |
| `matchmaking.queue_processed` | DEBUG | Queue processing completed | `pool_type`, `players_processed`, `matches_created` |
| `matchmaking.stale_cleanup` | INFO | Stale entries removed | `entries_removed`, `pool_type` |
| `matchmaking.creation_failed` | ERROR | Match creation failed | `player_id`, `opponent_id`, `error` |

---

### Error Types Used

From the error taxonomy (Interface Agent guidance):

- `NOT_FOUND_PLAYER` - Player ID doesn't exist
- `VALIDATION_INVALID_INPUT` - Invalid input parameters
- `VALIDATION_NOT_IN_QUEUE` - Player not in matchmaking queue (new error type)
- `CONFLICT_ALREADY_IN_QUEUE` - Player already queued (new error type)
- `CONFLICT_PLAYER_IN_MATCH` - Player already in active match
- `FORBIDDEN_POOL_RESTRICTED` - Player type not allowed in pool (new error type)
- `INTERNAL_MATCHMAKING_ERROR` - Match creation or queue operation failed (new error type)
- `INTERNAL_CACHE_ERROR` - Redis operation failed

**New error types to add to taxonomy:**
- `VALIDATION_NOT_IN_QUEUE` - Player attempted operation requiring queue membership
- `CONFLICT_ALREADY_IN_QUEUE` - Player already in matchmaking queue
- `FORBIDDEN_POOL_RESTRICTED` - Pool restricted to different player type
- `INTERNAL_MATCHMAKING_ERROR` - Matchmaking operation failed

All errors created through injected `ErrorServiceProtocol`, never bare raises.

---

## Data Access

### Owned Data

The matchmaking module owns Redis-backed queue data. **No PostgreSQL tables** - all state is transient and stored in Redis.

#### Redis Data Structures

**Sorted Sets (by pool type):**
```
chromacrush:matchmaking:queue:{pool_type}
  Score: player's ELO rating
  Member: player_id (UUID as string)
```

**Hash (per queued player):**
```
chromacrush:matchmaking:player:{player_id}
  pool_type: string
  elo_rating: int
  joined_at: ISO timestamp
  last_expansion_at: ISO timestamp
  current_min_elo: int
  current_max_elo: int
```

**Key patterns:**
- `chromacrush:matchmaking:queue:human` - Human-only pool sorted set
- `chromacrush:matchmaking:queue:bot` - Bot-only pool sorted set
- `chromacrush:matchmaking:queue:mixed` - Mixed pool sorted set
- `chromacrush:matchmaking:player:{player_id}` - Player queue state hash

**TTL strategy:**
- Player hashes have TTL = `queue_timeout_seconds + 60` (buffer for cleanup)
- Sorted set entries don't expire (cleaned by `cleanup_stale_entries`)

---

### Repository Interfaces Required

```python
# src/data/protocols/matchmaking_queue_repository.py
from typing import Protocol
from uuid import UUID
from datetime import datetime

from src.core.types.game import PlayerId
from src.modules.matchmaking.types import PoolType, QueueEntryData


class MatchmakingQueueRepositoryProtocol(Protocol):
    """Repository interface for matchmaking queue data (Redis-backed)."""

    async def add_to_queue(
        self,
        player_id: UUID,
        elo_rating: int,
        pool_type: PoolType,
        initial_elo_range: int,
    ) -> QueueEntryData:
        """
        Add player to matchmaking queue.

        Creates sorted set entry and player hash atomically.
        """
        ...

    async def remove_from_queue(self, player_id: UUID) -> bool:
        """
        Remove player from queue.

        Removes from sorted set and deletes player hash.
        Returns True if player was in queue.
        """
        ...

    async def get_player_queue_state(self, player_id: UUID) -> QueueEntryData | None:
        """Get player's current queue state from hash."""
        ...

    async def is_in_queue(self, player_id: UUID) -> bool:
        """Check if player is in any queue."""
        ...

    async def find_opponents_in_range(
        self,
        pool_type: PoolType,
        min_elo: int,
        max_elo: int,
        exclude_player_id: UUID,
        limit: int = 10,
    ) -> list[tuple[UUID, int]]:
        """
        Find players in ELO range using ZRANGEBYSCORE.

        Returns list of (player_id, elo_rating) tuples.
        Sorted by wait time (FIFO within range).
        """
        ...

    async def get_queue_count(self, pool_type: PoolType) -> int:
        """Get count of players in a queue."""
        ...

    async def get_all_queued_players(
        self,
        pool_type: PoolType,
    ) -> list[QueueEntryData]:
        """Get all players in a queue (for processing)."""
        ...

    async def update_elo_range(
        self,
        player_id: UUID,
        new_min_elo: int,
        new_max_elo: int,
    ) -> None:
        """Update player's expanded ELO range."""
        ...

    async def remove_stale_entries(
        self,
        cutoff_time: datetime,
    ) -> int:
        """
        Remove entries older than cutoff.

        Returns count of entries removed.
        """
        ...

    async def get_players_by_elo_bucket(
        self,
        pool_type: PoolType,
        bucket_size: int = 100,
    ) -> dict[str, int]:
        """Get count of players in each ELO bucket."""
        ...

    async def atomic_remove_pair(
        self,
        player1_id: UUID,
        player2_id: UUID,
    ) -> bool:
        """
        Atomically remove two players from queue.

        Uses Redis WATCH/MULTI for atomicity.
        Returns True if both were removed, False if either was already gone.
        """
        ...
```

---

### Data Read from Other Modules

| Data | Source Module | Access Method | Purpose |
|------|---------------|---------------|---------|
| Player entity | `player` | `PlayerServiceProtocol.get_player()` | Validate player exists, get player type |
| Player ELO | `player` | `PlayerServiceProtocol.get_elo()` | Get current rating for queue entry |
| Active matches | `match` | `MatchServiceProtocol.find_active_by_player()` (via match repo indirectly) | Prevent queuing while in match |
| Match creation | `match` | `MatchServiceProtocol.create_match()` | Create match when pair found |

---

### Transaction Requirements

| Operation | Transaction Scope | Notes |
|-----------|-------------------|-------|
| `join_queue` | Redis atomic (MULTI) | Add to sorted set + create hash atomically |
| `leave_queue` | Redis atomic (MULTI) | Remove from sorted set + delete hash atomically |
| `find_match` + create | Distributed | Redis removal + PostgreSQL match creation - use optimistic retry |
| `cleanup_stale_entries` | Redis atomic per batch | Process in batches to avoid long locks |

**Critical: Atomic Pairing**

When a match is found, both players must be removed from the queue atomically before the match is created. If match creation fails, they should be re-added (compensating transaction).

```python
# Pseudocode for atomic pairing
async def _create_match_from_pair(self, player1_id, player2_id):
    # 1. Atomically remove both from queue
    removed = await self._queue_repo.atomic_remove_pair(player1_id, player2_id)
    if not removed:
        return None  # One was already taken

    # 2. Create match
    try:
        match = await self._match_service.create_match(player1_id, player2_id)
        return match
    except AppError as e:
        # 3. Compensate: re-add to queues
        await self._re_add_to_queue(player1_id)
        await self._re_add_to_queue(player2_id)
        raise self._errors.internal(
            "Match creation failed",
            code="INTERNAL_MATCHMAKING_ERROR",
            original_error=str(e),
        )
```

---

## Presentation Boundary

### Business Logic API Surface

The matchmaking module exposes domain objects and DTOs:
- Input: `PlayerId`, `PoolType`
- Output: `QueueEntry`, `QueueStatus`, `MatchmakingResult`, `QueueStats`

All types are defined in this module (`src/modules/matchmaking/types.py`) or imported from `src/core/types/`.

### Adapter Needs

Presentation adapters need to:
1. Convert UUIDs to strings for JSON
2. Format timestamps to ISO format
3. Calculate human-readable wait time ("2 minutes", "30 seconds")
4. Convert ELO range tuple to object `{ min: 950, max: 1050 }`
5. Map `MatchmakingStatus` enum to user-friendly messages

Example adapter output for API:
```python
{
    "status": "searching",
    "queue_position": 3,
    "elo_rating": 1050,
    "current_range": { "min": 1000, "max": 1100 },
    "potential_opponents": 5,
    "wait_time": "45 seconds",
    "estimated_wait": "30-60 seconds"
}
```

### What Does NOT Belong in This Module

- No JSON serialization (adapter responsibility)
- No HTTP response construction
- No terminal formatting
- No WebSocket/SSE push notifications (separate notification system)
- No ELO calculation logic (player module responsibility)
- No match gameplay logic (match module responsibility)
- No leaderboard management (separate leaderboard concern)

---

## Internal Design

### Core Types

```python
# src/modules/matchmaking/types.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from src.core.types.game import PlayerId, MatchId


class PoolType(Enum):
    """Matchmaking queue pool types."""
    HUMAN = "human"    # Human players only
    BOT = "bot"        # Bot players only
    MIXED = "mixed"    # Humans and bots together


class MatchmakingStatus(Enum):
    """Result status of a matchmaking attempt."""
    MATCHED = "matched"
    SEARCHING = "searching"
    EXPIRED = "expired"
    NOT_IN_QUEUE = "not_in_queue"
    ERROR = "error"


@dataclass
class QueueEntryData:
    """Raw queue entry data from Redis."""
    player_id: PlayerId
    elo_rating: int
    pool_type: PoolType
    joined_at: datetime
    last_expansion_at: datetime
    current_min_elo: int
    current_max_elo: int


@dataclass
class QueueEntry:
    """A player's entry in the matchmaking queue."""
    player_id: PlayerId
    player_username: str
    elo_rating: int
    pool_type: PoolType
    joined_at: datetime
    current_elo_range: tuple[int, int]
    estimated_wait_seconds: int | None
    position_in_queue: int


@dataclass
class QueueStatus:
    """Current queue status for a player."""
    player_id: PlayerId
    pool_type: PoolType
    elo_rating: int
    joined_at: datetime
    wait_time_seconds: int
    current_elo_range: tuple[int, int]
    potential_opponents: int
    position_in_queue: int
    estimated_wait_seconds: int | None


@dataclass
class MatchmakingResult:
    """Result of a matchmaking attempt."""
    status: MatchmakingStatus
    player_id: PlayerId
    opponent_id: PlayerId | None = None
    match_id: MatchId | None = None
    wait_time_seconds: int = 0
    elo_difference: int | None = None
    pool_type: PoolType = PoolType.MIXED
    message: str = ""


@dataclass
class QueueStats:
    """Statistics about matchmaking queues."""
    pool_type: PoolType | None
    total_players: int
    players_by_elo_bucket: dict[str, int]
    average_wait_seconds: float
    longest_wait_seconds: int
    matches_created_last_hour: int
    average_elo_difference: float
```

---

### Algorithm: Join Queue

```python
async def join_queue(
    self,
    player_id: PlayerId,
    pool_type: PoolType = PoolType.MIXED,
) -> QueueEntry:
    # 1. Validate player exists and get details
    player = await self._player_service.get_player(player_id)

    # 2. Validate pool type matches player type
    if pool_type == PoolType.HUMAN and player.is_bot:
        raise self._errors.forbidden(
            "Bot players cannot join human-only queue",
            code="FORBIDDEN_POOL_RESTRICTED",
            player_id=str(player_id),
            pool_type=pool_type.value,
            player_type="bot",
        )

    if pool_type == PoolType.BOT and not player.is_bot:
        raise self._errors.forbidden(
            "Human players cannot join bot-only queue",
            code="FORBIDDEN_POOL_RESTRICTED",
            player_id=str(player_id),
            pool_type=pool_type.value,
            player_type="human",
        )

    # 3. Check not already in queue
    if await self._queue_repo.is_in_queue(player_id):
        existing = await self._queue_repo.get_player_queue_state(player_id)
        raise self._errors.conflict(
            "Player already in matchmaking queue",
            code="CONFLICT_ALREADY_IN_QUEUE",
            player_id=str(player_id),
            pool_type=existing.pool_type.value if existing else None,
            joined_at=existing.joined_at.isoformat() if existing else None,
        )

    # 4. Check not in active match
    active_matches = await self._match_service.find_active_by_player(player_id)
    if active_matches:
        raise self._errors.conflict(
            "Player is in an active match",
            code="CONFLICT_PLAYER_IN_MATCH",
            player_id=str(player_id),
            active_match_id=str(active_matches[0].match_id),
        )

    # 5. Get current ELO
    elo_rating = await self._player_service.get_elo(player_id)

    # 6. Calculate initial ELO range
    initial_range = self._config.get("matchmaking.initial_elo_range", 50)

    # 7. Add to queue
    entry_data = await self._queue_repo.add_to_queue(
        player_id=player_id,
        elo_rating=elo_rating,
        pool_type=pool_type,
        initial_elo_range=initial_range,
    )

    # 8. Log
    self._logger.info(
        "Player joined matchmaking queue",
        player_id=str(player_id),
        pool_type=pool_type.value,
        elo_rating=elo_rating,
    )

    # 9. Calculate position and estimate
    position = await self._calculate_queue_position(player_id, pool_type)
    estimate = await self._estimate_wait_time(elo_rating, pool_type)

    return QueueEntry(
        player_id=player_id,
        player_username=player.username,
        elo_rating=elo_rating,
        pool_type=pool_type,
        joined_at=entry_data.joined_at,
        current_elo_range=(entry_data.current_min_elo, entry_data.current_max_elo),
        estimated_wait_seconds=estimate,
        position_in_queue=position,
    )
```

---

### Algorithm: Find Match (Single Player)

```python
async def find_match(
    self,
    player_id: PlayerId,
) -> MatchmakingResult:
    # 1. Get player's queue state
    queue_state = await self._queue_repo.get_player_queue_state(player_id)
    if queue_state is None:
        raise self._errors.validation(
            "Player not in matchmaking queue",
            code="VALIDATION_NOT_IN_QUEUE",
            player_id=str(player_id),
        )

    # 2. Check for timeout
    wait_seconds = (datetime.utcnow() - queue_state.joined_at).total_seconds()
    timeout = self._config.get("matchmaking.queue_timeout_seconds", 300)

    if wait_seconds > timeout:
        await self._queue_repo.remove_from_queue(player_id)
        self._logger.info(
            "Player queue timeout",
            player_id=str(player_id),
            pool_type=queue_state.pool_type.value,
            wait_time_seconds=int(wait_seconds),
        )
        return MatchmakingResult(
            status=MatchmakingStatus.EXPIRED,
            player_id=player_id,
            wait_time_seconds=int(wait_seconds),
            pool_type=queue_state.pool_type,
            message="Queue timeout exceeded",
        )

    # 3. Expand ELO range if needed
    await self._maybe_expand_elo_range(player_id, queue_state)

    # Refresh state after potential expansion
    queue_state = await self._queue_repo.get_player_queue_state(player_id)

    # 4. Find opponents in range
    opponents = await self._queue_repo.find_opponents_in_range(
        pool_type=queue_state.pool_type,
        min_elo=queue_state.current_min_elo,
        max_elo=queue_state.current_max_elo,
        exclude_player_id=player_id,
        limit=10,
    )

    if not opponents:
        self._logger.debug(
            "No opponent found",
            player_id=str(player_id),
            elo_rating=queue_state.elo_rating,
            elo_range=(queue_state.current_min_elo, queue_state.current_max_elo),
            potential_count=0,
        )
        return MatchmakingResult(
            status=MatchmakingStatus.SEARCHING,
            player_id=player_id,
            wait_time_seconds=int(wait_seconds),
            pool_type=queue_state.pool_type,
            message="Searching for opponent",
        )

    # 5. Try to match with best opponent (FIFO, then closest ELO)
    for opponent_id, opponent_elo in opponents:
        match_result = await self._try_create_match(
            player_id=player_id,
            player_elo=queue_state.elo_rating,
            opponent_id=opponent_id,
            opponent_elo=opponent_elo,
            pool_type=queue_state.pool_type,
            wait_seconds=wait_seconds,
        )
        if match_result is not None:
            return match_result

    # 6. All opponents were taken
    return MatchmakingResult(
        status=MatchmakingStatus.SEARCHING,
        player_id=player_id,
        wait_time_seconds=int(wait_seconds),
        pool_type=queue_state.pool_type,
        message="Opponent selection in progress",
    )


async def _try_create_match(
    self,
    player_id: PlayerId,
    player_elo: int,
    opponent_id: PlayerId,
    opponent_elo: int,
    pool_type: PoolType,
    wait_seconds: float,
) -> MatchmakingResult | None:
    """Attempt to create a match with the opponent. Returns None if opponent was taken."""

    # 1. Atomically remove both from queue
    removed = await self._queue_repo.atomic_remove_pair(player_id, opponent_id)
    if not removed:
        self._logger.debug(
            "Opponent already taken",
            player_id=str(player_id),
            opponent_id=str(opponent_id),
        )
        return None

    # 2. Create match
    try:
        match_state = await self._match_service.create_match(
            player1_id=player_id,
            player2_id=opponent_id,
        )

        elo_diff = abs(player_elo - opponent_elo)

        self._logger.info(
            "Match found",
            player1_id=str(player_id),
            player2_id=str(opponent_id),
            match_id=str(match_state.match_id),
            elo_difference=elo_diff,
            wait_time_seconds=int(wait_seconds),
        )

        return MatchmakingResult(
            status=MatchmakingStatus.MATCHED,
            player_id=player_id,
            opponent_id=opponent_id,
            match_id=match_state.match_id,
            wait_time_seconds=int(wait_seconds),
            elo_difference=elo_diff,
            pool_type=pool_type,
            message="Match found!",
        )

    except AppError as e:
        # Compensate: re-add both to queues
        self._logger.error(
            "Match creation failed, compensating",
            player_id=str(player_id),
            opponent_id=str(opponent_id),
            error=str(e),
        )

        # Re-add to queues (best effort)
        try:
            await self._re_add_to_queue(player_id, player_elo, pool_type)
            await self._re_add_to_queue(opponent_id, opponent_elo, pool_type)
        except Exception:
            pass  # Log but don't propagate

        raise self._errors.internal(
            "Match creation failed",
            code="INTERNAL_MATCHMAKING_ERROR",
            player_id=str(player_id),
            opponent_id=str(opponent_id),
            original_error=str(e),
        )
```

---

### Algorithm: ELO Range Expansion

```python
async def _maybe_expand_elo_range(
    self,
    player_id: PlayerId,
    queue_state: QueueEntryData,
) -> None:
    """Expand ELO search range based on wait time."""

    wait_seconds = (datetime.utcnow() - queue_state.joined_at).total_seconds()
    min_wait = self._config.get("matchmaking.min_wait_before_expansion", 10)

    if wait_seconds < min_wait:
        return

    time_since_expansion = (datetime.utcnow() - queue_state.last_expansion_at).total_seconds()
    expansion_interval = self._config.get("matchmaking.elo_range_expansion_interval_seconds", 30)

    if time_since_expansion < expansion_interval:
        return

    max_range = self._config.get("matchmaking.max_elo_range", 500)
    current_range = queue_state.current_max_elo - queue_state.elo_rating

    if current_range >= max_range:
        return

    expansion = self._config.get("matchmaking.elo_range_expansion", 50)
    new_range = min(current_range + expansion, max_range)

    new_min_elo = max(0, queue_state.elo_rating - new_range)
    new_max_elo = queue_state.elo_rating + new_range

    await self._queue_repo.update_elo_range(player_id, new_min_elo, new_max_elo)

    self._logger.debug(
        "ELO range expanded",
        player_id=str(player_id),
        old_range=(queue_state.current_min_elo, queue_state.current_max_elo),
        new_range=(new_min_elo, new_max_elo),
    )
```

---

### Algorithm: Process Queue (Background)

```python
async def process_queue(
    self,
    pool_type: PoolType,
) -> list[MatchmakingResult]:
    """
    Process all players in a queue, attempting to create matches.

    Called periodically by background worker.
    """
    results = []

    # 1. Get all queued players, ordered by join time (FIFO)
    players = await self._queue_repo.get_all_queued_players(pool_type)

    # 2. Track matched players to avoid double-processing
    matched_ids: set[PlayerId] = set()

    # 3. Process each player
    for entry in players:
        if entry.player_id in matched_ids:
            continue

        # 4. Expand range if needed
        await self._maybe_expand_elo_range(entry.player_id, entry)

        # 5. Find opponents
        opponents = await self._queue_repo.find_opponents_in_range(
            pool_type=pool_type,
            min_elo=entry.current_min_elo,
            max_elo=entry.current_max_elo,
            exclude_player_id=entry.player_id,
            limit=10,
        )

        # 6. Filter out already-matched opponents
        opponents = [(oid, elo) for oid, elo in opponents if oid not in matched_ids]

        if not opponents:
            continue

        # 7. Try to match (FIFO priority)
        wait_seconds = (datetime.utcnow() - entry.joined_at).total_seconds()

        for opponent_id, opponent_elo in opponents:
            if opponent_id in matched_ids:
                continue

            result = await self._try_create_match(
                player_id=entry.player_id,
                player_elo=entry.elo_rating,
                opponent_id=opponent_id,
                opponent_elo=opponent_elo,
                pool_type=pool_type,
                wait_seconds=wait_seconds,
            )

            if result is not None:
                results.append(result)
                matched_ids.add(entry.player_id)
                matched_ids.add(opponent_id)
                break

    self._logger.debug(
        "Queue processed",
        pool_type=pool_type.value,
        players_processed=len(players),
        matches_created=len(results),
    )

    return results
```

---

## CLI Surface

### Commands

```bash
# Queue operations
chromacrush matchmaking join <player-id> [--pool human|bot|mixed]
chromacrush matchmaking leave <player-id>
chromacrush matchmaking status <player-id>
chromacrush matchmaking find <player-id>

# Admin operations
chromacrush matchmaking process [--pool human|bot|mixed|all]
chromacrush matchmaking cleanup
chromacrush matchmaking stats [--pool human|bot|mixed]
chromacrush matchmaking list [--pool human|bot|mixed] [--limit N]
```

### Example Invocations

```bash
$ chromacrush matchmaking join abc123 --pool mixed
Joined matchmaking queue!
  Player: alice (abc123)
  Pool: mixed
  ELO: 1050
  Search range: 1000 - 1100
  Queue position: 3
  Estimated wait: 30-60 seconds

$ chromacrush matchmaking status abc123
Queue Status:
  Player: alice (abc123)
  Pool: mixed
  ELO: 1050
  Wait time: 45 seconds
  Search range: 950 - 1150 (expanded)
  Potential opponents: 5
  Queue position: 2

$ chromacrush matchmaking find abc123
Match found!
  Match ID: 550e8400-e29b-41d4-a716-446655440000
  Opponent: bob (def456)
  ELO difference: 35 (bob: 1015)
  Wait time: 52 seconds

$ chromacrush matchmaking stats --pool mixed
Queue Statistics (mixed):
  Total players: 47
  ELO distribution:
    800-900:   3 players
    900-1000:  12 players
    1000-1100: 18 players
    1100-1200: 9 players
    1200+:     5 players
  Average wait: 38 seconds
  Longest wait: 2m 15s
  Matches (last hour): 156
  Average ELO diff: 42

$ chromacrush matchmaking process --pool all
Processing queues...
  human: 3 matches created
  bot:   5 matches created
  mixed: 12 matches created
Total: 20 matches created
```

### CLI Composition

Commands in `src/cli/commands/matchmaking_commands.py` use the same `MatchmakingService` instance as the main application, injected through the CLI composition root.

---

## Edge Cases & Decisions

### EC-1: Player Joins Queue While Opponent Searches

**Scenario:** Player A is searching. Player B joins queue. Player A's search completes before B is indexed.

**Decision:** Redis sorted set operations are atomic. Player B's add completes before or after A's query runs. If A's query runs first, A doesn't see B. Next search iteration will find B.

**Rationale:** Redis atomicity guarantees consistency. The short process interval (5s) ensures no significant delay.

---

### EC-2: Two Players Select Same Opponent

**Scenario:** Player A and B both find Player C as their best match simultaneously.

**Decision:** `atomic_remove_pair` uses Redis WATCH. First to complete the transaction wins. Second gets a retry with a different opponent.

**Rationale:** Optimistic concurrency is standard for Redis. The operation is fast enough that retries are rare.

---

### EC-3: Match Creation Fails After Queue Removal

**Scenario:** Both players removed from queue, but `match_service.create_match()` fails.

**Decision:** Compensating transaction re-adds both players to their queues with original timestamps preserved.

**Rationale:** Players shouldn't lose queue position due to transient failures. Re-adding preserves FIFO fairness.

---

### EC-4: Player in Multiple Pools

**Scenario:** Player wants to be in multiple pools simultaneously (e.g., mixed and human-only).

**Decision:** Not supported. Player can only be in one queue at a time.

**Rationale:** Simplifies logic, prevents double-matching. Player can leave one queue and join another.

---

### EC-5: ELO Changes While in Queue

**Scenario:** Player's ELO changes (from another system) while they're queued.

**Decision:** Queue entry uses ELO snapshot at join time. Updated ELO takes effect on next queue join.

**Rationale:** Mid-queue ELO changes would cause confusion and potential race conditions. Snapshot is simpler and fair.

---

### EC-6: Bot in Human-Only Pool

**Scenario:** Bot player attempts to join human-only queue.

**Decision:** Reject with `FORBIDDEN_POOL_RESTRICTED` error.

**Rationale:** Pool separation is a core feature for player preference. Enforcement must be strict.

---

### EC-7: Queue Timeout During Match Creation

**Scenario:** Player times out at the exact moment they're being matched.

**Decision:** Timeout check happens before match creation. If player times out, they're removed and not matched. The opponent continues searching.

**Rationale:** Time ordering ensures consistent behavior. Timeout is a terminal state.

---

### EC-8: Empty Queue

**Scenario:** No other players in queue when player joins.

**Decision:** Player enters queue and waits. `find_match` returns `SEARCHING` status. ELO range expands over time until timeout.

**Rationale:** Normal queue behavior. UI shows "searching for opponent."

---

### EC-9: Very Wide ELO Gap

**Scenario:** Only available opponent is 400+ ELO points away.

**Decision:** After max expansion (default: 500), player either matches with available opponent or times out. No forced matching outside configured range.

**Rationale:** Quality floor on matches is important. Players prefer timeout over extremely unfair matches.

---

### EC-10: Rapid Join/Leave Cycling

**Scenario:** Player rapidly joins and leaves queue (potential abuse).

**Decision:** No rate limiting at matchmaking layer. If needed, add at API layer.

**Rationale:** Keep matchmaking module focused. Rate limiting is a cross-cutting concern for the API layer.

---

## Open Questions

None. All design decisions resolved within existing guidance and GDD specifications.

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent (matchmaking) |
