# Events Module Implementation Document

**Module:** events
**Phase:** 2.2
**Author:** Coding Agent
**Date:** 2026-02-06

---

## 1. Summary

The events module manages time-limited competitive events, leaderboards, participant tracking, and reward distribution for ChromaCrush. It handles the full event lifecycle: creation, activation, player participation, match recording with scoring, real-time leaderboards (via Redis sorted sets), event finalization with reward distribution, and cancellation with energy refunds. All public methods are async (`async def`) because they involve database operations, Redis leaderboard updates, and cross-module coordination (player lookups, energy management, vault artifact grants). The service enforces entry requirements (level, ELO, energy, player type), capacity limits with atomic increment/rollback, configurable scoring types (total, best-match, matches-played, average), bonus conditions, and minimum match thresholds for reward eligibility.

## 2. Files Created

### Module Code (`src/modules/events/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Exports `EventService`, `EventServiceProtocol`, and all domain types/DTOs |
| `types.py` | Domain types: `EventType`, `EventStatus`, `ScoringType` enums; `EntryRequirements`, `RewardItem`, `RewardTier`, `BonusCondition`, `EventRules`, `MatchEventStats`, `Event`, `EventSummary`, `EventParticipant`, `LeaderboardEntry`, `EventLeaderboard`, `PlayerEventRank`, `PlayerEventSummary`, `EventFinalizationResult`, `ScheduledEventResult` dataclasses |
| `protocols.py` | `EventServiceProtocol` (15 methods), `EventRepositoryProtocol` (10 methods), `EventParticipantRepositoryProtocol` (10 methods), `EventLeaderboardRepositoryProtocol` (9 methods), plus minimal dependency protocols (`MatchServiceProtocol`, `PlayerServiceProtocol`, `EnergyServiceProtocol`, `VaultServiceProtocol`) |
| `dto.py` | DTOs for repository operations: `EventCreate`, `EventUpdate`, `EventDbUpdate`, `ParticipantCreate`, `ParticipantUpdate`, `EventMatchCreate`, `PaginatedResult[T]` |
| `service.py` | `EventService` -- full implementation (~1237 lines) |

### Data Layer (`src/data/`)
| File | Purpose |
|------|---------|
| `models/event.py` | `EventModel(Base, UUIDMixin, TimestampMixin)` ORM -- events table |
| `models/event_participant.py` | `EventParticipantModel(Base)` ORM -- event_participants table (composite PK, no UUIDMixin) |
| `models/event_match.py` | `EventMatchRecordModel(Base, UUIDMixin)` ORM -- event_matches table with unique constraint |
| `protocols/event_repository.py` | `EventRepositoryProtocol` data layer protocol |
| `protocols/event_participant_repository.py` | `EventParticipantRepositoryProtocol` data layer protocol |
| `protocols/event_leaderboard_repository.py` | `EventLeaderboardRepositoryProtocol` data layer protocol |
| `repositories/event_repository.py` | `SQLAlchemyEventRepository` with CRUD, status queries, partial index queries, atomic count increment/decrement |
| `repositories/event_participant_repository.py` | `SQLAlchemyEventParticipantRepository` with CRUD, ranking queries, bulk rank updates, eligibility queries, event match creation |
| `repositories/event_leaderboard_repository.py` | `RedisEventLeaderboardRepository` using sorted sets (ZADD, ZREVRANK, ZREVRANGE, ZSCORE, ZCARD, ZREM) with DB sync |
| `migrations/versions/006_event_tables.py` | Alembic migration for events, event_participants, event_matches tables with partial indexes |

### CLI (`src/cli/commands/`)
| File | Purpose |
|------|---------|
| `events_commands.py` | Click group "events" with 14 commands |

### Tests (`tests/unit/modules/events/`)
| File | Purpose |
|------|---------|
| `test_event_service.py` | 85 tests across 16 test classes covering all 15 public methods and error paths |

## 3. Deviations from Artifact

