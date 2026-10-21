# Module Artifact: API

## Header
- **Author:** Scout Agent
- **Date:** 2026-02-05
- **Version:** 1.1
- **Status:** Draft
- **Dependencies:** auth, player, matchmaking, match, vault, energy, events, ads, payments, bot_earnings
- **Dependents:** None (terminal node)
- **Build Wave:** 9 (Terminal Node - Depends on ALL other modules)

---

## Purpose

The API module is the **terminal node** of ChromaCrush, exposing ALL game functionality via REST API. It serves as the unified HTTP interface for both:

1. **Human Web Clients** - Browser-based players using JWT authentication
2. **Bot Players (LLMs)** - AI agents using API key authentication

The API is designed **bot-first**, meaning:
- All responses include structured bot hints for LLM decision-making
- Endpoints are stateless and predictable
- Error responses are parseable and actionable
- OpenAPI/Swagger documentation is auto-generated

Key responsibilities:
- **Route Handling** - FastAPI routes for all module operations
- **Authentication** - JWT/API key middleware delegating to auth module
- **Rate Limiting** - Per-key rate limiting via auth module
- **Request Validation** - Pydantic model validation
- **Response Formatting** - Consistent JSON structure with correlation IDs
- **Bot Hints** - Strategic hints in match state responses
- **Error Mapping** - AppError to HTTP status code translation

---

## Public Interface

### 2.1 ApiService Protocol

The API module does not expose a traditional service protocol for inter-module use. Instead, it exposes HTTP endpoints. However, for composition root wiring, it needs an application factory:

```python
# src/modules/api/protocols.py
from typing import Protocol
from fastapi import FastAPI


class ApiFactoryProtocol(Protocol):
    """Factory for creating the FastAPI application."""

    def create_app(self) -> FastAPI:
        """
        Create and configure the FastAPI application.

        Returns:
            Configured FastAPI app with all routes, middleware, and
            exception handlers registered.
        """
        ...
```

### 2.2 Route Groups

All routes are prefixed with `/api/v1`. The API exposes these endpoint groups:

#### Authentication Routes (`/api/v1/auth`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/auth/register` | Register human account | None |
| POST | `/auth/login` | Login (returns JWT) | None |
| POST | `/auth/refresh` | Refresh JWT token | JWT |
| POST | `/auth/logout` | Invalidate session | JWT |
| POST | `/auth/bot/register` | Register bot account | None |
| POST | `/auth/bot/api-key` | Generate API key | JWT (bot owner) |
| DELETE | `/auth/bot/api-key/{key_id}` | Revoke API key | JWT (bot owner) |
| GET | `/auth/bot/api-keys` | List API keys | JWT (bot owner) |

#### Player Routes (`/api/v1/players`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/players/me` | Get current player profile | JWT/API Key |
| GET | `/players/{player_id}` | Get player by ID | JWT/API Key |
| PATCH | `/players/me` | Update current player | JWT |
| DELETE | `/players/me` | Soft-delete account | JWT |
| GET | `/players/{player_id}/stats` | Get player statistics | JWT/API Key |
| GET | `/players/leaderboard` | Get ELO leaderboard | JWT/API Key |

#### Energy Routes (`/api/v1/energy`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/energy` | Get current energy state | JWT/API Key |
| POST | `/energy/login` | Record login for streak | JWT/API Key |
| GET | `/energy/streak` | Get streak info | JWT/API Key |

#### Matchmaking Routes (`/api/v1/matchmaking`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/matchmaking/queue` | Join matchmaking queue | JWT/API Key |
| DELETE | `/matchmaking/queue` | Leave matchmaking queue | JWT/API Key |
| GET | `/matchmaking/queue/status` | Get queue position | JWT/API Key |
| GET | `/matchmaking/pools` | Get pool sizes (bot hint) | API Key |

#### Match Routes (`/api/v1/matches`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/matches/active` | Get current active match | JWT/API Key |
| GET | `/matches/{match_id}` | Get match details | JWT/API Key |
| GET | `/matches/{match_id}/state` | Get full match state | JWT/API Key |
| GET | `/matches/{match_id}/board` | Get player's board view | JWT/API Key |
| POST | `/matches/{match_id}/move` | Submit a move | JWT/API Key |
| POST | `/matches/{match_id}/forfeit` | Forfeit match | JWT/API Key |
| GET | `/matches/history` | Get match history | JWT/API Key |
| GET | `/matches/{match_id}/moves` | Get move history | JWT/API Key |

#### Vault Routes (`/api/v1/vault`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/vault/artifacts` | Get owned artifacts | JWT/API Key |
| GET | `/vault/artifacts/{artifact_id}` | Get artifact details | JWT/API Key |
| POST | `/vault/shield` | Activate shield | JWT/API Key |
| GET | `/vault/shield` | Get shield status | JWT/API Key |
| POST | `/vault/raid` | Attempt raid | JWT/API Key |
| GET | `/vault/collection` | Get collection progress | JWT/API Key |
| GET | `/vault/targets` | Get raidable targets (bot hint) | API Key |

