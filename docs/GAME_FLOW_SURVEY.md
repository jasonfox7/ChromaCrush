# ChromaCrush Game Flow Survey

**Date:** 2026-02-10 (updated 2026-02-13 — schema-driven refactor, updated 2026-02-15 — queue-based drain + flat frontend orchestrator, updated 2026-02-22 — unified move pipeline for PvP + campaign)
**Purpose:** Ground-truth survey of the current move/cascade/special-gem flow across backend and frontend. This documents what the code actually does, not what it should do.

---

## Bugs and Edge Cases

### BUG 1 — FIXED: Special gems caught in flood-fill expansion are silently destroyed without activating
**Status:** Resolved (2026-02-10). Implementation superseded by queue-based drain (2026-02-15) — specials are now activated inline as their positions are dequeued in `_drain_clear_queue`.

---

### BUG 2 — FIXED: Swapping two specials doesn't produce a fusion — only one fires
**Status:** Resolved (2026-02-10)
**Fix:** Added early branch in `_execute_swap_activation`: when both `from_func != 0` and `to_func != 0`, delegates to new `_execute_fusion_activation()`. Encodes both functions as a mega gem value via `encode_mega_gem()`, computes combined blast centered on `from_pos`, chain-reacts adjacent specials, applies gravity + attractions + fill.

---

### BUG 3 — FIXED: Mega gems don't chain-trigger from blasts
**Status:** Resolved (2026-02-10). Implementation superseded by queue-based drain (2026-02-15) — `_drain_clear_queue` handles both specials and megas uniformly; the old `_find_triggered_specials` guard is gone.

---

### BUG 4 — FIXED: Pre-clear attraction can cause visual glitch (gem disappears then reappears)
**Status:** Resolved (2026-02-10). Root cause eliminated by queue-based drain (2026-02-15) — pre-clear attractions no longer exist. The API serialization still filters attraction center positions from removals as a safety measure.

---

### BUG 5 — FIXED: `animateAttraction` shrinks gems to zero instead of glowing
**Status:** Resolved (2026-02-10)
**Fix:** Added `animatePulse()` to `GemComponent` (scale 1.0 → 1.2 → 1.0). Replaced `animateAppear` calls in `board_layer.dart` `animateAttraction` with `animatePulse`. Source gems now pulse to highlight the attraction; center gem pulses to show the merge result.

---

### BUG 6 — FIXED: Special gem color on frontend relies on fragile snapshotting
**Status:** Resolved (2026-02-10)
**Fix:** Backend now sends `"color"` field in `special_gem_created` (from `matches.matches[0].gem_type`). Frontend DTO already supported it (defaulting to 0). Removed the fragile snapshot logic from `animation_sequencer.dart` — now uses `sp.color` directly.

---

### BUG 7 — FIXED: `total_matches` reports cascade depth, not actual match count
**Status:** Resolved (2026-02-10)
**Fix:** Changed `total_matches=len(cascades)` to `total_matches=sum(len(step.matches.matches) for step in cascades)` in `service.py`.

---

### BUG 8 — Expected behavior: `_expand_contiguous` collapses distinct match groups into one per color
**Status:** Not a bug — intentional "sticky clear" mechanic
**Location:** `src/modules/board/detection.py` `_expand_contiguous`

After expansion, output is one `MatchGroup` per color with `is_horizontal=True` hardcoded. Original distinct match groups (separate 3-matches, 4-matches) are collapsed. Special gem detection runs before expansion (correct). This is by design — a 3-match taking all attached same-colored gems is the intended gameplay behavior.

---

## Table of Contents

