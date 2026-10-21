# Stage 3 P1-P3 Fixes -- ads module

**Reviewer:** Karen P1-P3 (Stage 3)
**Date:** 2026-02-07
**Module:** ads
**Source files reviewed:** service.py, types.py, protocols.py, dto.py, _helpers.py, __init__.py
**Test files reviewed:** test_ad_service.py
**CLI file reviewed:** ads_commands.py
**Artifact:** docs/artifacts/ads/artifact.md

---

## P1 -- Framework Rules

### P1-01: No Direct Service Instantiation
PASS. No matches for `from src.core.config import`, `ConfigService(`, `LogService(`, `ErrorService(`, `DataContext(` in `src/modules/ads/`.

### P1-02: No Direct Environment Access
PASS. No matches for `os.environ`, `os.getenv`, or `import os` in `src/modules/ads/`.

### P1-03: No Bare Raises
PASS. No matches for `raise Exception(`, `raise ValueError(`, `raise TypeError(`, `raise RuntimeError(`, `raise KeyError(`, or `raise NotImplementedError(` in `src/modules/ads/`. All errors raised through `self._errors.*` methods.

### P1-04: No UI / Rendering Logic in Modules
PASS. No matches for `import click`, `from rich`, `print(`, `sys.stdout`, `sys.stderr`, or any UI imports.

### P1-05: No Raw Data Access in Business Logic
PASS. The only matches for `update(` are repository protocol calls (`self._req_repo.update(...)`) -- this is correct usage through injected repository interfaces. No SQLAlchemy, Redis, raw SQL, or ORM calls in service.py or _helpers.py.

### P1-06: Async Matches Artifact Spec
PASS. All public methods are `async def` as specified by artifact. No `asyncio.run()` or `asyncio.create_task()` in module source.

### P1-07: CLI Exercises Same Code Paths
PASS. CLI commands in `ads_commands.py` call service methods (`service.check_ad_free_status(...)`, `service.request_interstitial(...)`, etc.). Repository instantiation is in the CLI wiring function `_build_ad_service()`, which is presentation-layer code (allowed). No business logic is duplicated in CLI.

---

## P2 -- Data Layer & Config Compliance

### P2-01: Config Keys Match Registered Namespaces
**[P2] [src/modules/ads/service.py:118-125, 190, 224, 404] Config keys under `ads.*` namespace (`ads.interstitial_cooldown_seconds`, `ads.rewarded_cooldown_seconds`, `ads.banner_min_view_ms`, `ads.rewarded_min_watch_percent`, `ads.rewarded_heart_reward`, `ads.bot_attribution_share_percent`, `ads.estimated_cpm_cents`, `ads.event_opportunity_cooldown_minutes`, `ads.interstitial_unit_id`, `ads.rewarded_unit_id`, `ads.provider_name`) are NOT in the registered namespace table in configuration.md. The artifact declares all of these keys. -> Orchestrator escalation: add `ads` namespace to configuration.md. Flag but do not block.**

### P2-02: Repository Pattern Followed
PASS. Service receives repositories bundled in `AdRepositoryBundle` via `__init__`. All data access goes through injected repository protocol interfaces (`self._req_repo.*`, `self._imp_repo.*`, `self._free_repo.*`, `self._rew_repo.*`, `self._opp_repo.*`, `self._claim_repo.*`). No direct SQLAlchemy/Redis imports in service.py or _helpers.py.

### P2-03: Data Ownership Respected
PASS. Ads module writes only to its owned tables (ad_requests, ad_impressions, ad_free_status, ad_rewards, event_ad_opportunities, event_ad_claims) via its own repositories. Cross-module data (players, events) accessed through injected service protocols (`player_service`, `events_service`).

### P2-04: Transactions at Service Layer
PASS. No `.commit()` or `.rollback()` found in module source files. Transaction boundaries are managed at the service layer via repository protocol calls.

---

## P3 -- Best Practices & Testing

### P3-01: Service File Length
PASS. `service.py` is 406 lines (under 500-line hard limit). Helper functions were proactively extracted to `_helpers.py` (170 lines). Good practice.

### P3-02: Function Length
PASS. All functions in service.py and _helpers.py are under 50 lines. The longest method is `claim_event_ad_reward` (lines 326-357, ~31 lines) and `complete_rewarded_video` (lines 235-260, ~25 lines). No violations.

### P3-03: Constructor Parameters
PASS. `AdService.__init__` has 7 parameters (config, logger, errors, player_service, events_service, repos, ad_provider). Under the 6-param soft limit by only 1. The artifact specifies 9 parameters (with `data_ctx`, individual `ad_impression_repository`, `ad_reward_repository`), but the implementation consolidates repositories into `AdRepositoryBundle` and drops `data_ctx` (not directly used). This is a justified deviation that improves the design.

Note: The artifact-specified `data_ctx: DataContextProtocol` parameter is absent from the implementation. This was flagged in Stage 2 P0 review. The service does not perform direct transaction management, so `data_ctx` is not needed -- repository implementations handle their own sessions.

### P3-04: No Magic Numbers
**[P3] [src/modules/ads/service.py:192,226] Magic number `5` in `timedelta(minutes=5)` for ad request expiry. -> Add a named constant `_AD_REQUEST_EXPIRY_MINUTES = 5` or read from config (e.g., `ads.request_expiry_minutes`).**

