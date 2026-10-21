# API Module Implementation Document

**Module:** api
**Phase:** 2.2
**Author:** Coding Agent
**Date:** 2026-02-07

---

## 1. Summary

The API module is the **terminal node** of the ChromaCrush dependency graph, exposing all game functionality via REST endpoints and WebSocket real-time updates. It is a pure presentation layer: it owns no persistent data, performs no business logic, and delegates all operations to 13 injected module services (plus 3 core services). The tech stack consists of FastAPI (ASGI framework with auto-generated OpenAPI), Pydantic v2 (request/response validation and serialization), Starlette middleware (CORS, correlation, auth, rate limiting), and native WebSocket support.

All route handlers are `async def` because they await injected service method calls. Response formatting and bot hint generation are synchronous pure computations that run after service calls return.

The module is designed **bot-first**: all responses use a consistent JSON envelope, bot players receive strategic hints in match state responses, and API key authentication is a first-class auth path alongside JWT.

## 2. Files Created

### Module Code (`src/modules/api/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Exports `ApiFactory` and `ApiFactoryProtocol` |
| `factory.py` | `ApiFactory` -- creates and configures the FastAPI application |
| `protocols.py` | `ApiFactoryProtocol` (1 method: `create_app`) |
| `dependencies.py` | 17 FastAPI `Depends()` providers for services, adapters, and request context |
| `middleware/__init__.py` | Exports `AuthMiddleware`, `CorrelationMiddleware`, `RateLimitMiddleware` |
| `middleware/correlation.py` | `CorrelationMiddleware` -- generates/propagates `X-Correlation-ID` |
| `middleware/auth.py` | `AuthMiddleware` -- JWT and API key validation |
| `middleware/rate_limit.py` | `RateLimitMiddleware` -- per-identifier rate limiting |
| `middleware/error_handler.py` | `register_error_handlers()` -- AppError-to-HTTP mapping + catch-all |
| `adapters/__init__.py` | Exports `ResponseAdapter`, `BotHintGenerator` |
| `adapters/response.py` | `ResponseAdapter` -- constructs standard `ApiResponse` envelopes |
| `adapters/bot_hints.py` | `BotHintGenerator` -- match state analysis and move ranking |
| `schemas/__init__.py` | Exports `ApiResponse`, `BotHint`, `ErrorDetail`, `ResponseMeta` |
| `schemas/common.py` | `ApiResponse[T]`, `ResponseMeta`, `ErrorDetail`, `BotHint` (Pydantic v2) |
| `schemas/auth.py` | 11 schema classes for auth endpoints |
| `schemas/player.py` | 5 schema classes for player endpoints |
| `schemas/energy.py` | 3 schema classes for energy endpoints |
| `schemas/match.py` | 8 schema classes for match endpoints (including `MoveRequest` with `model_validator`) |
| `schemas/matchmaking.py` | 4 schema classes for matchmaking endpoints |
| `schemas/vault.py` | 7 schema classes for vault endpoints |
| `schemas/events.py` | 7 schema classes for event endpoints |
| `schemas/ads.py` | 11 schema classes for ads endpoints |
| `schemas/payments.py` | 7 schema classes for payment endpoints |
| `schemas/bot_earnings.py` | 8 schema classes for bot earnings endpoints |
| `routes/__init__.py` | Exports all 12 routers |
| `routes/health.py` | 3 health check endpoints |
| `routes/auth.py` | 8 auth endpoints |
| `routes/players.py` | 6 player endpoints |
| `routes/energy.py` | 3 energy endpoints |
| `routes/matchmaking.py` | 4 matchmaking endpoints |
| `routes/matches.py` | 8 match endpoints |
| `routes/vault.py` | 7 vault endpoints |
| `routes/events.py` | 5 event endpoints |
| `routes/ads.py` | 6 ads endpoints |
| `routes/payments.py` | 4 payment endpoints |
| `routes/bot_earnings.py` | 5 bot earnings endpoints |
| `routes/ws.py` | 1 WebSocket endpoint (`/ws`) |
| `websocket/__init__.py` | Exports `ConnectionManager`, `ChannelManager`, `WebSocketHandler` |
| `websocket/manager.py` | `ConnectionManager` -- per-player connection tracking, match subscriptions |
| `websocket/channels.py` | `ChannelManager` -- channel subscription management, event routing |
| `websocket/handler.py` | `WebSocketHandler` -- full connection lifecycle (auth, message loop, cleanup) |

### CLI (`src/cli/commands/`)

| File | Purpose |
|------|---------|
| `api_commands.py` | Click group "api" with 4 commands: `start`, `routes`, `health`, `config` |

### Tests (`tests/unit/modules/api/`)

| File | Purpose |
|------|---------|
| `conftest.py` | Shared fixtures: mock services, `TestAuthMiddleware`, test app, test client |
| `test_middleware.py` | 35 tests across 5 test classes |
| `test_adapters.py` | 24 tests across 2 test classes |
| `test_auth_routes.py` | 23 tests across 8 test classes |
| `test_player_routes.py` | 18 tests across 6 test classes |
| `test_energy_routes.py` | 10 tests across 3 test classes |
| `test_matchmaking_routes.py` | 13 tests across 4 test classes |
| `test_match_routes.py` | 14 tests across 8 test classes |
| `test_vault_routes.py` | 13 tests across 7 test classes |
| `test_events_routes.py` | 9 tests across 5 test classes |
| `test_ads_routes.py` | 11 tests across 6 test classes |
| `test_payments_routes.py` | 6 tests across 4 test classes |
| `test_bot_earnings_routes.py` | 6 tests across 5 test classes |

