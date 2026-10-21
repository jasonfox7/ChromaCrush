# Module Architecture Report: energy

**Module:** energy
**Build Wave:** 2
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The energy module manages the hearts/energy system that gates match play in ChromaCrush. It implements core energy operations (query, consume, check), time-based heart regeneration using a lazy calculation model, daily login streak tracking with milestone rewards, bonus heart grants from various sources with Redis-backed idempotency, and heart refunds for cancelled matches. All public service methods are **asynchronous** (`async def`). Pure calculation logic for regeneration and streaks is extracted into separate sync helper modules (`regen.py`, `streak.py`). The module uses a dual data access path: reads through `PlayerServiceProtocol` and writes through `EnergyStateRepositoryProtocol` directly (to bypass max_hearts cap for bonus overflow).

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get_energy` | `(player_id) -> EnergyInfo` | Get current energy with real-time regen calculation |
| `consume_heart` | `(player_id, amount=1) -> EnergyConsumeResult` | Consume hearts atomically with regen applied first |
| `can_play` | `(player_id, hearts_required=1) -> bool` | Non-consuming check if player has enough hearts |
| `apply_pending_regeneration` | `(player_id) -> RegenResult` | Calculate and persist regenerated hearts |
| `get_time_to_next_heart` | `(player_id) -> TimeToHeartResult` | Seconds until next heart regenerates |
| `record_login` | `(player_id) -> LoginResult` | Record login for streak tracking with milestone bonuses |
| `get_streak` | `(player_id) -> StreakInfo` | Get current streak information |
| `grant_bonus_hearts` | `(player_id, amount, source, idempotency_key=None) -> BonusGrantResult` | Grant bonus hearts with optional idempotency |
| `refund_heart` | `(player_id, amount=1, reason="match_cancelled") -> EnergyInfo` | Refund hearts capped at max_hearts |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Max hearts, regen interval, overflow limit, streak thresholds |
| `logger` | `LoggerProtocol` | Structured logging (debug, info, warn) |
| `errors` | `ErrorServiceProtocol` | Create validation, forbidden, not_found errors |
| `player_service` | `PlayerServiceProtocol` | Read energy state via `get_energy_state()` |
| `energy_repo` | `EnergyStateRepositoryProtocol` | Write energy state changes directly |
| `redis` | Redis client | Idempotency key storage for bonus grants |

---

## 4. Data Owned

| Table/Key | Storage | Description |
|-----------|---------|-------------|
| `energy_states` | PostgreSQL | Shared ownership with player module. Player owns the table; energy owns all business logic (regen, consume, streak, bonus) |
| `chromacrush:energy:bonus:{player_id}:{idempotency_key}` | Redis | Idempotency keys with 24-hour TTL for duplicate bonus prevention |

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `energy.max_hearts` | int | 5 | Maximum heart capacity |
| `energy.regen_interval_minutes` | int | 30 | Minutes per heart regeneration |
| `energy.bonus_overflow_limit` | int | 3 | Extra hearts allowed above max from bonuses |
| `energy.streak_reward_threshold_7` | int | 1 | Bonus hearts at 7-day streak |
| `energy.streak_reward_threshold_14` | int | 2 | Bonus hearts at 14-day streak |
| `energy.streak_reward_threshold_30` | int | 3 | Bonus hearts at 30-day streak |
| `energy.streak_reward_repeat_interval` | int | 7 | Days between reward repeats after day 30 |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_INVALID_INPUT` | 400 | amount < 1 in consume or grant |
| `FORBIDDEN_INSUFFICIENT_ENERGY` | 403 | Hearts < amount after regen in consume |
| `NOT_FOUND_PLAYER` | 404 | Energy state not found for player |

Note: Duplicate bonus grants return `BonusGrantResult(already_claimed=True)` rather than raising `CONFLICT_DUPLICATE_BONUS` (behavioral deviation from artifact; soft handling instead of error).

---

## 7. Cross-Module Interactions

**Called by:**
- `match` -- calls `consume_heart()` before match start, `can_play()` for pre-check, `refund_heart()` on cancellation
- `events` -- calls `grant_bonus_hearts()` for event rewards
- `ads` -- calls `grant_bonus_hearts()` for rewarded ad hearts
- `api` -- exposes energy endpoints

**Calls:**
- `player` -- calls `get_energy_state()` to read current state

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `BonusSource` | `src/modules/energy/dto.py` | Enum: AD_REWARD, STREAK_BONUS, EVENT_REWARD, REFERRAL, COMPENSATION, PROMOTION |
| `EnergyInfo` | `src/modules/energy/dto.py` | Complete energy state with real-time calculations |
| `EnergyConsumeResult` | `src/modules/energy/dto.py` | Result of consuming hearts |
| `RegenResult` | `src/modules/energy/dto.py` | Result of applying regeneration |
| `TimeToHeartResult` | `src/modules/energy/dto.py` | Time until next heart regenerates |
| `LoginResult` | `src/modules/energy/dto.py` | Result of recording a login |
| `StreakInfo` | `src/modules/energy/dto.py` | Current streak information |
| `BonusGrantResult` | `src/modules/energy/dto.py` | Result of granting bonus hearts |
| `EnergyServiceProtocol` | `src/modules/energy/protocols.py` | Protocol mirroring all 9 public methods for DI |
