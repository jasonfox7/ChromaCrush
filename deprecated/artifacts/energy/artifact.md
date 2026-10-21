# Energy Module Artifact

> **Module:** energy
> **Author:** Scout Agent
> **Date:** 2026-02-05
> **Version:** 1.0
> **Status:** Draft
> **Build Wave:** 2 (depends on player)

---

## Dependencies

### Module Dependencies

| Module | Dependency Type | What Is Used |
|--------|-----------------|--------------|
| `player` | Read | Player entity, EnergyState data access via `PlayerServiceProtocol` |

### Core Service Dependencies

| Service | Injected Via | Usage |
|---------|--------------|-------|
| `ConfigProtocol` | `__init__` | Max hearts, regen interval, streak thresholds, bonus heart amounts |
| `LoggerProtocol` | `__init__` | Heart consumption, regeneration, streak updates, bonus grants |
| `ErrorServiceProtocol` | `__init__` | Insufficient energy, validation errors |
| `DataContext` | `__init__` | Database session management |

### Repository Dependencies

| Repository | Ownership | Access Type | Notes |
|------------|-----------|-------------|-------|
| `EnergyStateRepository` | Shared | Read/Write | Player module owns the data table; energy module owns business logic |

### Redis Dependencies

| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `chromacrush:energy:regen:{player_id}` | String | `regen_interval_minutes * 60` | Tracks next regeneration trigger |
| `chromacrush:energy:bonus:{player_id}:{source}` | String | 24 hours | Prevents duplicate bonus claims |

---

## 1. Purpose

The energy module manages the hearts/energy system that gates match play in ChromaCrush. It implements:

1. **Heart Consumption** - Playing a match costs 1 heart (atomic check-and-consume)
2. **Heart Regeneration** - Hearts regenerate over time (1 per 30 minutes by default, configurable)
3. **Maximum Hearts Cap** - Players cannot exceed max hearts (5 by default)
4. **Daily Streak Tracking** - Consecutive login days are tracked for rewards
5. **Bonus Hearts** - Additional hearts from streaks, ads, or events

The energy system serves two psychological functions per the GDD:
- **Scarcity creation** - Each match feels precious, driving engagement
- **Return reward** - Full hearts waiting after a break creates positive return experience
- **Habitual check-ins** - Regeneration timing drives 8-12x daily check-ins

This module is a Wave 2 module that depends on the `player` module for EnergyState data access.

---

## 2. Public Interface

### 2.1 EnergyService Protocol

