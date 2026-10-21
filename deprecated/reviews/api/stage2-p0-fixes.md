# API Module -- Stage 2 P0 Fix Report

**Reviewer:** Agent Karen
**Date:** 2026-02-07
**Module:** api
**Scope:** Protocol signatures, error codes, type usage, HTTP status mapping, response envelope shape

---

## P0 Issues

### Error Code Issues

[P0] [src/modules/api/middleware/auth.py:76] `AUTH_TOKEN_MISSING` is not in the error taxonomy -> Should use `AUTH_TOKEN_INVALID` (defined in interface-contracts.md Section 2.2 Authentication Errors) with message "Authentication required". The code `AUTH_TOKEN_MISSING` does not exist in the error taxonomy. The closest match is `AUTH_TOKEN_INVALID` with a contextual `reason` field.

[P0] [src/modules/api/routes/ads.py:69] `FORBIDDEN_BOT_NOT_ALLOWED` is not in the error taxonomy -> Should use `FORBIDDEN_NOT_BOT` (for requiring bot status) or a more descriptive code. The taxonomy has `FORBIDDEN_NOT_BOT` meaning "Action requires bot account" but the inverse case (human-only endpoint blocking bots) has no dedicated code. Recommend using `FORBIDDEN_NOT_BOT` with an inverted message, or escalating to Orchestrator to add `FORBIDDEN_BOT_NOT_ALLOWED` to the taxonomy. This same issue appears in `src/modules/api/routes/payments.py:61`.

[P0] [src/modules/api/routes/payments.py:61] `FORBIDDEN_BOT_NOT_ALLOWED` is not in the error taxonomy -> Same as ads.py issue above. This code is used in the `_require_jwt` helper and does not appear in interface-contracts.md Section 2.2.

### Response Envelope Inconsistency

[P0] [src/modules/api/middleware/auth.py:129-136] Auth middleware error response uses `"meta": None` -> Should include `"meta": {"correlation_id": ..., "timestamp": ..., "version": "1.0"}` to match the envelope shape produced by the error handler (error_handler.py lines 62-78) and the ApiResponse schema (schemas/common.py). The auth middleware fires before correlation middleware has a chance to set the correlation ID, but it should still produce a consistent envelope. Currently the auth middleware omits `correlation_id` and `timestamp` from the `meta` field entirely, which violates the ApiResponse contract where `meta: ResponseMeta` is non-optional.

[P0] [src/modules/api/middleware/rate_limit.py:130-146] Rate limit middleware error response uses `"meta": None` -> Same issue as auth middleware. Should include `"meta": {"correlation_id": ..., "timestamp": ..., "version": "1.0"}` for envelope consistency with the ApiResponse schema. The rate limit middleware fires after correlation middleware, so `request.state.correlation_id` should be available here.

### Contract Error Response Shape Mismatch

[P0] [src/modules/api/middleware/error_handler.py:62-78 vs interface-contracts.md:346-353] Error response envelope shape differs from `AppError.to_dict()` contract -> The interface contract (Section 2.1) defines `AppError.to_dict()` as `{"error": {"code", "message", "correlation_id", "timestamp"}}`. The error handler instead produces `{"success", "data", "error": {"code", "message", "details"}, "meta": {"correlation_id", "timestamp", "version"}}`. The error handler uses a richer envelope (matching ApiResponse schema), which is defensible as a presentation-layer concern, but `correlation_id` and `timestamp` are in `meta` instead of inside `error`. This is a structural contract deviation. Since the ApiResponse schema in schemas/common.py is the api module's own contract and is applied consistently across success and error responses, this should be acknowledged as an intentional presentation-layer adaptation. **Recommendation:** Not a fix-required issue if the Orchestrator confirms the api module's envelope is the authoritative response shape. Escalate for clarification.

---

## Non-P0 Observations (Documented for Completeness)

1. **events.py:191** -- Bare `except Exception:` swallows all errors when looking up player event participation for leaderboard rank. If the player is not a participant, an `AppError` (NOT_FOUND) is expected, but the catch also silently swallows database errors, internal errors, etc. This is not a P0 protocol/type issue but should be narrowed to `except AppError:`.

2. **matches.py:357-368** -- The `submit_move` endpoint calls `result.match_state.get_player_state()` four times redundantly to extract `moves_made` and `score`. While functionally correct, the repeated calls are inefficient. Not a P0 issue.

3. **dependencies.py:249-261** -- `get_current_player_id` returns `str` rather than `PlayerId`. Every route that needs a `PlayerId` manually wraps it via `PlayerId(UUID(str(player_id)))`. This is consistently applied but diverges from the contract's type-safe `PlayerId` usage. Not a P0 issue (the conversion is handled at the boundary).

---

## P0 Summary

| # | File | Line | Issue | Fix |
|---|------|------|-------|-----|
| 1 | middleware/auth.py | 76 | `AUTH_TOKEN_MISSING` not in taxonomy | Use `AUTH_TOKEN_INVALID` with reason context |
| 2 | routes/ads.py | 69 | `FORBIDDEN_BOT_NOT_ALLOWED` not in taxonomy | Use existing taxonomy code or escalate to add |
| 3 | routes/payments.py | 61 | `FORBIDDEN_BOT_NOT_ALLOWED` not in taxonomy | Same as #2 |
| 4 | middleware/auth.py | 129-136 | `"meta": None` breaks ApiResponse envelope | Populate meta with correlation_id and timestamp |
| 5 | middleware/rate_limit.py | 130-146 | `"meta": None` breaks ApiResponse envelope | Populate meta with correlation_id and timestamp |
| 6 | middleware/error_handler.py | 62-78 | Envelope shape differs from AppError.to_dict() | Escalate: confirm api envelope is authoritative |

**Total P0 issues: 6** (5 actionable fixes + 1 escalation for clarification)