#### Events Routes (`/api/v1/events`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/events` | List active events | JWT/API Key |
| GET | `/events/{event_id}` | Get event details | JWT/API Key |
| POST | `/events/{event_id}/join` | Join event | JWT/API Key |
| GET | `/events/{event_id}/leaderboard` | Get event leaderboard | JWT/API Key |
| GET | `/events/{event_id}/status` | Get player's event status | JWT/API Key |

#### Ads Routes (`/api/v1/ads`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/ads/status` | Get ad-free status | JWT/API Key |
| POST | `/ads/interstitial/request` | Request interstitial | JWT |
| POST | `/ads/interstitial/complete` | Complete interstitial | JWT |
| POST | `/ads/rewarded/request` | Request rewarded video | JWT |
| POST | `/ads/rewarded/complete` | Complete rewarded video | JWT |
| GET | `/ads/bot/attributions` | Get bot ad attributions | API Key |

#### Payments Routes (`/api/v1/payments`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/payments/purchase/initiate` | Start ad-free purchase | JWT |
| POST | `/payments/purchase/validate` | Validate purchase receipt | JWT |
| POST | `/payments/restore` | Restore purchases | JWT |
| GET | `/payments/status` | Get purchase status | JWT |

#### Bot Earnings Routes (`/api/v1/bot-earnings`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/bot-earnings/balance` | Get earnings balance | API Key |
| POST | `/bot-earnings/sync` | Sync attributions | API Key |
| POST | `/bot-earnings/payout/request` | Request payout | API Key |
| GET | `/bot-earnings/payout/history` | Get payout history | API Key |
| GET | `/bot-earnings/attributions` | Get attribution details | API Key |

#### Health Routes (`/api/v1/health`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Basic health check | None |
| GET | `/health/ready` | Readiness check (DB, Redis) | None |
| GET | `/health/live` | Liveness check | None |

### 2.3 Request/Response Schemas

#### Standard Response Envelope

All responses follow a consistent envelope:

```python
# src/modules/api/schemas/common.py
from pydantic import BaseModel
from typing import TypeVar, Generic
from datetime import datetime

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""
    success: bool
    data: T | None = None
    error: "ErrorDetail | None" = None
    meta: "ResponseMeta"


class ResponseMeta(BaseModel):
    """Response metadata."""
    correlation_id: str
    timestamp: datetime
    version: str = "1.0"


class ErrorDetail(BaseModel):
    """Error details for failed requests."""
    code: str
    message: str
    details: dict | None = None


class BotHint(BaseModel):
    """Bot-specific hints included in responses."""
    recommended_action: str | None = None
    urgency: str | None = None  # "low", "medium", "high", "critical"
    context: dict | None = None
```

#### Match State Response (with Bot Hints)

```python
# src/modules/api/schemas/match.py
from pydantic import BaseModel
from typing import Literal
from datetime import datetime


class BoardCell(BaseModel):
    """Single cell on the game board."""
    row: int
    col: int
    gem_type: str  # "red", "blue", "green", "yellow", "purple", "orange"


class BoardState(BaseModel):
    """Current board state."""
    cells: list[list[str]]  # 8x8 grid of gem types
    size: int = 8


class MatchStateResponse(BaseModel):
    """Full match state with bot hints."""
    match_id: str
    status: Literal["pending", "in_progress", "completed", "abandoned"]
    player_turn: str  # player_id of whose turn
    is_my_turn: bool

    my_score: int
    opponent_score: int

    board: BoardState
    valid_moves: list["ValidMove"]

    turns_remaining: int | None  # None if time-based
    time_remaining_seconds: int | None

    # Bot hints (only populated for API key auth)
    bot_hints: "MatchBotHints | None" = None


class ValidMove(BaseModel):
    """A valid move on the board."""
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    estimated_score: int  # Minimum guaranteed score


class MatchBotHints(BaseModel):
    """Strategic hints for bot players."""
    best_moves: list["RankedMove"]
    board_analysis: "BoardAnalysis"
    strategic_context: "StrategicContext"


class RankedMove(BaseModel):
    """A move ranked by expected value."""
    move: ValidMove
    expected_score: int
    cascade_potential: Literal["low", "medium", "high"]
    special_gem_chance: float  # 0.0-1.0


class BoardAnalysis(BaseModel):
    """Analysis of current board state."""
    gem_distribution: dict[str, int]  # gem_type -> count
    special_gems_available: int
    chain_opportunities: int
    board_volatility: Literal["stable", "moderate", "volatile"]


class StrategicContext(BaseModel):
    """Strategic situation analysis."""
    score_differential: int
    recommended_strategy: Literal["aggressive", "defensive", "balanced"]
    risk_tolerance: Literal["low", "medium", "high"]
    game_phase: Literal["early", "mid", "late"]
```

#### Authentication Schemas