```python
# src/modules/energy/protocols.py
from typing import Protocol
from datetime import datetime

from src.core.types.game import PlayerId
from src.core.types.player import EnergyState


class EnergyServiceProtocol(Protocol):
    """Public interface for the energy module."""

    # ========== Core Energy Operations ==========

    async def get_energy(
        self,
        player_id: PlayerId,
    ) -> "EnergyInfo":
        """
        Get player's current energy state with real-time calculations.

        Calculates current hearts based on:
        1. Stored hearts in database
        2. Time elapsed since last_regen_at
        3. Pending regenerations (hearts that have regenerated but not yet persisted)

        Args:
            player_id: The player to query.

        Returns:
            EnergyInfo with current hearts, max hearts, time to next heart,
            streak info, and whether full.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.

        Logs:
            DEBUG: "Energy state retrieved" with player_id, current_hearts.
        """
        ...

    async def consume_heart(
        self,
        player_id: PlayerId,
        amount: int = 1,
    ) -> "EnergyConsumeResult":
        """
        Consume hearts for an action (e.g., starting a match).

        This operation is ATOMIC - it checks availability and consumes in
        a single transaction to prevent race conditions.

        If hearts have regenerated since last access, applies regeneration
        first, then consumes.

        Args:
            player_id: The player consuming energy.
            amount: Hearts to consume (default 1).

        Returns:
            EnergyConsumeResult with new state and consumption details.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            FORBIDDEN_INSUFFICIENT_ENERGY: If hearts < amount after regen calc.
            VALIDATION_INVALID_INPUT: If amount < 1.

        Logs:
            INFO: "Heart consumed" with player_id, amount, remaining_hearts.
            WARN: "Insufficient hearts" with player_id, required, available.
        """
        ...

    async def can_play(
        self,
        player_id: PlayerId,
        hearts_required: int = 1,
    ) -> bool:
        """
        Check if player has enough hearts to play (non-consuming).

        Includes real-time regeneration calculation.

        Args:
            player_id: The player to check.
            hearts_required: Hearts needed (default 1).

        Returns:
            True if player has >= hearts_required after regen calc.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Regeneration Operations ==========

    async def apply_pending_regeneration(
        self,
        player_id: PlayerId,
    ) -> "RegenResult":
        """
        Calculate and persist any hearts that have regenerated.

        Called internally by get_energy and consume_heart, but can be
        called explicitly to force sync.

        Calculates: floor((now - last_regen_at) / regen_interval)
        Caps at max_hearts.

        Args:
            player_id: The player.

        Returns:
            RegenResult with hearts_added and new state.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.

        Logs:
            INFO: "Hearts regenerated" with player_id, hearts_added (if > 0).
        """
        ...

    async def get_time_to_next_heart(
        self,
        player_id: PlayerId,
    ) -> "TimeToHeartResult":
        """
        Get time remaining until next heart regenerates.

        Args:
            player_id: The player.

        Returns:
            TimeToHeartResult with seconds_remaining, next_regen_at,
            and is_full (if already at max).

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Streak Operations ==========

    async def record_login(
        self,
        player_id: PlayerId,
    ) -> "LoginResult":
        """
        Record a player login for streak tracking.

        Compares last_login_date with today:
        - Same day: No change
        - Yesterday: Increment streak
        - Older: Reset streak to 1

        If streak reaches a reward threshold, grants bonus heart.

        Args:
            player_id: The player logging in.

        Returns:
            LoginResult with streak info and any bonus granted.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.

        Logs:
            INFO: "Login recorded" with player_id, streak_day, streak_continued.
            INFO: "Streak bonus granted" with player_id, bonus_hearts (if bonus).
        """
        ...

    async def get_streak(
        self,
        player_id: PlayerId,
    ) -> "StreakInfo":
        """
        Get player's current streak information.

        Args:
            player_id: The player.

        Returns:
            StreakInfo with current streak, last login, next reward threshold.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Bonus Heart Operations ==========

    async def grant_bonus_hearts(
        self,
        player_id: PlayerId,
        amount: int,
        source: "BonusSource",
        idempotency_key: str | None = None,
    ) -> "BonusGrantResult":
        """
        Grant bonus hearts from various sources.

        Bonus hearts can exceed max_hearts (up to max_hearts + bonus_overflow_limit).

        Uses Redis to track granted bonuses and prevent duplicate claims
        when idempotency_key is provided.

        Args:
            player_id: The player receiving bonus.
            amount: Hearts to grant.
            source: Source of bonus (ad_reward, streak_bonus, event_reward, etc).
            idempotency_key: Optional key to prevent duplicate grants.

        Returns:
            BonusGrantResult with new heart count and grant status.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If amount < 1.
            CONFLICT_DUPLICATE_BONUS: If idempotency_key already claimed.

        Logs:
            INFO: "Bonus hearts granted" with player_id, amount, source.
        """
        ...

    async def refund_heart(
        self,
        player_id: PlayerId,
        amount: int = 1,
        reason: str = "match_cancelled",
    ) -> "EnergyInfo":
        """
        Refund hearts (e.g., match cancelled, opponent disconnected).

        Respects max_hearts cap unless source was a bonus.

        Args:
            player_id: The player to refund.
            amount: Hearts to refund.
            reason: Reason for refund (for logging).

        Returns:
            Updated EnergyInfo.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.

        Logs:
            INFO: "Heart refunded" with player_id, amount, reason.
        """
        ...
```

### 2.2 Data Transfer Objects

