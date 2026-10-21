# Stage 1 Drift Review: energy

**Artifact Report:** `docs/artifacts/energy/report.md`
**Implementation Doc:** `docs/implementation/energy/implementation.md`
**Reviewer:** Karen (Stage 1 Document Sweep)
**Date:** 2026-02-06

---

## Method Count Comparison

Artifact defines 9 public methods on `EnergyServiceProtocol`:
1. `get_energy`
2. `consume_heart`
3. `can_play`
4. `apply_pending_regeneration`
5. `get_time_to_next_heart`
6. `record_login`
7. `get_streak`
8. `grant_bonus_hearts`
9. `refund_heart`

Implementation doc (Section 4) documents 9 public methods matching exactly. The protocol and service both list all 9.

Implementation doc also documents 5 pure functions across 2 helper modules (`regen.py`, `streak.py`):
- `calculate_regenerated_hearts`
- `calculate_time_to_next_heart`
- `calculate_streak_update`
- `calculate_streak_reward`
- `calculate_next_reward_threshold`

These helper functions match the artifact's internal design section (Section 6.3 and 6.4). Match confirmed.

---

## Findings

[DRIFT] Artifact Section 8 (Async Behavior) lists 9 async methods -> Implementation doc Section 8 lists "8 public methods" but then enumerates 9 method names including `refund_heart`. This is a counting error in the implementation doc text (says "8" but there are "9").

[DRIFT] Artifact error taxonomy lists `CONFLICT_DUPLICATE_BONUS` (409) for duplicate idempotency key -> Implementation doc Section 7 (Error Codes Used) does not list `CONFLICT_DUPLICATE_BONUS` at all. The implementation doc describes Redis idempotency checking in Section 9 ("Redis failures are silently tolerated") and the DTO has `already_claimed: bool` on `BonusGrantResult`, suggesting duplicates are handled as soft returns rather than errors. This is a behavioral change: artifact says raise an error, implementation returns a result with `already_claimed=True`.

[DRIFT] Artifact specifies data access is through `PlayerServiceProtocol` only (Section 4.2) -> Implementation doc Section 5 states `EnergyService` reads through `PlayerServiceProtocol.get_energy_state()` but writes through `EnergyStateRepositoryProtocol.update()` directly. The "dual data access path" is intentional (to bypass max_hearts cap for bonus overflow) but diverges from the artifact's single-path data access model.

[DRIFT] Artifact specifies `EnergyService.__init__` depends on `ConfigProtocol`, `LoggerProtocol`, `ErrorServiceProtocol`, `DataContext` -> Implementation doc shows `__init__` takes 6 parameters: `config`, `logger`, `errors`, `player_service`, `energy_repo`, `redis`. No `DataContext` is directly injected; the repository handles it. The explicit `energy_repo` injection and `redis` injection differ from the artifact's dependency table.

[DRIFT] Artifact Redis key patterns include `chromacrush:energy:regen:{player_id}` for cached regen timestamps -> Implementation doc Section 9 mentions only the `chromacrush:energy:bonus:{player_id}:{idempotency_key}` Redis key pattern. The regen cache key from the artifact appears to not be implemented.

[DRIFT] Artifact CLI section lists 9 commands -> Implementation doc lists 9 commands: `get`, `consume`, `can-play`, `regen`, `time-to-heart`, `login`, `streak`, `grant`, `refund`. Match confirmed.

[DRIFT] Artifact specifies `EnergyStateRepository` with methods `find_by_player_id`, `create`, `update` -> Implementation doc shows the same 3 methods on `EnergyStateRepositoryProtocol`. Match confirmed. However, the artifact's repository interface is defined in `player` module's Section 4.2, while the implementation creates a separate protocol at `src/data/protocols/energy_state_repository.py` with a slightly different signature (`update` takes `**changes: object` instead of a structured update DTO).

---

## Document Health

Implementation doc is 327 lines -- thorough and well-documented with detailed internal design notes covering lazy regen, dual data access, interval preservation, clock skew handling, streak logic, bonus overflow, idempotency, config caching, and UUID conversion patterns.

---

## Summary

5 drift items found. The most significant are: (1) `CONFLICT_DUPLICATE_BONUS` error replaced with soft `already_claimed` flag on the result DTO -- this is a behavioral change in how duplicates are communicated to callers, (2) the dual data access path (read through player service, write through energy repo directly) not specified in the artifact, and (3) the missing regen cache Redis key. Item (1) is arguably a better design (non-throwing duplicate handling) but was not documented as a deviation.