```python
# src/modules/api/schemas/auth.py
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    """Human registration request."""
    username: str
    password: str
    email: EmailStr | None = None


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class BotRegisterRequest(BaseModel):
    """Bot registration request."""
    bot_name: str
    owner_contact: str  # email for revenue sharing


class ApiKeyResponse(BaseModel):
    """API key creation response."""
    key_id: str
    api_key: str  # Only shown once on creation
    created_at: str
    name: str | None = None
```

#### Energy Schemas

```python
# src/modules/api/schemas/energy.py
from pydantic import BaseModel
from datetime import datetime


class EnergyResponse(BaseModel):
    """Current energy state."""
    current_hearts: int
    max_hearts: int
    seconds_to_next_heart: int | None
    next_heart_at: datetime | None
    is_full: bool
    daily_streak: int

    # Human-friendly formatting (presentation layer adds)
    time_to_next_heart_display: str | None = None


class StreakResponse(BaseModel):
    """Streak information."""
    current_streak: int
    last_login_date: str | None
    next_reward_threshold: int
    days_until_reward: int
    reward_hearts: int


class LoginResponse(BaseModel):
    """Login result for streak."""
    streak_day: int
    streak_continued: bool
    streak_broken: bool
    bonus_hearts_granted: int
    energy: EnergyResponse
```

---

## Error Cases

### 3.1 HTTP Status Code Mapping

Per interface-contracts.md, errors map to HTTP status codes:

| Error Category | HTTP Status | Error Codes |
|----------------|-------------|-------------|
| Validation | 400 | `VALIDATION_*` |
| Authentication | 401 | `AUTH_*` |
| Authorization | 403 | `FORBIDDEN_*` |
| Not Found | 404 | `NOT_FOUND_*` |
| Conflict | 409 | `CONFLICT_*` |
| Rate Limited | 429 | `RATE_LIMIT_*` |
| Internal | 500 | `INTERNAL_*` |

### 3.2 Error Response Format

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_INVALID_INPUT",
    "message": "Username must be at least 3 characters",
    "details": {
      "field": "username",
      "constraint": "min_length",
      "value": "ab"
    }
  },
  "meta": {
    "correlation_id": "cc_1a2b3c4d_5e6f7890",
    "timestamp": "2026-02-05T12:34:56Z",
    "version": "1.0"
  }
}
```

### 3.3 Error Cases by Endpoint Group

#### Authentication Errors

| Endpoint | Error Code | Condition |
|----------|------------|-----------|
| POST /auth/register | `VALIDATION_INVALID_INPUT` | Invalid username/password format |
| POST /auth/register | `CONFLICT_USERNAME_TAKEN` | Username exists |
| POST /auth/login | `AUTH_INVALID_CREDENTIALS` | Wrong username/password |
| POST /auth/login | `AUTH_ACCOUNT_LOCKED` | Too many failed attempts |
| POST /auth/refresh | `AUTH_TOKEN_EXPIRED` | Refresh token expired |
| POST /auth/refresh | `AUTH_TOKEN_INVALID` | Invalid refresh token |
| * | `AUTH_TOKEN_MISSING` | No auth header provided |
| * | `AUTH_TOKEN_INVALID` | Malformed/expired JWT |
| * | `AUTH_API_KEY_INVALID` | Invalid API key |

#### Rate Limit Errors

| Condition | Error Code | Retry-After |
|-----------|------------|-------------|
| Per-key limit exceeded | `RATE_LIMIT_EXCEEDED` | Seconds until reset |
| Global limit exceeded | `RATE_LIMIT_GLOBAL` | Seconds until reset |

---

## Async Behavior

All route handlers are `async def` because they:
1. Await service method calls (all services are async)
2. Await database operations via services
3. Await Redis operations for rate limiting

### Async Contract

| Layer | Async | Notes |
|-------|-------|-------|
| Route handlers | Yes | All FastAPI routes are async |
| Middleware | Yes | Auth, rate limit, correlation ID |
| Service calls | Yes | All module services are async |
| Response formatting | No | Pure transformation |

### Request Lifecycle

```
1. Request arrives
2. CorrelationMiddleware: Generate/extract correlation ID
3. RateLimitMiddleware: Check rate limits (async Redis)
4. AuthenticationMiddleware: Validate JWT/API key (async)
5. Route handler: Validate input, call service (async)
6. Service: Execute business logic (async)
7. Route handler: Format response
8. Response sent
```

---

## Mandatory Service Usage

### 5.1 Configuration Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api.host` | str | "0.0.0.0" | Server bind host |
| `api.port` | int | 8000 | Server bind port |
| `api.cors_origins` | list[str] | ["*"] | CORS allowed origins |
| `api.rate_limit.requests_per_minute` | int | 60 | Default rate limit |
| `api.rate_limit.burst_size` | int | 10 | Burst allowance |
| `api.docs_enabled` | bool | true | Enable OpenAPI docs |
| `api.bot_hints_enabled` | bool | true | Include bot hints in responses |

### 5.2 Logging Events

