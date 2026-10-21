# Stage 3 P1-P3 Fixes -- events module

**Date:** 2026-02-07
**Reviewer:** Karen P1-P3 Agent (S3-E)
**Module:** events
**Artifact:** `docs/artifacts/events/artifact.md` v1.0
**Source:** `src/modules/events/service.py` (1237 lines), `types.py`, `dto.py`, `protocols.py`, `__init__.py`
**Tests:** `tests/unit/modules/events/test_event_service.py` (~2185 lines)
**CLI:** `src/cli/commands/events_commands.py` (539 lines)

---

## P1 -- Framework Rules

### P1-01: No Direct Service Instantiation
**Result:** PASS (no violations)

Grep patterns clean. All core service imports are under `TYPE_CHECKING` guard (lines 47-59). Constructor receives all dependencies via `__init__`. No `ConfigService()`, `LogService()`, or `ErrorService()` instantiation.

Note: `from src.modules.energy.dto import BonusSource` at line 16 imports a DTO enum from another module at top level (not under `TYPE_CHECKING`). This is a type/enum import, not a service instantiation, so it is **allowed** per the checklist exception for type definitions. However, placing it under `TYPE_CHECKING` would be more consistent with the overall pattern used for cross-module imports in this file.

### P1-02: No Direct Environment Access
**Result:** PASS (no violations)

No `os.environ`, `os.getenv`, or `import os` found in module source.

### P1-03: No Bare Raises
**Result:** PASS (no violations)

All error raises go through `self._errors.validation()`, `self._errors.not_found()`, `self._errors.conflict()`, `self._errors.forbidden()`. No bare `raise Exception()`, `raise ValueError()`, etc.

### P1-04: No UI / Rendering Logic in Modules
**Result:** PASS (no violations)

No `click`, `rich`, `print()`, `sys.stdout`, HTTP response construction, or terminal formatting in module source.

### P1-05: No Raw Data Access in Business Logic
**Result:** PASS (no violations)

All data access flows through injected repository protocol interfaces (`self._event_repo`, `self._participant_repo`, `self._leaderboard_repo`). No SQLAlchemy, Redis, or raw SQL imports in `service.py`.

Exception: `self._data_ctx.redis.sadd()` and `self._data_ctx.redis.srem()` at lines 882-883 and 905-906 in `process_scheduled_events()` use direct Redis access through `data_ctx`. This is a borderline case -- the leaderboard repository handles most Redis operations, but the "active event set" maintenance uses direct Redis. This is acceptable since `data_ctx` is an injected dependency, but ideally this operation would be encapsulated in a repository method.

### P1-06: Async Matches Artifact Spec
**Result:** PASS (no violations)

Artifact specifies this module is **fully asynchronous** with all public methods as `async def`. Implementation confirms all 15 public methods in `EventService` are `async def`:
- `create_event`, `get_event`, `list_events`, `get_active_events`, `join_event`, `leave_event`, `record_event_match`, `get_leaderboard`, `get_player_rank`, `get_player_events`, `get_event_participant`, `finalize_event`, `cancel_event`, `update_event`, `process_scheduled_events`

Protocol in `protocols.py` matches -- all `EventServiceProtocol` methods are `async def`.

No `asyncio.run()` or `asyncio.create_task()` found in module source.

### P1-07: CLI Exercises Same Code Paths
**Result:** PASS (no violations)

All CLI commands in `events_commands.py` call service methods through `EventService`:
- `create` -> `svc.create_event()`
- `get` -> `svc.get_event()`
- `list` -> `svc.list_events()`
- `active` -> `svc.get_active_events()`
- `join` -> `svc.join_event()`
- `leave` -> `svc.leave_event()`
- `record-match` -> `svc.record_event_match()`
- `leaderboard` -> `svc.get_leaderboard()`
- `rank` -> `svc.get_player_rank()`
- `player-events` -> `svc.get_player_events()`
- `finalize` -> `svc.finalize_event()`
- `cancel` -> `svc.cancel_event()`
- `update` -> `svc.update_event()`
- `process-scheduled` -> `svc.process_scheduled_events()`

