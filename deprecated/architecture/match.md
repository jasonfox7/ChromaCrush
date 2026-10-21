# Module Architecture Report: match

**Module:** match
**Build Wave:** 5
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The match module orchestrates two-player asynchronous versus matches for ChromaCrush. It manages the full match lifecycle: creation with energy consumption and concurrent match limits, move submission with board processing and scoring, special gem effect application, deadlock reshuffle, forfeit handling, match history retrieval, and stale match abandonment. Each player maintains their own board state that diverges independently from an identical starting board. Match completion triggers winner determination, ELO updates, and player statistics finalization. All 10 public service methods are **asynchronous** (`async def`) because they involve database operations and cross-module coordination. The module delegates board computation, scoring, and special gem effects to their respective leaf modules while owning the match state machine (PENDING -> IN_PROGRESS -> COMPLETED/ABANDONED).

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_match` | `(player1_id, player2_id, board_seed?, match_type?) -> MatchState` | Create match, generate board, consume energy |
| `submit_move` | `(match_id, player_id, move) -> MoveSubmissionResult` | Process move, update score, handle completion |
| `get_match` | `(match_id) -> MatchState` | Retrieve current match state |
| `get_match_state` | `(match_id, for_player_id?) -> MatchState` | Get match state with optional participant validation |
| `get_player_board` | `(match_id, player_id) -> PlayerBoardState` | Get player's board, moves, score |
| `get_active_matches` | `(player_id) -> list[MatchState]` | List active (pending/in_progress) matches |
| `forfeit_match` | `(match_id, player_id) -> MatchState` | Forfeit, declare opponent winner |
| `get_match_history` | `(player_id, limit?, offset?, status?) -> PaginatedResult[MatchSummary]` | Paginated match history |
| `get_move_history` | `(match_id, player_id?) -> list[MoveRecord]` | Move history, optionally filtered by player |
| `abandon_stale_matches` | `() -> int` | Abandon timed-out matches, return count |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Match configuration (moves, timeout, energy cost) |
| `logger` | `LoggerProtocol` | Structured diagnostic logging |
| `errors` | `ErrorServiceProtocol` | Create typed errors |
| `data_ctx` | `DataContextProtocol` | Session management for repositories |
| `board_gen_service` | `BoardGenServiceProtocol` | Board generation and deadlock reshuffle |
| `board_service` | `BoardServiceProtocol` | Move processing, valid move detection |
| `scoring_service` | `ScoringServiceProtocol` | Score calculation from move results |
| `special_gems_service` | `SpecialGemsServiceProtocol` | Special gem detection and effect application |
| `player_service` | `PlayerServiceProtocol` | Player lookup, match result recording, ELO updates |
| `auth_service` | `AuthServiceProtocol` | Injected dependency (currently unused in service logic) |
| `energy_service` | `EnergyServiceProtocol` | Energy checks and consumption |
| `match_repository` | `MatchRepositoryProtocol` | Match persistence |
| `match_move_repository` | `MatchMoveRepositoryProtocol` | Move record persistence |

---

## 4. Data Owned

| Table | Description |
|-------|-------------|
| `matches` | Match records with per-player board state, scores, moves, and lifecycle timestamps |
| `match_moves` | Individual move records with board snapshots, scoring, and special gem data |

Both tables use UUID primary keys. Board state stored as JSONB in dual-grid format (`{"cells": [[int]], "functions": [[int]]}`) with partial indexes on active match status. Legacy single-grid format (`[[int]]`) accepted on read via `BoardState.from_list()` backwards compatibility.

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `match.moves_per_player` | int | 20 | Number of moves each player gets |
| `match.timeout_hours` | int | 24 | Hours before match auto-abandons |
| `match.energy_cost` | int | 1 | Hearts consumed to start a match |
| `match.allow_concurrent` | bool | false | Allow multiple active matches per player |
| `match.max_concurrent` | int | 1 | Maximum concurrent matches if allowed |
| `match.deadlock_reshuffle` | bool | true | Auto-reshuffle board on deadlock |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_INVALID_INPUT` | 400 | Same player in create_match; limit out of range |
| `NOT_FOUND_PLAYER` | 404 | Player does not exist (via player_service) |
| `NOT_FOUND_MATCH` | 404 | Match does not exist |
| `CONFLICT_CONCURRENT_MATCH` | 409 | Player has max active matches |
| `FORBIDDEN_INSUFFICIENT_ENERGY` | 403 | Player lacks hearts to start match |
| `FORBIDDEN_NOT_MATCH_PARTICIPANT` | 403 | Player not in match |
| `CONFLICT_MATCH_ALREADY_COMPLETED` | 409 | Action on finished match |
| `CONFLICT_MATCH_NOT_IN_PROGRESS` | 409 | Move on match not in valid state |
| `VALIDATION_NO_MOVES_REMAINING` | 400 | Player has exhausted all moves |
| `VALIDATION_INVALID_GEM_SWAP` | 400 | Move produced no matches |

---

## 7. Cross-Module Interactions

**Called by:**
- `matchmaking` -- creates matches via `create_match`
- `events` -- records event matches, reads match state
- `api` -- exposes match endpoints

**Calls:**
- `board_gen` -- board generation and deadlock reshuffle
- `board` -- move processing, cascade resolution, valid move detection
- `scoring` -- score calculation from move results
- `special_gems` -- special gem effect calculation and application
- `player` -- player existence, stats recording, ELO updates
- `energy` -- energy checks and consumption

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `MatchStatus` | `src/modules/match/types.py` | Enum: PENDING, IN_PROGRESS, COMPLETED, ABANDONED |
| `MatchType` | `src/modules/match/types.py` | Enum: STANDARD, COMPETITIVE, CASUAL, TUTORIAL |
| `MatchState` | `src/modules/match/types.py` | Complete match state with both players and lifecycle data |
| `PlayerMatchState` | `src/modules/match/types.py` | Per-player state (board, score, moves, chains) |
| `MoveSubmissionResult` | `src/modules/match/types.py` | Result of move (state, score, effects, completion) |
| `MatchSummary` | `src/modules/match/types.py` | Summary for history and profile views |