| Area | Artifact Spec | Implementation | Justification |
|------|--------------|----------------|---------------|
| `redis_ctx` dep | Separate `redis_ctx` dependency | Uses `data_ctx.redis` property | Per orchestrator guidance: "redis_ctx simplification -- The artifact describes a separate redis_ctx dependency; however, the codebase uses data_ctx.redis." Service constructor takes 11 deps (not 12). |
| `_calculate_points_to_next_tier` | Calculate exact points needed | Returns `None` (simplified) | Exact calculation would require knowing the score of the player at the rank boundary, which requires an additional leaderboard query per call. Simplified to `None`; can be enhanced in future iteration. |
| Finalize event status check | Artifact says "ended or active" | Implementation allows both `ended` and `active` | This matches the artifact's intent -- allows force-finalizing an active event (admin operation). |

## 4. Public Interface

### `EventService`

```python
def __init__(
    self,
    config: ConfigProtocol,
    logger: LoggerProtocol,
    errors: ErrorServiceProtocol,
    data_ctx: Any,
    vault_service: VaultServiceProtocol,
    energy_service: EnergyServiceProtocol,
    match_service: MatchServiceProtocol,
    player_service: PlayerServiceProtocol,
    event_repository: EventRepositoryProtocol,
    event_participant_repository: EventParticipantRepositoryProtocol,
    event_leaderboard_repository: EventLeaderboardRepositoryProtocol,
) -> None
```

#### Service Methods

| Method | Signature | Return Type | Purpose |
|--------|-----------|-------------|---------|
| `create_event` | `(event_data: EventCreate)` | `Event` | Create new event (admin) |
| `get_event` | `(event_id: EventId)` | `Event` | Retrieve event details |
| `list_events` | `(status?, event_type?, limit=20, offset=0)` | `PaginatedResult[EventSummary]` | List events with filters |
| `get_active_events` | `()` | `list[Event]` | Get all active events |
| `join_event` | `(event_id, player_id)` | `EventParticipant` | Register player, check requirements, consume energy |
| `leave_event` | `(event_id, player_id)` | `None` | Withdraw player, clean up leaderboard |
| `record_event_match` | `(event_id, player_id, match_id, score, match_stats)` | `EventParticipant` | Record match, apply scoring, update leaderboard |
| `get_leaderboard` | `(event_id, limit=100, offset=0)` | `EventLeaderboard` | Get leaderboard (Redis primary, DB fallback) |
| `get_player_rank` | `(event_id, player_id)` | `PlayerEventRank` | Get player's rank, percentile, tier |
| `get_player_events` | `(player_id, include_past=False, limit=20, offset=0)` | `PaginatedResult[PlayerEventSummary]` | Get events for player |
| `get_event_participant` | `(event_id, player_id)` | `EventParticipant` | Get participant record |
| `finalize_event` | `(event_id)` | `EventFinalizationResult` | Sync leaderboard, distribute rewards, set status |
| `cancel_event` | `(event_id, reason)` | `Event` | Cancel event, refund energy, clear leaderboard |
| `update_event` | `(event_id, updates: EventUpdate)` | `Event` | Update event details (admin) |
| `process_scheduled_events` | `()` | `ScheduledEventResult` | Activate/deactivate/finalize based on schedule |

## 5. Error Codes

| Code | HTTP | Condition |
|------|------|-----------|
| `VALIDATION_INVALID_INPUT` | 400 | Name too short/long, bad dates, invalid limit |
| `NOT_FOUND_EVENT` | 404 | Event ID does not exist |
| `FORBIDDEN_NOT_EVENT_PARTICIPANT` | 403 | Player not in event |
| `FORBIDDEN_CANNOT_LEAVE_EVENT` | 403 | Leave after match when not allowed |
| `FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET` | 403 | Entry requirements (level, ELO, player type) not met |
| `FORBIDDEN_INSUFFICIENT_ENERGY` | 403 | Not enough energy for entry |
| `CONFLICT_EVENT_NOT_ACTIVE` | 409 | Event not in required status |
| `CONFLICT_ALREADY_PARTICIPANT` | 409 | Already joined |
| `CONFLICT_EVENT_AT_CAPACITY` | 409 | Max participants reached |
| `CONFLICT_EVENT_ALREADY_FINALIZED` | 409 | Event already finalized |