## 3. Architecture

### Module Structure

```
src/modules/api/
    __init__.py               # Module entry: exports ApiFactory, ApiFactoryProtocol
    factory.py                # ApiFactory: creates FastAPI app, wires everything
    protocols.py              # ApiFactoryProtocol (typing.Protocol)
    dependencies.py           # FastAPI Depends() providers

    middleware/
        __init__.py
        correlation.py        # CorrelationMiddleware (generates X-Correlation-ID)
        auth.py               # AuthMiddleware (JWT + API key validation)
        rate_limit.py         # RateLimitMiddleware (per-key/player/IP)
        error_handler.py      # AppError -> HTTP status + catch-all

    adapters/
        __init__.py
        response.py           # ResponseAdapter (success/error envelope)
        bot_hints.py          # BotHintGenerator (board analysis, move ranking)

    schemas/
        __init__.py
        common.py             # ApiResponse[T], ResponseMeta, ErrorDetail, BotHint
        auth.py               # Auth request/response schemas
        player.py             # Player schemas
        energy.py             # Energy schemas
        match.py              # Match schemas (with model_validator for move adjacency)
        matchmaking.py        # Matchmaking schemas
        vault.py              # Vault schemas
        events.py             # Event schemas
        ads.py                # Ads schemas
        payments.py           # Payment schemas
        bot_earnings.py       # Bot earnings schemas

    routes/
        __init__.py           # Exports all 12 routers
        health.py             # /api/v1/health/*
        auth.py               # /api/v1/auth/*
        players.py            # /api/v1/players/*
        energy.py             # /api/v1/energy/*
        matchmaking.py        # /api/v1/matchmaking/*
        matches.py            # /api/v1/matches/*
        vault.py              # /api/v1/vault/*
        events.py             # /api/v1/events/*
        ads.py                # /api/v1/ads/*
        payments.py           # /api/v1/payments/*
        bot_earnings.py       # /api/v1/bot-earnings/*
        ws.py                 # /ws (WebSocket)

    websocket/
        __init__.py
        manager.py            # ConnectionManager (per-player WebSocket tracking)
        channels.py           # ChannelManager (subscription management)
        handler.py            # WebSocketHandler (lifecycle: auth -> loop -> cleanup)
```

### Request Lifecycle

```
1. Request arrives
2. CORSMiddleware: Handle preflight / CORS headers (Starlette built-in)
3. CorrelationMiddleware: Generate or extract X-Correlation-ID, set ContextVar
4. AuthMiddleware: Validate JWT/API key, set request.state (player_id, auth_type)
5. RateLimitMiddleware: Check per-identifier limits, return 429 if exceeded
6. Route handler: Validate input (Pydantic), call service (async), format response
7. Error handler (if needed): AppError -> structured JSON, Exception -> 500
8. Response sent with X-Correlation-ID header
```

## 4. Public Interface

### ApiFactoryProtocol

```python
class ApiFactoryProtocol(Protocol):
    def create_app(self) -> FastAPI: ...
```

### ApiFactory Constructor

```python
class ApiFactory:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        auth_service: AuthServiceProtocol,
        player_service: PlayerServiceProtocol,
        energy_service: EnergyServiceProtocol,
        matchmaking_service: MatchmakingServiceProtocol,
        match_service: MatchServiceProtocol,
        vault_service: VaultServiceProtocol,
        event_service: EventServiceProtocol,
        ad_service: AdServiceProtocol,
        payment_service: PaymentServiceProtocol,
        bot_earnings_service: BotEarningsServiceProtocol,
    ) -> None: ...

    def create_app(self) -> FastAPI: ...
```

### All Routes (60 endpoints across 12 routers)

#### Health Routes (`/api/v1/health`) -- 3 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | None | Basic health check (status, timestamp, version) |
| GET | `/api/v1/health/ready` | None | Readiness check (DB + Redis connectivity) |
| GET | `/api/v1/health/live` | None | Liveness probe (always 200) |

#### Auth Routes (`/api/v1/auth`) -- 8 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | None | Register human account (returns player + tokens) |
| POST | `/api/v1/auth/login` | None | Login (returns JWT tokens) |
| POST | `/api/v1/auth/refresh` | JWT | Refresh JWT token (rotation) |
| POST | `/api/v1/auth/logout` | JWT | Invalidate session |
| POST | `/api/v1/auth/bot/register` | None | Register bot account |
| POST | `/api/v1/auth/bot/api-key` | JWT | Generate API key for bot |
| DELETE | `/api/v1/auth/bot/api-key/{key_id}` | JWT | Revoke API key |
| GET | `/api/v1/auth/bot/api-keys` | JWT | List API keys (no raw keys) |

#### Player Routes (`/api/v1/players`) -- 6 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/players/leaderboard` | JWT/API Key | ELO leaderboard with pagination |
| GET | `/api/v1/players/me` | JWT/API Key | Current player profile (includes email) |
| GET | `/api/v1/players/{target_player_id}` | JWT/API Key | Player by ID (public profile, no email) |
| PATCH | `/api/v1/players/me` | JWT/API Key | Update current player (username, email) |
| DELETE | `/api/v1/players/me` | JWT/API Key | Soft-delete account |
| GET | `/api/v1/players/{target_player_id}/stats` | JWT/API Key | Player statistics |