No direct repository calls or business logic duplication in CLI. No bypassing of the service layer.

---

## P2 -- Data Layer & Config Compliance

### P2-01: Config Keys Match Registered Namespaces
**Result:** ESCALATION NEEDED

[ESCALATION] Config keys use the `events.*` namespace (12 keys: `events.flash_duration_hours`, `events.weekly_duration_days`, `events.seasonal_duration_days`, `events.entry_energy_cost`, `events.match_energy_cost`, `events.max_participants_flash`, `events.max_participants_weekly`, `events.max_participants_seasonal`, `events.leaderboard_cache_ttl_seconds`, `events.auto_finalize_delay_minutes`, `events.min_matches_for_rewards`, `events.allow_leave_after_match`).

The `events` namespace is **NOT** in the registered namespaces table in `configuration.md` Section 2. However, the compliance checklist notes: "Modules may define their own config namespaces if declared in their artifact." The events artifact (Section: Configuration Keys) declares all 12 keys. This is an **Orchestrator escalation item** -- the `events` namespace should be added to `configuration.md`.

All 12 config keys used in service.py (lines 109-121) match the artifact exactly.

### P2-02: Repository Pattern Followed
**Result:** PASS (no violations)

Service receives all repositories via `__init__` as Protocol interfaces:
- `event_repository: EventRepositoryProtocol`
- `event_participant_repository: EventParticipantRepositoryProtocol`
- `event_leaderboard_repository: EventLeaderboardRepositoryProtocol`

Service calls `self._event_repo.method()`, `self._participant_repo.method()`, `self._leaderboard_repo.method()`. No SQLAlchemy or direct database imports in `service.py`.

### P2-03: Data Ownership Respected
**Result:** PASS (no violations)

Events module writes to: `events`, `event_participants`, `event_matches` (via repositories) -- all owned per the ownership matrix.
Cross-module reads go through service protocols: `self._player_service.get_player()`, `self._energy_service.get_energy()`, `self._vault_service.add_artifact()`, etc.

No direct imports of other modules' repositories.

### P2-04: Transactions at Service Layer
**Result:** PASS (no violations)

No `.commit()` or `.rollback()` found in module source. The artifact specifies `async with self._data_ctx.session()` pattern for transactions, but the implementation does not use explicit session blocks -- it relies on the repositories handling individual operations. This is acceptable given the service delegates all persistence to repository calls.

---

## P3 -- Best Practices & Testing

### P3-01: Service Files Length
**Result:** FINDING

[P3] [src/modules/events/service.py:1-1237] Service file is 1237 lines, far exceeding the 500-line hard limit. -> Split into smaller files: extract private helpers (_parse_requirements, _parse_reward_tiers, _parse_rules, _record_to_event, _record_to_summary, _build_participant, _calculate_level, _check_bonus_condition, _calculate_new_score, _determine_reward_tier, _calculate_points_to_next_tier, _grant_reward, _check_entry_requirements) into a separate `helpers.py` or split by domain concern (e.g., `leaderboard_service.py`, `reward_service.py`).

### P3-02: Function Length
**Result:** FINDINGS

[P3] [src/modules/events/service.py:659-772] `finalize_event` is 114 lines, exceeding the 50-line maximum. -> Extract reward distribution loop into private method `_distribute_rewards()` and top-player assembly into `_get_top_players()`.

[P3] [src/modules/events/service.py:464-536] `get_leaderboard` is 73 lines, exceeding the 50-line maximum. -> Extract the Redis-path and DB-fallback-path entry assembly into separate private methods.

[P3] [src/modules/events/service.py:346-462] `record_event_match` is 117 lines, exceeding the 50-line maximum. -> Extract scoring calculation and participant update into private helpers.