| Level | Event | Context Fields | When |
|-------|-------|----------------|------|
| INFO | "Request received" | `method`, `path`, `correlation_id`, `user_id` | On request start |
| INFO | "Request completed" | `method`, `path`, `status`, `duration_ms`, `correlation_id` | On response |
| WARN | "Rate limit exceeded" | `api_key_id`, `player_id`, `limit`, `window` | On 429 |
| WARN | "Authentication failed" | `reason`, `correlation_id` | On 401 |
| ERROR | "Request failed" | `error_code`, `message`, `correlation_id` | On 500 |
| DEBUG | "Bot hints generated" | `match_id`, `moves_analyzed`, `duration_ms` | On match state with hints |

### 5.3 Error Types Used

The API module primarily **translates** errors from other modules to HTTP responses. It creates these directly:

| Error Code | When |
|------------|------|
| `AUTH_TOKEN_MISSING` | No Authorization header |
| `AUTH_TOKEN_INVALID` | Malformed/expired JWT |
| `AUTH_API_KEY_INVALID` | Invalid API key format |
| `RATE_LIMIT_EXCEEDED` | Rate limit hit |
| `VALIDATION_INVALID_INPUT` | Pydantic validation failure |

---

## Data Access

### 6.1 Owned Data

The API module owns **no persistent data**. It is a pure presentation layer.

### 6.2 Repository Interfaces Required

None. All data access is through injected service protocols.

### 6.3 Data Read from Other Modules

All data flows through injected service protocols:

| Service | Data Read | Operations |
|---------|-----------|------------|
| `AuthServiceProtocol` | Sessions, API keys | Validate, create, refresh |
| `PlayerServiceProtocol` | Player profiles, stats | Get, update, list |
| `EnergyServiceProtocol` | Energy state, streaks | Get, consume, grant |
| `MatchmakingServiceProtocol` | Queue state | Join, leave, status |
| `MatchServiceProtocol` | Match state, boards | Get, submit move, forfeit |
| `VaultServiceProtocol` | Artifacts, shields | Get, raid, shield |
| `EventServiceProtocol` | Events, leaderboards | List, join, status |
| `AdServiceProtocol` | Ad status, sessions | Request, complete |
| `PaymentServiceProtocol` | Purchase status | Initiate, validate |
| `BotEarningsServiceProtocol` | Earnings, payouts | Get balance, request payout |

### 6.4 Transaction Requirements

The API module does not manage transactions. Transaction boundaries are handled by the services it calls.

---

## Presentation Boundary

### 7.1 This IS the Presentation Layer

The API module **is** the presentation layer for REST clients. It:
- Receives HTTP requests
- Validates input via Pydantic
- Calls business logic services
- Formats responses as JSON
- Adds bot hints for API key auth
- Handles errors and maps to HTTP status

### 7.2 What Belongs Here

- FastAPI route definitions
- Pydantic request/response models
- Input validation logic
- Response adapters (domain -> DTO)
- Bot hint generation
- Error-to-HTTP mapping
- CORS, auth, rate limit middleware

### 7.3 What Does NOT Belong Here

- Business logic (lives in modules)
- Data access (lives in repositories)
- Domain entities (lives in src/core/types)
- Service implementations (lives in modules)

---

## Internal Design

### 8.1 Service Implementation Structure

```
src/modules/api/
    __init__.py           # Exports ApiFactory
    factory.py            # ApiFactory implementation
    protocols.py          # ApiFactoryProtocol

    middleware/
        __init__.py
        correlation.py    # CorrelationMiddleware
        auth.py           # AuthenticationMiddleware
        rate_limit.py     # RateLimitMiddleware
        error_handler.py  # Exception handlers

    routes/
        __init__.py       # Route registration
        auth.py           # /api/v1/auth/*
        players.py        # /api/v1/players/*
        energy.py         # /api/v1/energy/*
        matchmaking.py    # /api/v1/matchmaking/*
        matches.py        # /api/v1/matches/*
        vault.py          # /api/v1/vault/*
        events.py         # /api/v1/events/*
        ads.py            # /api/v1/ads/*
        payments.py       # /api/v1/payments/*
        bot_earnings.py   # /api/v1/bot-earnings/*
        health.py         # /api/v1/health/*

    schemas/
        __init__.py
        common.py         # ApiResponse, ErrorDetail, BotHint
        auth.py           # Auth request/response schemas
        player.py         # Player schemas
        energy.py         # Energy schemas
        match.py          # Match schemas with bot hints
        matchmaking.py    # Matchmaking schemas
        vault.py          # Vault schemas
        events.py         # Event schemas
        ads.py            # Ads schemas
        payments.py       # Payment schemas
        bot_earnings.py   # Bot earnings schemas

    adapters/
        __init__.py
        response.py       # ResponseAdapter (domain -> API response)
        bot_hints.py      # BotHintGenerator

    dependencies.py       # FastAPI Depends() providers
```

### 8.2 Component Diagram

