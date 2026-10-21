# Match Module Implementation Document

**Module:** match
**Phase:** 2.2
**Author:** Documentation Agent
**Date:** 2026-02-06

---

## 1. Summary

The match module orchestrates two-player asynchronous versus matches for ChromaCrush. It manages the full lifecycle: creation, move submission, board state synchronization, scoring, special gem processing, forfeit handling, match history retrieval, and stale match abandonment. All public methods are async (`async def`) because they involve database operations and cross-module coordination. Each player maintains their own board state, score, and move count. The service enforces energy requirements, concurrent match limits, move validity, and timeout deadlines. Match completion triggers winner determination, ELO updates, and player statistics finalization.

## 2. Files Created

### Module Code (`src/modules/match/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Exports `MatchService`, `MatchServiceProtocol`, and all domain types |
| `types.py` | Domain types: `MatchStatus`, `MatchType`, `PlayerMatchState`, `MatchState`, `MoveSubmissionResult`, `MatchSummary`, `MoveRecord`, `PlayerBoardState` |
| `protocols.py` | `MatchServiceProtocol` (9 methods), `MatchRepositoryProtocol` (7 methods), `MatchMoveRepositoryProtocol` (3 methods), plus minimal dependency protocols |
| `dto.py` | DTOs for repository operations: `MatchCreate`, `MatchUpdate`, `MoveCreate`, `PaginatedResult[T]` |
| `service.py` | `MatchService` — full implementation (1197 lines) |

### Data Layer (`src/data/`)
| File | Purpose |
|------|---------|
| `models/match.py` | `MatchModel` ORM — matches table (50 columns) |
| `models/match_move.py` | `MatchMoveModel` ORM — match_moves table (19 columns) |
| `repositories/match_repository.py` | `SQLAlchemyMatchRepository` (308 lines), `SQLAlchemyMatchMoveRepository` (133 lines) |
| `protocols/match_repository.py` | Repository protocol interfaces |
| `migrations/versions/005_match_tables.py` | Alembic migration for matches and match_moves tables |

### CLI (`src/cli/commands/`)
| File | Purpose |
|------|---------|
| `match_commands.py` | Click group "match" with 9 commands (776 lines) |

### Tests (`tests/unit/modules/match/`)
| File | Purpose |
|------|---------|
| `test_match_service.py` | 62 tests across 10 test classes covering all public methods and error paths (1824 lines) |

## 3. Deviations from Artifact
Not assessed — document produced from code examination only.

## 4. Public Interface

### `MatchService`

```python
def __init__(
    self,
    config: ConfigProtocol,
    logger: LoggerProtocol,
    errors: ErrorServiceProtocol,
    data_ctx: DataContextProtocol,
    board_gen_service: BoardGenServiceProtocol,
    board_service: BoardServiceProtocol,
    scoring_service: ScoringServiceProtocol,
    special_gems_service: SpecialGemsServiceProtocol,
    player_service: PlayerServiceProtocol,
    auth_service: AuthServiceProtocol,
    energy_service: EnergyServiceProtocol,
    match_repository: MatchRepositoryProtocol,
    match_move_repository: MatchMoveRepositoryProtocol,
) -> None
```

#### Service Methods

| Method | Signature | Return Type | Purpose |
|--------|-----------|-------------|---------|
| `create_match` | `(player1_id, player2_id, board_seed=None, match_type=MatchType.STANDARD)` | `MatchState` | Create new match, generate board, consume energy |
| `submit_move` | `(match_id, player_id, move)` | `MoveSubmissionResult` | Process move, update score, handle completion |
| `get_match` | `(match_id)` | `MatchState` | Retrieve current match state |
| `get_match_state` | `(match_id, for_player_id=None)` | `MatchState` | Get match state with optional participant validation |
| `get_player_board` | `(match_id, player_id)` | `PlayerBoardState` | Get player's board, moves, score |
| `get_active_matches` | `(player_id)` | `list[MatchState]` | List active (pending/in_progress) matches |
| `forfeit_match` | `(match_id, player_id)` | `MatchState` | Forfeit, declare opponent winner |
| `get_match_history` | `(player_id, limit=20, offset=0, status=None)` | `PaginatedResult[MatchSummary]` | Paginated match history |
| `get_move_history` | `(match_id, player_id=None)` | `list[MoveRecord]` | Move history, optionally filtered |
| `abandon_stale_matches` | `()` | `int` | Abandon timed-out matches, return count |

