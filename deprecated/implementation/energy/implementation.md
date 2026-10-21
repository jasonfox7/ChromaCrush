# Energy Module Implementation Document

**Module:** energy
**Phase:** 2.2
**Author:** Coding Agent
**Date:** 2026-02-05

---

## 1. Summary

The energy module manages the hearts/energy system that gates match play in ChromaCrush. It implements five areas of functionality:

1. **Core energy operations** -- querying a player's current heart count (with real-time regeneration calculation), consuming hearts to start matches, and checking whether a player can play.
2. **Regeneration** -- time-based heart recovery using a configurable interval (default 30 minutes per heart). Regeneration is calculated lazily on read and persisted on write operations. Partial interval progress is preserved.
3. **Daily login streaks** -- tracking consecutive-day logins, resetting on missed days, and granting bonus hearts at milestone thresholds (days 7, 14, 30, then repeating every 7 days after 30).
4. **Bonus heart grants** -- granting hearts from various sources (ad rewards, events, referrals, compensation, promotions) with optional Redis-backed idempotency and an overflow allowance above max hearts.
5. **Heart refunds** -- returning hearts for cancelled matches, capped at max hearts.

All public service methods are `async def`. Pure calculation logic is extracted into two helper modules (`regen.py`, `streak.py`) that contain no I/O.

## 2. Files Created

### Module Code (`src/modules/energy/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Package root; re-exports all public DTOs, the service class, and the protocol |
| `dto.py` | Defines 7 data transfer objects (`EnergyInfo`, `EnergyConsumeResult`, `RegenResult`, `TimeToHeartResult`, `LoginResult`, `StreakInfo`, `BonusGrantResult`) and the `BonusSource` enum |
| `protocols.py` | Defines `EnergyServiceProtocol` using `typing.Protocol` with all 8 public async methods |
| `service.py` | `EnergyService` -- concrete implementation of all energy business logic |
| `regen.py` | Pure functions: `calculate_regenerated_hearts` and `calculate_time_to_next_heart` |
| `streak.py` | Pure functions: `calculate_streak_update`, `calculate_streak_reward`, `calculate_next_reward_threshold` |

### Data Layer (`src/data/`)
| File | Purpose |
|------|---------|
| `models/energy_state.py` | SQLAlchemy ORM model `EnergyStateModel` mapping to `energy_states` table (columns: `player_id`, `hearts`, `max_hearts`, `last_regen_at`, `daily_streak`, `last_login_date`, plus `TimestampMixin` for `created_at`/`updated_at`) |
| `protocols/energy_state_repository.py` | `EnergyStateRepositoryProtocol` with three async methods: `find_by_player_id`, `create`, `update` |
| `repositories/energy_state_repository.py` | `SQLAlchemyEnergyStateRepository` -- concrete repository using `DataContextProtocol` for session management; converts between ORM models and `EnergyState` domain objects |
| `migrations/versions/002_player_stats_and_energy.py` | Alembic migration creating the `energy_states` table (shared migration that also creates `player_stats` and extends `players`) |

### CLI (`src/cli/commands/`)
| File | Purpose |
|------|---------|
| `energy_commands.py` | Click command group with 9 commands: `get`, `consume`, `can-play`, `regen`, `time-to-heart`, `login`, `streak`, `grant`, `refund`. Uses `asyncio.run()` bridge and Rich for terminal output. |

### Tests (`tests/unit/modules/energy/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Empty package marker |
| `test_regen.py` | 15 tests covering `calculate_regenerated_hearts` (10 tests: no-regen at max, single/multi-interval regen, cap at max, partial interval preservation, zero hearts, above-max, negative elapsed, boundary timing) and `calculate_time_to_next_heart` (5 tests: None at max, full interval, partial, just-before-regen, above-max) |
| `test_streak.py` | 25 tests covering `calculate_streak_update` (6 tests: first login, same-day, consecutive, 2-day miss, many-day miss, increment from 1), `calculate_streak_reward` (10 tests: no reward at days 1/6/31/35, rewards at days 7/14/30, repeats at 37/44, custom thresholds), and `calculate_next_reward_threshold` (9 tests: streaks 0/3/7/10/14/20/30/35/37) |
| `test_energy_service.py` | 40 async tests using `pytest-asyncio` with in-memory mocks covering all 8 public methods: `get_energy` (4), `consume_heart` (6), `can_play` (3), `apply_pending_regeneration` (4), `get_time_to_next_heart` (2), `record_login` (6), `get_streak` (2), `grant_bonus_hearts` (7), `refund_heart` (6) |