#### Energy Routes (`/api/v1/energy`) -- 3 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/energy` | JWT/API Key | Current energy state |
| POST | `/api/v1/energy/login` | JWT/API Key | Record login for streak |
| GET | `/api/v1/energy/streak` | JWT/API Key | Streak information |

#### Matchmaking Routes (`/api/v1/matchmaking`) -- 4 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/matchmaking/queue` | JWT/API Key | Join matchmaking queue |
| DELETE | `/api/v1/matchmaking/queue` | JWT/API Key | Leave matchmaking queue |
| GET | `/api/v1/matchmaking/queue/status` | JWT/API Key | Get queue position |
| GET | `/api/v1/matchmaking/pools` | JWT/API Key | Get pool statistics (bot hint) |

#### Match Routes (`/api/v1/matches`) -- 8 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/matches/active` | JWT/API Key | Get active matches |
| GET | `/api/v1/matches/history` | JWT/API Key | Match history (paginated) |
| GET | `/api/v1/matches/{match_id}` | JWT/API Key | Match details |
| GET | `/api/v1/matches/{match_id}/state` | JWT/API Key | Full match state (with bot hints for API key) |
| GET | `/api/v1/matches/{match_id}/board` | JWT/API Key | Player's board view |
| POST | `/api/v1/matches/{match_id}/move` | JWT/API Key | Submit a move |
| POST | `/api/v1/matches/{match_id}/forfeit` | JWT/API Key | Forfeit match |
| GET | `/api/v1/matches/{match_id}/moves` | JWT/API Key | Move history |

#### Vault Routes (`/api/v1/vault`) -- 7 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/vault/artifacts` | JWT/API Key | Owned artifacts (filterable by rarity, set) |
| GET | `/api/v1/vault/artifacts/{artifact_id}` | JWT/API Key | Artifact details |
| POST | `/api/v1/vault/shield` | JWT/API Key | Activate shield |
| GET | `/api/v1/vault/shield` | JWT/API Key | Shield status |
| POST | `/api/v1/vault/raid` | JWT/API Key | Attempt raid |
| GET | `/api/v1/vault/collection` | JWT/API Key | Collection progress |
| GET | `/api/v1/vault/targets` | JWT/API Key | Raidable targets (bot-oriented) |

#### Events Routes (`/api/v1/events`) -- 5 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/events` | JWT/API Key | List active events |
| GET | `/api/v1/events/{event_id}` | JWT/API Key | Event details |
| POST | `/api/v1/events/{event_id}/join` | JWT/API Key | Join event |
| GET | `/api/v1/events/{event_id}/leaderboard` | JWT/API Key | Event leaderboard |
| GET | `/api/v1/events/{event_id}/status` | JWT/API Key | Player's event status |

#### Ads Routes (`/api/v1/ads`) -- 6 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/ads/status` | JWT/API Key | Ad-free status |
| POST | `/api/v1/ads/interstitial/request` | JWT only | Request interstitial ad |
| POST | `/api/v1/ads/interstitial/complete` | JWT only | Complete interstitial impression |
| POST | `/api/v1/ads/rewarded/request` | JWT only | Request rewarded video |
| POST | `/api/v1/ads/rewarded/complete` | JWT only | Complete rewarded video |
| GET | `/api/v1/ads/bot/attributions` | API Key only | Bot ad attribution report |

#### Payments Routes (`/api/v1/payments`) -- 4 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/payments/purchase/initiate` | JWT only | Start ad-free purchase |
| POST | `/api/v1/payments/purchase/validate` | JWT only | Validate purchase receipt |
| POST | `/api/v1/payments/restore` | JWT only | Restore purchases |
| GET | `/api/v1/payments/status` | JWT only | Get purchase status |

#### Bot Earnings Routes (`/api/v1/bot-earnings`) -- 5 endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/bot-earnings/balance` | API Key only | Earnings balance |
| POST | `/api/v1/bot-earnings/sync` | API Key only | Sync attributions |
| POST | `/api/v1/bot-earnings/payout/request` | API Key only | Request payout |
| GET | `/api/v1/bot-earnings/payout/history` | API Key only | Payout history |
| GET | `/api/v1/bot-earnings/attributions` | API Key only | Attribution details |

#### WebSocket (`/ws`) -- 1 endpoint

| Protocol | Path | Auth | Description |
|----------|------|------|-------------|
| WebSocket | `/ws` | JWT/API Key (in-band) | Real-time event subscription |

## 5. Middleware Pipeline

Middleware is registered in the factory via `_register_middleware()`. Starlette processes middleware in reverse registration order, so the first registered middleware is outermost (runs first).

### Registration Order (in factory)

1. **CORSMiddleware** (Starlette built-in)
2. **CorrelationMiddleware**
3. **AuthMiddleware**
4. **RateLimitMiddleware**

### Execution Order (per request)