### Protocols

| Protocol | Methods | Purpose |
|----------|---------|---------|
| `MatchServiceProtocol` | 9 public methods listed above | Module interface for presentation layer |
| `MatchRepositoryProtocol` | create, find_by_id, update, find_active_by_player, find_by_player, find_stale_matches, bulk_abandon | Match persistence |
| `MatchMoveRepositoryProtocol` | create, find_by_match, count_by_player | Move record persistence |
| `BoardServiceProtocol` | process_move, has_valid_moves | Minimal board service interface |
| `ScoringServiceProtocol` | calculate_move_score | Minimal scoring service interface |

## 5. Domain Types

### Enums

| Type | Values |
|------|--------|
| `MatchStatus` | PENDING, IN_PROGRESS, COMPLETED, ABANDONED |
| `MatchType` | STANDARD, COMPETITIVE, CASUAL, TUTORIAL |

### Data Classes

| Type | Key Attributes | Mutable |
|------|----------------|---------|
| `PlayerMatchState` | player_id, player_username, score, moves_made, moves_remaining, current_board, longest_chain, special_gems_created, special_gems_activated, total_gems_cleared, finished_at | Yes |
| `MatchState` | match_id, board_seed, initial_board, status, match_type, player1, player2, winner_id, forfeit_by, created_at, started_at, completed_at, timeout_at | Yes |
| `MoveSubmissionResult` | match_state, move_result, score_result, special_effects, points_earned, move_number, moves_remaining, match_completed, player_finished, winner_id | No |
| `MatchSummary` | match_id, opponent_id, opponent_username, player_score, opponent_score, won (bool or None), status, match_type, created_at, completed_at | No |
| `MoveRecord` | move_number, player_id, move, board_before, board_after, score_earned, chain_count, gems_cleared, special_gems_created, special_gems_activated, timestamp | No |
| `PlayerBoardState` | player_id, board, moves_made, moves_remaining, score, has_valid_moves | No |

#### `MatchState` Methods

- `get_player_state(player_id: PlayerId) -> PlayerMatchState` — raises ValueError if not participant
- `get_opponent_state(player_id: PlayerId) -> PlayerMatchState` — raises ValueError if not participant
- `both_finished -> bool` — property, True if both players have 0 moves remaining
- `is_participant(player_id: PlayerId) -> bool` — check if player is in match

## 6. DTOs

| DTO | Purpose | Fields |
|-----|---------|--------|
| `MatchCreate` | Create match record | board_seed, initial_board_state, match_type, player1_id, player1_board_state, player1_moves_remaining, player2_id, player2_board_state, player2_moves_remaining, timeout_at |
| `MatchUpdate` | Update match record | Optional: status, player1_board_state, player1_score, player1_moves_made, player1_moves_remaining, player1_longest_chain, player1_finished_at, player2_* equivalents, started_at, completed_at, winner_id, forfeit_by |
| `MoveCreate` | Create move record | match_id, player_id, move_number, from_row, from_col, to_row, to_col, client_timestamp_ms, board_before, board_after, score_earned, chain_count, gems_cleared, special_gems_created, special_gems_activated |
| `PaginatedResult[T]` | Paginated query result | items: list[T], total: int, limit: int, offset: int; property: has_more |

## 7. Data Layer

### ORM Models

#### `MatchModel` (table: matches)
| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK, default gen_random_uuid() | Match identifier |
| board_seed | BigInteger | NOT NULL | Random seed for board generation |
| initial_board_state | JSONB | NOT NULL | Starting board (same for both players) |
| match_type | String(20) | NOT NULL, default 'standard' | Rule set variant |
| status | String(20) | NOT NULL, default 'pending', indexed | Match lifecycle state |
| player1_id | UUID | FK players.id, NOT NULL | First player |
| player1_board_state | JSONB | NOT NULL | Player 1's current board |
| player1_score | Integer | NOT NULL, default 0 | Player 1's score |
| player1_moves_made | Integer | NOT NULL, default 0 | Moves player 1 has made |
| player1_moves_remaining | Integer | NOT NULL, default 20 | Moves player 1 has left |
| player1_longest_chain | Integer | NOT NULL, default 0 | Player 1's best chain |
| player1_finished_at | DateTime(tz) | NULL | When player 1 exhausted moves |
| player2_id | UUID | FK players.id, NOT NULL | Second player |
| player2_board_state | JSONB | NOT NULL | Player 2's current board |
| player2_score | Integer | NOT NULL, default 0 | Player 2's score |
| player2_moves_made | Integer | NOT NULL, default 0 | Moves player 2 has made |
| player2_moves_remaining | Integer | NOT NULL, default 20 | Moves player 2 has left |
| player2_longest_chain | Integer | NOT NULL, default 0 | Player 2's best chain |
| player2_finished_at | DateTime(tz) | NULL | When player 2 exhausted moves |
| winner_id | UUID | FK players.id, NULL | Winning player |
| forfeit_by | UUID | FK players.id, NULL | Forfeiting player |
| created_at | DateTime(tz) | NOT NULL, default now() | Match creation timestamp |
| started_at | DateTime(tz) | NULL | When first move was made |
| completed_at | DateTime(tz) | NULL | When match finished |
| timeout_at | DateTime(tz) | NOT NULL | Deadline for match completion |