```
                         FastAPI Application
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
    CorrelationMiddleware  AuthMiddleware  RateLimitMiddleware
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                               ▼
                         Route Handlers
                               │
        ┌──────────────────────┼──────────────────────┐
        │          │           │          │           │
        ▼          ▼           ▼          ▼           ▼
    AuthService  PlayerSvc  MatchSvc  EnergyServ  ... (all services)
        │          │           │          │
        └──────────┴───────────┴──────────┘
                               │
                               ▼
                    ResponseAdapter + BotHintGenerator
                               │
                               ▼
                        ApiResponse (JSON)
```

### 8.3 Middleware Implementation

#### Correlation ID Middleware

```python
# src/modules/api/middleware/correlation.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import secrets


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to all requests."""

    async def dispatch(self, request: Request, call_next):
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            timestamp_hex = format(int(time.time()), 'x')
            random_hex = secrets.token_hex(4)
            correlation_id = f"cc_{timestamp_hex}_{random_hex}"

        # Store in request state for access in handlers
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

#### Authentication Middleware

```python
# src/modules/api/middleware/auth.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Protocol


class AuthMiddleware(BaseHTTPMiddleware):
    """Authenticate requests via JWT or API key."""

    def __init__(self, app, auth_service: "AuthServiceProtocol"):
        super().__init__(app)
        self._auth = auth_service
        self._public_paths = {
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/bot/register",
            "/api/v1/health",
            "/api/v1/health/ready",
            "/api/v1/health/live",
            "/docs",
            "/openapi.json",
        }

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        if request.url.path in self._public_paths:
            return await call_next(request)

        # Try API key first (X-API-Key header)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            auth_result = await self._auth.validate_api_key(api_key)
            if not auth_result.valid:
                raise HTTPException(
                    status_code=401,
                    detail={"code": "AUTH_API_KEY_INVALID", "message": "Invalid API key"}
                )
            request.state.auth_type = "api_key"
            request.state.player_id = auth_result.player_id
            request.state.api_key_id = auth_result.key_id
            return await call_next(request)

        # Try JWT (Authorization: Bearer ...)
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail={"code": "AUTH_TOKEN_MISSING", "message": "Authentication required"}
            )

        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail={"code": "AUTH_TOKEN_INVALID", "message": "Invalid token format"}
            )

        token = auth_header[7:]  # Remove "Bearer "
        auth_result = await self._auth.validate_token(token)
        if not auth_result.valid:
            raise HTTPException(
                status_code=401,
                detail={"code": "AUTH_TOKEN_INVALID", "message": auth_result.error or "Invalid token"}
            )

        request.state.auth_type = "jwt"
        request.state.player_id = auth_result.player_id
        request.state.session_id = auth_result.session_id

        return await call_next(request)
```

#### Rate Limit Middleware

```python
# src/modules/api/middleware/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce rate limits per API key/session."""

    def __init__(self, app, auth_service: "AuthServiceProtocol", config: "ConfigProtocol"):
        super().__init__(app)
        self._auth = auth_service
        self._requests_per_minute = config.get("api.rate_limit.requests_per_minute", 60)
        self._burst_size = config.get("api.rate_limit.burst_size", 10)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)

        # Get identifier for rate limiting
        if hasattr(request.state, "api_key_id"):
            identifier = f"api_key:{request.state.api_key_id}"
        elif hasattr(request.state, "player_id"):
            identifier = f"player:{request.state.player_id}"
        else:
            identifier = f"ip:{request.client.host}"

        # Check rate limit
        result = await self._auth.check_rate_limit(identifier)
        if not result.allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded",
                    "retry_after": result.retry_after_seconds,
                },
                headers={"Retry-After": str(result.retry_after_seconds)},
            )

        # Record request
        await self._auth.record_api_request(identifier)

        return await call_next(request)
```

### 8.4 Response Adapter

```python
# src/modules/api/adapters/response.py
from typing import TypeVar, Generic
from datetime import datetime, timezone

from src.modules.api.schemas.common import ApiResponse, ResponseMeta, ErrorDetail


T = TypeVar("T")


class ResponseAdapter:
    """Adapts domain objects to API responses."""

    def success(
        self,
        data: T,
        correlation_id: str,
    ) -> ApiResponse[T]:
        """Create a successful response."""
        return ApiResponse(
            success=True,
            data=data,
            error=None,
            meta=ResponseMeta(
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc),
            ),
        )

    def error(
        self,
        code: str,
        message: str,
        correlation_id: str,
        details: dict | None = None,
    ) -> ApiResponse:
        """Create an error response."""
        return ApiResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code=code,
                message=message,
                details=details,
            ),
            meta=ResponseMeta(
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc),
            ),
        )
```

### 8.5 Bot Hint Generator

```python
# src/modules/api/adapters/bot_hints.py
from src.modules.api.schemas.match import (
    MatchBotHints, RankedMove, BoardAnalysis, StrategicContext, ValidMove
)


