# Module Architecture Report: api

**Module:** api
**Build Wave:** 9 (Terminal Node)
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The API module is the terminal node of the ChromaCrush dependency graph, exposing all game functionality via 60 REST endpoints and 1 WebSocket endpoint across 12 route groups. It is a pure presentation layer: it owns no persistent data, performs no business logic, and delegates all operations to 13 injected module services plus 3 core services. The tech stack consists of FastAPI (ASGI with auto-generated OpenAPI), Pydantic v2 (request/response validation), Starlette middleware (CORS, correlation ID, auth, rate limiting), and native WebSocket support. The module is designed **bot-first**: all responses use a consistent JSON envelope (`ApiResponse[T]`), bot players receive strategic hints in match state responses, and API key authentication is a first-class auth path alongside JWT. All route handlers are **asynchronous** (`async def`) because they await injected service methods.

---

## 2. Public Interface

| Route Group | Path Prefix | Endpoints | Description |
|-------------|-------------|-----------|-------------|
| Health | `/api/v1/health` | 3 | Basic health, readiness, liveness probes |
| Auth | `/api/v1/auth` | 8 | Register, login, refresh, logout, bot API keys |
| Players | `/api/v1/players` | 6 | Profile, stats, leaderboard, update, delete |
| Energy | `/api/v1/energy` | 3 | Energy state, login streak, streak info |
| Matchmaking | `/api/v1/matchmaking` | 4 | Queue join/leave, status, pool stats |
| Matches | `/api/v1/matches` | 8 | Active, history, state, board, move, forfeit, moves |
| Vault | `/api/v1/vault` | 7 | Artifacts, shield, raid, collection, targets |
| Events | `/api/v1/events` | 5 | List, details, join, leaderboard, status |
| Ads | `/api/v1/ads` | 6 | Status, interstitial, rewarded, bot attributions |
| Payments | `/api/v1/payments` | 4 | Initiate, validate, restore, status |
| Bot Earnings | `/api/v1/bot-earnings` | 5 | Balance, sync, payout, history, attributions |
| WebSocket | `/ws` | 1 | Real-time subscriptions (match, energy, matchmaking, events) |

**Total: 60 REST + 1 WebSocket = 61 endpoints**

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | API server config, bot hints, rate limits |
| `logger` | `LoggerProtocol` | Structured logging (factory, WebSocket) |
| `errors` | `ErrorServiceProtocol` | Auth-type guards in route handlers |
| `auth_service` | `AuthServiceProtocol` | Auth middleware, rate limit middleware, WS handler |
| `player_service` | `PlayerServiceProtocol` | Auth routes, player routes, vault targets |
| `energy_service` | `EnergyServiceProtocol` | Energy routes |
| `matchmaking_service` | `MatchmakingServiceProtocol` | Matchmaking routes |
| `match_service` | `MatchServiceProtocol` | Match routes |
| `vault_service` | `VaultServiceProtocol` | Vault routes |
| `event_service` | `EventServiceProtocol` | Event routes |
| `ad_service` | `AdServiceProtocol` | Ads routes |
| `payment_service` | `PaymentServiceProtocol` | Payment routes |
| `bot_earnings_service` | `BotEarningsServiceProtocol` | Bot earnings routes |

**16 total injected services (3 core + 13 module).** All arrive via `ApiFactory.__init__` and are stored on `app.state`.

---

## 4. Data Owned

**Stateless.** The API module owns no persistent data. It performs no direct database or Redis operations. All data access flows through injected service protocols. Internal adapters (`ResponseAdapter`, `BotHintGenerator`) and WebSocket managers (`ConnectionManager`, `ChannelManager`) hold only in-memory transient state.

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `api.host` | string | "0.0.0.0" | Server bind address |
| `api.port` | int | 8000 | Server bind port |
| `api.cors_origins` | list[string] | ["*"] | Allowed CORS origins |
| `api.docs_enabled` | bool | true | Enable /docs, /redoc, /openapi.json |
| `api.bot_hints_enabled` | bool | true | Include bot hints in match state responses |
| `api.rate_limit.requests_per_minute` | int | 60 | Rate limit per identifier per minute |
| `api.rate_limit.burst_size` | int | 10 | Burst allowance above rate limit |
| `app.version` | string | "0.1.0" | Application version (health, OpenAPI) |
| `websocket.heartbeat_interval_seconds` | int | 30 | WS heartbeat interval |
| `websocket.connection_timeout_seconds` | int | 60 | WS auth and receive timeout |
| `websocket.max_connections_per_player` | int | 3 | Max concurrent WS connections per player |
| `websocket.max_message_size_bytes` | int | 65536 | Maximum incoming WS message size |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `AUTH_TOKEN_MISSING` | 401 | No Authorization header on protected path |
| `AUTH_TOKEN_INVALID` | 401 | Malformed or expired JWT / invalid API key |
| `RATE_LIMIT_EXCEEDED` | 429 | API key rate limit hit |
| `FORBIDDEN_BOT_NOT_ALLOWED` | 403 | Bot accessing JWT-only endpoint |
| `FORBIDDEN_NOT_BOT` | 403 | Human accessing API-key-only endpoint |
| `INTERNAL_UNEXPECTED` | 500 | Unhandled exception catch-all |

All other error codes originate from downstream services and are translated to HTTP status by the `AppError` exception handler using error code prefix mapping.

---

## 7. Cross-Module Interactions

**Called by:** No other modules. API is the terminal node.

**Calls:** All modules -- auth, player, energy, matchmaking, match, vault, events, ads, payments, bot_earnings. The API module is the sole HTTP presentation layer for the entire application.

---

## 8. Key Schemas

| Schema | Location | Description |
|--------|----------|-------------|
| `ApiResponse[T]` | `src/modules/api/schemas/common.py` | Generic response envelope (success, data, error, meta) |
| `ResponseMeta` | `src/modules/api/schemas/common.py` | Correlation ID, timestamp, version metadata |
| `ErrorDetail` | `src/modules/api/schemas/common.py` | Structured error with code, message, details |
| `BotHint` | `src/modules/api/schemas/common.py` | Bot strategic hint in match state responses |
| `MoveRequest` | `src/modules/api/schemas/match.py` | Move input with adjacency model_validator |
| `MatchStateResponse` | `src/modules/api/schemas/match.py` | Nested player1/player2 match state |
| `RegisterRequest` | `src/modules/api/schemas/auth.py` | Human account registration input |
| `LoginResponse` | `src/modules/api/schemas/auth.py` | JWT token pair response |
