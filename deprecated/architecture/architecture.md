# ChromaCrush Architectural Skeleton

**Version:** 1.1  
**Purpose:** This document serves as a detailed, LLM-oriented architectural skeleton for the ChromaCrush software system. It is designed to facilitate automated surveying, analysis, code generation, and navigation by LLMs (e.g., for dependency mapping, interface extraction, or module simulation). Human-readable elements like timelines, projections, and executive summaries are omitted. Instead, focus is on hierarchical structures, dependencies, interfaces, data flows, and LLM-specific affordances (e.g., API schemas for bot integration, protocol definitions for DI, type systems for schema validation). The skeleton integrates the Game Design Document (GDD) mechanics, backend module reports, and iOS frontend design, treating the system as a complete, surveyable graph of components.

**LLM Survey Guidelines:**
- **Traversal:** Start from root nodes (e.g., API module as entry point) and follow dependency edges. Use type protocols for interface mocking.
- **Querying:** Extract schemas (e.g., DTOs, enums) for prompt engineering or simulation. For bot LLM integration, prioritize auth (API keys) and match APIs (hints for optimization).
- **Generation:** Use public interfaces and configs as templates for code stubs. Validate against error codes and types.
- **Analysis:** Map cross-module calls for dependency graphs; identify pure functions (sync, stateless) for isolated testing.

## 1. System Topology

### 1.1 High-Level Component Graph
- **Clients (Render-Only Leaves):** Web (HTML5/React), iOS (SwiftUI/SpriteKit). Depend on Backend API; no local logic.
- **Backend (Core DAG):** Modular Python services in waves (1-9). Root: Config/Logger/Errors. Leaves: Player/Board. Terminal: API/Payments/Bot_Earnings.
- **Persistence:** PostgreSQL (structured data), Redis (transient state).
- **Communication:** REST (actions), WebSocket (real-time: match updates, energy regen, events).
- **External Integrations:** Ad providers (e.g., AdMob abstraction), Payment gateways (Apple/Google protocols).

### 1.2 Dependency Waves (Backend)
Waves define build order and acyclic dependencies. Each module lists: Overview, Public Interface (methods/signatures), Dependencies (protocols), Data Owned (tables/keys), Config Keys, Error Codes, Cross-Module Flows, Key Types (DTOs/Enums).

- **Wave 1 (Leaves: Pure Foundations):** Player, Board.
- **Wave 2 (Basic Logic):** Scoring, Energy, Auth.
- **Wave 3 (Enhancements):** Vault, Special_Gems.
- **Wave 4 (Generation):** Board_Gen.
- **Wave 5 (Orchestration):** Match.
- **Wave 6 (Social/Competitive):** Events, Matchmaking.
- **Wave 7 (Monetization Base):** Ads.
- **Wave 8 (Terminals: Revenue):** Bot_Earnings, Payments.
- **Wave 9 (Exposure Terminal):** API.

### 1.3 Frontend Phases (iOS-Specific; Web Analogous)
Phases align with backend waves for integration. Each phase lists: Components, Dependencies, Interfaces (e.g., Swift structs mapping backend DTOs), Render Flows, LLM Affordances (e.g., animation sequences for procedural gen).

- **Phase 1 (Core Loop):** APIClient, Board Rendering.
- **Phase 2 (Juice/Sensory):** Animations, Audio, Haptics.
- **Phase 3 (Psychology):** Post-Match Screens.
- **Phase 4 (Persistence):** Vault, Energy UI.
- **Phase 5 (Monetization):** Ads, Purchases.
- **Phase 6 (LiveOps):** Events, A/B.

## 2. Game Mechanics Skeleton (From GDD)

