# ChromaCrush Render Flow Survey

**Date:** 2026-02-14 (updated 2026-02-22 — added CampaignGame + GameLoadoutMixin references)
**Purpose:** Ground-truth technical survey of the frontend rendering pipeline — from API response receipt through Flame component lifecycle to pixels on screen. Documents what the code actually does, not what it should do.

---

## Bugs Under Investigation

### BUG R1 — FIXED: Fill gems invisible during cascades
**Status:** Resolved (2026-02-14)
**Symptom:** During long cascade chains, `animateFill` creates gems in the `gems[][]` array and adds them to the Flame tree, but they do not render visually. The cells they occupy are "reserved" (nothing else fills them), and specials can fire from those positions in subsequent cascade steps, confirming the data layer is correct. Gems only become visible when `syncToBoard` runs after all cascade steps complete.
**Root cause:** `animateFill` called `_createGem` (which queues the component via `add()`) and then immediately called `gem.animateAppear()`, which sets `scale = Vector2.zero()` and adds a `ScaleEffect` child to animate back to 1.0. But the gem hadn't mounted yet — both the gem and its ScaleEffect were sitting in Flame's `_addLater` queue. The ScaleEffect could not advance via `update(dt)` until the component lifecycle caught up, leaving gems stuck at scale 0 for the duration of the cascade. `syncToBoard` masked the issue by forcing `scale = Vector2.all(1.0)` after all steps.
**Fix:** Split `animateFill` into two phases: (1) create all gems and `await Future.wait([for (g in gems) g.loaded])` to ensure they complete `onLoad` and mount in the Flame tree, (2) only then call `animateAppear` on each gem so the ScaleEffect is added to a mounted component that can immediately process it.
**Location:** `board_layer.dart` `animateFill`

---

### BUG R2 — FIXED: Special gems created during cascades invisible / show wrong type
**Status:** Resolved (2026-02-14)
**Symptom:** Chromatic Storm card overrides all specials to chromatic orbs on the backend. The `special_gem_created` data in cascade steps carries the correct overridden type. `placeSpecialGem` is called with the correct function. But the gem visually displays as the original special type (e.g., LINE_BLAST_H) until `syncToBoard` runs after all cascade steps. The gem *acts* as a chromatic orb (correct blast pattern), meaning the `gems[][]` array has the right data but the visual component doesn't reflect it.
**Root cause:** Same as R1. The sequencer's Phase 4 calls `boardLayer.placeSpecialGem()` (which calls `_createGem` → `add(gem)` queued) then immediately calls `gem.animateAppear()` (sets `scale = Vector2.zero()`, adds ScaleEffect to unmounted gem). The newly created special gem sat at scale 0 while the old dying gem (still in Flame tree, animating removal) remained visible at the same position, showing the original type.
**Fix:** Added `await gem.loaded` before `gem.animateAppear()` in `animation_sequencer.dart` Phase 4. The gem mounts and renders at correct scale before the ScaleEffect is applied.
**Location:** `animation_sequencer.dart` line ~201

### Lesson Learned
**Flame lifecycle rule:** Never add Effects (ScaleEffect, MoveEffect, etc.) to a component that hasn't finished mounting. Always `await component.loaded` before adding child effects, or the effects will sit in the add queue unable to advance via `update(dt)`. This applies to any newly-created component — effects on already-mounted components (e.g., removal animations on existing gems) work fine because the parent is already in the render cycle.

---

## Table of Contents

