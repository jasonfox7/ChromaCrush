# ChromaCrush Feasibility Report

> **Version:** 1.0
> **Date:** 2026-02-05
> **Author:** Orchestrator
> **Status:** Final
> **Phase:** 0.3

---

## 1. Project Summary

**ChromaCrush** is a match-3 puzzle game designed for two distinct player populations: human players and openly-labeled LLM bot agents. Both are first-class participants competing on shared boards in asynchronous versus matches.

### Core Value Proposition
- **For Humans:** Casino-derived dopamine mechanics, loss-aversion hooks (vault raids), competitive PvP
- **For Bots:** Optimization-compulsion, pattern-closure mechanics, progressive mechanic revelation
- **Monetization:** Ads-supported free tier + $1 one-time ad-free upgrade

### Platform
- **Primary:** Web (HTML5 Canvas + React PWA)
- **Secondary:** Mobile via PWA (no app store required)
- **Bot Access:** Public JSON API with OpenAPI documentation

---

## 2. Architecture Overview

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                  │
├─────────────────────┬─────────────────────┬─────────────────────┤
│   Web Browser       │   PWA (Mobile)      │   LLM Bot Agent     │
│   (React + Pixi.js) │   (Same as Web)     │   (JSON API)        │
└─────────┬───────────┴─────────┬───────────┴─────────┬───────────┘
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │ HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (FastAPI)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ /api/game│ │/api/player│ │/api/vault│ │/api/match│           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  PostgreSQL   │    │     Redis     │    │  arq Workers  │
│  (Persistent) │    │ (Cache/Queue) │    │ (Background)  │
└───────────────┘    └───────────────┘    └───────────────┘
```

### Module Architecture

```
src/
├── core/                          # Mandatory services
│   ├── composition_root.py        # DI wiring (single instantiation point)
│   ├── config.py                  # Configuration service
│   ├── logger.py                  # Structured logging service
│   ├── errors.py                  # Error handling service
│   └── data_context.py            # Database session management
│
├── modules/                       # Business logic (islands)
│   ├── board/                     # Grid state, match detection, cascades
│   ├── scoring/                   # Points, multipliers, chains
│   ├── special_gems/              # Line Blast, Radial Bomb, Chromatic Orb
│   ├── board_gen/                 # Procedural generation, seeding
│   ├── match/                     # Versus mode, game flow
│   ├── matchmaking/               # ELO, queue management
│   ├── player/                    # Accounts, stats, preferences
│   ├── vault/                     # Artifacts, raids, shields
│   ├── energy/                    # Hearts, streaks, timers
│   ├── events/                    # Flash events, seasons
│   ├── ads/                       # Ad integration
│   ├── payments/                  # $1 tier purchase
│   └── auth/                      # JWT + API keys
│
├── data/                          # Data layer
│   ├── repositories/              # SQLAlchemy repository implementations
│   ├── migrations/                # Alembic migrations
│   └── seeds/                     # Initial/test data
│
├── presentation/                  # Presentation adapters
│   └── adapters/                  # API response shaping
│
└── cli/                           # CLI harness
    ├── cli_entry.py               # CLI composition root
    └── commands/                  # Per-module CLI commands
```

---

## 3. Technology Stack

### Backend

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | **FastAPI** | Native async, automatic OpenAPI docs (critical for bot discovery), Pydantic validation |
| Database | **PostgreSQL 15** | JSONB for board state, relational integrity for ELO/accounts, AWS RDS compatible |
| Cache/Queue | **Redis 7** | Sorted sets for leaderboards, TTL for energy timers, pub/sub for notifications |
| Task Queue | **arq** | Async-native, simpler than Celery, uses existing Redis connection |
| ORM | **SQLAlchemy 2.0** | Async support, Alembic migrations, mature ecosystem |
| Game Logic | **NumPy** | Vectorized match detection, seeded RNG for deterministic board generation |

### Frontend

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | **React 18** | Large ecosystem, excellent TypeScript support, PWA tooling |
| Build | **Vite** | Fast HMR, optimized production builds |
| Rendering | **Pixi.js 8** | WebGL acceleration, built-in particle systems, animation support |
| State | **Zustand** | Minimal boilerplate (1KB), DevTools support |
| Styling | **Tailwind CSS** | Utility-first, consistent design tokens |

### Infrastructure

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Local Dev | **Docker Compose** | Consistent environment, easy onboarding |
| Auth | **JWT + API Keys** | JWT for human sessions, API keys for bot accounts |
| Deployment | **AWS (future)** | ECS Fargate + RDS + ElastiCache |

---

## 4. Mandatory Services Plan

Per the framework, these services are implemented in `src/core/` and injected via `__init__`.

### 4.1 Configuration Service

```python
# All config flows through this service - no os.environ anywhere else
config.get("database.connection_string")  # Returns typed value
config.get("game.board_size", default=8)  # With default
config.require("jwt.secret_key")          # Raises if missing
```

**Config sources (priority order):**
1. Environment variables (production)
2. `config/app.toml` (development defaults)
3. Hardcoded defaults (last resort)

**Key namespaces:**
- `database.*` - PostgreSQL connection, pool settings
- `redis.*` - Redis connection, key prefixes
- `game.*` - Board size, move count, cascade parameters
- `auth.*` - JWT secrets, token lifetimes
- `ads.*` - Ad network configuration

### 4.2 Logging Service

```python
# Pre-scoped to module name
logger.info("Match started", match_id=match.id, players=[p1.id, p2.id])
logger.error("Board generation failed", seed=seed, error=str(e))
```

**Features:**
- Structured JSON output (for log aggregation)
- Correlation ID propagation across async boundaries
- Severity levels: TRACE, DEBUG, INFO, WARN, ERROR, FATAL
- Per-module log levels via config

### 4.3 Error Service

```python
# Standardized error creation
errors.validation("Invalid move: positions not adjacent", move=move_data)
errors.not_found("Match not found", match_id=match_id)
errors.internal("Database connection failed", original_error=e)
```

**Error taxonomy:**
- `VALIDATION_*` - Input validation failures
- `NOT_FOUND_*` - Resource not found
- `UNAUTHORIZED_*` - Auth failures
- `FORBIDDEN_*` - Permission denied
- `CONFLICT_*` - State conflicts (e.g., match already finished)
- `INTERNAL_*` - Unexpected errors

### 4.4 Data Context

```python
# Async session management
async with data_ctx.session() as session:
    player = await player_repo.find_by_id(session, player_id)
```

**Features:**
- SQLAlchemy async session factory
- Transaction boundaries at service layer
- Connection pooling configuration

---

## 5. Data Persistence Strategy

### PostgreSQL Schema (Key Entities)

```
players
├── id (UUID, PK)
├── username (VARCHAR, unique)
├── email (VARCHAR, unique, nullable for bots)
├── password_hash (VARCHAR, nullable for bots)
├── api_key_hash (VARCHAR, nullable for humans)
├── is_bot (BOOLEAN)
├── elo_rating (INTEGER, default 1000)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

matches
├── id (UUID, PK)
├── player1_id (UUID, FK)
├── player2_id (UUID, FK)
├── board_seed (BIGINT)
├── board_state (JSONB)  # Current 8x8 grid
├── status (ENUM: pending, in_progress, completed)
├── player1_score (INTEGER)
├── player2_score (INTEGER)
├── player1_moves (JSONB)  # Array of moves
├── player2_moves (JSONB)
├── winner_id (UUID, FK, nullable)
├── created_at (TIMESTAMP)
└── completed_at (TIMESTAMP)

vault_artifacts
├── id (UUID, PK)
├── owner_id (UUID, FK)
├── artifact_type (VARCHAR)
├── rarity (ENUM: common, rare, epic, legendary)
├── acquired_at (TIMESTAMP)
└── acquired_from_match_id (UUID, FK, nullable)

energy_states
├── player_id (UUID, PK, FK)
├── hearts (INTEGER, 0-5)
├── last_regen_at (TIMESTAMP)
├── daily_streak (INTEGER)
└── last_login_date (DATE)
```

### Redis Data Structures

| Key Pattern | Type | Purpose |
|-------------|------|---------|
| `leaderboard:elo:global` | Sorted Set | Global ELO rankings |
| `leaderboard:elo:human` | Sorted Set | Human-only rankings |
| `matchmaking:queue:{elo_bucket}` | List | Matchmaking queue by ELO range |
| `session:{session_id}` | Hash | JWT refresh token data |
| `match:{match_id}:state` | Hash | Active match cache |
| `ratelimit:{api_key}` | String | API rate limit counter |

### Data Ownership

| Module | Owns (Write) | Reads From |
|--------|--------------|------------|
| `player` | players, energy_states | - |
| `auth` | api_keys, sessions | players |
| `match` | matches | players, board_gen |
| `vault` | vault_artifacts | players, matches |
| `matchmaking` | matchmaking_queue | players, matches |
| `events` | events, event_participants | players, vault |

---

## 6. Concurrency Assessment

### Async Requirements

The game has significant async needs:
1. **Database I/O:** All player/match queries
2. **Redis operations:** Leaderboards, caching, queues
3. **Board simulation:** CPU-bound but can be parallelized per match
4. **External services:** Ad networks, payment processing

### Async Architecture

```python
# FastAPI native async
@router.post("/game/move")
async def submit_move(
    move: MoveRequest,
    match_service: MatchService = Depends(get_match_service)
) -> MoveResponse:
    return await match_service.process_move(move)