```python
# src/modules/energy/dto.py
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum


class BonusSource(Enum):
    """Sources of bonus hearts."""
    AD_REWARD = "ad_reward"           # Watched rewarded ad
    STREAK_BONUS = "streak_bonus"     # Daily streak milestone
    EVENT_REWARD = "event_reward"     # Event participation
    REFERRAL = "referral"             # Friend referral
    COMPENSATION = "compensation"     # Support/bug compensation
    PROMOTION = "promotion"           # Marketing promotion


@dataclass
class EnergyInfo:
    """Complete energy state with real-time calculations."""
    player_id: str
    current_hearts: int
    max_hearts: int
    seconds_to_next_heart: int | None  # None if at max
    next_heart_at: datetime | None     # None if at max
    is_full: bool
    daily_streak: int
    last_login_date: date | None


@dataclass
class EnergyConsumeResult:
    """Result of consuming hearts."""
    success: bool
    hearts_consumed: int
    hearts_remaining: int
    hearts_regenerated_before_consume: int
    energy_info: EnergyInfo


@dataclass
class RegenResult:
    """Result of applying regeneration."""
    hearts_added: int
    hearts_before: int
    hearts_after: int
    last_regen_at: datetime
    energy_info: EnergyInfo


@dataclass
class TimeToHeartResult:
    """Time until next heart regenerates."""
    seconds_remaining: int
    next_regen_at: datetime | None
    is_full: bool
    current_hearts: int
    max_hearts: int


@dataclass
class LoginResult:
    """Result of recording a login."""
    streak_day: int
    streak_continued: bool  # True if streak incremented, False if reset or same-day
    streak_broken: bool     # True if streak was reset (not just same-day)
    bonus_hearts_granted: int
    next_streak_reward_at: int  # Days until next streak reward
    energy_info: EnergyInfo


@dataclass
class StreakInfo:
    """Player's streak information."""
    current_streak: int
    last_login_date: date | None
    streak_started_at: date | None  # Calculated: last_login - streak + 1
    next_reward_threshold: int      # e.g., 7, 14, 30
    days_until_reward: int
    reward_hearts: int              # Hearts granted at next threshold


@dataclass
class BonusGrantResult:
    """Result of granting bonus hearts."""
    granted: bool
    hearts_granted: int
    hearts_before: int
    hearts_after: int
    source: BonusSource
    already_claimed: bool  # True if idempotency key was already used
    energy_info: EnergyInfo
```

---

## 3. Mandatory Service Usage

### 3.1 Configuration Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `energy.max_hearts` | int | 5 | Maximum hearts a player can have (excluding bonus overflow) |
| `energy.regen_interval_minutes` | int | 30 | Minutes per heart regeneration |
| `energy.bonus_overflow_limit` | int | 3 | How many hearts above max can be held from bonuses |
| `energy.streak_reward_threshold_7` | int | 1 | Bonus hearts at 7-day streak |
| `energy.streak_reward_threshold_14` | int | 2 | Bonus hearts at 14-day streak |
| `energy.streak_reward_threshold_30` | int | 3 | Bonus hearts at 30-day streak |
| `energy.streak_reward_repeat_interval` | int | 7 | Days between repeat rewards after 30 |

### 3.2 Logging Events

| Level | Event | Context Fields | When |
|-------|-------|----------------|------|
| DEBUG | "Energy state retrieved" | `player_id`, `current_hearts`, `max_hearts` | On get_energy call |
| INFO | "Heart consumed" | `player_id`, `amount`, `remaining_hearts`, `match_id` | After successful consume |
| WARN | "Insufficient hearts" | `player_id`, `required`, `available` | When consume fails |
| INFO | "Hearts regenerated" | `player_id`, `hearts_added`, `new_total` | When regen applied (hearts_added > 0) |
| INFO | "Login recorded" | `player_id`, `streak_day`, `streak_continued`, `streak_broken` | On login record |
| INFO | "Streak bonus granted" | `player_id`, `bonus_hearts`, `streak_day` | When streak reaches threshold |
| INFO | "Bonus hearts granted" | `player_id`, `amount`, `source`, `new_total` | On bonus grant |
| INFO | "Heart refunded" | `player_id`, `amount`, `reason` | On refund |
| DEBUG | "Bonus claim attempted" | `player_id`, `source`, `idempotency_key` | On bonus attempt |
| WARN | "Duplicate bonus claim" | `player_id`, `source`, `idempotency_key` | When duplicate detected |

