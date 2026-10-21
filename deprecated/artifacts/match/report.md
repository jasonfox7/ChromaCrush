# Module Report: match

## Header
- **Author:** Scout Agent (match)
- **Date:** 2026-02-05

## Summary

The **match** module was designed as the central game coordinator for ChromaCrush's asynchronous versus mode. Key outcomes:

1. **Complete State Machine Design** - Defined the match lifecycle with four states: PENDING, IN_PROGRESS, COMPLETED, and ABANDONED. Transitions are triggered by move submission, completion of both players' moves, forfeit actions, or timeout.

2. **Asynchronous Fairness Model** - Both players play the same board independently via deterministic seeded generation. Each player gets 20 moves (configurable) and the winner is determined by final score comparison. This enables true asynchronous PvP without requiring simultaneous play.

3. **Comprehensive Public Interface** - Designed 8 public methods covering the complete match lifecycle:
   - `create_match` - Creates a new match between two players with atomic energy consumption
   - `submit_move` - Validates, executes, and records player moves with full cascade resolution
   - `get_match_state` - Retrieves current match state
   - `get_player_board` - Gets a player's current board state
   - `forfeit_match` - Allows player to forfeit, awarding victory to opponent
   - `get_match_history` - Retrieves paginated match history
   - `get_move_history` - Retrieves move records for replay/verification
   - `abandon_stale_matches` - Background operation for timeout handling

4. **12 Edge Cases Resolved** - Documented handling for: simultaneous completion, draws, forfeit race conditions, board deadlock, atomic transaction failure, concurrent match restrictions, timeout handling, invalid moves, Chromatic Orb targeting, replay verification, timestamp validation, and special gem fusion.

5. **Data Layer Design** - Defined two owned tables (`matches`, `match_moves`) with appropriate indexes and repository interfaces (`MatchRepository`, `MatchMoveRepository`).

6. **Integration Points** - Documented all 7 dependency module integrations with specific method calls and data flows.

## Alternatives Considered

### 1. Real-Time vs Asynchronous Versus Mode

**Considered:** Implementing real-time turn-based versus where both players are online simultaneously, taking turns.

**Rejected:** The GDD explicitly specifies asynchronous versus mode where players can complete their moves at any time within the timeout window. Real-time would require websocket infrastructure, presence tracking, and turn timers - significantly more complexity with different UX. The async model allows casual mobile play patterns.

### 2. Shared Board vs Individual Boards

**Considered:** Having both players share a single board state that evolves based on combined moves.

**Rejected:** This would require real-time synchronization and make asynchronous play impossible. The GDD's async fairness model requires identical starting boards that evolve independently. Each player's board state is tracked separately in the database.

### 3. Move Validation in Board Module vs Match Module

**Considered:** Delegating all move validation (including move count, participant check) to the board module.

**Rejected:** Move validation involves match-specific context (moves remaining, player participation, match status) that the board module shouldn't know about. The board module handles grid-level validation (adjacent positions, valid gem swap), while match module handles match-level validation. This maintains single responsibility.

### 4. Transaction Scope for Match Creation

**Considered:** Checking energy first, then creating match in a separate transaction.

**Rejected:** This would allow race conditions where a player's energy is checked, they join another match, and then the original match creation succeeds with insufficient energy. Atomic transaction ensures energy consumption and match creation succeed or fail together.

### 5. ELO Calculation in Match Module

**Considered:** Implementing ELO calculation logic directly in the match module.

**Rejected:** The player module already owns player stats and ratings per its artifact. ELO calculation is a player concern. Match module calls `calculate_elo_change` and `update_elo` through the player service interface, maintaining proper module boundaries.

### 6. Separate Move Processing Service

**Considered:** Creating a dedicated `MoveProcessingService` to orchestrate board, scoring, and special gems.

**Rejected:** The match module is already the coordinator for versus gameplay. Adding another service would create unnecessary indirection. The match module's `submit_move` method orchestrates the existing services without reimplementing their logic.

## Risks

### R-1: Cascade Chain Performance (Medium)

**Risk:** Long cascade chains with multiple special gem activations could be computationally expensive, potentially causing timeout issues in async contexts.

**Mitigation:** The board and scoring modules handle pure computation (synchronous). Match module awaits only database operations. Performance testing should verify cascade processing stays under acceptable thresholds. Consider adding a maximum cascade depth configuration if needed.

### R-2: Concurrent Move Submission Race Conditions (Low)

**Risk:** Two players submitting moves simultaneously could cause database contention or inconsistent state.

**Mitigation:** Each player updates only their own fields (`playerN_board_state`, `playerN_score`, etc.). The database transaction ensures atomic updates. Match completion check happens after update, so both moves are processed correctly even if simultaneous.

### R-3: Deadlock Reshuffle Fairness (Low)

**Risk:** If deadlock reshuffle produces different board characteristics for one player vs another (though starting from same seed), it could affect fairness.

**Mitigation:** Reshuffle uses deterministic seeds derived from match seed + player ID + move number. Both players would get the same reshuffle behavior on the same board state at the same move number. The `board_gen` module's `regenerate_from_deadlock` preserves special gems.

### R-4: Move History Storage Growth (Medium)

**Risk:** Storing full `board_before` and `board_after` JSONB for every move (40 moves per match) could cause database growth issues at scale.

**Mitigation:** Board state is 8x8 = 64 cells, each a small integer. ~500 bytes per board state, ~1KB per move record, ~40KB per match. Acceptable for reasonable scale. Consider archival strategy for completed matches if storage becomes a concern.

### R-5: Energy Consumption Atomicity Across Services (Medium)

**Risk:** The `energy_service.consume_heart` call is inside the match module's transaction, but energy module has its own data ownership. Cross-module transactional consistency could be fragile.

**Mitigation:** The data layer guidance specifies transaction boundaries at service level. The match module's `create_match` owns the transaction and calls energy consumption within it. Energy module's repository operates on the same database connection/session passed through the data context.

### R-6: Special Gem Integration Complexity (Medium)

**Risk:** The interaction between match module, board module, scoring module, and special_gems module during move processing has multiple handoffs that could introduce bugs.

**Mitigation:** Clear sequencing documented in the artifact: (1) board processes move and cascade, (2) special gems calculates effects for triggered gems, (3) scoring calculates points including special bonuses. Each module has a single responsibility. Comprehensive CLI harness will enable testing of complex scenarios.

## Dependencies & Sequencing Notes

### Build Order Position

The match module is **Wave 5** in the dependency graph - the last wave before higher-level features (matchmaking, vault, events).

### Direct Dependencies (Must Be Complete First)

| Module | Wave | Required For |
|--------|------|--------------|
| `board_gen` | Wave 4 | Board generation for new matches, deadlock reshuffle |
| `board` | Wave 1 | Move processing, cascade resolution, valid move detection |
| `scoring` | Wave 2 | Score calculation from move results |
| `special_gems` | Wave 3 | Special gem effect calculation, fusion handling |
| `player` | Wave 1 | Player existence validation, username lookup, stats updates, ELO |
| `auth` | Wave 2 | Player authentication (if verifying requests) |
| `energy` | Wave 2 | Energy check and consumption |

### Artifact Dependencies

Before implementing match module, the coder must have access to:
- `board_gen` artifact for `BoardGenServiceProtocol` interface
- `board` artifact for `BoardServiceProtocol` and `MoveProcessingResult`
- `scoring` artifact for `ScoringServiceProtocol` and `MoveScore`
- `special_gems` artifact for `SpecialGemsServiceProtocol` and `SpecialGemEffect`
- `player` artifact for `PlayerServiceProtocol`
- `energy` artifact for `EnergyServiceProtocol`

All dependency artifacts are now complete (confirmed during design).

### Core Services Required

- `ConfigProtocol` - For match configuration values
- `LoggerProtocol` - For event logging
- `ErrorServiceProtocol` - For standardized error handling
- `DataContextProtocol` - For transaction management

### Coordination Notes

1. **Repository Implementations:** The data layer team must implement `MatchRepository` and `MatchMoveRepository` before match module implementation can be fully tested. Schema migrations should be created early in Phase 2.

2. **CLI Commands:** The match CLI commands require all dependency services to be instantiated. CLI composition root must wire all 7 dependency services plus the match service.

3. **Testing Dependencies:** Test fixtures will need mock implementations of all 7 dependency service protocols. The testing agent should coordinate mock creation across modules.

4. **Integration Testing:** Match module integration tests should exercise the full move submission flow including board, scoring, and special_gems. Consider creating a dedicated integration test suite.

### Downstream Dependents

The following modules will depend on match module (future work):
- `matchmaking` - Will create matches via `MatchService.create_match`
- `vault` - May read match history for rewards/achievements
- `events` - May read match state for event triggers

These modules should not be designed until match module artifact is finalized.