class BotHintGenerator:
    """Generates strategic hints for bot players."""

    def generate_match_hints(
        self,
        board: list[list[str]],
        valid_moves: list[ValidMove],
        my_score: int,
        opponent_score: int,
        turns_remaining: int | None,
    ) -> MatchBotHints:
        """Generate hints for current match state."""

        # Analyze board
        board_analysis = self._analyze_board(board)

        # Rank moves
        ranked_moves = self._rank_moves(board, valid_moves)

        # Determine strategy
        strategic_context = self._determine_strategy(
            my_score, opponent_score, turns_remaining, board_analysis
        )

        return MatchBotHints(
            best_moves=ranked_moves[:5],  # Top 5 moves
            board_analysis=board_analysis,
            strategic_context=strategic_context,
        )

    def _analyze_board(self, board: list[list[str]]) -> BoardAnalysis:
        """Analyze current board state."""
        gem_counts = {}
        for row in board:
            for gem in row:
                gem_counts[gem] = gem_counts.get(gem, 0) + 1

        # Count chain opportunities (adjacent same-color pairs)
        chain_opportunities = 0
        for r in range(len(board)):
            for c in range(len(board[0])):
                if c < len(board[0]) - 1 and board[r][c] == board[r][c+1]:
                    chain_opportunities += 1
                if r < len(board) - 1 and board[r][c] == board[r+1][c]:
                    chain_opportunities += 1

        # Determine volatility
        if chain_opportunities > 20:
            volatility = "volatile"
        elif chain_opportunities > 10:
            volatility = "moderate"
        else:
            volatility = "stable"

        return BoardAnalysis(
            gem_distribution=gem_counts,
            special_gems_available=0,  # Would need special gem tracking
            chain_opportunities=chain_opportunities,
            board_volatility=volatility,
        )

    def _rank_moves(
        self,
        board: list[list[str]],
        valid_moves: list[ValidMove],
    ) -> list[RankedMove]:
        """Rank moves by expected value."""
        ranked = []
        for move in valid_moves:
            # Simple heuristic: estimated_score + cascade bonus
            cascade_potential = self._estimate_cascade(board, move)

            ranked.append(RankedMove(
                move=move,
                expected_score=move.estimated_score + (cascade_potential * 10),
                cascade_potential="high" if cascade_potential > 2 else "medium" if cascade_potential > 0 else "low",
                special_gem_chance=min(0.3 * cascade_potential, 1.0),
            ))

        return sorted(ranked, key=lambda r: r.expected_score, reverse=True)

    def _estimate_cascade(self, board: list[list[str]], move: ValidMove) -> int:
        """Estimate cascade potential for a move."""
        # Simplified: count adjacent matches after swap
        # Real implementation would simulate the swap
        return 0  # Placeholder

    def _determine_strategy(
        self,
        my_score: int,
        opponent_score: int,
        turns_remaining: int | None,
        analysis: BoardAnalysis,
    ) -> StrategicContext:
        """Determine recommended strategy."""
        diff = my_score - opponent_score

        # Game phase
        if turns_remaining is None:
            phase = "mid"
        elif turns_remaining > 20:
            phase = "early"
        elif turns_remaining > 5:
            phase = "mid"
        else:
            phase = "late"

        # Strategy based on situation
        if diff < -100 and phase == "late":
            strategy = "aggressive"
            risk = "high"
        elif diff > 100:
            strategy = "defensive"
            risk = "low"
        else:
            strategy = "balanced"
            risk = "medium"

        return StrategicContext(
            score_differential=diff,
            recommended_strategy=strategy,
            risk_tolerance=risk,
            game_phase=phase,
        )
```

### 8.6 Route Example: Match Endpoints

```python
# src/modules/api/routes/matches.py
from fastapi import APIRouter, Depends, Request
from uuid import UUID

from src.modules.api.schemas.match import MatchStateResponse, MoveRequest, MoveResponse
from src.modules.api.schemas.common import ApiResponse
from src.modules.api.adapters.response import ResponseAdapter
from src.modules.api.adapters.bot_hints import BotHintGenerator
from src.modules.api.dependencies import get_match_service, get_response_adapter


router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/{match_id}/state", response_model=ApiResponse[MatchStateResponse])
async def get_match_state(
    match_id: str,
    request: Request,
    match_service = Depends(get_match_service),
    response_adapter: ResponseAdapter = Depends(get_response_adapter),
    bot_hint_generator: BotHintGenerator = Depends(get_bot_hint_generator),
):
    """
    Get full match state.

    For bot players (API key auth), includes strategic hints.
    """
    player_id = request.state.player_id
    correlation_id = request.state.correlation_id
    is_bot = request.state.auth_type == "api_key"

    # Get match state from service
    match_state = await match_service.get_match_state(UUID(match_id))
    board = await match_service.get_player_board(UUID(match_id), player_id)
    valid_moves = match_service.get_valid_moves(board)

    # Build response
    response_data = MatchStateResponse(
        match_id=match_id,
        status=match_state.status.value,
        player_turn=str(match_state.current_turn_player_id),
        is_my_turn=match_state.current_turn_player_id == player_id,
        my_score=match_state.get_score(player_id),
        opponent_score=match_state.get_opponent_score(player_id),
        board=board,
        valid_moves=valid_moves,
        turns_remaining=match_state.turns_remaining,
        time_remaining_seconds=match_state.time_remaining_seconds,
        bot_hints=None,
    )

    # Add bot hints if API key auth
    if is_bot:
        response_data.bot_hints = bot_hint_generator.generate_match_hints(
            board=board.cells,
            valid_moves=valid_moves,
            my_score=response_data.my_score,
            opponent_score=response_data.opponent_score,
            turns_remaining=match_state.turns_remaining,
        )

    return response_adapter.success(response_data, correlation_id)