**Constraints:**
- CHECK `player1_id != player2_id` (name: check_players_different)

**Indexes:**
- `idx_matches_status` on `status`
- `idx_matches_player1` on `player1_id` WHERE `status IN ('pending', 'in_progress')` (partial)
- `idx_matches_player2` on `player2_id` WHERE `status IN ('pending', 'in_progress')` (partial)
- `idx_matches_timeout` on `timeout_at` WHERE `status = 'in_progress'` (partial)

#### `MatchMoveModel` (table: match_moves)
| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK, default gen_random_uuid() | Move identifier |
| match_id | UUID | FK matches.id ON DELETE CASCADE, NOT NULL, indexed | Parent match |
| player_id | UUID | FK players.id, NOT NULL | Who made the move |
| move_number | Integer | NOT NULL | Sequential move number for player |
| from_row | Integer | NOT NULL | Source row |
| from_col | Integer | NOT NULL | Source column |
| to_row | Integer | NOT NULL | Destination row |
| to_col | Integer | NOT NULL | Destination column |
| client_timestamp_ms | BigInteger | NOT NULL | Client-side timestamp |
| board_before | JSONB | NOT NULL | Board state before move |
| board_after | JSONB | NOT NULL | Board state after cascades |
| score_earned | Integer | NOT NULL | Points from this move |
| chain_count | Integer | NOT NULL | Cascade steps |
| gems_cleared | Integer | NOT NULL | Total gems cleared |
| special_gems_created | JSONB | NOT NULL, default [] | [{row, col, gem_type}, ...] |
| special_gems_activated | JSONB | NOT NULL, default [] | [{row, col}, ...] |
| created_at | DateTime(tz) | NOT NULL, default now() | Server timestamp |

**Constraints:**
- UNIQUE (match_id, player_id, move_number) (name: unique_player_move)

**Indexes:**
- `idx_match_moves_match` on `match_id`
- `idx_match_moves_player` on `(match_id, player_id)`

### Migration: 005_match_tables

Creates both tables with all columns, constraints, and indexes. Uses PostgreSQL-specific JSONB for board state storage. CASCADE delete on match_moves when parent match deleted.

### Repository Implementations

#### `SQLAlchemyMatchRepository`

| Method | Purpose | Notable Implementation Details |
|--------|---------|-------------------------------|
| create | Insert new match | Uses session.flush() to populate defaults (id, created_at) |
| find_by_id | Find by UUID | Returns None if not found |
| update | Update match | Uses dataclasses.fields() to iterate MatchUpdate, only updates non-None values; raises NOT_FOUND_MATCH if missing |
| find_active_by_player | Find pending/in_progress | WHERE (player1_id = X OR player2_id = X) AND status IN ('pending', 'in_progress') |
| find_by_player | Paginated match list | Optional status filter, ORDER BY created_at DESC, returns (items, total_count) |
| find_stale_matches | Find timed-out | WHERE status = 'in_progress' AND timeout_at < cutoff |
| bulk_abandon | Atomic status update | sa_update().where(id.in_(match_ids)).values(status='abandoned'), returns rowcount |

#### `SQLAlchemyMatchMoveRepository`

| Method | Purpose | Notable Implementation Details |
|--------|---------|-------------------------------|
| create | Insert move record | Uses session.flush() to populate id |
| find_by_match | Find moves for match | Optional player_id filter, ORDER BY move_number ASC |
| count_by_player | Count moves | SELECT count(*) WHERE match_id AND player_id |

