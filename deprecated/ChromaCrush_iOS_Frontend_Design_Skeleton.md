# ChromaCrush iOS Frontend — Design Skeleton & Implementation Guide

**Version:** 1.0 — February 2026  
**Platform:** iOS (iPhone + iPad, iOS 17+)  
**Architecture:** Decoupled client — all game logic is server-authoritative  
**Rendering:** SpriteKit (game board) + SwiftUI (shell/UI)  
**Target:** Agentic-driven codebase generation from this specification

---

## 0. Pre-Implementation: Backend Survey Directive

> **AGENT INSTRUCTION:** Before writing any frontend code, the implementing agent MUST:
>
> 1. **Locate and read the backend architecture document** (provided separately or in the project repo). This contains all API endpoint specifications, request/response schemas, board state formats, and authentication flows.
> 2. **Survey the backend codebase** to extract:
>    - All API endpoint signatures (method, path, request body, response body)
>    - The exact JSON schema for board state representation (8×8 grid encoding, gem type enums, special gem metadata)
>    - The move submission format (coordinates, validation response, cascade event stream)
>    - Authentication flow (account creation, session tokens, guest/anonymous play for first 3 matches)
>    - WebSocket or polling strategy for asynchronous match state updates
>    - Vault/artifact data model (artifact IDs, names, rarity, visual metadata)
>    - Player stats schema (ELO, win rate, cascade stats, match history)
>    - Energy system state (hearts remaining, regen timestamps)
>    - Event system schema (flash events, daily streaks, revenge timers)
> 3. **Generate a `BackendContract.swift` file** containing:
>    - All Codable structs matching backend JSON schemas
>    - An enum of all API endpoints with associated request/response types
>    - Documentation comments mapping each struct field to its gameplay meaning
> 4. **Only then proceed** with the implementation phases below.
>
> The frontend makes ZERO game logic decisions. It sends moves, receives results, and renders spectacle. The backend is the source of truth for: board state, legal moves, match detection, cascade resolution, scoring, special gem creation, matchmaking, vault contents, and all randomness.

---

## 1. Architecture & Project Structure

### 1.1 Layer Diagram

```
┌──────────────────────────────────────────────┐
│  ChromaCrushApp (SwiftUI App entry point)     │
│  ┌────────────────────────────────────────┐   │
│  │  NavigationShell (SwiftUI)             │   │
│  │  - MainMenuView                        │   │
│  │  - MatchmakingView                     │   │
│  │  - VaultView                           │   │
│  │  - StatsView                           │   │
│  │  - LeaderboardView                     │   │
│  │  - SettingsView                        │   │
│  │  - PostMatchView                       │   │
│  │  ┌──────────────────────────────────┐  │   │
│  │  │  GameContainerView (SwiftUI)     │  │   │
│  │  │  ┌────────────────────────────┐  │  │   │
│  │  │  │  GameScene (SKScene)       │  │  │   │
│  │  │  │  - BoardLayer (SKNode)     │  │  │   │
│  │  │  │  - ParticleLayer (SKNode)  │  │  │   │
│  │  │  │  - HUDLayer (SKNode)       │  │  │   │
│  │  │  └────────────────────────────┘  │  │   │
│  │  │  Embedded via SpriteView         │  │   │
│  │  └──────────────────────────────────┘  │   │
│  └────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────┐   │
│  │  Services Layer                        │   │
│  │  - APIClient (async/await + Codable)   │   │
│  │  - AudioEngine (AVAudioEngine)         │   │
│  │  - HapticsEngine (Core Haptics)        │   │
│  │  - SessionManager (auth, energy state) │   │
│  │  - EventBus (Combine publishers)       │   │
│  └────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────┐   │
│  │  Models (Codable structs)              │   │
│  │  - BackendContract.swift (generated)   │   │
│  │  - ViewModels (ObservableObject)       │   │
│  └────────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

### 1.2 Xcode Project Structure

```
ChromaCrush/
├── ChromaCrushApp.swift                    # @main entry point
├── Models/
│   ├── BackendContract.swift               # GENERATED from backend survey — all API types
│   ├── GemType.swift                       # Local enum mapping backend gem IDs → visual properties
│   ├── MatchEvent.swift                    # Cascade/match/special events from backend
│   └── ViewState.swift                     # UI state enums (loading, playing, postMatch, etc.)
├── Services/
│   ├── APIClient.swift                     # All backend communication
│   ├── AudioEngine.swift                   # Sound system (AVAudioEngine + procedural synthesis)
│   ├── HapticsEngine.swift                 # Core Haptics patterns
│   ├── SessionManager.swift                # Auth, energy, streaks, timers
│   └── EventBus.swift                      # Combine-based pub/sub for cross-layer communication
├── Views/
│   ├── Shell/
│   │   ├── NavigationShell.swift           # Root navigation (tab or stack based)
│   │   ├── MainMenuView.swift              # Play button, daily streak, energy display
│   │   ├── MatchmakingView.swift           # Searching for opponent animation
│   │   └── SettingsView.swift              # Audio, haptics, dark mode, account
│   ├── Game/
│   │   ├── GameContainerView.swift         # SwiftUI wrapper for SpriteView + HUD overlay
│   │   └── GameHUDOverlay.swift            # Score, moves remaining, opponent info (SwiftUI over SpriteKit)
│   ├── PostMatch/
│   │   ├── PostMatchView.swift             # Win/loss orchestration
│   │   ├── VaultRaidAnimation.swift        # Artifact stolen/gained sequence
│   │   ├── NearMissView.swift              # "One cascade away" messaging
│   │   └── RevengePromptView.swift         # 2-hour timer, rematch button
│   ├── Vault/
│   │   ├── VaultView.swift                 # Collection grid display
│   │   ├── ArtifactDetailView.swift        # Individual artifact showcase
│   │   └── ArtifactShieldView.swift        # Shield status, ad-to-protect flow
│   ├── Social/
│   │   ├── LeaderboardView.swift           # Weekly/all-time, human-only vs mixed
│   │   └── StatsView.swift                 # ELO graph, cascade stats, match history
│   └── Store/
│       ├── AdFreeUpgradeView.swift         # $1 purchase flow
│       └── EnergyRefillView.swift          # Rewarded ad → heart flow
├── Game/
│   ├── GameScene.swift                     # Main SKScene — board rendering + animation orchestration
│   ├── BoardLayer.swift                    # 8×8 gem grid rendering + swap gesture handling
│   ├── ParticleLayer.swift                 # All particle emitters (match bursts, cascades, fusions)
│   ├── GemNode.swift                       # Individual gem sprite + shader + pulse animation
│   ├── GemShaderLibrary.swift              # Fragment shaders for procedural gem rendering
│   ├── AnimationSequencer.swift            # Chains backend events → visual animation sequences
│   └── CascadeAnimator.swift              # Specifically handles multi-step cascade visual flow
├── Shaders/
│   ├── gem_base.fsh                        # Base gem shape + color + glow
│   ├── gem_pulse.fsh                       # Heartbeat pulse overlay
│   ├── gem_special_line.fsh                # Line Blast visual
│   ├── gem_special_bomb.fsh                # Radial Bomb visual
│   ├── gem_special_chromatic.fsh           # Chromatic Orb visual (rainbow cycle)
│   └── board_vignette.fsh                  # Board edge glow that reacts to chain length
├── Audio/
│   ├── SoundBank.swift                     # Enum of all sound events → synthesis parameters
│   └── MusicEngine.swift                   # Adaptive background music (tempo/intensity scaling)
├── Haptics/
│   └── HapticPatterns.swift                # Pre-built AHAP patterns for match/cascade/fusion/loss
├── Resources/
│   ├── Particles/
│   │   ├── MatchBurst.sks                  # Basic match particle emitter
│   │   ├── CascadeTrail.sks                # Falling gem trail particles
│   │   ├── FusionExplosion.sks             # Over-the-top fusion particle system
│   │   ├── VictoryConfetti.sks             # Post-match win confetti
│   │   └── NearMissSparkle.sks            # Subtle tease sparkle on potential matches
│   └── Fonts/
│       └── (system fonts — no custom fonts needed initially)
└── Extensions/
    ├── SKAction+ChromaCrush.swift          # Custom easing curves, shake, zoom, slow-mo
    ├── Color+Gems.swift                    # Gem color palette definitions (normal + dark mode)
    └── CGPoint+Grid.swift                  # Grid coordinate ↔ screen position math
```

### 1.3 Dependency Management (Swift Package Manager)

| Dependency | Purpose | Required? |
|------------|---------|-----------|
| None (SpriteKit) | Game rendering | Built-in |
| None (SwiftUI) | UI shell | Built-in |
| None (AVFoundation) | Audio | Built-in |
| None (CoreHaptics) | Haptics | Built-in |
| None (Combine) | Event bus / reactive bindings | Built-in |
| StoreKit 2 | $1 ad-free purchase | Built-in |
| AdMob SDK (Google) | Interstitial + rewarded + banner ads | Yes — add via SPM |
| KeychainAccess (kishikawakatsumi) | Secure token storage | Optional — can use raw Keychain API |

**Design principle: Minimize external dependencies.** Apple's frameworks cover nearly everything. The only mandatory external SDK is the ad network.

### 1.4 Data Flow: Move Lifecycle

This is the most critical flow in the app. Every visual spectacle is driven by this sequence:

```
User drags gem A → gem B (gesture on BoardLayer)
        │
        ▼
GameScene validates: adjacent? within board bounds?
        │ (local pre-check only — server is authoritative)
        ▼
APIClient.submitMove(row1, col1, row2, col2)
        │
        ▼
Backend responds with MoveResult:
{
    "valid": true,
    "events": [
        { "type": "swap", "gems": [...] },
        { "type": "match", "positions": [...], "gem_type": "red", "count": 3 },
        { "type": "special_created", "position": [2,4], "kind": "line_blast" },
        { "type": "fall", "movements": [...] },
        { "type": "cascade_match", "chain_step": 2, "positions": [...], "count": 4 },
        { "type": "fall", "movements": [...] },
        { "type": "cascade_match", "chain_step": 3, ... },
        ...
    ],
    "score_delta": 1240,
    "total_score": 5680,
    "moves_remaining": 14,
    "board_state": [[...]]  // final board after all cascades resolve
}
        │
        ▼
AnimationSequencer receives events array
        │
        ▼
Plays each event as a chained SKAction sequence:
  1. Swap animation (150ms elastic)
  2. Match burst particles + sound + haptic
  3. Special gem creation animation (if applicable)
  4. Gem fall animation (overshoot + bounce)
  5. Next cascade match burst (escalated particles + rising pitch)
  6. Repeat 4-5 for each chain_step
  7. Final board settle
        │
        ▼
Board state synced to backend's final board_state
(visual state must match server truth after animation completes)
```

**CRITICAL INVARIANT:** After the animation sequence completes, the visual board MUST exactly match `board_state` from the response. If any desync occurs, snap to server state. The animations are cosmetic — the server result is reality.

---

## 2. GameScene (SpriteKit Rendering) Full Spec

### 2.1 Scene Setup

| Property | Value | Notes |
|----------|-------|-------|
| Scene size | 390 × 844 (iPhone 14 logical) | Scale mode: `.aspectFill` — adapts to device |
| Board origin | Centered horizontally, vertically offset ~60% from bottom | Leave room for HUD overlay above |
| Gem cell size | 44 × 44 pt (with 2pt spacing) | Total board: ~368 × 368 pt on iPhone |
| Frame rate | 120fps on ProMotion, 60fps fallback | SpriteKit handles this automatically |
| Background | Solid dark (`#0D0D14` normal, `#000000` dark mode) | Muted to maximize gem pop |
| Z-ordering | Background (0) → Board (10) → Gems (20) → Particles (30) → HUD (40) → Overlay effects (50) | Strict layering prevents visual artifacts |

### 2.2 Node Hierarchy

```
GameScene (SKScene)
├── backgroundNode (SKSpriteNode — solid dark fill)
├── boardContainer (SKNode — positioned for centering)
│   ├── boardBackground (SKShapeNode — subtle rounded rect, very dark)
│   ├── gemGrid[8][8] (GemNode instances)
│   │   └── Each GemNode:
│   │       ├── shapeSprite (SKSpriteNode with custom fragment shader)
│   │       ├── glowSprite (SKSpriteNode — additive blend, pulsing alpha)
│   │       └── highlightSprite (SKSpriteNode — selection indicator, hidden by default)
│   └── gridOverlay (SKNode — subtle grid lines, very low alpha)
├── particleContainer (SKNode — all transient particle emitters live here)
├── overlayContainer (SKNode — screen-wide effects: flash, vignette, shake target)
└── hudContainer (SKNode — in-scene HUD elements if needed beyond SwiftUI overlay)
```

### 2.3 Gem Rendering (GemNode)

Each gem is a `GemNode: SKNode` subclass containing:

| Component | Implementation | Purpose |
|-----------|---------------|---------|
| Shape sprite | SKSpriteNode (32×32) with fragment shader | Base gem visual — shape, color, inner glow |
| Glow sprite | SKSpriteNode (48×48), `.additiveBlend` | Outer glow halo, alpha oscillates for pulse |
| Selection ring | SKShapeNode (circle, 40pt diameter) | Appears on touch-down, disappears on release |
| Special indicator | Additional SKSpriteNode with dedicated shader | Line arrows, bomb rings, chromatic rainbow |

**Gem types and their visual signatures:**

| Gem Color | Hex (Normal) | Hex (Dark Mode) | Shape Hint | Special Visual |
|-----------|-------------|-----------------|------------|----------------|
| Red | `#FF2D55` | `#FF375F` | Circle | — |
| Blue | `#007AFF` | `#0A84FF` | Diamond | — |
| Green | `#34C759` | `#30D158` | Hexagon | — |
| Yellow | `#FFCC00` | `#FFD60A` | Square (rounded) | — |
| Purple | `#AF52DE` | `#BF5AF2` | Triangle | — |
| Orange | `#FF9500` | `#FF9F0A` | Pentagon | — |
| Line Blast | Base color + white arrows | Same, brighter | Base shape + directional arrows overlaid | Arrows pulse along blast axis |
| Radial Bomb | Base color + concentric rings | Same, brighter | Base shape + expanding ring animation | Rings pulse outward continuously |
| Chromatic Orb | Rainbow cycle (all 6 hues) | Same, more vivid | Sphere with prismatic refraction shader | Constant slow hue rotation |

### 2.4 Gesture Handling

| Gesture | Recognition | Action |
|---------|------------|--------|
| Tap gem | UITapGestureRecognizer → hit test on gemGrid | Select gem (glow highlight) |
| Drag to swap | UIPanGestureRecognizer with threshold (>22pt in cardinal direction) | Determine swap direction, trigger swap |
| Tap second gem | If adjacent to selected gem | Trigger swap |
| Tap non-adjacent | — | Deselect, select new gem |
| Long press | UILongPressGestureRecognizer (0.5s) | Show gem info tooltip (type, potential) |

**Swap commit logic:**
1. User initiates swap gesture
2. Client immediately plays optimistic swap animation (150ms)
3. Simultaneously sends move to backend via APIClient
4. If backend returns `"valid": false`, reverse the swap animation (150ms rubber-band back)
5. If backend returns `"valid": true`, proceed with AnimationSequencer

**Latency hiding:** The optimistic swap animation buys ~150ms. Typical API round-trip on cellular is 100-300ms. If response arrives before swap animation completes, queue the result events. If response is slow (>300ms), hold gems in swapped position with subtle "waiting" shimmer until response arrives.

### 2.5 Camera & Screen Effects

| Effect | Trigger | Implementation |
|--------|---------|---------------|
| Screen shake | Special gem activation, fusion combo | `SKAction.shake(intensity:duration:)` custom action on `overlayContainer` — random x/y offset, decaying |
| Slow motion | Fusion combo, Radial Bomb activation | `scene.speed = 0.3` for 200ms, then ease back to 1.0 via `SKAction.customAction` |
| Screen flash | Special activation, chain threshold (3+) | Full-screen SKSpriteNode, alpha 0→0.4→0 over 150ms, color matches gem |
| Vignette glow | Cascade chain length ≥ 2 | Board edge glow node, intensity scales with chain step count |
| Zoom pulse | Fusion combo | `SKAction.scale` on boardContainer: 1.0→1.03→1.0 over 300ms, ease-in-out |
| Gold tint | Post-fusion "win mode" (2-3 seconds) | Overlay node with gold color, blend mode `.multiply`, alpha 0→0.15→0 over 2.5s |

---

## 3. SwiftUI Shell & Navigation

### 3.1 Navigation Architecture

```
ChromaCrushApp
└── NavigationShell (NavigationStack)
    ├── MainMenuView (root)
    │   ├── → MatchmakingView → GameContainerView → PostMatchView
    │   ├── → VaultView → ArtifactDetailView
    │   ├── → LeaderboardView
    │   ├── → StatsView
    │   ├── → SettingsView
    │   └── → AdFreeUpgradeView
    └── Persistent overlays:
        ├── EnergyBar (top — hearts + regen timer)
        ├── DailyStreakBadge (top-right — flame icon + count)
        └── RevengeNotification (banner — slides in when timer expires)
```

### 3.2 Screen Specifications

#### MainMenuView

| Element | Behavior | Visual |
|---------|----------|--------|
| Play button | Primary CTA — checks energy, enters matchmaking | Large, centered, pulsing glow animation, gem-colored gradient |
| Energy display | Shows hearts (0-5), regen timer for next heart | Heart icons, filled/empty, countdown text below |
| Daily streak | Shows current streak day count | Flame icon + "Day N" — tapping shows reward track |
| Vault preview | Miniature 3×3 grid of rarest artifacts | Tapping navigates to full VaultView |
| Revenge badge | Shows if revenge match available + countdown | Red notification dot, timer text, tapping starts revenge match |
| Bot opponent teaser | "OptiBot-7741 is climbing the ranks..." | Subtle animated text, rotates through active bot names |
| Ad-free banner | Only shown to free-tier users | Minimal, bottom of screen, "Remove ads — $1" |

#### MatchmakingView

| Phase | Duration | Visual |
|-------|----------|--------|
| Searching | 1-5 seconds (real) + min 2s (artificial floor) | Spinning gem animation, "Finding opponent..." text |
| Opponent found | 1 second hold | Opponent card slides in: name/icon, ELO, bot tag if applicable |
| Board loading | 0.5 seconds | Board fades in from below, gems drop into place one by one (staggered 20ms per column) |
| Match start | — | Transition to GameContainerView |

**Artificial floor rationale:** Even if matchmaking is instant, a 2-second minimum search creates anticipation. Slot machines do this with reel spin time.

#### GameContainerView

This is a SwiftUI view containing:
1. `SpriteView(scene: gameScene)` — fills most of the screen
2. `GameHUDOverlay` — SwiftUI overlay on top of SpriteKit, containing:
   - Score display (your score, large, animated on change)
   - Moves remaining (large number, color shifts yellow→orange→red as moves decrease)
   - Opponent info bar (name, bot icon if applicable, ELO — score hidden until match end)
   - Chain counter (appears during cascades, shows "x2", "x3", etc., scales up with each step)

**Why SwiftUI overlay instead of SpriteKit HUD?** Dynamic text, accessibility, and easier layout math. The HUD doesn't need 60fps rendering — it updates on game events only.

#### PostMatchView

Detailed in Section 7 (Post-Match Psychology Screens).

#### VaultView

Detailed in Section 6 (Vault/Collection UI Spec).

### 3.3 State Management

```swift
// Central app state — single source of truth
@Observable
class AppState {
    var currentScreen: Screen = .mainMenu
    var playerProfile: PlayerProfile?        // From backend
    var matchState: MatchState?              // Active match data
    var vaultContents: [Artifact] = []       // From backend
    var energyState: EnergyState             // Hearts + timers
    var dailyStreak: StreakState             // Day count + rewards
    var revengeTargets: [RevengeTarget] = [] // Available revenge matches
    var isAdFree: Bool = false              // Purchase status
    var isDarkMode: Bool = false            // Visual mode (locked behind ad-free)
    var audioEnabled: Bool = true
    var hapticsEnabled: Bool = true
}

enum Screen {
    case mainMenu
    case matchmaking
    case playing(MatchState)
    case postMatch(MatchResult)
    case vault
    case stats
    case leaderboard
    case settings
}
```

### 3.4 Dark Mode Implementation

Dark mode is a *premium visual upgrade*, not system dark mode. It's controlled by `AppState.isDarkMode` and gated behind ad-free purchase.

| Element | Normal Mode | Dark Mode (Ad-Free) |
|---------|------------|-------------------|
| Board background | `#0D0D14` (very dark blue-gray) | `#000000` (pure black) |
| Gem colors | Standard saturated palette | +10% brightness, +5% saturation |
| Gem glow radius | 4pt | 6pt |
| Particle brightness | 1.0× | 1.3× |
| Screen flash alpha | 0.3 peak | 0.45 peak |
| Board vignette | Subtle | Pronounced, color-reactive |
| UI chrome | Dark gray backgrounds | Pure black backgrounds, gem-colored accents |

The difference should be immediately noticeable and feel like "unlocking the real game." Every visual reward hits harder in dark mode.

---

## 4. Particle / Juice / Haptics System Spec

### 4.1 Particle System Architecture

All particle effects use SpriteKit's `SKEmitterNode` loaded from `.sks` files, with runtime parameter adjustments based on context (chain length, gem color, dark mode).

**Performance budget:** Maximum 500 active particles at any time. Each emitter has `particleBirthRate` and `numParticlesToEmit` caps. On older devices (A12 and below), reduce caps by 40%.

#### Particle Effect Catalog

| Effect | Trigger | Particle Count | Lifetime | Behavior | Colors |
|--------|---------|---------------|----------|----------|--------|
| MatchBurst | 3-gem match | 15-25 | 0.4s | Radial burst from match center, gravity pull down | Matched gem color, desaturating to white |
| CascadeBurst | Cascade step 2+ | 30-50 (scales with chain) | 0.5s | Larger radial burst + upward sparkle trail | Gem color + gold accents |
| LineSweep | Line Blast activation | 40-60 | 0.6s | Directional sweep along row/column | Gem color, white leading edge |
| RadialWave | Radial Bomb activation | 60-80 | 0.5s | Expanding ring + debris scatter in 3×3 | Gem color + white shockwave ring |
| ChromaticRain | Chromatic Orb activation | 80-120 | 0.8s | All gems of target color explode simultaneously, particles drift upward like embers | Target color → rainbow spectrum |
| FusionStorm | Fusion combo | 200-300 | 1.5s | Multi-phase: initial shockwave → rainbow particle vortex → golden confetti rain | Full rainbow cycle + gold |
| VictoryConfetti | Match won | 150-200 | 2.0s | Top-screen confetti cannon, gravity fall, slow drift | Gold + gem colors |
| NearMissSparkle | Board settle, potential match detected | 5-8 per spot | 0.3s | Subtle twinkle on gem positions that *almost* matched | White, very low alpha (0.3) |
| GemTrail | Gem falling after match | 3-5 per gem | 0.2s | Trailing sparkles behind falling gem | Gem color, fading |
| DefeatDust | Match lost | 30-40 | 1.0s | Slow grey-blue particle drift downward | Desaturated blue-gray |

### 4.2 Animation Sequencer — Timing Spec

The AnimationSequencer translates backend `events` into chained `SKAction` sequences. Timing is everything — too fast feels chaotic, too slow feels sluggish. These are target durations:

| Animation | Duration | Easing | Notes |
|-----------|----------|--------|-------|
| Gem swap | 150ms | `.easeInEaseOut` | Both gems move simultaneously |
| Invalid swap (rubber-band) | 150ms out + 150ms back | `.easeOut` + `.easeIn` | Subtle haptic "nope" on reversal |
| Match removal (gems shrink + burst) | 200ms | `.easeIn` | Gems scale to 0 while particles spawn |
| Special gem creation | 300ms | `.easeOutBack` (overshoot) | New gem scales from 0→1.1→1.0 with flash |
| Gem fall (per row of distance) | 80ms per row | Custom bounce: overshoot 15% + 2 diminishing bounces | Elastic feel, like physical gems dropping |
| Cascade pause (between chain steps) | 100ms | — | Brief beat to let player register the chain |
| Chain counter increment | 50ms | `.easeOutBack` | Number scales up 1.0→1.4→1.0 |
| Fusion sequence total | 1200-1800ms | Multi-phase (see below) | The showstopper moment |
| Board settle (final) | 200ms | — | All gems in final positions, gentle "landing" |

#### Fusion Combo Sequence (The Jackpot Moment)

```
T+0ms:      Slow-motion begins (scene.speed → 0.3)
T+0ms:      Both special gems glow intensely (brightness 2×)
T+100ms:    Screen shake begins (low intensity, building)
T+200ms:    Gems collide/merge animation (scale up + blend)
T+400ms:    FLASH — full-screen white, 100ms
T+400ms:    Slow-motion ends (scene.speed → 1.0)
T+400ms:    Shockwave ring expands from fusion point
T+500ms:    Affected gems begin chain-exploding (staggered 30ms each)
T+500ms:    Rainbow particle vortex active (200-300 particles)
T+600ms:    Screen shake peaks
T+800ms:    "MEGA FUSION!" text appears (scale 0→1.2→1.0, gold + glow)
T+800ms:    Triumphant fanfare audio cue
T+1000ms:   Golden confetti begins raining
T+1200ms:   Screen shake decays
T+1500ms:   Board tints gold (overlay, alpha 0.15)
T+1500ms:   Particle storm fading
T+1800ms:   Gold tint fading, board settling
T+2000ms:   Board fully settled, normal play resumes
```

### 4.3 Haptics Spec (Core Haptics)

Haptics are a massive differentiator on iOS. They make every action feel physical.

| Event | Pattern Type | Intensity | Sharpness | Duration | Notes |
|-------|-------------|-----------|-----------|----------|-------|
| Gem tap/select | `.hapticTransient` | 0.4 | 0.6 | — | Crisp "click" |
| Swap initiated | `.hapticTransient` | 0.5 | 0.4 | — | Softer "thud" |
| Invalid swap | `.hapticTransient` × 2 | 0.3, 0.5 | 0.8, 0.8 | 50ms gap | Double-tap "nope" |
| Basic match (3) | `.hapticTransient` | 0.6 | 0.5 | — | Satisfying "pop" |
| 4-match / small cascade | `.hapticContinuous` | 0.5→0.7 ramp | 0.4 | 150ms | Building rumble |
| Chain step (each) | `.hapticTransient` | 0.6 + (0.1 × step) | 0.5 | — | Escalating intensity per chain step, cap at 1.0 |
| Special activation | `.hapticContinuous` + `.hapticTransient` | 0.8 cont → 1.0 transient | 0.3→0.7 | 200ms + hit | Rumble building to sharp hit |
| Fusion combo | Complex AHAP pattern | Ramps 0.3→1.0 | Sweeps 0.2→0.9 | 800ms | Multi-phase: low rumble → building → sharp peak → decay |
| Victory | `.hapticContinuous` | 0.6 | 0.4 | 500ms | Warm sustained buzz |
| Loss | `.hapticTransient` | 0.7 | 0.9 | — | Single sharp "thud" — the gut-punch |
| Vault raided | `.hapticTransient` × 3 | 0.4, 0.6, 0.8 | 0.7 | 100ms gaps | Escalating alarm pattern |
| Gem landing (fall) | `.hapticTransient` | 0.2 + (0.05 × rows_fallen) | 0.6 | — | Heavier for longer falls |

**Device fallback:** If Core Haptics unavailable (older devices), fall back to `UIImpactFeedbackGenerator` with `.light` / `.medium` / `.heavy` mapping.

### 4.4 Escalation System — The Pulse

The game board has a global "intensity" value (0.0–1.0) that scales with game tension. This drives ambient visual/audio/haptic behavior.

**Intensity inputs (from backend state):**

| Factor | Contribution | Logic |
|--------|-------------|-------|
| Moves remaining | 0.0–0.4 | `(20 - movesRemaining) / 20 × 0.4` — pressure builds as moves decrease |
| Score differential | 0.0–0.3 | Close match → high tension. Blowout → low. `1.0 - abs(scoreDiff) / maxPossibleDiff` scaled |
| Recent cascade length | 0.0–0.2 | Hot streak → elevated intensity for 3 seconds post-cascade |
| Board state (from backend hints) | 0.0–0.1 | Low available matches → "dangerous" feeling |

**Intensity outputs (what changes visually):**

| Visual/Audio Element | At intensity 0.0 | At intensity 1.0 |
|---------------------|-------------------|-------------------|
| Gem pulse rate | 1.0 Hz (resting heartbeat, 60 BPM) | 2.5 Hz (tachycardic, 150 BPM) |
| Gem pulse amplitude (glow alpha range) | 0.05–0.15 | 0.10–0.40 |
| Background particle density | 0 (none) | 30-50 slow-drifting ambient particles |
| Board vignette intensity | 0.0 (invisible) | 0.3 (pronounced edge darkening) |
| Background music tempo | 100% base BPM | 130% base BPM |
| Background music filter | Full frequency | High-pass filter gradually applied (removes bass, adds tension) |
| Ambient hum volume | 0.0 | 0.15 (subtle but perceptible) |

This replaces the heartbeat-synced pulsing idea with something more nuanced — the pulse rate IS the heartbeat metaphor, but it's driven by game state, not physiological targeting. The player won't consciously notice the pulse rate change, but they'll *feel* the mounting tension.

---

## 5. Procedural Gem Art Spec

### 5.1 Design Philosophy

Gems are rendered via SpriteKit fragment shaders applied to simple quad sprites. No texture atlas, no artist-created assets. Benefits:

- Dark mode variant is a parameter change, not a second asset set
- Pulse/glow animations are shader uniform changes (GPU-driven, zero CPU cost)
- New gem types are new shaders, not new art production
- Resolution-independent — looks perfect on every device

### 5.2 Base Gem Shader Architecture

Each gem shader receives these uniforms:

```glsl
uniform float u_time;          // Elapsed time (drives animation)
uniform float u_pulse_rate;    // Current pulse frequency (from intensity system)
uniform float u_pulse_amp;     // Current pulse amplitude (from intensity system)
uniform float u_brightness;    // 1.0 normal, 1.1-1.3 dark mode
uniform float u_glow_radius;   // Outer glow size (4pt normal, 6pt dark mode)
uniform vec3  u_color;         // Primary gem color (RGB)
uniform float u_selected;      // 0.0 or 1.0 — selection highlight
uniform float u_special;       // 0.0 = normal, 1.0 = line, 2.0 = bomb, 3.0 = chromatic
```

### 5.3 Gem Shape Definitions

Each color gets a distinct silhouette so gems are distinguishable even without color (accessibility):

| Color | Shape | Shader approach |
|-------|-------|----------------|
| Red | Circle | SDF circle, smooth edge |
| Blue | Diamond (rotated square) | SDF rotated box |
| Green | Hexagon | SDF hexagon (6-fold symmetry) |
| Yellow | Rounded square | SDF box with corner radius |
| Purple | Triangle (equilateral) | SDF triangle |
| Orange | Pentagon | SDF 5-gon |

**SDF (Signed Distance Field) rendering** gives clean, resolution-independent shapes with smooth anti-aliased edges and easy glow/outline effects by using distance values from the shape boundary.

### 5.4 Shader Visual Layers (per gem)

```
Layer 1 (bottom): Outer glow
  - Gaussian falloff from shape edge, color = u_color at 30% alpha
  - Radius oscillates with u_pulse_rate (sin(u_time * u_pulse_rate * 2π) * u_pulse_amp)
  - This IS the heartbeat pulse

Layer 2: Shape fill
  - Solid u_color with subtle radial gradient (lighter center, darker edges)
  - Simulates "gem-like" depth/shine

Layer 3: Inner highlight
  - Small bright spot (near-white) offset upper-left
  - Simulates light reflection
  - Position subtly shifts with u_time (slow orbit, 0.2 Hz)

Layer 4 (top): Specular edge
  - Thin bright line on upper edge of shape SDF
  - Creates "polished gem" look

Layer 5 (conditional): Selection ring
  - When u_selected > 0.5: White ring just outside shape SDF, pulsing alpha

Layer 6 (conditional): Special overlay
  - Line Blast: Animated arrows along blast axis
  - Radial Bomb: Concentric expanding rings
  - Chromatic Orb: Full hue rotation on u_color, prismatic rainbow edge refraction
```

### 5.5 Visual Quality Targets

- Gems should feel like polished candy — glossy, saturated, physically "there"
- The dark background makes them float like lit objects in darkness
- Glow should feel like the gems are emitting light, not just blurry
- Shape variety must be clearly distinguishable at 44×44pt (phone viewing distance)
- Special gems should be immediately visually distinct from base gems without reading text
- Chromatic Orb should feel magical/rare — the rainbow effect signals "this is special"

---

## 6. Vault / Collection UI Spec

### 6.1 Vault Design Philosophy

The vault is a visual trophy case that creates attachment. Every artifact should feel *owned* — named, visually distinctive, displayed prominently. The goal: losing an artifact to a raid should produce a genuine emotional sting.

### 6.2 VaultView Layout

```
┌────────────────────────────────────┐
│  MY VAULT              [23 items]  │
│  ──────────────────────────────── │
│  ┌──────┐ ┌──────┐ ┌──────┐      │
│  │      │ │      │ │      │      │
│  │ Ruby │ │Sapph │ │Ember │      │
│  │Phoenx│ │Crown │ │Heart │      │
│  │  ★★★ │ │  ★★  │ │  ★   │      │
│  └──────┘ └──────┘ └──────┘      │
│  ┌──────┐ ┌──────┐ ┌──────┐      │
│  │      │ │      │ │ ░░░░ │      │
│  │Frost │ │Gold  │ │      │      │
│  │Blade │ │Lotus │ │ ???  │      │
│  │  ★★  │ │ ★★★★ │ │      │      │
│  └──────┘ └──────┘ └──────┘      │
│  ...                              │
│  ──────────────────────────────── │
│  RAID LOG                         │
│  ◈ OptiBot-7741 took Ruby Phoenix │
│    2 hours ago — REVENGE READY    │
│  ◈ human_player_42 took Frost... │
│    14 hours ago                   │
└────────────────────────────────────┘
```

### 6.3 Artifact Visual System

Artifacts are procedurally generated visuals (no artist assets), built from composable elements:

| Component | Options | Drives |
|-----------|---------|--------|
| Base shape | Gem, blade, crown, orb, heart, phoenix, lotus, shield, flame, star (10 shapes) | Silhouette |
| Primary color | Any of the 6 gem colors | Fill color |
| Accent color | Complementary or analogous to primary | Detail/trim color |
| Rarity tier | ★ (Common), ★★ (Uncommon), ★★★ (Rare), ★★★★ (Epic), ★★★★★ (Legendary) | Glow intensity, animation complexity |
| Name | Procedural: [Adjective] + [Noun] (e.g., "Frost Blade", "Ruby Phoenix") | Emotional attachment |

**Rarity visual escalation:**

| Rarity | Background | Glow | Animation | Frame |
|--------|-----------|------|-----------|-------|
| ★ Common | Plain dark | None | None | Simple border |
| ★★ Uncommon | Subtle gradient | Faint pulse | None | Silver border |
| ★★★ Rare | Color gradient | Medium pulse | Slow rotation | Gold border |
| ★★★★ Epic | Animated gradient | Strong pulse + particles | Floating/bobbing | Ornate gold + gem accents |
| ★★★★★ Legendary | Animated rainbow | Intense glow + particle trail | Floating + slow spin + sparkle trail | Animated ornate frame + light rays |

### 6.4 Raid Notification

When a vault raid occurs (pushed from backend or detected on poll):

1. **Banner notification** slides down from top (even if in a different screen)
2. Banner text: "**◈ OptiBot-7741** raided your vault!"
3. Tapping banner → **RaidDetailView**: Shows the stolen artifact with dramatic "taken" animation (artifact shrinks and fades with red vignette)
4. Revenge button with countdown timer prominently displayed
5. Haptic: Vault raided pattern (escalating triple-tap)
6. Sound: Alert sting — sharp, attention-grabbing, slightly ominous

### 6.5 Shield System UI

Shields protect artifacts from raids. Earned through play or rewarded ads.

| State | Visual | Interaction |
|-------|--------|-------------|
| No shield | Artifact displayed normally | Vulnerable — shown with subtle red tint on vault grid |
| Shield available (not applied) | Shield icon in inventory | Player chooses which artifact to protect |
| Shield active | Semi-transparent shield overlay on artifact | Tap to see shield duration remaining |
| Shield via ad | "Watch ad → Protect artifact" button | Rewarded ad flow → shield applied on completion |

---

## 7. Post-Match Psychology Screens

### 7.1 Screen Flow

```
Match ends (0 moves remaining)
        │
        ▼
Score reveal (your score, animated count-up)
        │ (1 second hold)
        ▼
Opponent score reveal (slides in from right)
        │ (0.5 second hold for comparison)
        ▼
Result declaration:
  ┌─── WIN ──────────────────────────────┐
  │ "VICTORY" text + confetti + haptic   │
  │ → Vault raid animation (their vault  │
  │   opens, artifact floats to you)     │
  │ → Trophy points awarded display      │
  │ → "Play Again" + "Vault" buttons     │
  └──────────────────────────────────────┘
  ┌─── LOSS (by large margin) ──────────┐
  │ "DEFEAT" text + muted animation     │
  │ → Your vault raided animation       │
  │ → "Play Again" button (prominent)   │
  │ → Revenge timer starts (2 hours)    │
  └──────────────────────────────────────┘
  ┌─── LOSS (by small margin, near-miss)┐
  │ "DEFEAT" text + brief pause         │
  │ → Near-miss messaging (see 7.2)     │
  │ → Your vault raided animation       │
  │ → "REVENGE" button (glowing, urgent)│
  │ → Revenge timer starts              │
  └──────────────────────────────────────┘
```

### 7.2 Near-Miss Messaging

When the backend flags a loss as a near-miss (the 40% engineered close losses):

| Element | Content | Purpose |
|---------|---------|---------|
| Score differential | "You lost by **340 points**" | Frames loss as small/close |
| Cascade tease | "One more cascade would have changed everything." | Implies near-win, triggers "one more try" |
| Board state hint | "Your board had **3 potential chains** on the final turn." | Suggests skill could have won — not just luck |
| Visual treatment | Score difference number pulses red, cascade text has subtle sparkle | Draws eye to the "almost" framing |

**What we do NOT show:** No animated replay of what could have happened. No "Close Call!" celebration particles. These cross the line from compelling framing into manipulation that could feel insulting if the player catches on. The text-based near-miss messaging is powerful enough.

### 7.3 Win Screen Spec

```
Phase 1 — Result Declaration (0-500ms):
  "VICTORY" text scales in (0→1.2→1.0), gold color, shadow glow
  Confetti burst from top of screen
  Victory haptic pattern
  Short triumph sting (audio)

Phase 2 — Score Celebration (500ms-1500ms):
  Your score: large number, already visible
  Score differential: "+1,240 points ahead" in green
  Trophy points: "+15 🏆" animated count-up

Phase 3 — Vault Raid (1500ms-3000ms):
  Opponent's vault icon appears (miniature, shaking)
  Vault cracks open (animated — splitting + golden light pours out)
  Artifact floats out with golden particle trail
  Artifact name + rarity revealed as it arrives at "your vault" indicator
  "You claimed [Artifact Name]!" text

Phase 4 — Actions (3000ms+):
  "Play Again" button (primary, prominent)
  "View Vault" button (secondary)
  Energy cost reminder if applicable
```

### 7.4 Loss Screen Spec

```
Phase 1 — Result Declaration (0-500ms):
  "DEFEAT" text fades in (muted, gray-red)
  Single gut-punch haptic
  Low, brief defeat tone (audio)
  NO confetti, NO celebration, NO particles
  The tone is somber — not punishing, but distinctly "not winning"

Phase 2 — Near-Miss (if flagged, 500ms-1500ms):
  Near-miss messaging appears (see 7.2)
  1 second hold for player to absorb

Phase 3 — Vault Raided (1500ms-2500ms):
  Your vault icon appears (shaking, red-tinted)
  Vault opens, artifact taken (artifact shrinks away with red/dark particle trail)
  "[Opponent] claimed your [Artifact Name]!" text
  If opponent is a bot: bot name in distinctive format with icon

Phase 4 — Revenge Prompt (2500ms+):
  Revenge timer begins: "Revenge available in 2:00:00"
  "REVENGE" button appears but is initially grayed/locked with timer
  "Play Again" button (standard match)
  Energy state visible
  
  The revenge button should feel like unfinished business —
  it stays in the player's mind during the 2-hour wait.
```

### 7.5 Post-Match → Next Match Pipeline

After tapping "Play Again":

1. If energy available: Transition directly to MatchmakingView (no return to main menu)
2. If no energy: Show EnergyRefillView with "Watch ad for +1 heart" or "Wait [timer] for next heart"
3. Transition animation: Board from previous match subtly blurs and slides away as matchmaking spinner appears — visual continuity, no hard cuts to menus

**Rationale:** Minimizing friction between matches is critical. Every extra tap or screen between "I want to play" and "I'm playing" is a chance for the player to leave. The flow should feel like pulling the next lever.

---

## 8. Audio System Spec

### 8.1 Architecture

Audio uses `AVAudioEngine` for layered, real-time sound with the following bus structure:

```
AVAudioEngine
├── SFX Bus (AVAudioMixerNode)
│   ├── Match sounds (pooled: 4 simultaneous)
│   ├── Cascade sounds (pooled: 4 simultaneous)
│   ├── Special activation sounds (pooled: 2)
│   ├── UI interaction sounds (pooled: 2)
│   └── Notification sounds (1)
├── Music Bus (AVAudioMixerNode)
│   ├── Background music player (AVAudioPlayerNode, looping)
│   └── Adaptive filter chain (high-pass, tempo adjustment)
└── Ambient Bus (AVAudioMixerNode)
    └── Tension hum (AVAudioPlayerNode, looping, volume from intensity system)
```

### 8.2 Sound Effect Design (Procedural Synthesis Preferred)

To avoid asset management and enable dynamic parameter scaling, generate SFX procedurally where possible using `AVAudioSourceNode` or pre-rendered short buffers:

| Sound | Synthesis Approach | Parameters |
|-------|-------------------|------------|
| Gem select | Short sine wave ping, 800-1200 Hz, 50ms, fast decay | Pitch varies by gem color |
| Swap | Dual-tone sweep (up+down), 200-600 Hz, 100ms | — |
| Invalid swap | Low buzz, 150 Hz, 80ms, slight distortion | — |
| Match (3) | Bright chime, pentatonic note, 80ms, clean decay | Pitch = base note for current chain position |
| Cascade step N | Same as match but pitch = base + N semitones ascending | C4→D4→E4→F#4→A4→C5→... |
| Special creation | Rising arpeggio (3 notes, 40ms each) + shimmer noise | — |
| Line Blast | Whoosh sweep (noise, band-pass moving 200→4000 Hz, 300ms) | Direction (L→R or T→B) pans stereo |
| Radial Bomb | Low impact (80 Hz thud, 100ms) + debris scatter (noise burst, 200ms) | — |
| Chromatic Orb | Shimmering chord (major triad + octave, 500ms sustain, slow fade) | Hue-matched to target color |
| Fusion fanfare | Multi-layered: brass stab + bell chime + rising sweep + crowd-cheer noise | 1200ms total, synced to visual sequence |
| Victory sting | Triumphant major chord (I-IV-V-I), bright, 800ms | — |
| Defeat sting | Minor chord (i), muted, single hit, 400ms | Low energy, not punishing |
| Near-miss sting | Tension build (rising tone) that cuts off abruptly | The "almost" feeling in audio — anticipation with no payoff |
| Vault raid alert | Alarm pattern: 3 ascending sharp tones, 100ms each | Urgency without annoyance |
| Heart refill | Gentle ascending chime, 200ms | Reward sound — positive |
| Gem landing | Short thud, pitch varies with fall distance | Barely audible, contributes to "physical" feel |

### 8.3 Cascade Audio Escalation

The ascending pitch chain on cascades is a core dopamine driver. Specification:

```
Chain step 1: C4  (261.6 Hz) — single chime
Chain step 2: D4  (293.7 Hz) — chime + subtle harmony (octave below)
Chain step 3: E4  (329.6 Hz) — chime + harmony + light sparkle layer
Chain step 4: F#4 (370.0 Hz) — chime + harmony + sparkle + bass swell begins
Chain step 5: A4  (440.0 Hz) — all layers + bass swell + ambient brightening
Chain step 6: C5  (523.3 Hz) — all layers intensified + crowd murmur sample
Chain step 7+: Continue ascending by whole tones, add layers until fusion-level density
```

Each step adds harmonic density. By step 5+ the player should feel the audio equivalent of a slot machine building to a jackpot. The ascending scale creates irresistible forward momentum — the brain wants to hear the next note.

### 8.4 Adaptive Background Music

Background music is a looping track (MIDI-rendered or procedural) with real-time adaptation:

| Intensity Range | Music Behavior |
|----------------|----------------|
| 0.0–0.3 (calm) | Base tempo (110 BPM), full frequency, relaxed feel |
| 0.3–0.6 (tension building) | Tempo +10%, subtle high-pass filter begins (removes low-end warmth) |
| 0.6–0.8 (high tension) | Tempo +20%, high-pass stronger, percussion layer added |
| 0.8–1.0 (critical) | Tempo +30%, high-pass aggressive, percussion prominent, bass pulses |

**Implementation:** Use `AVAudioUnitTimePitch` for tempo adjustment without pitch shift. Use `AVAudioUnitEQ` for filter sweeps. Percussion layer is a separate `AVAudioPlayerNode` with volume crossfade.

### 8.5 Audio Defaults & Settings

| Setting | Default | Notes |
|---------|---------|-------|
| SFX volume | 80% | Slightly below max — room for cascade escalation to feel louder |
| Music volume | 40% | Background, not foreground |
| Haptics | On | Separate from audio |
| Master mute | Off | Single toggle mutes all audio |

**Default loud rationale:** Many players leave audio on when it defaults to on, especially if it sounds good. The cascade audio escalation is a key retention mechanic — it should be heard.

---

## 9. API Client & Backend Integration

### 9.1 APIClient Design

```swift
// Core API client — async/await, Codable, minimal
actor APIClient {
    let baseURL: URL                    // Backend server URL
    let session: URLSession             // Configured with timeout, caching policy
    var authToken: String?              // Set after login/account creation
    
    // MARK: - Match endpoints
    func newMatch() async throws -> NewMatchResponse
    func submitMove(row1: Int, col1: Int, row2: Int, col2: Int) async throws -> MoveResult
    func getGameState() async throws -> GameState
    func getMatchResult() async throws -> MatchResult
    
    // MARK: - Player endpoints
    func getPlayerStats() async throws -> PlayerStats
    func getVault() async throws -> VaultContents
    func getEnergyState() async throws -> EnergyState
    
    // MARK: - Social endpoints
    func getLeaderboard(type: LeaderboardType) async throws -> Leaderboard
    func getRevengeTargets() async throws -> [RevengeTarget]
    func startRevengeMatch(targetId: String) async throws -> NewMatchResponse
    
    // MARK: - Monetization endpoints
    func reportAdWatched(type: AdType) async throws -> AdRewardResponse
    func purchaseAdFree(receipt: String) async throws -> PurchaseResponse
    
    // MARK: - Auth
    func createAccount(username: String) async throws -> AuthResponse
    func loginAnonymous() async throws -> AuthResponse  // First 3 matches
}
```

### 9.2 Polling vs. Push Strategy

| Data | Strategy | Frequency | Notes |
|------|----------|-----------|-------|
| Match state during play | Request-response per move | On each move submission | Not real-time — async matches don't need WebSocket |
| Opponent score (end of match) | Single request on match completion | Once | Revealed only after both players finish |
| Energy regeneration | Client-side timer + server validation | Validate on each match start | Client counts down visually, server confirms on action |
| Vault raid notifications | Poll on app foreground + push notification | Every 30s when app active | Backend sends push notification for immediate raids |
| Revenge timer | Client-side countdown | Validate on revenge attempt | Server checks timer validity |
| Flash events | Poll on app foreground | Every 60s | Backend provides active events list |
| Leaderboard | Fetch on view | On navigation to leaderboard | Cache for 60 seconds |

### 9.3 Offline / Error Handling

| Scenario | Behavior |
|----------|----------|
| No network on match start | Show error, disable Play button, retry on network change |
| Network loss mid-match | Queue move locally, retry with exponential backoff, show subtle "reconnecting..." indicator. If 30s timeout, show "Connection lost — your match is saved" and return to menu |
| Server error (5xx) | Retry once, then show "Server issue — try again shortly" |
| Auth token expired | Silent refresh, retry original request |
| Move rejected (invalid) | Rubber-band swap animation, show nothing (no error message — feels like a misswipe) |

---

## 10. Feasibility & Implementation Priority Matrix

### 10.1 Feature-Level Breakdown

| Category | Feature | Incremental? | Dependencies | Effort (days) | Priority Phase |
|----------|---------|-------------|--------------|---------------|----------------|
| **Architecture** | Xcode project scaffold + SwiftUI shell + SpriteView embedding | Foundation | None | 1-2 | **Phase 1** |
| **Architecture** | APIClient + BackendContract generation from backend survey | Foundation | Backend docs | 1-2 | **Phase 1** |
| **Board Rendering** | 8×8 grid of placeholder gem sprites (colored circles) | Foundation | Project scaffold | 1 | **Phase 1** |
| **Board Rendering** | Gem swap gesture handling (drag + tap) | Foundation | Grid rendering | 1 | **Phase 1** |
| **Board Rendering** | Swap → API call → response → basic match removal animation | Foundation | APIClient + grid | 2-3 | **Phase 1** |
| **Board Rendering** | Gem fall animation (basic, linear) | Foundation | Match removal | 1 | **Phase 1** |
| **Board Rendering** | Cascade chaining animation (sequential match → fall → match) | Foundation | Fall animation | 2 | **Phase 1** |
| **Gem Art** | Procedural gem shaders (SDF shapes + color + glow) | Incremental | Grid rendering | 2-3 | **Phase 2** |
| **Gem Art** | Special gem visual variants (line/bomb/chromatic shaders) | Incremental | Base gem shaders | 1-2 | **Phase 2** |
| **Gem Art** | Gem pulse animation (shader uniform driven by intensity system) | Incremental | Base gem shaders | 0.5 | **Phase 2** |
| **Juice** | Match burst particles (SKEmitterNode per color) | Very incremental | Match removal working | 1 | **Phase 2** |
| **Juice** | Cascade escalating particles (density scales with chain) | Very incremental | Cascade animation | 0.5 | **Phase 2** |
| **Juice** | Screen shake on specials | Very incremental | Special activation | 0.5 | **Phase 2** |
| **Juice** | Slow-mo on fusion | Very incremental | Fusion detection | 0.5 | **Phase 2** |
| **Juice** | Fusion jackpot sequence (full multi-phase) | Medium | All particle systems | 2-3 | **Phase 2** |
| **Juice** | Elastic bounce on gem falls | Very incremental | Fall animation | 0.5 | **Phase 2** |
| **Juice** | Gem trail particles on fall | Very incremental | Fall animation | 0.5 | **Phase 2** |
| **Audio** | AVAudioEngine setup + SFX bus | Incremental | None | 1 | **Phase 2** |
| **Audio** | Match/cascade chime with ascending pitch | Incremental | Audio engine + cascade animation | 1 | **Phase 2** |
| **Audio** | Special activation sounds | Incremental | Audio engine | 0.5 | **Phase 2** |
| **Audio** | Fusion fanfare | Incremental | Audio engine | 1 | **Phase 2** |
| **Haptics** | Core Haptics engine setup + basic patterns | Incremental | None | 0.5 | **Phase 2** |
| **Haptics** | Match/cascade/fusion haptic patterns | Incremental | Haptics engine | 0.5 | **Phase 2** |
| **Intensity** | Global intensity system (inputs from game state) | Medium | Game state from API | 1 | **Phase 3** |
| **Intensity** | Intensity → gem pulse rate/amplitude | Incremental | Intensity system + gem shaders | 0.5 | **Phase 3** |
| **Intensity** | Intensity → ambient particles + vignette | Incremental | Intensity system | 0.5 | **Phase 3** |
| **Intensity** | Intensity → music adaptation (tempo/filter) | Medium | Music system + intensity | 1-2 | **Phase 3** |
| **Navigation** | MainMenuView (play button, energy, streak) | Medium | SwiftUI shell + APIClient | 1-2 | **Phase 3** |
| **Navigation** | MatchmakingView (search animation + opponent reveal) | Medium | Matchmaking endpoint | 1 | **Phase 3** |
| **Post-Match** | Win screen (victory text + confetti + score) | Medium | Match result endpoint | 1-2 | **Phase 3** |
| **Post-Match** | Loss screen (defeat text + near-miss messaging) | Medium | Match result endpoint | 1-2 | **Phase 3** |
| **Post-Match** | Vault raid animation (win: artifact gained) | Medium | Vault endpoint + artifact art | 2 | **Phase 3** |
| **Post-Match** | Vault raid animation (loss: artifact taken) | Medium | Vault endpoint | 1 | **Phase 3** |
| **Post-Match** | Revenge prompt + timer | Medium | Revenge endpoint | 1 | **Phase 3** |
| **Post-Match** | Play-again flow (direct to matchmaking, no menu) | Incremental | Post-match screen | 0.5 | **Phase 3** |
| **Vault** | VaultView grid display | Medium | Vault endpoint | 1-2 | **Phase 4** |
| **Vault** | Artifact procedural visuals (shape + color + rarity) | Medium | Art system defined | 2-3 | **Phase 4** |
| **Vault** | Raid log display | Incremental | Vault endpoint | 0.5 | **Phase 4** |
| **Vault** | Shield system UI | Medium | Shield endpoint | 1 | **Phase 4** |
| **Vault** | Raid notification banner (push + in-app) | Medium | Push notification setup | 1-2 | **Phase 4** |
| **Energy** | Heart display + regen timer | Medium | Energy endpoint | 1 | **Phase 4** |
| **Energy** | Rewarded ad → heart flow | Medium | Ad SDK integration | 1-2 | **Phase 4** |
| **Social** | Leaderboard view | Easy | Leaderboard endpoint | 1 | **Phase 5** |
| **Social** | Stats view (ELO graph, cascade stats) | Medium | Stats endpoint | 1-2 | **Phase 5** |
| **Monetization** | Ad SDK integration (interstitial every 3rd match) | Medium | Ad SDK | 1-2 | **Phase 5** |
| **Monetization** | $1 ad-free purchase (StoreKit 2) | Medium | StoreKit | 1-2 | **Phase 5** |
| **Dark Mode** | Dark mode visual variant (shader params + UI colors) | Incremental | Ad-free purchase working + gem shaders | 0.5 | **Phase 5** |
| **Near-Miss** | Post-match near-miss sparkle on board (what almost matched) | Incremental | Board rendering + match result | 1 | **Phase 5** |
| **Near-Miss** | Idle board tease (potential matches flicker subtly) | Incremental | Board rendering | 0.5 | **Phase 5** |
| **Music** | Background music loop + adaptive tempo/filter | Medium | Audio engine | 2-3 | **Phase 5** |
| **Daily Streak** | Streak counter + reward track display | Medium | Streak endpoint | 1-2 | **Phase 5** |
| **FOMO** | Flash event banner + event-specific UI | Medium-heavy | Event system endpoint | 2-3 | **Phase 6** |

### 10.2 Phased Roadmap

**Phase 1 — Playable Core (Estimated: 8-12 days)**
> A human can start a match, see the board, make swaps, see matches resolve with basic animation, and reach an end screen. No juice, no art, no audio. Colored circles on a dark background. This is the skeleton.

- Project scaffold + SwiftUI shell + SpriteView
- Backend survey → BackendContract.swift generation
- APIClient with auth + core match endpoints
- 8×8 grid rendering (colored circles)
- Swap gesture → API call → response handling
- Match removal animation (fade/shrink, basic)
- Gem fall animation (linear)
- Cascade chain animation (sequential)
- Move counter + score display (SwiftUI overlay)
- Basic end-of-match screen (win/loss text)

**Phase 2 — Juice Pass (Estimated: 8-12 days)**
> The game feels good to play. Every match pops, cascades escalate, fusions feel incredible. This is where the dopamine starts.

- Procedural gem shaders (SDF shapes, color, glow)
- Special gem visual variants
- All particle effects (match burst through fusion storm)
- Elastic bounce on gem falls + trail particles
- Screen shake, slow-mo, flash, zoom
- Audio engine + all SFX (match chimes, cascade ascending scale, fusion fanfare)
- Core Haptics for all game events
- Gem pulse animation

**Phase 3 — Psychology Layer (Estimated: 8-12 days)**
> The game hooks players. Post-match screens drive "one more match." The intensity system makes tense moments feel tense.

- Intensity system (game state → visual/audio scaling)
- Intensity outputs (pulse rate, ambient particles, vignette, music adaptation)
- MainMenuView (full: play button, energy, streak badge, revenge indicator)
- MatchmakingView (search animation, opponent reveal)
- Win screen (full sequence: victory → raid → artifact → actions)
- Loss screen (full sequence: defeat → near-miss → raided → revenge)
- Play-again flow (direct to matchmaking)

**Phase 4 — Persistence & Loss Aversion (Estimated: 6-10 days)**
> Players care about their stuff and hurt when they lose it.

- VaultView (grid display, artifact visuals, rarity scaling)
- Artifact procedural generation (shape + color + rarity compositing)
- Raid animations (gain and loss)
- Raid notification system (in-app banner + push)
- Shield system UI
- Energy display + regen timer
- Rewarded ad → heart refill flow

**Phase 5 — Monetization & Polish (Estimated: 8-12 days)**
> Revenue mechanics are live. Social features create competitive context.

- Ad SDK integration (interstitial + rewarded + banner)
- $1 ad-free purchase (StoreKit 2)
- Dark mode unlock
- Leaderboard view
- Stats view
- Background music (adaptive)
- Daily streak system
- Near-miss subtle effects (board sparkle, idle tease)

**Phase 6 — LiveOps (Ongoing)**
> The game has legs. Events drive return visits. A/B testing refines everything.

- Flash event system UI
- Event-specific artifacts
- A/B testing infrastructure for psychology parameters
- Performance optimization pass
- Accessibility audit

### 10.3 Critical Path

The longest dependency chain is:

```
Backend survey → APIClient → Board rendering → Swap + API → Match animation → Cascade animation
```

This is Phase 1 and cannot be parallelized. Once this is complete, Phases 2-5 are largely parallelizable — juice, audio, haptics, vault, and monetization can all proceed independently with occasional integration points.

### 10.4 Most Coupled Components

| Component A | Component B | Coupling Nature |
|------------|------------|-----------------|
| AnimationSequencer | Backend event format | Sequencer must handle every event type backend produces |
| Intensity system | Gem shaders + Audio + Haptics | Intensity drives parameters across all sensory systems |
| Post-match screens | Backend match result schema | Near-miss flag, raid result, revenge availability |
| Vault view | Artifact data model | Visual generation depends on backend artifact schema |
| Energy system | Ad SDK | Rewarded ad completion → heart refill flow |

### 10.5 Bottom Line

Once Phase 1 is stable (human can play a full match through the API with basic visuals), everything else is additive. The architecture is designed so that juice, psychology, vault, and monetization are all independent layers that plug into the core loop without requiring refactoring.

The fastest path to a compelling demo: **Phase 1 + Phase 2 partial (just gem shaders + match particles + cascade audio).** This gives you a game that looks and sounds great within ~12-16 days, even without the psychology screens or vault system.

---

*End of Document*