### 2.1 Match-3 Core
- **Grid (Two-Grid Model):** Two parallel 8x8 NumPy int8 arrays per board — `grid` (colors: 0=EMPTY, 1-6=standard gem colors) and `func_grid` (functions: 0=NEUTRAL, 1=LINE_BLAST_H, 2=LINE_BLAST_V, 3=RADIAL_BOMB, 4=CHROMATIC_ORB). Every gem has both a color and a function. Match detection reads only `grid` (colors), so colored special gems participate in same-color runs automatically.
- **Operations (Board Module):** Swap (adjacent positions), Detect Matches (horiz/vert, min=3), Clear (both grids), Gravity (both grids), Fill (seeded random, func_grid=NEUTRAL).
- **Cascades:** Loop until stable; track steps for scoring multipliers. Special gem placement writes color to `grid` and function to `func_grid`.
- **Special Gems:** GemFunction enum (NEUTRAL, LINE_BLAST_H/V, RADIAL_BOMB, CHROMATIC_ORB); creation rules and effect areas defined in `config/board_rules.json`, interpreted by `EffectInterpreter`. Specials carry their match's base color. Detection via `func_grid != 0`.
- **Fusions:** Swap two specials; mega gem value = `funcA * 10 + funcB`; combo effects defined in `board_rules.json` `mega_gems.combos` section.
- **API Serialization:** Board state serialized as `{"cells": [[int]], "functions": [[int]]}`. Backwards-compatible deserialization accepts legacy `[[int]]` format (func_grid defaults to all-NEUTRAL).

### 2.2 Versus Mode
- **Lifecycle:** Create (seed board, consume energy), Submit Move (process cascades, score), Forfeit/Abandon.
- **Scoring:** Base per gem + length/chain multipliers + special bonuses.
- **Async:** Divergent per-player boards from shared seed; compare final scores.
- **Raids:** Post-loss; probabilistic artifact transfer from vault.

### 2.3 Progression Systems
- **Energy:** Hearts (max 5, regen interval); bonuses from streaks/ads/events.
- **Vault:** Artifacts (rarity enums: COMMON/RARE/EPIC/LEGENDARY); sets for completion; shields (time-limited).
- **Events:** Types (FLASH/WEEKLY/SEASONAL); scoring modes (TOTAL/BEST/AVERAGE); leaderboards (Redis sorted sets).
- **ELO:** Initial 1000; K-factor 32; updates post-match.

### 2.4 Psychology Affordances (LLM-Relevant)
- **Human Hooks:** Near-miss tuning (board_gen params); variable reinforcement (cascade potential 0.0-1.0).
- **Bot Hooks:** Hints in API responses (valid moves count, potential score categories); progressive mechanics (level-gated: basics → fusions → obstacles).
- **LLM Integration:** Bot players use API keys; responses include semantic hints for reasoning (e.g., "high-cascade potential quadrant").

## 3. Backend Modules Detail

### 3.1 Wave 1: Player Module
- **Overview:** Player entities (HUMAN/BOT enums), ELO, stats aggregation, energy state.
- **Public Interface:** async def create_player(username: str, player_type: PlayerType, password_hash: Optional[str]) -> Player; get_player(player_id: UUID) -> Player; update_elo(player_id: UUID, new_rating: int) -> Player; etc. (14 methods).
- **Dependencies:** ConfigProtocol (ELO init/K-factor), LoggerProtocol, ErrorServiceProtocol; repositories (Player/Stats/Energy).
- **Data Owned:** Tables: players (UUID PK, username_lower), player_stats (aggregates), energy_states (hearts, streak).
- **Config Keys:** matchmaking.elo_initial: int=1000; energy.max_hearts: int=5; player.username_pattern: str="^[a-zA-Z0-9_]+$".
- **Error Codes:** NOT_FOUND_PLAYER (404), CONFLICT_USERNAME_TAKEN (409).
- **Cross-Module Flows:** Provides player lookups to all; called for ELO/stats updates (match), energy reads (energy).
- **Key Types:** Player (dataclass: id, type, elo), PlayerStats (wins, highest_score), EnergyState (hearts, last_regen_at), PlayerType Enum.

### 3.2 Wave 1: Board Module
- **Overview:** Pure sync grid ops; NumPy-backed in-place mutation. Schema-driven special gem rules and effects.
- **Public Interface:** def create_board(width: int, height: int, seed: int) -> BoardState; def process_move(board: BoardState, move: Move, seed: int) -> MoveProcessingResult; etc. (9 methods).
- **Dependencies:** ConfigProtocol (dimensions), LoggerProtocol, ErrorServiceProtocol.
- **Data Owned:** Stateless.
- **Config Keys:** game.board_width: int=8; game.gem_types: int=6.
- **Config Files:** `config/board_rules.json` — JSON schema defining special creation rules, effect areas, mega combos, attraction config. Loaded at `BoardService.__init__` by `schema_loader.load_board_rules()`.
- **Schema Interpreter:** `EffectInterpreter` class replaces all hardcoded if/elif trees in detection, special_gems, and mega_gems mixins with schema-driven dispatch.
- **Cascade Architecture:** `_run_cascade_step_inplace` refactored into 10 named phase methods operating on a `CascadeContext` dataclass.
- **Error Codes:** VALIDATION_OUT_OF_BOUNDS (400), VALIDATION_INVALID_GEM_SWAP (400).
- **Cross-Module Flows:** Provides match detection to scoring/special_gems/board_gen/match.
- **Key Types:** BoardState (np.ndarray[int8]), MatchResult (list[MatchGroup]), Move (tuple[Position, Position]), Position (tuple[int, int]), CascadeContext (mutable cascade state).