## 8. Dependencies

### Constructor Dependencies (13 total)

| Dependency | Protocol | Sync/Async | Purpose |
|------------|----------|------------|---------|
| `config` | `ConfigProtocol` | Sync | Configuration values |
| `logger` | `LoggerProtocol` | Sync | Diagnostic logging |
| `errors` | `ErrorServiceProtocol` | Sync | Typed error creation |
| `data_ctx` | `DataContextProtocol` | Async | Session management (unused directly, passed to repos) |
| `board_gen_service` | `BoardGenServiceProtocol` | Sync | Board generation, deadlock reshuffle |
| `board_service` | `BoardServiceProtocol` | Sync | Move processing, valid move detection |
| `scoring_service` | `ScoringServiceProtocol` | Sync | Score calculation |
| `special_gems_service` | `SpecialGemsServiceProtocol` | Sync | Special gem detection and effects |
| `player_service` | `PlayerServiceProtocol` | Async | Player lookup, match result recording, ELO updates |
| `auth_service` | `AuthServiceProtocol` | Async | (injected but unused in current code) |
| `energy_service` | `EnergyServiceProtocol` | Async | Energy checks and consumption |
| `match_repository` | `MatchRepositoryProtocol` | Async | Match persistence |
| `match_move_repository` | `MatchMoveRepositoryProtocol` | Async | Move persistence |

### MatchType to BoardGenMatchType Mapping

Module-level constant `_MATCH_TYPE_TO_BOARD_GEN` maps:
- `MatchType.STANDARD` → `BoardGenMatchType.STANDARD`
- `MatchType.COMPETITIVE` → `BoardGenMatchType.COMPETITIVE`
- `MatchType.CASUAL` → `BoardGenMatchType.CASUAL`
- `MatchType.TUTORIAL` → `BoardGenMatchType.TUTORIAL`

## 9. Configuration Keys Used

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `match.moves_per_player` | int | 20 | Number of moves each player gets |
| `match.timeout_hours` | int | 72 | Hours before match auto-abandons |
| `match.energy_cost` | int | 1 | Hearts required to start match |
| `match.allow_concurrent` | bool | False | Whether players can have multiple active matches |
| `match.max_concurrent` | int | 1 | Maximum concurrent matches if allowed |
| `match.deadlock_reshuffle` | bool | True | Whether to reshuffle on deadlock |

All config values cached in `__init__` as instance variables for performance.

## 10. Service Logic

### create_match Flow (10 steps)

1. **Validate distinct players**: Raise `VALIDATION_INVALID_INPUT` if player1_id == player2_id
2. **Validate players exist**: Call `player_service.get_player()` for both; raises `NOT_FOUND_PLAYER` internally if missing
3. **Check concurrent match limits**: If `allow_concurrent=False`, call `match_repo.find_active_by_player()` for both players; raise `CONFLICT_CONCURRENT_MATCH` if count >= max_concurrent
4. **Check energy**: Call `energy_service.can_play()` for both; raise `FORBIDDEN_INSUFFICIENT_ENERGY` if insufficient
5. **Generate seed**: Use provided seed or call `_generate_seed()` (secrets.randbits(63))
6. **Generate board**: Map match_type to BoardGenMatchType, call `board_gen_service.generate_board_for_match()`
7. **Calculate timeout**: timeout_at = now + timedelta(hours=timeout_hours)
8. **Consume energy**: Call `energy_service.consume_heart()` for both players
9. **Persist match**: Create MatchCreate DTO with identical initial_board for both players, call `match_repo.create()`
10. **Build result**: Call `_build_match_state()` to convert ORM to domain object, log "match.created", return MatchState

### submit_move Flow (15 steps)

