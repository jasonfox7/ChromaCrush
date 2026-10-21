# Stage 4 Karen Compliance Sweep -- ads module

**Date:** 2026-02-07
**Agent:** Compliance Coder (Stage 4)
**Module:** ads
**Source:** `src/modules/ads/service.py`, `src/modules/ads/_helpers.py`

---

## Findings Addressed

### P3-04: Magic Numbers

All magic number findings from `stage3-fixes.md` have been resolved.

| Finding | Location | Constant Defined | Value |
|---------|----------|-----------------|-------|
| Ad request expiry `timedelta(minutes=5)` | service.py:192,226 | `_AD_REQUEST_EXPIRY_MINUTES` | `5` |
| Standard video duration 30000 ms | service.py:239 | `_STANDARD_VIDEO_DURATION_MS` | `30000` |
| Rewarded CPM multiplier 1.5 | _helpers.py:76 | `_REWARDED_CPM_MULTIPLIER` | `1.5` |
| Banner CPM multiplier 0.3 | _helpers.py:77 | `_BANNER_CPM_MULTIPLIER` | `0.3` |
| CPM divisor 1000 | _helpers.py:79 | `_CPM_DIVISOR` | `1000` |
| Week days 7 | _helpers.py:90 | `_WEEK_DAYS` | `7` |
| Month days 30 | _helpers.py:92 | `_MONTH_DAYS` | `30` |

### P3-09: Type Hints

All `Any` type findings from `stage3-fixes.md` have been resolved.

#### _helpers.py -- Record Protocol definitions

Defined `@runtime_checkable` Protocol classes to replace `Any` on all helper function parameters:

| Protocol | Replaces | Used By |
|----------|----------|---------|
| `AdFreeStatusRecord` | `record: Any` | `build_ad_free_status()` |
| `ImpressionRecord` | `record: Any` | `build_impression()` |
| `PlayerStatsRecord` | `record: Any` | `build_player_stats()` |
| `DailyAttributionRecord` | `record: Any` | `build_daily_attr()` |
| `EventOpportunityRecord` | `record: Any` | `build_event_opp()` |
| `BotAggregateRecord` | `agg: Any` | `build_bot_report()` |

Each Protocol declares the exact attributes accessed by the corresponding helper function. The `@runtime_checkable` decorator is applied so that `isinstance()` checks work at runtime if needed.

Additionally, `player_id: Any` was replaced with `player_id: PlayerId` on `build_ad_free_status()` and `build_player_stats()`, and `event_id: Any` was replaced with `event_id: EventId` on `build_event_opp()`. The `daily_recs: list[Any]` parameter on `build_bot_report()` was replaced with `list[DailyAttributionRecord]`.

#### service.py -- Method return types and parameter types

| Method | Change |
|--------|--------|
| `_valid_request()` | Return type changed from `Any` to `AdRequestRecord` (new Protocol) |
| `_mid_request_check()` | Parameter `ar` changed from `Any` to `AdRequestRecord` |
| `_provider_call()` | Parameter `fn` changed from `Any` to `Callable[[str, str], Awaitable[AdProviderResponse]]`; return type changed from `Any` to `AdProviderResponse` |

The `AdRequestRecord` Protocol was defined in `service.py` (module-level, after constants) to describe the shape of records returned by `AdRequestRepositoryProtocol.find_by_id()`. It declares: `id`, `player_id`, `ad_type`, `status`, `trigger`, `match_id`, `reward_type`, `reward_value`, `expires_at`, `completed_at`, `created_at`.

### Changes Made

1. **service.py**:
   - Added `Awaitable`, `Callable`, `Protocol` to typing imports
   - Added `AdProviderResponse` to types import
   - Added constants `_AD_REQUEST_EXPIRY_MINUTES` and `_STANDARD_VIDEO_DURATION_MS`
   - Added `AdRequestRecord` Protocol class
   - Replaced `timedelta(minutes=5)` with `timedelta(minutes=_AD_REQUEST_EXPIRY_MINUTES)` (2 occurrences)
   - Replaced `30000` with `_STANDARD_VIDEO_DURATION_MS`
   - Typed `_valid_request` return as `AdRequestRecord`
   - Typed `_mid_request_check` parameter as `AdRequestRecord`
   - Typed `_provider_call` with `Callable` and `AdProviderResponse`

2. **_helpers.py**:
   - Added `Protocol`, `runtime_checkable` to typing imports
   - Added 5 named constants for magic numbers
   - Added 6 record Protocol classes
   - Updated all helper function signatures to use typed Protocols instead of `Any`

### Findings NOT Addressed (by design)

- **P3-01** (file length): Not in scope for Stage 4.
- **P3-02** (function length): Not in scope for Stage 4.

### Behavioral Equivalence

All changes are strictly mechanical: named constants replace literal values, and Protocol type hints replace `Any`. No runtime behavior has changed. The Protocol classes use structural subtyping, so any ORM record that has the declared attributes will satisfy the type checker without requiring inheritance.
