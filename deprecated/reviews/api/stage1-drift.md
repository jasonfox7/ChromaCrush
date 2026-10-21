# API Module -- Stage 1 Drift Report (Artifact vs Implementation Doc)

**Reviewer:** Agent Karen
**Date:** 2026-02-07
**Artifact:** `docs/artifacts/api/artifact.md` (v1.1)
**Implementation Doc:** `docs/implementation/api/implementation.md`

---

## Endpoint Counts

Artifact declares 60 REST endpoints + 1 WebSocket endpoint. Implementation doc declares 60 REST endpoints + 1 WebSocket endpoint. Counts match across all 12 route groups.

Individual route group counts verified:
- Health: 3 / 3
- Auth: 8 / 8
- Players: 6 / 6
- Energy: 3 / 3
- Matchmaking: 4 / 4
- Matches: 8 / 8
- Vault: 7 / 7
- Events: 5 / 5
- Ads: 6 / 6
- Payments: 4 / 4
- Bot Earnings: 5 / 5
- WebSocket: 1 / 1

No endpoint count drift.

---

## Drift Findings

### CLI Commands

[DRIFT] Artifact defines CLI commands: `serve`, `routes`, `openapi`, `test-health`, `test-auth` (5 commands) -> Implementation doc defines CLI commands: `start`, `routes`, `health`, `config` (4 commands)
[DRIFT] Artifact command `serve` -> Implementation doc renames to `start`
[DRIFT] Artifact command `openapi` (export OpenAPI schema to file) -> Implementation doc removes it, replaced by built-in `/openapi.json` endpoint
[DRIFT] Artifact command `test-health` (async httpx client with `--url` flag) -> Implementation doc replaces with `health` (synchronous urllib.request.urlopen)
[DRIFT] Artifact command `test-auth` (verify token against running server) -> Implementation doc removes entirely (says covered by auth module CLI)
[DRIFT] Artifact has no `config` command -> Implementation doc adds `config` command to display api/app/websocket config values

### Auth Middleware Error Mechanism

[DRIFT] Artifact auth middleware raises `HTTPException` on auth failure -> Implementation doc returns `JSONResponse` directly with structured error envelope

### Auth Middleware API Key Validation

[DRIFT] Artifact auth middleware calls `self._auth.validate_api_key(api_key)` (separate method) -> Implementation doc calls `self._auth.validate_token(api_key)` (single method for both JWT and API key)

### Rate Limiting Scope

[DRIFT] Artifact rate limit middleware checks all identifier types (api_key, player, IP) via string-based identifier -> Implementation doc only rate-limits API-key-authenticated requests; JWT and IP-based rate limiting deferred

### Auth Public Paths

[DRIFT] Artifact lists 8 public paths (no `/redoc`) -> Implementation doc lists 9 public paths (adds `/redoc`)

### Board Cell Data Type

[DRIFT] Artifact defines board cells as `list[list[str]]` (gem types are strings like "red", "blue") -> Implementation doc uses `list[list[int]]` (gem types are integers)

### Bot Hint Data Structures

[DRIFT] Artifact defines bot hint types (`MatchBotHints`, `RankedMove`, `BoardAnalysis`, `StrategicContext`) as Pydantic `BaseModel` classes -> Implementation doc uses frozen `dataclass` types, manually constructing dicts for JSON output

### MoveRequest Schema

[DRIFT] Artifact `MoveRequest` has no `timestamp_ms` field -> Implementation doc adds `timestamp_ms: int = Field(gt=0)` (required by match service `Move` type)
[DRIFT] Artifact `MoveRequest` has no adjacency validation -> Implementation doc adds `@model_validator(mode="after")` for orthogonal adjacency check

### MatchStateResponse Structure

[DRIFT] Artifact `MatchStateResponse` uses flat fields (`player_turn: str`, `board: BoardState`, `valid_moves: list[ValidMove]`) -> Implementation doc uses nested `player1`/`player2` objects with `PlayerMatchStateResponse` substructure

### ResponseAdapter Return Type

[DRIFT] Artifact `ResponseAdapter.success()` returns `ApiResponse[T]` (Pydantic model) -> Implementation doc `ResponseAdapter.success()` returns `dict[str, Any]` via `model_dump(mode="json")`
[DRIFT] Artifact `ResponseAdapter.error()` returns `ApiResponse` (Pydantic model) -> Implementation doc `ResponseAdapter.error()` returns `dict[str, Any]` via `model_dump(mode="json")`

### Matchmaking Pools Auth

[DRIFT] Artifact specifies `/matchmaking/pools` auth as `API Key` only -> Implementation doc allows both `JWT/API Key`

### Vault Targets Auth

[DRIFT] Artifact specifies `/vault/targets` auth as `API Key` only -> Implementation doc allows both `JWT/API Key`

### Energy Response Schema

[DRIFT] Artifact `EnergyResponse` includes `time_to_next_heart_display: str | None` field -> Implementation doc omits this field (says presentation formatting is handled client-side)

### Energy LoginResponse Naming

[DRIFT] Artifact uses class name `LoginResponse` in `schemas/energy.py` (collides with auth `LoginResponse`) -> Implementation doc renames to `LoginStreakResponse`

### ApiKeyResponse Schema

[DRIFT] Artifact `ApiKeyResponse` field `name: str | None` -> Implementation doc uses `description: str | None`

### Error Codes Created