1. **Load match**: Call `match_repo.find_by_id()`; raise `NOT_FOUND_MATCH` if None
2. **Validate participant**: Raise `FORBIDDEN_NOT_MATCH_PARTICIPANT` if player_id not in (player1_id, player2_id)
3. **Validate status**: Raise `CONFLICT_MATCH_ALREADY_COMPLETED` if status in (COMPLETED, ABANDONED); raise `CONFLICT_MATCH_NOT_IN_PROGRESS` if status not in (PENDING, IN_PROGRESS)
4. **Determine player state**: Extract moves_remaining, board_state, score, moves_made, longest_chain for the moving player
5. **Validate moves remaining**: Raise `VALIDATION_NO_MOVES_REMAINING` if moves_remaining <= 0
6. **Process move**: Call `_derive_move_seed()` to generate deterministic seed, call `board_service.process_move()`
7. **Validate match created**: Raise `VALIDATION_INVALID_GEM_SWAP` if `move_result.was_valid_match=False`
8. **Process special gems**: For each special gem created, if `special_gems_service.is_special_gem()`, call `calculate_effect()` and `apply_effect()`, accumulate bonus_score
9. **Calculate score**: Call `scoring_service.calculate_move_score()`, add special gem bonuses to points_earned
10. **Check deadlock**: Call `board_service.has_valid_moves()`; if False and deadlock_reshuffle=True and moves_remaining > 1, derive reshuffle_seed, call `board_gen_service.regenerate_from_deadlock()`
11. **Build MatchUpdate**: Update player's board_state, score, moves_made (+1), moves_remaining (-1), longest_chain (max); set finished_at if moves_remaining=0
12. **Transition status**: If status=PENDING, set status=IN_PROGRESS, set started_at
13. **Persist move record**: Create MoveCreate DTO with all move details including special_gems_created/activated as JSON, call `move_repo.create()`
14. **Check match completion**: If both players have moves_remaining=0, determine winner (higher score), set status=COMPLETED, completed_at, winner_id; call `_finalize_match()` to record results and update ELO
15. **Persist match update**: Call `match_repo.update()`, reload players, build MatchState, log "match.move_submitted", return MoveSubmissionResult

### forfeit_match Flow

1. Load match, validate participant, validate status not COMPLETED/ABANDONED
2. Determine opponent as winner
3. Create MatchUpdate: status=COMPLETED, completed_at=now, winner_id=opponent, forfeit_by=player
4. Call `match_repo.update()`
5. Call `_finalize_match()` with current scores
6. Log "match.forfeited", return updated MatchState

### abandon_stale_matches Flow

1. Call `match_repo.find_stale_matches(datetime.now())`
2. If empty, return 0
3. Extract match IDs, call `match_repo.bulk_abandon()`
4. Log "match.stale_matches_abandoned", return count

### Match Completion and Winner Determination

**Trigger:** Both players have moves_remaining=0 (checked in submit_move step 14)

**Winner logic:**
- If player1_score > player2_score: winner_id = player1_id
- Else if player2_score > player1_score: winner_id = player2_id
- Else: winner_id = None (draw)

**Finalization:** Call `_finalize_match(p1_id, p2_id, p1_score, p2_score, winner_id)`

### _finalize_match (called from submit_move and forfeit_match)

**Purpose:** Record match results for both players and update ELO ratings

**Steps:**
1. Determine is_draw (winner_id is None)
2. Call `player_service.record_match_result()` for player1 with won=(winner==p1), is_draw
3. Call `player_service.record_match_result()` for player2 with won=(winner==p2), is_draw
4. If draw: Call `player_service.calculate_elo_change(p1, p2, is_draw=True)`, get current ELOs, update both
5. Else: Call `calculate_elo_change(winner, loser, is_draw=False)`, get current ELOs, update both
6. Log "match.finalized" with scores and winner

### Deadlock Reshuffle Logic

**Trigger:** `board_service.has_valid_moves()` returns False AND `deadlock_reshuffle=True` AND `(moves_remaining - 1) > 0`

**Process:**
1. Calculate move_number = moves_made + 1
2. Call `_derive_reshuffle_seed(board_seed, player_id, move_number)` for deterministic seed
3. Call `board_gen_service.regenerate_from_deadlock(result_board, reshuffle_seed)`
4. Update result_board with reshuffled state
5. Re-check `has_valid_moves()`
6. Log "match.deadlock_reshuffle"

**Note:** No reshuffle if this is the player's last move (moves_remaining becomes 0).

### Score Calculation with Special Gem Bonuses

**Base score:** `scoring_service.calculate_move_score(move_result).total_points`

**Special gem bonus:**
For each special gem created that passes `is_special_gem()`:
- Calculate effect via `special_gems_service.calculate_effect(board, position)`
- Apply effect via `apply_effect(board, effect)` — modifies board in-place
- Add `effect.bonus_score.total_bonus` to points_earned

**Total points:** base + sum(special_bonuses)

### State Machine

```
PENDING → IN_PROGRESS → COMPLETED
   ↓             ↓
ABANDONED ← ABANDONED
```