@router.post("/{match_id}/move", response_model=ApiResponse[MoveResponse])
async def submit_move(
    match_id: str,
    move: MoveRequest,
    request: Request,
    match_service = Depends(get_match_service),
    response_adapter: ResponseAdapter = Depends(get_response_adapter),
):
    """Submit a move in the match."""
    player_id = request.state.player_id
    correlation_id = request.state.correlation_id

    result = await match_service.submit_move(
        match_id=UUID(match_id),
        player_id=player_id,
        from_row=move.from_row,
        from_col=move.from_col,
        to_row=move.to_row,
        to_col=move.to_col,
    )

    return response_adapter.success(
        MoveResponse(
            valid=result.valid,
            score_earned=result.score_earned,
            gems_matched=result.gems_matched,
            cascade_count=result.cascade_count,
            match_completed=result.match_completed,
            winner_id=str(result.winner_id) if result.winner_id else None,
        ),
        correlation_id,
    )
```

---

## CLI Surface

### 9.1 Commands

The API module CLI provides server management:

```bash
# Server operations
chromacrush api serve [--host HOST] [--port PORT] [--reload]
chromacrush api routes
chromacrush api openapi [--output FILE]

# Testing endpoints
chromacrush api test-health
chromacrush api test-auth --token TOKEN
```

### 9.2 CLI Command Implementation

```python
# src/cli/commands/api_commands.py
import click
import uvicorn
import json


@click.group()
def api():
    """API server commands."""
    pass


