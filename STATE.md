# Project State — ChromaCrush

> **Last updated:** 2026-02-22
> **Current phase:** Phase 4 Complete + Barter + Tutorial + Campaign Mode + UX Polish
> **Status:** Full card system + gold economy + barter marketplace + standalone tutorial + campaign mode (100 levels, obstacles, deadlock reshuffle, HSL obstacle tinting). Backend: 1241 tests passing. Frontend: 138 tests passing, `flutter analyze` clean. Build +13.
> **Framework version:** 7.0 (Frontend Edition — Card System + Gem Miner)
> **Older sessions:** See [FINISHED_STATE.md](FINISHED_STATE.md) for sessions prior to 2026-02-21.

---

## Session Log

<!-- Most recent first. One entry per Orchestrator work session. -->
<!-- Only the Orchestrator writes here. Subagents report status through commits. -->

### 2026-02-22 — Campaign Mode (Complete)

- **Backend: Campaign Service + API**
  - `src/modules/campaign/service.py` — `CampaignService` with `start_attempt`, `submit_move`, `activate_mega`, `abandon_attempt`, `get_player_progress`
  - `src/modules/api/routes/campaign.py` — 8 endpoints under `/api/v1/campaign/` (list levels, get level, progress, start/get/abandon attempt, submit move, activate mega)
  - `src/modules/api/schemas/campaign.py` — Request schemas (`StartAttemptRequest`, `CampaignMoveRequest`, `CampaignMegaRequest`)
  - `src/data/models/campaign_attempt.py` — ORM model + `src/data/repositories/campaign_attempt_repository.py`
  - `src/data/migrations/versions/019_campaign.py` — Alembic migration (campaign_attempts table, campaign_level column on players)
  - `config/campaign_levels.json` — 100 levels, 10 checkpoints with rewards, progressive difficulty (obstacle types, gem colors, move budgets)
  - `scripts/gen_campaign_levels.py` — Level generation script
  - `tests/unit/modules/test_campaign_service.py` + `tests/unit/modules/api/test_campaign_endpoints.py`
  - 1241 backend tests passing

- **Backend: Deadlock Detection + Reshuffle**
  - After each move/mega in campaign, checks `board_service.has_valid_moves()`
  - If deadlocked, reshuffles via `board_service.shuffle_board()` with derived seed
  - Returns `reshuffled: true` + `reshuffled_board` in API response
  - Frontend swaps board state to reshuffled board when flag is set

- **Frontend: Campaign Game + Screens (7 new files)**
  - `lib/game/campaign_game.dart` — `CampaignGame` FlameGame subclass (no bot, no PvP timers, campaign API calls)
  - `lib/widgets/campaign/campaign_screen.dart` — Level select (5-column grid, lock/unlock state, warning banner)
  - `lib/widgets/campaign/campaign_level_screen.dart` — Pre-level detail (objective, moves, obstacles, start button)
  - `lib/widgets/campaign/campaign_game_container.dart` — Campaign GameWidget wrapper + HUD integration
  - `lib/widgets/game/campaign_hud.dart` — Campaign HUD (moves remaining, obstacles remaining, score)
  - `lib/view_models/campaign_view_model.dart` — Campaign state machine (idle→loading→playing→complete/failed)
  - `lib/game/game_loadout_mixin.dart` — Shared mixin for card loadout + mega inventory (used by both ChromaCrushGame and CampaignGame)