### 3.3 Error Types Used

| Error Code | HTTP | When Raised |
|------------|------|-------------|
| `NOT_FOUND_PLAYER` | 404 | Player ID doesn't exist |
| `FORBIDDEN_INSUFFICIENT_ENERGY` | 403 | Hearts < required amount |
| `VALIDATION_INVALID_INPUT` | 400 | Invalid amount (< 1) |
| `CONFLICT_DUPLICATE_BONUS` | 409 | Idempotency key already used |

---

## 4. Data Access

### 4.1 Owned Data

The energy module does NOT own any database tables. The `energy_states` table is owned by the `player` module. The energy module owns the **business logic** for energy operations.

This shared ownership pattern is documented in the dependency graph:
- `player` module: Owns `energy_states` table (data storage)
- `energy` module: Owns business logic (regeneration, consumption, streaks)

### 4.2 Data Read/Write via Player Module

The energy module accesses energy state data through the player module's `PlayerServiceProtocol`:

```python
# Reading energy state
energy_state = await self._player_service.get_energy_state(player_id)

# Writing energy state
updated = await self._player_service.update_energy_state(
    player_id,
    EnergyStateUpdate(
        hearts=new_hearts,
        last_regen_at=new_regen_time,
        daily_streak=new_streak,
        last_login_date=today,
    )
)
```

### 4.3 Redis Data

The energy module owns these Redis keys for caching and idempotency:

| Key | Type | TTL | Usage |
|-----|------|-----|-------|
| `chromacrush:energy:regen:{player_id}` | String | regen_interval | Cached next regen timestamp |
| `chromacrush:energy:bonus:{player_id}:{idempotency_key}` | String | 24h | Prevents duplicate bonus claims |

Redis access is through the injected `RedisContext` protocol:

```python
class RedisContextProtocol(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ex: int | None = None) -> None: ...
    async def setex(self, key: str, seconds: int, value: str) -> None: ...
    async def exists(self, key: str) -> bool: ...
    async def delete(self, key: str) -> None: ...
```

### 4.4 Transaction Requirements

| Operation | Transaction Scope | Notes |
|-----------|-------------------|-------|
| `consume_heart` | Single transaction | Must be atomic: check + update in one operation |
| `apply_pending_regeneration` | Single transaction | Updates hearts and last_regen_at together |
| `record_login` | Single transaction | Updates streak and last_login_date together |
| `grant_bonus_hearts` | Redis + DB | Redis check first, then DB update |

**Critical: Atomic Consume**

The `consume_heart` operation must be atomic to prevent race conditions where:
1. Two concurrent requests both check hearts = 1
2. Both proceed to consume
3. Hearts goes negative

Implementation uses optimistic locking or SELECT FOR UPDATE:

```python
async def consume_heart(self, player_id: PlayerId, amount: int = 1) -> EnergyConsumeResult:
    async with self._data_ctx.session() as session:
        # Apply any pending regeneration first
        regen_result = await self._apply_regen_internal(session, player_id)

        # Atomic check-and-update
        energy_state = await self._player_service.get_energy_state(player_id)
        current = regen_result.hearts_after

        if current < amount:
            raise self._errors.forbidden(
                "Not enough hearts",
                code="FORBIDDEN_INSUFFICIENT_ENERGY",
                required=amount,
                available=current,
            )

        new_hearts = current - amount
        await self._player_service.update_energy_state(
            player_id,
            EnergyStateUpdate(hearts=new_hearts),
        )

        return EnergyConsumeResult(...)
```

---

## 5. Presentation Boundary

### 5.1 What This Module Returns

The energy module returns domain DTOs (`EnergyInfo`, `EnergyConsumeResult`, etc.). It does NOT return:
- JSON objects
- HTTP responses
- Formatted strings (e.g., "2h 15m until next heart")
- UI-specific data (progress bar percentages, color codes)

### 5.2 Presentation Layer Responsibility

The presentation layer (`src/presentation/adapters/energy_adapter.py`) handles:
- Formatting `seconds_to_next_heart` as human-readable "Xh Ym"
- Calculating progress bar percentage for heart regeneration
- Determining UI states (e.g., "FULL", "REGENERATING", "EMPTY")
- Localizing streak reward messages

