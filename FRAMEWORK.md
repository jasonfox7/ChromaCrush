# LLM-Orchestrated Multi-Agent Development Framework — Frontend Edition

> **Version:** 7.0
> **Target stack:** Flutter / Dart (Flame + flutter_soloud) — iOS only
> **Execution model:** Parallel agents dispatched by an orchestrator
> **Backend status:** Complete (v1.0.0 on `main`) — 16 modules (incl. campaign), 63 REST endpoints, 1241 tests
> **Design source:** `ChromaCrush_iOS_Frontend_Design_Skeleton.md`
> **Development platform:** Windows (Flutter SDK) — iOS builds via macOS CI or remote Mac
> **v7.0 additions:** Card/Artifact meta-game system (Phase 4), Gem Miner mode (Phase 7), schema-driven multi-mode vision

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Services Layer & Dependency Architecture](#services-layer--dependency-architecture)
3. [Agent Roster & Responsibilities](#agent-roster--responsibilities)
4. [Shared Infrastructure](#shared-infrastructure)
5. [Phase 0 — Backend Survey & Project Scaffold](#phase-0--backend-survey--project-scaffold)
6. [Phase 1 — Playable Core](#phase-1--playable-core)
7. [Phase 2 — Juice Pass](#phase-2--juice-pass)
8. [Phase 3 — Psychology Layer](#phase-3--psychology-layer)
9. [Phase 4 — Card System & Loss Aversion](#phase-4--card-system--loss-aversion)
10. [Phase 5 — Monetization & Polish](#phase-5--monetization--polish)
11. [Phase 6 — LiveOps](#phase-6--liveops)
12. [Phase 7 — Gem Miner Mode](#phase-7--gem-miner-mode)
13. [Artifact & Documentation Standards](#artifact--documentation-standards)
14. [Dispute Resolution Protocol](#dispute-resolution-protocol)
15. [Version Control Workflow](#version-control-workflow)
16. [Cold-Start Recovery Protocol](#cold-start-recovery-protocol)
17. [Appendix A — Component Artifact Template](#appendix-a--component-artifact-template)
18. [Appendix B — Glossary](#appendix-b--glossary)
19. [Appendix C — Future Vision (Benched)](#appendix-c--future-vision-benched)

---

## Core Principles

Non-negotiable. Every agent, every phase.

1. **No Hot Fixes.** Cross-component or services-layer problems are escalated, never patched in place.
2. **Server Is Truth.** The frontend makes ZERO game logic decisions. It sends moves, receives results, renders spectacle. Board state, scoring, matchmaking, vault — all server-authoritative.
3. **Services Are Injected, Never Global.** No widget or component creates or directly imports services. All services arrive through constructor injection or Provider/context lookup from the composition root.
4. **Widgets Are Dumb.** Flutter widgets and Flame components read state and dispatch actions. Business decisions live in view models or the services layer.
5. **Layers Are Distinct.** Models (data classes) / Services (APIClient, Audio, Haptics) / ViewModels (ChangeNotifier) / Widgets (Flutter + Flame) — never bleed across boundaries.
6. **Backend Contract Is Generated.** All Dart data classes matching backend JSON schemas live in `backend_contract.dart`, generated from backend survey. No hand-typed API schemas.
7. **Animations Are Data-Driven.** The AnimationSequencer consumes a backend event array and produces chained Flame effects/actions. No animation logic is hardcoded to specific game states.
8. **Design Skeleton Before Code.** The iOS Frontend Design Skeleton is the authoritative design document. Implementation follows its specs. Deviations documented with justification.
9. **Edge Cases Flow Upstream.** Undocumented situations escalated to the Orchestrator. No improvisation.
10. **Context Window Discipline.** No agent gets more work than it can hold in context. Split when in doubt.
11. **Human-in-the-Loop at Phase Gates.** No phase transition without explicit human approval.
12. **Recoverable by Design.** All project state captured such that any agent with zero context can resume from STATE.md alone.
13. **Visual Sync Invariant.** After any animation sequence completes, the visual board MUST exactly match the server's `board_state`. Animations are cosmetic — the server result is reality.
14. **Tests Run on Every Change.** `flutter test` is the verification loop. Every agent runs tests before committing. No blind code — if it doesn't pass tests, it doesn't ship.

---

## Services Layer & Dependency Architecture

The frontend has five injectable services. All created at app startup and provided to the widget tree via `MultiProvider` and to the Flame game via constructor injection.

### Injection Pattern: Provider + Constructor

```dart
// main.dart — composition root
void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final apiClient = ApiClient(baseUrl: AppConfig.apiBaseUrl);
  final audioEngine = AudioEngine();
  final hapticsEngine = HapticsEngine();
  final sessionManager = SessionManager(apiClient: apiClient);
  final eventBus = EventBus();

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: apiClient),
        Provider<AudioEngine>.value(value: audioEngine),
        Provider<HapticsEngine>.value(value: hapticsEngine),
        ChangeNotifierProvider<SessionManager>.value(value: sessionManager),
        Provider<EventBus>.value(value: eventBus),
      ],
      child: const ChromaCrushApp(),
    ),
  );
}
```

**Rules:**
- No service is created inside a Widget or Component. They are created once in `main()`.
- The Flame `FlameGame` subclass receives services through its constructor (Flame cannot use `context`).
- `VisualThemeBase` is injected via both Provider (for widgets like `BotMovePreview`) and constructor (for Flame components like `GemComponent`, `ParticleLayer`, `BackgroundLayer`).
- Abstract classes define service interfaces for testability. Concrete implementations injected at the composition root.
- Services that hold mutable state extend `ChangeNotifier`. Stateless services are plain classes.

---

### Service: ApiClient

All backend communication. Async/await, JSON serialization, HTTP.

**Responsibilities:**
- HTTP requests to all backend endpoints (55 core + card system endpoints).
- Auth token management (JWT storage via flutter_secure_storage, refresh, header injection).
- Request retry with exponential backoff.
- Response deserialization into BackendContract types.
- Error mapping (network errors, server errors, auth errors → typed `AppError`).
- Card system endpoints (Phase 4): `/vault/cards`, `/match/equip`, card-aware move submission.

**Not responsible for:** Game logic, UI decisions, caching policy beyond HTTP cache.

**Package:** `http` (dart:io built-in) or `dio`. Prefer `http` for simplicity.

---

### Service: AudioEngine

Layered sound via flutter_soloud (SoLoud C++ engine). Three logical buses: SFX, Music, Ambient.

**Responsibilities:**
- SFX playback with pitch shifting (match chimes, cascade ascending scale, fusion fanfare).
- Adaptive background music (playback speed + filter driven by intensity system).
- Ambient tension hum (volume driven by intensity system).
- Sound pooling via SoLoud's multi-voice support (4 simultaneous match sounds, 4 cascade, 2 special, 2 UI, 1 notification).
- Volume settings persistence.
- Real-time filter effects (reverb, bass boost, EQ) via SoLoud's built-in filter chain.

**Package:** `flutter_soloud`

---

### Service: HapticsEngine

iOS Core Haptics patterns for physical feedback, accessed via platform channel.

**Responsibilities:**
- Pre-built haptic patterns for all game events (match, cascade, fusion, victory, loss, raid).
- Intensity scaling per chain step.
- Device capability detection.
- Haptics enabled/disabled setting.
- Fallback to `HapticFeedback` (Flutter built-in) for basic patterns during development/testing on non-iOS.

**Implementation:** Dart interface with two backends:
1. `IOSHapticsEngine` — platform channel to Swift Core Haptics (AHAP patterns). Used on iOS.
2. `StubHapticsEngine` — no-op or basic `HapticFeedback.lightImpact()`. Used during Windows development and testing.

---

### Service: SessionManager

Player state that persists across screens. Extends `ChangeNotifier`.

**Responsibilities:**
- Auth state (token, player profile, anonymous vs registered).
- Energy state (hearts, regen timer — client-side countdown, server-validated on action).
- Match state (active match ID, game state during play).
- Equipped cards (`equippedCards: List<CardId>`) — synced with backend on equip/unequip.
- Daily streak state.
- Revenge targets.
- Ad-free purchase status.
- App settings (audio, haptics toggles).

**Sources:** Populated from backend API responses. Cached locally for offline display. Server is truth — local state is convenience.

---

### Service: EventBus

Stream-based pub/sub for cross-layer communication.

**Responsibilities:**
- Decouples Flame (game scene) from Flutter widgets (HUD, navigation).
- Events: move submitted, match resolved, chain step, score updated, match ended, energy changed, raid notification.
- Type-safe event classes with sealed class hierarchy.
- No retained state — fire and forget. Subscribers manage their own state.

**Implementation:** `StreamController.broadcast()` with typed event classes.

---

### Service Lifecycle

| Phase | Service Role |
|-------|-------------|
| 0 | Services designed, abstract interfaces defined, BackendContract generated |
| 1 | ApiClient + SessionManager functional. AudioEngine + HapticsEngine stubbed (silent). EventBus wired. |
| 2 | AudioEngine (flutter_soloud) + HapticsEngine (platform channel) fully implemented. All services integrated with game scene. |
| 3 | Services stable. Psychology layer consumes existing service APIs. |
| 4 | SessionManager gains `ownedCards` + `equippedLoadout`. ApiClient gains 6 card + 2 mega inventory endpoints. BackendContract adds 8 card DTOs + 3 mega DTOs. CardService backend with JSON definitions + DB instances. InventoryService manages 5 mega gem slots per player. `applied_modifiers` on `MoveProcessingResult` deferred to 4C. |
| 5+ | Services stable. Monetization and new modes consume existing service APIs. |

---

## Agent Roster & Responsibilities

### Execution Model

Same as backend: subagents dispatched by the Orchestrator. Each reads its role instructions, writes to scoped directories, and communicates through committed files.

**Key advantage over native iOS:** All agents can run `flutter test` to verify their work. No blind code generation.

---

### Orchestrator

**Role:** Pure coordination. Never implements code.

**Responsibilities:**
- Dispatches agents in dependency-ordered waves within each phase.
- Tracks progress in STATE.md.
- Owns the design skeleton interpretation — resolves ambiguities.
- Produces human-facing reports at phase gates.
- Sole writer of shared guidance docs.
- Dispatches parallel Karen instances for verification.
- Enforces visual sync invariant across all animation work.
- Runs `flutter test` as gate verification before presenting phase to human.

**Context discipline:** No agent gets more than one Flame system (e.g., BoardLayer OR ParticleLayer OR AnimationSequencer, not all three) or more than 3 Flutter widgets simultaneously.

---

### Mandatory Agents

#### Backend Integration Agent

**Domain:** ApiClient implementation, BackendContract generation, request/response mapping.

Responsible for:
- Surveying backend architecture docs and source code.
- Generating `backend_contract.dart` from backend API schemas.
- Defining ApiClient abstract interface and error handling.
- Ensuring all 55 endpoints are covered with correct types.
- Polling vs push strategy per data type.

#### Rendering Agent

**Domain:** Flame rendering standards, shader architecture, animation timing.

Responsible for:
- Gem shader spec compliance (SDF shapes, uniforms, visual layers via GLSL FragmentProgram).
- Animation timing standards (from design skeleton Section 4.2).
- Performance budget enforcement (500 particle cap, 60fps target).
- Visual sync invariant enforcement.
- Visual parameter standards.

#### Sensory Agent

**Domain:** Audio engine (flutter_soloud), haptics engine, intensity system.

Responsible for:
- SFX standards using flutter_soloud (sound loading, pitch shifting, filter chains).
- Haptic pattern specifications (Core Haptics via platform channel).
- Cascade audio escalation (ascending pitch chain via SoLoud pitch parameter).
- Intensity system inputs/outputs (design skeleton Section 4.4).
- Adaptive music parameters (playback speed, filter manipulation).

#### UX Agent

**Domain:** Flutter widget navigation, screen flow, psychology mechanics.

Responsible for:
- Navigation architecture compliance (GoRouter or Navigator 2.0, screen transitions).
- Post-match screen flow (win/loss/near-miss sequences from design skeleton Section 7).
- State management patterns (ChangeNotifier, Provider, context lookup).
- Accessibility standards.
- Play-again flow (minimize friction between matches).

#### Testing Agent

**Domain:** Test strategy, flutter_test, widget testing.

Responsible for:
- Unit test standards (flutter_test, mock services via abstract interfaces).
- Widget test coverage (every screen widget has a widget test with mock data).
- Flame component testability patterns (component unit tests with mock services).
- Integration test approach (ApiClient against test server).
- `flutter test` must pass on Windows without iOS simulator.

---

### Scout Swarm (Lightweight)

The iOS Design Skeleton replaces traditional scouting for most components. Scouts are only dispatched for:
- **Backend survey** (Phase 0) — reading backend source to generate backend_contract.dart.
- **Component deep-dives** — when a design skeleton section needs expansion before implementation (e.g., shader math, SoLoud filter chains).

Most work goes directly to coding agents guided by the design skeleton.

---

### Agent Karen (Verification Agent)

**Role:** Quality gate between design skeleton intent and actual implementation.

**Mandatory compliance checks:**
- No global service access (no singletons, no static service instances, no service locators outside main.dart).
- No game logic in widgets (widgets read state + dispatch, nothing else).
- Visual sync invariant (animations resolve to server board state).
- Animation timing matches design skeleton specs (within 20% tolerance).
- All BackendContract types match actual backend schemas.
- No hardcoded API URLs or auth tokens.
- Performance budget respected (particle counts, frame rate).
- All `flutter test` tests pass.
- No platform-specific imports in non-platform-channel code (keep Dart pure except ios/ directory).

---

## Shared Infrastructure

### Project Structure

```
chromacrush_app/                         # Flutter project root (inside ChromaCrush/)
├── lib/
│   ├── main.dart                        # Entry point — composition root
│   ├── config.dart                      # API URL, feature flags
│   ├── config/
│   │   ├── game_config.dart             # Board dimensions, cell sizes, layout constants
│   │   ├── visual_config.dart           # Animation/rendering constants (pulse, glow, shake)
│   │   ├── visual_theme_service.dart    # VisualThemeBase abstract + VisualThemeService (loads visual_theme.json)
│   │   ├── animation_timings.dart       # Duration constants for all animations
│   │   └── audio_config.dart            # Audio channel counts, volume defaults
│   ├── models/
│   │   ├── backend_contract.dart        # GENERATED — all API response/request types
│   │   ├── tutorial_script.dart         # Tutorial data models (TutorialScript, TutorialStep)
│   │   ├── gem_type.dart                # GemType + GemFunction enums
│   │   ├── match_event.dart             # Backend event types for animation sequencer
│   │   ├── view_state.dart              # UI state enums (loading, playing, postMatch)
│   │   └── app_error.dart               # Typed error cases (sealed class)
│   ├── services/
│   │   ├── api_client.dart              # Abstract interface + HTTP implementation
│   │   ├── audio_engine.dart            # flutter_soloud wrapper
│   │   ├── haptics_engine.dart          # Abstract + iOS platform channel + stub
│   │   ├── session_manager.dart         # Auth, energy, match state (ChangeNotifier)
│   │   └── event_bus.dart               # Stream-based pub/sub
│   ├── view_models/
│   │   ├── match_view_model.dart        # PvP game state management during match
│   │   ├── campaign_view_model.dart     # Campaign state machine (idle→loading→playing→complete/failed)
│   │   ├── vault_view_model.dart
│   │   ├── leaderboard_view_model.dart
│   │   └── ...
│   ├── widgets/
│   │   ├── shell/
│   │   │   ├── navigation_shell.dart    # Root navigation
│   │   │   ├── main_menu.dart           # Play button, energy, streak, vault preview
│   │   │   ├── matchmaking_screen.dart  # Search animation, opponent reveal
│   │   │   └── settings_screen.dart     # Audio, haptics, account
│   │   ├── game/
│   │   │   ├── game_container.dart      # GameWidget wrapper + HUD overlay (PvP)
│   │   │   ├── campaign_hud.dart        # Campaign HUD (moves, obstacles, score)
│   │   │   └── game_hud_overlay.dart    # Score, moves remaining, chain counter
│   │   ├── post_match/
│   │   │   ├── post_match_screen.dart   # Win/loss orchestration
│   │   │   ├── vault_raid_animation.dart
│   │   │   ├── near_miss_view.dart
│   │   │   └── revenge_prompt.dart
│   │   ├── vault/
│   │   │   ├── vault_screen.dart        # Collection grid + card preview/upgrade UI + glowing help button
│   │   │   ├── vault_help_overlay.dart  # Dismissable gesture hints overlay (dimmed scrim + GlassPanel)
│   │   │   ├── card_widget.dart         # Card rendering with rarity glow + foil shader
│   │   │   ├── artifact_detail.dart     # Individual artifact showcase
│   │   │   └── artifact_shield.dart     # Shield status, ad-to-protect flow
│   │   ├── tutorial/
│   │   │   ├── tutorial_screen.dart     # Standalone tutorial (state machine, coach overlay, completion)
│   │   │   └── coach_overlay.dart       # Dim + spotlight cutouts + animated hand + coach text
│   │   ├── campaign/                    # Campaign mode — single-player level progression
│   │   │   ├── campaign_screen.dart     # Level select grid (5-col, lock/unlock, warning banner)
│   │   │   ├── campaign_level_screen.dart # Pre-level detail (objective, moves, obstacles, start)
│   │   │   └── campaign_game_container.dart # Campaign GameWidget wrapper + HUD
│   │   ├── cards/                       # Phase 4 — Card equip system
│   │   │   ├── card_equip_screen.dart   # Equip slots, drag-drop, loadout saves
│   │   │   └── card_detail.dart         # Card stats, merge UI, rarity display
│   │   ├── social/
│   │   │   ├── leaderboard_screen.dart
│   │   │   └── stats_screen.dart
│   │   └── store/
│   │       ├── ad_free_upgrade.dart     # $1 purchase flow
│   │       └── energy_refill.dart       # Rewarded ad → heart flow
│   ├── game/                            # Flame engine layer
│   │   ├── chroma_crush_game.dart       # FlameGame subclass — main PvP game scene
│   │   ├── campaign_game.dart           # Campaign FlameGame subclass (no bot, campaign API)
│   │   ├── game_loadout_mixin.dart      # Shared mixin for card loadout + mega inventory
│   │   ├── tutorial_game.dart           # Standalone FlameGame for tutorial (no API/session/cards)
│   │   ├── board_layer.dart             # 8×8 gem grid component + swap gesture
│   │   ├── gem_component.dart           # Individual gem — shader + pulse animation
│   │   ├── gem_shader_library.dart      # Fragment shader loading + uniform management
│   │   ├── animation_sequencer.dart     # Backend events → chained Flame effects
│   │   ├── cascade_animator.dart        # Multi-step cascade visual flow
│   │   ├── particle_layer.dart          # Particle emitter management + budget
│   │   ├── modifier_layer.dart          # Phase 4 — Card proc overlays, slot icon pulse, activation VFX
│   │   └── miner/                       # Phase 7 — Gem Miner mode
│   │       ├── miner_game.dart          # Miner FlameGame subclass
│   │       ├── dirt_grid_layer.dart     # Dirt rendering with 4×4 subsampling
│   │       └── miner_input.dart         # Click-to-mine interaction
│   ├── audio/
│   │   ├── sound_bank.dart              # Enum of all sounds → asset paths + params
│   │   └── music_engine.dart            # Adaptive background music (tempo/filter)
│   ├── haptics/
│   │   └── haptic_patterns.dart         # Pattern definitions (Dart-side, sent to iOS)
│   └── extensions/
│       ├── flame_effects_ext.dart       # Custom easing, shake, zoom, slow-mo effects
│       ├── grid_math.dart               # Grid coordinate ↔ screen position math
│       └── gem_colors.dart              # DEPRECATED — empty, all lookups via VisualThemeBase
├── shaders/                             # GLSL fragment shaders (.frag)
│   ├── gem_base.frag                    # Base gem shape + color + glow + specials + mega aura
│   ├── ripple_background.frag           # Ripple background shader
│   └── foil.frag                        # Holographic foil shader for card overlays (epic/legendary)
├── assets/
│   ├── config/
│   │   ├── visual_theme.json            # All visual values: gem colors, shapes, shader params, particle colors, background tints
│   │   ├── campaign_levels.json         # 100 campaign level definitions (obstacles, moves, checkpoints, rewards)
│   │   └── tutorial_script.json         # Enriched 7-step tutorial (seed 1234, full cascade data)
│   ├── audio/                           # Pre-rendered sound files for SoLoud
│   │   ├── sfx/                         # Match chimes, cascade tones, UI sounds
│   │   └── music/                       # Background loops
│   └── particles/                       # Particle sprite sheets (if needed)
├── ios/
│   └── Runner/
│       ├── HapticsChannel.swift         # Platform channel → Core Haptics (AHAP)
│       └── Info.plist
├── test/
│   ├── unit/                            # Pure Dart unit tests
│   │   ├── models/
│   │   ├── services/
│   │   └── view_models/
│   ├── widget/                          # Flutter widget tests
│   │   ├── shell/
│   │   ├── game/
│   │   ├── post_match/
│   │   └── ...
│   └── game/                            # Flame component tests
│       ├── board_layer_test.dart
│       ├── animation_sequencer_test.dart
│       └── ...
├── pubspec.yaml                         # Dependencies
└── analysis_options.yaml                # Lint rules
```

### Dependencies (pubspec.yaml)

```yaml
dependencies:
  flutter:
    sdk: flutter
  flame: ^1.22.0                    # 2D game engine
  flutter_soloud: ^3.0.0            # SoLoud audio engine (SFX, music, filters)
  provider: ^6.1.0                  # DI / state management
  http: ^1.2.0                      # HTTP client for API
  flutter_secure_storage: ^9.2.0    # JWT token storage (Keychain on iOS)
  go_router: ^14.0.0                # Declarative navigation
  in_app_purchase: ^3.2.0           # StoreKit for $1 ad-free
  google_mobile_ads: ^5.2.0         # AdMob (interstitial + rewarded)

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^5.0.0
  mocktail: ^1.0.0                  # Mock generation for tests
```

**Design principle:** Minimize external dependencies. Flutter's framework covers most needs. Only four external packages are mandatory: Flame (game engine), flutter_soloud (audio), flutter_secure_storage (token storage), and the ad SDK.

### File Ownership

| Role | Write Scope |
|------|------------|
| Orchestrator | `STATE.md`, `docs/`, `README.md` |
| Backend Integration Agent | `lib/models/backend_contract.dart`, `lib/services/api_client.dart` |
| Board Rendering Coder | `lib/game/board_layer.dart`, `lib/game/gem_component.dart`, `lib/game/gem_shader_library.dart`, `shaders/` |
| Animation Coder | `lib/game/animation_sequencer.dart`, `lib/game/cascade_animator.dart`, `lib/game/particle_layer.dart` |
| Audio Coder | `lib/audio/`, `lib/services/audio_engine.dart`, `assets/audio/` |
| Haptics Coder | `lib/haptics/`, `lib/services/haptics_engine.dart`, `ios/Runner/HapticsChannel.swift` |
| Scene Coder | `lib/game/chroma_crush_game.dart` (integration of Board + Animation + Particles) |
| Shell Coder | `lib/widgets/shell/`, `lib/widgets/game/` |
| PostMatch Coder | `lib/widgets/post_match/` |
| Vault Coder | `lib/widgets/vault/`, card visuals, artifact-to-card UI |
| Card Equip Coder | `lib/widgets/cards/` (`card_equip_screen.dart`, equip slots, loadout UI) |
| Modifier Coder | `lib/game/modifier_layer.dart` (in-match proc overlays, slot icon pulse, activation VFX) |
| Social Coder | `lib/widgets/social/` |
| Store Coder | `lib/widgets/store/` |
| ViewModel Coder | `lib/view_models/` |
| Miner Coder | `lib/game/miner/` (Gem Miner mode renderer, gameplay, dirt grid — Phase 7) |
| Testing Agent | `test/` |

---

## Phase 0 — Backend Survey & Project Scaffold

**Gate:** Human directs frontend work to begin.
**Exit:** `backend_contract.dart` generated. `flutter test` passes. `flutter run -d chrome` shows empty shell. Human approves.

### Step 0.1 — Backend Survey

Agent reads backend architecture docs (`docs/architecture/architecture.md` + per-module reports) and backend source code to extract:
- All API endpoint signatures (method, path, request body, response body).
- Board state JSON schema (8x8 grid encoding, gem type enums, special gem metadata).
- Move submission format and response event types.
- Authentication flow (JWT creation, token refresh, API key for bots).
- All Dart data class shapes needed by the frontend.

### Step 0.2 — BackendContract Generation

Produce `lib/models/backend_contract.dart`:
- All Dart data classes matching backend JSON schemas (`fromJson` / `toJson`).
- Endpoint enum with associated request/response types.
- Documentation comments mapping each field to gameplay meaning.

### Step 0.3 — Project Scaffold

- `flutter create chromacrush_app` with iOS target.
- `pubspec.yaml` with all dependencies listed above.
- Directory structure per Shared Infrastructure.
- Service abstract interfaces (stubs, not implementations).
- `config.dart` with API base URL.
- `main.dart` wiring services into `MultiProvider`.
- `analysis_options.yaml` with strict lint rules.

### Step 0.4 — Scaffold Verification

- `flutter analyze` — zero errors, zero warnings.
- `flutter test` — scaffold tests pass.
- `flutter run -d chrome` — empty navigation shell renders (if web target available).
- BackendContract types compile.

**Human reviews and approves. Phase 0 ends.**

---

## Phase 1 — Playable Core

**Gate:** Human approved Phase 0.
**Exit:** Human can play a full match through the API with basic animation. Colored circles, no juice.

### Step 1.1 — ApiClient Implementation

Functional ApiClient covering:
- Auth (create account, anonymous login, token storage via flutter_secure_storage).
- Match endpoints (new match, submit move, get state, get result).
- Energy endpoints (get state, consume).
- Error handling (network, server, auth errors → `AppError`).
- Response deserialization into BackendContract types.
- Unit tests with mocked HTTP responses.

### Step 1.2 — Board Rendering (Basic)

8x8 grid of colored circles (no shaders yet):
- `GemComponent` as Flame `CircleComponent` (colored circle, 44x44 logical pixels).
- Grid positioning (centered, 2px spacing).
- Gem color mapping from backend gem type.
- Proper rendering order per design skeleton Section 2.1.

### Step 1.3 — Gesture Handling + Move Submission

- Tap-to-select, drag-to-swap, tap-adjacent-to-swap via Flame's gesture detection.
- Optimistic swap animation (150ms `MoveEffect`).
- `ApiClient.submitMove()` on gesture commit.
- Invalid swap rubber-band (150ms reverse `MoveEffect`).

### Step 1.4 — Animation Pipeline (Basic)

AnimationSequencer handling backend event array:
- Swap animation (`MoveEffect`).
- Match removal (fade/shrink via `ScaleEffect` + `OpacityEffect`).
- Gem fall (linear `MoveEffect`, no bounce yet).
- Cascade chaining (sequential: match → fall → match via `SequenceEffect`).
- Board state sync after animation completes (visual sync invariant).

### Step 1.5 — Game Shell

- `GameContainer` widget (Flame `GameWidget` + Flutter HUD overlay via `Stack`).
- Score display (animated on change).
- Moves remaining counter.
- Basic end-of-match screen (win/loss text, play again button).
- SessionManager tracking match state.
- EventBus wiring game scene → Flutter HUD.

### Step 1.6 — Phase 1 Verification

- Full match playable: matchmaking → board → swaps → cascades → end screen.
- All moves validated by server.
- Visual board matches server state after every animation.
- `flutter test` — all tests pass (ApiClient mocks, component tests, widget tests).

**Human reviews and approves. Phase 1 ends.**

---

## Phase 2 — Juice Pass

**Gate:** Human approved Phase 1.
**Exit:** Game feels good. Matches pop, cascades escalate, fusions feel incredible.

### Step 2.1 — Procedural Gem Shaders

Per design skeleton Section 5:
- GLSL fragment shaders via Flutter's `FragmentProgram` API.
- SDF shapes (circle, diamond, hexagon, rounded square, triangle, pentagon).
- Shader uniforms (time, pulse_rate, pulse_amp, brightness, glow_radius, color, selected, special).
- Visual layers: outer glow → shape fill → inner highlight → specular edge → selection ring → special overlay.
- Special gem variants: Line Blast arrows, Radial Bomb rings, Chromatic Orb rainbow.

### Step 2.2 — Particle System

Per design skeleton Section 4.1:
- Flame `ParticleSystemComponent` for all effects.
- Particle effects: MatchBurst, CascadeBurst, LineSweep, RadialWave, ChromaticRain, FusionStorm, VictoryConfetti, NearMissSparkle, GemTrail, DefeatDust.
- ParticleLayer managing emitter lifecycle.
- Runtime parameter adjustment (chain length, gem color).
- Performance budget: 500 active particles max.

### Step 2.3 — Animation Upgrade

- Elastic bounce on gem falls (overshoot 15% + 2 diminishing bounces, 80ms per row) via custom `EffectController`.
- Gem trail particles on fall.
- Screen shake on special activation (custom `MoveEffect` on camera/world).
- Slow-motion on fusion (game `timeScale` 0.3 → 1.0).
- Screen flash on chain threshold (overlay component, opacity pulse).
- Zoom pulse on fusion (`ScaleEffect` on board: 1.0→1.03→1.0).
- Full fusion jackpot sequence (design skeleton Section 4.2).

### Step 2.4 — Audio Engine (flutter_soloud)

Per design skeleton Section 8:
- SoLoud engine initialization and asset preloading.
- SFX: gem select, swap, invalid swap, match chime, cascade ascending scale (pitch shift per chain step), special activation, fusion fanfare, victory/defeat stings.
- Sound pooling via SoLoud multi-voice playback.
- SoLoud filters for real-time EQ and effects.
- Audio settings (SFX 80%, Music 40%, master mute) persisted via shared_preferences.

### Step 2.5 — Haptics Engine (Platform Channel)

Per design skeleton Section 4.3:
- `MethodChannel` to Swift Core Haptics on iOS.
- `ios/Runner/HapticsChannel.swift` implementing AHAP pattern playback.
- Dart-side pattern definitions sent as structured data to iOS.
- Escalating intensity per chain step (cap at 1.0).
- Fusion combo multi-phase pattern.
- `StubHapticsEngine` for Windows development (no-op, tests pass).

### Step 2.6 — Phase 2 Verification

- Cascade chain feels compelling (audio + visual + haptic escalation).
- Fusion combo is a showstopper moment.
- Frame rate stable at 60fps.
- Particle budget respected.
- All animation timings within 20% of design skeleton specs.
- `flutter test` — all tests pass.

**Human reviews and approves. Phase 2 ends.**

---

## Phase 3 — Psychology Layer

**Gate:** Human approved Phase 2.
**Exit:** Post-match screens drive "one more match." Intensity system makes tense moments tense.

### Step 3.1 — Intensity System

Per design skeleton Section 4.4:
- Global intensity value (0.0–1.0) computed from: moves remaining, score differential, recent cascade length, board state hints.
- Outputs driving: gem pulse rate/amplitude (shader uniforms), ambient particles, board vignette (shader), background music tempo/filter (SoLoud), ambient hum volume.

### Step 3.2 — Navigation Shell (Full)

Per design skeleton Section 3:
- MainMenu: play button (energy-gated), energy display with regen timer, daily streak badge, vault preview, revenge indicator, bot opponent teaser, ad-free banner.
- MatchmakingScreen: search animation (2s artificial floor), opponent card reveal, board drop-in.
- Settings: audio, haptics, account.
- GoRouter navigation with proper route definitions.

### Step 3.3 — Post-Match Screens

Per design skeleton Section 7:
- Win screen: 4-phase sequence (victory declaration → score celebration → vault raid animation → action buttons).
- Loss screen: 4-phase sequence (defeat declaration → near-miss messaging → vault raided → revenge prompt).
- Near-miss messaging (score differential, cascade tease, board state hint).
- Play-again flow: direct to matchmaking, no return to menu.

### Step 3.4 — Adaptive Music

Per design skeleton Section 8.4:
- Background music loop via flutter_soloud.
- Playback speed adjustment for tempo scaling (100%–130% based on intensity).
- SoLoud filter chain for EQ sweeps (bass removal at high intensity).
- Percussion layer crossfade at high intensity (second audio source, volume ramp).

### Step 3.5 — Phase 3 Verification

- Post-match flow feels complete and compelling.
- Near-miss messaging appears on flagged losses.
- Intensity system visibly affects ambiance during gameplay.
- Play-again minimizes friction (1 tap from end screen to next match).
- `flutter test` — all tests pass.

**Human reviews and approves. Phase 3 ends.**

---

## Phase 4 — Card System & Loss Aversion

**Gate:** Human approved Phase 3 (+ Schema-Driven Refactor complete).
**Exit:** Card meta-game functional. Players equip cards, modifiers proc during play, raids steal cards, vault feels like an arsenal.

> **Phase 4: COMPLETE.** 4A (backend card foundation), 4B (frontend card integration), 4D (mega gem activation + board shuffle) all implemented. 4C (card effects/modifier hooks) **DEFERRED** for collaborative design with the human. Remaining directional items (raids, opponent preview, energy UI) are future enhancements.
>
> **Detailed plans:** Card and mega plans were kept outside the repo during design.

### Step 4A — Backend Card Foundation (COMPLETE)

Card definitions and player card instances:
- `config/card_definitions.json` — static catalog (12 cards, 3 sets, 4 rarities). JSON-only, no DB table for definitions.
- `player_cards` DB table — UUID PK, player_id FK, sequential integer card_id, positional equip ordering (1-3 = equipped, 4+ = vault), level, source, acquired_at.
- `CardService` — get/list definitions, grant/equip/unequip/reorder/remove/merge cards.
- Merge logic: consume 3 same-rarity equipped cards → 1 random card of next rarity tier. Legendary cannot be merged.
- 8 REST endpoints under `/api/v1/cards/` (GET definitions, mine, equipped; POST equip, unequip, reorder, merge).
- Rarity tiers: Common, Rare, Epic, Legendary (4 tiers, not 6 — simplified from original plan).
- No `trigger`/`effect` fields yet — reserved for Phase 4C.

### Step 4B — Frontend Card Integration (COMPLETE)

Vault screen and card visuals:
- Backend contract DTOs: `CardDefinitionResponse`, `PlayerCardResponse`, `EquippedLoadoutResponse`, `PlayerCardsResponse`, `MergeResultResponse`, `CardEquipRequest`, `CardUnequipRequest`, `CardReorderRequest`.
- API client: 6 card methods in `ApiClientBase` + `HttpApiClient`.
- `SessionManager` gains `ownedCards` and `equippedLoadout` state.
- **Vault screen** (`vault_screen.dart`): 3 equip slots at top (drag-down-to-unequip with visual feedback), merge button (enabled when 3 same-rarity equipped, disabled for legendary), horizontal card carousel (PageView with mouse/touch/trackpad `ScrollConfiguration`), drag-up-to-equip gesture with transform/opacity/arrow feedback and animated snap-back.
- **Card widget** (`card_widget.dart`): glassmorphism panels with rarity-colored border glow, card name/description/rarity badge/level/set/value. Holographic foil shader overlay for epic (0.45 intensity) and legendary (0.85 intensity). Legendary gets extra outer glow.
- **Foil shader** (`shaders/foil.frag`): GLSL diagonal rainbow sweep + specular highlight band + Fresnel edges. Animated via time uniform. Fallback gradient for shader-less environments.
- Route `/vault` registered in `app_router.dart`. CARD VAULT button on main menu.
- 11 card DTO unit tests. 129 total tests passing.

### Step 4C — Dynamic Modifiers / Card Effects (DEFERRED)

**Requires collaborative design with human.** Once 4A+4B exist, discuss:
- What individual cards do (triggers, effects, conditions).
- How modifiers hook into `CascadeContext` / `_run_cascade_step_inplace`.
- `applied_modifiers` field on `MoveProcessingResult`.
- Frontend proc overlays and animations.
- Balance/power-budget system.

The foundation from 4A/4B supports this — `CardDefinition` has `tags` for filtering, `level` for scaling, and `EquippedLoadout` is available to pass into `process_move`.

### Step 4D — Mega Gem Activation + Board Shuffle (COMPLETE)

Tap-to-activate mega gems from persistent inventory:
- **Inventory:** `mega_gem_inventory` table with 5 slots per player. Slot 0-3 = mega gem types (values 14/24/34/44), Slot 4 = shuffle (value -1). `InventoryService` with get/consume/grant. `GET /api/v1/inventory/mega` endpoint.
- **Activation:** `POST /api/v1/matches/{match_id}/mega` with `{slot_index, timestamp_ms, source?}`. Slots 0-3 trigger full cascade pipeline (place mega at random non-special cell, fire effect, cascade, gravity, fill). Slot 4 calls `shuffle_board`. All slots consume 1 from inventory.
- **Move refund:** Mega activation increments `moves_made` (for unique move_number tracking) but does NOT decrement `moves_remaining`. The move is "free" — megas feel like bonus power.
- **Frontend:** `PlayerStatusBar` has 5 mega slots with tap callbacks and dim-when-empty. `ChromaCrushGame._onMegaActivated()` handles full flow: API call → cascade animation → board sync → score update → inventory refresh. `finally` block ensures input handler always unblocked.
- **Shuffle:** Same activation pattern as megas. Void Instability card is net-zero (`source="void_instability"` flag skips inventory check — card grants + consumes atomically).

### Step 4.4 — Card UI & Visuals (PARTIALLY COMPLETE)

- [x] Glassmorphism vault UI with glass panels and rarity-colored borders.
- [x] Rarity escalation: plain glass (common/rare) → foil shader overlay (epic) → full foil + outer glow (legendary).
- [ ] `EffectIconPainter` + particle triggers for in-match proc overlays (Phase 4C).
- [ ] Slot icons pulse on proc, activation particles/SFX (Phase 4C).

### Step 4.5 — Merge & Progression (PARTIALLY COMPLETE)

- [x] Merge: consume 3 same-rarity equipped cards → 1 random card of next rarity tier.
- [ ] Visual evolution on upgrade (post-merge animation).
- [ ] Power-budget validation for designers (Phase 4C).

### Step 4.6 — Raid Evolution

Loss aversion 2.0 — cards make raids personal:
- Winner steals 1 random equipped card (priority: unequipped last).
- If shielded: just unequips it (forces re-equip next match).
- Raid notification: "Your Fusion Amp was raided by OptiBot-7741! Revenge now?" + red trail animation.
- 50% chance reclaim on revenge win.
- Shield system: watch ad → protect card, shield duration countdown.

### Step 4.7 — Pre-Match Opponent Preview

- Show opponent's equipped cards before match starts.
- Bot opponent cards visible (mind games).
- Integrates with matchmaking screen flow.

### Step 4.8 — Energy UI

- Heart display with filled/empty icons.
- Regeneration timer countdown.
- Rewarded ad → heart refill flow (ad SDK integration point).

### Step 4.9 — Phase 4 Verification

- Card equip flow works end-to-end (vault → equip → match → proc → post-match).
- Modifier procs confirmed server-side, frontend renders correctly.
- Raid animations target equipped cards.
- Merge/upgrade functional with visual evolution.
- Energy display accurate, regen timer counts down.
- `flutter test` — all tests pass.

**Human reviews and approves. Phase 4 ends.**

---

## Phase 5 — Monetization & Polish

**Gate:** Human approved Phase 4.
**Exit:** Revenue mechanics live. Card economy monetized. Social features create competitive context.

### Step 5.1 — Ad Integration (DEFERRED)

- google_mobile_ads SDK integration (interstitial + rewarded + banner).
- Interstitial frequency (every 3rd match).
- Rewarded ads for hearts, shields, and card slot unlocks.
- Ad-free detection suppresses all ad surfaces.

### Step 5.2 — In-App Purchase (COMPLETE)

- in_app_purchase package for $1 ad-free purchase (StoreKit on iOS).
- Purchase validation via backend payments endpoint.
- Ad-free unlocks premium 6th card slot.

### Step 5.3 — Card Economy Monetization (COMPLETE)

> Gold currency + barter marketplace implemented. Economy module with `gold_balances` table. Players sell equipped cards for gold (40% of `base_value`), buy mega specials and card packs in the barter marketplace. 5 arsenal items (mega chromatic combos) + 4 forge supply items (card packs by rarity). Confirmation dialogs on destructive actions. Remaining items below are future enhancements.

- ~~Card packs (random cards by rarity tier).~~ **DONE** — available in barter marketplace (forge supply section).
- Daily shop (rotating card selection).
- Merge boosters (increase upgrade success chance).
- 4th–5th equip slot unlock via progression milestones or rewarded ads.

### Step 5.4 — Social Screens (COMPLETE)

- LeaderboardScreen (weekly/all-time, filterable).
- StatsScreen (ELO graph, cascade stats, match history).
- Daily streak counter + reward track display.

### Step 5.5 — Near-Miss Polish

- Board sparkle on positions that almost matched.
- Idle board tease (potential matches flicker subtly after inactivity).

### Step 5.6 — Phase 5 Verification

- Purchase flow completes end-to-end.
- Ads display and reward correctly.
- Card economy items purchasable and functional.
- Leaderboard and stats populate from backend.
- `flutter test` — all tests pass.

**Human reviews and approves. Phase 5 ends.**

---

## Phase 6 — LiveOps

**Gate:** Human approved Phase 5.
**Exit:** Ongoing — events, A/B testing, performance tuning, card balance.

- Flash event banner + event-specific UI.
- Event-specific artifacts and event-themed card drops.
- Card balance patches via server-side config (adjust proc rates, cooldowns, power budgets without app update).
- A/B testing infrastructure for psychology parameters and card balance tuning.
- Performance optimization pass (Flutter DevTools profiling).
- Accessibility audit (Semantics widgets, Dynamic Type, color blind modes).

---

## Phase 7 — Gem Miner Mode

**Gate:** Human approved Phase 6 (or human directs earlier start).
**Exit:** Gem Miner mode playable. Cross-mode resource sharing functional.

> **Planning note:** This phase will be planned in detail with the human when reached. The steps below are directional. The roadmap (`roadmap_new_features.md`) contains Gem Miner ideas, dirt mask code examples, and optimization notes. Detailed design, step breakdown, agent assignments, and schema definitions will be defined collaboratively.

### Step 7.1 — Gem Miner Design & Schema

- Game mode schema definition in JSON (extends the schema-driven architecture).
- Vein types: heart, artifact, rock, ladder, mystery — each with durability, reward, and visual config.
- Monster spawning rules (30–60s intervals, steal hearts or damage unless paid off).
- Dust currency and upgrade definitions.

### Step 7.2 — Grid Augmentation

- 16-bit dirt mask per cell for 4×4 subsampling (virtual 32×32 grid over logical 8×8).
- `Cell.dirt_mask` — bit k = dirt at `sub_y*4 + sub_x`, `0xFFFF` = full dirt, `0x0000` = cleared.
- Virtual → logical coordinate mapping (`fine_x // 4`, `fine_y // 4`).
- Match-3 code unaffected — only reads existing `gem_type`/`animation_state` fields.

### Step 7.3 — Miner Renderer

- `ProceduralGridRenderer` reading cell definitions from schema.
- Dirt shader (SDF erosion based on durability / revealed state).
- Static dirt optimization: bake unchanging cells into a single `Picture` at level load.
- Batch rendering for similar dirt cells (SpriteBatch / Canvas.drawAtlas).
- Culling: only render visible cells ±1 margin around screen.

### Step 7.4 — Miner Gameplay

- Click-to-mine interaction (tap dirt cells to reveal veins).
- Passive heart generation (1 heart / 10s, upgradable with dust).
- Dust currency from mining — used for upgrades.
- Monster encounters: spawn periodically, steal hearts or damage unless dealt with.
- Ladder / depth progression.

### Step 7.5 — Cross-Mode Resources

- Hearts shared with Match-3 (consumed by both modes, max 5).
- Artifact drops from mining feed the vault/card system.
- Dust earned in Miner, spent on Miner upgrades.
- Schema collision flags: `none | solid | pickup | deadly` for entity interaction.

### Step 7.6 — Phase 7 Verification

- Gem Miner mode playable end-to-end.
- Dirt rendering performant (60fps with full 32×32 virtual grid).
- Cross-mode resources sync correctly (mine a heart → see it in Match-3 energy).
- `flutter test` — all tests pass.

**Human reviews and approves. Phase 7 ends.**

---

## Artifact & Documentation Standards

All artifacts follow Appendix A template.

- Markdown format.
- Header: title, author agent, date, version, status (draft/final).
- Consistent heading levels.
- Dart code blocks with `dart` language identifier.
- Decisions include brief rationale.
- Open questions flagged with `> **OPEN QUESTION:**`.

---

## Dispute Resolution Protocol

### Level 1 — Agent Resolution
Coding agent and relevant mandatory agent discuss. If implementation was intentional and justified, design skeleton interpretation is documented. If in error, coder corrects.

### Level 2 — Orchestrator Escalation
If Level 1 doesn't resolve: Orchestrator evaluates, makes binding decision, assigns corrective work.

### Level 3 — Human Escalation
Fundamental design or UX issue beyond Orchestrator's scope. Escalated with: problem, options, recommendation, impact.

---

## Version Control Workflow

### Branching Strategy

- **`main`** — Backend v1.0.0. Receives frontend merges at phase gates after human approval.
- **`develop`** — Working branch. All frontend agent work here.

### Commit Conventions

```
[phase].[step] [role]: [concise description]
```

Examples:
```
0.2 scout: backend_contract.dart generated from backend survey
1.2 coder: board_layer 8x8 grid rendering with colored circles
2.1 coder: Procedural gem shaders — 6 SDF shapes with glow (GLSL)
2.4 coder: AudioEngine flutter_soloud + cascade ascending scale SFX
3.3 coder: PostMatch win/loss screens with raid animation
```

### Phase Gate Checkpoints

1. All work on `develop` committed.
2. `flutter analyze` — zero errors.
3. `flutter test` — all tests pass.
4. STATE.md fully current.
5. `develop` merged to `main`.
6. Tagged: `v2.0` (Phase 0), `v2.1` (Phase 1), `v2.2` (Phase 2), etc.
7. Human reviews.

---

## Cold-Start Recovery Protocol

Same as backend framework. STATE.md is the project root truth file.

### Recovery Procedure

1. **Read STATE.md.** Session Log → what was happening. Phase Checklist → what's done. Key Decisions → what's settled.
2. **Identify position.** First unchecked item = where to resume.
3. **Check for crash damage.** Interrupted work → check files touched against repo state.
4. **Read design skeleton section** relevant to current phase.
5. **Announce recovery.** Tell human. Summarize position and intent. Wait for confirmation.
6. **Resume.**

---

## Appendix A — Component Artifact Template

```markdown
# Component Artifact: [Component Name]

## Header
- **Author:** [Agent ID]
- **Date:** [Date]
- **Version:** [Version]
- **Design Skeleton Reference:** Section [X.Y]

## Purpose
[One paragraph: what this component does.]

## Inputs
[Data it receives: types, sources (backend response, user gesture, EventBus, etc.)]

## Outputs
[What it produces: rendered visuals, events published, state changes.]

## Service Dependencies
[Which injected services it uses and why.]

## Design Skeleton Compliance
[How it maps to the design skeleton spec. Any deviations with justification.]

## Implementation Notes
[Internal design decisions, performance considerations, edge cases.]

## Test Plan
[How this component is tested: unit, widget, game component test.]
```

---

## Appendix B — Glossary

- **AnimationSequencer:** Flame component translating backend event arrays into chained `Effect` sequences.
- **backend_contract.dart:** Generated file containing all Dart data classes matching backend API schemas.
- **BoardLayer:** Flame `PositionComponent` managing the 8x8 gem grid rendering and swap gesture handling.
- **Design Skeleton:** `ChromaCrush_iOS_Frontend_Design_Skeleton.md` — the authoritative design document for the frontend.
- **EventBus:** Dart `StreamController.broadcast()`-based pub/sub decoupling Flame from Flutter widgets.
- **Flame:** 2D game engine for Flutter. Provides game loop, component tree, effects, particles, and rendering.
- **flutter_soloud:** Dart binding to the SoLoud C++ audio engine. Provides low-latency sound, multi-voice, filters, faders.
- **FragmentProgram:** Flutter API for loading and running GLSL fragment shaders on the GPU.
- **Fusion Jackpot:** Multi-phase animation sequence when two special gems combine (design skeleton Section 4.2).
- **GemComponent:** Flame `PositionComponent` subclass for individual gem rendering with fragment shader.
- **Intensity System:** Global 0.0–1.0 value driven by game state, scaling visual/audio/haptic ambiance.
- **Near-Miss:** Backend-flagged close loss triggering specific post-match messaging (design skeleton Section 7.2).
- **Optimistic Swap:** Client plays swap animation immediately while awaiting server response, rubber-bands on rejection.
- **ParticleLayer:** Flame component managing all transient particle emitters with performance budget.
- **Platform Channel:** Flutter mechanism for calling native iOS (Swift) code from Dart. Used for Core Haptics.
- **SDF:** Signed Distance Field — shader technique for resolution-independent gem shape rendering.
- **Visual Sync Invariant:** After any animation completes, visual board must exactly match server `board_state`.
- **Card:** A gameplay modifier derived from a vault artifact. Has rarity, trigger condition, and server-authoritative effect. Equipped pre-match, procs dynamically during play.
- **Dirt Mask:** 16-bit bitmask per cell representing 4×4 subsampled dirt state for Gem Miner mode. `0xFFFF` = full dirt, `0x0000` = cleared.
- **Dynamic Modifier:** A card effect that activates on a game trigger (match/cascade/fusion). Server computes, frontend renders.
- **Equip Slot:** Pre-match slot for a card. Start with 3, unlock up to 5–6 via progression/ads.
- **Loadout:** A saved configuration of equipped cards. Named presets like "Cascade Grind" or "Anti-Bot Aggro."
- **Proc:** When a card's trigger condition is met and its effect activates during gameplay. Short for "programmed random occurrence."
- **ProceduralGridRenderer:** Flame component that reads cell definitions from JSON schema and renders shapes/shaders at grid coordinates. Used for Gem Miner mode.
- **Vein:** A minable resource deposit in Gem Miner mode (heart, artifact, rock, ladder, mystery).

---

## Appendix C — Future Vision (Benched)

Features documented for future reference. Not assigned to phases. Will be evaluated after core modes are stable.

### Flappy Gem Mode
- Horizontal scrolling reflex game using the same 8×8 grid + 4× subsampling architecture.
- Player entity navigates procedural columns, collecting gems and avoiding obstacles.
- Specials earned in Match-3 become projectiles: LINE_BLAST → horizontal/vertical laser, RADIAL_BOMB → 3×3 clear, CHROMATIC_ORB → invincibility.
- 20 progressive levels. Every 5 levels refunds entry heart.
- Procedural generation from JSON schema (column spacing, obstacle types, collectible density).

### Cross-Game Resource Loop
When multiple modes exist, shared resources create a meta-game loop:
- **Hearts:** Max 5, consumed by Match-3 and Flappy. Regenerated passively in Gem Miner (1/10s, upgradable).
- **Special Bank:** Specials earned in Match-3, spent as projectiles in Flappy.
- **Artifact Vault:** Drops from all modes feed the card system.
- **Dust:** Earned in Gem Miner, spent on Miner upgrades.

### Match-3 Specials → Flappy Projectile Mapping
| Match-3 Special | Flappy Projectile |
|----------------|-------------------|
| LINE_BLAST_H/V | Horizontal/vertical laser |
| RADIAL_BOMB | 3×3 area clear |
| CHROMATIC_ORB | Temporary invincibility |