1. **CORS** -- Handles preflight `OPTIONS` requests, sets `Access-Control-*` headers, exposes `X-Correlation-ID`. Configured with `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
2. **Correlation** -- Extracts `X-Correlation-ID` from request header or generates a new one (`cc_{timestamp_hex}_{random_hex}`). Stores in `request.state.correlation_id` and in an async-safe `ContextVar` (`correlation_id_var`). Echoes back in response header. Uses `try/finally` to reset the ContextVar token.
3. **Auth** -- Skips public paths (frozenset of 9 paths including `/docs`, `/redoc`, `/openapi.json`). For non-public paths: checks `X-API-Key` header first, then `Authorization: Bearer <token>`. Delegates to `AuthServiceProtocol.validate_token()`. Sets `request.state.auth_type` ("jwt" or "api_key"), `request.state.player_id`, and optionally `request.state.api_key_id` or `request.state.session_id`. Returns 401 `JSONResponse` on failure with standard error envelope.
4. **Rate Limit** -- Skips health endpoints (`/api/v1/health*`). For API-key-authenticated requests: delegates to `AuthServiceProtocol.check_rate_limit(api_key_id)` and `record_api_request(api_key_id)`. Returns 429 `JSONResponse` with `Retry-After` header if exceeded. Non-API-key requests pass through without rate limit checks.

### Error Handlers (registered via `register_error_handlers()`)

Two exception handlers are registered as FastAPI exception handlers (not middleware):

- **`AppError` handler** -- Maps `AppError.code` prefix to HTTP status via `_resolve_status_code()`. Returns structured envelope with `correlation_id`, `timestamp`, and `version`.
- **Generic `Exception` handler** -- Catch-all for unhandled exceptions. Returns 500 with `INTERNAL_UNEXPECTED` code and generic "An unexpected error occurred" message.

### Error Prefix to HTTP Status Mapping

| Error Prefix | HTTP Status |
|-------------|-------------|
| `VALIDATION` | 400 |
| `AUTH` | 401 |
| `FORBIDDEN` | 403 |
| `NOT_FOUND` | 404 |
| `CONFLICT` | 409 |
| `RATE_LIMIT` | 429 |
| `INTERNAL` | 500 |
| *(unknown prefix)* | 500 |

## 6. Schema Design

All schemas use Pydantic v2 patterns.

### Patterns Used

- **`ConfigDict(frozen=True)`** on all response schemas -- response models are immutable after creation.
- **`ConfigDict(from_attributes=True)`** on `ApiResponse` -- allows construction from ORM-like objects.
- **`Field(...)` with constraints** -- `min_length`, `max_length`, `pattern`, `ge`, `lt`, `gt`, `le` for request validation.
- **`model_validator(mode="after")`** -- used in `MoveRequest` to validate orthogonal adjacency of move positions.
- **`Generic[T]`** -- `ApiResponse[T]` is generic over the data payload type.

### Standard Response Envelope

Every response (success and error) uses the `ApiResponse[T]` envelope:

```python
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ErrorDetail | None = None
    meta: ResponseMeta  # correlation_id, timestamp, version
```

The `ResponseAdapter` constructs this envelope and calls `model_dump(mode="json")` to produce a plain dict for return from route handlers.

### Request Validation Examples

- `RegisterRequest` / `BotRegisterRequest`: Username pattern `^[a-zA-Z0-9_]+$`, length 3-32, password min 8 chars.
- `MoveRequest`: Board coordinates `ge=0, lt=8`, `timestamp_ms` `gt=0`, plus `model_validator` for adjacency check.
- Query parameters: `limit` with `ge=1, le=100` (or `le=500` for event leaderboards), `offset` with `ge=0`.

## 7. Adapters

### ResponseAdapter (`adapters/response.py`)

Pure presentation helper that wraps any data payload in the standard `ApiResponse` envelope.

- **`success(data, correlation_id) -> dict[str, Any]`** -- Creates `ApiResponse(success=True, data=data, ...)` and calls `model_dump(mode="json")`.
- **`error(code, message, correlation_id, details=None) -> dict[str, Any]`** -- Creates `ApiResponse(success=False, error=ErrorDetail(...), ...)` and calls `model_dump(mode="json")`.

Both methods generate a `ResponseMeta` with `datetime.now(timezone.utc)` timestamp and version `"1.0"`.

### BotHintGenerator (`adapters/bot_hints.py`)

Synchronous presentation-layer analysis of match state for bot players. Uses its own frozen dataclass hierarchy (not Pydantic models) for hint data: `ValidMoveHint`, `RankedMove`, `BoardAnalysis`, `StrategicContext`, `MatchBotHints`.

**`generate_match_hints(board, valid_moves, my_score, opponent_score, turns_remaining) -> MatchBotHints`** performs:

1. **Board analysis** (`_analyze_board`) -- Counts gem distribution (keys as strings), identifies special gems (negative gem values), counts adjacent same-colour pairs as chain opportunities, classifies board volatility:
   - `>20` chain opportunities: `"volatile"`
   - `>10` chain opportunities: `"moderate"`
   - Otherwise: `"stable"`

2. **Move ranking** (`_rank_moves`) -- For each valid move:
   - Estimates cascade potential via `_estimate_cascade` (counts same-colour neighbours around destination cells after conceptual swap, excluding the swap partner)
   - Calculates expected score: `estimated_score + (cascade_potential * 10)`
   - Classifies cascade potential: `>2` = `"high"`, `>0` = `"medium"`, else `"low"`
   - Special gem chance: `min(0.3 * cascade_potential, 1.0)`
   - Sorts descending by expected score, returns top 5

3. **Strategy determination** (`_determine_strategy`) -- Game phase from turns remaining:
   - `>20`: `"early"`
   - `>5`: `"mid"`
   - Otherwise: `"late"`
   - `None` (time-based): `"mid"`
   - Strategy: deficit `< -100` and late = `"aggressive"` / `"high"` risk; lead `> 100` = `"defensive"` / `"low"` risk; else `"balanced"` / `"medium"`

**When hints are included:**
- Request authenticated via API key (`auth_type == "api_key"`)
- Endpoint is `GET /matches/{match_id}/state`
- Config `api.bot_hints_enabled` is true (checked in route handler)

## 8. WebSocket

### Architecture

Three components work together:

1. **`ConnectionManager`** (`websocket/manager.py`) -- Tracks active WebSocket connections per player (`dict[UUID, set[WebSocket]]`). Also tracks match subscriptions (`dict[UUID, set[UUID]]`). Thread-safe via `asyncio.Lock`. Provides `broadcast_to_player()` and `broadcast_to_match()` with safe-send error suppression.

2. **`ChannelManager`** (`websocket/channels.py`) -- Tracks per-player channel subscriptions. Supports four channels with their allowed event types:
   - `match`: `match_update`, `opponent_moved`, `match_ended`
   - `energy`: `energy_update`
   - `matchmaking`: `matchmaking_found`, `matchmaking_timeout`
   - `events`: `event_started`, `event_ended`

3. **`WebSocketHandler`** (`websocket/handler.py`) -- Manages the full lifecycle of a WebSocket connection.

### Connection Lifecycle

```
1. Client connects to /ws -> websocket.accept()
2. Handler waits for auth message (timeout: connection_timeout_seconds, default 60s)
3. Client sends: {"type": "auth", "payload": {"token": "<jwt_or_api_key>"}}
4. Handler validates via auth_service.validate_token(token)
5. On success: {"type": "auth_ok", "payload": {"player_id": "..."}}
   On failure: {"type": "auth_failed", "payload": {"code": "...", "message": "..."}} -> close