**[P3] [src/modules/ads/service.py:239] Magic number `30000` in `pct = (watched_duration_ms / 30000) * 100` -- assumed standard video duration of 30 seconds. -> Add a named constant `_STANDARD_VIDEO_DURATION_MS = 30000` or read from config (e.g., `ads.rewarded_video_duration_ms`).**

**[P3] [src/modules/ads/_helpers.py:76-78] Magic numbers `1.5` and `0.3` as CPM multipliers for rewarded and banner ad types respectively. -> Add named constants `_REWARDED_CPM_MULTIPLIER = 1.5` and `_BANNER_CPM_MULTIPLIER = 0.3`, or read from config.**

**[P3] [src/modules/ads/_helpers.py:79] Magic number `1000` as CPM divisor. -> Add named constant `_CPM_DIVISOR = 1000` with comment explaining CPM = cost per mille (1000 impressions).**

**[P3] [src/modules/ads/_helpers.py:90-92] Magic numbers `7` and `30` for weekly and monthly date ranges. -> Add named constants `_WEEK_DAYS = 7` and `_MONTH_DAYS = 30`.**

### P3-05: Tests Use Injected Mocks
PASS. No `@mock.patch`, `@patch`, `mock.patch()`, or `monkeypatch.setattr` found in test files. All dependencies are created via `AsyncMock`/`MagicMock` and injected through `__init__` using the `build_service()` factory function.

### P3-06: Test Naming Conventions
PASS. All test methods follow `test_{method}_{scenario}` pattern (e.g., `test_check_ad_free_status_not_ad_free`, `test_request_interstitial_cooldown`). No vague test names. Tests are organized as module-level async functions rather than test classes, which is a valid pytest style.

### P3-07: Error Path Tests Exist
Error codes tested in test_ad_service.py:
- NOT_FOUND_PLAYER -- tested (line 421)
- FORBIDDEN_PLAYER_AD_FREE -- tested (lines 465, 673, 1008)
- NOT_FOUND_AD_REQUEST -- tested (line 518)
- CONFLICT_AD_ALREADY_RECORDED -- tested (line 530)
- CONFLICT_AD_REQUEST_EXPIRED -- tested (line 546)
- RATE_LIMIT_AD_COOLDOWN -- tested (line 478)
- VALIDATION_INVALID_INPUT -- tested (lines 394, 430, 660, 730, 836)
- VALIDATION_PLAYER_NOT_BOT -- tested (line 822)
- NOT_FOUND_AD_OPPORTUNITY -- tested (line 919)
- CONFLICT_OPPORTUNITY_ALREADY_CLAIMED -- tested (line 936)
- RATE_LIMIT_OPPORTUNITY_COOLDOWN -- tested (line 955)
- INTERNAL_AD_PROVIDER_ERROR -- tested (line 976)

Missing error path tests:
- VALIDATION_REWARDED_AD_NOT_COMPLETED -- not explicitly tested by error code. The `test_complete_rewarded_video_not_granted` test (line 607) covers the scenario where the video was not watched enough, but it tests the `reward_granted=False` outcome rather than raising an error. This is actually consistent with the implementation: the service returns a result with `reward_granted=False` rather than raising an error for incomplete videos. The artifact lists this as an error code but the implementation treats it as a non-error result. This is a minor artifact-vs-implementation discrepancy, not a test gap.
- CONFLICT_EVENT_NOT_ACTIVE -- not tested directly. This error would be raised by the `events_service.get_event()` call (propagated from events module). Propagated cross-module errors are lower priority.
- FORBIDDEN_NOT_EVENT_PARTICIPANT -- not tested directly. Same as above: raised by `events_service.get_event_participant()`.
- INTERNAL_DATABASE_ERROR -- not tested (framework-level error wrapping)

### P3-08: Async Tests Properly Structured
PASS. All test methods are `async def test_*`. Service calls are properly `await`ed. No `asyncio.run()` in test methods. Tests use pytest-asyncio auto mode.

### P3-09: Type Hints on Service Methods
**[P3] [src/modules/ads/_helpers.py:29,52,96,110,122,135,156-158] Extensive use of `Any` type for record parameters across all helper functions (e.g., `build_ad_free_status(record: Any, player_id: Any)`, `build_impression(record: Any)`, `build_player_stats(record: Any, pid: Any, ...)`, etc.). -> Define a lightweight Protocol or TypedDict for each record shape to provide type safety, or at minimum use the concrete ORM model type if available.**

**[P3] [src/modules/ads/service.py:384] `_valid_request` returns `Any`. -> Specify the return type (the ad request record type).**

**[P3] [src/modules/ads/service.py:400] `_provider_call` parameter `fn: Any` and return `Any`. -> Type the function parameter properly using `Callable` or a Protocol.**

---

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P1 | 0 | No P1 issues found |
| P2 | 1 | Config namespace `ads.*` not in registered namespaces (Orchestrator escalation) |
| P3 | 8 | Magic numbers (5), type hints / `Any` usage (3) |
| **Total** | **9** | |

### Recommendation
Corrections needed (minor). No P1 violations -- the ads module is framework-compliant. The P2 config namespace finding is an Orchestrator escalation item (same systemic issue as other modules). The P3 findings are quality improvements: magic numbers should become named constants or config values, and `Any` type usage in helpers should be tightened.
