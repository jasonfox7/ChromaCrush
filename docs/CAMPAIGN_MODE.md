# Campaign Mode — Technical White Paper

**Date:** 2026-02-24
**Status:** Implemented and deployed (production)
**Purpose:** Ground-truth LLM reference for all campaign mode mechanics, data flow, and file locations. Read this instead of surveying campaign files.

---

## Table of Contents

1. [Design Overview](#1-design-overview)
2. [Core Mechanic: Obstacles as Inverted Specials](#2-core-mechanic-obstacles-as-inverted-specials)
3. [Obstacle Clearing Rules](#3-obstacle-clearing-rules)
4. [Multi-HP Transmutation](#4-multi-hp-transmutation)
5. [Board Generation](#5-board-generation)
6. [Level Definitions](#6-level-definitions)
7. [Difficulty Curve](#7-difficulty-curve)
8. [Checkpoint System](#8-checkpoint-system)
9. [Backend Architecture](#9-backend-architecture)
10. [API Endpoints](#10-api-endpoints)
11. [Database Schema](#11-database-schema)
12. [Frontend Architecture](#12-frontend-architecture)
13. [Move Submission Flow](#13-move-submission-flow)
14. [Mega Gem Activation in Campaign](#14-mega-gem-activation-in-campaign)
15. [Deadlock Detection & Reshuffle](#15-deadlock-detection--reshuffle)
16. [Gravity with Obstacles](#16-gravity-with-obstacles)
17. [Obstacle Tinting (HSL)](#17-obstacle-tinting-hsl)
18. [Invincible Walls](#18-invincible-walls)
19. [Obstacle Spread (Infection)](#19-obstacle-spread-infection)
20. [Obstacle Regeneration](#20-obstacle-regeneration)
21. [Card System Integration](#21-card-system-integration)
22. [File Index](#22-file-index)

---

## 1. Design Overview

Campaign mode is a 120-level single-player progression system built on top of the existing match-3 engine. The objective is always: **clear all obstacles within a move budget**. There is no opponent, no bot, no timer pressure — pure puzzle gameplay. The system is fully server-authoritative.

Key properties:
- Obstacles reuse the two-grid gem model (`cells = 7`, `functions = 0-4`)
- **Invincible walls** (`func >= 10`) shape the board as permanent terrain (introduced level 51+)
- **Obstacle spread** infects adjacent gem cells after each move (introduced level 71+)
- **Obstacle regeneration** respawns cleared obstacles after N moves (introduced level 81+)
- The player's card loadout and mega gem inventory are the primary strategic tools
- Every 10th level is a **checkpoint** with heart cost, rewards, and failure regression
- Boards are deterministically generated from `(player_id, level_number)` so retries produce identical layouts
- Card modifiers (Phase 4C hooks) apply normally in campaign
- Lucky Rabbit (instant win card) is **disabled** in campaign (`enable_instant_win=False`)

---

## 2. Core Mechanic: Obstacles as Inverted Specials

The two-grid model encodes obstacles as `cells = 7` (OBSTACLE_COLOR) on the color grid and `functions = 0-4` on the function grid. This inverts the special gem concept:

| Entity | Color Grid (`cells`) | Function Grid (`functions`) | Behavior |
|---|---|---|---|
| Regular gem | 1-6 (color) | 0 (NEUTRAL) | Participates in matching |
| Special gem | 1-6 (color) | 1-4 (function) | When cleared, **PRODUCES** that effect |
| Mega gem | 1-6 (color) | 11-44 (encoded combo) | When cleared, **PRODUCES** mega effect |
| Obstacle | 7 (OBSTACLE) | 0-4 (required function) | Does NOT match; to be cleared, **REQUIRES** that effect |
| Invincible wall | 7 (OBSTACLE) | 10+ | Permanent terrain; **CANNOT** be cleared by any blast |

Obstacles:
- Cannot be swapped (moves involving `cells == 7` are rejected)
- Do not participate in match detection (color 7 never matches colors 1-6)
- Are immovable walls for gravity (columns partition at obstacle positions)
- Absorb blast effects that reach them (processed but not chain-reactive)

---

## 3. Obstacle Clearing Rules

The function `_obstacle_satisfied(obstacle_func, blast_func)` in `cascade.py` determines whether a blast damages an obstacle:

| Obstacle `func` | Meaning | Cleared By |
|---|---|---|
| 0 (basic glass) | No special requirement | Any special or mega blast (`blast_func != 0`) |
| 1 (H-keyed) | Requires LINE_BLAST_H | LINE_BLAST_H, or any mega whose decoded pair contains 1 |
| 2 (V-keyed) | Requires LINE_BLAST_V | LINE_BLAST_V, or any mega whose decoded pair contains 2 |
| 3 (B-keyed) | Requires RADIAL_BOMB | RADIAL_BOMB, or any mega whose decoded pair contains 3 |
| 4 (O-keyed) | Requires CHROMATIC_ORB | CHROMATIC_ORB clears **all** obstacles (full board effect) |

**Important:** Regular match clears (`blast_func == 0`) NEVER damage obstacles. Only special/mega blasts can interact with them.

Mega gems satisfy keyed obstacles if either component of their encoded pair matches the obstacle's func. For example, mega value `13` (LINE_BLAST_H + RADIAL_BOMB) satisfies both func=1 and func=3 obstacles.

---

## 4. Multi-HP Transmutation

Keyed obstacles (func 1-4) have implicit multi-HP behavior through **transmutation degradation**:

1. When a blast satisfies the obstacle's requirement, it clears immediately (if func=0) or transmutes down by 1 (if func > 0).
2. A func=3 obstacle hit by a RADIAL_BOMB becomes func=2. Then func=2 → func=1 → func=0 → cleared.
3. A "wrong" special that still qualifies follows the same degradation. For example, a func=3 (B-keyed) obstacle hit by a mega whose pair includes `3` will transmute.

**Retained mechanic (happy bug):** Mega gem attraction mergers can strip an obstacle of its designation down to basic glass (func=0) in one step, bypassing the normal degradation chain. This was kept as a strategic tool — players can use mega fusions near obstacles for faster clearing.

The backend tracks both event types:
- `obstacle_clearings`: positions where obstacles were completely destroyed (func was 0)
- `obstacle_transmutations`: `(position, from_func, to_func)` tuples for degradation steps

Both are returned in the API response and surfaced to the frontend via `ObstaclesUpdatedEvent`.

---

## 5. Board Generation

Boards are generated deterministically by `BoardService.create_board_with_obstacles()`:

1. **Derive seed:** `_derive_board_seed(player_id, level_number)` — hashes player UUID XORed with level number times LCG multiplier. Same player + same level = same board every retry.
2. **Place obstacles:** Iterate `obstacles` list from level definition, set `grid[r,c] = 7` and `func_grid[r,c] = f`.
3. **Fill remaining cells:** Same no-match-3 cell-by-cell strategy as PvP board generation, but skips obstacle positions. Uses `gem_colors` parameter (defaults to 6, reduced at higher levels).

The `gem_colors` parameter controls difficulty — fewer colors mean more frequent matches but potentially less strategic depth.

---

## 6. Level Definitions

All 120 levels are defined in `config/campaign_levels.json`. Each level is a JSON object:

```json
{
  "level": 91,
  "moves": 15,
  "gem_colors": 5,
  "objective": "clear_all_obstacles",
  "is_checkpoint": false,
  "obstacles": [
    {"row": 2, "col": 0, "func": 10},
    {"row": 1, "col": 1, "func": 0},
    {"row": 1, "col": 6, "func": 2}
  ],
  "obstacle_spread": {"chance": 0.25, "func": 0, "max_per_turn": 2},
  "obstacle_regen": {"after_moves": 6}
}
```

Fields:
- `level`: Integer 1-120
- `moves`: Move budget for this level
- `gem_colors`: Number of gem colors (6 default, reduced at higher levels)
- `objective`: Always `"clear_all_obstacles"` (only objective type implemented)
- `is_checkpoint`: Boolean (true for levels 10, 20, 30, ..., 120)
- `heart_cost`: Hearts consumed on start (checkpoint levels only, typically 1)
- `reward`: Checkpoint reward object (see section 8)
- `obstacles`: Array of `{row, col, func}` placement definitions. `func >= 10` = invincible wall
- `obstacle_spread` *(optional)*: Infection config — `{chance, func, max_per_turn}` (see section 19)
- `obstacle_regen` *(optional)*: Regeneration config — `{after_moves}` (see section 20)

Generated by `scripts/gen_campaign_levels.py`.

---

## 7. Difficulty Curve

Progressive difficulty across 120 levels:

| Level Range | New Mechanics | Obstacles | Move Budget | Notes |
|---|---|---|---|---|
| 1-10 | — | 2-8, func=0 only | 30→23 | Introduction. **CP 10**: common card pack |
| 11-20 | — | 4-8, func=0-1 | 25→22 | H-keyed obstacles. **CP 20**: 1000 gold |
| 21-30 | — | 5-8, func=0-2 | 23→22 | V-keyed obstacles. **CP 30**: rare card pack |
| 31-50 | — | 6-10, func=0-3 | 22→20 | B-keyed obstacles. **CP 40**: 2000 gold, **CP 50**: epic card pack |
| 51-60 | **Invincible walls** | Walls + 6-10 clearable | 22→20 | Wall patterns: gravity_wall, funnel, corner_walls. **CP 60**: 3000 gold |
| 61-70 | **Layered shells** | Concentric rings + walls (66+) | 21→20 | Outer ring glass, inner ring keyed. **CP 70**: 1 mega gem |
| 71-80 | **Obstacle spread** | 10-12 + infection | 22→18 | Adjacent cells become obstacles. Walls from 76+. **CP 80**: 4000 gold |
| 81-90 | **Obstacle regen** | 10-14 + respawning (as glass) | 20→18 | Cleared obstacles return as basic glass after 6-8 moves. Walls from 86+. **CP 90**: legendary card pack |
| 91-100 | **Combined** | Walls + spread + regen | 18→16 | All mechanics active. Regen every 6 moves. **CP 100**: 5000 gold |
| 101-110 | **Harder combined** | Shells + walls + spread + regen | 20→16 | 5 gem colors, no glass obstacles. Regen every 6 moves. **CP 110**: 10 mega gems |
| 111-120 | **Boss gauntlet** | All mechanics, tightest budgets | 18→16 | Regen every 4 moves, 40% spread chance. **CP 120**: 10,000 gold |

The exact numbers per level are defined in `campaign_levels.json`. The table above reflects the general progression curve.

---

## 8. Checkpoint System

Every 10th level (10, 20, 30, ..., 120) is a checkpoint with three special properties:

### Heart Cost
Checkpoints cost 1 heart to attempt (deducted on `start_attempt`). Non-checkpoint levels are free. If the player has insufficient hearts, `start_attempt` raises `FORBIDDEN_INSUFFICIENT_ENERGY`.

### Rewards
Checkpoints define rewards granted on first-time completion. Reward types:

| Type | Fields | Example |
|---|---|---|
| `card_pack` | `rarity`, `count` | `{"type": "card_pack", "rarity": "common", "count": 20}` |
| `gold` | `amount` | `{"type": "gold", "amount": 1000}` |
| `mega_gem` | `item_id`, `count` | `{"type": "mega_gem", "item_id": "mega_hv", "count": 1}` |

Rewards are granted via `EconomyService` methods (`credit_gold`, `grant_card_pack`, `grant_mega_reward`). Only granted when the level was the player's current frontier (`level_number >= campaign_level`), preventing reward farming by replaying old checkpoints.

### Souls-Like Regression
Failing a checkpoint (running out of moves) triggers regression: `campaign_level = max(1, campaign_level - 5)`. This re-locks up to 5 previously completed levels, forcing the player to replay them.

Non-checkpoint failure has no regression — the player simply retries or picks a different level.

---

## 9. Backend Architecture

### CampaignService (`src/modules/campaign/service.py`)

The central service class with these dependencies injected:

| Dependency | Purpose |
|---|---|
| `board_service` | Board creation, move processing, gravity, shuffle |
| `energy_service` | Heart deduction for checkpoints |
| `card_service` | Build modifier engine for card effects |
| `scoring_service` | Score computation during cascade |
| `economy_service` | Reward granting (gold, cards, megas) |
| `board_gen_service` | Board fill during cascade |
| `player_repo` | Read/write `campaign_level` on player record |
| `campaign_repo` | CRUD for `campaign_attempts` table |

### Public API Methods

| Method | Purpose |
|---|---|
| `start_attempt(player_id, level_number)` | Validate unlock, deduct heart, generate board, persist attempt |
| `submit_move(attempt_id, player_id, move)` | Process move via shared pipeline, count obstacles, check win/lose |
| `activate_mega(attempt_id, player_id, slot_index, source)` | Activate mega/shuffle without consuming a move |
| `abandon_attempt(attempt_id, player_id)` | Mark attempt as abandoned |
| `abandon_stale_attempts(timeout_hours)` | Cleanup old in-progress attempts |
| `get_player_progress(player_id)` | Return campaign_level, max_level, active_attempt_id |
| `get_level_definition(level_number)` | Return level JSON from LevelLoader |

### Move Processing

Campaign moves use the **shared move pipeline** (`src/core/move_pipeline.py`):
- `process_move_pipeline()` for regular moves
- `process_mega_pipeline()` for mega activations

These are the same functions used by PvP `MatchService`, ensuring identical game mechanics. Campaign-specific flags:
- `deadlock_reshuffle=True` — auto-reshuffle if no valid moves remain
- `enable_instant_win=False` — Lucky Rabbit card disabled

### Entity Locking

Both `submit_move` and `activate_mega` acquire an `EntityLock` on the attempt ID before processing. This prevents race conditions from rapid taps or duplicate requests. If the lock is held, `CONFLICT_ENTITY_BUSY` is returned.

### Seed Derivation

| Seed | Derivation | Purpose |
|---|---|---|
| Board seed | `hash(player_id) XOR (level_number * LCG_MULTIPLIER)` | Deterministic board per player+level |
| Move seed | `derive_move_seed(board_seed, player_id, moves_remaining)` | Unique seed per move for cascade RNG |
| Mega seed | Move seed `XOR (slot_index * 7919) XOR (score * 104729)` | Unique per mega activation accounting for cumulative score |

---

## 10. API Endpoints

All under `/api/v1/campaign/`, JWT-authenticated.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/levels` | List all 120 levels with unlock status |
| `GET` | `/levels/{level_number}` | Get single level definition with obstacles |
| `GET` | `/progress` | Get player's `campaign_level`, `max_level`, `active_attempt_id` |
| `POST` | `/attempts` | Start new attempt (body: `{level_number}`) |
| `GET` | `/attempts/{attempt_id}` | Get attempt state (board, moves, obstacles, status) |
| `POST` | `/attempts/{attempt_id}/move` | Submit move (body: `{from_row, from_col, to_row, to_col}`) |
| `POST` | `/attempts/{attempt_id}/mega` | Activate mega (body: `{slot_index, source?}`) |
| `POST` | `/attempts/{attempt_id}/abandon` | Abandon active attempt |

### Key Response Fields (move/mega endpoints)

| Field | Type | Description |
|---|---|---|
| `valid` | bool | Whether the move produced matches |
| `new_board` | `{cells, functions}` | Server board state after processing |
| `cascade_steps` | array | Serialized cascade steps for animation |
| `applied_modifiers` | array | Card procs that triggered during this move |
| `obstacles_remaining` | int | Count of obstacle cells still on the board |
| `moves_remaining` | int | Moves left (decremented on move, NOT on mega) |
| `status` | string | `"in_progress"`, `"won"`, or `"lost"` |
| `obstacle_events` | array | `{type: "clear"/"transmute", row, col, ...}` events |
| `score_gained` | int | Points earned this move |
| `reshuffled` | bool | Whether deadlock reshuffle occurred |

---

## 11. Database Schema

### Migration: `src/data/migrations/versions/019_campaign.py`

**Table: `campaign_attempts`**

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Attempt identifier |
| `player_id` | UUID (FK → players) | Owning player |
| `level_number` | int | Campaign level being attempted |
| `board_seed` | int | Deterministic seed used for board generation |
| `board_state` | JSON | Current `{cells, functions, regen_counters?}` state |
| `moves_remaining` | int | Moves left |
| `obstacles_remaining` | int | Obstacles left to clear |
| `score` | int | Cumulative score (used for mega seed uniqueness) |
| `status` | string | `"in_progress"`, `"won"`, `"lost"`, `"abandoned"` |
| `created_at` | timestamp | Attempt start time |
| `updated_at` | timestamp | Last state update |

**Column added to `players` table:**

| Column | Type | Default | Description |
|---|---|---|---|
| `campaign_level` | int | 1 | Highest level the player has unlocked |

---

## 12. Frontend Architecture

### Screen Flow

```
MainMenuScreen
    └── "CAMPAIGN" button
         └── CampaignScreen (/campaign)
              ├── Level grid (5-column wrap, sections of 10)
              ├── Checkpoint bars (full-width reward display)
              └── Tap level →
                   └── CampaignLevelScreen (/campaign/level/:id)
                        ├── Obstacle preview grid (8×8 mini-board)
                        ├── Stats: moves, obstacles, heart cost
                        └── START button →
                             └── CampaignGameContainer (/campaign/play)
                                  ├── CampaignGame (Flame)
                                  ├── CampaignHUD (score, obstacles, moves)
                                  ├── CampaignScoreBar (left side vertical)
                                  ├── ObjectiveTooltip (fade: "Clear all obstacles")
                                  ├── CompletionOverlay (win + reward display)
                                  ├── FailedOverlay (retry + back buttons)
                                  └── ConnectionOverlay (slow connection warning)
```

### CampaignViewModel (`lib/view_models/campaign_view_model.dart`)

State machine: `idle → loading → playing → complete / failed`

Subscribes to EventBus events:
- `ScoreUpdatedEvent` → updates `myScore`
- `MovesUpdatedEvent` → updates `movesRemaining`, triggers `failed` if 0 moves + obstacles remain
- `ObstaclesUpdatedEvent` → updates `obstaclesRemaining`, triggers `complete` if 0

Public methods:
- `startLevel(levelNumber, {checkpoint, levelReward})` — resets state, calls API, transitions to `playing`
- `abandon()` — calls API, returns to `idle`
- `reset()` — return to `idle` for navigation

### CampaignGame (`lib/game/campaign_game.dart`)

`FlameGame` subclass with `GameLoadoutMixin` and `ApiCallTrackerMixin`. Identical component tree to `ChromaCrushGame` minus PvP-specific components:

```
CampaignGame
├── BackgroundLayer (ripple shader)
├── BoardLayer (8×8 gem grid + GemComponents)
├── PlayerStatusBar (hearts + mega inventory + card runes)
├── ParticleLayer (match/cascade effects)
├── InputHandler (tap-to-select + drag-to-swap)
├── AnimationSequencer (cascade step playback)
└── CascadeAnimator (visual transitions)
```

No `BotPlayerService`, no `ScoreComparisonBars`, no opponent score tracking.

### CampaignHUD (`lib/widgets/game/campaign_hud.dart`)

Bottom bar with three glass panels: SCORE, OBSTACLES, MOVES.
- Moves turn orange at ≤7, red at ≤3
- Obstacles turn orange at ≤2
- Top section: card rune panel (left) + level label (center)

### CampaignScreen (`lib/widgets/campaign/campaign_screen.dart`)

Level select grid:
- Levels grouped into sections of 10, each tinted by a cycling gem color
- 9 regular tiles in 5-column wrap + 1 checkpoint bar per section
- Tiles show: level number, lock icon (locked), checkmark (completed), glow border (current)
- Checkpoint bars show: star icon, heart cost, reward badge (card pack / gold / mega gem)
- Warning banner at top: "Campaign mode may prove difficult without card abilities."
- **Auto-scroll:** On open, the list scrolls to the section containing the player's current level

---

## 13. Move Submission Flow

```
User swaps two gems (tap-tap or drag)
    │
    ├── InputHandler validates swap is adjacent
    ├── InputHandler.state = animating (locks further input)
    ├── boardLayer.animateSwap() — optimistic visual swap
    │
    ├── POST /campaign/attempts/{id}/move
    │       Backend:
    │       ├── Acquire entity lock on attempt_id
    │       ├── Reconstruct BoardState from stored JSON
    │       ├── Build card modifier engine (optional)
    │       ├── process_move_pipeline(board, move, seed, ...)
    │       │       ├── Swap gems
    │       │       ├── Detect matches
    │       │       ├── Cascade loop (drain queue → gravity → attract → fill)
    │       │       │       └── Each step: obstacle clearing/transmutation tracked
    │       │       ├── Deadlock check → reshuffle if needed
    │       │       └── Return MoveProcessingResult
    │       ├── Count remaining clearable obstacles (excluding walls)
    │       ├── If 0 obstacles → WIN (skip spread/regen — clean victory)
    │       ├── If not won: apply obstacle spread (if level has obstacle_spread config)
    │       ├── If not won: apply obstacle regen as basic glass (tick=True, if obstacle_regen config)
    │       ├── If not won: deadlock check after spread/regen → reshuffle if needed
    │       ├── If not won: recount obstacles after spread/regen
    │       ├── Determine status: won / lost (0 moves) / in_progress
    │       ├── Persist updated board_state, moves, obstacles, score, status
    │       ├── If won: advance campaign_level, grant checkpoint reward
    │       ├── If lost + checkpoint: regress campaign_level by 5
    │       └── Return serialized response
    │
    ├── If invalid: rubber-band animation
    ├── If valid:
    │       ├── Detect win early → fire events BEFORE cascade animation
    │       ├── animationSequencer.playCascadeSteps(steps, newBoard, newFunctions)
    │       ├── boardLayer.syncToBoard(newBoard, newFunctions) — visual sync invariant
    │       ├── Fire ScoreUpdatedEvent, MovesUpdatedEvent, ObstaclesUpdatedEvent
    │       └── Fire CardProcEvent if modifiers applied
    │
    └── InputHandler.state = idle (unlock input)
```

---

## 14. Mega Gem Activation in Campaign

Mega gems do NOT consume a move. They use the player's persistent inventory (same as PvP).

| Slot | Value | Effect |
|---|---|---|
| 0 | 11 (H+H) | Place mega on random empty cell, fire H+H blast, cascade |
| 1 | 22 (V+V) | Place mega, fire V+V blast, cascade |
| 2 | 33 (B+B) | Place mega, fire B+B blast, cascade |
| 3 | 44 (O+O) | Place mega, fire O+O blast (chromatic), cascade |
| 4 | shuffle | Reshuffle all non-obstacle cells |

The seed for mega activation includes a score XOR: `derive_move_seed(...) ^ (slot * 7919) ^ (score * 104729)`. This ensures that activating the same mega type at different points in the level produces different placements.

---

## 15. Deadlock Detection & Reshuffle

After every move and mega activation, the shared pipeline calls `board_service.has_valid_moves()`. If no valid moves exist:

1. Derive reshuffle seed from current state
2. Call `board_service.shuffle_board(board, seed)` — shuffles non-obstacle cells only
3. Set `reshuffled=True` in response
4. Frontend receives `reshuffled_board` and swaps to it via `boardLayer.syncToBoard()`

Shuffle attempts up to 10 permutations to find one with valid moves. Obstacles remain fixed in place during shuffle.

---

## 16. Gravity with Obstacles

`BoardService.apply_gravity_inplace()` handles obstacles as immovable walls:

1. For each column, identify obstacle row positions
2. Segment the column at obstacle boundaries into independent sections
3. Each segment compacts independently (gems fall within their segment only)
4. Gems above an obstacle fall only to the row above it, not through it
5. New gem fill happens per-segment (each segment has its own "top" opening for spawns, except segments below an obstacle which are sealed)

This creates puzzle-relevant topology: obstacles block gem flow and create isolated pockets.

---

## 17. Obstacle Tinting (HSL)

`VisualThemeBase.obstacleColor(funcValue)` derives per-type colors from a single base grey (`#888888`):

| Func | Hue | Description | Resulting Tint |
|---|---|---|---|
| 0 | — | Base grey, no tint | `#888888` |
| 1 | 180° | Teal | H-blast obstacle |
| 2 | 90° | Chartreuse | V-blast obstacle |
| 3 | 250° | Indigo | Bomb obstacle |
| 4 | rainbow | Rainbow cycle | Chromatic orb obstacle |

HSL conversion: Lightness from base grey, fixed Saturation = 0.30, per-type Hue. Changing the base grey auto-updates all obstacle tints. Applied in `GemComponent._resolveColor()` for both shader and canvas fallback rendering paths.

---

## 18. Invincible Walls

Permanent terrain obstacles that shape the board topology but do not count toward the win condition. Introduced at level 51.

### Encoding

`cells = 7` (OBSTACLE_COLOR) + `func_grid >= 10` (WALL_FUNC_THRESHOLD). The constant `WALL_FUNC_THRESHOLD = 10` is defined in `src/modules/board/_constants.py`.

### Behavior

- **Indestructible:** `_obstacle_satisfied()` in cascade.py never matches func=10 — no blast_func satisfies it, so walls survive all effects including chromatic orb full-board clear.
- **Excluded from attraction:** `_check_special_attractions()` in mega_gems.py only considers func values 1-4 (single specials). Wall func=10 is never treated as an attraction candidate.
- **Gravity anchor:** `apply_gravity_inplace()` segments columns at all OBSTACLE_COLOR positions. Walls serve as gravity anchors identically to clearable obstacles.
- **Board shaping:** Walls create forced gem flow patterns (funnels, isolated pockets, split halves).
- **Unswappable:** Move validation rejects swaps involving cells=7.
- **Excluded from win condition:** `_count_clearable_obstacles()` masks out `func_grid >= WALL_FUNC_THRESHOLD` from the obstacle count.

### Wall Patterns (Level Generation)

| Pattern | Description | Placement |
|---|---|---|
| `gravity_wall` | Full row at row 3 with 2-col gap in center | Row 3, cols 0-2 and 5-7 |
| `funnel` | Two partial rows creating a funnel shape | Rows 2,5 × cols 0-1 and 6-7 |
| `corner_walls` | L-shaped walls in opposite corners | Top-left L + bottom-right L |

### Visual

Stone grey octagon — reads as solid wall block. Rendered via the standard gem SDF shader with different color/shape values:
- Color: `#4A4A5A` (medium cool grey, distinct from clearable obstacle tints)
- Shape: octagon (SDF shape index 5) — the most block-like shape available in the shader
- Symbol: `■` (U+25A0) in level preview grid

All wall visual properties are data-driven from `visual_theme.json` → `"wall"` section → `VisualThemeService` (`wallColor`, `wallShape`, `wallSymbol` getters).

---

## 19. Obstacle Spread (Infection)

After each move, existing obstacles "infect" adjacent regular gem cells, converting them to new obstacles. Creates urgency — players must clear faster than infection grows. Introduced at level 71.

### Level JSON Schema

```json
"obstacle_spread": {"chance": 0.25, "func": 0, "max_per_turn": 2}
```

| Field | Type | Description |
|---|---|---|
| `chance` | float (0.0-1.0) | Probability each candidate cell becomes an obstacle |
| `func` | int | Function value assigned to new obstacles (0 = basic glass) |
| `max_per_turn` | int | Maximum new obstacles created per move |

### Processing Pipeline

Called by `_apply_obstacle_spread()` in `service.py`:

1. Collect all current obstacle positions on the board
2. Find orthogonal neighbors (up/down/left/right) that are regular gems (cells 1-6, func=0)
3. Deduplicate candidates
4. Deterministic shuffle using `move_seed ^ 0xDEAD_BEEF`
5. Convert up to `max_per_turn` candidates at `chance` probability
6. Each conversion sets `grid[r,c] = OBSTACLE_COLOR` and `func_grid[r,c] = spread_func`
7. Returns `{"type": "spread", "row": r, "col": c, "func": f}` events

### Ordering

Per-move processing order: **cascade → count obstacles → WIN CHECK → spread → regen → deadlock check → recount → loss check**

Win condition is checked BEFORE spread/regen. If the cascade cleared all obstacles, the player wins immediately — spread and regen never fire. This prevents a "stolen victory" where the player clears everything but spread/regen instantly add new obstacles.

### Deadlock Protection

If spread creates obstacles that eliminate all valid moves, the board is auto-reshuffled (`move_seed ^ 0xBEEF_CAFE`).

### Mega Activation

Spread also runs after mega gem activations (same pipeline position). Does NOT run after shuffles (slot_index=4).

### Frontend

Zero frontend changes needed. Board sync via `syncToBoard()` handles new obstacle cells automatically. Spread events appear in the `obstacle_events` response array for future animation polish.

---

## 20. Obstacle Regeneration

Cleared obstacles respawn at their original position after N moves. Forces sustained pressure — players can't just clear one area and ignore it. Introduced at level 81.

### Level JSON Schema

```json
"obstacle_regen": {"after_moves": 6}
```

| Field | Type | Description |
|---|---|---|
| `after_moves` | int | Number of moves after clearing before the obstacle respawns (range: 4-8) |

### State Storage

Regen counters are stored in the `board_state` JSON column (no database migration needed):

```json
{
  "cells": [[...]],
  "functions": [[...]],
  "regen_counters": {
    "3,4": {"original_func": 2, "moves_since_cleared": 1},
    "5,2": {"original_func": 0, "moves_since_cleared": 5}
  }
}
```

### Processing Pipeline

Called by `_apply_obstacle_regen()` in `service.py`:

1. Build map of original obstacle positions from level definition (excluding walls: func >= 10)
2. For each original obstacle position:
   - If obstacle is still intact → remove from regen tracking
   - If cleared → start tracking (or increment counter if `tick=True`)
   - If counter reaches `after_moves` AND cell contains a regular gem (1-6) → respawn obstacle
3. Respawn always restores as **basic glass** (func=0), regardless of original func — a keyed obstacle comes back as glass that any special can clear
4. Returns `{"type": "regen", "row": r, "col": c, "func": 0}` events

### Tick Behavior

- `tick=True` for `_submit_move_locked` — each player move increments regen counters
- `tick=False` for `_activate_mega_locked` — megas don't count as moves for regen timing
- Shuffle branch: counters are preserved but no regen logic runs

### Design Invariants

- Invincible walls (func >= 10) are never tracked for regen — they're permanent
- Spread-created obstacles are NOT tracked for regen — only original level-defined obstacles respawn
- Regen only targets cells with regular gems (1-6), not empty cells or other obstacles
- Regen counters persist across moves via `board_state` JSON

### Frontend

Zero frontend changes needed. Board sync handles regenerated cells. Regen events appear in `obstacle_events` for future animation polish.

---

## 21. Card System Integration

Campaign fully supports the card modifier system:

1. On each move, `CampaignService` calls `card_service.build_modifier_engine(player_id)` to construct the modifier engine from equipped cards
2. The modifier engine is passed to `process_move_pipeline()` which invokes hooks at each cascade phase
3. Card procs (e.g., bonus score, extra clears, special upgrades) apply identically to PvP
4. `applied_modifiers` are returned in the API response and surfaced as `CardProcEvent` on the frontend

**Exception:** Lucky Rabbit card (`enable_instant_win=False`) is disabled in campaign. This card can trigger an instant match win in PvP, which has no meaningful equivalent in obstacle-clearing gameplay.

Periodic shuffle cards (Void Instability, Tremor, Earthquake) work in campaign via `CampaignGame.onPeriodicShuffleTriggered()`, which calls the mega activation endpoint with `slot_index=4, source='card_shuffle'`.

---

## 22. File Index

### Backend

| File | Purpose |
|---|---|
| `src/modules/campaign/service.py` | CampaignService — all campaign business logic |
| `src/modules/campaign/level_loader.py` | LevelLoader — JSON level definitions, O(1) lookup by number |
| `src/modules/api/routes/campaign.py` | 8 REST endpoints under `/api/v1/campaign/` |
| `src/modules/api/schemas/campaign.py` | Request schemas: StartAttemptRequest, CampaignMoveRequest, CampaignMegaRequest |
| `src/data/models/campaign_attempt.py` | ORM model for campaign_attempts table |
| `src/data/repositories/campaign_attempt_repository.py` | Repository: create, find, update, bulk_abandon |
| `src/data/migrations/versions/019_campaign.py` | Alembic migration: campaign_attempts table + campaign_level column |
| `config/campaign_levels.json` | 120 level definitions (obstacles, moves, rewards, spread/regen config) |
| `scripts/gen_campaign_levels.py` | Level generation script (walls, shells, spread, regen patterns) |
| `src/core/move_pipeline.py` | Shared move/mega processing pipeline (used by both PvP + campaign) |
| `src/modules/board/cascade.py` | `_obstacle_satisfied()`, `_drain_clear_queue()` with obstacle handling |
| `src/modules/board/service.py` | `create_board_with_obstacles()`, obstacle-aware gravity |
| `src/modules/board/_constants.py` | `OBSTACLE_COLOR = 7`, `WALL_FUNC_THRESHOLD = 10` |
| `tests/unit/modules/test_campaign_service.py` | Campaign service unit tests |
| `tests/unit/modules/api/test_campaign_endpoints.py` | Campaign API integration tests |

### Frontend

| File | Purpose |
|---|---|
| `lib/game/campaign_game.dart` | CampaignGame FlameGame subclass (no bot, campaign API calls) |
| `lib/view_models/campaign_view_model.dart` | State machine: idle→loading→playing→complete/failed |
| `lib/widgets/campaign/campaign_screen.dart` | Level select grid (5-column, sections, checkpoint bars) |
| `lib/widgets/campaign/campaign_level_screen.dart` | Pre-level detail (obstacle preview, stats, start button) |
| `lib/widgets/campaign/campaign_game_container.dart` | GameWidget wrapper + HUD + win/lose overlays |
| `lib/widgets/game/campaign_hud.dart` | Campaign HUD (score, obstacles, moves, card runes) |
| `lib/game/game_loadout_mixin.dart` | Shared mixin for card loadout + mega inventory (PvP + campaign) |
| `lib/navigation/app_router.dart` | Routes: `/campaign`, `/campaign/level/:id`, `/campaign/play` |

### Shared (used by both PvP and Campaign)

| File | Relevance to Campaign |
|---|---|
| `lib/game/animation_sequencer.dart` | Plays cascade step animations identically |
| `lib/game/board_layer.dart` | Renders obstacles via `GemComponent._resolveColor()` |
| `lib/game/gem_component.dart` | Obstacle tinting in shader + canvas paths |
| `lib/config/visual_theme_service.dart` | `obstacleColor(funcValue)` HSL derivation |
| `lib/services/event_bus.dart` | `ObstaclesUpdatedEvent`, `MovesUpdatedEvent`, `ScoreUpdatedEvent` |
| `lib/models/backend_contract.dart` | Campaign DTOs: `CampaignLevelSummary`, `CampaignAttemptResponse`, `CampaignMoveResponse`, etc. |