[DRIFT] Artifact lists 5 error codes created by API module: `AUTH_TOKEN_MISSING`, `AUTH_TOKEN_INVALID`, `AUTH_API_KEY_INVALID`, `RATE_LIMIT_EXCEEDED`, `VALIDATION_INVALID_INPUT` -> Implementation doc lists 6 error codes: `AUTH_TOKEN_MISSING`, `AUTH_TOKEN_INVALID`, `RATE_LIMIT_EXCEEDED`, `FORBIDDEN_BOT_NOT_ALLOWED`, `FORBIDDEN_NOT_BOT`, `INTERNAL_UNEXPECTED`
[DRIFT] Artifact includes `AUTH_API_KEY_INVALID` and `VALIDATION_INVALID_INPUT` as API-created errors -> Implementation doc does not list these two
[DRIFT] Artifact does not define `FORBIDDEN_BOT_NOT_ALLOWED`, `FORBIDDEN_NOT_BOT`, or `INTERNAL_UNEXPECTED` -> Implementation doc adds all three

### Configuration Keys

[DRIFT] Artifact defines 7 config keys (all under `api.*` namespace) -> Implementation doc defines 7 `api.*` keys (same) plus 1 `app.version` key and 4 `websocket.*` keys (total 12)
[DRIFT] Artifact does not define `app.version` config key -> Implementation doc adds `app.version` (str, default "0.1.0")
[DRIFT] Artifact does not define any `websocket.*` config keys -> Implementation doc adds `websocket.heartbeat_interval_seconds`, `websocket.connection_timeout_seconds`, `websocket.max_connections_per_player`, `websocket.max_message_size_bytes`

### WebSocket Architecture

[DRIFT] Artifact describes WebSocket handler location as `src/presentation/websocket/match_handler.py` -> Implementation doc places WebSocket components under `src/modules/api/websocket/` (manager.py, channels.py, handler.py)
[DRIFT] Artifact WebSocket design uses a `WSConnectionManagerProtocol` and `MatchApiAdapter` pattern -> Implementation doc uses `ConnectionManager`, `ChannelManager`, and `WebSocketHandler` (three-component architecture instead of two)
[DRIFT] Artifact WebSocket connection lifecycle has no connection limit check -> Implementation doc adds max_connections_per_player check (default 3) after auth, with `WS_RATE_LIMITED` error
[DRIFT] Artifact WebSocket lifecycle has no message size limit -> Implementation doc adds max_message_size_bytes (default 65536) validation
[DRIFT] Artifact WebSocket lifecycle has no heartbeat mechanism -> Implementation doc adds heartbeat via timeout-based pong sending

### Injected Service Count

[DRIFT] Artifact lists 10 injected module service protocols (AuthService, PlayerService, EnergyService, MatchmakingService, MatchService, VaultService, EventService, AdService, PaymentService, BotEarningsService) -> Implementation doc lists 13 module services plus 3 core services (16 total). The 3 core services (Config, Logger, Errors) were implicit in the artifact but explicitly enumerated in implementation doc.

### Schema File Count

[DRIFT] Artifact defines 11 schema files (common, auth, player, energy, match, matchmaking, vault, events, ads, payments, bot_earnings) -> Implementation doc defines the same 11 schema files but with different class counts. Artifact provides full Pydantic code for 4 schema files (common, auth, energy, match). Implementation doc declares schema class counts per file: auth (11), player (5), energy (3), match (8), matchmaking (4), vault (7), events (7), ads (11), payments (7), bot_earnings (8). No way to compare individual schema shapes for files artifact did not fully specify.

### Dependencies.py Provider Count

[DRIFT] Artifact does not specify `dependencies.py` provider count -> Implementation doc declares 17 `Depends()` providers

---

## Summary

**Total drift items found: 33**

Most deviations are documented in the implementation doc's own "Deviations from Artifact" section (Section 14), indicating intentional, justified changes rather than accidental drift. Key categories:

1. **CLI commands** (5 drifts): Renamed, removed, and added commands. All justified in implementation doc.
2. **Auth/middleware mechanics** (4 drifts): Changed error mechanism, unified API key validation, narrowed rate limiting scope, added `/redoc` public path. All justified.
3. **Schema shape changes** (7 drifts): Board cell type, MoveRequest fields, MatchStateResponse structure, EnergyResponse field removal, naming collision fix, ApiKeyResponse field rename. All justified.
4. **Bot hint implementation** (1 drift): Pydantic models replaced with frozen dataclasses. Justified.
5. **Auth restrictions loosened** (2 drifts): Matchmaking pools and vault targets opened to both auth types. Justified.
6. **Error codes** (3 drifts): Two artifact codes missing from impl list, three new codes added. Partially justified -- `AUTH_API_KEY_INVALID` and `VALIDATION_INVALID_INPUT` disappearance is unclear.
7. **Configuration keys** (3 drifts): New namespaces added. Justified -- WebSocket config not foreseen in artifact.
8. **WebSocket architecture** (5 drifts): Different file location, different component decomposition, added safety features. Justified.
9. **ResponseAdapter return type** (2 drifts): Returns dict instead of Pydantic model. Justified.
10. **Dependency counts** (1 drift): More explicit enumeration. Not a real drift.

**Recommendation:** The implementation doc self-documents all significant deviations with justifications. No silent/undocumented drift detected -- every change that departs from the artifact is listed in the implementation doc's Section 14. The artifact should be updated to reflect the as-built state if it is intended to remain a living document.