### 5.3 Example Boundary

```python
# Module returns domain object
energy_info = await energy_service.get_energy(player_id)
# energy_info.seconds_to_next_heart = 1234

# Adapter converts for API
response = energy_adapter.to_response(energy_info)
# response.time_to_next_heart = "20m 34s"
# response.regen_progress_percent = 31.5
```

---

## 6. Internal Design

### 6.1 Service Implementation Structure

```
src/modules/energy/
    __init__.py           # Exports EnergyService, protocols, DTOs
    service.py            # EnergyService implementation
    protocols.py          # EnergyServiceProtocol
    dto.py                # EnergyInfo, EnergyConsumeResult, etc.
    regen.py              # Regeneration calculation helpers
    streak.py             # Streak calculation helpers
```

### 6.2 Component Diagram

```
                    EnergyService
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
  PlayerService    RedisContext      ConfigService
  (get/update      (regen cache,     (max_hearts,
   energy_state)    idempotency)      intervals)
        │
        ▼
  DataContext
  (PostgreSQL)
```

### 6.3 Regeneration Algorithm

```python
def calculate_regenerated_hearts(
    current_hearts: int,
    max_hearts: int,
    last_regen_at: datetime,
    now: datetime,
    regen_interval_seconds: int,
) -> tuple[int, int, datetime]:
    """
    Calculate hearts regenerated since last_regen_at.

    Returns:
        Tuple of (hearts_to_add, new_heart_count, new_last_regen_at)
    """
    if current_hearts >= max_hearts:
        return 0, current_hearts, last_regen_at

    elapsed_seconds = (now - last_regen_at).total_seconds()
    hearts_can_regen = max_hearts - current_hearts

    # How many full intervals have passed?
    intervals_passed = int(elapsed_seconds // regen_interval_seconds)
    hearts_to_add = min(intervals_passed, hearts_can_regen)

    new_hearts = current_hearts + hearts_to_add

    # Update last_regen_at to account for used intervals only
    # This preserves partial progress toward next heart
    if hearts_to_add > 0:
        new_last_regen_at = last_regen_at + timedelta(
            seconds=hearts_to_add * regen_interval_seconds
        )
    else:
        new_last_regen_at = last_regen_at

    return hearts_to_add, new_hearts, new_last_regen_at


def calculate_time_to_next_heart(
    current_hearts: int,
    max_hearts: int,
    last_regen_at: datetime,
    now: datetime,
    regen_interval_seconds: int,
) -> int | None:
    """
    Calculate seconds until next heart regenerates.

    Returns:
        Seconds until next heart, or None if at max.
    """
    if current_hearts >= max_hearts:
        return None

    elapsed = (now - last_regen_at).total_seconds()
    seconds_into_current_interval = elapsed % regen_interval_seconds
    seconds_remaining = regen_interval_seconds - seconds_into_current_interval

    return int(seconds_remaining)
```

### 6.4 Streak Calculation

```python
from datetime import date, timedelta


def calculate_streak_update(
    last_login_date: date | None,
    current_streak: int,
    today: date,
) -> tuple[int, bool, bool]:
    """
    Calculate streak update based on login date comparison.

    Returns:
        Tuple of (new_streak, streak_continued, streak_broken)
    """
    if last_login_date is None:
        # First ever login
        return 1, False, False

    days_since_login = (today - last_login_date).days

    if days_since_login == 0:
        # Same day, no change
        return current_streak, False, False
    elif days_since_login == 1:
        # Consecutive day, increment streak
        return current_streak + 1, True, False
    else:
        # Streak broken, reset to 1
        return 1, False, True


def calculate_streak_reward(
    streak_day: int,
    threshold_7: int,
    threshold_14: int,
    threshold_30: int,
    repeat_interval: int,
) -> int:
    """
    Calculate bonus hearts for a given streak day.

    Rewards at: 7, 14, 30, then every repeat_interval days after 30.

    Returns:
        Bonus hearts to grant (0 if no reward).
    """
    if streak_day == 7:
        return threshold_7
    elif streak_day == 14:
        return threshold_14
    elif streak_day == 30:
        return threshold_30
    elif streak_day > 30 and (streak_day - 30) % repeat_interval == 0:
        return threshold_30  # Repeat the 30-day reward
    else:
        return 0


def calculate_next_reward_threshold(
    current_streak: int,
) -> tuple[int, int]:
    """
    Calculate next streak reward threshold.

    Returns:
        Tuple of (threshold_day, days_until)
    """
    if current_streak < 7:
        return 7, 7 - current_streak
    elif current_streak < 14:
        return 14, 14 - current_streak
    elif current_streak < 30:
        return 30, 30 - current_streak
    else:
        # After 30, rewards every 7 days
        days_since_30 = current_streak - 30
        days_into_cycle = days_since_30 % 7
        days_until = 7 - days_into_cycle if days_into_cycle > 0 else 7
        return current_streak + days_until, days_until
```