## 6. Configuration Keys

| Key | Default | Purpose |
|-----|---------|---------|
| `events.flash_duration_hours` | 4 | Flash event duration |
| `events.weekly_duration_days` | 7 | Weekly event duration |
| `events.seasonal_duration_days` | 28 | Seasonal event duration |
| `events.entry_energy_cost` | 0 | Default entry energy cost |
| `events.match_energy_cost` | 1 | Energy cost per event match |
| `events.max_participants_flash` | 10000 | Flash event max capacity |
| `events.max_participants_weekly` | 50000 | Weekly event max capacity |
| `events.max_participants_seasonal` | 0 | Seasonal max (0 = unlimited) |
| `events.leaderboard_cache_ttl_seconds` | 30 | Leaderboard cache TTL |
| `events.auto_finalize_delay_minutes` | 15 | Delay before auto-finalization |
| `events.min_matches_for_rewards` | 3 | Min matches for reward eligibility |
| `events.allow_leave_after_match` | False | Whether players can leave after playing |

## 7. Data Access Patterns

### Owned Data
- `events` table -- event lifecycle records
- `event_participants` table -- participation tracking
- `event_matches` table -- individual match records within events
- `chromacrush:event:{event_id}:leaderboard` -- Redis sorted set per event
- `chromacrush:event:active` -- Redis set of active event IDs

### Read Data (Cross-Module)
- Players via `PlayerServiceProtocol.get_player()`, `get_stats()`, `get_elo()`, `update_elo()`
- Energy via `EnergyServiceProtocol.get_energy()`, `consume_heart()`, `grant_bonus_hearts()`, `refund_heart()`
- Vault via `VaultServiceProtocol.add_artifact()`
- Matches via `MatchServiceProtocol.get_match()`

### Key Algorithms
1. **Atomic Join**: `increment_participant_count` returns new count; if exceeds max, `decrement_participant_count` + energy refund
2. **Scoring**: Score = base_score * multiplier + sum(bonus_points for met conditions)
3. **New Total Calculation**: Depends on `ScoringType` -- TOTAL_SCORE (sum), BEST_MATCH (max), MATCHES_PLAYED (count), AVERAGE_SCORE (sum for later avg)
4. **Reward Tier Assignment**: Check rank-based ranges first, then percentile-based ranges
5. **Leaderboard Fallback**: Redis first; if empty but participants exist, fall back to DB query

## 8. Testing Summary

- **85 unit tests** across 16 test classes
- All 15 public methods tested with success + error paths
- Test classes: `TestCreateEvent` (5), `TestGetEvent` (2), `TestListEvents` (6), `TestGetActiveEvents` (2), `TestJoinEvent` (10), `TestLeaveEvent` (6), `TestRecordEventMatch` (9), `TestGetLeaderboard` (4), `TestGetPlayerRank` (3), `TestGetPlayerEvents` (3), `TestGetEventParticipant` (3), `TestFinalizeEvent` (7), `TestCancelEvent` (5), `TestUpdateEvent` (2), `TestProcessScheduledEvents` (5), `TestHelperBehavior` (13)
- Uses `MockConfigService`, `MockLogService`, `MockErrorService` from `tests/mocks/services`
- All service and repo deps mocked with `AsyncMock`
- Coverage includes: validation errors, not-found errors, conflict errors, forbidden errors, entry requirements (ELO, level, energy, player type), scoring types, bonus conditions, capacity limits, race condition handling, config-driven behavior, energy refunds on cancel, reward distribution (artifact, energy, elo_bonus), leaderboard fallback, scheduled event processing with error handling, logging verification

## 9. Dependency Injection

All dependencies arrive via `__init__` constructor. No direct imports of core services. No `os.environ` or `os.getenv`. No bare raises -- all errors via `self._errors` factory. No raw SQL in service -- all data access via injected repository interfaces. The sole exception is `BonusSource.EVENT_REWARD` imported from `src.modules.energy.dto` (an enum value, not a service).