6. Connection limit check (max_connections_per_player, default 3)
   Exceeds limit: {"type": "error", ...} with WS_RATE_LIMITED -> close
7. Register connection with ConnectionManager
8. Enter message loop:
   - "ping" -> respond with "pong"
   - "subscribe" -> subscribe to channel via ChannelManager
     (for "match" channel, also subscribe in ConnectionManager for match broadcasts)
   - "unsubscribe" -> unsubscribe from channel
   - Unknown type -> "error" response
   - Timeout -> send pong as heartbeat check
   - Message too large (>max_message_size_bytes) -> "error" response
   - Malformed JSON -> "error" response
9. On disconnect/error -> cleanup (ConnectionManager.disconnect + ChannelManager.unsubscribe_all)
```

### WebSocket Configuration Keys

| Key | Default | Purpose |
|-----|---------|---------|
| `websocket.heartbeat_interval_seconds` | 30 | Heartbeat interval |
| `websocket.connection_timeout_seconds` | 60 | Auth and message receive timeout |
| `websocket.max_connections_per_player` | 3 | Max concurrent connections per player |
| `websocket.max_message_size_bytes` | 65536 | Maximum incoming message size |

### Message Format

All WebSocket messages use the `WSMessage` type from `src.core.types.websocket`, serialized via `to_dict()`:

```json
{
    "type": "<WSMessageType value>",
    "payload": { ... },
    "correlation_id": "cc_...",
    "timestamp": "2026-02-05T18:30:00Z"
}
```

## 9. Authentication

### Dual Auth Model

The API supports two authentication mechanisms:

1. **JWT (`Authorization: Bearer <token>`)** -- For human web clients. Sets `request.state.auth_type = "jwt"`, `request.state.player_id`, `request.state.session_id`.

2. **API Key (`X-API-Key` header)** -- For bot players (LLMs). Sets `request.state.auth_type = "api_key"`, `request.state.player_id`, `request.state.api_key_id`.

### Auth Flow

- API key is checked first when both headers are present.
- Both auth types delegate to `AuthServiceProtocol.validate_token()`.
- Auth failures return `JSONResponse` with 401 status and structured error body (not `HTTPException`).
- The `_auth_error` static method constructs the 401 response with the standard envelope format (`success`, `data`, `error`, `meta` fields).

### Public Paths (no auth required)

```python
frozenset({
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/bot/register",
    "/api/v1/health",
    "/api/v1/health/ready",
    "/api/v1/health/live",
    "/docs",
    "/redoc",
    "/openapi.json",
})
```

### Auth-Type Restrictions

Some endpoints enforce a specific auth type in the route handler itself:

- **JWT only** (human players): All ads interstitial/rewarded endpoints, all payment endpoints. Enforced via `_require_jwt()` helper that raises `FORBIDDEN_BOT_NOT_ALLOWED` through the error service.
- **API Key only** (bot players): Bot ad attributions, all bot earnings endpoints. Enforced via `_require_api_key()` helper that raises `FORBIDDEN_NOT_BOT` through the error service.

### Bot Hint Gating

Bot hints in match state responses are gated on three conditions checked in the `get_match_state` route handler:
1. `get_auth_type(request) == "api_key"`
2. `config.get("api.bot_hints_enabled", True)` is True
3. The endpoint being called is `GET /matches/{match_id}/state`

## 10. Error Handling

### AppError to HTTP Status Mapping

The `error_handler.py` module registers two FastAPI exception handlers:

1. **`AppError` handler** -- Resolves HTTP status from the error code prefix (see table in section 5). Constructs a structured JSON response with:
   - `success: false`
   - `error.code`: The full error code (e.g., `VALIDATION_INVALID_INPUT`)
   - `error.message`: Human-readable message
   - `error.details`: Context dict from `AppError.context` (if non-empty, else `None`)
   - `meta.correlation_id`: From `request.state` or `exc.correlation_id`
   - `meta.timestamp`: Current UTC ISO timestamp
   - `meta.version`: `"1.0"`

2. **Generic `Exception` handler** -- Catch-all for unhandled exceptions. Returns 500 with `INTERNAL_UNEXPECTED` code and "An unexpected error occurred" message. Details are always `None` to avoid leaking internal information.

### Validation Error Handling

Pydantic v2 validation errors (from request body/query parameter validation) are handled by FastAPI's built-in `RequestValidationError` handler, which returns 422 with field-level error details.

The `model_validator` on `MoveRequest` raises `ValueError` for non-adjacent positions, which FastAPI converts to a 422 response.

### Error Codes Created by the API Module

| Error Code | HTTP | When |
|------------|------|------|
| `AUTH_TOKEN_MISSING` | 401 | No Authorization header on protected path |
| `AUTH_TOKEN_INVALID` | 401 | Malformed or expired JWT |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit hit (per API key) |
| `FORBIDDEN_BOT_NOT_ALLOWED` | 403 | Bot accessing JWT-only endpoint |
| `FORBIDDEN_NOT_BOT` | 403 | Human accessing API-key-only endpoint |
| `INTERNAL_UNEXPECTED` | 500 | Unhandled exception catch-all |

All other error codes originate from downstream services and are translated to HTTP status by the `AppError` exception handler.

## 11. CLI Commands

### Command Group: `api`

Four commands defined in `src/cli/commands/api_commands.py`:

| Command | Options | Description |
|---------|---------|-------------|
| `api start` | `--host` (0.0.0.0), `--port` (8000), `--reload`, `--config` (config/app.toml) | Start the API server via uvicorn with `factory=True`. Config file defaults override CLI defaults; explicit CLI args take precedence. |
| `api routes` | `--config` (config/app.toml) | List all registered routes in a Rich table. Creates a temporary app with stub services. |
| `api health` | `--url` (http://localhost:8000) | Check `/api/v1/health` of a running server. Uses `urllib.request.urlopen`. |
| `api config` | `--config` (config/app.toml) | Display all `api.*`, `app.*`, and `websocket.*` config values in a Rich table. |

### Implementation Details

- Uses `rich.console.Console`, `rich.table.Table`, and `rich.panel.Panel` for formatted output.
- The `routes` command builds a stub factory with `_build_stub_factory()` that creates an `_Stub` class accepting any attribute access, paired with a `_LoggerStub` satisfying the logger protocol. This avoids requiring real service implementations for route inspection.
- Config is loaded via `src.core.composition_root.load_config()`.
- The `start` command uses `uvicorn.run()` with `factory=True` pointing to `src.modules.api.factory:create_app`.

## 12. Configuration Keys

### API Namespace

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api.host` | str | `"0.0.0.0"` | Server bind host |
| `api.port` | int | `8000` | Server bind port |
| `api.cors_origins` | list[str] | `["*"]` | CORS allowed origins |
| `api.docs_enabled` | bool | `true` | Enable OpenAPI docs (`/docs`, `/redoc`, `/openapi.json`) |
| `api.bot_hints_enabled` | bool | `true` | Include bot hints in match state responses |
| `api.rate_limit.requests_per_minute` | int | `60` | Default rate limit per identifier |
| `api.rate_limit.burst_size` | int | `10` | Burst allowance |