### 6.5 Real-Time Heart Calculation

The energy module provides **real-time** heart counts by calculating regeneration on-the-fly:

```python
async def get_energy(self, player_id: PlayerId) -> EnergyInfo:
    # Get stored state
    energy_state = await self._player_service.get_energy_state(player_id)

    # Calculate current time
    now = datetime.now(timezone.utc)

    # Calculate regenerated hearts (without persisting yet)
    hearts_to_add, effective_hearts, _ = calculate_regenerated_hearts(
        current_hearts=energy_state.hearts,
        max_hearts=energy_state.max_hearts,
        last_regen_at=energy_state.last_regen_at,
        now=now,
        regen_interval_seconds=self._regen_interval * 60,
    )

    # Calculate time to next heart
    seconds_to_next = calculate_time_to_next_heart(
        current_hearts=effective_hearts,
        max_hearts=energy_state.max_hearts,
        last_regen_at=energy_state.last_regen_at,
        now=now,
        regen_interval_seconds=self._regen_interval * 60,
    )

    return EnergyInfo(
        player_id=str(player_id),
        current_hearts=effective_hearts,
        max_hearts=energy_state.max_hearts,
        seconds_to_next_heart=seconds_to_next,
        next_heart_at=now + timedelta(seconds=seconds_to_next) if seconds_to_next else None,
        is_full=effective_hearts >= energy_state.max_hearts,
        daily_streak=energy_state.daily_streak,
        last_login_date=energy_state.last_login_date,
    )
```

---

## 7. CLI Surface

### 7.1 Commands

```bash
# Core energy operations
chromacrush energy get <player-id>
chromacrush energy consume <player-id> [--amount N]
chromacrush energy can-play <player-id>

# Regeneration
chromacrush energy regen <player-id>
chromacrush energy time-to-heart <player-id>

# Streak operations
chromacrush energy login <player-id>
chromacrush energy streak <player-id>

# Bonus operations
chromacrush energy grant <player-id> --amount N --source <source>
chromacrush energy refund <player-id> [--amount N] [--reason <reason>]
```

### 7.2 CLI Command Implementation