1. [Two-Grid Gem Model](#1-two-grid-gem-model)
2. [Backend: Board Module Structure](#2-backend-board-module-structure)
3. [Backend: process_move — The Critical Path](#3-backend-process_move--the-critical-path)
4. [Backend: Match Detection](#4-backend-match-detection)
5. [Backend: Special Gem Creation Rules](#5-backend-special-gem-creation-rules)
6. [Backend: Cascade Step Execution](#6-backend-cascade-step-execution)
7. [Backend: Special Gem Triggering (Chain Reactions)](#7-backend-special-gem-triggering-chain-reactions)
8. [Backend: Mega Gem Attractions](#8-backend-mega-gem-attractions)
9. [Backend: Mega Gem Effects](#9-backend-mega-gem-effects)
10. [Backend: Swap-to-Activate](#10-backend-swap-to-activate)
11. [Backend: Match Module — Move Submission Orchestration](#11-backend-match-module--move-submission-orchestration)
12. [Backend: API Serialization — cascade_steps](#12-backend-api-serialization--cascade_steps)
13. [Frontend: Move Submission Flow](#13-frontend-move-submission-flow)
14. [Frontend: Animation Sequencer — playCascadeSteps](#14-frontend-animation-sequencer--playcascadesteps)
15. [Frontend: BoardLayer Animations](#15-frontend-boardlayer-animations)
16. [Frontend: Board Sync Invariant](#16-frontend-board-sync-invariant)
17. [Data Contract: CascadeStepResponse](#17-data-contract-cascadestepresponse)
18. [Known Workarounds](#18-known-workarounds)
19. [Backend: Card Effect Hooks (Phase 4C)](#19-backend-card-effect-hooks-phase-4c)

---

## 1. Two-Grid Gem Model

Every cell on the 8x8 board has two values stored in parallel arrays:

| Grid | Values | Purpose |
|------|--------|---------|
| `grid` (cells) | 0=EMPTY, 1-6=gem colors (RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE) | Match detection reads only this |
| `func_grid` (functions) | 0=NEUTRAL, 1=LINE_BLAST_H, 2=LINE_BLAST_V, 3=RADIAL_BOMB, 4=CHROMATIC_ORB | Special gem abilities |

**Special gems** have a standard color (1-6) in `grid` AND a non-zero function in `func_grid`. They participate in same-color matches automatically because detection reads `grid` only.

**Mega gems** encode two functions in a single `func_grid` value: `funcA * 10 + funcB` where `funcA <= funcB`. Valid mega values: `{11, 12, 13, 14, 22, 23, 24, 33, 34, 44}`.

**GemType enum (backend)** uses negative values for special identifiers in MatchResult (not stored on grid):
- LINE_BLAST_H = -1, LINE_BLAST_V = -2, RADIAL_BOMB = -3, CHROMATIC_ORB = -4

**Files:**
- `src/core/types/game.py` — GemType, GemFunction, Position, Move, mega gem encode/decode
- `src/core/types/board.py` — BoardState (grid + func_grid), MatchGroup, MatchResult

---

## 2. Backend: Board Module Structure

`BoardService` (`src/modules/board/service.py`) inherits from four mixins:

| Mixin | File | Responsibility |
|-------|------|----------------|
| `_DetectionMixin` | `detection.py` | `detect_matches`, `_determine_special_gem` (delegates to EffectInterpreter), `_expand_contiguous` |
| `_SpecialGemsMixin` | `special_gems.py` | `_calculate_special_effect_positions` (delegates to EffectInterpreter), `_clear_positions_inplace`, `_clear_matches_inplace` |
| `_CascadeMixin` | `cascade.py` | `_drain_clear_queue` (FIFO clear + chain reactions), `_run_cascade_step_inplace` (7 phases via CascadeContext), `_execute_swap_activation`, `_execute_fusion_activation`, `_create_activation`, `_try_attraction_only_step_inplace`, `_rebuild_inert_megas` |
| `_MegaGemsMixin` | `mega_gems.py` | `_check_special_attractions`, `_process_attractions_inplace`, `_calculate_mega_gem_effect_positions` (delegates to EffectInterpreter) |

`BoardService.__init__` loads `config/board_rules.json` via `schema_loader.load_board_rules()` and creates `self._effect_interp = EffectInterpreter(schema)`. All special gem creation rules, effect areas, and mega gem combos are now schema-driven — the old if/elif trees have been deleted.

Constants (`_constants.py`): `MAX_CASCADE_STEPS = 100`, `LCG_MULTIPLIER = 1103515245`, `LCG_INCREMENT = 12345`, `LCG_MASK = 0x7FFFFFFF`.

**New files:**
| File | Contents |
|------|----------|
| `config/board_rules.json` | JSON schema defining board dimensions, special creation rules, effect areas, mega combos, attraction config, chain reaction config |
| `src/modules/board/schema_loader.py` | `load_board_rules()`, `validate_board_rules()` — loads and validates the JSON schema |
| `src/modules/board/effect_interpreter.py` | `EffectInterpreter` class — replaces all hardcoded if/elif trees with schema-driven dispatch |

---

## 3. Backend: process_move — The Critical Path

**File:** `src/modules/board/service.py` lines 329-501

```
process_move(board, move, seed) -> MoveProcessingResult
```

### Step-by-step (refactored 2026-02-15):

1. **Swap gems.** `swap_gems(board, move)` — swaps both `grid` and `func_grid` at the two positions.

2. **Post-swap attraction check.** `_check_special_attractions(swapped)` — if the swap positioned two specials within attraction range, process the attraction immediately. Newly formed megas are added to the move-wide `inert_megas` set (they cannot activate until a future move).

3. **Detect matches.** `detect_matches(swapped)` — scans for horizontal and vertical runs of 3+ same-color gems.

4. **If no matches:**
   - If post-swap attraction was found: **move is valid** (swap-to-attract). Falls through to cascade loop.
   - Otherwise check swap-to-activate: reads `func_grid` at both swap positions.
     - Both specials: `_execute_swap_activation` (fusion).
     - One special, no attraction: invalid move.
     - Neither special: invalid move.

5. **Cascade loop setup.** Initializes `inert_megas: set[Position]`. If swap activation happened, starts from its board. Otherwise copies `swapped` once.

6. **Cascade loop** (up to `MAX_CASCADE_STEPS = 100`, all in-place mutation):
   - `detect_matches(current_board)`
   - If no matches: `_try_attraction_only_step_inplace(current_board, chain, inert_megas)`. If no attractions either, cascade is done.
   - If matches found: `_run_cascade_step_inplace(current_board, matches, chain, cascade_seed, inert_megas)`. Passes `inert_megas` through for the move-wide inert rule.
   - Board is mutated in place — no reassignment needed between steps.

7. **Return** `MoveProcessingResult` with all cascade steps, final board, total matches/cleared, special gems created.

---

## 4. Backend: Match Detection

**File:** `src/modules/board/detection.py`

### `detect_matches(board, min_length=3, expand=True) -> MatchResult`

**Horizontal scan:** For each row, walks left-to-right tracking run length. When the color changes or hits a sentinel, if run >= 3 and color > 0, records a MatchGroup.

**Vertical scan:** Same logic per column, top-to-bottom.

Only `grid` values > 0 are eligible. Empty (0) breaks runs. Special gems participate because their color is in `grid`.

**Special gem detection** (`_determine_special_gem`): Delegates to `self._effect_interp.determine_special_gem()`. Iterates `special_creation_rules` from `board_rules.json` by priority. Default rules:
1. **T/L shape** (position appears in both a horizontal and vertical match) → CHROMATIC_ORB at intersection
2. **5+ straight match** → RADIAL_BOMB at center (sorted by row,col, middle element)
3. **4-match horizontal** → LINE_BLAST_H at middle (index `len//2` when sorted)
4. **4-match vertical** → LINE_BLAST_V at middle
5. **3-match** → no special

**Flood-fill expansion** (`_expand_contiguous`): After run detection, each match group expands to all contiguous same-colored tiles adjacent to any matched position. Uses numpy boolean mask dilation: builds a color mask, seeds matched positions, then iteratively shifts (N/S/E/W) and ORs with the color mask until stable. This is the "sticky clear" mechanic — all connected same-color tiles clear, not just the strict 3+ run.

**MatchResult** carries: `matches` (tuple of MatchGroup), `total_gems_matched`, `creates_special_gem`, `special_gem_type`, `special_gem_position`.

---

## 5. Backend: Special Gem Creation Rules

When `MatchResult.creates_special_gem` is true, `_place_special_gem(board, matches)` in `service.py`:

1. Gets the match color from `matches.matches[0].gem_type`.
2. Writes color to `grid[sp.row, sp.col]`.
3. Writes function to `func_grid[sp.row, sp.col]` via `SPECIAL_TO_FUNCTION[matches.special_gem_type]`.

The special gem is placed **after** matches are cleared, so its position is in a cell that was just emptied. It keeps the match's base color and gains a function.

---

## 6. Backend: Cascade Step Execution

**File:** `src/modules/board/cascade.py` — `_run_cascade_step_inplace`

**Refactored (2026-02-15):** Replaced the 10-phase pipeline with a queue-based clear drain followed by gravity → single attraction check → fill. This eliminates ordering ambiguity at phase interaction seams (particularly between pre-clear attractions, pre-fire specials, clearing, and chain reactions).

```
_run_cascade_step_inplace(board, matches, chain, cascade_seed, inert_megas) -> (CascadeStep, gems_cleared, new_specials, next_seed, applied_modifiers)
```

Order of operations within one step:

1. **Record special gem creation** from `matches.creates_special_gem`.
   - Hook 1: `apply_special_override()` — cards can override the special type.

2. **Drain clear queue.** `_drain_clear_queue(board, matched_positions, inert_megas, trigger_color)` — FIFO `collections.deque` processes all clears and chain reactions in a single loop:
   - Seed queue with all matched positions (sorted by row, col for deterministic order).
   - For each position: read `func_grid` value BEFORE clearing, clear both grids.
   - If the position had a special/mega function (and not in inert set): compute blast positions, enqueue them, record a `SpecialActivation`.
   - Check orthogonal neighbors for specials/megas not yet processed: if found, compute blast, enqueue.
   - Repeat until queue empty.
   - Returns: `(all_cleared_positions, activations_list)`.
   - Hook 2: `get_effect_param_overrides()` — cards can boost radius/range per special.

3. **Place special gem.** `_phase_place_new_special(ctx)` — writes color and function to the cleared position. Survives this cascade step.
   - Hook 1 (cont): uses `ctx.special_override_func` if set.

4. **Gravity.** `apply_gravity_inplace(board)` — both grids mutated in lock step.

5. **Rebuild inert megas.** `_rebuild_inert_megas(board, inert_megas)` — re-scans `func_grid` for mega values (11-44) after gravity moved gems. Updates the move-wide inert set.

6. **Attraction check (single point, post-gravity).** `_check_special_attractions(board)` → `_process_attractions_inplace(board, pairs)`. Newly formed megas added to `inert_megas`.

7. **Fill.** `fill_empty_inplace(board, cascade_seed)` — random gems fill empty cells.
   - Hook 4: `get_spawn_weights()` — cards can bias gem color distribution.

8. **Card injection (post-fill).** `_phase_post_fill_injection(ctx)` — Hook 3 can inject specials. Recorded in `ctx.injected_special` for frontend animation.

**CascadeStep** records: `step_number`, `matches`, `gems_dropped`, `gems_spawned`, `board_after_fill`, `special_activations`, `special_attractions`, `injected_special`.

---

## 7. Backend: Special Gem Triggering (Chain Reactions)

**Refactored (2026-02-15):** Chain reactions are now handled entirely inside `_drain_clear_queue` in `cascade.py`. The previous multi-wave methods (`_find_triggered_specials`, `_trigger_adjacent_specials_inplace`) have been removed. The drain queue subsumes both match clearing and all chain-reaction propagation in a single FIFO loop.

### `_drain_clear_queue(board, initial_positions, inert_megas, trigger_color, modifiers) -> (all_cleared, activations)`

**File:** `src/modules/board/cascade.py`

Single FIFO `collections.deque` processes all clears and chain reactions:

1. **Seed queue** with all matched positions (sorted by row, col for deterministic order).
2. **For each position dequeued:**
   - Read `func_grid` value BEFORE clearing.
   - Clear both `grid` and `func_grid` at that position (lock step).
   - If the position had a special/mega function AND is not in the move-wide `inert_megas` set:
     - Compute blast positions via `_calculate_special_effect_positions` (or `_calculate_mega_gem_effect_positions` for megas).
     - Enqueue all blast positions not already processed.
     - Record a `SpecialActivation` (with affected positions, `is_mega`, `mega_func_value`).
   - Check orthogonal neighbors: if a neighbor has a non-zero `func_grid` value and hasn't been queued yet and isn't inert, compute its blast and enqueue.
3. **Repeat until queue is empty.** All chain reactions resolve within this single loop — no separate "wave" tracking needed.
4. **Returns:** `(all_cleared_positions: set[Position], activations: list[SpecialActivation])`.

**Key properties:**
- FIFO ordering ensures deterministic chain-reaction order (row-major seeding, breadth-first propagation).
- The `inert_megas` set prevents mega gems formed during the current move from activating (they fire on a future move).
- Hook 2 (`get_effect_param_overrides`) applies inside `_create_activation` before blast positions are computed.

### `_calculate_special_effect_positions(board, position, gem_type, trigger_color, overrides) -> set[Position]`

**File:** `src/modules/board/special_gems.py`

Delegates to `self._effect_interp.calculate_effect_positions()`. Looks up effect definition from `special_gems.functions` in `board_rules.json`. Default effects:

| Special | Effect | Schema `select` |
|---------|--------|----------------|
| LINE_BLAST_H | Entire row | `"row"` |
| LINE_BLAST_V | Entire column | `"column"` |
| RADIAL_BOMB | 3x3 square centered on position (radius 1) | `"radius"`, `radius: 1` |
| CHROMATIC_ORB | All gems matching `trigger_color`. If no trigger color, uses most common color on board. | `"color_match"`, `fallback: "most_common"` |

Source position always included in affected set.

---

## 8. Backend: Mega Gem Attractions

**File:** `src/modules/board/mega_gems.py`

### `_check_special_attractions(board) -> list[(posA, posB, centerPos)]`

Scans for pairs of special gems exactly 2 cells apart (horizontally or vertically) with a regular gem between them.

**Conditions:**
- posA has `func_grid != 0` and is not already a mega gem
- posB has `func_grid != 0` and is not already a mega gem
- center has `func_grid == 0` (regular gem) and `grid > 0` (not empty)
- None of the three positions already consumed by another attraction this scan

Scans right (+2 col) and down (+2 row) only, to avoid double-counting. Greedy: each position participates in at most one attraction per call.

### `_process_attractions_inplace(board, triples) -> list[SpecialAttraction]`

Mutates `board.func_grid` directly. For each triple:
1. Source specials lose their function (`func_grid = 0`).
2. Center gem gets `func_grid = encode_mega_gem(funcA, funcB)`.
3. **No gems are removed.** Only `func_grid` mutates. Color grid unchanged.

### Where attractions are checked:

Attractions are checked at **two points** (refactored 2026-02-15 — reduced from five):
1. **Post-swap** (in `process_move`, before cascade loop) — handles swap-to-attract: player swaps a special into attraction range of another special, forming a mega even without a color match. Newly formed megas added to the move-wide `inert_megas` set.
2. **Post-gravity** (in `_run_cascade_step_inplace`, after gravity) — handles attractions formed by gems dropping into new positions. Also checked in `_execute_swap_activation` and `_execute_fusion_activation` after their gravity phase.

The pre-clear, post-clear, and final-settled checks were removed. The queue-based drain handles chain reactions inline, eliminating the need for pre-clear and post-clear attraction checks. Attractions at the settled-board level are caught by the cascade loop's `_try_attraction_only_step_inplace` fallback.

---

## 9. Backend: Mega Gem Effects

**File:** `src/modules/board/mega_gems.py` — `_calculate_mega_gem_effect_positions`

Delegates to `self._effect_interp.calculate_mega_effect_positions()`. Looks up combo definition from `mega_gems.combos` in `board_rules.json`.

Mega gems are triggered when they're caught in a match (via `_fire_matched_mega_gems` before clear) or when they're adjacent to a cleared area (via `_trigger_adjacent_specials`).

| Mega Value | Combo | Effect |
|------------|-------|--------|
| 11 | H+H | 3 rows centered on position |
| 12 | H+V | Cross blast (entire row + entire column) |
| 13 | H+B | 3 rows centered on position |
| 14 | H+O | All target color become H, each fires (full row) |
| 22 | V+V | 3 columns centered on position |
| 23 | V+B | 3 columns centered on position |
| 24 | V+O | All target color become V, each fires (full column) |
| 33 | B+B | 5x5 area |
| 34 | B+O | All target color become B, each fires (3x3 blast) |
| 44 | O+O | Entire board |

Target color for orb combos: `trigger_color` if valid, else most common color on board.

---

## 10. Backend: Swap-to-Activate and Swap-to-Attract

**File:** `src/modules/board/cascade.py` — `_execute_swap_activation`, `_execute_fusion_activation`
**File:** `src/modules/board/service.py` — `process_move` (swap-to-attract path)

When a swap produces no matches, three paths are checked (in order):

### Swap-to-attract (post-swap attraction found):
**Added 2026-02-15.** If `process_move` detected post-swap attractions before checking matches, and no matches exist, the move is still valid. The attractions were already processed (forming an inert mega). The cascade loop continues from this board state — the mega activates on a future move.

### Single special (one gem has function, other is neutral):
1. Copy board once as mutable working copy.
2. Identify which gem is the special (`from_func != 0` preferred).
3. Trigger color = color of the other (non-special) gem.
4. `_create_activation(work, sp_pos, sp_raw, trigger_color)` — computes effect.
5. Seed drain queue with effect positions. `_drain_clear_queue` handles all clearing + chain reactions.
6. Gravity in place + rebuild inert megas + post-gravity attraction check + fill in place.

### Fusion (both gems have functions):
When both `from_func != 0` and `to_func != 0`, delegates to `_execute_fusion_activation`:
1. Copy board once as mutable working copy.
2. Encode mega value: `encode_mega_gem(GemFunction(from_func), GemFunction(to_func))`.
3. Trigger color = color of `from_pos` gem.
4. `_calculate_mega_gem_effect_positions(work, from_pos, mega_value, trigger_color)` — computes combined blast.
5. Build initial `SpecialActivation` with `mega_func_value`.
6. Seed drain queue with blast positions. `_drain_clear_queue` handles all clearing + chain reactions (additional activations appended).
7. Gravity in place + rebuild inert megas + post-gravity attraction check + fill in place.

All paths return a `CascadeStep` with `step_number=0`.

---

## 11. Backend: Move Submission Orchestration (Shared Pipeline)

**Updated 2026-02-22:** Move processing, scoring, card hooks, and deadlock handling extracted into a shared pipeline (`src/core/move_pipeline.py`). Both `MoveProcessor` (PvP) and `CampaignService` (campaign) delegate to the same functions. Seed derivation, scoring with card modifiers (Hooks 6-8), and deadlock reshuffle are no longer duplicated.

### Shared Pipeline Functions (`src/core/move_pipeline.py`)

| Function | Purpose |
|----------|---------|
| `derive_move_seed(board_seed, player_id, moves_remaining)` | Deterministic per-move seed: `(board_seed ^ player_hash ^ (moves_remaining * LCG_MULTIPLIER)) & 0x7FFFFFFF` |
| `derive_reshuffle_seed(board_seed, player_id, move_number)` | Deterministic reshuffle seed: `(board_seed ^ player_hash ^ (move_number * RESHUFFLE_MULTIPLIER)) & 0x7FFFFFFF` |
| `process_move_pipeline(board, move, seed, ...)` | Swap move: board cascade → scoring (Hook 6) → instant win check (Hook 7) → energy grant (Hook 8) → deadlock reshuffle |
| `process_mega_pipeline(board, mega_value, seed, ...)` | Mega activation: place + cascade → scoring → hooks → deadlock |

Both pipeline functions return `BoardProcessingResult` (dataclass): `move_result`, `result_board`, `score_result`, `points_earned`, `reshuffled`, `instant_win`, `hearts_earned`.

### PvP: `MoveProcessor.submit_move`

**File:** `src/modules/match/move_processor.py`

```
MoveProcessor.submit_move(match_id, player_id, move) -> (MoveSubmissionResult, MatchModel)
```

1. **Validate preconditions.** `_validate_move_preconditions` — load match, check participant, check status, check moves remaining.
2. **Build card modifiers.** `card_service.build_modifier_engine(player_id)` (async, optional).
3. **Derive seed.** `derive_move_seed(board_seed, player_id, moves_remaining)`.
4. **Process through shared pipeline.** `process_move_pipeline(board, move, seed, ..., enable_instant_win=True)` via `asyncio.to_thread()`. Returns `BoardProcessingResult` with cascade steps, score, hook results, deadlock status.
5. **Build MatchUpdate** with new board, score, moves remaining.
6. **Persist move record** to database.
7. **Check completion.** `_check_and_finalize` — if both players have 0 moves, finalize match (ELO, raids, rewards).
8. **Persist match update.**
9. **Return** `MoveSubmissionResult`.

### PvP: `MoveProcessor.process_mega_activation`

1. **Validate preconditions.** Same as submit_move.
2. **Build card modifiers.**
3. **Derive seed with slot + score XOR.** `derive_move_seed(...) ^ (slot_index * 7919) ^ (current_score * 104729)` — ensures each mega at different scores produces different placement.
4. **Process through shared pipeline.** `process_mega_pipeline(board, mega_value, seed, ..., enable_instant_win=True)` via `asyncio.to_thread()`.
5. **Persist and finalize** (same as submit_move steps 5-9).

### Campaign: `CampaignService.submit_move` / `activate_mega`

**File:** `src/modules/campaign/service.py`

Same shared pipeline with campaign-specific differences:
- `enable_instant_win=False` — Lucky Rabbit (Hook 7) disabled to prevent cheesing levels.
- Cumulative `score` tracked on `campaign_attempts` table (migration 020). Used in mega seed XOR for placement uniqueness.
- `board_gen_service` injected via composition root for deadlock reshuffle (replaces old `shuffle_board ^ 0xDEAD` hack).
- Slot 4 (user-activated full board shuffle) stays using `board_service.shuffle_board` directly — not through the pipeline.

### What stays mode-specific

| MoveProcessor (PvP) | CampaignService (Campaign) |
|---------------------|---------------------------|
| `_validate_move_preconditions` (match state, turn order) | Attempt validation (status, ownership) |
| `_check_and_finalize` (ELO, raids, rewards) | Obstacle counting, win/loss determination |
| Move record persistence, dual-player state | Level completion rewards, economy grants |
| Bot-skip modifier logic | `_derive_board_seed` (level-specific) |

**Note:** `special_effects` list in MoveSubmissionResult is initialized empty and never populated. The `special_gems` module (Wave 3) has `calculate_effect` and `calculate_fusion_effect` methods, but they are **not called** from `move_processor.py`. All special gem handling is done inside `board_service.process_move` via the mixin methods.

---

## 12. Backend: API Serialization — cascade_steps

**File:** `src/modules/api/routes/matches.py`

The API route iterates over `result.move_result.cascades` (list of `CascadeStep`) and builds `cascade_steps` JSON:

```json
{
  "step_number": int,
  "removals": [{"row": int, "col": int}, ...],
  "drops": [{"gem_type": int, "from_row": int, "from_col": int, "to_row": int, "to_col": int}, ...],
  "spawns": [{"gem_type": int, "row": int, "col": int}, ...],
  "special_gem_created": {"row": int, "col": int, "gem_type": int, "color": int} | null,
  "special_activations": [{"gem_type": int, "row": int, "col": int, "affected": [...], "is_mega": bool, "mega_func": int|null}, ...],
  "special_attractions": [{"pos_a_row": int, ..., "center_row": int, ..., "func_a": int, "func_b": int, "mega_func": int}, ...],
  "injected_special": {"row": int, "col": int, "function": int} | null
}
```

**Removals** come from `step.matches.matches` — the matched gem positions (including flood-fill expansion). Positions protected by attraction centers are filtered out to prevent visual glitches.

**special_gem_created.gem_type** is the negative GemType identifier (e.g., -1 for LINE_BLAST_H). The frontend uses `abs()` to map to GemFunction.

**special_gem_created.color** is the color of the match that created the special (from `matches.matches[0].gem_type`). The frontend uses this directly to set the gem color, avoiding fragile snapshot logic.

**special_activations[].gem_type** is also a negative GemType identifier.

**special_activations[].affected** are sorted by (row, col).

**injected_special** (added 2026-02-15): Serialized from `CascadeStep.injected_special`. When Hook 3 (Heavenly Gift, Heavy Gravity, Acid Rain) injects a special gem after fill, this field tells the frontend what was injected so it can animate the appearance. For `fire_immediately` injections, the extra gravity drops and fill spawns are appended to the step's `drops` and `spawns` arrays.

---

## 13. Frontend: Move Submission Flow

**File:** `chromacrush_app/lib/game/chroma_crush_game.dart` — `_onSwapCommitted`

1. **Block input.** `inputHandler.state = InputState.animating`.
2. **Optimistic swap animation.** `boardLayer.animateSwap(from, to)` (150ms).
3. **Submit to backend.** `apiClient.submitMove(matchId, request)`.
4. **If failed/invalid:** Rubber-band swap back. Unblock input. Return.
5. **If valid:**
   - Call `animationSequencer.playMoveResult(...)`.
   - **Catch animation errors** — force board sync anyway.
   - `boardLayer.syncToBoard(newBoard, newFunctions)` — visual sync invariant.
   - Cache `_currentBoard`.
   - Fire `ScoreUpdatedEvent`, `MovesUpdatedEvent`, `ChainCompletedEvent`.
   - If `matchCompleted || movesRemaining == 0`: fire `MatchEndedEvent`, stop music.
6. **On exception:** Rubber-band swap. Log error.
7. **Always:** `inputHandler.onAnimationComplete()`.

---

## 14. Frontend: Animation Sequencer — playCascadeSteps

**File:** `chromacrush_app/lib/game/animation_sequencer.dart`

**Rewritten (2026-02-15):** Flat 7-phase loop mirroring the backend pipeline 1:1. The old complex partitioning logic (specialPositions, protectedPositions, regularRemovals split) was removed entirely.

For each cascade step in order:

### JUICE (fire-and-forget):
- Step 0 + fusion (4+ steps): fusion sequence + fusionFanfare audio + haptics.
- Step 1+: screen shake (escalating displacement), cascade audio (pitch ladder), haptics (escalating intensity).

### DRAIN — sequential wave replay:

**Wave 0: Match removals** (`step.removals`):
- Audio: `matchChime` (step 0, non-fusion).
- Particles: `matchBurst` (step 0) or `cascadeBurst` (step 1+). `fusionStorm` if fusion step 0.
- Background ripple at centroid of removals.
- `animateRemoval(step.removals)` + settle pause.

**Waves 1..N: Special activations** (sequential, for each `activation` in `step.specialActivations`):
- Screen shake: mega intensity (8px/500ms) or regular (6px/400ms).
- Audio + haptics: `megaActivation` or `specialActivation`.
- Particles per type: `lineSweep(H/V)`, `radialWave`, `chromaticRain`, `megaActivationBurst`.
- Background ripple at activation position.
- Chromatic conversion flash for orb combos (H+O=14, V+O=24, B+O=34): `boardLayer.flashPositions` + hold.
- `SpecialGemActivatedEvent` pause + `animateRemoval(activation.affected)`.

### PLACE — special gem creation:
- If `specialGemCreated`: `boardLayer.placeSpecialGem(row, col, color, func)` + `animateAppear` (250ms).

### GRAVITY:
- `boardLayer.animateDrops(step.drops)` (120ms per row) + settle pause.

### ATTRACT — mega formation:
- For each attraction: audio `megaMerge`, particles `megaMergeSparks`, background ripple.
- `boardLayer.animateAttraction(...)` + settle pause.

### FILL:
- `boardLayer.animateFill(step.spawns)` (300ms) + settle pause.

### INJECT — card injection:
- If `injectedSpecial`: read existing gem color at position, `boardLayer.placeSpecialGem(row, col, color, func)` + `animateAppear` (250ms).

### SETTLE:
- Brief delay between cascade steps (200ms).

### After all steps:
**SYNC** — `boardLayer.syncToBoard(finalBoard, finalFunctions)` + 250ms settle. Safety net ensuring visual board matches server state.

---

## 15. Frontend: BoardLayer Animations

**File:** `chromacrush_app/lib/game/board_layer.dart`

| Method | What it does |
|--------|-------------|
| `animateSwap` | MoveEffect both gems to each other's positions (150ms). Updates grid refs. |
| `animateRemoval` | Scale-to-zero + fade on each gem (200ms default, 350ms in sequencer). Sets `gems[r][c] = null`. |
| `animateDrops` | Snapshot pattern: (1) resolve all gems, (2) clear sources, (3) animate to targets with elastic bounce. Duration = 80ms × row distance. |
| `animateFill` | Create gems at positions, scale-from-zero appear (150ms). |
| `animateAttraction` | Glow sources (300ms), strip special from sources, apply mega to center, flash center (250ms). |
| `placeSpecialGem` | Remove existing gem, create new one with color + function. |
| `syncToBoard` | Snaps all gems to server state. Updates types/functions, removes empties, creates missing, removes orphans. |

---

## 16. Frontend: Board Sync Invariant

After every valid move, `boardLayer.syncToBoard(newBoard, newFunctions)` is called. This is the safety net.

**syncToBoard logic:**
1. Track all currently-referenced gems.
2. For each cell: if server says empty → remove. If server has a gem but frontend doesn't → create. If both exist → update type/function if changed.
3. Snap position, reset scale.
4. Remove orphaned GemComponents still in Flame tree but not tracked in grid.

This runs **even if animations threw an error** (catch block in `_onSwapCommitted`).

---

## 17. Data Contract: CascadeStepResponse

**File:** `chromacrush_app/lib/models/backend_contract.dart`

```dart
class CascadeStepResponse {
  final int stepNumber;
  final List<({int row, int col})> removals;
  final List<DropResponse> drops;
  final List<SpawnResponse> spawns;
  final SpecialGemCreatedResponse? specialGemCreated;
  final List<SpecialActivationResponse> specialActivations;
  final List<SpecialAttractionResponse> specialAttractions;
  final ({int row, int col, int function})? injectedSpecial;  // added 2026-02-15
  final SpecialActivationResponse? injectedActivation;  // added 2026-02-17 (fire_immediately activation)
  final List<DropResponse> injectedDrops;    // added 2026-02-17 (fire_immediately aftermath)
  final List<SpawnResponse> injectedSpawns;  // added 2026-02-17 (fire_immediately aftermath)
}

class SpecialActivationResponse {
  final int gemType;       // negative GemType (e.g., -1 = LINE_BLAST_H)
  final int row, col;
  final List<({int row, int col})> affected;
  final bool isMega;
  final int? megaFunc;     // encoded mega value (11-44) or null
}

class SpecialAttractionResponse {
  final int posARow, posACol;
  final int posBRow, posBCol;
  final int centerRow, centerCol;
  final int? megaFunc;     // encoded mega value
}
```

**injectedSpecial** — Card injection position and function value (Hook 3). When a card (e.g. Heavenly Gift) injects a special gem after fill, this record tells the frontend to animate the appearance. `function` maps to `GemFunction.fromValue()` (1=H, 2=V, 3=Bomb, 4=Orb). Null when no injection occurred.

**injectedActivation** — The special activation from a `fire_immediately` injection (Hook 3). Separated from main `specialActivations` so the frontend plays it as a distinct INJECTED_ACTIVATION phase after INJECT, before INJECTED_GRAVITY. Null when no fire_immediately injection occurred.

**injectedDrops / injectedSpawns** — Gravity drops and fill spawns caused by `fire_immediately` injections (Hook 3). Separated from main `drops`/`spawns` so the frontend plays them as distinct INJECTED_GRAVITY + INJECTED_FILL phases after INJECTED_ACTIVATION. Empty lists when no fire_immediately injection occurred.

---

## 18. Known Workarounds

### Match-end workaround
Backend only sets `matchCompleted=true` when BOTH players have 0 moves remaining. In single-player bot matches, the bot plays through the real API but may not finish. Frontend fires `MatchEndedEvent` when `movesRemaining == 0` as a workaround.
**Location:** `chroma_crush_game.dart` line 335.

### Animation error recovery
If cascade animation throws, board sync is forced immediately. The visual board always converges to server state.
**Location:** `chroma_crush_game.dart` lines 301-306.

### special_effects list always empty in MoveProcessor
`move_processor.py` initializes `special_effects = []` and never populates it. The iteration over it (for bonus score) is a no-op. All special gem handling is done inside `board_service.process_move` — the match module doesn't independently track special effects.
**Location:** `move_processor.py` line 136.

### Flood-fill expansion
Match detection expands matches to all contiguous same-colored tiles via numpy boolean mask dilation. A 3-match next to a large blob of the same color will clear the entire blob. This is intentional ("sticky clear" mechanic) but can cause surprising large clears.
**Location:** `detection.py` `_expand_contiguous`.

### Chromatic Orb fallback color
If a Chromatic Orb has no trigger color (or trigger color <= 0), it falls back to the most common standard color on the board.
**Location:** `special_gems.py` lines 84-96, `mega_gems.py` `_resolve_orb_target`.

---

## Appendix A: Complete File Map

### Backend — Board Module
| File | Contents |
|------|----------|
| `src/core/types/game.py` | GemType, GemFunction, Position, Move, mega gem encode/decode |
| `src/core/types/board.py` | BoardState, MatchGroup, MatchResult |
| `src/modules/board/service.py` | BoardService: create_board, swap_gems, clear_matches, apply_gravity, apply_gravity_inplace, fill_empty, fill_empty_inplace, process_move, has_valid_moves, _place_special_gem_inplace |
| `src/modules/board/detection.py` | _DetectionMixin: detect_matches, _determine_special_gem, _expand_contiguous (numpy mask dilation) |
| `src/modules/board/special_gems.py` | _SpecialGemsMixin: _calculate_special_effect_positions, _clear_positions_inplace, _clear_matches_inplace |
| `src/modules/board/cascade.py` | _CascadeMixin: _drain_clear_queue, _run_cascade_step_inplace, _execute_swap_activation, _execute_fusion_activation, _create_activation, _try_attraction_only_step_inplace, _rebuild_inert_megas |
| `src/modules/board/mega_gems.py` | _MegaGemsMixin: _check_special_attractions, _process_attractions_inplace, _calculate_mega_gem_effect_positions |
| `src/modules/board/_constants.py` | MAX_CASCADE_STEPS=100, LCG constants |
| `src/modules/board/types.py` | GemDrop, GemSpawn, SpecialActivation, SpecialAttraction, CascadeStep (with injected_special), CascadeContext (with injected_special, inert_megas), MoveProcessingResult |
| `src/modules/board/schema_loader.py` | `load_board_rules()`, `validate_board_rules()` — JSON schema loading |
| `src/modules/board/effect_interpreter.py` | `EffectInterpreter` — schema-driven special creation, effect areas, mega combos |
| `config/board_rules.json` | Default board rules schema (special creation rules, effect definitions, mega combos, attraction config) |

### Backend — Shared Pipeline
| File | Contents |
|------|----------|
| `src/core/move_pipeline.py` | Shared processing: `process_move_pipeline`, `process_mega_pipeline`, `derive_move_seed`, `derive_reshuffle_seed`, `BoardProcessingResult`. Used by both PvP and campaign. |

### Backend — Match Module (PvP)
| File | Contents |
|------|----------|
| `src/modules/match/service.py` | MatchService: create_match, submit_move, forfeit_match |
| `src/modules/match/move_processor.py` | MoveProcessor: move validation, delegates to shared pipeline, match finalization (ELO/raids/rewards) |
| `src/modules/match/match_finalizer.py` | MatchFinalizer: ELO updates, result recording |
| `src/modules/api/routes/matches.py` | POST /move endpoint, cascade_steps serialization |

### Backend — Campaign Module
| File | Contents |
|------|----------|
| `src/modules/campaign/service.py` | CampaignService: start attempt, submit_move, activate_mega, abandon. Delegates to shared pipeline with `enable_instant_win=False`. |
| `src/modules/campaign/level_loader.py` | LevelLoader: reads `config/campaign_levels.json` |
| `src/modules/api/routes/campaign.py` | 8 endpoints under `/api/v1/campaign/` |

### Frontend — Game Layer
| File | Contents |
|------|----------|
| `lib/game/chroma_crush_game.dart` | PvP game: move submission orchestration, board loading, intensity |
| `lib/game/campaign_game.dart` | Campaign game: same structure as PvP, obstacle-clearing mode |
| `lib/game/game_loadout_mixin.dart` | Shared mixin: card/mega loadout setup, `handleSelectionChanged`, periodic shuffle timers. Used by both PvP and campaign games. |
| `lib/game/board_layer.dart` | 8x8 grid: gem CRUD, swap/removal/drop/fill/attraction animations, syncToBoard |
| `lib/game/animation_sequencer.dart` | Consumes cascade_steps, sequences all animations |
| `lib/game/cascade_animator.dart` | Screen shake, flash, zoom pulse, fusion sequence |
| `lib/config/visual_theme_service.dart` | `VisualThemeBase` abstract + `VisualThemeService` — loads visual_theme.json, provides all gem colors/shapes/shader params/particle colors/background tints |
| `assets/config/visual_theme.json` | All frontend visual values: gem colors, shapes, shader params, special symbols, particle colors, background tints |
| `lib/game/gem_component.dart` | Individual gem: shader/canvas rendering, animations (all visuals from VisualThemeBase) |
| `lib/game/input_handler.dart` | Tap-to-select, tap-adjacent-to-swap state machine |
| `lib/game/particle_layer.dart` | 10 particle effects, 500-particle budget |
| `lib/game/background_layer.dart` | Ripple shader background |
| `lib/models/backend_contract.dart` | All API DTOs |
| `lib/view_models/match_view_model.dart` | Match lifecycle (idle→matchmaking→loading→playing→ended) |

---

## Appendix B: Cascade Step Order of Operations (Backend)

**Refactored (2026-02-15).** This is the definitive sequence within `_run_cascade_step_inplace`. Replaced the 10-phase pipeline with a queue-based drain followed by simple sequential phases. All operations mutate the board in place:

```
_phase_record_special(ctx)           — Record special_gem_created from matches
                                       ↳ Hook 1: apply_special_override() — cards can override the special type
_drain_clear_queue(board, ...)       — FIFO queue: clear matched positions + chain-react specials/megas
                                       ↳ Hook 2: get_effect_param_overrides() — cards can boost radius/range per special
                                       Returns (all_cleared, activations)
_phase_place_new_special(ctx)        — Place newly-created special gem in cleared position
                                       ↳ Hook 1 (cont): uses ctx.special_override_func if set
apply_gravity_inplace(board)         — Gravity (both grids mutated in lock step)
_rebuild_inert_megas(board, inert)   — Re-scan func_grid for megas after gravity shifted positions
_check_special_attractions(board)    — Post-gravity attraction check
  → _process_attractions_inplace()     (newly formed megas added to inert_megas)
_phase_fill(ctx)                     — Fill empty cells in place (random standard gems)
                                       ↳ Hook 4: get_spawn_weights() — cards can bias gem color distribution
_phase_post_fill_injection(ctx)      — Card injection after fill
                                       ↳ Hook 3: get_cascade_injection() — cards can inject specials onto board
                                       Records ctx.injected_special for frontend animation
                                       fire_immediately: activation stored in ctx.injected_activation (not all_activations)
                                       extra gravity + fill stored in ctx.injected_drops / ctx.injected_spawns
                                       (all separate from main fields for distinct animation phases)
```

**Key change from old pipeline:** The old 10-phase model had separate pre-clear attractions, pre-fire specials, clear-and-restore, post-clear attractions, and chain reaction phases. The queue-based drain collapses all of these into a single FIFO loop: positions are dequeued, cleared, and any specials found are computed and enqueued — chain reactions resolve naturally as the queue grows. No separate "wave" tracking, no protected-position restoration, no pre/post clear attraction gymnastics.

`CascadeContext` (in `types.py`) is a mutable dataclass. Carries: `board`, `matches`, `chain`, `seed`, `all_activations`, `all_attractions`, `new_specials`, `all_cleared`, `gems_dropped`, `gems_spawned`, `next_seed`, `inert_megas`, `injected_special`, `injected_activation`, `injected_drops`, `injected_spawns`, `modifiers`, `applied_modifiers`, `special_override_func`. Has a `build_step()` method to produce the final `CascadeStep`.

Output: `CascadeStep` with `step_number`, `matches`, `gems_dropped`, `gems_spawned`, `board_after_fill`, `special_activations`, `special_attractions`, `injected_special`, `injected_activation`, `injected_drops`, `injected_spawns`.

---

## Appendix C: Animation Timing Summary (Frontend)

| Phase | Duration | Notes |
|-------|----------|-------|
| Optimistic swap | 150ms | Plays before API call returns |
| Regular removal | 350ms + 150ms settle | |
| Special gem appear | 250ms | After removal, before activations |
| Special activation pause | 200ms | |
| Special activation removal | 350ms + 150ms settle | Special gem + affected |
| Attraction glow | 300ms | Source gems pulse |
| Attraction flash | 250ms | Center gem flash |
| Gravity drops | 120ms per row × distance | Elastic bounce |
| Fill spawns | 300ms + 150ms settle | |
| Between-cascade settle | 200ms | |
| Final board sync settle | 250ms | |
| Rubber-band (invalid) | 250ms | Swap back |
| Fusion sequence | 600ms+ | Shake + flash + zoom |

---

## Appendix D: Performance Optimizations (2026-02-11)

Two-phase optimization pass on the cascade loop. All 1149 tests passing after each change.

### Phase 1

| # | Optimization | Files | Technique |
|---|-------------|-------|-----------|
| 1 | In-place board mutation in cascade loop | cascade.py, service.py, special_gems.py, mega_gems.py, types.py | Single `board.copy()` at cascade entry; all steps (`clear`, `gravity`, `fill`, `trigger`, `attract`) mutate directly. Eliminated ~6 BoardState allocations per cascade step. |
| 2 | Eliminate numpy scalar overhead | detection.py, mega_gems.py, special_gems.py | `.tolist()` converts numpy arrays to Python lists in one C call; all scanning loops use native Python `list[list[int]]` instead of `int(array[r, c])`. |
| 3 | (Merged with Opt 1) | — | Tuple internals combined with in-place refactor to avoid double-churn. |
| 4 | Fast-exit attraction checks | mega_gems.py | `np.count_nonzero(fg) < 2` early return — skips full scan when fewer than 2 specials exist (common case). |
| 5 | Vectorize `fill_empty` | service.py | `np.where` + `np.lexsort` (column-major order) + batch `rng.integers(size=N)`. One vectorized assignment instead of per-cell loop. |
| 6 | Pattern-based `has_valid_moves` | service.py | 8 local pattern checks per swap position instead of brute-force swap + `detect_matches`. Checks left-2, vertical up-2, down-2, sandwich for each swapped position. |

### Phase 2

| # | Optimization | Files | Technique |
|---|-------------|-------|-----------|
| 7 | Vectorize `_clear_positions_inplace` | special_gems.py | numpy fancy indexing: build row/col arrays, single `grid[rows, cols] = 0` assignment. Also vectorized `_clear_matches_inplace`. |
| 8 | Drop intermediate CascadeStep board fields | types.py, test_scoring_service.py | Removed `board_after_clear` and `board_after_gravity` fields. Only `board_after_fill` retained (feeds next cascade step). API serialization and scoring never consumed these. |
| 9 | Vectorize `_expand_contiguous` | detection.py | Replaced Python BFS with numpy boolean mask dilation: color mask, seed from matched positions, iterative shift-and-OR in 4 directions until stable. |
| 10 | Remove dead copying wrappers | special_gems.py | Deleted `_clear_positions` (copying variant) and `_trigger_adjacent_specials` (wrapper that called `.copy()` then delegated to inplace). All callers already use inplace variants. |

---

## Appendix E: Schema-Driven Architecture (2026-02-13)

All hardcoded game rules and visual values replaced with JSON schemas.

### Backend: `config/board_rules.json`

Defines: board dimensions, `special_creation_rules` (priority-ordered pattern matching), `special_gems.functions` (effect definitions with `select` type), `mega_gems.combos` (10 combo effects), `mega_gems.attractions` (distance, scan directions), `chain_reaction` config.

`EffectInterpreter` (`src/modules/board/effect_interpreter.py`) loads the schema once at `BoardService.__init__` and replaces all hardcoded if/elif dispatch trees:
- `determine_special_gem()` replaces `detection.py` priority chain
- `calculate_effect_positions()` replaces `special_gems.py` switch
- `calculate_mega_effect_positions()` replaces `mega_gems.py` 10-case switch
- `get_attraction_config()` / `get_chain_config()` provide rule parameters

### Frontend: `assets/config/visual_theme.json`

Defines: `gem_colors` (6 hex values), `gem_shapes` (type→shape index), `gem_shader_params` (pulse, glow, brightness), `special_symbols` (4 Unicode chars), `particle_colors` (14 named effects), `chromatic_rain_colors`, `victory_confetti_colors`, `background` (base, calm, storm tints, ripple RGB).

`VisualThemeBase` abstract class (`lib/config/visual_theme_service.dart`) injected through constructor into all Flame components and via Provider into widgets. All components read visuals from theme — no hardcoded colors, shapes, or shader params remain in component code.

### Test suite timing (board module, 32 tests)

| Checkpoint | Time |
|-----------|------|
| Before any optimization | 0.48s |
| After Opts 4 + 2 | 0.35s |
| After Opts 5 + 6 | 0.23s |
| After Opt 1 (Phase 1 complete) | 0.42s |
| After Phase 2 complete | 0.32s |

---

## 19. Backend: Card Effect Hooks (Phase 4C)

**Date:** 2026-02-14
**Status:** Implemented (53 of 55 cards active; 2 deferred to Phase 4.6 raid system)

### Architecture

Players equip 0-3 cards from their collection. Each card has `trigger`, `effect`, and `effect_params` fields in `config/card_definitions.json`. At move submission time, a `CardModifierEngine` is built from the player's equipped loadout and threaded as an optional `modifiers` parameter through the entire cascade pipeline. When `None` (no cards or card service unavailable), all behavior is unchanged — fully backward compatible.

```
composition_root (card_service)
  → MatchService(card_service=card_service)
    → MoveProcessor(card_service=card_service)
      → submit_move(): builds CardModifierEngine from equipped cards
        → process_move_pipeline(modifiers=engine)    [src/core/move_pipeline.py]
          → BoardService.process_move(modifiers=engine)
            → _run_cascade_step_inplace(modifiers=engine)
              → CascadeContext(modifiers=engine)
  → CampaignService(card_service=card_service)
    → submit_move(): builds CardModifierEngine from equipped cards
      → process_move_pipeline(modifiers=engine, enable_instant_win=False)
        → BoardService.process_move(modifiers=engine)    [same path]
```

**Key design:** The engine is pure and stateless — no DB calls, no I/O. Built async once (to fetch loadout), used synchronously everywhere. All random effects use the cascade seed (deterministic LCG) for replay integrity.

### Files

| File | Purpose |
|------|---------|
| `src/modules/cards/modifier_types.py` | `CardModifierDef`, `AppliedModifier`, `InjectionAction`, `ScoreModifiers` (frozen dataclasses) |
| `src/modules/cards/modifier_engine.py` | `CardModifierEngine` — 8 hook methods, indexes cards by `effect` string |
| `config/card_definitions.json` | 55 card definitions with trigger/effect/effect_params (v2.0) |

### Hook Points

The engine indexes cards by their `effect` string at construction time (`self._by_effect`). Each hook method looks up the relevant effect type and processes matching cards. Any card with a matching `effect` value in the JSON automatically fires through the correct hook.

#### Hook 1 — Special Override (`apply_special_override`)
**Where:** `_phase_record_special` + `_phase_place_new_special` in `cascade.py`
**Cards:** Short Fuse (`override_special → target_function: 3`), Chroma Storm (`override_special → target_function: 4`), The Path (`override_special_mega → mega_func: 11`), The North Star (`override_special_mega → mega_func: 22`)
**Behavior:** When a special gem is about to be created from a match, the hook can change which special type is placed. Mega overrides write mega values (11, 22) to `func_grid` instead of regular functions.

#### Hook 2 — Effect Parameter Override (`get_effect_param_overrides`)
**Where:** `_fire_matched_specials` in `cascade.py` → `_create_activation` → `_calculate_special_effect_positions` → `EffectInterpreter.calculate_effect_positions`
**Cards:** Detonation (`effect_param_override → function: 3, radius_bonus: 2`)
**Behavior:** Before a special gem's effect executes, the hook injects parameter overrides (e.g. `radius_bonus`) into the effect dict. For Detonation, radial bombs get +2 radius. Filters by `function` or `target_function` param; applies to all functions if neither present.

#### Hook 3 — Cascade Injection (`get_cascade_injection`)
**Where:** `_phase_post_fill_injection` in `cascade.py` (Phase 11, after fill)
**Cards:** Heavenly Gift (`inject_special → function: "random"`), Heavy Gravity (`inject_and_fire → mega_func: 11`), Acid Rain (`inject_and_fire → function: 2`)
**Behavior:** After each cascade step's fill phase, the hook can inject a special gem onto a random neutral-gem position. Supports `function: "random"` (picks 1-4 via deterministic LCG), `mega_func` (places a mega gem), and `fire_immediately` (fires the injected special — activation stored in `ctx.injected_activation`, gravity in `ctx.injected_drops`, fill in `ctx.injected_spawns`; all separate from main fields so the frontend plays them as distinct INJECT → INJECTED_ACTIVATION → INJECTED_GRAVITY → INJECTED_FILL phases in lockstep with backend execution order). Interval controlled by `trigger_condition.every_n` or `effect_params.every_n`.

#### Hook 4 — Spawn Bias (`get_spawn_weights`)
**Where:** `_phase_fill` in `cascade.py` → `fill_empty_inplace` in `service.py`
**Cards:** 18 spawn_bias cards (Mysterious Inclination I-VI, Resonance I-VI, Affinity I-VI) with `gem_color: 1-6`, `weight_bonus: 0.1-0.3`
**Behavior:** Returns a weighted probability array for gem color selection during fill. Starts with uniform `[1.0, 1.0, 1.0, 1.0, 1.0, 1.0]`, adds each card's `weight_bonus` to its `gem_color` index, normalizes to sum 1.0. Multiple cards for different colors stack independently. Uses `rng.choice` with probability array instead of `rng.integers`.

#### Hook 5a — Special Type Bias (`get_special_type_bias`)
**Where:** `detect_matches` in `detection.py` → `_determine_special_gem`
**Cards:** 12 special_type_bias cards (Arcane Inclination I-IV, Resonance I-IV, Affinity I-IV) with `function: 1-4`, `bias_bonus: 0.1-0.3`
**Behavior:** Accumulates bias weights per function ID. Applied during special gem type selection to shift probabilities toward specific special types.

#### Hook 5b — Fortune's Favor (`get_three_match_special_chance`)
**Where:** `detect_matches` in `detection.py` (after `_determine_special_gem` returns None for 3-matches)
**Cards:** Fortune's Favor (`special_creation_chance → three_match_special_chance: 0.15`)
**Behavior:** When a 3-gem match produces no special (normal behavior), this hook grants a chance for it to create one anyway. Uses deterministic LCG roll: `(seed * 1103515245 + 12345) & 0x7FFFFFFF`. If roll succeeds, picks the middle position of the first 3-match group and creates a LINE_BLAST_H (func 1).

#### Hook 6 — Score Modifiers (`get_score_modifiers`)
**Where:** `process_move_pipeline` / `process_mega_pipeline` in `core/move_pipeline.py` → `calculate_move_score` in `scoring/service.py`
**Cards:** 10 score_multiplier cards + Thick Skin (opponent_score_reduction) + Lucky Rabbit (all_multiplier: 0.0)
**Behavior:** Aggregates all scoring params into a `ScoreModifiers` frozen dataclass via `dataclasses.replace()`. Applied in scoring service in this order:
1. `first_step_multiplier` — bonus on cascade step 0 match points (Opening Gambit +25%, Quick Draw +50%)
2. `cascade_multiplier` — scales total points (Cascade Proficiency, Double Edge, Special Affection)
3. `chain_reaction_multiplier` — bonus when 2+ cascade steps (Chain Lightning +25%)
4. `special_multiplier` — adjusts special activation points (Detonation Proficiency, Double Edge zeroes specials)
5. `cascade_depth_bonus` — flat bonus per cascade step beyond 1 (Cascade Momentum)
6. `all_multiplier` — global multiplier on final total (Lucky Rabbit zeroes all scoring)
7. `opponent_score_reduction` — fraction applied at match finalization (Thick Skin -5%)

#### Hook 7 — Win Condition (`check_win_condition`)
**Where:** `process_move_pipeline` / `process_mega_pipeline` in `core/move_pipeline.py` (post-scoring). **Disabled in campaign** via `enable_instant_win=False` — prevents cheesing levels with Lucky Rabbit.
**Cards:** Lucky Rabbit (`lucky_rabbit → win_on_mega: 44, all_multiplier: 0.0`)
**Behavior:** Scans cascade steps for special activations with `mega_func_value` matching the card's `win_on_mega` param. If Lucky Rabbit is equipped and an O+O combo (mega value 44) fires, flags instant win. Combined with the scoring penalty (all_multiplier: 0.0), the card is high-risk/high-reward: zero points from normal play, only wins via the rarest combo.

#### Hook 8 — Energy Grant (`check_energy_grant`)
**Where:** `process_move_pipeline` / `process_mega_pipeline` in `core/move_pipeline.py` (post-scoring)
**Cards:** Heart of Fire (`grant_energy → hearts: 1`, `trigger_condition: {min_chain: 3}`)
**Behavior:** If cascade chain count meets the threshold (`min_chain` from `trigger_condition` or `effect_params`), awards bonus hearts. Currently a TODO for actual energy service integration.

#### Hook 9 — Board Shuffle (`shuffle_board`)
**Where:** `BoardService.shuffle_board` in `service.py`
**Cards:** Void Instability (`board_shuffle`, `trigger_condition: {interval_seconds: 10}`)
**Behavior:** Fisher-Yates shuffle of both `grid` and `func_grid` using seeded RNG. Generates same permutation for both arrays to keep color/function pairs together. Validates no pre-existing matches after shuffle (up to 10 attempts). Frontend triggers shuffle requests on timer for Void Instability card.

#### Hook 10 — Raid Protection (Deferred)
**Cards:** Eternal Guardian (`raid_protection`), Resilient Shield (`raid_block`)
**Status:** Deferred to Phase 4.6 when the raid system is built. TODO comments in `modifier_engine.py`.

### Card Effect Types Summary

| Effect | Cards | Hook | Stacking |
|--------|-------|------|----------|
| `spawn_bias` | 18 | Hook 4 | Additive per color, then normalized |
| `special_type_bias` | 12 | Hook 5a | Additive per function ID |
| `score_multiplier` | 10 | Hook 6 | Multiplicative per field |
| `inject_and_fire` | 2 | Hook 3 | First matching card fires |
| `override_special` | 2 | Hook 5 | Last card wins |
| `override_special_mega` | 2 | Hook 1 | Last card wins |
| `inject_special` | 1 | Hook 3 | First matching card fires |
| `special_creation_chance` | 1 | Hook 5b | First card with passing roll |
| `effect_param_override` | 1 | Hook 2 | Additive (radius_bonus) |
| `opponent_score_reduction` | 1 | Hook 6 | Additive |
| `lucky_rabbit` | 1 | Hooks 6+7 | Unique (scoring penalty + win check) |
| `grant_energy` | 1 | Hook 8 | Additive hearts |
| `board_shuffle` | 1 | Hook 9 | Frontend-triggered |
| `raid_protection` | 1 | Hook 10 | Deferred |
| `raid_block` | 1 | Hook 10 | Deferred |

### API Response

Move responses now include `applied_modifiers` — a list of card effects that fired during the move:

```json
{
  "applied_modifiers": [
    {
      "card_id": 1,
      "card_name": "Mysterious Inclination I",
      "hook": "spawn_bias",
      "description": "Mysterious Inclination I: color 1 +0.1"
    }
  ]
}
```

**Serialized in:** `src/modules/api/routes/matches.py` submit_move endpoint.
**DTO field:** `MoveProcessingResult.applied_modifiers` (list, propagated from `CascadeContext.applied_modifiers`).