## 3. Deviations from Artifact

Not assessed -- document produced from code examination only.

## 4. Public Interface

### `EnergyServiceProtocol` / `EnergyService`

All methods are `async def`. The `PlayerId` type is a `NewType` wrapping `uuid.UUID` from `src.core.types.game`.

```python
class EnergyService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        energy_repo: EnergyStateRepositoryProtocol,
        redis: Any,  # Redis client for idempotency
    ) -> None: ...

    # Core Energy Operations
    async def get_energy(self, player_id: PlayerId) -> EnergyInfo: ...
    async def consume_heart(self, player_id: PlayerId, amount: int = 1) -> EnergyConsumeResult: ...
    async def can_play(self, player_id: PlayerId, hearts_required: int = 1) -> bool: ...

    # Regeneration Operations
    async def apply_pending_regeneration(self, player_id: PlayerId) -> RegenResult: ...
    async def get_time_to_next_heart(self, player_id: PlayerId) -> TimeToHeartResult: ...

    # Streak Operations
    async def record_login(self, player_id: PlayerId) -> LoginResult: ...
    async def get_streak(self, player_id: PlayerId) -> StreakInfo: ...

    # Bonus Heart Operations
    async def grant_bonus_hearts(
        self,
        player_id: PlayerId,
        amount: int,
        source: BonusSource,
        idempotency_key: str | None = None,
    ) -> BonusGrantResult: ...

    async def refund_heart(
        self,
        player_id: PlayerId,
        amount: int = 1,
        reason: str = "match_cancelled",
    ) -> EnergyInfo: ...
```

### Pure Functions (`regen.py`)

```python
def calculate_regenerated_hearts(
    current_hearts: int,
    max_hearts: int,
    last_regen_at: datetime,
    now: datetime,
    regen_interval_seconds: int,
) -> tuple[int, int, datetime]: ...
# Returns (hearts_to_add, new_heart_count, new_last_regen_at)

def calculate_time_to_next_heart(
    current_hearts: int,
    max_hearts: int,
    last_regen_at: datetime,
    now: datetime,
    regen_interval_seconds: int,
) -> int | None: ...
# Returns seconds until next heart, or None if at/above max
```

### Pure Functions (`streak.py`)

```python
def calculate_streak_update(
    last_login_date: date | None,
    current_streak: int,
    today: date,
) -> tuple[int, bool, bool]: ...
# Returns (new_streak, streak_continued, streak_broken)

def calculate_streak_reward(
    streak_day: int,
    threshold_7: int,
    threshold_14: int,
    threshold_30: int,
    repeat_interval: int,
) -> int: ...
# Returns bonus hearts (0 if no reward at this day)

def calculate_next_reward_threshold(
    current_streak: int,
) -> tuple[int, int]: ...
# Returns (threshold_day, days_until_reward)
```

### DTOs (`dto.py`)

```python
class BonusSource(Enum):
    AD_REWARD = "ad_reward"
    STREAK_BONUS = "streak_bonus"
    EVENT_REWARD = "event_reward"
    REFERRAL = "referral"
    COMPENSATION = "compensation"
    PROMOTION = "promotion"

@dataclass
class EnergyInfo:
    player_id: str
    current_hearts: int
    max_hearts: int
    seconds_to_next_heart: int | None
    next_heart_at: datetime | None
    is_full: bool
    daily_streak: int
    last_login_date: date | None

@dataclass
class EnergyConsumeResult:
    success: bool
    hearts_consumed: int
    hearts_remaining: int
    hearts_regenerated_before_consume: int
    energy_info: EnergyInfo

@dataclass
class RegenResult:
    hearts_added: int
    hearts_before: int
    hearts_after: int
    last_regen_at: datetime
    energy_info: EnergyInfo

@dataclass
class TimeToHeartResult:
    seconds_remaining: int
    next_regen_at: datetime | None
    is_full: bool
    current_hearts: int
    max_hearts: int

@dataclass
class LoginResult:
    streak_day: int
    streak_continued: bool
    streak_broken: bool
    bonus_hearts_granted: int
    next_streak_reward_at: int
    energy_info: EnergyInfo

@dataclass
class StreakInfo:
    current_streak: int
    last_login_date: date | None
    streak_started_at: date | None
    next_reward_threshold: int
    days_until_reward: int
    reward_hearts: int

@dataclass
class BonusGrantResult:
    granted: bool
    hearts_granted: int
    hearts_before: int
    hearts_after: int
    source: BonusSource
    already_claimed: bool
    energy_info: EnergyInfo
```

### Repository Protocol

```python
class EnergyStateRepositoryProtocol(Protocol):
    async def find_by_player_id(self, player_id: UUID) -> EnergyState | None: ...
    async def create(self, player_id: UUID, hearts: int, max_hearts: int) -> EnergyState: ...
    async def update(self, player_id: UUID, **changes: object) -> EnergyState: ...
```

## 5. Dependencies Injected

### `EnergyService.__init__`
| Parameter | Protocol Type | Purpose |
|-----------|--------------|---------|
| `config` | `ConfigProtocol` | Read energy configuration values |
| `logger` | `LoggerProtocol` | Structured logging (debug, info, warn) |
| `errors` | `ErrorServiceProtocol` | Create typed `AppError` instances via `.validation()`, `.forbidden()`, `.not_found()` |
| `player_service` | `PlayerServiceProtocol` | Read energy state via `get_energy_state(player_id)` |
| `energy_repo` | `EnergyStateRepositoryProtocol` | Write energy state changes directly (bypasses player service validation for overflow) |
| `redis` | `Any` | Redis client for idempotency key checking (`exists`, `setex`) |

### `SQLAlchemyEnergyStateRepository.__init__`
| Parameter | Protocol Type | Purpose |
|-----------|--------------|---------|
| `data_ctx` | `DataContextProtocol` | Provides async SQLAlchemy sessions |
| `logger` | `LoggerProtocol` | Debug logging for data operations |
| `errors` | `ErrorServiceProtocol` | Create NOT_FOUND and VALIDATION errors |

## 6. Configuration Keys Used

All accessed via `self._config.get(key, default)` in `EnergyService.__init__`:

| Key | Default | Type | Purpose |
|-----|---------|------|---------|
| `energy.max_hearts` | `5` | `int` | Maximum heart capacity for a player |
| `energy.regen_interval_minutes` | `30` | `int` | Minutes per heart regeneration interval |
| `energy.bonus_overflow_limit` | `3` | `int` | Extra hearts allowed above max from bonus grants |
| `energy.streak_reward_threshold_7` | `1` | `int` | Bonus hearts granted at 7-day streak |
| `energy.streak_reward_threshold_14` | `2` | `int` | Bonus hearts granted at 14-day streak |
| `energy.streak_reward_threshold_30` | `3` | `int` | Bonus hearts granted at 30-day streak |
| `energy.streak_reward_repeat_interval` | `7` | `int` | Days between repeated rewards after day 30 |

## 7. Error Codes Used

| Code | Method(s) | Error Factory |
|------|-----------|---------------|
| `VALIDATION_INVALID_INPUT` | `consume_heart` (amount < 1), `grant_bonus_hearts` (amount < 1) | `errors.validation()` |
| `FORBIDDEN_INSUFFICIENT_ENERGY` | `consume_heart` (hearts < amount after regen) | `errors.forbidden()` |
| `NOT_FOUND_PLAYER` | `energy_repo.update` (energy state not found), `player_service.get_energy_state` (player not found) | `errors.not_found()` |
| `VALIDATION_INVALID_ATTRIBUTE` | `energy_repo.update` (invalid field name in `**changes`) | `errors.validation()` |