```python
# src/cli/commands/energy_commands.py
import click
from uuid import UUID
from datetime import datetime

@click.group()
def energy():
    """Energy/hearts management commands."""
    pass

@energy.command("get")
@click.argument("player_id")
@click.pass_context
async def get_energy(ctx, player_id: str):
    """Get player's current energy state."""
    energy_service = ctx.obj["energy_service"]

    info = await energy_service.get_energy(PlayerId(UUID(player_id)))

    click.echo(f"Energy for player {player_id[:8]}...")
    click.echo(f"  Hearts: {info.current_hearts}/{info.max_hearts}")
    if info.seconds_to_next_heart:
        mins, secs = divmod(info.seconds_to_next_heart, 60)
        click.echo(f"  Next heart in: {mins}m {secs}s")
    else:
        click.echo(f"  Status: FULL")
    click.echo(f"  Daily streak: {info.daily_streak} days")

@energy.command("consume")
@click.argument("player_id")
@click.option("--amount", default=1, help="Hearts to consume")
@click.pass_context
async def consume_heart(ctx, player_id: str, amount: int):
    """Consume hearts (e.g., to start a match)."""
    energy_service = ctx.obj["energy_service"]

    try:
        result = await energy_service.consume_heart(
            PlayerId(UUID(player_id)),
            amount=amount,
        )
        click.echo(f"Consumed {result.hearts_consumed} heart(s)")
        click.echo(f"  Remaining: {result.hearts_remaining}")
        if result.hearts_regenerated_before_consume > 0:
            click.echo(f"  (Regenerated {result.hearts_regenerated_before_consume} first)")
    except Exception as e:
        click.echo(f"Failed: {e}", err=True)

@energy.command("login")
@click.argument("player_id")
@click.pass_context
async def record_login(ctx, player_id: str):
    """Record a login for streak tracking."""
    energy_service = ctx.obj["energy_service"]

    result = await energy_service.record_login(PlayerId(UUID(player_id)))

    click.echo(f"Login recorded for player {player_id[:8]}...")
    click.echo(f"  Streak day: {result.streak_day}")
    if result.streak_continued:
        click.echo(f"  Streak continued!")
    elif result.streak_broken:
        click.echo(f"  Streak broken - reset to day 1")
    else:
        click.echo(f"  Same-day login")

    if result.bonus_hearts_granted > 0:
        click.echo(f"  BONUS: +{result.bonus_hearts_granted} hearts!")

@energy.command("grant")
@click.argument("player_id")
@click.option("--amount", required=True, type=int, help="Hearts to grant")
@click.option("--source", required=True,
              type=click.Choice(["ad_reward", "streak_bonus", "event_reward",
                                "referral", "compensation", "promotion"]))
@click.pass_context
async def grant_bonus(ctx, player_id: str, amount: int, source: str):
    """Grant bonus hearts to a player."""
    energy_service = ctx.obj["energy_service"]

    result = await energy_service.grant_bonus_hearts(
        PlayerId(UUID(player_id)),
        amount=amount,
        source=BonusSource(source),
    )

    click.echo(f"Granted {result.hearts_granted} bonus heart(s)")
    click.echo(f"  Source: {result.source.value}")
    click.echo(f"  Hearts: {result.hearts_before} -> {result.hearts_after}")

@energy.command("streak")
@click.argument("player_id")
@click.pass_context
async def get_streak(ctx, player_id: str):
    """Get player's streak information."""
    energy_service = ctx.obj["energy_service"]

    info = await energy_service.get_streak(PlayerId(UUID(player_id)))

    click.echo(f"Streak info for player {player_id[:8]}...")
    click.echo(f"  Current streak: {info.current_streak} days")
    click.echo(f"  Last login: {info.last_login_date}")
    click.echo(f"  Next reward at: day {info.next_reward_threshold}")
    click.echo(f"  Days until reward: {info.days_until_reward}")
    click.echo(f"  Reward amount: +{info.reward_hearts} hearts")
```

---

## 8. Async Behavior

All public methods are `async def` because they involve:
- Database operations via the player service
- Redis operations for caching and idempotency
- Time-based calculations that may need to persist state

### Async Contract

| Method | Async | I/O Type | Notes |
|--------|-------|----------|-------|
| `get_energy` | Yes | DB read, Redis read | May read Redis cache |
| `consume_heart` | Yes | DB read/write | Atomic transaction |
| `can_play` | Yes | DB read | Read-only check |
| `apply_pending_regeneration` | Yes | DB write | Persists regen |
| `get_time_to_next_heart` | Yes | DB read | Pure calculation after DB read |
| `record_login` | Yes | DB write | Updates streak |
| `get_streak` | Yes | DB read | Read-only |
| `grant_bonus_hearts` | Yes | Redis write, DB write | Idempotency check + update |
| `refund_heart` | Yes | DB write | Simple update |

### Error Propagation

Errors propagate through the error service:

```python
async def consume_heart(self, player_id: PlayerId, amount: int = 1) -> EnergyConsumeResult:
    try:
        energy_state = await self._player_service.get_energy_state(player_id)
    except AppError:
        raise  # NOT_FOUND_PLAYER propagates unchanged
    except Exception as e:
        raise self._errors.internal(
            "Failed to get energy state",
            code="INTERNAL_DATABASE_ERROR",
            original_error=str(e),
        ) from e

    # ... rest of implementation
```