1. [Component Tree & Ownership](#1-component-tree--ownership)
2. [Flame Component Lifecycle](#2-flame-component-lifecycle)
3. [GemComponent Creation & Rendering](#3-gemcomponent-creation--rendering)
4. [Board Population: loadBoard](#4-board-population-loadboard)
5. [Move Submission Orchestration](#5-move-submission-orchestration)
6. [AnimationSequencer: playCascadeSteps](#6-animationsequencer-playcascadesteps)
7. [BoardLayer Animation Methods](#7-boardlayer-animation-methods)
8. [syncToBoard: The Safety Net](#8-synctoboard-the-safety-net)
9. [Timing Constants Summary](#9-timing-constants-summary)
10. [Data Flow: Backend Response → Visual State](#10-data-flow-backend-response--visual-state)
11. [Identified Issues & Anomalies](#11-identified-issues--anomalies)

---

## 1. Component Tree & Ownership

```
ChromaCrushGame (FlameGame) — PvP
├── BackgroundLayer (priority -10, ripple shader)
├── BoardLayer (PositionComponent, centered at ~40% from top)
│   └── GemComponent × 64 (8×8 grid, PositionComponent with TapCallbacks)
│       └── TextComponent (_debugLabel, child of GemComponent)
├── PlayerStatusBar (hearts, mega inventory, card runes)
├── ParticleLayer (positioned at board offset, renders on top)
└── [FlashOverlay] (temporary, priority 50, added/removed by CascadeAnimator)

CampaignGame (FlameGame) — Campaign (same tree structure)
├── BackgroundLayer, BoardLayer, PlayerStatusBar, ParticleLayer, [FlashOverlay]
└── (no bot opponent, obstacle-clearing mode, shared rendering pipeline)
```

Both games use `GameLoadoutMixin` for shared behavior: card/mega loadout setup, `handleSelectionChanged` (gem selection clearing + highlighting), and periodic shuffle timers.

**Non-component collaborators** (plain Dart objects, not in Flame tree):
- `InputHandler` — gesture state machine
- `AnimationSequencer` — consumes cascade steps, orchestrates BoardLayer calls
- `CascadeAnimator` — screen shake, flash, zoom (adds effects to BoardLayer/Game)

**Ownership invariant:** `BoardLayer.gems[r][c]` is the single source of truth for which GemComponent occupies each cell. Every animation method that creates, moves, or removes gems must update this array in lockstep with the Flame tree operations.

---

## 2. Flame Component Lifecycle

**Critical for understanding the bugs.** When a component is added to the Flame tree:

```
add(component)
  → component queued in _addLater list
  → next game loop tick: processLifecycleEvents()
    → component.onLoad() called (async — may take >0 frames)
    → after onLoad completes: component.onMount() called
    → component now participates in update() and render() cycles
```

**Key implication:** A newly `add()`ed component does NOT render on the same frame it is added. It must survive at least one game loop tick for `onLoad` to run, and potentially more if `onLoad` is async.

### GemComponent.onLoad()
```dart
@override
Future<void> onLoad() async {
  await super.onLoad();
  _shader = GemShaderLibrary.instance.createGemShader();  // synchronous lookup
  _updatePaints();                                          // synchronous
  _debugLabel = TextComponent(...);                         // creates child
  add(_debugLabel!);                                        // queues child
}
```

`onLoad` is technically async but does no actual async work — `GemShaderLibrary.instance.createGemShader()` is a synchronous factory call. The `add(_debugLabel!)` queues the text child, which will itself need a lifecycle tick. The gem should be renderable after one tick, but the debug label after two.

---

## 3. GemComponent Creation & Rendering

### _createGem (BoardLayer)
```dart
GemComponent _createGem(int row, int col, GemType type,
    [GemFunction func = GemFunction.neutral, int? rawFunc]) {
  final gem = GemComponent(
    gemType: type,
    gridRow: row,
    gridCol: col,
    theme: theme,
    gemFunction: func,
    rawFunc: rawFunc ?? func.value,
    onTap: (r, c) => onGemTapped?.call(r, c),
  );
  gems[row][col] = gem;   // ← data layer updated immediately
  add(gem);                // ← queued for Flame tree (NOT immediate)
  return gem;
}
```

**The gem is in `gems[][]` immediately, but NOT in the render tree until the next game loop tick processes the add queue.**

### Constructor
```dart
GemComponent({...})
    : rawFunction = rawFunc ?? 0,
      super(
        size: Vector2.all(kCellSize),        // 44×44
        position: gridToPosition(gridRow, gridCol),  // correct position from creation
        anchor: Anchor.topLeft,
      );
```

Position is set correctly at construction time. Scale defaults to `Vector2.all(1.0)` (Flame default).

### Rendering
```dart
@override
void render(Canvas canvas) {
  if (paintAlpha < 1.0) { canvas.saveLayer(...); }
  if (_shader != null) {
    _renderShader(canvas);    // GPU path: sets 14 uniforms, draws rect
  } else {
    _renderFallback(canvas);  // Canvas path: SDF polygons
  }
  if (paintAlpha < 1.0) { canvas.restore(); }
}
```

Both paths read `gemType` and `rawFunction` at render time (not cached). So if these fields are updated, the next render frame will reflect the change — **provided the component is mounted and participating in render cycles.**

### animateAppear
```dart
Future<void> animateAppear({Duration duration = kGemAppearDuration}) {
  final completer = Completer<void>();
  final seconds = duration.inMilliseconds / 1000.0;
  scale = Vector2.zero();          // ← SET SCALE TO ZERO IMMEDIATELY
  add(
    ScaleEffect.to(
      Vector2.all(1.0),
      EffectController(duration: seconds),
      onComplete: completer.complete,
    ),
  );
  return completer.future;
}
```

**CRITICAL OBSERVATION:** `scale = Vector2.zero()` is set immediately on the GemComponent. Then a `ScaleEffect` is added (queued) to animate scale from 0→1. But the ScaleEffect is a child component — it goes through the same lifecycle queue as any other component.

**Potential issue chain:**
1. `_createGem()` creates gem, `add(gem)` — gem queued
2. Caller immediately calls `gem.animateAppear()` — sets `scale = Vector2.zero()`, then `gem.add(ScaleEffect)` — effect queued on gem
3. Gem hasn't been mounted yet (still in parent's add queue)
4. Can a queued-but-not-mounted component accept child adds? In Flame, yes — children are queued and processed when the parent mounts. So the ScaleEffect should work.
5. But: the `await completer.future` waits for the ScaleEffect's `onComplete` callback. The ScaleEffect won't start advancing until both the gem AND the effect are mounted and participating in `update()` cycles.

**If the gem takes 1+ frames to mount, but the animation sequencer awaits the completer and then immediately proceeds to the next cascade step, the timing could be off.** However, the animation duration is 150-300ms (many frames), so a 1-frame delay shouldn't make gems invisible. The real question is whether the ScaleEffect completes correctly.

### animateRemoval
```dart
Future<void> animateRemoval({Duration duration = kGemRemovalDuration}) {
  final completer = Completer<void>();
  final seconds = duration.inMilliseconds / 1000.0;
  add(
    ScaleEffect.to(
      Vector2.zero(),
      EffectController(duration: seconds),
      onComplete: () {
        removeFromParent();
        completer.complete();
      },
    ),
  );
  return completer.future;
}
```

Scales to zero, then removes from parent. The `gems[r][c] = null` is done by the CALLER (BoardLayer.animateRemoval), not here. So the data layer and Flame tree are updated at different times:
- `gems[r][c] = null` — immediate (in BoardLayer.animateRemoval)
- `removeFromParent()` — after animation completes

---

## 4. Board Population: loadBoard

Called once when a match starts.

```dart
void loadBoard(BoardStateResponse board) {
  // Remove all existing gems.
  for (var r = 0; r < kBoardSize; r++) {
    for (var c = 0; c < kBoardSize; c++) {
      gems[r][c]?.removeFromParent();
      gems[r][c] = null;
    }
  }
  // Create new gems with color and function.
  for (var r = 0; r < kBoardSize; r++) {
    for (var c = 0; c < kBoardSize; c++) {
      final gemType = GemType.fromValue(board.cells[r][c]);
      if (!gemType.isEmpty) {
        final rawFunc = board.functions[r][c];
        final func = GemFunction.fromValue(rawFunc);
        _createGem(r, c, gemType, func, rawFunc);
      }
    }
  }
}
```

Creates up to 64 gems. All are queued via `add()`. All will mount on the next game loop tick. No animations — gems appear at scale 1.0 immediately after mount. This works fine because there's no time pressure (no cascade is running).

---

## 5. Move Submission Orchestration

**File:** `chroma_crush_game.dart` — `_onSwapCommitted`

```
1. inputHandler.state = InputState.animating     (blocks further input)
2. boardLayer.animateSwap(from, to)              (150ms optimistic swap)
3. apiClient.submitMove(matchId, request)         (network call)
4. IF invalid → rubber-band swap back, return
5. IF valid:
   a. await animationSequencer.playMoveResult(...)   ← ALL CASCADE ANIMATIONS
   b. CATCH: log error (animation can fail)
   c. boardLayer.syncToBoard(newBoard, newFunctions) ← SAFETY NET (always runs)
   d. _currentBoard = newBoard
   e. fire ScoreUpdatedEvent, MovesUpdatedEvent, ChainCompletedEvent
   f. if matchCompleted → fire MatchEndedEvent
6. CATCH: rubber-band swap
7. FINALLY: inputHandler.onAnimationComplete()     (unblocks input)
```

**Key observation:** `syncToBoard` at step 5c runs AFTER `playMoveResult` completes (or throws). This is the safety net that fixes all visual state. The fact that bugs R1 and R2 are resolved by syncToBoard confirms the issue is in the animation pipeline (step 5a), not in the final state application.

---

## 6. AnimationSequencer: playCascadeSteps

**File:** `animation_sequencer.dart`

**Refactored (2026-02-15):** Rewrote from scratch to mirror the backend's queue-based drain pipeline 1:1. Old orchestrator had complex partitioning (specialPositions, protectedPositions, regularRemovals split) that caused visual board state drift — gravity not animating, blank spaces appearing. New orchestrator is a flat 7-phase loop per step with no partitioning logic.

### Design Principle
Backend pipeline per step: `DRAIN → PLACE → GRAVITY → ATTRACT → FILL → INJECT → INJECTED_ACTIVATION → INJECTED_GRAVITY → INJECTED_FILL`
Frontend mirrors it: `DRAIN REPLAY → PLACE → GRAVITY → ATTRACT → FILL → INJECT → INJECTED_ACTIVATION → INJECTED_GRAVITY → INJECTED_FILL`

### Pre-step: Juice (fire-and-forget)
- Step 0 + fusion (≥4 steps): `cascadeAnimator.playFusionSequence()` + fusionFanfare audio + haptics
- Step 1+: `cascadeAnimator.screenShake()` (escalating), cascade audio (pitch ladder), haptics (escalating)

### Per-step sequence:

```
DRAIN wave 0: Match removals
  - IF step.removals non-empty:
    - Audio: matchChime (step 0, non-fusion)
    - Particles: matchBurst (step 0) or cascadeBurst (step 1+)
    - fusionStorm if fusion + step 0
    - Background ripple at centroid
    - await _playEvent(MatchRemovalEvent(step.removals))
      → boardLayer.animateRemoval(positions, 350ms) + 150ms settle

DRAIN waves 1..N: Special activations (sequential)
  - FOR EACH activation (in backend drain order):
    - Screen shake (mega vs regular intensity)
    - Audio + haptics (megaActivation or specialActivation)
    - Type-specific particles: lineSweep(H/V), radialWave, chromaticRain, megaActivationBurst
    - Background ripple at activation position
    - Chromatic conversion flash (if O combo: H+O, V+O, B+O): flash + await delay
    - await _playEvent(SpecialGemActivatedEvent) → 200ms pause
    - await _playEvent(MatchRemovalEvent(activation.affected))
      → boardLayer.animateRemoval(affected, 350ms) + 150ms settle

PLACE: Special gem from match
  - IF step.specialGemCreated != null:
    - func = GemFunction.fromValue(sp.gemType.abs())
    - color = sp.color → colorType = GemType.fromValue(color)
    - gem = boardLayer.placeSpecialGem(row, col, colorType, func)
    - await gem.loaded (wait for mount)
    - await gem.animateAppear(250ms)

GRAVITY: Drops
  - IF step.drops non-empty:
    - await _playEvent(GravityEvent(drops))
      → boardLayer.animateDrops(drops, 120ms per row) + 100ms settle

ATTRACT: Post-gravity mega formation
  - FOR EACH attraction:
    - Audio: megaMerge. Haptics.
    - Particles: megaMergeSparks
    - Background ripple at center
    - await _playEvent(SpecialAttractionEvent)
      → boardLayer.animateAttraction(...) + 200ms settle

FILL: Spawns
  - IF step.spawns non-empty:
    - await _playEvent(FillEvent(spawns))
      → boardLayer.animateFill(spawns, 300ms):
        1. Create all gems via _createGem
        2. await Future.wait(loaded)
        3. await Future.wait(animateAppear)
      → 150ms settle

INJECT: Card injection (e.g. Heavenly Gift)
  - IF step.injectedSpecial != null:
    - Read existing gem's color at (row, col)
    - boardLayer.placeSpecialGem(row, col, colorType, func)
    - await gem.loaded + await gem.animateAppear(250ms)

INJECTED_ACTIVATION: fire_immediately — bomb goes off
  - IF step.injectedActivation != null:
    - Screen shake (mega vs regular intensity)
    - Audio + haptics (megaActivation or specialActivation)
    - Type-specific particles (same as DRAIN waves)
    - Background ripple at activation position
    - await _playEvent(SpecialGemActivatedEvent) → 200ms pause
    - await _playEvent(MatchRemovalEvent(activation.affected))
      → boardLayer.animateRemoval(affected, 350ms) + 150ms settle

INJECTED_GRAVITY: fire_immediately aftermath drops
  - IF step.injectedDrops non-empty:
    - await _playEvent(GravityEvent(injectedDrops))
      → boardLayer.animateDrops(drops, 120ms per row) + 100ms settle

INJECTED_FILL: fire_immediately aftermath spawns
  - IF step.injectedSpawns non-empty:
    - await _playEvent(FillEvent(injectedSpawns))
      → boardLayer.animateFill(spawns, 300ms) + 150ms settle

SETTLE: Between-step pause
  - await Future.delayed(200ms)
```

### After ALL steps:
```
SYNC: Final board sync (safety net)
  - await _playEvent(BoardSyncEvent(finalBoard, finalFunctions))
    → boardLayer.syncToBoard(finalBoard, finalFunctions) + 250ms settle
```

---

## 7. BoardLayer Animation Methods

### animateRemoval
```dart
Future<void> animateRemoval(positions, {duration = 200ms}) async {
  final futures = <Future<void>>[];
  for (final pos in positions) {
    final gem = gems[pos.row][pos.col];
    if (gem != null) {
      futures.add(gem.animateRemoval(duration: duration));  // ScaleEffect 1→0, then removeFromParent
      gems[pos.row][pos.col] = null;                        // data layer nulled IMMEDIATELY
    }
  }
  await Future.wait(futures);  // wait for all removal animations
}
```

**Data-visual timing gap:** `gems[r][c]` is set to null before the animation completes. The GemComponent is still in the Flame tree (scaling to zero) but not tracked in the grid. Any subsequent code checking `gems[r][c]` will see null even though the component is still rendering its death animation.

### animateDrops
```dart
Future<void> animateDrops(drops, {durationPerRow = 80ms}) async {
  // Phase 1: Snapshot — resolve every gem reference BEFORE mutating
  final resolved = <int, GemComponent>{};
  for (var i = 0; i < drops.length; i++) {
    final gem = gems[drops[i].fromRow][drops[i].fromCol];
    if (gem != null) resolved[i] = gem;
  }

  // Phase 2: Clear all source slots
  for (final drop in drops) {
    gems[drop.fromRow][drop.fromCol] = null;
  }

  // Phase 3: Place at destinations + animate
  final futures = <Future<void>>[];
  for (var i = 0; i < drops.length; i++) {
    final gem = resolved[i];
    if (gem == null) continue;
    gem.position = gridToPosition(drop.fromRow, drop.fromCol);  // snap to pre-drop position
    final target = gridToPosition(drop.toRow, drop.toCol);
    futures.add(gem.animateMoveToElastic(target, duration: dur));
    gems[drop.toRow][drop.toCol] = gem;                          // data layer updated
    gem.updateGridPosition(drop.toRow, drop.toCol);              // tracking updated
  }
  await Future.wait(futures);
}
```

**Snapshot pattern prevents cross-contamination.** Resolves all gem references first, then clears sources, then animates. This is correct.

**POTENTIAL ISSUE:** If a gem at `fromRow, fromCol` was already set to null by a prior animation (e.g., removal in Phase 3 of the cascade step), then `resolved[i]` will be null and that drop is silently skipped. The backend computed drops based on the board state AFTER clearing — if the frontend's removal already nulled those positions... wait, drops reference gems that SURVIVED clearing, not cleared gems. So drops should reference positions that still have gems after removal. This should be fine.

### animateFill (after R1 fix)
```dart
Future<void> animateFill(spawns, {duration = 150ms}) async {
  // Phase 1: Create all gems (queued in Flame tree at default scale 1.0)
  final newGems = <GemComponent>[];
  for (final spawn in spawns) {
    final type = GemType.fromValue(spawn.gemType);
    newGems.add(_createGem(spawn.row, spawn.col, type));
  }
  if (newGems.isEmpty) return;
  // Phase 2: Wait for all gems to complete onLoad and mount
  await Future.wait([for (final g in newGems) g.loaded]);
  // Phase 3: Now animate — ScaleEffect added to mounted components
  await Future.wait([for (final g in newGems) g.animateAppear(duration: duration)]);
}
```

**Note:** `_createGem` is called with only `type` — no `func` parameter. The default is `GemFunction.neutral`. For normal fills (new random gems) this is correct. If card injection (Hook 3) produces specials in the spawn list, the function would only be corrected at `syncToBoard`.

**BUG R1 was here.** The original code called `_createGem` then immediately `gem.animateAppear()` in the same loop iteration. `animateAppear` sets `scale = Vector2.zero()` and adds a `ScaleEffect` child. But the gem itself was still in Flame's `_addLater` queue (not yet mounted). The ScaleEffect, added as a child of an unmounted component, could not advance via `update(dt)` — it sat inert in the gem's own add queue. The gem rendered at scale 0 (invisible) for the entire cascade. The `await completer.future` from the ScaleEffect would eventually resolve when the component lifecycle caught up, but by then the cascade had moved on and `syncToBoard` masked the issue by forcing `scale = Vector2.all(1.0)`.

**Fix:** Split into create → await loaded → animate. The `Component.loaded` future (Flame 1.22+) resolves after `onLoad` completes and the component is mounted. ScaleEffects added after this point are on a mounted parent and immediately participate in `update(dt)` cycles.

### placeSpecialGem
```dart
GemComponent? placeSpecialGem(int row, int col, GemType colorType, GemFunction func) {
  if (colorType.isEmpty) return null;
  gems[row][col]?.removeFromParent();    // remove whatever was there
  gems[row][col] = null;
  return _createGem(row, col, colorType, func);  // creates with function
}
```

**Note:** Passes `func` to `_createGem` but does NOT pass `rawFunc`. The `_createGem` signature is:
```dart
GemComponent _createGem(int row, int col, GemType type,
    [GemFunction func = GemFunction.neutral, int? rawFunc])
```

So `rawFunc` defaults to `null`, which means in the constructor: `rawFunction = rawFunc ?? func.value`. For standard specials (1-4), `func.value` gives the correct raw value. For mega gems, `func` would be the dominant function (from `GemFunction.fromValue` which calls `megaDominant`), and `rawFunc` would be `func.value` (e.g., 4 for chromaticOrb), NOT the mega value (e.g., 34). **This could cause mega gems placed via `placeSpecialGem` to render with the wrong shader function.** However, `placeSpecialGem` is used for newly CREATED specials (from matches), which are never mega gems — they're always single specials (1-4). Mega gems are created via attractions, which use `animateAttraction` → `updateGemFunction(dominant, raw: megaFunc)`.

### animateAttraction
```dart
Future<void> animateAttraction({posARow, posACol, posBRow, posBCol, centerRow, centerCol, megaFunc}) async {
  final gemA = gems[posARow][posACol];
  final gemB = gems[posBRow][posBCol];
  final gemCenter = gems[centerRow][centerCol];

  // Pulse sources (300ms)
  await Future.wait([gemA?.animatePulse(), gemB?.animatePulse()]);

  // Strip function from sources, apply mega to center
  gemA?.updateGemFunction(GemFunction.neutral);
  gemB?.updateGemFunction(GemFunction.neutral);
  gemCenter?.updateGemFunction(dominant, raw: megaFunc);

  // Pulse center (250ms)
  await gemCenter?.animatePulse();
}
```

Updates `gemFunction` and `rawFunction` directly on existing, already-mounted components. These will reflect on the next render frame. This is correct.

---

## 8. syncToBoard: The Safety Net

```dart
void syncToBoard(List<List<int>> cells, List<List<int>> functions) {
  // Collect tracked gems for orphan detection
  final tracked = <GemComponent>{};
  for (var r = 0; r < kBoardSize; r++) {
    for (var c = 0; c < kBoardSize; c++) {
      if (gems[r][c] != null) tracked.add(gems[r][c]!);
    }
  }

  for (var r = 0; r < kBoardSize; r++) {
    for (var c = 0; c < kBoardSize; c++) {
      final serverType = GemType.fromValue(cells[r][c]);
      final rawFunc = functions[r][c];
      final serverFunc = GemFunction.fromValue(rawFunc);
      final existing = gems[r][c];

      if (serverType.isEmpty) {
        existing?.removeFromParent();
        gems[r][c] = null;
      } else if (existing == null) {
        _createGem(r, c, serverType, serverFunc, rawFunc);    // ← creates missing gems
      } else {
        if (existing.gemType != serverType) {
          existing.updateGemType(serverType);                   // ← fixes color
        }
        if (existing.rawFunction != rawFunc) {
          existing.updateGemFunction(serverFunc, raw: rawFunc); // ← fixes function
        }
      }
      // Snap position and reset scale
      final gem = gems[r][c];
      if (gem != null) {
        gem.position = gridToPosition(r, c);
        gem.updateGridPosition(r, c);
        gem.scale = Vector2.all(1.0);     // ← FORCES SCALE TO 1.0
      }
    }
  }

  // Remove orphans
  for (final child in children.toList()) {
    if (child is GemComponent && !nowTracked.contains(child)) {
      child.removeFromParent();
    }
  }
}
```

**This fixes everything because:**
1. Missing gems → created
2. Wrong type/function → updated (fixes R2 — chromatic storm override now displayed)
3. `gem.scale = Vector2.all(1.0)` → forces any gem stuck at scale 0 to become visible
4. Position snapped → fixes any drift from failed animations

**Before the R1 fix**, syncToBoard was the only thing making fill gems visible — its `scale = Vector2.all(1.0)` rescued gems stuck at scale 0 from failed ScaleEffects on unmounted components.

---

## 9. Timing Constants Summary

| Phase | Sequencer passes | BoardLayer default | Actual used |
|-------|------------------|--------------------|-------------|
| Swap | 150ms | 150ms | 150ms |
| Removal | 350ms | 200ms | 350ms (sequencer overrides) |
| Removal settle | 150ms | — | 150ms |
| Special appear | 250ms | 150ms | 250ms |
| Activation pause | 200ms | — | 200ms |
| Activation removal | 350ms | 200ms | 350ms |
| Attraction pulse | — | 300ms | 300ms |
| Attraction result | — | 250ms | 250ms |
| Attraction settle | 200ms | — | 200ms |
| Gravity per row | 120ms | 80ms | 80ms (BoardLayer default, sequencer passes durationPerRow: kDropPerRowDuration = 120ms) |
| Drop settle | 100ms | — | 100ms |
| Fill | 300ms | 150ms | 300ms (sequencer overrides) |
| Fill settle | 150ms | — | 150ms |
| Cascade settle | 200ms | — | 200ms |
| Board sync settle | 250ms | — | 250ms |

**Wait — timing discrepancy in gravity:** The sequencer calls `_playEvent(GravityEvent)` which calls `boardLayer.animateDrops(drops, durationPerRow: kDropPerRowDuration)`. Looking at the code:

```dart
case GravityEvent():
  await boardLayer.animateDrops(
    event.drops,
    durationPerRow: kDropPerRowDuration,  // 120ms
  );
```

But `kDropPerRowDuration = Duration(milliseconds: 120)` while `kBoardDropPerRowDuration = Duration(milliseconds: 80)`. The sequencer overrides the board's default 80ms with 120ms.

**Wait — another issue:** The sequencer constructs the `GravityEvent` with drops as `({int fromRow, int fromCol, int toRow, int toCol})` records. But the backend's drop data also includes `gemType`. The sequencer strips `gemType` when creating the GravityEvent:

```dart
drops: step.drops.map((d) => (
  fromRow: d.fromRow,
  fromCol: d.fromCol,
  toRow: d.toRow,
  toCol: d.toCol,
)).toList(),
```

This is fine — `animateDrops` doesn't need gemType since it moves existing gems.

---

## 10. Data Flow: Backend Response → Visual State

### Complete trace for one cascade step with fill:

```
Backend sends CascadeStepResponse:
  removals: [(0,0), (0,1), (0,2)]      ← 3-match on row 0
  drops: [{from:(1,0)→to:(2,0)}, ...]  ← gravity
  spawns: [{row:0, col:0, gemType:3}, {row:0, col:1, gemType:5}, ...]  ← new gems
  specialGemCreated: null
  specialActivations: []
  specialAttractions: []
  injectedSpecial: null

Animation sequencer processes (flat pipeline):
  DRAIN wave 0:
    1. boardLayer.animateRemoval([(0,0),(0,1),(0,2)], 350ms)
       → gems[0][0] = null, gems[0][1] = null, gems[0][2] = null  (immediate)
       → ScaleEffect 1→0 on each gem (350ms)
       → removeFromParent() on each after animation
    2. await 150ms settle
  DRAIN waves 1..N: (none — no activations)
  PLACE: (none — no special created)
  GRAVITY:
    3. boardLayer.animateDrops([...], 120ms per row)
       → snapshot existing gems at from positions
       → clear from slots, assign to destinations
       → MoveEffect with elastic bounce
    4. await 100ms settle
  ATTRACT: (none)
  FILL:
    5. boardLayer.animateFill([{0,0,3}, {0,1,5}, ...], 300ms)
       → _createGem(0, 0, GemType.green)     → add(gem) to BoardLayer
       → _createGem(0, 1, GemType.purple)     → add(gem) to BoardLayer
       → await Future.wait(loaded) — wait for all gems to mount
       → gem.animateAppear(300ms)             → ScaleEffect 0→1
    6. await 150ms settle
  INJECT: (none)
  SETTLE: await 200ms
  → NEXT CASCADE STEP (if any)

After all steps:
  boardLayer.syncToBoard(finalBoard, finalFunctions)
  → forces scale=1.0 on all gems, creates missing, fixes types
```

### What the user sees (expected):
- Matched gems shrink to zero (350ms)
- Brief pause (150ms)
- Surviving gems drop down with bounce (variable)
- Brief pause (100ms)
- New gems appear from scale 0→1 (300ms)
- Brief pause (150ms + 200ms)
- Next cascade step begins

---

## 11. Identified Issues & Anomalies

### ISSUE 1 — RESOLVED (R1 root cause): ScaleEffect on not-yet-mounted GemComponent

**The bug:** `animateFill` called `_createGem` (queues gem via `add()`) then immediately `gem.animateAppear()` (sets `scale = Vector2.zero()`, queues ScaleEffect via `gem.add()`). The ScaleEffect sat inert in the unmounted gem's add queue — it couldn't advance via `update(dt)` because neither the gem nor the effect had gone through Flame's lifecycle. Gems stayed at scale 0 (invisible) until `syncToBoard` forced `scale = Vector2.all(1.0)`.

**The fix:** `await Future.wait([for (g in gems) g.loaded])` between creation and animation. `Component.loaded` (Flame 1.22+) resolves after `onLoad` completes. ScaleEffects added after this point are on mounted components and immediately participate in the game loop.

**Flame lifecycle rule discovered:** Never add Effects to a not-yet-mounted component. Effects on already-mounted components (removal, drops) work fine because the parent is already in the render cycle. This only manifests for newly-created components in the same async call chain.

### ISSUE 2 — RESOLVED (R2 root cause): placeSpecialGem same lifecycle issue

`placeSpecialGem` calls `_createGem` then the sequencer immediately called `gem.animateAppear(250ms)`. Same pattern as R1 — ScaleEffect on an unmounted gem. The new special gem sat at scale 0 while the old dying gem remained visible, showing the original type.

**Fix:** Added `await gem.loaded` before `gem.animateAppear()` in `animation_sequencer.dart` Phase 4.

### ISSUE 3 — FIXED: Card injection was a phantom write (no animation data)
**Status:** Resolved (2026-02-15)
**Symptom:** Heavenly Gift card places specials after fill (Hook 3), but the injected special had no animation data — it was invisible until `syncToBoard`. Subsequent cascade steps operated on a board the visual board didn't match, causing gravity animations to reference wrong positions.
**Fix:** Added `injected_special` field to `CascadeStep` (backend) and `CascadeStepResponse` (frontend DTO). Backend records `(position, function)` when injection occurs. New INJECT phase in animator replaces the existing gem with a special variant and plays `animateAppear`. For `fire_immediately` injections (updated 2026-02-17): activation stored in separate `injected_activation` field (not `all_activations`), extra gravity drops in `injected_drops`, fill spawns in `injected_spawns`. Frontend plays these as distinct INJECTED_ACTIVATION → INJECTED_GRAVITY → INJECTED_FILL phases after INJECT, maintaining 1:1 lockstep with the backend's execution order.

### ISSUE 4 (OBSERVATION): Two duration constant systems

Sequencer overrides BoardLayer defaults: removal 350ms vs 200ms, fill 300ms vs 150ms. Not a bug — the sequencer is the authoritative caller for cascade animations. BoardLayer defaults exist for standalone use (e.g., board load).

### ISSUE 5 (KNOWN LIMITATION): Cosmetic effects are hardcoded per special type, not server-driven

**Status:** Documented (2026-02-20). Not a bug — accepted coupling with inline comments.

Cell destruction is fully server-driven: `activation.affected` contains the exact positions computed by the backend's `EffectInterpreter` from `board_rules.json`. If a backend rule changes (e.g. radial bomb area grows from 3x3 to 5x5), the correct cells are destroyed on the frontend automatically.

However, **cosmetic effects** (particles, chromatic flash) are dispatched by gem function ID in `animation_sequencer.dart`, not by the backend's actual effect shape. Two specific couplings:

1. **Particle type selection** (~line 168 and ~line 371): A switch on `GemFunction` maps lineBlastH→`lineSweep(horizontal)`, lineBlastV→`lineSweep(vertical)`, radialBomb→`radialWave`, chromaticOrb→`chromaticRain`. If a backend rule changed the *shape* of an effect (e.g. bomb reconfigured to clear a cross pattern), the correct cells would still be destroyed but particles would still show a radial wave.

2. **Chromatic conversion flash** (~line 215): Mega func values `14`, `24`, `34` (the three orb combos) are hardcoded to trigger `boardLayer.flashPositions` before removal. If new orb combos were added or these combos changed behavior, this check would not adapt.

**Why this is acceptable:** The backend's four special types (H, V, Bomb, Orb) and ten mega combos are stable game design — they define the game's identity. Changing what a special *does* without also updating its visual feedback would be a design error regardless. The comments in `animation_sequencer.dart` document the coupling and describe the decoupling path (backend `effect_style` hint on `SpecialActivationResponse`) if this ever needs to change.

**Note:** Special gem *symbols* (the Unicode chars rendered on gems) are already fully theme-driven via `visual_theme.json` → `VisualThemeBase.specialSymbol()`. No hardcoded symbol mappings exist in component code.

---

## Appendix A: Full File Map (Render Pipeline)

| File | Role |
|------|------|
| `lib/game/chroma_crush_game.dart` | PvP game: move submission orchestration, syncToBoard call |
| `lib/game/campaign_game.dart` | Campaign game: same rendering pipeline, obstacle-clearing mode |
| `lib/game/game_loadout_mixin.dart` | Shared mixin: card/mega loadout, `handleSelectionChanged`, periodic shuffle timers |
| `lib/game/animation_sequencer.dart` | Cascade step → animation event decomposition and sequencing |
| `lib/game/board_layer.dart` | 8×8 grid management, all gem CRUD and animation methods |
| `lib/game/gem_component.dart` | Individual gem: lifecycle, shader/canvas render, animation effects |
| `lib/game/cascade_animator.dart` | Screen shake, flash overlay, zoom pulse, fusion sequence |
| `lib/game/particle_layer.dart` | Fire-and-forget particle effects (match burst, cascade burst, etc.) |
| `lib/game/background_layer.dart` | Ripple shader background |
| `lib/game/gem_shader_library.dart` | Shader program loading and instance creation |
| `lib/game/input_handler.dart` | Gesture state machine: idle → selected → swapping → animating |
| `lib/models/match_event.dart` | Sealed event types consumed by AnimationSequencer._playEvent |
| `lib/models/backend_contract.dart` | CascadeStepResponse, SpawnResponse, DropResponse DTOs |
| `lib/models/gem_type.dart` | GemType (colors), GemFunction (specials), mega gem helpers |
| `lib/config/animation_timings.dart` | All duration constants |
| `lib/config/visual_config.dart` | All visual effect constants (shake, flash, glow, etc.) |
| `lib/extensions/grid_math.dart` | gridToPosition, positionToGrid, isAdjacent |
| `lib/extensions/flame_effects_ext.dart` | ElasticBounceController, ShakeController, FlashOverlay |

---

## Appendix B: Cascade Step Timing Budget

For a single cascade step with matches, gravity, and fill (no specials):

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Removal animation | 350ms | 350ms |
| Removal settle | 150ms | 500ms |
| Gravity (2 rows) | 240ms | 740ms |
| Drop settle | 100ms | 840ms |
| Fill animation | 300ms | 1140ms |
| Fill settle | 150ms | 1290ms |
| Cascade settle | 200ms | 1490ms |

A 5-step cascade takes approximately 7.5 seconds minimum. With specials, the budget increases significantly per step.

---

## Appendix C: Audit — All `_createGem` → immediate animation sites

Both R1 and R2 were caused by adding Effects to unmounted components. All known sites and their status:

| Site | Pattern | Status |
|------|---------|--------|
| `board_layer.dart` `animateFill` | `_createGem` → `animateAppear` | **Fixed** — `await loaded` between create and animate |
| `animation_sequencer.dart` Phase 4 | `placeSpecialGem` → `animateAppear` | **Fixed** — `await gem.loaded` before `animateAppear` |
| `board_layer.dart` `loadBoard` | `_createGem` (no animation) | Safe — no Effects added, gems appear at default scale |
| `board_layer.dart` `syncToBoard` | `_createGem` (no animation) | Safe — no Effects added, scale forced to 1.0 |
| `board_layer.dart` `placeSpecialGem` | `_createGem` (returns gem, caller animates) | Safe — caller now awaits `loaded` |

No remaining vulnerable sites.