- **Frontend: Obstacle Tinting via HSL**
  - `VisualThemeBase.obstacleColor(funcValue)` derives tinted obstacle colors from base grey (#888888)
  - HSL conversion: L from base grey, fixed S=0.30, per-type hues (H-blast→180° teal, V-blast→90° chartreuse, Bomb→250° indigo)
  - `GemComponent._resolveColor()` applies tints in both shader and canvas fallback paths
  - Changing the base grey auto-updates all obstacle tints

- **Frontend: UX Polish**
  - Campaign warning banner: "Campaign mode may prove difficult without card abilities."
  - Slimmer secondary menu buttons (vertical padding 10→6)
  - Expandable leaderboard modal (tap inline to open full-screen overlay, for small phones like iPhone SE)
  - Campaign score bar via EventBus `ScoreUpdatedEvent`

- **Production Deployment**
  - Alembic migration 019 deployed to production server
  - `campaign_attempts` table + `campaign_level` column on `players` table created

- **Build:** Bumped to `2.0.0+13`
- **New files (backend 7, frontend 7):** campaign service, routes, schemas, ORM, repo, migration, level gen script; campaign_game, campaign_screen, campaign_level_screen, campaign_game_container, campaign_hud, campaign_view_model, game_loadout_mixin
- **Modified files:** backend_contract.dart, visual_theme_service.dart, gem_component.dart, main_menu_screen.dart, app_router.dart, main.dart, api factory.py, event_bus.dart

---

### 2026-02-21 — Tutorial System + Vault Help Overlay

- **Part 1: CLI — `board enrich-tutorial` command**
  - New CLI command in `src/cli/commands/board_commands.py`
  - Reads tutorial JSON, re-processes each move via `board_svc.process_move()`, serializes full cascade step data
  - `_serialize_cascade_steps()` helper (~140 lines) mirrors cascade serialization from `matches.py`
  - Output: enriched `tutorial_script.json` with `move_result` containing `cascade_steps` per step
  - Synthetic `BoardStateResponse` metadata (size, moves_made, moves_remaining, score, has_valid_moves) so `BoardStateResponse.fromJson` works unchanged
  - 7 steps: step 1 (5 removals, 1 cascade) → step 6 (36 removals, 6 cascades, 2 activations) → step 7 (60 removals, 7 cascades, 4 activations)

- **Part 2: Frontend — Standalone Tutorial Screen (4 new files)**
  - `lib/models/tutorial_script.dart` — `TutorialScript` + `TutorialStep` data models, reuses `BoardStateResponse.fromJson` and `MoveResultResponse.fromJson`
  - `lib/game/tutorial_game.dart` — standalone `FlameGame` subclass with BoardLayout, BackgroundLayer, BoardLayer, ParticleLayer, InputHandler, CascadeAnimator, AnimationSequencer. Skips API, session, cards, megas, bot. Fresh `EventBus()` isolates tutorial events. Callbacks: `onReady`, `onStepAdvanced`, `onTutorialComplete`, `onFinalCascadeStarted`, `onWrongMove`. Wrong moves rubber-band, correct moves play full cascade via `animationSequencer.playMoveResult()`
  - `lib/widgets/tutorial/coach_overlay.dart` — `CoachOverlay` with `_SpotlightPainter` (even-odd path fill, two circular cutouts at from/to gem positions), animated hand icon (1.5s repeat, slides from→to), coach text in `GlassPanel`, tap to dismiss
  - `lib/widgets/tutorial/tutorial_screen.dart` — State machine: loading → showingCoach → waitingForInput → animating → ... → complete. `_WellDoneFlash` animated widget (2s scale+fade, shows during final cascade). `_CompletionOverlay` with "Tutorial Complete!" and back-to-menu button. Step indicator (top center), back button (top left)

- **Part 3: Route + Menu**
  - `app_router.dart` — added `/tutorial` route
  - `main_menu_screen.dart` — added TUTORIAL button (secondary style)

- **Part 4: Vault Help Overlay**
  - `lib/widgets/vault/vault_help_overlay.dart` — dimmed scrim (0.75 alpha black) with `GlassPanel` containing 4 hint rows: swap left/right to browse, swipe up to equip, swipe down for preview, drag equipped card down to unequip. Tap anywhere to dismiss
  - `lib/widgets/vault/vault_screen.dart` — added `_showHelp` state, `_GlowingHelpButton` widget (36px circle, pulsing `accentGlow` box-shadow on 2s reverse-repeat), wired into Stack above card preview overlay

- **Coach texts (7 steps):**
  1. "Swap to make a match of three or more. Some swaps produce specials."
  2. "Try another swap."
  3. "Let's make another Line Blast."
  4. "Sometimes you can swap two specials close enough together that they will fuse and form a Mega gem."
  5. "Let's match three more tiles so we can be positioned to activate the Mega gem."
  6. "Specials can be activated by being adjacent to a match, or part of a match if they share the same base color."
  7. "Now try triggering these two specials in a chain by swapping the highlighted gems."

- **Build:** Bumped to `2.0.0+12`
- **Verification:** `flutter analyze` 0 issues, `flutter test` 138/138 passing
- **New files (5):** `tutorial_script.dart`, `tutorial_game.dart`, `coach_overlay.dart`, `tutorial_screen.dart`, `vault_help_overlay.dart`
- **Modified files (4):** `app_router.dart`, `main_menu_screen.dart`, `vault_screen.dart`, `board_commands.py`
- **Asset:** `assets/config/tutorial_script.json` (enriched, 7 steps with full cascade data)

---

## Phase Checklist

<!-- Check items as they complete. Do not remove or reorder. -->
<!-- Skipped steps: mark [SKIPPED: reason]. -->

### Phase 0 — Research & Feasibility
- [x] 0.1 Requirements discovery complete
- [x] 0.2 Technology selection approved by human
- [x] 0.3 Feasibility report produced
- [x] **GATE: Human approved Phase 0** — 2026-02-05

### Phase 1 — Scouting & Architecture
- [x] 1.0 Mandatory agent initialization
  - [x] Wave 1 (parallel): Configuration Agent, Best Practices Agent, Data Agent
  - [x] Wave 2 (parallel, after Wave 1): Interface Agent, Testing Agent, Dependency Agent
- [x] 1.1 Scout dispatch complete
- [x] 1.2 Scout execution
  - [x] board: artifact + report
  - [x] scoring: artifact + report
  - [x] special_gems: artifact + report
  - [x] board_gen: artifact + report
  - [x] match: artifact + report
  - [x] matchmaking: artifact + report
  - [x] player: artifact + report
  - [x] vault: artifact + report
  - [x] energy: artifact + report
  - [x] events: artifact + report
  - [x] ads: artifact + report
  - [x] payments: artifact + report
  - [x] bot_earnings: artifact + report
  - [x] auth: artifact + report
  - [x] api: artifact + report
- [x] 1.3 Continuous review complete (all artifacts reviewed)
- [x] 1.4 Phase 1 progress report produced
- [x] **GATE: Human approved Phase 1** — 2026-02-05

### Phase 1.5 — Dry Integration Review
- [x] 1.5.1 Interface compatibility audit
- [x] 1.5.2 Data layer consistency audit
- [x] 1.5.3 Mandatory service consistency check
- [x] 1.5.4 Dependency validation
- [x] 1.5.5 Gap analysis + Dry Integration Report
- [x] **GATE: Human approved Phase 1.5** — 2026-02-05

### Phase 2 — Implementation & Integration
- [x] 2.0 Core services + data layer
  - [x] Logger service
  - [x] Config service
  - [x] Error service
  - [x] Data context
  - [x] Composition root
  - [x] CLI entry point
  - [x] Repository implementations
  - [x] Migration baseline
  - [ ] Seed data
  - [x] Core services tested (54/54 passed)
- [x] 2.1 Scout-to-coder transition
- [x] 2.2 Module implementation — all 15 modules complete, 1086 tests passing
  - [x] board: implemented + CLI commands
  - [x] scoring: implemented + CLI commands
  - [x] special_gems: implemented + CLI commands
  - [x] board_gen: implemented + CLI commands
  - [x] match: implemented + CLI commands
  - [x] matchmaking: implemented + CLI commands
  - [x] player: implemented + CLI commands
  - [x] vault: implemented + CLI commands
  - [x] energy: implemented + CLI commands
  - [x] events: implemented + CLI commands
  - [x] ads: implemented + CLI commands
  - [x] payments: implemented + CLI commands
  - [x] bot_earnings: implemented + CLI commands
  - [x] auth: implemented + CLI commands
  - [x] api: implemented + CLI commands (Wave 9, commit `69f54b1`)
- [x] 2.3 Agent Karen Compliance Sweep — all 7 stages complete
  - [x] Stage 1: Document-Level Sweep (artifact reports vs implementation docs) — 14/14 reports, no showstoppers
  - [x] Stage 2: P0 Code Review (interface-contracts only, parallel) — ~112 findings, interface-contracts.md v1.6 updated (+986 lines)
  - [x] Stage 3: P1-P3 Code Review (pre-baked checklist, parallel) — 95 findings (9 P1, 16 P2, 83 P3)
  - [x] Stage 4: Compliance Coders fix module source (parallel) — 50 fixes across 12 modules, 905 tests passing
  - [x] Stage 5: Testing Agent sweep — SKIPPED (all 905 tests passed after Stage 4)
  - [x] Stage 6: Module Architecture Reports (parallel) — 15/15 per-module reports in docs/architecture/
  - [x] Stage 7: Master architecture.md aggregated — docs/architecture/architecture.md
- [x] 2.4 Module-level testing — 1086 unit tests passing across all 15 modules
- [x] 2.5 Integration testing complete — 63 integration tests across 7 files (real PostgreSQL + Redis)
- [x] 2.6 Phase 2 completion report — docs/reports/phase2-completion-report.md
- [x] **GATE: Human approved Phase 2** — 2026-02-08

### Phase 3 — Verification & Delivery
- [x] 3.1 Final documentation (README.md)
- [x] 3.2 Human handoff
- [x] **GATE: Human accepted delivery** — 2026-02-08

### Frontend Phase 0 — Backend Survey & Project Scaffold
- [x] 0.1 Backend survey (read architecture docs, extract all API schemas)
- [x] 0.2 BackendContract generation (`backend_contract.dart` — all Dart data classes)
- [x] 0.3 Project scaffold (`flutter create`, pubspec.yaml, directory structure, service stubs)
- [x] 0.4 Scaffold verification (`flutter analyze` clean, `flutter test` passes — 48/48)
- [x] **GATE: Human approved Phase 0** — 2026-02-08

### Frontend Phase 1 — Playable Core
- [x] 1.1 ApiClient implementation (auth, match, energy endpoints + tests)
- [x] 1.2 Board rendering basic (8x8 grid, colored circles, GemComponent)
- [x] 1.3 Gesture handling + move submission (tap, drag, optimistic swap)
- [x] 1.4 Animation pipeline basic (swap, match removal, fall, cascade chain)
- [x] 1.5 Game shell (GameContainer, HUD overlay, end-of-match screen)
- [x] 1.6 Phase 1 verification (full match playable, visual sync, tests pass)
- [x] **GATE: Human approved Phase 1** — 2026-02-09

### Frontend Phase 2 — Juice Pass
- [x] 2.1 Procedural gem shaders (GLSL FragmentProgram, uniform 6-sided gem SDF)
- [x] 2.2 Particle system (Flame ParticleSystemComponent, 10 effects, 500 particle budget)
- [x] 2.3 Animation upgrade (elastic bounce, screen shake, slow-mo, fusion sequence)
- [x] 2.4 Audio engine (flutter_soloud — SFX, cascade ascending scale, fusion fanfare)
- [x] 2.5 Haptics engine (platform channel to iOS Core Haptics + stub for Windows)
- [x] 2.6 Phase 2 verification (94 tests pass, 0 analyze issues, Windows build succeeds)
- [x] **GATE: Human approved Phase 2** — 2026-02-09

### Frontend Phase 3 — Psychology Layer
- [x] 3.1 Intensity system (0.0-1.0, drives gem pulse, particles, vignette, music) — IntensityService + 18 tests
- [x] 3.2 Navigation shell full (MainMenu, Matchmaking, Settings with GoRouter) — 5 routes, shared MatchViewModel
- [x] 3.3 Post-match screens (win/loss sequences, near-miss messaging, revenge prompt) — 4-phase animated flows
- [x] 3.4 Adaptive music (flutter_soloud tempo/filter scaling with intensity) — 29 OGG tracks, speed + highpass
- [x] 3.5 Phase 3 verification (psychology loop complete, tests pass) — 112 tests, 0 analyze issues
- [x] **GATE: Human approved Phase 3** — 2026-02-09

### Frontend — Single-Player Bot Integration (Post-Phase 3)
- [x] Backend: quick-match extended with optional `bot_player_id`
- [x] Backend: `find_valid_moves()` in `bot_hints.py`
- [x] `BotApiClient` (X-API-Key auth HTTP client)
- [x] `BotHints` DTOs (typed bot hints parsing)
- [x] `BotPlayerService` (timer-driven bot, difficulty levels, debug logging)
- [x] `BotScoreUpdatedEvent` on EventBus + IntensityService wiring
- [x] `MatchViewModel` bot lifecycle (start/stop/forfeit cleanup)
- [x] `config.dart` bot player UUID + API key
- [x] `main.dart` composition root wiring
- [x] `ScoreComparisonBars` (dual bars, delayed reveal, graduated scale ticks)
- [x] Main menu: PLAY → SINGLE PLAYER
- [x] Bot difficulty tuning (easy default, variable timing)
- [x] Agent instructions rewritten (practical reference)
- [x] STATE.md updated

### Schema-Driven Refactor (Post-Phase 3)
- [x] Phase A: Backend effect schema (`board_rules.json`, `schema_loader.py`, `effect_interpreter.py`)
- [x] Phase A.4: Wire interpreter into BoardService, replace if/elif trees in detection/special_gems/mega_gems
- [x] Phase B: Cascade flow cleanup (`CascadeContext`, 10 named phases, consolidated attractions)
- [x] Phase C: Frontend visual schema (`visual_theme.json`, `VisualThemeService`, Provider registration)
- [x] Phase D: Wire visual schema into all frontend components (gem_component, particle_layer, background_layer, board_layer, player_status_bar, bot_move_preview)
- [x] Verification: `flutter analyze` 0 issues, `flutter test` 118/118 passing

### Frontend Phase 4 — Card System & Loss Aversion
> **Planning:** Phase 4A+4B complete. Phase 4C deferred for collaborative design.

**Phase 4A — Backend Card Foundation (COMPLETE)**
- [x] 4A.1 Card definitions JSON schema (`config/card_definitions.json` — 12 cards, 3 sets, 4 rarities)
- [x] 4A.2 Database migration (`005_card_tables.py` — `player_cards` table, JSON-only definitions)
- [x] 4A.3 ORM models (`player_card.py`)
- [x] 4A.4 Repository layer (CardDefinitionRepository JSON-backed, PlayerCardRepository SQLAlchemy)
- [x] 4A.5 Card DTOs (CardDefinition, PlayerCard, EquippedLoadout, MergeResult)
- [x] 4A.6 CardService (grant, equip, unequip, reorder, remove, merge)
- [x] 4A.7 API routes (8 endpoints under `/api/v1/cards/`)
- [x] 4A.8 Composition root wiring
- [x] 4A.9 Backend tests

**Phase 4B — Frontend Card Integration (COMPLETE)**
- [x] 4B.1 Backend contract DTOs (8 new classes in `backend_contract.dart`)
- [x] 4B.2 API client card endpoints (6 methods in ApiClientBase + HttpApiClient)
- [x] 4B.3 SessionManager card state (ownedCards, equippedLoadout)
- [x] 4B.4 Vault screen (equip slots + carousel + merge button + drag gestures + mouse support)
- [x] 4B.5 Card widget with foil shader (rarity styling, `foil.frag` GLSL, epic/legendary foil overlay)
- [x] 4B.6 Frontend tests (11 card DTO tests, 129 total passing)

**Phase 4C — Card Effects & Modifier Hooks (COMPLETE)**
- [x] 4C Card effect design — 55-card modifier system with 10 hooks (backend complete from prior session)
- [x] 4C Modifier hooks in cascade loop (`CascadeContext` / `_run_cascade_step_inplace`) — backend complete
- [x] 4C `applied_modifiers` field on `MoveProcessingResult` — backend complete
- [x] 4C Frontend card proc visibility — `AppliedModifierResponse` DTO, `CardProcEvent`, rune pulse animation in `PlayerStatusBar`

**Phase 4D — Mega Gem Activation + Board Shuffle (COMPLETE)**
- [x] 4D.1 Database migration `011_mega_inventory.py` (mega_gem_inventory table, 5 slots per player)
- [x] 4D.2 ORM model + repository (MegaGemInventoryModel, ensure_slots/get/consume/add)
- [x] 4D.3 InventoryService (get_mega_counts, consume_mega, grant_mega)
- [x] 4D.4 Inventory API route `GET /api/v1/inventory/mega`
- [x] 4D.5 BoardService.process_mega_activation (place mega, fire, cascade, return result)
- [x] 4D.6 MoveProcessor.process_mega_activation (validate, seed, score, persist, moves_made++)
- [x] 4D.7 MatchService.activate_mega (inventory consume, slot 0-3 cascade vs slot 4 shuffle)
- [x] 4D.8 API endpoint `POST /api/v1/matches/{match_id}/mega`
- [x] 4D.9 Frontend DTOs + API client (MegaInventoryResponse, MegaActivationRequest, getMegaInventory, activateMega)
- [x] 4D.10 PlayerStatusBar 5th slot (shuffle) + onMegaTapped + dim on empty + heart layout rework
- [x] 4D.11 ChromaCrushGame._onMegaActivated (API call, cascade animation, board sync, score update, finally block)
- [x] 4D.12 MegaActivatedEvent on EventBus + composition root wiring
- [x] 4D.13 Live testing — 5 bugs found and fixed, all 5 mega types confirmed working

**Phase 4.6 — Raid Evolution (COMPLETE)**
- [x] 4.6 Backend: `CardRaidResult` dataclass, `steal_random_equipped()`, `transfer_card()`, `unequip_to_vault()` in CardService
- [x] 4.6 Backend: `MatchFinalizer._process_card_raid()` — shield check, steal or unequip, return result
- [x] 4.6 Backend: Raid result surfaced through `MoveSubmissionResult` → API responses
- [x] 4.6 Frontend: `CardRaidResultResponse` DTO, `RaidResultEvent`, raid phase in PostMatchScreen

**Phase 4.7 — Bot Cards + Opponent Preview (COMPLETE)**
- [x] 4.7 Backend: `is_bot` guard on modifier engine (bots don't trigger card effects)
- [x] 4.7 Backend: `ensure_bot_loadout()` grants 3 random cards to bots
- [x] 4.7 Backend: `GET /cards/equipped/{player_id}` public endpoint
- [x] 4.7 Frontend: Opponent card rune glyphs on matchmaking screen

**Phase 4.8 — Energy Regen Timer (COMPLETE)**
- [x] 4.8 SessionManager `regenSecondsRemaining` + `tickRegenTimer()`
- [x] 4.8 MainMenuScreen 1s tick + 30s server re-sync timers
- [x] 4.8 `_EnergyDisplay` M:SS countdown next to hearts

**Barter System + Gold Economy (COMPLETE)**
- [x] Gold backend (economy module, `gold_balances` table, 4 endpoints, 7 tests)
- [x] Gold frontend (SessionManager gold state, main menu gold display, login fetch)
- [x] Exchange button in vault (sell 3 equipped cards for gold, side-by-side with merge)
- [x] Barter marketplace screen (arsenal mega specials + forge supply card packs, buy with gold)
- [x] Confirmation dialogs for merge and exchange (CupertinoAlertDialog)
- [x] Inventory display on barter page (owned count per mega slot)

**Tutorial System (COMPLETE)**
- [x] CLI `board enrich-tutorial` command (re-process moves, serialize cascade steps into tutorial JSON)
- [x] `TutorialScript` + `TutorialStep` data models (reuse `BoardStateResponse`, `MoveResultResponse`)
- [x] `TutorialGame` standalone FlameGame (all visual components, no API/session/cards)
- [x] `CoachOverlay` (spotlight cutouts, animated hand, coach text, tap to dismiss)
- [x] `TutorialScreen` (state machine, "Well done!!" flash, completion overlay, step indicator)
- [x] Route `/tutorial` + TUTORIAL menu button
- [x] Enriched `tutorial_script.json` asset (7 steps, seed 1234, full cascade data)

**Vault Help Overlay (COMPLETE)**
- [x] `VaultHelpOverlay` (dimmed scrim, 4 gesture hint rows in GlassPanel)
- [x] `_GlowingHelpButton` (pulsing question mark, top-right of vault screen)

**Phase 4 Verification (COMPLETE)**
- [x] 4.9 Phase 4 verification (card equip flow, modifier procs, raid animations, tests pass)
- [x] **GATE: Human approved Phase 4**

### Campaign Mode (COMPLETE)
- [x] Backend campaign service (100 levels, obstacle-clearing objective, progressive difficulty)
- [x] Campaign level definitions JSON (`config/campaign_levels.json` — 100 levels, 10 checkpoints with card pack rewards)
- [x] Database migration 019 (campaign_attempts table, campaign_level on players)
- [x] Campaign API routes (8 endpoints: list levels, get level, progress, start/get/abandon attempt, submit move, activate mega)
- [x] Campaign deadlock detection + auto-reshuffle (reuses `board_service.has_valid_moves` + `shuffle_board`)
- [x] Frontend CampaignGame FlameGame (skips PvP components, uses campaign API)
- [x] Campaign level select screen (5-column grid, lock/unlock, warning banner)
- [x] Campaign level detail screen (objective display, start button)
- [x] Campaign HUD (moves remaining, obstacles remaining, score)
- [x] Campaign view model (state machine: idle→loading→playing→complete/failed)
- [x] GameLoadoutMixin (shared card loadout + mega inventory for both game modes)
- [x] HSL obstacle tinting (deterministic color derivation from base grey per special type)
- [x] Campaign score bar + expandable leaderboard modal
- [x] Production deployment (Alembic 019 migrated)
- [x] **GATE: Human confirmed campaign mode success**

### Frontend Phase 5 — Monetization & Polish
- [DEFERRED] 5.1 Ad integration (google_mobile_ads — interstitial, rewarded, banner, card slot unlock ads)
- [x] 5.2 In-app purchase (complete)
- [x] 5.3 Card economy monetization (complete — gold economy, barter marketplace, card packs)
- [x] 5.5 Social screens — leaderboard (complete)
- [ ] 5.6 Near-miss polish (board sparkle, idle tease)
- [ ] 5.7 Phase 5 verification (remaining items, tests pass)
- [ ] **GATE: Human approved Phase 5**

### Frontend Phase 6 — LiveOps
- [ ] 6.1 Flash event system UI + event-themed card drops
- [ ] 6.2 Card balance patches via server-side config
- [ ] 6.3 A/B testing infrastructure (psychology params + card balance tuning)
- [ ] 6.4 Performance optimization pass
- [ ] 6.5 Accessibility audit
- [ ] **GATE: Human approved Phase 6**

### Frontend Phase 7 — Gem Miner Mode
> **Planning note:** This phase will be planned in detail with the human when reached. Steps are directional. See `roadmap_new_features.md` for Gem Miner ideas, dirt mask code examples, and optimization notes.
- [ ] 7.1 Gem Miner design & schema (game mode JSON, vein types, monster rules, dust currency)
- [ ] 7.2 Grid augmentation (16-bit dirt mask, 4×4 subsampling, virtual 32×32 positioning)
- [ ] 7.3 Miner renderer (ProceduralGridRenderer, dirt shader, batch rendering, culling)
- [ ] 7.4 Miner gameplay (click-to-mine, passive hearts, dust, monster encounters)
- [ ] 7.5 Cross-mode resources (shared hearts, artifact drops → vault, dust upgrades)
- [ ] 7.6 Phase 7 verification (Miner playable, 60fps, cross-mode sync, tests pass)
- [ ] **GATE: Human approved Phase 7**

---

## Key Decisions

<!-- Numbered. Never removed. Never relitigated unless human requests. -->

1. **Tech stack: FastAPI + PostgreSQL + Redis** — Accept GDD recommendations for backend. Phase 0.2. Rationale: Native async, excellent bot API support via OpenAPI.

2. **Task queue: arq over Celery** — Simpler async-native alternative. Phase 0.2. Rationale: Matches FastAPI's async model, uses existing Redis, lower operational complexity.

3. **Rendering: Pixi.js over raw Canvas** — WebGL-accelerated rendering library. Phase 0.2. Rationale: Required for particle effects, animations, and visual juice without building from scratch.

4. **State management: Zustand** — Lightweight React state library. Phase 0.2. Rationale: 1KB bundle, minimal boilerplate, good DevTools support.

5. **Auth: JWT + API keys (hybrid)** — JWT for human sessions, API keys for bots. Phase 0.2. Rationale: Different auth flows suit different client types.

6. **Deployment: Local-first, AWS-ready** — Docker Compose for local dev, architected for ECS Fargate + RDS + ElastiCache. Phase 0.2. Rationale: Minimizes deployment friction while enabling cloud scaling.

7. **Scope: Full Alpha per GDD** — Core match-3 engine, basic versus mode, API endpoints, web client. Phase 0.2. Rationale: Human preference for complete Alpha implementation.

8. **Bot earnings module** — Add `bot_earnings` as 15th module (Wave 8). Phase 1.1. Rationale: Enable future bot revenue sharing. Tracks earnings ledger and payout requests. Actual payout integration deferred — initial implementation allows balance viewing and manual payouts.

9. **WebSocket support** — Add WebSocket transport alongside REST API. Phase 1.5. Rationale: Enterprise UI requires real-time updates for match state, energy regeneration, and matchmaking notifications. REST remains primary; WebSocket is additive for subscriptions.

10. **Karen Compliance Team — 7-Stage Sweep** (Backend) — Expand Agent Karen from review-only to Compliance Team Lead with a structured 7-stage process. Phase 2.3. Rationale: Guidance drift accumulated across context windows during module implementation. Stages: (1) Document-level sweep comparing artifact reports vs impl docs — lightweight, catches design drift. (2) P0 code review — interface-contracts only, laser-focused, ~2k context per agent. (3) P1-P3 code review using pre-baked checklist extract (not raw guidance docs). (4) Compliance Coders fix module source only — do NOT touch tests. (5) Testing Agents fix all tests in grouped sweeps (sync-pure / async-repos / Redis / presentation) using fix reports + change reports. (6) Architecture Reporters produce per-module architecture docs from corrected code. (7) Karen aggregates into project-wide architecture.md.

11. **Frontend framework: Flutter/Dart over native Swift** — Enables development on Windows, `flutter test` verification loop, web preview via Chrome. iOS only target. Trade-off: lose some Core Haptics fidelity (mitigated by platform channel), gain testability and development velocity. Frontend Phase 0.

12. **Audio engine: flutter_soloud** — SoLoud C++ engine via Flutter binding. Provides multi-voice, pitch shifting, real-time filters, faders — covers ~90% of AVAudioEngine design skeleton spec. Procedural synthesis replaced by pre-rendered short audio files with runtime pitch/filter manipulation. Frontend Phase 0.

13. **Two-grid gem model** — Replace single int8 grid (where specials were negative values) with two parallel int8 arrays: `grid` (colors 0-6) and `func_grid` (functions 0-4). Specials now carry a base color and participate in same-color matches naturally. Match detection only reads colors, so zero logic changes needed there. Frontend Phase 1. Rationale: Enables Candy Crush-style colored specials; old negative encoding made specials invisible to match detection and unrenderable with a base color.

14. **Match-end workaround for single-player** — Frontend triggers match end on `movesRemaining == 0` in addition to `matchCompleted == true`. Backend requires both players to have 0 moves for `matchCompleted`, but bots never play moves. Frontend Phase 3. Rationale: Unblocks single-player mode. TODO: remove once backend auto-completes bot matches or multiplayer "waiting for opponent" state is added. See `chroma_crush_game.dart` line 272.

16. **Schema-driven gems, specials, and visuals** — All special gem creation rules, effect areas, mega combos, and attraction mechanics extracted from hardcoded if/elif trees into `config/board_rules.json`, interpreted by `EffectInterpreter`. All frontend visual values (gem colors, shapes, shader params, particle colors, background tints) extracted into `assets/config/visual_theme.json`, loaded by `VisualThemeService`. Cascade step refactored from 14-step monolith to 10 named phases with `CascadeContext`. Post-Phase 3. Rationale: Enables designers to tune game rules and visuals via JSON without code changes. Makes cascade flow debuggable and testable per-phase.

15. **Server-integrated bot opponent** — Bot plays through the real backend API using X-API-Key auth and the backend's built-in bot hints system. No local game logic. A pre-seeded bot player (UUID in `config.dart`) plays moves via `BotPlayerService` timer loop. Default difficulty: easy (random move from all valid moves, 4-8s delay). Scores are 100% server-computed. Post-Phase 3. Rationale: Validates the backend's bot API layer end-to-end while providing a real single-player opponent. Future TODO: auto-create a dedicated bot per user at registration time.

18. **Mega gem activation = refunded move with persistent inventory** — Mega activation reuses the full cascade pipeline (`process_move`-style logic) but does NOT decrement `moves_remaining`. It DOES increment `moves_made` (needed for unique `move_number` in match_moves table). 5 inventory slots per player: slots 0-3 for mega gem types (values 14/24/34/44), slot 4 for shuffle (calls `shuffle_board` instead of cascade). Inventory is persistent in `mega_gem_inventory` table. Void Instability card is net-zero — grants + consumes shuffle atomically via `source="void_instability"` flag. Phase 4D. Rationale: Reusing cascade infrastructure keeps behavior consistent and deterministic. Refunding the move makes megas feel like bonus power, not a wasted turn.

19. **Gold economy + barter marketplace** — Soft currency ("gold") earned by selling equipped cards (40% of card `base_value`), spent in the barter marketplace on mega specials and card packs. Backend: `economy` module with `gold_balances` table, 4 endpoints (get balance, sell cards, buy item, list marketplace). Marketplace items are config-driven in `service.py` (5 arsenal megas + 4 forge supply card packs). Exchange sells all 3 equipped cards at once. Confirmation dialogs on merge and exchange to prevent accidental actions. Phase 4. Rationale: Creates a meaningful economy loop (play → earn cards → sell duplicates → buy megas/packs) and implements Phase 5.3 card economy monetization ahead of schedule.

17. **Card system: JSON-only definitions, DB instances** — Card definitions stored in `config/card_definitions.json` (static catalog loaded into memory by CardService), NOT in a database table. Player card instances stored in `player_cards` DB table with UUID PK, positional equip ordering (positions 1-3 = equipped, 4+ = vault). Sequential integer card IDs. Merge consumes 3 same-rarity equipped cards → 1 random card of next rarity tier. No `trigger`/`effect` fields yet — Phase 4C after collaborative design with human. Phase 4A. Rationale: JSON-only definitions are simpler to manage and edit; DB instances track ownership and equip state which needs transactional integrity.

20. **Campaign mode: obstacle-clearing single-player** — 100 levels with progressive difficulty. Objective: clear all obstacles (cells=7) within a move budget. 10 checkpoint levels (every 10th) award card pack rewards. Obstacles interact with specials via the existing effect system (H-blast, V-blast, bomb clear adjacent obstacles; chromatic orb clears all of one type). Deadlock auto-reshuffles board. Level definitions in `config/campaign_levels.json`. HSL-based obstacle tinting derives per-type colors from a single base grey value. Campaign mode. Rationale: Adds single-player progression alongside the PvP match-3 mode, giving players a reason to earn cards and megas.

---

## Active Blockers

<!-- Remove when resolved. -->

(none)

---

## Document Map

<!-- Status: draft | final | not yet created -->

| Document | Path | Status |
|----------|------|--------|
| Finished Session Log | ./FINISHED_STATE.md | archived (2026-02-05 through 2026-02-09) |
| **Frontend Phase** | | |
| Framework (Frontend v7.0) | ./FRAMEWORK.md | final |
| Roadmap & Feature Ideas | ./roadmap_new_features.md | living doc — planning input for Phase 4 & 7 |
| iOS Design Skeleton | ./ChromaCrush_iOS_Frontend_Design_Skeleton.md | final |
| Flutter App Scaffold | chromacrush_app/ | final |
| Backend Contract (Dart) | chromacrush_app/lib/models/backend_contract.dart | final |
| **Backend Reference** | | |
| Master Architecture | docs/architecture/architecture.md | final |
| Architecture — per-module (15) | docs/architecture/[module].md | final |
| README | README.md | final |
| **Backend (Deprecated — in deprecated/)** | | |
| Backend Framework (v4.0) | deprecated/FRAMEWORK.md | archived |
| GDD | ./ChromaCrush_Game_Design_Document.pdf | final |
| All guidance docs | deprecated/guidance/ | archived |
| All artifacts | deprecated/artifacts/ | archived |
| All reviews | deprecated/reviews/ | archived |
| All implementation docs | deprecated/implementation/ | archived |
| All reports | deprecated/reports/ | archived |
| Feasibility Report | deprecated/feasibility-report.md | archived |