### App Namespace (consumed by factory)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `app.version` | str | `"0.1.0"` | Application version (shown in health, OpenAPI) |

### WebSocket Namespace

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `websocket.heartbeat_interval_seconds` | int | `30` | Heartbeat interval |
| `websocket.connection_timeout_seconds` | int | `60` | Auth and receive timeout |
| `websocket.max_connections_per_player` | int | `3` | Max concurrent WS connections per player |
| `websocket.max_message_size_bytes` | int | `65536` | Maximum incoming message size |

## 13. Dependencies

### Injected Services (16 total: 3 core + 13 module)

All dependencies arrive via the `ApiFactory.__init__` constructor and are stored on `app.state` by `_configure_state()`. Route handlers access them via `Depends()` providers in `dependencies.py`.

| Service | Protocol | app.state Key | Used By |
|---------|----------|---------------|---------|
| Config | `ConfigProtocol` | `config` | Factory, middleware, routes (bot hints check) |
| Logger | `LoggerProtocol` | `logger` | Factory, WebSocket handler |
| Errors | `ErrorServiceProtocol` | `errors` | Ads routes, payments routes, bot earnings routes (auth guards) |
| Auth | `AuthServiceProtocol` | `auth_service` | Auth routes, auth middleware, rate limit middleware, WS handler |
| Player | `PlayerServiceProtocol` | `player_service` | Auth routes, player routes, vault routes (targets) |
| Energy | `EnergyServiceProtocol` | `energy_service` | Energy routes |
| Matchmaking | `MatchmakingServiceProtocol` | `matchmaking_service` | Matchmaking routes |
| Match | `MatchServiceProtocol` | `match_service` | Match routes |
| Vault | `VaultServiceProtocol` | `vault_service` | Vault routes |
| Event | `EventServiceProtocol` | `event_service` | Event routes |
| Ad | `AdServiceProtocol` | `ad_service` | Ads routes |
| Payment | `PaymentServiceProtocol` | `payment_service` | Payment routes |
| Bot Earnings | `BotEarningsServiceProtocol` | `bot_earnings_service` | Bot earnings routes |

