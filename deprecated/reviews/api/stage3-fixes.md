# Stage 3 P1-P3 Compliance Fixes -- api module

Reviewer: Agent Karen
Date: 2026-02-07

---

## P1 -- Framework Rules

No P1 issues found. All seven checks pass:

- P1-01 No direct service instantiation: PASS (all `from src.core.*` imports are Protocol types under TYPE_CHECKING, AppError for catching, or type definitions)
- P1-02 No direct env access: PASS
- P1-03 No bare raises: PASS (`raise ValueError` in `schemas/match.py:42` is inside a Pydantic `model_validator` -- allowed)
- P1-04 No UI/rendering in modules: PASS (api module IS the presentation layer; HTTP response construction is its job)
- P1-05 No raw data access: PASS (grep matches are `@router.delete` decorators, not SQL)
- P1-06 Async matches artifact: PASS (all route handlers are `async def` per artifact section 4)
- P1-07 CLI exercises same code paths: PASS (`api_commands.py` uses `ApiFactory.create_app()` and uvicorn)

---

## P2 -- Data / Config

- P2-02 Repository pattern: N/A (api module owns no repositories)
- P2-03 Data ownership: PASS (api module owns no persistent data, per artifact section 6)
- P2-04 Transactions: N/A

### Escalation to Orchestrator

[P2] docs/guidance/configuration.md -- `api.*` config namespace is not registered in the namespace table, but the artifact (section 5.1) declares keys `api.host`, `api.port`, `api.cors_origins`, `api.rate_limit.requests_per_minute`, `api.rate_limit.burst_size`, `api.docs_enabled`, `api.bot_hints_enabled`. The code in `factory.py` and `middleware/rate_limit.py` uses these keys via the config service. The Orchestrator should add the `api` namespace to `docs/guidance/configuration.md` section 2.3 registered namespaces. This is NOT a code fix -- it is a guidance doc update.

---

## P3 -- Best Practices

### P3-01 File length (<=500 lines): PASS

All files are within limits. Largest files: `routes/matches.py` (422 lines), `websocket/handler.py` (430 lines).

### P3-02 Function length (<=50 lines): 4 FINDINGS

[P3] src/modules/api/routes/matches.py:216 `get_match_state` is 82 lines (limit 50) -- extract bot-hint building (lines 234-294) into a private helper `_build_bot_hints(state, player_id, request) -> dict | None`

[P3] src/modules/api/routes/matches.py:327 `submit_move` is 57 lines (limit 50) -- extract new-board dict construction (lines 352-369) into a private helper `_build_new_board_dict(result, player_id) -> dict | None`

[P3] src/modules/api/websocket/handler.py:121 `_authenticate` is 61 lines (limit 50) -- extract JSON parse + type check (lines 143-160) into `_parse_auth_message(raw) -> dict | None` that returns None on failure

[P3] src/modules/api/websocket/handler.py:258 `_handle_subscribe` is 52 lines (limit 50) -- marginal; extract match-channel subscription (lines 291-302) into `_subscribe_to_match_channel(player_id, params) -> str | None` error code

### P3-03 Constructor params (<=6): DEFERRED

`ApiFactory.__init__` takes 13 parameters. The artifact explicitly specifies all 13 (api is the terminal node that wires all module services). Deferred to artifact authority.

### P3-04 Magic numbers: PASS

Named constants used throughout (`_MAX_BEST_MOVES`, `_VOLATILE_THRESHOLD`, `_MODERATE_THRESHOLD`, etc. in `adapters/bot_hints.py`; config-driven thresholds in middleware).

### P3-05 Tests use injected mocks: PASS

No `@patch` or `monkeypatch` usage. All mocks injected via `app.state` in `conftest.py`.

### P3-06 Test naming: PASS

All test methods follow `test_<what>_<condition>` or `test_<what>_<expected_result>` convention.

---

## Summary

| Priority | Findings | Severity |
|----------|----------|----------|
| P1       | 0        | --       |
| P2       | 1 escalation (config namespace) | Low (guidance doc, not code) |
| P3       | 4 functions over 50-line limit | Low (readability) |

Recommendation: **Corrections needed** -- 4 function extractions in P3-02. Config namespace escalation to Orchestrator for guidance doc update.