@api.command("serve")
@click.option("--host", default="0.0.0.0", help="Bind host")
@click.option("--port", default=8000, type=int, help="Bind port")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.pass_context
def serve(ctx, host: str, port: int, reload: bool):
    """Start the API server."""
    config = ctx.obj["config"]

    # Override with CLI args if provided
    if host == "0.0.0.0":
        host = config.get("api.host", "0.0.0.0")
    if port == 8000:
        port = config.get("api.port", 8000)

    click.echo(f"Starting API server at http://{host}:{port}")
    click.echo("Press Ctrl+C to stop")

    uvicorn.run(
        "src.modules.api:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


@api.command("routes")
@click.pass_context
def list_routes(ctx):
    """List all registered routes."""
    api_factory = ctx.obj["api_factory"]
    app = api_factory.create_app()

    click.echo("Registered Routes:")
    click.echo("-" * 60)

    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            methods = ", ".join(route.methods - {"HEAD", "OPTIONS"})
            click.echo(f"  {methods:8} {route.path}")


@api.command("openapi")
@click.option("--output", "-o", type=click.Path(), help="Output file")
@click.pass_context
def export_openapi(ctx, output: str | None):
    """Export OpenAPI schema."""
    api_factory = ctx.obj["api_factory"]
    app = api_factory.create_app()

    schema = app.openapi()
    schema_json = json.dumps(schema, indent=2)

    if output:
        with open(output, "w") as f:
            f.write(schema_json)
        click.echo(f"OpenAPI schema written to {output}")
    else:
        click.echo(schema_json)


@api.command("test-health")
@click.option("--url", default="http://localhost:8000", help="API base URL")
@click.pass_context
async def test_health(ctx, url: str):
    """Test health endpoint."""
    import httpx

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{url}/api/v1/health")
            click.echo(f"Status: {response.status_code}")
            click.echo(f"Response: {response.json()}")
        except Exception as e:
            click.echo(f"Failed: {e}", err=True)
```

---

## Edge Cases & Decisions

### 10.1 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | FastAPI | Auto OpenAPI, async native, Pydantic validation |
| Bot hints scope | Match state only | Most strategic value; keep responses fast |
| Rate limiting location | Middleware via auth service | Centralized, per-key tracking |
| API versioning | URL path (`/api/v1/`) | Clear, explicit, easy to maintain |
| Auth header format | Bearer for JWT, X-API-Key for bots | Industry standard, unambiguous |
| Response envelope | Always wrap in ApiResponse | Consistent structure for all clients |
| Bot hint generation | Synchronous after service call | Keep hints lightweight; avoid blocking |

### 10.2 Edge Cases

| Scenario | Handling |
|----------|----------|
| Both JWT and API key provided | API key takes precedence |
| Expired JWT on non-critical endpoint | Return 401, client refreshes |
| Rate limit during active match | Allow match endpoints, reject others |
| Invalid correlation ID header | Generate new one, don't reject |
| Very large response (history) | Pagination with limit/offset |
| Bot requests human-only endpoint | Return 403 FORBIDDEN |
| Human requests bot-only endpoint | Allow (no bot hints) |
| Service timeout | Return 503 with retry guidance |
| Malformed JSON body | Return 400 with parse error details |

### 10.3 Bot Hints Design

Bot hints are included only when:
1. Request authenticated with API key (not JWT)
2. Endpoint is match-state related
3. Config `api.bot_hints_enabled` is true

Hints include:
- **best_moves**: Top 5 moves ranked by expected value
- **board_analysis**: Gem distribution, chain opportunities
- **strategic_context**: Recommended strategy based on game state

Hints are generated synchronously after service call returns, keeping latency low.

### 10.4 Escalation Required

None. All edge cases covered by existing guidance and error taxonomy.

---

## 11. WebSocket Real-Time API

In addition to REST, the API module provides WebSocket support for real-time updates. WebSocket is **additive** — all functionality remains accessible via REST.

### 11.1 WebSocket Endpoint

| Path | Protocol | Description |
|------|----------|-------------|
| `/ws` | WebSocket | Real-time event subscription |

### 11.2 Connection Lifecycle

```
1. Client connects to /ws
2. Client sends: {"type": "auth", "payload": {"token": "<jwt_or_api_key>"}}
3. Server responds: {"type": "auth_ok", "payload": {"player_id": "..."}}
   OR: {"type": "auth_failed", "payload": {"code": "...", "message": "..."}}
4. Client subscribes: {"type": "subscribe", "payload": {"channel": "match", "match_id": "..."}}
5. Server pushes events as they occur
6. Client can ping: {"type": "ping"} → Server responds: {"type": "pong"}
7. Connection closes on timeout, explicit close, or auth revocation
```

### 11.3 Channels and Events

| Channel | Subscription Params | Events |
|---------|---------------------|--------|
| `match` | `{"match_id": "uuid"}` | `match_update`, `opponent_moved`, `match_ended` |
| `energy` | (none) | `energy_update` (pushed on regen tick) |
| `matchmaking` | (none) | `matchmaking_found`, `matchmaking_timeout` |
| `events` | (none) | `event_started`, `event_ended` |

### 11.4 Event Payloads

```python
# Match Update Event
{
    "type": "match_update",
    "payload": {
        "match_id": "...",
        "board": [[1, 2, 3, ...], ...],  # 8x8 grid
        "scores": {"player1_id": 1500, "player2_id": 1200},
        "current_turn": "player1_id",
        "moves_remaining": {"player1_id": 8, "player2_id": 9}
    },
    "correlation_id": "cc_...",
    "timestamp": "2026-02-05T18:30:00Z"
}

# Energy Update Event
{
    "type": "energy_update",
    "payload": {
        "hearts": 4,
        "max_hearts": 5,
        "next_regen_at": "2026-02-05T19:00:00Z",
        "time_to_next_seconds": 1800
    },
    "correlation_id": "cc_...",
    "timestamp": "2026-02-05T18:30:00Z"
}

# Matchmaking Found Event
{
    "type": "matchmaking_found",
    "payload": {
        "match_id": "...",
        "opponent_id": "...",
        "opponent_username": "...",
        "opponent_elo": 1050
    },
    "correlation_id": "cc_...",
    "timestamp": "2026-02-05T18:30:00Z"
}
```

### 11.5 WebSocket Integration Pattern

WebSocket handlers listen to domain events and push to subscribers. Modules do NOT import WebSocket code:

```python
# src/presentation/websocket/match_handler.py
class MatchWebSocketHandler:
    """Bridges match domain events to WebSocket push."""

    def __init__(
        self,
        ws_manager: WSConnectionManagerProtocol,
        match_adapter: MatchApiAdapter,
    ):
        self._ws = ws_manager
        self._adapter = match_adapter

    async def on_move_processed(
        self,
        match_id: UUID,
        match_state: MatchState,
    ) -> None:
        """Called when a move is processed. Pushes to match subscribers."""
        message = WSMessage(
            type=WSMessageType.MATCH_UPDATE,
            payload=self._adapter.to_ws_payload(match_state),
        )
        await self._ws.broadcast_to_match(match_id, message)
```

### 11.6 Bot WebSocket Support

Bots can use WebSocket with API key authentication:
- Connect with API key in auth message
- Subscribe to match channel for real-time opponent moves
- Receive match_update events without polling

This reduces API calls for bots during active matches.

---

## Open Questions

None. All design decisions resolved based on:
- Feasibility report specifications
- Interface contracts guidance
- All dependent module artifacts
- Bot-first design requirements

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.1 | Added WebSocket real-time API (Section 11) | Orchestrator |
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent |
