# Dependency Graph — ChromaCrush

> **Version:** 1.0
> **Author:** Dependency Agent
> **Date:** 2026-02-05
> **Status:** Final
> **Framework Phase:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Module Dependency DAG](#module-dependency-dag)
3. [ASCII Dependency Diagram](#ascii-dependency-diagram)
4. [Build Order Waves](#build-order-waves)
5. [Module-by-Module Breakdown](#module-by-module-breakdown)
6. [Circular Dependency Prevention](#circular-dependency-prevention)
7. [Changelog](#changelog)

---

## Overview

This document defines the directed acyclic graph (DAG) of module dependencies for ChromaCrush. It governs:

- **Scout dispatch order** — Scouts cannot design modules that depend on artifacts that don't yet exist.
- **Coder build order** — Coders cannot implement modules that depend on interfaces that don't yet exist.
- **Karen verification order** — Verification follows the same dependency order.

### Universal First Dependencies

Before any module work begins, these must be complete:

1. **`src/core/`** — All mandatory services (config, logger, errors, data context, composition root)
2. **`src/data/`** — Repository implementations, migrations, seeds

Every module implicitly depends on `src/core/` and `src/data/`. These are not shown in the module DAG to reduce visual noise, but they are always first.

---

## Module Dependency DAG

### Dependency Matrix

| Module | Depends On (Direct) | Depended On By |
|--------|---------------------|----------------|
| `board` | — | `scoring`, `special_gems`, `board_gen`, `match` |
| `scoring` | `board` | `special_gems`, `match` |
| `special_gems` | `board`, `scoring` | `board_gen`, `match` |
| `board_gen` | `board`, `special_gems` | `match` |
| `player` | — | `auth`, `match`, `matchmaking`, `vault`, `energy`, `events`, `ads`, `payments` |
| `auth` | `player` | `match`, `api` |
| `match` | `board_gen`, `player`, `auth`, `scoring`, `special_gems` | `matchmaking`, `vault`, `events` |
| `matchmaking` | `match`, `player` | `api` |
| `vault` | `match`, `player` | `events` |
| `energy` | `player` | `events`, `match` |
| `events` | `vault`, `energy`, `match`, `player` | `ads` |
| `ads` | `player`, `events` | `payments`, `bot_earnings` |
| `bot_earnings` | `ads`, `player` | — |
| `payments` | `player`, `ads` | — |
| `api` | `auth`, `matchmaking`, `match`, `player`, `vault`, `energy`, `events`, `ads`, `payments`, `bot_earnings` | — |

### Edge Definitions

```
board → scoring         # Scoring needs board state to calculate points
board → special_gems    # Special gems operate on board positions
board → board_gen       # Board generation creates board instances
board → match           # Match manages board state during gameplay

scoring → special_gems  # Special gems use scoring for chain multipliers
scoring → match         # Match uses scoring for point calculations

special_gems → board_gen  # Board generation must know about special gem placement
special_gems → match      # Match processes special gem activations

board_gen → match       # Match uses board_gen to create game boards

player → auth           # Auth manages player authentication
player → match          # Match references players
player → matchmaking    # Matchmaking pairs players
player → vault          # Vault belongs to players
player → energy         # Energy system per player
player → events         # Events track player participation
player → ads            # Ads tracked per player
player → payments       # Payments linked to players

auth → match            # Match validates auth tokens
auth → api              # API authenticates requests

match → matchmaking     # Matchmaking creates matches
match → vault           # Vault raids triggered by match outcomes
match → events          # Events include match participation

energy → match          # Match checks energy before play
energy → events         # Events may grant energy

vault → events          # Events may include vault rewards

events → ads            # Events may trigger ad opportunities

ads → bot_earnings      # Bot earnings derived from ad revenue
ads → payments          # Payment removes ads

bot_earnings → api      # API exposes earnings/payout endpoints
```

---

## ASCII Dependency Diagram

```
                                    ┌──────────────────────────────────────────────────────────────┐
                                    │                        src/core/                              │
                                    │   (config, logger, errors, data_context, composition_root)   │
                                    └──────────────────────────────┬───────────────────────────────┘
                                                                   │
                                    ┌──────────────────────────────┴───────────────────────────────┐
                                    │                        src/data/                              │
                                    │            (repositories, migrations, seeds)                  │
                                    └──────────────────────────────┬───────────────────────────────┘
                                                                   │
                          ┌────────────────────────────────────────┼────────────────────────────────────────┐
                          │                                        │                                        │
                          ▼                                        ▼                                        │
                    ┌──────────┐                              ┌──────────┐                                  │
                    │  board   │                              │  player  │                                  │
                    └────┬─────┘                              └────┬─────┘                                  │
                         │                                         │                                        │
              ┌──────────┼──────────┐                    ┌─────────┼─────────┬─────────┐                    │
              │          │          │                    │         │         │         │                    │
              ▼          │          │                    ▼         │         │         │                    │
        ┌──────────┐     │          │              ┌──────────┐    │         │         │                    │
        │ scoring  │     │          │              │   auth   │    │         │         │                    │
        └────┬─────┘     │          │              └────┬─────┘    │         │         │                    │
             │           │          │                   │          │         │         │                    │
             ▼           ▼          │                   │          ▼         ▼         ▼                    │
      ┌──────────────────────┐      │                   │    ┌──────────┐ ┌──────────┐ │                    │
      │    special_gems      │      │                   │    │  energy  │ │  vault   │ │                    │
      └──────────┬───────────┘      │                   │    └────┬─────┘ └────┬─────┘ │                    │
                 │                  │                   │         │            │       │                    │
                 ▼                  │                   │         │            │       │                    │
          ┌──────────┐              │                   │         │            │       │                    │
          │ board_gen│              │                   │         │            │       │                    │
          └────┬─────┘              │                   │         │            │       │                    │
               │                    │                   │         │            │       │                    │
               └────────────────────┼───────────────────┼─────────┼────────────┼───────┘                    │
                                    │                   │         │            │                            │
                                    ▼                   ▼         ▼            ▼                            │
                              ┌─────────────────────────────────────────────────────┐                       │
                              │                      match                          │                       │
                              └──────────────────────────┬──────────────────────────┘                       │
                                                         │                                                  │
                         ┌───────────────────────────────┼───────────────────────────────┐                  │
                         │                               │                               │                  │
                         ▼                               ▼                               ▼                  │
                  ┌──────────────┐                ┌──────────────┐                (vault, energy)           │
                  │  matchmaking │                │    events    │◄───────────────────────┘                 │
                  └──────┬───────┘                └──────┬───────┘                                          │
                         │                               │                                                  │
                         │                               ▼                                                  │
                         │                         ┌──────────┐                                             │
                         │                         │   ads    │◄────────────────────────────────────────────┘
                         │                         └────┬─────┘
                         │                              │
                         │                              ▼
                         │                       ┌──────────┐
                         │                       │ payments │
                         │                       └────┬─────┘
                         │                            │
                         └──────────────┬─────────────┘
                                        │
                                        ▼
                                  ┌──────────┐
                                  │   api    │
                                  └──────────┘
```

### Simplified Layer View

```
Layer 0 (Foundation):  src/core/ → src/data/

Layer 1 (Leaf Nodes):  board   player
                         │        │
Layer 2:               scoring   auth   energy
                         │        │       │
Layer 3:             special_gems │       │
                         │        │       │
Layer 4:               board_gen  │       │
                         │        │       │
Layer 5:               ──────► match ◄────┴───── vault
                                 │
Layer 6:               matchmaking   events
                                        │
Layer 7:                              ads
                                        │
Layer 8:                     payments   bot_earnings
                                        │
Layer 9 (Terminal):                   api
```

---

## Build Order Waves

### Phase 1 (Scouting) — Artifact Production Order

#### Wave 1: Foundation Modules (No Inter-Module Dependencies)
Scout these first. They depend only on core services.

| Module | Complexity | Notes |
|--------|------------|-------|
| `board` | Medium | Core match-3 grid logic. No module dependencies. |
| `player` | Low | Basic account/profile CRUD. No module dependencies. |

**Parallel execution:** Yes — these two modules have no dependencies on each other.

#### Wave 2: First Dependents
Scout these after Wave 1 artifacts exist.

| Module | Depends On | Complexity | Notes |
|--------|------------|------------|-------|
| `scoring` | board | Low | Needs board state definitions from board artifact. |
| `auth` | player | Medium | Needs player entity definitions from player artifact. |
| `energy` | player | Low | Needs player entity definitions from player artifact. |

**Parallel execution:** Yes — `scoring` depends on `board`; `auth` and `energy` depend on `player`. No cross-dependencies within this wave.

#### Wave 3: Second-Order Dependents
Scout these after Wave 2 artifacts exist.

| Module | Depends On | Complexity | Notes |
|--------|------------|------------|-------|
| `special_gems` | board, scoring | Medium | Needs both board state and scoring interfaces. |
| `vault` | player | Medium | Needs player entity. Could be Wave 2 but grouped here for complexity balance. |

**Parallel execution:** Yes — `special_gems` depends on Wave 1+2; `vault` depends on Wave 1.

#### Wave 4: Third-Order Dependents
Scout these after Wave 3 artifacts exist.

| Module | Depends On | Complexity | Notes |
|--------|------------|------------|-------|
| `board_gen` | board, special_gems | High | Needs complete board and special_gems interfaces. |

**Parallel execution:** Single module wave.

#### Wave 5: Match Core
Scout this after Wave 4 artifacts exist.

| Module | Depends On | Complexity | Notes |
|--------|------------|------------|-------|
| `match` | board_gen, player, auth, scoring, special_gems, energy | Medium | Central gameplay coordinator. Heavy dependencies. |

**Parallel execution:** Single module wave (critical path).

#### Wave 6: Match Consumers
Scout these after Wave 5 artifact exists.

| Module | Depends On | Complexity | Notes |
|--------|------------|------------|-------|
| `matchmaking` | match, player | Medium | Pairs players for matches. |
| `events` | vault, energy, match, player | Medium | Coordinates special events. |

**Parallel execution:** Yes — both depend on match but not on each other.

#### Wave 7: Monetization Layer
Scout these after Wave 6 artifacts exist.

| Module | Depends On | Complexity | Notes |
|--------|------------|------------|-------|
| `ads` | player, events | Low | Ad integration. |

**Parallel execution:** Single module wave.

#### Wave 8: Payment & Earnings Layer
Scout these after Wave 7 artifact exists.

| Module | Depends On | Complexity | Notes |
|--------|------------|------------|-------|
| `payments` | player, ads | Low | $1 tier purchase for ad-free. |
| `bot_earnings` | ads, player | Medium | Bot revenue share tracking, payout requests. |

**Parallel execution:** Yes — both depend on `ads` but not on each other.

#### Wave 9: API Gateway
Scout this last. It depends on all modules.

| Module | Depends On | Complexity | Notes |
|--------|------------|------------|-------|
| `api` | auth, matchmaking, match, player, vault, energy, events, ads, payments, bot_earnings | Medium | Exposes all functionality via REST. |

**Parallel execution:** Single module wave (terminal node).

---

### Phase 2 (Implementation) — Coder Build Order

Same wave structure applies. Key differences:

1. **Wave 0 (Before All Modules):** Implement `src/core/` and `src/data/` completely.
2. **Same dependency ordering:** Coders cannot implement a module until all its dependencies are implemented.
3. **CLI commands:** Built alongside each module implementation.

```
Wave 0: src/core/ → src/data/
Wave 1: board, player
Wave 2: scoring, auth, energy
Wave 3: special_gems, vault
Wave 4: board_gen
Wave 5: match
Wave 6: matchmaking, events
Wave 7: ads
Wave 8: payments, bot_earnings
Wave 9: api
```

---

## Module-by-Module Breakdown

### board

**Category:** Core Game Logic
**Build Wave:** 1 (Leaf Node)

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | None |
| Core Services | config, logger, errors |
| Repository Dependencies | `BoardStateRepository` (owns) |

**Interface Provided:**
- Board state representation (8x8 grid)
- Match detection algorithms
- Cascade simulation
- Board validation

**Notes:** Foundation module. All gameplay modules ultimately depend on board state definitions.

---

### scoring

**Category:** Core Game Logic
**Build Wave:** 2

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `board` |
| Core Services | config, logger, errors |
| Repository Dependencies | `ScoringConfigRepository` (owns), reads `BoardStateRepository` |

**Interface Provided:**
- Point calculation
- Chain multipliers
- Score state

**Notes:** Depends on board for understanding what constitutes a match and cascade length.

---

### special_gems

**Category:** Core Game Logic
**Build Wave:** 3

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `board`, `scoring` |
| Core Services | config, logger, errors |
| Repository Dependencies | `SpecialGemConfigRepository` (owns) |

**Interface Provided:**
- Special gem types (Line Blast, Radial Bomb, Chromatic Orb)
- Activation effects
- Fusion rules

**Notes:** Must understand both board positions and scoring multipliers for fusion bonuses.

---

### board_gen

**Category:** Core Game Logic
**Build Wave:** 4

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `board`, `special_gems` |
| Core Services | config, logger, errors |
| Repository Dependencies | `BoardGenConfigRepository` (owns) |

**Interface Provided:**
- Seeded board generation
- Cascade potential tuning
- No-initial-match guarantee

**Notes:** Highest complexity core module. Needs special_gems interface to correctly place starting specials.

---

### player

**Category:** Account Management
**Build Wave:** 1 (Leaf Node)

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | None |
| Core Services | config, logger, errors, data_context |
| Repository Dependencies | `PlayerRepository` (owns), `EnergyStateRepository` (owns) |

**Interface Provided:**
- Player creation/update/deletion
- Stats management
- Preferences
- Bot vs human distinction

**Notes:** Foundation module for all account-related functionality.

---

### auth

**Category:** Security
**Build Wave:** 2

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `player` |
| Core Services | config, logger, errors |
| Repository Dependencies | `SessionRepository` (owns), `ApiKeyRepository` (owns), reads `PlayerRepository` |

**Interface Provided:**
- JWT token generation/validation
- API key generation/validation
- Session management

**Notes:** Dual auth system for humans (JWT) and bots (API keys).

---

### energy

**Category:** Engagement Mechanics
**Build Wave:** 2

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `player` |
| Core Services | config, logger, errors |
| Repository Dependencies | `EnergyStateRepository` (shared ownership with player) |

**Interface Provided:**
- Heart count management
- Regeneration timers
- Daily streak tracking

**Notes:** Energy state is co-located with player but energy module owns the business logic.

---

### vault

**Category:** Progression
**Build Wave:** 3

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `player` |
| Core Services | config, logger, errors |
| Repository Dependencies | `VaultArtifactRepository` (owns), `VaultShieldRepository` (owns), reads `PlayerRepository` |

**Interface Provided:**
- Artifact collection
- Raid mechanics
- Shield management

**Notes:** Could be Wave 2, placed in Wave 3 for complexity balancing with scouts.

---

### match

**Category:** Game Flow
**Build Wave:** 5

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `board_gen`, `player`, `auth`, `scoring`, `special_gems`, `energy` |
| Core Services | config, logger, errors, data_context |
| Repository Dependencies | `MatchRepository` (owns), reads from all dependency repositories |

**Interface Provided:**
- Match creation
- Move processing
- Turn management
- Match completion

**Notes:** Central coordinator. Critical path module. Most dependencies of any module.

---

### matchmaking

**Category:** Multiplayer
**Build Wave:** 6

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `match`, `player` |
| Core Services | config, logger, errors |
| Repository Dependencies | `MatchmakingQueueRepository` (owns, Redis-backed), reads `PlayerRepository`, reads `MatchRepository` |

**Interface Provided:**
- ELO-based pairing
- Queue management
- Separate human/bot/mixed pools

**Notes:** Heavy Redis usage for real-time queue operations.

---

### events

**Category:** Engagement Mechanics
**Build Wave:** 6

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `vault`, `energy`, `match`, `player` |
| Core Services | config, logger, errors |
| Repository Dependencies | `EventRepository` (owns), `EventParticipantRepository` (owns) |

**Interface Provided:**
- Flash event management
- Season tracking
- Leaderboard snapshots

**Notes:** Coordinates multiple systems for special events.

---

### ads

**Category:** Monetization
**Build Wave:** 7

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `player`, `events` |
| Core Services | config, logger, errors |
| Repository Dependencies | `AdImpressionRepository` (owns), reads `PlayerRepository` |

**Interface Provided:**
- Ad opportunity triggers
- Impression tracking
- Reward distribution

**Notes:** Third-party integration wrapper.

---

### payments

**Category:** Monetization
**Build Wave:** 8

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `player`, `ads` |
| Core Services | config, logger, errors |
| Repository Dependencies | `PaymentRepository` (owns), `PurchaseRepository` (owns) |

**Interface Provided:**
- $1 tier purchase
- Ad-free status management
- Receipt validation

**Notes:** Third-party payment processor integration.

---

### bot_earnings

**Category:** Monetization
**Build Wave:** 8

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | `ads`, `player` |
| Core Services | config, logger, errors |
| Repository Dependencies | `EarningsLedgerRepository` (owns), `PayoutRequestRepository` (owns), reads `PlayerRepository`, reads `AdImpressionRepository` |

**Interface Provided:**
- Revenue attribution (match → ad impressions → bot share)
- Earnings balance tracking
- Payout request management
- Earnings history/reporting

**Notes:** Tracks bot share of ad revenue. Initial implementation tracks earnings only — actual payout integration deferred. Bot owners can view balance; manual payouts until automated integration added.

---

### api

**Category:** Presentation
**Build Wave:** 9 (Terminal Node)

| Dependency Type | Dependencies |
|-----------------|--------------|
| Module Dependencies | All modules |
| Core Services | All core services |
| Repository Dependencies | None directly (all access through modules) |

**Interface Provided:**
- REST endpoints for all functionality
- OpenAPI documentation
- Bot-first design

**Notes:** Final integration point. Does not own any data — pure coordination and response shaping.

---

## Circular Dependency Prevention

### Prevention Rules

1. **Unidirectional Flow.** Dependencies flow in one direction only. If A depends on B, B must never depend on A.

2. **Event-Based Decoupling.** When bidirectional communication is needed, use events:
   ```
   # WRONG: Circular dependency
   match imports vault  # for raid triggers
   vault imports match  # to read match outcomes

   # RIGHT: Event-based decoupling
   match emits MatchCompletedEvent
   vault subscribes to MatchCompletedEvent
   ```

3. **Interface Segregation.** Depend on Protocol interfaces, not concrete implementations:
   ```python
   # vault depends on the interface, not the match module
   class MatchOutcomeProvider(Protocol):
       async def get_outcome(self, match_id: str) -> MatchOutcome: ...
   ```

4. **Shared Data Through Data Layer.** When two modules need the same data, one owns it and the other reads through the data layer:
   ```
   # player owns PlayerRepository (write)
   # vault reads PlayerRepository (read-only)
   # No module-to-module import needed
   ```

### Detection Procedure

If you suspect a circular dependency during artifact design or implementation:

1. **Draw the graph.** List your module and all its imports. Then list all modules that import your module.

2. **Check for cycles.** If any import chain leads back to your module, you have a cycle.

3. **Stop immediately.** Do not attempt to "work around" the cycle.

4. **Escalate.** Report to the Orchestrator with:
   - The modules involved
   - The direction of dependencies you need
   - Why each direction seems necessary

### Resolution Patterns

When a cycle is detected, the Dependency Agent (via Orchestrator) will apply one of these patterns:

| Pattern | When to Use | Example |
|---------|-------------|---------|
| **Extract Interface** | Both modules need to call each other's methods | Extract shared Protocol to `src/core/interfaces/` |
| **Event Bus** | One module needs to react to another's state changes | Module A emits event, Module B subscribes |
| **Shared Data** | Both modules need the same underlying data | One module owns data, other reads via repository |
| **Merge Modules** | The "two" modules are actually one logical unit | Combine into single module |
| **Introduce Mediator** | Complex coordination between multiple modules | New orchestration module that depends on all |

### Prohibited Patterns

- **Import gymnastics** (conditional imports, import inside functions to avoid cycles)
- **Global state sharing** (modules communicating through shared globals)
- **Runtime wiring** (one module dynamically discovering another)
- **Callback registration** (Module A registers callback with Module B that calls back into A)

---

## Changelog

| Date | Version | Change | Raised By |
|------|---------|--------|-----------|
| 2026-02-05 | 1.0 | Initial dependency graph from feasibility report | Dependency Agent |

---

*This document is a living artifact. Updates are committed by the Orchestrator when edge cases require dependency graph modifications.*
