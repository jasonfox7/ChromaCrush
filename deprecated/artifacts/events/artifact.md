# Module Artifact: events

## Header
- **Author:** Scout Agent (events)
- **Date:** 2026-02-05
- **Version:** 1.0
- **Status:** Final
- **Dependencies:** `vault` (Wave 3), `energy` (Wave 2), `match` (Wave 5), `player` (Wave 1)
- **Dependents:** `ads`

---

## Purpose

The **events** module manages time-limited events and competitive seasons in ChromaCrush. It orchestrates special gameplay periods that drive player engagement through:

1. **Flash Events** - Short-duration special challenges (2-4 hours) with immediate rewards
2. **Weekly Events** - Multi-day events with progressive reward tiers
3. **Seasonal Events** - Extended themed events (2-4 weeks) with exclusive cosmetics and artifacts
4. **Event Leaderboards** - Real-time competitive rankings within each event
5. **Participation Tracking** - Record who joined events and their performance
6. **Reward Distribution** - Grant artifacts, energy, and other rewards based on rankings
7. **Event Scheduling** - Automated event activation/deactivation based on configured times

The events module serves both psychological engagement goals (urgency, exclusivity, competition) and provides content variety to prevent player fatigue. Per the GDD, events create "FOMO mechanics" that drive return engagement and provide a reason to play beyond standard matches.

This module is **asynchronous** - all public methods involving database or Redis operations are `async def`.

---

## Public Interface

### Class: `EventService`

The events module exposes a single service class that receives dependencies via `__init__` injection.

```python
class EventService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        data_ctx: DataContextProtocol,
        redis_ctx: RedisContextProtocol,
        vault_service: VaultServiceProtocol,
        energy_service: EnergyServiceProtocol,
        match_service: MatchServiceProtocol,
        player_service: PlayerServiceProtocol,
        event_repository: EventRepositoryProtocol,
        event_participant_repository: EventParticipantRepositoryProtocol,
        event_leaderboard_repository: EventLeaderboardRepositoryProtocol,
    ) -> None:
        ...
```

---

### Inputs

#### `create_event(event_data: EventCreate) -> Event`

Creates a new event (admin operation).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_data.name` | `str` | Display name | 3-100 chars |
| `event_data.event_type` | `EventType` | FLASH, WEEKLY, SEASONAL | Valid enum value |
| `event_data.description` | `str` | Event description | Max 1000 chars |
| `event_data.start_at` | `datetime` | When event activates | Must be in future |
| `event_data.end_at` | `datetime` | When event ends | Must be after start_at |
| `event_data.scoring_type` | `ScoringType` | How scores are calculated | Valid enum value |
| `event_data.entry_requirements` | `EntryRequirements` | Level, energy cost, etc. | Optional, validated if present |
| `event_data.reward_tiers` | `list[RewardTier]` | Rewards by rank/percentile | At least one tier |
| `event_data.rules` | `EventRules` | Event-specific rules | Optional |

---

#### `get_event(event_id: EventId) -> Event`

Retrieves event details.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_id` | `EventId` | The event to retrieve | Must exist |

---

#### `list_events(status: EventStatus | None = None, event_type: EventType | None = None, limit: int = 20, offset: int = 0) -> PaginatedResult[EventSummary]`

Lists events with optional filtering.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `status` | `EventStatus \| None` | Filter by status | Valid enum if provided |
| `event_type` | `EventType \| None` | Filter by type | Valid enum if provided |
| `limit` | `int` | Max results | 1-100 |
| `offset` | `int` | Pagination offset | >= 0 |

---

#### `get_active_events() -> list[Event]`

Gets all currently active events.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| (none) | - | - | - |

---

#### `join_event(event_id: EventId, player_id: PlayerId) -> EventParticipant`

Registers a player for an event.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_id` | `EventId` | The event to join | Must exist, must be active |
| `player_id` | `PlayerId` | The player joining | Must exist, must meet requirements |

---

#### `leave_event(event_id: EventId, player_id: PlayerId) -> None`

Withdraws a player from an event (if allowed).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_id` | `EventId` | The event | Must exist |
| `player_id` | `PlayerId` | The player leaving | Must be a participant |

---

#### `record_event_match(event_id: EventId, player_id: PlayerId, match_id: MatchId, score: int, match_stats: MatchEventStats) -> EventParticipant`

Records a match played as part of an event.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_id` | `EventId` | The event | Must exist, must be active |
| `player_id` | `PlayerId` | The player | Must be a participant |
| `match_id` | `MatchId` | The match played | Must be a valid completed match |
| `score` | `int` | Score achieved | >= 0 |
| `match_stats` | `MatchEventStats` | Additional stats | Valid stats object |

---

#### `get_leaderboard(event_id: EventId, limit: int = 100, offset: int = 0) -> EventLeaderboard`

Gets the current leaderboard for an event.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_id` | `EventId` | The event | Must exist |
| `limit` | `int` | Max entries | 1-500 |
| `offset` | `int` | Pagination offset | >= 0 |

---

#### `get_player_rank(event_id: EventId, player_id: PlayerId) -> PlayerEventRank`

Gets a specific player's rank in an event.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_id` | `EventId` | The event | Must exist |
| `player_id` | `PlayerId` | The player | Must be a participant |

---

#### `get_player_events(player_id: PlayerId, include_past: bool = False, limit: int = 20, offset: int = 0) -> PaginatedResult[PlayerEventSummary]`

Gets events a player is participating in or has participated in.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist |
| `include_past` | `bool` | Include completed events | - |
| `limit` | `int` | Max results | 1-100 |
| `offset` | `int` | Pagination offset | >= 0 |

---

#### `get_event_participant(event_id: EventId, player_id: PlayerId) -> EventParticipant`

Gets a player's participation record for an event.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_id` | `EventId` | The event | Must exist |
| `player_id` | `PlayerId` | The player | Must be a participant |

---

#### `finalize_event(event_id: EventId) -> EventFinalizationResult`

Ends an event and distributes rewards (automated or admin).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_id` | `EventId` | The event to finalize | Must be ended, not already finalized |

---

#### `cancel_event(event_id: EventId, reason: str) -> Event`

Cancels an event before completion (admin operation).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_id` | `EventId` | The event to cancel | Must not be finalized |
| `reason` | `str` | Cancellation reason | Max 500 chars |

---

#### `update_event(event_id: EventId, updates: EventUpdate) -> Event`

Updates event details (admin operation, limited fields).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `event_id` | `EventId` | The event | Must exist, status-dependent restrictions |
| `updates` | `EventUpdate` | Fields to update | Valid update object |

---

#### `process_scheduled_events() -> ScheduledEventResult`

Background operation to activate/deactivate events based on schedule.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| (none) | - | Called by background worker | - |

---

### Outputs

#### `Event`

```python
@dataclass
class Event:
    """Complete event entity."""
    id: EventId
    name: str
    description: str
    event_type: EventType
    status: EventStatus
    scoring_type: ScoringType
    entry_requirements: EntryRequirements
    reward_tiers: list[RewardTier]
    rules: EventRules
    participant_count: int
    start_at: datetime
    end_at: datetime
    activated_at: datetime | None
    finalized_at: datetime | None
    created_at: datetime
    created_by: PlayerId | None  # Admin who created, None for system-generated
```

---

#### `EventSummary`

```python
@dataclass
class EventSummary:
    """Abbreviated event info for lists."""
    id: EventId
    name: str
    event_type: EventType
    status: EventStatus
    participant_count: int
    start_at: datetime
    end_at: datetime
    time_remaining_seconds: int | None  # None if not active
```

---

#### `EventParticipant`

```python
@dataclass
class EventParticipant:
    """A player's participation in an event."""
    event_id: EventId
    player_id: PlayerId
    player_username: str
    joined_at: datetime
    total_score: int
    matches_played: int
    best_match_score: int
    average_score: float
    current_rank: int | None  # None if not yet ranked
    rewards_claimed: bool
    last_match_at: datetime | None
```

---

#### `EventLeaderboard`

```python
@dataclass
class EventLeaderboard:
    """Event leaderboard with rankings."""
    event_id: EventId
    event_name: str
    event_status: EventStatus
    total_participants: int
    entries: list[LeaderboardEntry]
    updated_at: datetime
    has_more: bool
```

@dataclass
class LeaderboardEntry:
    """Single leaderboard entry."""
    rank: int
    player_id: PlayerId
    player_username: str
    score: int
    matches_played: int
    best_match_score: int
    reward_tier: str | None  # Which reward tier they qualify for
```

---

#### `PlayerEventRank`

```python
@dataclass
class PlayerEventRank:
    """A player's rank and status in an event."""
    event_id: EventId
    player_id: PlayerId
    rank: int
    total_participants: int
    percentile: float  # e.g., 95.5 means top 4.5%
    score: int
    matches_played: int
    reward_tier: str | None
    points_to_next_tier: int | None
```

---

#### `PlayerEventSummary`

```python
@dataclass
class PlayerEventSummary:
    """Summary of a player's participation in an event."""
    event_id: EventId
    event_name: str
    event_type: EventType
    event_status: EventStatus
    player_rank: int | None
    player_score: int
    matches_played: int
    reward_tier: str | None
    rewards_claimed: bool
    joined_at: datetime
```

---

#### `EventFinalizationResult`

```python
@dataclass
class EventFinalizationResult:
    """Result of finalizing an event."""
    event_id: EventId
    total_participants: int
    rewards_distributed: int
    reward_summary: dict[str, int]  # tier_name -> count
    top_players: list[LeaderboardEntry]  # Top 10
    finalized_at: datetime
```

---

### Error Cases

| Condition | Error Code | Error Type | Context Fields |
|-----------|------------|------------|----------------|
| Event not found | `NOT_FOUND_EVENT` | not_found | `event_id` |
| Player not found | `NOT_FOUND_PLAYER` | not_found | `player_id` |
| Event not active | `CONFLICT_EVENT_NOT_ACTIVE` | conflict | `event_id`, `current_status` |
| Event already finalized | `CONFLICT_EVENT_ALREADY_FINALIZED` | conflict | `event_id`, `finalized_at` |
| Player already joined | `CONFLICT_ALREADY_PARTICIPANT` | conflict | `event_id`, `player_id`, `joined_at` |
| Player not a participant | `FORBIDDEN_NOT_EVENT_PARTICIPANT` | forbidden | `event_id`, `player_id` |
| Entry requirements not met | `FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET` | forbidden | `event_id`, `player_id`, `missing_requirements` |
| Insufficient energy for entry | `FORBIDDEN_INSUFFICIENT_ENERGY` | forbidden | `required`, `available` |
| Event at capacity | `CONFLICT_EVENT_AT_CAPACITY` | conflict | `event_id`, `max_participants` |
| Cannot leave event | `FORBIDDEN_CANNOT_LEAVE_EVENT` | forbidden | `event_id`, `reason` |
| Invalid event dates | `VALIDATION_INVALID_INPUT` | validation | `field`, `reason` |
| Pagination limit out of range | `VALIDATION_INVALID_INPUT` | validation | `field="limit"`, `max=500` |

---

### Async Behavior

**This module is fully asynchronous.**

All public methods are `async def` because they involve:
- Database reads/writes via repositories
- Redis operations for real-time leaderboards
- Cross-module service calls to `vault_service`, `energy_service`, `player_service`, `match_service`

**Async operations:**
- `create_event` - DB write
- `get_event` - DB read
- `list_events` - DB read
- `get_active_events` - DB read + cache
- `join_event` - DB write + Redis leaderboard init + energy check/consume
- `leave_event` - DB write + Redis update
- `record_event_match` - DB write + Redis leaderboard update
- `get_leaderboard` - Redis read (real-time) or DB fallback
- `get_player_rank` - Redis read
- `get_player_events` - DB read
- `get_event_participant` - DB read
- `finalize_event` - DB write + reward distribution (vault, energy grants)
- `cancel_event` - DB write + optional refunds
- `update_event` - DB write
- `process_scheduled_events` - Batch DB updates + event activation/deactivation

**Error propagation:** All errors are raised through the injected `ErrorServiceProtocol`. Database/Redis errors are caught and wrapped in `INTERNAL_DATABASE_ERROR` or `INTERNAL_CACHE_ERROR`. Cross-module errors (`NOT_FOUND_PLAYER`, `FORBIDDEN_INSUFFICIENT_ENERGY`) propagate unchanged.

---

## Mandatory Service Usage

### Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `events.flash_duration_hours` | int | 4 | Default flash event duration |
| `events.weekly_duration_days` | int | 7 | Default weekly event duration |
| `events.seasonal_duration_days` | int | 28 | Default seasonal event duration |
| `events.entry_energy_cost` | int | 0 | Default energy cost to join (0 = free) |
| `events.match_energy_cost` | int | 1 | Energy per event match |
| `events.max_participants_flash` | int | 10000 | Max participants for flash events |
| `events.max_participants_weekly` | int | 50000 | Max participants for weekly events |
| `events.max_participants_seasonal` | int | 0 | 0 = unlimited |
| `events.leaderboard_cache_ttl_seconds` | int | 30 | Redis leaderboard cache TTL |
| `events.auto_finalize_delay_minutes` | int | 15 | Delay after end_at before auto-finalize |
| `events.min_matches_for_rewards` | int | 3 | Minimum matches to qualify for rewards |
| `events.allow_leave_after_match` | bool | false | Whether players can leave after playing |

---

### Logging Events

| Event | Severity | Trigger | Context |
|-------|----------|---------|---------|
| `event.created` | INFO | Event created | `event_id`, `event_type`, `start_at`, `end_at` |
| `event.activated` | INFO | Event starts (becomes active) | `event_id`, `participant_count` |
| `event.player_joined` | INFO | Player joins event | `event_id`, `player_id`, `participant_count` |
| `event.player_left` | INFO | Player leaves event | `event_id`, `player_id`, `reason` |
| `event.match_recorded` | DEBUG | Match score recorded | `event_id`, `player_id`, `match_id`, `score` |
| `event.leaderboard_updated` | DEBUG | Leaderboard position changed | `event_id`, `player_id`, `old_rank`, `new_rank` |
| `event.finalized` | INFO | Event ended, rewards distributed | `event_id`, `total_participants`, `rewards_distributed` |
| `event.cancelled` | WARN | Event cancelled | `event_id`, `reason`, `affected_participants` |
| `event.reward_granted` | INFO | Reward given to player | `event_id`, `player_id`, `reward_type`, `reward_value` |
| `event.entry_blocked` | WARN | Player blocked from joining | `event_id`, `player_id`, `reason` |
| `event.finalization_failed` | ERROR | Auto-finalization failed | `event_id`, `error` |
| `event.scheduled_activation` | INFO | Background job activated event | `event_id` |
| `event.scheduled_deactivation` | INFO | Background job deactivated event | `event_id` |

---

### Error Types Used

From the error taxonomy (Interface Agent guidance):

- `NOT_FOUND_EVENT` - Event ID doesn't exist
- `NOT_FOUND_PLAYER` - Player ID doesn't exist
- `VALIDATION_INVALID_INPUT` - Invalid parameters
- `FORBIDDEN_NOT_EVENT_PARTICIPANT` - Player not in event
- `FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET` - Entry requirements not met
- `FORBIDDEN_INSUFFICIENT_ENERGY` - Not enough hearts
- `FORBIDDEN_CANNOT_LEAVE_EVENT` - Leave not allowed
- `CONFLICT_EVENT_NOT_ACTIVE` - Event not currently active
- `CONFLICT_EVENT_ALREADY_FINALIZED` - Event already ended
- `CONFLICT_ALREADY_PARTICIPANT` - Already joined
- `CONFLICT_EVENT_AT_CAPACITY` - Max participants reached
- `INTERNAL_DATABASE_ERROR` - Database operation failed
- `INTERNAL_CACHE_ERROR` - Redis operation failed

All errors created through injected `ErrorServiceProtocol`, never bare raises.

---

## Data Access

### Owned Data

The events module owns these database tables:

#### `events` Table

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    event_type VARCHAR(20) NOT NULL,  -- 'flash', 'weekly', 'seasonal'
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',  -- 'scheduled', 'active', 'ended', 'finalized', 'cancelled'
    scoring_type VARCHAR(30) NOT NULL,  -- 'total_score', 'best_match', 'matches_played', 'average_score'

    entry_requirements JSONB NOT NULL DEFAULT '{}',
    reward_tiers JSONB NOT NULL DEFAULT '[]',
    rules JSONB NOT NULL DEFAULT '{}',

    max_participants INTEGER,  -- NULL = unlimited
    participant_count INTEGER NOT NULL DEFAULT 0,

    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    activated_at TIMESTAMPTZ,
    finalized_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES players(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT check_dates CHECK (end_at > start_at)
);

CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_start_at ON events(start_at) WHERE status = 'scheduled';
CREATE INDEX idx_events_end_at ON events(end_at) WHERE status = 'active';
```

#### `event_participants` Table

```sql
CREATE TABLE event_participants (
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES players(id),

    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    left_at TIMESTAMPTZ,  -- NULL if still participating

    total_score INTEGER NOT NULL DEFAULT 0,
    matches_played INTEGER NOT NULL DEFAULT 0,
    best_match_score INTEGER NOT NULL DEFAULT 0,

    current_rank INTEGER,  -- Cached from leaderboard
    rewards_claimed BOOLEAN NOT NULL DEFAULT false,
    reward_tier VARCHAR(50),  -- Which tier they earned

    last_match_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (event_id, player_id)
);

CREATE INDEX idx_event_participants_player ON event_participants(player_id);
CREATE INDEX idx_event_participants_score ON event_participants(event_id, total_score DESC);
CREATE INDEX idx_event_participants_active ON event_participants(event_id) WHERE left_at IS NULL;
```

#### `event_matches` Table

```sql
CREATE TABLE event_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES players(id),
    match_id UUID NOT NULL,  -- Reference to matches table

    score INTEGER NOT NULL,
    chain_count INTEGER NOT NULL DEFAULT 0,
    gems_cleared INTEGER NOT NULL DEFAULT 0,
    special_gems_activated INTEGER NOT NULL DEFAULT 0,

    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_event_match UNIQUE (event_id, player_id, match_id)
);

CREATE INDEX idx_event_matches_event ON event_matches(event_id);
CREATE INDEX idx_event_matches_player ON event_matches(event_id, player_id);
```

### Redis Data Structures

| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `chromacrush:event:{event_id}:leaderboard` | Sorted Set | None (persistent during event) | Real-time leaderboard scores |
| `chromacrush:event:{event_id}:participant_count` | String | 60s | Cached participant count |
| `chromacrush:event:active` | Set | None | Set of active event IDs |

```python
# Leaderboard operations
async def update_leaderboard(event_id: str, player_id: str, score: int):
    await self._redis.zadd(
        f"chromacrush:event:{event_id}:leaderboard",
        {player_id: score}
    )

async def get_rank(event_id: str, player_id: str) -> int | None:
    # 0-indexed rank, so add 1 for display
    rank = await self._redis.zrevrank(
        f"chromacrush:event:{event_id}:leaderboard",
        player_id
    )
    return rank + 1 if rank is not None else None

async def get_top_players(event_id: str, limit: int) -> list[tuple[str, float]]:
    return await self._redis.zrevrange(
        f"chromacrush:event:{event_id}:leaderboard",
        0, limit - 1,
        withscores=True
    )
```

---

### Repository Interfaces Required

```python
# src/data/protocols/event_repository.py
from typing import Protocol
from uuid import UUID
from datetime import datetime

from src.core.types.game import EventId, PlayerId


class EventRepository(Protocol):
    """Repository interface for event data."""

    async def create(self, data: "EventCreate") -> "EventRecord":
        """Create a new event."""
        ...

    async def find_by_id(self, event_id: UUID) -> "EventRecord | None":
        """Find event by ID."""
        ...

    async def update(self, event_id: UUID, changes: "EventUpdate") -> "EventRecord":
        """Update event fields."""
        ...

    async def find_by_status(
        self,
        status: str | None = None,
        event_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list["EventRecord"], int]:
        """Find events by status/type."""
        ...

    async def find_active(self) -> list["EventRecord"]:
        """Find all currently active events."""
        ...

    async def find_scheduled_to_start(self, before: datetime) -> list["EventRecord"]:
        """Find scheduled events that should start."""
        ...

    async def find_active_to_end(self, before: datetime) -> list["EventRecord"]:
        """Find active events that should end."""
        ...

    async def find_ended_to_finalize(self, before: datetime) -> list["EventRecord"]:
        """Find ended events ready for finalization."""
        ...

    async def increment_participant_count(self, event_id: UUID) -> int:
        """Atomically increment and return new count."""
        ...

    async def decrement_participant_count(self, event_id: UUID) -> int:
        """Atomically decrement and return new count."""
        ...


class EventParticipantRepository(Protocol):
    """Repository interface for event participants."""

    async def create(self, data: "ParticipantCreate") -> "ParticipantRecord":
        """Add participant to event."""
        ...

    async def find_by_event_and_player(
        self,
        event_id: UUID,
        player_id: UUID,
    ) -> "ParticipantRecord | None":
        """Find specific participant."""
        ...

    async def update(
        self,
        event_id: UUID,
        player_id: UUID,
        changes: "ParticipantUpdate",
    ) -> "ParticipantRecord":
        """Update participant record."""
        ...

    async def find_by_event(
        self,
        event_id: UUID,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list["ParticipantRecord"], int]:
        """Find participants in an event."""
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        include_past: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list["ParticipantRecord"], int]:
        """Find events a player is/was in."""
        ...

    async def find_ranked_by_event(
        self,
        event_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list["ParticipantRecord"]:
        """Find participants ordered by score (for DB fallback)."""
        ...

    async def count_by_event(self, event_id: UUID, active_only: bool = True) -> int:
        """Count participants in an event."""
        ...

    async def bulk_update_ranks(
        self,
        event_id: UUID,
        ranks: list[tuple[UUID, int]],  # (player_id, rank)
    ) -> int:
        """Bulk update ranks from leaderboard. Returns count updated."""
        ...

    async def find_eligible_for_rewards(
        self,
        event_id: UUID,
        min_matches: int,
    ) -> list["ParticipantRecord"]:
        """Find participants who qualify for rewards."""
        ...


class EventLeaderboardRepository(Protocol):
    """Repository interface for event leaderboards (Redis-backed)."""

    async def update_score(
        self,
        event_id: UUID,
        player_id: UUID,
        score: int,
    ) -> None:
        """Update player's score on leaderboard."""
        ...

    async def get_rank(
        self,
        event_id: UUID,
        player_id: UUID,
    ) -> int | None:
        """Get player's current rank (1-indexed)."""
        ...

    async def get_score(
        self,
        event_id: UUID,
        player_id: UUID,
    ) -> int | None:
        """Get player's current score."""
        ...

    async def get_top(
        self,
        event_id: UUID,
        limit: int,
        offset: int = 0,
    ) -> list[tuple[str, int]]:
        """Get top players: list of (player_id, score)."""
        ...

    async def get_total_count(self, event_id: UUID) -> int:
        """Get total number of ranked players."""
        ...

    async def get_percentile(
        self,
        event_id: UUID,
        player_id: UUID,
    ) -> float | None:
        """Get player's percentile (0-100, higher is better)."""
        ...

    async def remove_player(
        self,
        event_id: UUID,
        player_id: UUID,
    ) -> None:
        """Remove player from leaderboard."""
        ...

    async def clear_leaderboard(self, event_id: UUID) -> None:
        """Clear entire leaderboard (for cleanup)."""
        ...

    async def sync_to_database(
        self,
        event_id: UUID,
        participant_repo: EventParticipantRepository,
    ) -> int:
        """Sync leaderboard ranks to database. Returns count synced."""
        ...
```

---

### Data Read from Other Modules

| Data | Source Module | Access Method | Purpose |
|------|---------------|---------------|---------|
| Player entity | `player` | `PlayerServiceProtocol.get_player()` | Validate player exists, get username |
| Player level | `player` | `PlayerServiceProtocol.get_stats()` | Check level requirements |
| Energy balance | `energy` | `EnergyServiceProtocol.get_energy()`, `consume_heart()` | Entry/match energy costs |
| Match outcome | `match` | `MatchServiceProtocol.get_match_state()` | Verify match completion |
| Vault artifacts | `vault` | `VaultServiceProtocol.add_artifact()` | Grant artifact rewards |

---

### Transaction Requirements

| Operation | Transaction Scope | Notes |
|-----------|-------------------|-------|
| `create_event` | Single transaction | Insert event record |
| `join_event` | Single transaction | Insert participant + increment count + consume energy |
| `leave_event` | Single transaction | Update participant + decrement count |
| `record_event_match` | Single transaction + Redis | Update participant stats + update leaderboard |
| `finalize_event` | Single transaction | Update event + all participant rewards + vault/energy grants |
| `cancel_event` | Single transaction | Update event + optional refunds |
| Leaderboard sync | Single transaction | Bulk update ranks from Redis to DB |

**Critical: Atomic Join**

The `join_event` operation must be atomic to prevent:
1. Participant count exceeding max when capacity is limited
2. Energy consumed but participant record fails

Implementation uses `SELECT FOR UPDATE` on event row + atomic increment.

---

## Presentation Boundary

### Business Logic API Surface

The events module exposes domain objects and DTOs:
- Input: `EventId`, `PlayerId`, `MatchId`, `EventCreate`, `EventUpdate`, `MatchEventStats`
- Output: `Event`, `EventSummary`, `EventParticipant`, `EventLeaderboard`, `PlayerEventRank`, `EventFinalizationResult`

All types are defined in this module (`src/modules/events/types.py`) or imported from `src/core/types/`.

### Adapter Needs

Presentation adapters need to:
1. Convert `Event` to `EventResponse` (format dates, calculate time_remaining)
2. Convert `EventLeaderboard` to `LeaderboardResponse` (add player position if viewing player is included)
3. Format reward tiers for display (icons, descriptions)
4. Calculate countdown timers (seconds to start/end)
5. Determine if current player is eligible to join
6. Show "Your Rank" card separately from leaderboard

### What Does NOT Belong in This Module

- No JSON serialization (adapter responsibility)
- No HTTP response construction
- No terminal formatting
- No push notifications (separate notification system)
- No match creation logic (match module responsibility)
- No artifact definitions (vault module responsibility)
- No animation or visual timing data

---

## Internal Design

### State Machine

```
                 create_event()
                      |
                      v
               +-----------+
               | SCHEDULED |
               +-----------+
                      |
                      | start_at reached (background job)
                      v
                +--------+
                | ACTIVE |<-----+
                +--------+      |
                  |    |        | (event continues)
                  |    +--------+
                  |
                  | end_at reached (background job)
                  v
               +-------+
               | ENDED |
               +-------+
                  |
                  | finalize_event() (auto or manual)
                  v
             +-----------+
             | FINALIZED |
             +-----------+


Alternative paths:
- SCHEDULED -> CANCELLED (via cancel_event)
- ACTIVE -> CANCELLED (via cancel_event)
- ENDED -> CANCELLED (rare, admin override)
```

**Status definitions:**
- `SCHEDULED`: Created but not yet started
- `ACTIVE`: Currently running, players can join and play
- `ENDED`: Time expired, no more matches, awaiting finalization
- `FINALIZED`: Rewards distributed, leaderboard frozen
- `CANCELLED`: Event terminated early, no rewards

---

### Core Data Structures

```python
# src/modules/events/types.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from src.core.types.game import PlayerId, MatchId, ArtifactId


class EventType(Enum):
    FLASH = "flash"        # 2-4 hours
    WEEKLY = "weekly"      # ~7 days
    SEASONAL = "seasonal"  # 2-4 weeks


class EventStatus(Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ENDED = "ended"
    FINALIZED = "finalized"
    CANCELLED = "cancelled"


class ScoringType(Enum):
    TOTAL_SCORE = "total_score"      # Sum of all match scores
    BEST_MATCH = "best_match"        # Highest single match score
    MATCHES_PLAYED = "matches_played"  # Number of matches (participation)
    AVERAGE_SCORE = "average_score"  # Average score per match


@dataclass
class EntryRequirements:
    """Requirements to join an event."""
    min_level: int | None = None
    min_elo: int | None = None
    max_elo: int | None = None
    energy_cost: int = 0
    player_types: list[str] | None = None  # ['human', 'bot'] or subset


@dataclass
class RewardTier:
    """Reward tier definition."""
    tier_id: str              # e.g., "gold", "silver", "bronze", "participation"
    name: str                 # Display name
    description: str
    rank_min: int | None      # Min rank (1 = first place), None for percentile-based
    rank_max: int | None      # Max rank
    percentile_min: float | None  # Min percentile (0-100), e.g., 90 = top 10%
    percentile_max: float | None  # Max percentile
    rewards: list["RewardItem"]


@dataclass
class RewardItem:
    """Single reward within a tier."""
    reward_type: str  # "artifact", "energy", "elo_bonus", "cosmetic"
    value: str | int  # artifact_type_id, heart count, elo points, cosmetic_id
    quantity: int = 1


@dataclass
class EventRules:
    """Event-specific rules and settings."""
    max_matches_per_player: int | None = None  # None = unlimited
    match_cooldown_minutes: int = 0  # Time between matches
    scoring_multiplier: float = 1.0  # Score multiplier for event
    allowed_match_types: list[str] | None = None  # Match types allowed
    special_board_seed: int | None = None  # Fixed seed for fairness
    bonus_conditions: list["BonusCondition"] | None = None


@dataclass
class BonusCondition:
    """Bonus scoring condition."""
    condition_type: str  # "chain_length", "special_gems", "time_bonus"
    threshold: int
    bonus_points: int


@dataclass
class MatchEventStats:
    """Stats from a match for event scoring."""
    chain_count: int
    gems_cleared: int
    special_gems_activated: int
    match_duration_seconds: int


EventId = NewType("EventId", UUID)
```

---

### Algorithm: Join Event

```python
async def join_event(
    self,
    event_id: EventId,
    player_id: PlayerId,
) -> EventParticipant:
    # 1. Load and validate event
    event = await self._event_repo.find_by_id(event_id)
    if event is None:
        raise self._errors.not_found(
            "Event not found",
            code="NOT_FOUND_EVENT",
            event_id=str(event_id),
        )

    if event.status != EventStatus.ACTIVE.value:
        raise self._errors.conflict(
            "Event is not active",
            code="CONFLICT_EVENT_NOT_ACTIVE",
            event_id=str(event_id),
            current_status=event.status,
        )

    # 2. Check if already participating
    existing = await self._participant_repo.find_by_event_and_player(
        event_id, player_id
    )
    if existing is not None and existing.left_at is None:
        raise self._errors.conflict(
            "Already participating in event",
            code="CONFLICT_ALREADY_PARTICIPANT",
            event_id=str(event_id),
            player_id=str(player_id),
            joined_at=existing.joined_at.isoformat(),
        )

    # 3. Validate player exists and get info
    player = await self._player_service.get_player(player_id)

    # 4. Check entry requirements
    requirements = self._parse_requirements(event.entry_requirements)
    await self._check_entry_requirements(player, requirements)

    # 5. Check capacity
    if event.max_participants is not None:
        if event.participant_count >= event.max_participants:
            raise self._errors.conflict(
                "Event is at capacity",
                code="CONFLICT_EVENT_AT_CAPACITY",
                event_id=str(event_id),
                max_participants=event.max_participants,
            )

    # 6. Consume entry energy if required
    if requirements.energy_cost > 0:
        await self._energy_service.consume_heart(
            player_id,
            amount=requirements.energy_cost,
        )

    # 7. Create participant record (atomic with count increment)
    async with self._data_ctx.session() as session:
        # Atomic increment with capacity check
        new_count = await self._event_repo.increment_participant_count(event_id)

        if event.max_participants and new_count > event.max_participants:
            # Race condition - someone else took last spot
            await self._event_repo.decrement_participant_count(event_id)
            # Refund energy if consumed
            if requirements.energy_cost > 0:
                await self._energy_service.refund_heart(
                    player_id,
                    amount=requirements.energy_cost,
                    reason="event_full",
                )
            raise self._errors.conflict(
                "Event is at capacity",
                code="CONFLICT_EVENT_AT_CAPACITY",
                event_id=str(event_id),
                max_participants=event.max_participants,
            )

        participant = await self._participant_repo.create(ParticipantCreate(
            event_id=event_id,
            player_id=player_id,
        ))

    # 8. Initialize on leaderboard (with score 0)
    await self._leaderboard_repo.update_score(event_id, player_id, 0)

    # 9. Log and return
    self._logger.info(
        "Player joined event",
        event_id=str(event_id),
        player_id=str(player_id),
        participant_count=new_count,
    )

    return self._build_participant(participant, player, event)


async def _check_entry_requirements(
    self,
    player: Player,
    requirements: EntryRequirements,
) -> None:
    """Check if player meets entry requirements."""
    missing = []

    if requirements.min_level is not None:
        stats = await self._player_service.get_stats(player.id)
        # Derive level from total matches or other stat
        player_level = self._calculate_level(stats)
        if player_level < requirements.min_level:
            missing.append(f"level {requirements.min_level} required")

    if requirements.min_elo is not None:
        if player.elo_rating < requirements.min_elo:
            missing.append(f"ELO {requirements.min_elo} required")

    if requirements.max_elo is not None:
        if player.elo_rating > requirements.max_elo:
            missing.append(f"ELO below {requirements.max_elo} required")

    if requirements.player_types is not None:
        if player.player_type.value not in requirements.player_types:
            missing.append(f"player type must be {requirements.player_types}")

    if requirements.energy_cost > 0:
        energy_info = await self._energy_service.get_energy(player.id)
        if energy_info.current_hearts < requirements.energy_cost:
            raise self._errors.forbidden(
                "Insufficient energy for event entry",
                code="FORBIDDEN_INSUFFICIENT_ENERGY",
                required=requirements.energy_cost,
                available=energy_info.current_hearts,
            )

    if missing:
        raise self._errors.forbidden(
            "Entry requirements not met",
            code="FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET",
            event_id=str(requirements),
            player_id=str(player.id),
            missing_requirements=missing,
        )
```

---

### Algorithm: Record Event Match

```python
async def record_event_match(
    self,
    event_id: EventId,
    player_id: PlayerId,
    match_id: MatchId,
    score: int,
    match_stats: MatchEventStats,
) -> EventParticipant:
    # 1. Validate event and participant
    event = await self._event_repo.find_by_id(event_id)
    if event is None:
        raise self._errors.not_found("Event not found", event_id=str(event_id))

    if event.status != EventStatus.ACTIVE.value:
        raise self._errors.conflict(
            "Event is not active",
            code="CONFLICT_EVENT_NOT_ACTIVE",
            event_id=str(event_id),
            current_status=event.status,
        )

    participant = await self._participant_repo.find_by_event_and_player(
        event_id, player_id
    )
    if participant is None or participant.left_at is not None:
        raise self._errors.forbidden(
            "Not a participant in this event",
            code="FORBIDDEN_NOT_EVENT_PARTICIPANT",
            event_id=str(event_id),
            player_id=str(player_id),
        )

    # 2. Parse event rules
    rules = self._parse_rules(event.rules)

    # 3. Check match limits
    if rules.max_matches_per_player is not None:
        if participant.matches_played >= rules.max_matches_per_player:
            raise self._errors.conflict(
                "Maximum matches reached for this event",
                code="CONFLICT_MAX_MATCHES_REACHED",
                event_id=str(event_id),
                max_matches=rules.max_matches_per_player,
            )

    # 4. Apply scoring multiplier and bonus conditions
    event_score = int(score * rules.scoring_multiplier)

    if rules.bonus_conditions:
        for bonus in rules.bonus_conditions:
            if self._check_bonus_condition(bonus, match_stats):
                event_score += bonus.bonus_points

    # 5. Calculate new totals based on scoring type
    scoring_type = ScoringType(event.scoring_type)
    new_total = self._calculate_new_score(
        scoring_type,
        participant.total_score,
        participant.matches_played,
        event_score,
    )

    # 6. Update participant record
    async with self._data_ctx.session() as session:
        updated = await self._participant_repo.update(
            event_id,
            player_id,
            ParticipantUpdate(
                total_score=new_total,
                matches_played=participant.matches_played + 1,
                best_match_score=max(participant.best_match_score, event_score),
                last_match_at=datetime.utcnow(),
            ),
        )

        # Record the match entry
        await self._match_repo.create(EventMatchCreate(
            event_id=event_id,
            player_id=player_id,
            match_id=match_id,
            score=event_score,
            chain_count=match_stats.chain_count,
            gems_cleared=match_stats.gems_cleared,
            special_gems_activated=match_stats.special_gems_activated,
        ))

    # 7. Update leaderboard
    await self._leaderboard_repo.update_score(event_id, player_id, new_total)

    # 8. Get new rank
    new_rank = await self._leaderboard_repo.get_rank(event_id, player_id)

    if participant.current_rank != new_rank:
        self._logger.debug(
            "Leaderboard position changed",
            event_id=str(event_id),
            player_id=str(player_id),
            old_rank=participant.current_rank,
            new_rank=new_rank,
        )

    self._logger.debug(
        "Match recorded",
        event_id=str(event_id),
        player_id=str(player_id),
        match_id=str(match_id),
        score=event_score,
    )

    player = await self._player_service.get_player(player_id)
    return self._build_participant(updated, player, event, rank=new_rank)


def _calculate_new_score(
    self,
    scoring_type: ScoringType,
    current_total: int,
    matches_played: int,
    new_score: int,
) -> int:
    """Calculate new total based on scoring type."""
    if scoring_type == ScoringType.TOTAL_SCORE:
        return current_total + new_score
    elif scoring_type == ScoringType.BEST_MATCH:
        return max(current_total, new_score)
    elif scoring_type == ScoringType.MATCHES_PLAYED:
        return matches_played + 1
    elif scoring_type == ScoringType.AVERAGE_SCORE:
        # Store total, calculate average on display
        return current_total + new_score
    else:
        return current_total + new_score
```

---

### Algorithm: Finalize Event

```python
async def finalize_event(
    self,
    event_id: EventId,
) -> EventFinalizationResult:
    # 1. Load and validate event
    event = await self._event_repo.find_by_id(event_id)
    if event is None:
        raise self._errors.not_found("Event not found", event_id=str(event_id))

    if event.status == EventStatus.FINALIZED.value:
        raise self._errors.conflict(
            "Event already finalized",
            code="CONFLICT_EVENT_ALREADY_FINALIZED",
            event_id=str(event_id),
            finalized_at=event.finalized_at.isoformat(),
        )

    if event.status not in (EventStatus.ENDED.value, EventStatus.ACTIVE.value):
        raise self._errors.conflict(
            "Event cannot be finalized",
            code="CONFLICT_EVENT_NOT_ACTIVE",
            event_id=str(event_id),
            current_status=event.status,
        )

    # 2. Sync leaderboard to database
    await self._leaderboard_repo.sync_to_database(
        event_id,
        self._participant_repo,
    )

    # 3. Get eligible participants (met minimum matches)
    min_matches = self._config.get("events.min_matches_for_rewards", 3)
    eligible = await self._participant_repo.find_eligible_for_rewards(
        event_id,
        min_matches,
    )

    # 4. Parse reward tiers
    reward_tiers = self._parse_reward_tiers(event.reward_tiers)
    total_participants = len(eligible)

    # 5. Assign reward tiers to participants
    reward_summary: dict[str, int] = {}
    rewards_distributed = 0

    async with self._data_ctx.session() as session:
        for participant in eligible:
            tier = self._determine_reward_tier(
                participant.current_rank,
                total_participants,
                reward_tiers,
            )

            if tier is not None:
                # Grant rewards
                for reward in tier.rewards:
                    await self._grant_reward(
                        participant.player_id,
                        reward,
                        event_id,
                    )
                    rewards_distributed += 1

                # Update participant
                await self._participant_repo.update(
                    event_id,
                    participant.player_id,
                    ParticipantUpdate(
                        rewards_claimed=True,
                        reward_tier=tier.tier_id,
                    ),
                )

                reward_summary[tier.tier_id] = reward_summary.get(tier.tier_id, 0) + 1

                self._logger.info(
                    "Reward granted",
                    event_id=str(event_id),
                    player_id=str(participant.player_id),
                    reward_tier=tier.tier_id,
                )

        # 6. Update event status
        await self._event_repo.update(
            event_id,
            EventDbUpdate(
                status=EventStatus.FINALIZED.value,
                finalized_at=datetime.utcnow(),
            ),
        )

    # 7. Get top players for result
    top_entries = await self._leaderboard_repo.get_top(event_id, 10)
    top_players = []
    for player_id_str, score in top_entries:
        player = await self._player_service.get_player(PlayerId(UUID(player_id_str)))
        participant = await self._participant_repo.find_by_event_and_player(
            event_id, PlayerId(UUID(player_id_str))
        )
        top_players.append(LeaderboardEntry(
            rank=top_players.__len__() + 1,
            player_id=PlayerId(UUID(player_id_str)),
            player_username=player.username,
            score=int(score),
            matches_played=participant.matches_played,
            best_match_score=participant.best_match_score,
            reward_tier=participant.reward_tier,
        ))

    self._logger.info(
        "Event finalized",
        event_id=str(event_id),
        total_participants=total_participants,
        rewards_distributed=rewards_distributed,
    )

    return EventFinalizationResult(
        event_id=event_id,
        total_participants=total_participants,
        rewards_distributed=rewards_distributed,
        reward_summary=reward_summary,
        top_players=top_players,
        finalized_at=datetime.utcnow(),
    )


async def _grant_reward(
    self,
    player_id: PlayerId,
    reward: RewardItem,
    event_id: EventId,
) -> None:
    """Grant a single reward to a player."""
    if reward.reward_type == "artifact":
        for _ in range(reward.quantity):
            await self._vault_service.add_artifact(
                player_id=player_id,
                artifact_type_id=str(reward.value),
                source="event_reward",
                source_id=str(event_id),
            )
    elif reward.reward_type == "energy":
        await self._energy_service.grant_bonus_hearts(
            player_id=player_id,
            amount=int(reward.value) * reward.quantity,
            source=BonusSource.EVENT_REWARD,
            idempotency_key=f"event:{event_id}:player:{player_id}:energy",
        )
    elif reward.reward_type == "elo_bonus":
        current_elo = await self._player_service.get_elo(player_id)
        await self._player_service.update_elo(
            player_id,
            current_elo + int(reward.value),
        )
    # Other reward types handled similarly


def _determine_reward_tier(
    self,
    rank: int | None,
    total_participants: int,
    tiers: list[RewardTier],
) -> RewardTier | None:
    """Determine which reward tier a participant qualifies for."""
    if rank is None:
        return None

    percentile = ((total_participants - rank + 1) / total_participants) * 100

    for tier in tiers:
        # Check rank-based criteria
        if tier.rank_min is not None and tier.rank_max is not None:
            if tier.rank_min <= rank <= tier.rank_max:
                return tier
        # Check percentile-based criteria
        elif tier.percentile_min is not None and tier.percentile_max is not None:
            if tier.percentile_min <= percentile <= tier.percentile_max:
                return tier
        # Check rank minimum only
        elif tier.rank_min is not None and tier.rank_max is None:
            if rank >= tier.rank_min:
                return tier
        # Check percentile minimum only
        elif tier.percentile_min is not None and tier.percentile_max is None:
            if percentile >= tier.percentile_min:
                return tier

    return None
```

---

### Background Job: Scheduled Event Processing

```python
async def process_scheduled_events(self) -> ScheduledEventResult:
    """
    Background job to activate/deactivate events based on schedule.
    Called periodically (e.g., every minute) by arq worker.
    """
    now = datetime.utcnow()
    activated = []
    deactivated = []
    finalized = []

    # 1. Activate scheduled events that should start
    to_activate = await self._event_repo.find_scheduled_to_start(before=now)
    for event in to_activate:
        try:
            await self._event_repo.update(
                event.id,
                EventDbUpdate(
                    status=EventStatus.ACTIVE.value,
                    activated_at=now,
                ),
            )
            # Add to active set in Redis
            await self._redis.sadd("chromacrush:event:active", str(event.id))
            activated.append(event.id)

            self._logger.info(
                "Scheduled event activated",
                event_id=str(event.id),
            )
        except Exception as e:
            self._logger.error(
                "Failed to activate event",
                event_id=str(event.id),
                error=str(e),
            )

    # 2. Deactivate active events that should end
    to_deactivate = await self._event_repo.find_active_to_end(before=now)
    for event in to_deactivate:
        try:
            await self._event_repo.update(
                event.id,
                EventDbUpdate(status=EventStatus.ENDED.value),
            )
            # Remove from active set
            await self._redis.srem("chromacrush:event:active", str(event.id))
            deactivated.append(event.id)

            self._logger.info(
                "Scheduled event ended",
                event_id=str(event.id),
            )
        except Exception as e:
            self._logger.error(
                "Failed to end event",
                event_id=str(event.id),
                error=str(e),
            )

    # 3. Auto-finalize ended events after delay
    finalize_delay = self._config.get("events.auto_finalize_delay_minutes", 15)
    finalize_cutoff = now - timedelta(minutes=finalize_delay)
    to_finalize = await self._event_repo.find_ended_to_finalize(before=finalize_cutoff)

    for event in to_finalize:
        try:
            await self.finalize_event(EventId(event.id))
            finalized.append(event.id)
        except Exception as e:
            self._logger.error(
                "Finalization failed",
                event_id=str(event.id),
                error=str(e),
            )

    return ScheduledEventResult(
        activated=activated,
        deactivated=deactivated,
        finalized=finalized,
        processed_at=now,
    )
```

---

## CLI Surface

### Commands

```bash
# Event management (admin)
chromacrush events create --name "Flash Challenge" --type flash --start "2026-02-06T10:00:00Z" --end "2026-02-06T14:00:00Z"
chromacrush events update <event-id> --name "New Name"
chromacrush events cancel <event-id> --reason "Technical issues"
chromacrush events finalize <event-id>

# Event queries
chromacrush events get <event-id>
chromacrush events list [--status active|scheduled|ended] [--type flash|weekly|seasonal]
chromacrush events active

# Participation
chromacrush events join <event-id> --player <player-id>
chromacrush events leave <event-id> --player <player-id>
chromacrush events record-match <event-id> --player <player-id> --match <match-id> --score 1500

# Leaderboards
chromacrush events leaderboard <event-id> [--limit 100]
chromacrush events rank <event-id> --player <player-id>
chromacrush events player-events <player-id> [--include-past]

# Background operations
chromacrush events process-scheduled
```

### Example Invocations

```bash
$ chromacrush events create --name "Weekend Flash" --type flash \
    --start "2026-02-06T18:00:00Z" --end "2026-02-06T22:00:00Z"
Event created!
  ID: 550e8400-e29b-41d4-a716-446655440001
  Name: Weekend Flash
  Type: flash
  Status: scheduled
  Starts: 2026-02-06 18:00:00 UTC
  Ends: 2026-02-06 22:00:00 UTC

$ chromacrush events join 550e8400 --player abc123
Joined event!
  Event: Weekend Flash
  Player: alice
  Rank: 1 (first participant!)

$ chromacrush events record-match 550e8400 --player abc123 --match def456 --score 2500
Match recorded!
  Score: 2500
  Total Score: 2500
  New Rank: 1

$ chromacrush events leaderboard 550e8400 --limit 10
Leaderboard: Weekend Flash
  Status: active
  Participants: 127

  Rank  Player      Score    Matches
  ----  ------      -----    -------
  1     alice       8500     4
  2     bob_bot     7200     5
  3     charlie     6800     3
  ...

$ chromacrush events rank 550e8400 --player abc123
Your Rank in Weekend Flash:
  Rank: 1 / 127
  Percentile: Top 1%
  Score: 8500
  Matches: 4
  Reward Tier: Gold (Top 10)
  Points to Silver: N/A (you're in Gold!)

$ chromacrush events finalize 550e8400
Event finalized!
  Total Participants: 127
  Rewards Distributed: 95
  Summary:
    Gold: 10
    Silver: 15
    Bronze: 30
    Participation: 40
  Top 3:
    1. alice (8500)
    2. bob_bot (7200)
    3. charlie (6800)
```

---

## Edge Cases & Decisions

### EC-1: Concurrent Joins at Capacity

**Scenario:** Event has 1 spot remaining. Two players try to join simultaneously.

**Decision:** Use atomic increment with capacity check. First to increment wins. Second sees over-capacity, decrements back, and gets `CONFLICT_EVENT_AT_CAPACITY`. If energy was consumed, it's refunded.

**Rationale:** Database-level atomicity prevents double-booking.

---

### EC-2: Event Ends While Match in Progress

**Scenario:** Player is mid-match when event end_at is reached.

**Decision:** Match continues and is recorded when completed, even if recorded_at > end_at. We allow a grace period (configurable, default 30 minutes) for in-progress matches.

**Rationale:** Harsh cutoff would be frustrating. Grace period maintains player trust.

---

### EC-3: Leaderboard Tie Breaking

**Scenario:** Two players have identical scores.

**Decision:** Secondary sort by `last_match_at` (earlier is better - reached score first). Tertiary by `joined_at` (earlier is better). Redis ZADD handles this via lexicographic tie-breaking on member IDs if scores are equal; we add timestamp prefixes.

**Rationale:** Rewards faster players. Standard competitive game practice.

---

### EC-4: Player Leaves and Rejoins

**Scenario:** Player leaves an event then wants to rejoin.

**Decision:** If `allow_leave_after_match=false` (default), players cannot leave events they've played matches in. If they leave before playing, they can rejoin but lose their previous participation record (fresh start).

**Rationale:** Prevents gaming the system by leaving when losing and rejoining later.

---

### EC-5: Reward Distribution Failure

**Scenario:** Finalization succeeds for 99 players but fails on the 100th (vault service error).

**Decision:** Finalization is atomic. On any failure, entire finalization rolls back. Admin must retry. Partial rewards are never granted.

**Rationale:** Consistency over availability. Partial reward distribution causes support nightmares.

---

### EC-6: Zero Participants at Finalization

**Scenario:** Event ends with no participants or no one met minimum matches.

**Decision:** Event still finalizes with status=FINALIZED. No rewards distributed. Log as successful with zero rewards.

**Rationale:** Clean state transition. Event lifecycle completes normally.

---

### EC-7: Scoring Type: Average Score

**Scenario:** Event uses `AVERAGE_SCORE` scoring. Player has 5 matches, plays a bad 6th.

**Decision:** Store total_score in database. Calculate average on display as total_score / matches_played. Leaderboard stores total (for tie-breaking consistency). Display shows average.

**Rationale:** Simpler storage. Average calculated at read time.

---

### EC-8: Event Cancelled With Participants

**Scenario:** Event cancelled while 50 players have already joined.

**Decision:** If energy was consumed for entry, all participants get refunds. Leaderboard is cleared. Event status becomes CANCELLED. No rewards distributed.

**Rationale:** Fair to players. Cancellation is exceptional.

---

### EC-9: Player Deleted During Active Event

**Scenario:** Player is participating in event, then soft-deleted.

**Decision:** Participation record remains. Leaderboard entry remains (frozen). Player cannot play more matches. At finalization, rewards are skipped for deleted players.

**Rationale:** Preserves event integrity. Rewards for deleted accounts have nowhere to go.

---

### EC-10: Redis Leaderboard Out of Sync

**Scenario:** Redis restarts during event. Leaderboard data lost.

**Decision:**
1. On any leaderboard read that finds empty Redis, rebuild from `event_participants` table.
2. Before finalization, always sync Redis -> DB via `sync_to_database()`.
3. Background job periodically syncs active leaderboards to DB (every 5 minutes).

**Rationale:** Database is source of truth. Redis is performance cache.

---

## Open Questions

None. All design decisions have been resolved based on:
- Feasibility report specifications
- Interface contracts guidance
- Data layer guidance
- Dependency module artifacts (vault, energy, match, player)
- GDD requirements for events system

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent (events) |