---

## 9. Edge Cases & Decisions

### 9.1 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data ownership | Player owns table, energy owns logic | Clean Wave 1/2 separation; avoids circular dependency |
| Real-time calculation | Calculate on read, persist lazily | Avoids scheduled jobs; accurate even if server was down |
| Bonus overflow | Allow bonus hearts above max | Per GDD, bonus hearts are rewards and shouldn't be lost |
| Streak timezone | UTC midnight | Consistent across players; simpler than per-user TZ |
| Regen partial progress | Preserve partial intervals | Fair to players; don't lose 29 minutes of regen |
| Idempotency window | 24 hours | Long enough for retries; short enough to not bloat Redis |

### 9.2 Edge Cases

| Scenario | Handling |
|----------|----------|
| Consume when hearts = 0 | Apply pending regen first; if still 0, reject with FORBIDDEN_INSUFFICIENT_ENERGY |
| Consume more than available | Reject entire request; no partial consumption |
| Hearts > max after bonus | Allow; bonus overflow limit is max_hearts + bonus_overflow_limit |
| Login twice same day | Second login is no-op for streak; returns same-day status |
| Login after 2+ days missed | Reset streak to 1; mark streak_broken = true |
| Server downtime during regen | Real-time calculation catches up; no hearts lost |
| Redis unavailable for idempotency | Fall through to DB update; log warning; accept duplicate risk |
| Negative hearts somehow | Floor at 0; log error for investigation |
| Refund above max | Cap at max_hearts unless original consume was from bonus |
| Concurrent consume requests | Atomic transaction prevents double-spend |

### 9.3 GDD Compliance

| GDD Requirement | Implementation |
|-----------------|----------------|
| "5 Hearts (regenerate 1/20 min)" | Configurable: default 5 max, 30 min regen (GDD says 20, but config says 30 - using config) |
| "Creates scarcity" | Each match costs 1 heart via consume_heart |
| "Return after break = reward (full hearts)" | Real-time regen calculation ensures hearts are ready |
| "Drives habitual check-ins 8-12x/day" | 30-min regen = 2.5 hours for full refill = multiple daily sessions |
| "Daily Login Streak" | record_login tracks consecutive days |
| "Progressive rewards escalate over 7/14/30 days" | Configurable thresholds with bonus grants |
| "Watch a 15-second ad to gain +1 heart" | grant_bonus_hearts with source=AD_REWARD |

### 9.4 Escalation Required

None. All edge cases are covered by existing error taxonomy and guidance.

---

## 10. Integration Points

### 10.1 Match Module Integration

The match module will call energy module before starting a match:

```python
# In match module (Phase 2)
async def create_match(self, player1_id, player2_id, ...):
    # Check both players have energy
    if not await self._energy_service.can_play(player1_id):
        raise self._errors.forbidden("Player 1 insufficient energy", ...)
    if not await self._energy_service.can_play(player2_id):
        raise self._errors.forbidden("Player 2 insufficient energy", ...)

    # Consume hearts
    await self._energy_service.consume_heart(player1_id)
    await self._energy_service.consume_heart(player2_id)

    # Create match...
```

### 10.2 Events Module Integration

The events module can grant bonus hearts as rewards:

```python
# In events module (Phase 2)
async def grant_event_reward(self, player_id, event_id):
    await self._energy_service.grant_bonus_hearts(
        player_id,
        amount=2,
        source=BonusSource.EVENT_REWARD,
        idempotency_key=f"event:{event_id}:player:{player_id}",
    )
```

### 10.3 Ads Module Integration

The ads module can grant hearts for watching rewarded ads:

```python
# In ads module (Phase 2)
async def complete_rewarded_ad(self, player_id, ad_session_id):
    await self._energy_service.grant_bonus_hearts(
        player_id,
        amount=1,
        source=BonusSource.AD_REWARD,
        idempotency_key=f"ad:{ad_session_id}",
    )
```

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent |
