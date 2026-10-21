# Stage 3 P1-P3 Fixes -- match module

**Reviewer:** Karen P1-P3 (Stage 3)
**Date:** 2026-02-07
**Module:** match
**Source files reviewed:** service.py, types.py, protocols.py, dto.py, __init__.py
**Test files reviewed:** test_match_service.py
**CLI file reviewed:** match_commands.py
**Artifact:** docs/artifacts/match/artifact.md

---

## P1 -- Framework Rules

### P1-01: No Direct Service Instantiation
PASS. No matches for `from src.core.config import`, `ConfigService(`, `LogService(`, `ErrorService(`, `DataContext(` in `src/modules/match/`.

### P1-02: No Direct Environment Access
PASS. No matches for `os.environ`, `os.getenv`, or `import os` in `src/modules/match/`.

### P1-03: No Bare Raises
**[P1] [src/modules/match/types.py:112] `raise ValueError(f"Player {player_id} not in this match")` in `MatchState.get_player_state()` -- bare raise bypassing error taxonomy -> Replace with AppError or refactor to return Optional and let the caller (service.py) raise through ErrorService.**

**[P1] [src/modules/match/types.py:130] `raise ValueError(f"Player {player_id} not in this match")` in `MatchState.get_opponent_state()` -- same bare raise issue -> Same fix as above.**

Note: These are NOT `__post_init__` validators on frozen dataclasses (which would be exempt). They are regular methods on a `@dataclass(frozen=True)` class used at runtime for business logic lookups. The checklist exempts only `__post_init__` validators.

### P1-04: No UI / Rendering Logic in Modules
PASS. No matches for `import click`, `from rich`, `print(`, `sys.stdout`, `sys.stderr`, or any UI imports.

### P1-05: No Raw Data Access in Business Logic
PASS. The only matches for `update(` are repository protocol calls (`self._match_repo.update(...)`) -- this is correct usage through injected repository interfaces, not raw data access.

### P1-06: Async Matches Artifact Spec
PASS. All public methods (`create_match`, `submit_move`, `get_match`, `get_match_state`, `get_player_board`, `get_active_matches`, `forfeit_match`, `get_match_history`, `get_move_history`, `abandon_stale_matches`) are `async def`. No `asyncio.run()` or `asyncio.create_task()` in module source.

### P1-07: CLI Exercises Same Code Paths
PASS. CLI commands in `match_commands.py` call service methods (`service.create_match(...)`, `service.submit_move(...)`, etc.). Repository instantiation is in the CLI wiring function `_build_services()`, which is presentation-layer code (allowed). No business logic is duplicated in CLI.

---

## P2 -- Data Layer & Config Compliance

### P2-01: Config Keys Match Registered Namespaces
**[P2] [src/modules/match/service.py:107-112] Config keys under `match.*` namespace (`match.moves_per_player`, `match.timeout_hours`, `match.energy_cost`, `match.allow_concurrent`, `match.max_concurrent`, `match.deadlock_reshuffle`) are NOT in the registered namespace table in configuration.md. The artifact declares these keys. -> Orchestrator escalation: add `match` namespace to configuration.md. Flag but do not block.**

Note: The artifact also lists `game.board_width` and `game.board_height` as config keys, but the match service does not directly read them (board_gen_service handles board dimensions). This is correct delegation, not a gap.

### P2-02: Repository Pattern Followed
PASS. Service receives `match_repository: MatchRepositoryProtocol` and `match_move_repository: MatchMoveRepositoryProtocol` via `__init__`. All data access goes through `self._match_repo.*` and `self._move_repo.*`. No direct SQLAlchemy/Redis imports in service.py.

### P2-03: Data Ownership Respected
PASS. Match module writes only to its owned tables (matches, match_moves) via its own repositories. Cross-module data (players, energy) accessed through injected service protocols (`player_service`, `energy_service`).

### P2-04: Transactions at Service Layer
PASS. No `.commit()` or `.rollback()` found in module source files. Transaction boundaries are managed at the service layer via repository protocol calls.

---

## P3 -- Best Practices & Testing

### P3-01: Service File Length
**[P3] [src/modules/match/service.py] 1196 lines -- exceeds the 500-line hard limit by 696 lines (139% over). -> Refactor by extracting private helpers (_build_match_state, _derive_move_seed, _derive_reshuffle_seed, _generate_seed, _finalize_match) into a `_helpers.py` file (similar to the ads module pattern). Consider also extracting the submit_move orchestration into a separate method or helper class.**

### P3-02: Function Length
**[P3] [src/modules/match/service.py:255-555] `submit_move` is approximately 300 lines (including docstring ~25 lines, so ~275 lines of code). Exceeds the 50-line limit by 5x. -> Break into smaller private methods: `_validate_move_preconditions()`, `_process_move_on_board()`, `_handle_match_completion()`, `_persist_move_record()`.**

**[P3] [src/modules/match/service.py:811-902] `get_match_history` is approximately 91 lines. Exceeds the 50-line limit. -> Extract the MatchSummary building loop (lines 850-895) into a private `_build_match_summary()` helper.**

**[P3] [src/modules/match/service.py:720-805] `forfeit_match` is approximately 85 lines. Exceeds the 50-line limit. -> Some of this is validation boilerplate shared with `submit_move`; consider a shared `_validate_match_access()` helper.**

**[P3] [src/modules/match/service.py:1123-1196] `_finalize_match` is approximately 73 lines. Exceeds the 50-line limit. -> Extract ELO calculation logic into a separate `_apply_elo_changes()` helper.**

**[P3] [src/modules/match/service.py:1011-1079] `_build_match_state` is approximately 68 lines. Exceeds the 50-line limit. -> This is a data mapping method; consider extracting `_build_player_match_state()` for each player.**

### P3-03: Constructor Parameters
**[P3] [src/modules/match/service.py:76-91] Constructor has 13 parameters. Artifact specifies 12 (without `match_move_repository`). The added parameter is justified (move history needs its own repository) but exceeds both the 6-param soft limit and the artifact's specified count. -> Document the deviation. Consider bundling repositories into a `MatchRepositoryBundle` (similar to ads module's `AdRepositoryBundle`) to reduce parameter count.**

### P3-04: No Magic Numbers
**[P3] [src/modules/match/service.py:1097] Magic number `1103515245` in `_derive_move_seed()` -- LCG constant without explanation. -> Add a named constant `_LCG_MULTIPLIER = 1103515245` with a comment explaining it's a Linear Congruential Generator constant.**

**[P3] [src/modules/match/service.py:1112] Magic number `12345` in `_derive_reshuffle_seed()`. -> Add a named constant `_RESHUFFLE_MULTIPLIER = 12345`.**

**[P3] [src/modules/match/service.py:833] Magic number `100` for pagination limit max. -> Add a named constant `_MAX_PAGINATION_LIMIT = 100` or read from config.**

### P3-05: Tests Use Injected Mocks
PASS. No `@mock.patch`, `@patch`, `mock.patch()`, or `monkeypatch.setattr` found in test files. All dependencies are created via `AsyncMock`/`MagicMock` and injected through `__init__`.

### P3-06: Test Naming Conventions
PASS. All test methods follow `test_{method}_{scenario}` pattern (e.g., `test_create_match_success`, `test_submit_move_match_not_found`). Test classes follow `Test{ClassName}` pattern. No vague test names.

### P3-07: Error Path Tests Exist
Error codes tested in test_match_service.py:
- VALIDATION_INVALID_INPUT -- tested (lines 380-384, 1325-1337)
- NOT_FOUND_PLAYER -- tested (lines 391-418)
- NOT_FOUND_MATCH -- tested (lines 661-669, 1014-1019, 1124-1129, 1252-1257, 1429-1434)
- FORBIDDEN_NOT_MATCH_PARTICIPANT -- tested (lines 676-685, 1050-1060, 1135-1143, 1263-1271)
- CONFLICT_MATCH_ALREADY_COMPLETED -- tested (lines 692-715, 1277-1287, 1813-1823)
- VALIDATION_NO_MOVES_REMAINING -- tested (lines 722-731)
- VALIDATION_INVALID_GEM_SWAP -- tested (lines 738-747)
- FORBIDDEN_INSUFFICIENT_ENERGY -- tested (lines 458-483)
- CONFLICT_CONCURRENT_MATCH -- tested (lines 421-455) (note: code uses `CONFLICT_CONCURRENT_MATCH`, artifact says `CONFLICT_PLAYER_IN_MATCH` -- this is a P0 issue already tracked in Stage 2)

Missing error path tests:
- VALIDATION_POSITIONS_NOT_ADJACENT -- not tested (this error is raised by the board service, not match service directly; propagated unchanged)
- VALIDATION_OUT_OF_BOUNDS -- not tested (same: raised by board service)
- CONFLICT_MATCH_NOT_IN_PROGRESS -- not directly tested (the test for status=abandoned implicitly covers this via CONFLICT_MATCH_ALREADY_COMPLETED, but the specific NOT_IN_PROGRESS code path for statuses other than completed/abandoned/pending/in_progress is not exercised)
- INTERNAL_DATABASE_ERROR -- not tested (framework-level error wrapping)

Note: The missing tests are for errors that propagate from dependency services or are framework-level. This is acceptable per checklist guidance ("having ONE test is acceptable" and propagated errors from dependencies are lower priority).

### P3-08: Async Tests Properly Structured
PASS. All test methods are `async def test_*`. Service calls are properly `await`ed. No `asyncio.run()` in test methods. Tests use pytest-asyncio auto mode.

### P3-09: Type Hints on Service Methods
PASS. All public service methods have full parameter and return type hints. Private methods also have type hints. One minor note: `_build_match_state` uses `object` type for `match_record`, `player1`, `player2` parameters (line 1011-1015) with `# type: ignore[attr-defined]` comments throughout -- consider using a proper protocol or TypeVar, but this is cosmetic.

---

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P1 | 2 | Bare `raise ValueError` in types.py (lines 112, 130) |
| P2 | 1 | Config namespace `match.*` not in registered namespaces (Orchestrator escalation) |
| P3 | 10 | File length (1), function lengths (5), constructor params (1), magic numbers (3) |
| **Total** | **13** | |

### Recommendation
Corrections needed. The 2 P1 findings must be fixed in Stage 4. The P2 config namespace finding is an Orchestrator escalation item. The P3 findings are quality improvements; the file length and function length issues are the most impactful.