- **PENDING → IN_PROGRESS:** First move on either player (submit_move step 12)
- **IN_PROGRESS → COMPLETED:** Both players finish moves OR forfeit
- **IN_PROGRESS → ABANDONED:** Timeout (abandon_stale_matches) OR admin action
- **PENDING → ABANDONED:** Timeout (abandon_stale_matches)

### Deterministic Seed Derivation

**Move seed:**
```python
player_hash = hash(str(player_id)) & 0xFFFFFFFF
return (match_seed ^ player_hash ^ (moves_remaining * 1103515245)) & 0x7FFFFFFF
```
Ensures same player making same move number always gets same RNG seed for board cascades.

**Reshuffle seed:**
```python
player_hash = hash(str(player_id)) & 0xFFFFFFFF
return (match_seed ^ player_hash ^ (move_number * 12345)) & 0x7FFFFFFF
```
Different constant (12345 vs 1103515245) ensures reshuffle seed differs from move seed.

**Random seed generation:**
```python
return secrets.randbits(63)  # 63-bit positive integer
```

## 11. CLI Commands

**Group:** `match`

| Command | Arguments | Options | Purpose |
|---------|-----------|---------|---------|
| `create` | player1_username, player2_username | --seed, --match-type, --config | Create new match |
| `submit-move` | match_id, player_username, from_row, from_col, to_row, to_col | --timestamp, --config | Submit a move |
| `show` | match_id | --config | Display full match state |
| `board` | match_id, player_username | --config | Display player's board with colored gems |
| `active` | player_username | --config | List active matches for player |
| `history` | player_username | --limit, --offset, --config | Show match history (paginated) |
| `moves` | match_id | --player, --config | Show move history for match |
| `forfeit` | match_id, player_username | --config | Forfeit match, declare opponent winner |
| `abandon-stale` | (none) | --config | Abandon timed-out matches |

**Service Wiring:** CLI uses `_run_async()` helper to bridge synchronous Click to async service. Creates full ApplicationContext, builds MatchService with all 13 dependencies (including manually constructing AuthService and EnergyService), executes command, shuts down context.

**Board Display:** Uses `_GEM_COLORS` dict to map gem types to Rich markup:
- Standard gems: R, B, G, Y, P, O (colored)
- Special gems: LINE_BLAST_H (—), LINE_BLAST_V (|), RADIAL_BOMB (◉), CHROMATIC_ORB (◆)
- Empty: centered dot (·)

## 12. Error Handling

### Error Codes Used

| Code | Raised When |
|------|-------------|
| `VALIDATION_INVALID_INPUT` | Same player in create_match; limit out of range in get_match_history |
| `NOT_FOUND_PLAYER` | Player doesn't exist (raised by player_service) |
| `NOT_FOUND_MATCH` | Match doesn't exist |
| `CONFLICT_CONCURRENT_MATCH` | Player already has max_concurrent active matches |
| `FORBIDDEN_INSUFFICIENT_ENERGY` | Player doesn't have enough hearts |
| `FORBIDDEN_NOT_MATCH_PARTICIPANT` | Player not in match (submit_move, get_match_state, forfeit, get_player_board) |
| `CONFLICT_MATCH_ALREADY_COMPLETED` | Match status is COMPLETED or ABANDONED |
| `CONFLICT_MATCH_NOT_IN_PROGRESS` | Match status invalid for moves (not PENDING or IN_PROGRESS) |
| `VALIDATION_NO_MOVES_REMAINING` | Player has 0 moves left |
| `VALIDATION_INVALID_GEM_SWAP` | Move produced no matches |

All errors raised via `self._errors.<method>()` with code, message, and context fields. Repository methods also raise errors (e.g., NOT_FOUND_MATCH from update if match missing).

## 13. Testing

### Test Organization

**File:** `tests/unit/modules/match/test_match_service.py` (1824 lines)

**Test Classes:**
1. `TestCreateMatch` — 10 tests
2. `TestSubmitMove` — 25 tests
3. `TestGetMatch` — 2 tests
4. `TestGetMatchState` — 2 tests
5. `TestGetPlayerBoard` — 4 tests
6. `TestGetActiveMatches` — 2 tests
7. `TestForfeitMatch` — 5 tests
8. `TestGetMatchHistory` — 4 tests
9. `TestGetMoveHistory` — 3 tests
10. `TestAbandonStaleMatches` — 2 tests
11. `TestFinalizeMatch` — 4 tests
12. `TestEdgeCases` — 9 tests