### Internal Adapters (created by factory, stored on app.state)

| Component | app.state Key | Purpose |
|-----------|---------------|---------|
| `ResponseAdapter` | `response_adapter` | Standard response envelope |
| `BotHintGenerator` | `bot_hint_generator` | Match state bot hints |
| `ConnectionManager` | `connection_manager` | WebSocket connection tracking |
| `ChannelManager` | `channel_manager` | WebSocket channel subscriptions |
| `WebSocketHandler` | `ws_handler` | WebSocket lifecycle handler |

### External Type Imports

Route handlers import domain types from other modules for type conversion (e.g., `PlayerId`, `MatchId`, `Position`, `Move` from `src.core.types.game`, `PlayerType` from `src.core.types.player`, `PoolType` from `src.modules.matchmaking.types`, `PaymentProvider`/`PurchaseReceipt` from `src.modules.payments.types`, `ArtifactRarity` from `src.modules.vault.dto`, `EventStatus` from `src.modules.events.types`, `PayoutStatus` from `src.modules.bot_earnings.types`, `PlayerUpdate` from `src.modules.player.dto`). These are value types/enums used for parameter conversion, not service instantiation.

The `correlation.py` middleware imports `correlation_id_var` from `src.core.protocols.correlation` to set the async-safe ContextVar. The `error_handler.py` and `auth.py` middleware import `AppError` from `src.core.errors`. The `websocket/` components import `WSMessage`, `WSMessageType`, `WSChannel` from `src.core.types.websocket`.

## 14. Deviations from Artifact