## 8. Async Behavior

All 8 public methods on `EnergyService` are `async def`:
- `get_energy`, `consume_heart`, `can_play`, `apply_pending_regeneration`, `get_time_to_next_heart`, `record_login`, `get_streak`, `grant_bonus_hearts`, `refund_heart`

All 3 repository methods are `async def`:
- `find_by_player_id`, `create`, `update`

The CLI bridges sync Click commands to async service methods using `asyncio.run()` via a `_run_async` helper that creates and shuts down an `ApplicationContext` per command invocation.

Pure functions in `regen.py` and `streak.py` are synchronous -- they perform no I/O and are called from within the async service methods.

Redis operations (`exists`, `setex`) in `grant_bonus_hearts` are awaited, indicating the Redis client is expected to be an async client. Redis failures are caught with bare `except Exception` and logged as warnings, allowing the operation to proceed (accepting duplicate-grant risk if Redis is unavailable).

## 9. Internal Design Notes

### Lazy vs. Eager Regeneration
The module uses a **lazy regeneration** pattern. `get_energy` and `can_play` calculate regenerated hearts in-memory without persisting. Only `apply_pending_regeneration`, `consume_heart`, and `record_login` persist regeneration to the database.

### Dual Data Access Path
`EnergyService` reads energy state through `PlayerServiceProtocol.get_energy_state()` but writes through `EnergyStateRepositoryProtocol.update()` directly. This is intentional: the player service enforces a `max_hearts` cap on writes, but the energy module needs to bypass that cap for bonus overflow (where hearts can reach `max_hearts + bonus_overflow_limit`). The service docstring explicitly notes this pattern.

### Interval-Preserving Regen
`calculate_regenerated_hearts` advances `last_regen_at` by exactly the number of consumed intervals (not to `now`). This preserves partial progress toward the next heart. For example, if 1.5 intervals have passed, one heart regenerates and 0.5 intervals of progress remain.

### Clock Skew Handling
Both `calculate_regenerated_hearts` and `calculate_time_to_next_heart` handle negative elapsed time (clock skew where `now < last_regen_at`). The regen function returns 0 hearts added; the time function returns a full interval as remaining time.

### Streak Logic
- **First login** (no `last_login_date`): streak = 1, `streak_continued = False`, `streak_broken = False`
- **Same-day login**: no changes persisted, 0 bonus hearts
- **Consecutive day** (1 day gap): streak increments, `streak_continued = True`
- **Missed days** (2+ day gap): streak resets to 1, `streak_broken = True`

Streak rewards fire at days 7, 14, 30, then every `repeat_interval` days after 30 (default 7). After day 30, the reward amount always uses the day-30 threshold value.

### Bonus Overflow Cap
Bonus hearts from `grant_bonus_hearts` can push hearts above `max_hearts` up to `max_hearts + bonus_overflow_limit` (default 5 + 3 = 8). In contrast, `refund_heart` caps at `max_hearts` only (no overflow). Streak bonus hearts in `record_login` also use the overflow cap.

### Idempotency via Redis
`grant_bonus_hearts` supports an optional `idempotency_key`. When provided, it checks/sets a Redis key at `chromacrush:energy:bonus:{player_id}:{idempotency_key}` with a 24-hour TTL (`86400` seconds via `setex`). Redis failures are silently tolerated.

### Config Caching
All configuration values are read once during `__init__` and cached as instance attributes. Changes to configuration after service construction are not reflected.

### UUID Conversion
The service converts `PlayerId` (a `NewType` of `uuid.UUID`) to `UUID` via `UUID(str(player_id))` when calling the repository's `update` method. This double-conversion pattern appears consistently throughout the service.