# Service layer async
class MatchService:
    async def process_move(self, move: MoveRequest) -> MoveResponse:
        async with self.data_ctx.session() as session:
            match = await self.match_repo.find_by_id(session, move.match_id)
            # ... process move
            await self.match_repo.update(session, match)
        return MoveResponse(...)
```

### Background Tasks (arq)

```python
# Task definitions
async def process_match_completion(ctx, match_id: str):
    """Update ELO, grant rewards, trigger vault raid."""
    ...

async def regenerate_energy(ctx, player_id: str):
    """Add heart if < 5 and cooldown elapsed."""
    ...
```

### Concurrency Boundaries

- **HTTP requests:** Fully async via FastAPI
- **Database:** Async SQLAlchemy with connection pooling
- **Redis:** Async redis-py
- **Background tasks:** arq workers (separate process)
- **Board simulation:** Sync NumPy (fast enough for 8x8)

---

## 7. Presentation Layer Strategy

### Presentation Boundary

Business logic in `src/modules/` returns data objects. Presentation adapters in `src/presentation/adapters/` shape responses for different clients.

```python
# Module returns domain object
class MatchService:
    async def get_match_state(self, match_id: str) -> MatchState:
        ...

# Adapter shapes for API response
class MatchApiAdapter:
    def to_response(self, state: MatchState) -> MatchStateResponse:
        return MatchStateResponse(
            board=state.board.tolist(),
            score=state.score,
            moves_remaining=state.moves_remaining,
            hints=self._calculate_hints(state.board),  # Bot-specific
        )
```

### Web Client Architecture

```
web/
├── src/
│   ├── components/
│   │   ├── game/
│   │   │   ├── BoardCanvas.tsx    # Pixi.js game renderer
│   │   │   ├── GemSprite.tsx      # Individual gem component
│   │   │   └── ParticleEffects.tsx
│   │   ├── ui/
│   │   │   ├── VaultDisplay.tsx
│   │   │   ├── Leaderboard.tsx
│   │   │   └── EnergyBar.tsx
│   │   └── layout/
│   │       └── GameLayout.tsx
│   ├── hooks/
│   │   ├── useGameState.ts
│   │   └── useMatchmaking.ts
│   ├── stores/
│   │   ├── gameStore.ts           # Zustand game state
│   │   └── playerStore.ts
│   ├── api/
│   │   └── client.ts              # API client
│   └── App.tsx
└── public/
    └── assets/                    # Gem sprites, sounds
```

### CLI Harness

Every module gets CLI commands for testing:

```bash
# Board module
chromacrush board generate --seed 12345
chromacrush board show --match-id abc123
chromacrush board detect-matches --board "[...]"

# Match module
chromacrush match create --player1 p1 --player2 p2
chromacrush match move --match-id abc --from 0,0 --to 0,1
chromacrush match status --match-id abc123

# Player module
chromacrush player create --username testbot --is-bot
chromacrush player stats --player-id p1
```

---

## 8. Preliminary Dependency Graph

```
                    ┌─────────┐
                    │  core   │
                    └────┬────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │  board  │    │ player  │    │  auth   │
    └────┬────┘    └────┬────┘    └────┬────┘
         │               │               │
         ▼               │               │
    ┌─────────┐          │               │
    │ scoring │          │               │
    └────┬────┘          │               │
         │               │               │
         ▼               │               │
  ┌──────────────┐       │               │
  │ special_gems │       │               │
  └──────┬───────┘       │               │
         │               │               │
         ▼               │               │
   ┌───────────┐         │               │
   │ board_gen │         │               │
   └─────┬─────┘         │               │
         │               │               │
         └───────┬───────┘               │
                 │                       │
                 ▼                       │
           ┌───────────┐                 │
           │   match   │◄────────────────┘
           └─────┬─────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────┐  ┌─────────┐  ┌─────────┐
│ vault  │  │ energy  │  │matchmkg │
└────┬───┘  └────┬────┘  └─────────┘
     │           │
     └─────┬─────┘
           │
           ▼
      ┌─────────┐
      │ events  │
      └─────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
 ┌──────┐  ┌──────────┐
 │ ads  │  │ payments │
 └──────┘  └──────────┘