| Area | Artifact Spec | Implementation | Justification |
|------|--------------|----------------|---------------|
| Auth middleware error mechanism | Artifact raises `HTTPException` on auth failure | Implementation returns `JSONResponse` directly | Returning `JSONResponse` directly avoids FastAPI's default `HTTPException` handler, ensuring the standard error envelope format (`success`, `data`, `error`, `meta`) is preserved. |
| Auth middleware API key method | Artifact calls `self._auth.validate_api_key(api_key)` | Implementation calls `self._auth.validate_token(api_key)` for both JWT and API key | The `AuthServiceProtocol` exposes a single `validate_token` method that handles both token types. No separate `validate_api_key()` exists on the protocol. |
| Rate limit scope | Artifact checks all identifier types (api_key, player, IP) | Implementation only checks rate limit for API-key-authenticated requests | `AuthServiceProtocol.check_rate_limit()` takes a UUID (key_id), not a string identifier. JWT and IP-based rate limiting is deferred. |
| Auth public paths | Artifact lists 8 paths (no `/redoc`) | Implementation includes `/redoc` in the public paths frozenset | `/redoc` is another OpenAPI documentation endpoint that should not require auth. |
| Board cell type | Artifact uses `list[list[str]]` for board cells | Implementation uses `list[list[int]]` | Board cells are stored as integers internally in the match module; the implementation matches the actual data type. |
| Bot hint data structures | Artifact uses Pydantic `BaseModel` for hint types (`MatchBotHints`, `RankedMove`, `BoardAnalysis`, `StrategicContext`) | Implementation uses frozen `dataclass` types in `bot_hints.py` | Frozen dataclasses are lighter-weight for presentation-only data. Route handler manually constructs dicts from them for JSON output. |
| `MoveRequest` fields | Artifact does not include `timestamp_ms` | Implementation adds `timestamp_ms: int = Field(gt=0)` | The match service's `Move` type requires a client-side timestamp for move validation. |
| `MoveRequest` validation | Artifact does not include adjacency validation | Implementation adds `@model_validator(mode="after")` | Early validation prevents invalid moves from reaching the service layer. |
| `MatchStateResponse` structure | Artifact uses flat fields (`player_turn`, `board`, `valid_moves`) | Implementation uses nested `player1`/`player2` objects with `PlayerMatchStateResponse` | Provides richer data (both players' full state) while still computing `is_my_turn`, `my_score`, `opponent_score` at the top level. |
| CLI commands | Artifact: `serve`, `routes`, `openapi`, `test-health`, `test-auth` | Implementation: `start`, `routes`, `health`, `config` | `serve` renamed to `start`. `openapi` replaced by built-in `/openapi.json` endpoint. `test-auth` removed (covered by auth module CLI). `config` added for configuration inspection. |
| `ResponseAdapter` return type | Artifact returns `ApiResponse[T]` Pydantic model | Implementation returns `dict[str, Any]` via `model_dump(mode="json")` | Route handlers return dicts that FastAPI serializes; returning the model would cause double-serialization. |
| Matchmaking pools auth | Artifact specifies `API Key` only | Implementation allows both JWT and API Key | Useful information for all clients; the "bot hint" label is advisory. |
| Vault targets auth | Artifact specifies `API Key` only | Implementation allows both JWT and API Key | Same reasoning: no explicit auth type enforcement in the route handler. |
| Energy response `time_to_next_heart_display` | Artifact includes this field | Implementation omits it from `EnergyResponse` schema | Presentation formatting is handled client-side; the server provides `seconds_to_next_heart` for calculations. |
| `LoginResponse` naming collision | Artifact uses `LoginResponse` for both auth and energy schemas | Implementation uses `LoginStreakResponse` for energy login | Avoids naming collision between `schemas/auth.py` and `schemas/energy.py`. |
| Auth schema `ApiKeyResponse.name` | Artifact uses `name: str | None` | Implementation uses `description: str | None` | Matches the `ApiKeyCreateRequest.description` field for consistency. |

## 15. Test Coverage

### Summary

- **181 test functions** across **13 test files** (plus `conftest.py` with shared fixtures)
- **63 test classes** covering middleware, adapters, and all 11 route groups + WebSocket infrastructure

### Test Pattern

All tests follow a self-contained test app pattern:

1. Each test file (or group of route tests) creates a minimal `FastAPI` instance.
2. Mock services are injected via `app.state` (no `@patch`, no `monkeypatch`).
3. A `TestAuthMiddleware` pre-populates `request.state.player_id`, `auth_type`, and `correlation_id` to simulate authenticated requests without exercising the real auth middleware.
4. Real `ResponseAdapter` and `BotHintGenerator` instances are used (they are pure functions with no external dependencies).
5. `register_error_handlers()` is called to install the `AppError` exception handler so service errors are mapped correctly.
6. Starlette `TestClient` is used for synchronous HTTP testing.
7. Tests verify response envelope structure (`success`, `data`, `error`, `meta`), HTTP status codes, and service call arguments via `AsyncMock` assertions.

### Test Classes by File

| File | Test Classes (test count) |
|------|--------------------------|
| `test_middleware.py` | TestCorrelationMiddleware, TestAuthMiddleware, TestRateLimitMiddleware, TestErrorHandler, TestResolveStatusCode (35 tests) |
| `test_adapters.py` | TestResponseAdapter, TestBotHintGenerator (24 tests) |
| `test_auth_routes.py` | TestRegisterRoute, TestLoginRoute, TestRefreshTokenRoute, TestLogoutRoute, TestBotRegisterRoute, TestCreateApiKeyRoute, TestRevokeApiKeyRoute, TestListApiKeysRoute (23 tests) |
| `test_player_routes.py` | TestGetCurrentPlayer, TestGetPlayerById, TestUpdateCurrentPlayer, TestDeleteCurrentPlayer, TestGetPlayerStats, TestGetLeaderboard (18 tests) |
| `test_match_routes.py` | TestGetActiveMatches, TestGetMatch, TestGetMatchState, TestGetBoard, TestSubmitMove, TestForfeitMatch, TestGetMatchHistory, TestGetMoveHistory (14 tests) |
| `test_matchmaking_routes.py` | TestJoinQueue, TestLeaveQueue, TestGetQueueStatus, TestGetPoolStats (13 tests) |
| `test_vault_routes.py` | TestGetArtifacts, TestGetArtifact, TestActivateShield, TestGetShieldStatus, TestAttemptRaid, TestGetCollectionProgress, TestGetRaidTargets (13 tests) |
| `test_ads_routes.py` | TestGetAdFreeStatus, TestRequestInterstitial, TestCompleteInterstitial, TestRequestRewardedVideo, TestCompleteRewardedVideo, TestGetBotAttributions (11 tests) |
| `test_energy_routes.py` | TestGetEnergy, TestRecordLogin, TestGetStreak (10 tests) |
| `test_events_routes.py` | TestListEvents, TestGetEvent, TestJoinEvent, TestGetLeaderboard, TestGetPlayerEventStatus (9 tests) |
| `test_payments_routes.py` | TestInitiatePurchase, TestValidatePurchase, TestRestorePurchases, TestGetPurchaseStatus (6 tests) |
| `test_bot_earnings_routes.py` | TestGetEarningsBalance, TestSyncAttributions, TestRequestPayout, TestGetPayoutHistory, TestGetAttributionEntries (6 tests) |

### Coverage Includes

- Success paths for all 60 REST endpoints
- Service error propagation (AppError -> HTTP status mapping)
- Auth middleware: public path skip, API key auth, JWT auth, missing token, invalid token, expired token format
- Rate limit middleware: API key rate checking, rate exceeded with Retry-After header
- Correlation middleware: generation, client-provided preservation, response header echo
- Error handler: all 7 prefix-to-status mappings, unknown prefix default (500), generic exception catch-all
- ResponseAdapter: success envelope, error envelope, None data, complex nested data, version/timestamp presence
- BotHintGenerator: board analysis (gem distribution, chain opportunities, volatility), move ranking (expected score, cascade potential, special gem chance), strategy determination (game phase, score differential, strategy/risk), empty board/moves edge cases

## 16. Dependency Injection

All dependencies arrive via the `ApiFactory.__init__` constructor. No direct imports of core service constructors. No `os.environ` or `os.getenv`. No bare raises -- all errors flow through the injected `errors` service (in route handlers that create errors) or propagate as `AppError` from downstream services (caught by exception handlers). No raw SQL or data access -- all data flows through injected service protocols. The API module owns no persistent data and no repository interfaces.

The dependency injection chain is:

1. **Composition root** creates `ApiFactory` with all 16 service dependencies (3 core + 13 module).
2. **`ApiFactory.create_app()`** stores services on `app.state` via `_configure_state()`.
3. **`dependencies.py`** provides 17 `Depends()` functions that read from `request.app.state`.
4. **Route handlers** declare dependencies via `Depends(get_xxx_service)`.
5. **Middleware** receives services via constructor arguments at registration time.
6. **WebSocket handler** receives `ConnectionManager`, `ChannelManager`, `AuthServiceProtocol`, `ConfigProtocol`, and `LoggerProtocol` via its constructor, called in `_configure_state()`.