### 3.3 Wave 2: Scoring Module
- **Overview:** Pure sync arithmetic; multipliers for matches/chains/specials.
- **Public Interface:** def calculate_move_score(move_result: MoveProcessingResult) -> MoveScore; etc. (6 methods).
- **Dependencies:** ConfigProtocol (multipliers), LoggerProtocol, ErrorServiceProtocol; imports board types.
- **Data Owned:** Stateless.
- **Config Keys:** scoring.base_points: int=50; scoring.chain_multipliers: list[float]=[1.0,1.5,...].
- **Error Codes:** VALIDATION_INVALID_INPUT (400).
- **Cross-Module Flows:** Called by special_gems (bonuses), match (move scores).
- **Key Types:** MoveScore (total, breakdown), SpecialGemBonus (base + per_gem).

### 3.4 Wave 2: Energy Module
- **Overview:** Async gating; lazy regen, streak bonuses.
- **Public Interface:** async def consume_heart(player_id: UUID, amount: int=1) -> EnergyConsumeResult; etc. (9 methods).
- **Dependencies:** ConfigProtocol (regen), LoggerProtocol, ErrorServiceProtocol, PlayerServiceProtocol; EnergyStateRepositoryProtocol, Redis (idempotency).
- **Data Owned:** energy_states (shared); Redis keys (bonus:{player_id}:{key}).
- **Config Keys:** energy.regen_interval_minutes: int=30; energy.streak_reward_threshold_7: int=1.
- **Error Codes:** FORBIDDEN_INSUFFICIENT_ENERGY (403).
- **Cross-Module Flows:** Called by match (consume/refund), ads/events (bonuses); calls player (state access).
- **Key Types:** EnergyInfo (current, time_to_next), BonusSource Enum (AD_REWARD, etc.).

### 3.5 Wave 2: Auth Module
- **Overview:** Dual: JWT (humans), API keys (bots); rate limiting.
- **Public Interface:** async def authenticate(username: str, password: str) -> AuthResult; def hash_password(password: str) -> str (sync); etc. (12 methods).
- **Dependencies:** ConfigProtocol (JWT secret), LoggerProtocol, ErrorServiceProtocol, PlayerServiceProtocol; repositories (Session/ApiKey/Password); Redis (limits).
- **Data Owned:** sessions, api_keys; Redis counters.
- **Config Keys:** auth.jwt_secret: str; auth.rate_limit_requests: int=100.
- **Error Codes:** AUTH_TOKEN_INVALID (401), RATE_LIMIT_API_KEY (429).
- **Cross-Module Flows:** Middleware in API; calls player (verifications).
- **Key Types:** AuthResult (tokens), RateLimitStatus (remaining, reset_at).

### 3.6 Wave 3: Vault Module
- **Overview:** Async artifact CRUD; sync raid/collection logic.
- **Public Interface:** async def add_artifact(player_id: UUID, artifact_type_id: str, source: str) -> VaultArtifact; async def attempt_raid(attacker_id: UUID, defender_id: UUID) -> RaidResult; etc. (17 methods).
- **Dependencies:** ConfigProtocol (raid chance), LoggerProtocol, ErrorServiceProtocol, PlayerServiceProtocol; repositories (Artifacts/Definitions/Shields/RaidLogs).
- **Data Owned:** vault_artifacts, artifact_definitions, vault_shields, raid_logs.
- **Config Keys:** vault.raid_success_base_chance: float=0.5; vault.max_artifacts_per_player: int=100.
- **Error Codes:** NOT_FOUND_ARTIFACT (404), FORBIDDEN_VAULT_PROTECTED (403).
- **Cross-Module Flows:** Called by events (rewards); calls player (existence).
- **Key Types:** VaultArtifact (id, type_id, rarity), ArtifactRarity Enum, RaidResult (success, artifact).

### 3.7 Wave 3: Special_Gems Module
- **Overview:** Pure sync effects; separation of calculation/application.
- **Public Interface:** def calculate_effect(board: BoardState, position: Position, target_color: Optional[GemType]) -> SpecialGemEffect; etc. (6 methods).
- **Dependencies:** ConfigProtocol (radii), LoggerProtocol, ErrorServiceProtocol, ScoringServiceProtocol.
- **Data Owned:** Stateless.
- **Config Keys:** special_gems.radial_bomb_radius: int=1; special_gems.chain_reaction_enabled: bool=True.
- **Error Codes:** VALIDATION_INVALID_INPUT (400).
- **Cross-Module Flows:** Called by board_gen (validation), match (activation); calls scoring (bonuses).
- **Key Types:** SpecialGemEffect (positions, bonus), FusionType Enum.

### 3.8 Wave 4: Board_Gen Module
- **Overview:** Pure sync procedural gen; tuning for psychology (cascade, near-miss).
- **Public Interface:** def generate_board(seed: int, options: Optional[BoardGenOptions]) -> GeneratedBoard; etc. (5 methods).
- **Dependencies:** ConfigProtocol (potentials), LoggerProtocol, ErrorServiceProtocol, BoardServiceProtocol, SpecialGemsServiceProtocol.
- **Data Owned:** Stateless.
- **Config Keys:** board_gen.default_cascade_potential: float=0.5; board_gen.max_generation_attempts: int=100.
- **Error Codes:** INTERNAL_UNEXPECTED (500, max attempts).
- **Cross-Module Flows:** Called by match (creation); calls board/special_gems (validation).
- **Key Types:** GeneratedBoard (state, metadata), BoardGenOptions (cascade, specials).

### 3.9 Wave 5: Match Module
- **Overview:** Async orchestration; state machine (PENDING/IN_PROGRESS/COMPLETED).
- **Public Interface:** async def create_match(player1_id: UUID, player2_id: UUID, board_seed: Optional[int]) -> MatchState; async def submit_move(match_id: UUID, player_id: UUID, move: Move) -> MoveSubmissionResult; etc. (10 methods).
- **Dependencies:** ConfigProtocol (moves), LoggerProtocol, ErrorServiceProtocol, DataContextProtocol; services (BoardGen/Board/Scoring/SpecialGems/Player/Energy); repositories (Matches/Moves).
- **Data Owned:** matches (JSONB boards), match_moves.
- **Config Keys:** match.moves_per_player: int=20; match.timeout_hours: int=24.
- **Error Codes:** CONFLICT_MATCH_ALREADY_COMPLETED (409).
- **Cross-Module Flows:** Called by matchmaking/events; calls lower waves (board ops, scoring, energy consume).
- **Key Types:** MatchState (players, status), MatchStatus Enum.

### 3.10 Wave 6: Events Module
- **Overview:** Async lifecycle; Redis leaderboards, rewards.
- **Public Interface:** async def join_event(event_id: UUID, player_id: UUID) -> EventParticipant; async def finalize_event(event_id: UUID) -> EventFinalizationResult; etc. (15 methods).
- **Dependencies:** ConfigProtocol (capacities), LoggerProtocol, ErrorServiceProtocol, DataContextProtocol; services (Vault/Energy/Match/Player); repositories (Events/Participants); Redis (sorted sets).
- **Data Owned:** events, event_participants; Redis keys.
- **Config Keys:** events.max_participants_flash: int=100; events.min_matches_for_rewards: int=3.
- **Error Codes:** CONFLICT_EVENT_AT_CAPACITY (409).
- **Cross-Module Flows:** Called by ads; calls vault (artifacts), energy (costs), match (recording), player (ELO).
- **Key Types:** Event (type, status), EventType Enum, ScoringType Enum.

### 3.11 Wave 6: Matchmaking Module
- **Overview:** Async ELO pairing; Redis queues with expansion.
- **Public Interface:** async def join_queue(player_id: UUID, pool_type: PoolType=MIXED) -> QueueEntry; etc. (7 methods).
- **Dependencies:** ConfigProtocol (ranges), LoggerProtocol, ErrorServiceProtocol, MatchServiceProtocol, PlayerServiceProtocol; MatchmakingQueueRepositoryProtocol (Redis).
- **Data Owned:** Redis queues/player hashes (transient, TTL).
- **Config Keys:** matchmaking.initial_elo_range: int=50; matchmaking.queue_timeout_seconds: int=300.
- **Error Codes:** CONFLICT_ALREADY_IN_QUEUE (409).
- **Cross-Module Flows:** Called by API; calls match (creation), player (ELO).
- **Key Types:** QueueEntry (position, estimate), PoolType Enum.

### 3.12 Wave 7: Ads Module
- **Overview:** Async impressions; ad-free grants, bot attributions.
- **Public Interface:** async def request_interstitial(player_id: UUID, trigger: str, match_id: Optional[UUID]) -> AdRequest; etc. (16 methods).
- **Dependencies:** ConfigProtocol (cooldowns), LoggerProtocol, ErrorServiceProtocol, DataContextProtocol; services (Player/Events/Energy); AdRepositoryBundle.
- **Data Owned:** ad_requests, ad_impressions, ad_free_statuses.
- **Config Keys:** ads.interstitial_cooldown_minutes: int=5; ads.bot_attribution_share_percent: float=30.0.
- **Error Codes:** RATE_LIMIT_AD_COOLDOWN (429).
- **Cross-Module Flows:** Called by payments (grants), bot_earnings (attributions); calls energy (rewards), player/events.
- **Key Types:** AdRequest (status), AdType Enum.

### 3.13 Wave 8: Bot_Earnings Module
- **Overview:** Async revenue sharing; sync from ads.
- **Public Interface:** async def sync_attributions(bot_player_id: UUID) -> AttributionSyncResult; async def request_payout(bot_player_id: UUID, owner_player_id: UUID) -> PayoutRequest; etc. (13 methods).
- **Dependencies:** ConfigProtocol (thresholds), LoggerProtocol, ErrorServiceProtocol, DataContextProtocol, PlayerServiceProtocol, AdServiceProtocol; repositories (Earnings/Attributions/Payouts).
- **Data Owned:** bot_earnings_ledger, bot_attribution_entries, bot_payout_requests, bot_earnings_daily.
- **Config Keys:** bot_earnings.minimum_payout_cents: int=1000; bot_earnings.sync_lookback_days: int=7.
- **Error Codes:** FORBIDDEN_NOT_BOT (403), CONFLICT_PENDING_PAYOUT_EXISTS (409).
- **Cross-Module Flows:** Called by API; calls ads (pull), player (verifications).
- **Key Types:** EarningsBalance (current, lifetime), PayoutStatus Enum.

### 3.14 Wave 8: Payments Module
- **Overview:** Async purchase lifecycle; provider abstraction.
- **Public Interface:** async def validate_purchase(player_id: UUID, receipt: PurchaseReceipt) -> PurchaseResult; etc. (8 methods).
- **Dependencies:** ConfigProtocol (secrets), LoggerProtocol, ErrorServiceProtocol, DataContextProtocol, PlayerServiceProtocol, AdServiceProtocol; repositories (Products/Intents/Purchases); PaymentProviderProtocol.
- **Data Owned:** products, purchase_intents, purchases, receipt_validations, refund_notifications.
- **Config Keys:** payments.product_id: str="ad_free"; payments.apple_shared_secret: str.
- **Error Codes:** VALIDATION_RECEIPT_INVALID (400).
- **Cross-Module Flows:** Called by API; calls player (verifications), ads (ad-free grant/revoke).
- **Key Types:** PurchaseResult (status), PaymentProvider Enum.

### 3.15 Wave 9: API Module
- **Overview:** Presentation; 55 REST endpoints + health + WebSocket delegating to modules.
- **Public Interface:** Route groups: /api/v1/auth (8 endpoints), /api/v1/matches (8), /ws (1); etc.
- **Dependencies:** ConfigProtocol (rate limits), LoggerProtocol, ErrorServiceProtocol; all module protocols (AuthServiceProtocol, etc.).
- **Data Owned:** Transient (in-memory).
- **Config Keys:** api.rate_limit.requests_per_minute: int=60; websocket.heartbeat_interval_seconds: int=30.
- **Error Codes:** AUTH_TOKEN_INVALID (401), RATE_LIMIT_EXCEEDED (429).
- **Cross-Module Flows:** Terminal; calls all (e.g., match for /matches, ads for /ads).
- **Key Types:** ApiResponse[T] (success, data, error), BotHint (strategic, for bot responses).

## 4. Frontend Skeleton (iOS Focus; Web Mirrors)

### 4.1 Phase 1: Core Loop
- **Components:** APIClient (async HTTP/WS, auth interceptor), BackendContract (Codable structs: BoardState, MatchState, etc.), MatchView (SKScene: grid nodes, gesture recognizer for swaps).
- **Dependencies:** Backend API schemas (surveyed pre-implementation).
- **Interfaces:** Endpoint enum (e.g., .createMatch(player1: UUID, player2: UUID) -> MatchState).
- **Render Flows:** Receive BoardState JSON → map to SKSpriteNodes (gem textures); submit Move → await MoveProcessingResult → sequence animations.
- **LLM Affordances:** Structs for schema gen; event streams for simulation (swap → match → cascade).

### 4.2 Phase 2: Juice
- **Components:** AnimationSequencer (chains backend events: swap anim → particle bursts → audio cues), IntensitySystem (scales based on match size/chain: volume, haptics, shaders).
- **Dependencies:** SpriteKit (SKAction, SKEmitterNode), AVAudioPlayer, UIImpactFeedbackGenerator.
- **Interfaces:** Event handlers (e.g., onMatch(result: MatchResult) → burst particles).
- **Render Flows:** Backend cascade steps → timed sequences (gravity drops, fills); adaptive music (intensity → track modulation).
- **Visual Schema:** All gem colors, shapes, shader params, particle colors, and background tints loaded from `assets/config/visual_theme.json` via `VisualThemeBase` interface. Injected into all Flame components via constructor and into widgets via Provider.
- **LLM Affordances:** Parametric shaders (e.g., GLSL for gems); procedural audio params for gen.

### 4.3 Phase 3: Psychology
- **Components:** PostMatchView (SwiftUI: score comparison, near-miss highlights), RevengeView (timer, prompt).
- **Dependencies:** Phase 1/2; backend flags (near_miss: bool).
- **Interfaces:** DTOs (MatchSummary, RaidResult).
- **Render Flows:** Loss → animated raid (artifact fly-out); revenge countdown → WS updates.
- **LLM Affordances:** Screen flows as state machines; tunable params (near-miss threshold) for A/B sim.

### 4.4 Phase 4: Persistence
- **Components:** VaultView (SwiftUI grid, procedural artifact gen: shape/color/rarity compositing), EnergyView (heart icons, regen timer).
- **Dependencies:** Phase 1; backend VaultSummary DTO.
- **Interfaces:** /api/v1/vault endpoints.
- **Render Flows:** Artifact list → dynamic SKShapes (procedural); shield activation → overlay anim.
- **LLM Affordances:** Gen funcs (e.g., artifactFromDefinition(type_id: str) → SKNode); idempotency for bonuses.

### 4.5 Phase 5: Monetization
- **Components:** AdIntegration (AdMob wrappers: interstitial/rewarded), PurchaseManager (StoreKit: initiate/validate $1).
- **Dependencies:** Phase 1; backend Payments DTOs.
- **Interfaces:** /api/v1/payments, /api/v1/ads.
- **Render Flows:** Rewarded ad complete → grant hearts (WS push); ad-free → toggle dark mode (UserDefaults).
- **LLM Affordances:** Mock providers for testing; revenue sim via configs.

### 4.6 Phase 6: LiveOps
- **Components:** EventView (list/join, leaderboards), ABTesting (remote configs for psych params).
- **Dependencies:** All phases; backend Events DTOs.
- **Interfaces:** /api/v1/events, WS subscriptions.
- **Render Flows:** Flash event → timed UI (banners, rewards); leaderboards → sorted lists.
- **LLM Affordances:** Config overrides for variant gen; event schemas for procedural content.

## 5. Integration Points
- **Client-Backend:** All via API; clients map DTOs to views (e.g., BoardState → grid render).
- **LLM Bot Paths:** Auth (create_api_key) → Matchmaking (join_queue) → Matches (get_match_state with hints) → Moves (submit_move).
- **Error Handling:** Unified AppError mapping (HTTP codes to UI alerts).
- **Data Flows:** Persistence (PostgreSQL writes) → Cache (Redis reads) → API (JSON) → Client (Codable/JSON parse).
- **Testing Affordances:** Protocols for mocking; pure sync funcs for unit sim.

## 6. Risks & Analysis Hooks (LLM-Oriented)
- **Dependency Cycles:** None (DAG enforced); survey via wave traversal.
- **Schema Drift:** Use BackendContract for validation; LLM can diff types.
- **Performance:** NumPy/Redis hotspots; profile via code_execution tool.
- **Ethical Scans:** Psychology params (e.g., near_miss_factor); flag for addiction analysis.

Here is the addendum content extracted and formatted cleanly in Markdown, exactly as it was provided:

#### Consolidated Module Map with Responsibilities
| Module          | Responsibilities                                                                 |
|-----------------|----------------------------------------------------------------------------------|
| Player          | Manage accounts (HUMAN/BOT), ELO calculations, stats aggregation, energy state initialization/updates. |
| Board           | Pure grid operations: creation, swaps, match detection, gravity, cascades, validation. |
| Scoring         | Calculate points from matches/cascades/specials using multipliers.               |
| Energy          | Handle heart consumption/regeneration, streak bonuses, refunds.                 |
| Auth            | Dual authentication (JWT/API keys), sessions, rate limiting.                    |
| Vault           | Artifact CRUD, raids (probabilistic), shields, collection progress.             |
| Special_Gems    | Compute/apply special effects, fusions, chain reactions.                        |
| Board_Gen       | Procedural board generation with tuning (cascade/near-miss), reshuffles.        |
| Match           | Orchestrate versus matches: lifecycle, move processing, scoring, abandonment.   |
| Events          | Manage event lifecycles: participation, scoring, leaderboards, rewards.         |
| Matchmaking     | ELO-based queuing/pairing with range expansion.                                 |
| Ads             | Ad placements/impressions, ad-free status, attributions.                        |
| Bot_Earnings    | Revenue sharing for bots: attributions, payouts, reports.                       |
| Payments        | $1 purchase validation, refunds, ad-free integration.                           |
| API             | Expose endpoints/WS; delegate to modules, middleware (auth/rate).               |
| iOS Frontend (Phases) | Render board/animations/UI; API integration (no logic).                   |

#### Full Runtime Dependency Graph
Textual adjacency list (runtime calls/imports; bidirectional for flows). Can be visualized as DOT graph for LLM processing.

- Config → All (injected for params)
- Logger → All (logging)
- Errors → All (error factory)
- Player → Auth (verifications), Energy (state access), Match (ELO/stats), Matchmaking (ELO), Vault/Events/Ads/Payments/Bot_Earnings (existence)
- Board → Scoring (match results), Special_Gems (effects), Board_Gen (validation), Match (processing)
- Scoring → Special_Gems (bonuses), Match (move scores)
- Energy → Match (consume/refund), Events (costs/bonuses), Ads (rewards)
- Auth → API (middleware), Match (player_id extraction)
- Vault → Events (rewards)
- Special_Gems → Board_Gen (validation), Match (activation)
- Board_Gen → Match (creation)
- Match → Matchmaking (creation), Events (recording), API (endpoints)
- Events → Ads (opportunities)
- Matchmaking → API (endpoints)
- Ads → Payments (grants/revokes), Bot_Earnings (attributions)
- Bot_Earnings → API (endpoints)
- Payments → API (endpoints)
- API → All modules (delegation)
- iOS Frontend → API (REST/WS calls)

No cycles; topological order matches waves.

#### Data Flow Across Modules
Key scenarios as sequences (data entities in italics):

1. **Match Creation Flow:**
   - Matchmaking: _Player ELO_ from Player → Find pair → Call Match.create_match (_player_ids, seed_) → Board_Gen.generate_board → Energy.consume_heart → Persist _MatchState_ (PostgreSQL) → Return to API/Frontend.

2. **Move Submission Flow:**
   - API: Receive _Move_ → Auth.validate → Match.submit_move → Board.process_move (_cascades_) → Special_Gems.apply_effect → Scoring.calculate_move_score → Player.record_match_result (_stats_) → Persist _MoveRecord_ → WS push _MatchState update_.

3. **Ad Impression to Bot Earnings:**
   - Ads.record_impression (_AdImpression_) → Persist (PostgreSQL) → Bot_Earnings.sync_attributions → Pull _BotAdAttributionReport_ from Ads → Update _EarningsLedger_ (PostgreSQL) → API exposes _EarningsBalance_.

4. **Event Reward Distribution:**
   - Events.finalize_event → Redis leaderboard sync → Vault.add_artifact (_rewards_) → Energy.grant_bonus_hearts → Player.update_elo → Persist all.

5. **Purchase Flow:**
   - Payments.validate_purchase (_Receipt_) → Ads.grant_ad_free_status → Persist _PurchaseRecord_ (PostgreSQL) → Frontend toggles UI.

Frontend Flows: API response (_DTOs_) → Map to views (e.g., _BoardState_ → SKNodes) → User input (_Move_) → API request.

#### Shared Type Registry Summary
Aggregated from all modules; categorized. Locations: src/modules/<module>/types.py (backend), BackendContract.swift (frontend mappings).

- **Core/Board Types (Shared):** BoardState (np.ndarray), Position (tuple[int,int]), Move (tuple[Position,Position]), MatchResult (list[MatchGroup]), GemType Enum (6 colors + specials + EMPTY).
- **Player-Related:** Player (id, type, elo), PlayerType Enum (HUMAN,BOT), PlayerStats (wins, highest_score), EnergyState (hearts, streak), EnergyInfo (calculated regen).
- **Match Types:** MatchState (players, boards, status), MatchStatus Enum (PENDING,IN_PROGRESS,...), MoveProcessingResult (cascades, effects), MoveScore (total, breakdown).
- **Special/Scoring:** SpecialGemEffect (positions, bonus), FusionType Enum, SpecialGemBonus.
- **Vault/Events:** VaultArtifact (id, rarity), ArtifactRarity Enum, Event (id, type, status), EventType Enum (FLASH,...), ScoringType Enum.
- **Auth/Monetization:** AuthResult (tokens), AdRequest (status), AdType Enum, EarningsBalance, PayoutStatus Enum, PurchaseResult.
- **Frontend Mappings:** Codable equivalents (e.g., BoardStateStruct mirroring np.array as [[Int]]).

#### Cross-Module Interface Map
Table of protocols (DI interfaces); implementer = module providing service, consumers = callers.

| Protocol                  | Methods (Summary)                          | Implementer     | Consumers                                                                 |
|---------------------------|--------------------------------------------|-----------------|---------------------------------------------------------------------------|
| PlayerServiceProtocol     | 14 async (create_player, update_elo, ...)  | Player          | Auth, Energy, Match, Matchmaking, Vault, Events, Ads, Payments, Bot_Earnings |
| BoardServiceProtocol      | 4 sync (detect_matches, has_valid_moves, ...) | Board        | Board_Gen, Scoring (types only), Special_Gems (types), Match              |
| ScoringServiceProtocol    | 1 sync (calculate_special_gem_bonus)       | Scoring         | Special_Gems                                                              |
| EnergyServiceProtocol     | 9 async (consume_heart, ...)               | Energy          | Match, Events, Ads                                                        |
| AuthServiceProtocol       | 12 methods (authenticate, ...)             | Auth            | API (middleware), Match                                                   |
| VaultServiceProtocol        | 17 async (add_artifact, attempt_raid, ...)| Vault           | Events                                                                    |
| SpecialGemsServiceProtocol| 1 sync (is_special_gem)                    | Special_Gems    | Board_Gen                                                                 |
| BoardGenServiceProtocol   | 5 sync (generate_board, ...)               | Board_Gen       | Match                                                                     |
| MatchServiceProtocol      | 10 async (create_match, ...)               | Match           | Matchmaking, Events                                                       |
| EventServiceProtocol      | 15 async (join_event, ...)                 | Events          | Ads, API                                                                  |
| MatchmakingServiceProtocol| 7 async (join_queue, ...)                  | Matchmaking     | API                                                                       |
| AdServiceProtocol         | 16 async (request_interstitial, ...)       | Ads             | Payments, Bot_Earnings                                                    |
| BotEarningsServiceProtocol  | 13 async (sync_attributions, ...)         | Bot_Earnings    | API                                                                       |
| PaymentProviderProtocol   | Abstract (validate_receipt, ...)           | Payments        | - (external)                                                              |
| All *Protocol in API      | Mirror module interfaces                   | Respective modules | API (injection)                                                        |

**END OF SKELETON**