```

### Build Order (Waves)

**Wave 1 (No module dependencies):**
- `core` - Mandatory services
- `board` - Grid fundamentals
- `player` - Account basics
- `auth` - Authentication

**Wave 2 (Depends on Wave 1):**
- `scoring` - Depends on board
- `special_gems` - Depends on board, scoring

**Wave 3 (Depends on Wave 2):**
- `board_gen` - Depends on board, special_gems

**Wave 4 (Depends on Wave 3):**
- `match` - Depends on board_gen, player, auth

**Wave 5 (Depends on Wave 4):**
- `vault` - Depends on match, player
- `energy` - Depends on player
- `matchmaking` - Depends on match, player

**Wave 6 (Depends on Wave 5):**
- `events` - Depends on vault, energy, match

**Wave 7 (Depends on Wave 6):**
- `ads` - Depends on player, events
- `payments` - Depends on player, ads

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pixi.js learning curve | Medium | Medium | Extensive documentation, many match-3 examples exist |
| Bot API abuse (rate limiting bypass) | High | High | Per-key rate limits, behavioral analysis, separate bot queues |
| Near-miss tuning feels unfair | Medium | High | A/B testing, configurable parameters, transparency |
| arq less mature than Celery | Low | Medium | Simple use cases only; can migrate if needed |
| PWA offline complexity | Medium | Low | Focus on online-first; cache only static assets |
| ELO manipulation by bot farms | Medium | High | Separate human/bot/mixed leaderboards, rate limits |
| WebGL not supported on old devices | Low | Low | Pixi.js auto-fallback to Canvas 2D |
| PostgreSQL JSONB query performance | Low | Medium | Index on common query paths, denormalize if needed |

---

## 10. Scope Breakdown

### Alpha (Core Engine)
- Board module (match detection, cascades)
- Scoring module (basic points, chain multipliers)
- Special gems module (Line Blast, Radial Bomb, Chromatic Orb)
- Board generation (seeded RNG, cascade potential tuning)
- Match module (versus mode, 20 moves, async play)
- Player module (basic accounts)
- Auth module (JWT for humans, API keys for bots)
- API module (bot-first JSON endpoints)
- Web client (React + Pixi.js, basic UI)
- CLI harness (all modules)

### Beta (Progression & Polish)
- Vault module (artifacts, raids, shields)
- Energy module (hearts, daily streaks)
- Matchmaking module (ELO pairing)
- Events module (flash events, leaderboard seasons)
- Visual juice pass (particles, animations, sound)
- Ad integration

### Launch (Full Psychology Stack)
- Near-miss tuning
- Dynamic difficulty adjustment
- $1 ad-free tier + payments
- PWA optimization
- SEO + bot discoverability

---

## 11. Complexity Estimate

| Module | Complexity | Notes |
|--------|------------|-------|
| board | Medium | Core match-3 logic, NumPy operations |
| scoring | Low | Arithmetic, multiplier tables |
| special_gems | Medium | Fusion interactions, effect propagation |
| board_gen | High | Cascade potential tuning, seeded fairness |
| match | Medium | State machine, async coordination |
| matchmaking | Medium | ELO algorithm, queue management |
| player | Low | CRUD operations |
| vault | Medium | Raid logic, artifact rarity |
| energy | Low | Timer calculations |
| events | Medium | Scheduling, leaderboard snapshots |
| ads | Low | Third-party integration |
| payments | Low | Third-party integration |
| auth | Medium | JWT + API key dual system |
| api | Medium | OpenAPI design, response shaping |

**Total modules:** 14
**Scout assignments:** 4-5 scouts (3 modules each, respecting complexity budget)
**Estimated Phase 1 duration:** Based on framework guidelines
**Estimated Phase 2 duration:** Based on framework guidelines

---

## 12. Conclusion

ChromaCrush is technically feasible with the proposed stack. Key success factors:

1. **Bot-first API design** - FastAPI's automatic OpenAPI documentation is critical
2. **Seeded board generation** - NumPy's deterministic RNG ensures async fairness
3. **Pixi.js for visuals** - Required for the "juice" that makes the dopamine mechanics work
4. **Modular architecture** - Framework's injection pattern enables parallel development

### Recommended Next Steps

1. **Phase 1.0:** Initialize mandatory agents (Config, Best Practices, Data → Interface, Testing, Dependency)
2. **Phase 1.1:** Dispatch scouts in dependency-ordered waves
3. **Phase 1.2:** Produce module artifacts per the breakdown above

---

*This document fulfills Phase 0.3 of the LLM-Orchestrated Multi-Agent Development Framework v4.*