**Total:** 62 tests

### Coverage Areas

**create_match:**
- Happy path (valid players, energy, board generation)
- Same player error
- Player not found (p1, p2)
- Concurrent match limits (p1, p2)
- Insufficient energy (p1, p2)
- Custom seed, custom match type
- Energy consumption verification
- Concurrent allowed (skips check)

**submit_move:**
- Happy path
- Match not found
- Not participant
- Match completed/abandoned
- No moves remaining
- Invalid swap (no matches)
- Score updates, move decrements
- PENDING → IN_PROGRESS transition
- Player finishes (p1, p2)
- Both finish, determine winner
- Both finish, draw
- Longest chain updates
- Move record persistence
- Special gem processing
- Deadlock reshuffle

**get_match:**
- Happy path
- Not found

**get_match_state:**
- Happy path with participant validation
- Not participant
- No validation when for_player_id=None

**get_player_board:**
- Player1 board
- Player2 board
- Not found
- Not participant

**get_active_matches:**
- Returns list of MatchState
- Empty list

**forfeit_match:**
- Player1 forfeits (p2 wins)
- Player2 forfeits (p1 wins)
- Not found
- Not participant
- Already completed

**get_match_history:**
- Returns PaginatedResult with MatchSummary
- Invalid limit (too low, too high)
- Empty history
- Win/loss/draw determination

**get_move_history:**
- Returns list of MoveRecord
- Not found
- Filtered by player
- Special gems parsed correctly

**abandon_stale_matches:**
- Abandons stale matches, returns count
- No stale matches, returns 0

**_finalize_match:**
- Records match result for both players
- Updates ELO for winner/loser
- Updates ELO for draw
- Forfeit triggers finalize

**Edge cases:**
- Player2 completes match, p2 wins
- Chain not updated when lower
- No deadlock reshuffle when no moves remain
- Random seed generation
- Move number increments
- Forfeit abandoned match raises

### Mock Strategy

**Fixtures:** All dependencies mocked with AsyncMock (async services) or MagicMock (sync services).

**Helpers:** `make_player()`, `make_board()`, `make_match_record()`, `make_move_result()`, `make_score_result()`, `make_generated_board()`, `make_move_record_orm()` — construct test data.

**Verification:** Assert mock call counts, arguments, return values; check error codes; validate state transitions.

**No real I/O:** All database, config, logging, and external service calls mocked. Tests are pure unit tests.

## 14. Deviations from Standard Patterns

### Extra Public Method: `get_match_state`

**Not in MatchServiceProtocol** but present in service implementation (lines 593-621). Differs from `get_match()` by accepting optional `for_player_id` parameter to validate participant access. Internally calls `get_match()` then performs additional validation.

**Purpose:** Convenience method for presentation layer to fetch match with automatic authorization check.

### MatchType Enum Mapping

Module maintains a separate `MatchType` enum that maps to `board_gen.MatchType` (renamed `BoardGenMatchType` on import). This allows match module to define its own match type semantics while delegating board generation logic.

### Deterministic Seed Derivation

Uses custom XOR-based derivation for move seeds and reshuffle seeds rather than sequential RNG. Ensures deterministic behavior across replays and different execution orders.

**Formula:**
- Move seed: `(match_seed ^ hash(player_id) ^ (moves_remaining * large_prime)) & 0x7FFFFFFF`
- Reshuffle seed: `(match_seed ^ hash(player_id) ^ (move_number * different_constant)) & 0x7FFFFFFF`

### Independent Player Board States

Each player has their own `board_state` field in the database. After initial creation (identical boards), they diverge based on each player's moves. This supports asynchronous gameplay where players don't see each other's boards.

### Finished Timestamp Fields

Separate `player1_finished_at` and `player2_finished_at` fields track when each player exhausted their moves. Match completion (`completed_at`) only set when both finish or forfeit occurs.

### ELO Update Flow

Match finalization calls player_service methods in specific order:
1. `record_match_result()` for both players (won/loss/draw statistics)
2. `calculate_elo_change()` for winner/loser pair or both players (draw)
3. `get_elo()` for each player
4. `update_elo()` for each player with new value

This multi-step flow gives player_service control over ELO calculation algorithm while match service orchestrates the update.

---

**End of Document**
