# Module Architecture Report: events

**Module:** events
**Build Wave:** 6
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The events module manages time-limited competitive events for ChromaCrush, handling the full event lifecycle: creation, activation, player participation with entry requirements and energy costs, match recording with configurable scoring types, real-time leaderboards via Redis sorted sets, event finalization with tiered reward distribution (artifacts, energy, ELO bonuses), and cancellation with energy refunds. Three event types are supported: flash (hours), weekly (days), and seasonal (weeks). All 15 public service methods are **asynchronous** (`async def`) because they involve database operations, Redis leaderboard updates, and cross-module coordination with player, energy, vault, and match services. The service enforces capacity limits with atomic increment/rollback, configurable scoring (total, best-match, matches-played, average), bonus conditions, and minimum match thresholds for reward eligibility.

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_event` | `(event_data: EventCreate) -> Event` | Create new event (admin) |
| `get_event` | `(event_id) -> Event` | Retrieve event details |
| `list_events` | `(status?, event_type?, limit?, offset?) -> PaginatedResult[EventSummary]` | List events with filters |
| `get_active_events` | `() -> list[Event]` | Get all currently active events |
| `join_event` | `(event_id, player_id) -> EventParticipant` | Register player, check requirements, consume energy |
| `leave_event` | `(event_id, player_id) -> None` | Withdraw player, clean up leaderboard |
| `record_event_match` | `(event_id, player_id, match_id, score, match_stats) -> EventParticipant` | Record match, apply scoring, update leaderboard |
| `get_leaderboard` | `(event_id, limit?, offset?) -> EventLeaderboard` | Get leaderboard (Redis primary, DB fallback) |
| `get_player_rank` | `(event_id, player_id) -> PlayerEventRank` | Get player's rank, percentile, tier |
| `get_player_events` | `(player_id, include_past?, limit?, offset?) -> PaginatedResult[PlayerEventSummary]` | Get events for a player |
| `get_event_participant` | `(event_id, player_id) -> EventParticipant` | Get participant record |
| `finalize_event` | `(event_id) -> EventFinalizationResult` | Sync leaderboard, distribute rewards, set finalized |
| `cancel_event` | `(event_id, reason) -> Event` | Cancel event, refund energy, clear leaderboard |
| `update_event` | `(event_id, updates: EventUpdate) -> Event` | Update event details (admin) |
| `process_scheduled_events` | `() -> ScheduledEventResult` | Activate/deactivate/finalize based on schedule |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Event configuration (durations, costs, capacity limits) |
| `logger` | `LoggerProtocol` | Structured diagnostic logging |
| `errors` | `ErrorServiceProtocol` | Create typed errors |
| `data_ctx` | `Any` | Session management and Redis access via `data_ctx.redis` |
| `vault_service` | `VaultServiceProtocol` | Grant artifact rewards via `add_artifact` |
| `energy_service` | `EnergyServiceProtocol` | Energy checks, consumption, grants, and refunds |
| `match_service` | `MatchServiceProtocol` | Match verification via `get_match` |
| `player_service` | `PlayerServiceProtocol` | Player lookup, stats, ELO updates |
| `event_repository` | `EventRepositoryProtocol` | Event lifecycle persistence |
| `event_participant_repository` | `EventParticipantRepositoryProtocol` | Participation tracking and match recording |
| `event_leaderboard_repository` | `EventLeaderboardRepositoryProtocol` | Redis sorted set leaderboard operations |

---

## 4. Data Owned

| Store | Description |
|-------|-------------|
| `events` table | Event lifecycle records (type, status, rules, schedule, capacity) |
| `event_participants` table | Participation tracking (composite PK, scores, match counts, rank) |
| `event_matches` table | Individual match records within events (unique per event+match+player) |
| `chromacrush:event:{event_id}:leaderboard` | Redis sorted set per event for real-time ranking |
| `chromacrush:event:active` | Redis set of active event IDs |

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `events.flash_duration_hours` | int | 4 | Flash event duration |
| `events.weekly_duration_days` | int | 7 | Weekly event duration |
| `events.seasonal_duration_days` | int | 30 | Seasonal event duration |
| `events.entry_energy_cost` | int | 1 | Energy to join event |
| `events.match_energy_cost` | int | 1 | Energy per event match |
| `events.max_participants_flash` | int | 100 | Flash event player cap |
| `events.max_participants_weekly` | int | 1000 | Weekly event player cap |
| `events.max_participants_seasonal` | int | 10000 | Seasonal event player cap |
| `events.leaderboard_cache_ttl_seconds` | int | 60 | Redis leaderboard cache TTL |
| `events.auto_finalize_delay_minutes` | int | 15 | Delay before auto-finalization |
| `events.min_matches_for_rewards` | int | 3 | Min matches to earn rewards |
| `events.allow_leave_after_match` | bool | false | Allow leaving after playing |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_INVALID_INPUT` | 400 | Name too short/long, bad dates, invalid limit |
| `NOT_FOUND_EVENT` | 404 | Event ID does not exist |
| `NOT_FOUND_PLAYER` | 404 | Player does not exist (via player_service) |
| `FORBIDDEN_NOT_EVENT_PARTICIPANT` | 403 | Player not in event |
| `FORBIDDEN_CANNOT_LEAVE_EVENT` | 403 | Leave after match when not allowed |
| `FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET` | 403 | Entry requirements (level, ELO, player type) not met |
| `FORBIDDEN_INSUFFICIENT_ENERGY` | 403 | Not enough energy for entry |
| `CONFLICT_EVENT_NOT_ACTIVE` | 409 | Event not in required status |
| `CONFLICT_ALREADY_PARTICIPANT` | 409 | Already joined event |
| `CONFLICT_EVENT_AT_CAPACITY` | 409 | Max participants reached |
| `CONFLICT_EVENT_ALREADY_FINALIZED` | 409 | Event already finalized |

---

## 7. Cross-Module Interactions

**Called by:**
- `ads` -- event-triggered ad opportunities reference event data
- `api` -- exposes event endpoints

**Calls:**
- `vault` -- grants artifacts as event rewards
- `energy` -- energy checks, consumption, grants, and refunds
- `match` -- match verification
- `player` -- player lookup, stats, ELO updates

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `EventType` | `src/modules/events/types.py` | Enum: FLASH, WEEKLY, SEASONAL |
| `EventStatus` | `src/modules/events/types.py` | Enum: SCHEDULED, ACTIVE, ENDED, FINALIZED, CANCELLED |
| `ScoringType` | `src/modules/events/types.py` | Enum: TOTAL_SCORE, BEST_MATCH, MATCHES_PLAYED, AVERAGE_SCORE |
| `Event` | `src/modules/events/types.py` | Full event entity with rules, schedule, and capacity |
| `EventParticipant` | `src/modules/events/types.py` | Player participation record with scores and match count |
| `EventLeaderboard` | `src/modules/events/types.py` | Ranked leaderboard with entries and metadata |
| `EventFinalizationResult` | `src/modules/events/types.py` | Result of event finalization with reward distribution |
| `ScheduledEventResult` | `src/modules/events/types.py` | Result of processing scheduled event transitions |