[P3] [src/modules/events/service.py:208-297] `join_event` is 90 lines, exceeding the 50-line maximum. -> Extract capacity check and race-condition rollback into a private method.

[P3] [src/modules/events/service.py:774-834] `cancel_event` is 61 lines, exceeding the 50-line maximum. -> Extract energy refund loop into a private method.

[P3] [src/modules/events/service.py:863-941] `process_scheduled_events` is 79 lines, exceeding the 50-line maximum. -> Extract activation, deactivation, and finalization loops into private methods.

### P3-03: Constructor Parameters
**Result:** PASS (deferred to artifact)

Constructor has 11 parameters: `config`, `logger`, `errors`, `data_ctx`, `vault_service`, `energy_service`, `match_service`, `player_service`, `event_repository`, `event_participant_repository`, `event_leaderboard_repository`.

Artifact specifies 12 parameters (includes `redis_ctx`). Implementation has 11, which is fewer than the artifact spec. The missing `redis_ctx` is replaced by using `data_ctx.redis` directly. Per the checklist note: "If the artifact specifies the constructor signature, defer to the artifact." 11 < 12, so no finding.

### P3-04: No Magic Numbers
**Result:** FINDING

[P3] [src/modules/events/service.py:1054-1062] `_calculate_level` uses bare numeric literals 5, 20, 50, 100 as level thresholds without named constants. -> Define named constants at the top of the service (e.g., `_LEVEL_THRESHOLDS = [5, 20, 50, 100]`) or pull from config.

[P3] [src/modules/events/service.py:127] Validation uses literal `3` for minimum name length. -> Define as a named constant `_MIN_EVENT_NAME_LENGTH = 3`.

[P3] [src/modules/events/service.py:134] Validation uses literal `100` for maximum name length. -> Define as a named constant `_MAX_EVENT_NAME_LENGTH = 100`.

[P3] [src/modules/events/service.py:181] Validation uses literal `100` for max limit. -> Define as a named constant.

[P3] [src/modules/events/service.py:468] Validation uses literal `500` for max leaderboard limit. -> Define as a named constant.

[P3] [src/modules/events/service.py:776] Validation uses literal `500` for max cancellation reason length. -> Define as a named constant.

### P3-05: Tests Use Injected Mocks
**Result:** PASS (no violations)

No `@mock.patch`, `@patch`, `mock.patch()`, `unittest.mock.patch`, or `monkeypatch.setattr` found in test files. All dependencies are injected through `__init__` using `AsyncMock` and `MagicMock`. Tests import from `tests.mocks.services` for `MockConfigService`, `MockErrorService`, `MockLogService`.

### P3-06: Test Naming Conventions
**Result:** PASS (no violations)

All test files use `test_` prefix. Test classes use `Test` prefix (e.g., `TestCreateEvent`, `TestJoinEvent`, `TestFinalizeEvent`). Test methods follow `test_{method}_{scenario}` pattern (e.g., `test_create_event_success`, `test_join_event_not_found`, `test_finalize_event_already_finalized`). No vague names like `test_it_works`.

### P3-07: Error Path Tests Exist
**Result:** PASS (all artifact error codes covered)

Mapping of artifact error codes to test coverage:

| Error Code | Test(s) |
|------------|---------|
| `NOT_FOUND_EVENT` | `test_get_event_not_found`, `test_join_event_not_found`, `test_leave_event_not_found`, `test_record_match_event_not_found`, `test_get_leaderboard_not_found`, `test_get_player_rank_event_not_found`, `test_get_event_participant_event_not_found`, `test_finalize_event_not_found`, `test_cancel_event_not_found`, `test_update_event_not_found` |
| `CONFLICT_EVENT_NOT_ACTIVE` | `test_join_event_not_active`, `test_record_match_event_not_active`, `test_finalize_event_wrong_status`, `test_record_match_max_matches_reached` |
| `CONFLICT_EVENT_ALREADY_FINALIZED` | `test_finalize_event_already_finalized`, `test_cancel_event_already_finalized` |
| `CONFLICT_ALREADY_PARTICIPANT` | `test_join_event_already_participant` |
| `FORBIDDEN_NOT_EVENT_PARTICIPANT` | `test_leave_event_not_participant`, `test_record_match_not_participant`, `test_get_player_rank_not_participant`, `test_get_event_participant_not_found` |
| `FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET` | `test_join_event_min_elo_requirement`, `test_join_event_max_elo_requirement`, `test_player_type_requirement_filter` |
| `FORBIDDEN_INSUFFICIENT_ENERGY` | `test_join_event_insufficient_energy` |
| `CONFLICT_EVENT_AT_CAPACITY` | `test_join_event_at_capacity`, `test_join_event_race_condition_rollback` |
| `FORBIDDEN_CANNOT_LEAVE_EVENT` | `test_leave_event_after_match_forbidden` |
| `VALIDATION_INVALID_INPUT` | `test_create_event_name_too_short`, `test_create_event_name_too_long`, `test_create_event_end_before_start`, `test_list_events_invalid_limit_low`, `test_list_events_invalid_limit_high`, `test_get_leaderboard_invalid_limit`, `test_get_player_events_invalid_limit`, `test_cancel_event_reason_too_long` |

No missing error path tests found.

### P3-08: Async Tests Properly Structured
**Result:** PASS (no violations)

All test methods that call async service methods are `async def test_...` with `@pytest.mark.asyncio`. Service calls are properly `await`ed. No `asyncio.run()` inside test methods.

### P3-09: Type Hints on Service Methods
**Result:** PASS (no violations)

All 15 public methods have full parameter and return type annotations. Private helper methods also have type hints. The `data_ctx` parameter is typed as `Any` (line 87) rather than `DataContextProtocol`, which is a minor deviation but not a violation since the artifact's `DataContextProtocol` is not used in the implementation (the implementation uses `data_ctx.redis` directly in `process_scheduled_events`).

---

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P1 | 0 | No framework rule violations |
| P2 | 0 | No data/config violations (1 Orchestrator escalation for config namespace) |
| P3 | 10 | 1 file length, 6 function length, 3 magic numbers groups |

### Escalation Items

- [ESCALATION] [P2-01] The `events` namespace with 12 config keys is not registered in `configuration.md` Section 2. The artifact declares these keys. Orchestrator should add `events` to the registered namespace table.

### Findings List

```
[P3] [src/modules/events/service.py:1-1237] Service file is 1237 lines (hard limit 500) -> Split into smaller files by extracting helpers and domain concerns.
[P3] [src/modules/events/service.py:659-772] finalize_event is 114 lines (limit 50) -> Extract reward distribution and top-player assembly.
[P3] [src/modules/events/service.py:464-536] get_leaderboard is 73 lines (limit 50) -> Extract entry assembly paths.
[P3] [src/modules/events/service.py:346-462] record_event_match is 117 lines (limit 50) -> Extract scoring and update logic.
[P3] [src/modules/events/service.py:208-297] join_event is 90 lines (limit 50) -> Extract capacity check and rollback.
[P3] [src/modules/events/service.py:774-834] cancel_event is 61 lines (limit 50) -> Extract energy refund loop.
[P3] [src/modules/events/service.py:863-941] process_scheduled_events is 79 lines (limit 50) -> Extract activation/deactivation/finalization loops.
[P3] [src/modules/events/service.py:1054-1062] Magic numbers in _calculate_level (5, 20, 50, 100) -> Define named constants or config.
[P3] [src/modules/events/service.py:127,134] Magic numbers for name length validation (3, 100) -> Define named constants.
[P3] [src/modules/events/service.py:181,468,776] Magic numbers for limit/length validation (100, 500, 500) -> Define named constants.
```
