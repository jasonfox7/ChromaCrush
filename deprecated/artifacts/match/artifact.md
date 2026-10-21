# Module Artifact: match

## Header
- **Author:** Scout Agent (match)
- **Date:** 2026-02-05
- **Version:** 1.0
- **Status:** Final
- **Dependencies:** `board_gen` (Wave 4), `board` (Wave 1), `scoring` (Wave 2), `special_gems` (Wave 3), `player` (Wave 1), `auth` (Wave 2), `energy` (Wave 2)
- **Dependents:** `matchmaking`, `vault`, `events`

---

## Purpose

The **match** module is the central game coordinator for ChromaCrush's asynchronous versus mode. It orchestrates complete 1v1 matches where two players compete on an identical seeded board, each making 20 moves to achieve the highest score.

Core responsibilities:
- **Match Creation** - Create a new match with two players sharing a deterministically-generated board from a common seed
- **Move Processing** - Validate, execute, and record player moves with full cascade resolution
- **State Machine Management** - Manage match lifecycle: PENDING -> IN_PROGRESS -> COMPLETED/ABANDONED
- **Turn Management** - Track each player's moves remaining, enforce move limits
- **Score Tracking** - Accumulate scores per player through the scoring module
- **Winner Determination** - Compare final scores when both players exhaust moves
- **Move History** - Persist all moves with timestamps for replay and verification
- **Forfeit Handling** - Allow players to forfeit, awarding victory to opponent

The module enables **asynchronous versus play** - both players play the same board independently (not real-time), and the winner is determined by final score comparison. This is the "async fairness" model per the GDD.

This module is **asynchronous** - all public methods that involve database operations are `async def`.

---

## Public Interface

### Class: `MatchService`

The match module exposes a single service class that receives dependencies via `__init__` injection.

```python
class MatchService:
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
    ) -> None:
        ...
```

---

### Inputs

#### `create_match(player1_id: PlayerId, player2_id: PlayerId, board_seed: int | None = None, match_type: MatchType = MatchType.STANDARD) -> MatchState`

Creates a new versus match between two players.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player1_id` | `PlayerId` | First player's ID | Must exist, must have sufficient energy |
| `player2_id` | `PlayerId` | Second player's ID | Must exist, must have sufficient energy, must not equal player1_id |
| `board_seed` | `int \| None` | Optional seed for board generation | If None, generates random seed |
| `match_type` | `MatchType` | Type of match (affects board generation) | Must be valid MatchType |

---

#### `submit_move(match_id: MatchId, player_id: PlayerId, move: Move) -> MoveSubmissionResult`

Submits a move for a player in an active match.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `match_id` | `MatchId` | The match to submit to | Must exist |
| `player_id` | `PlayerId` | The player submitting the move | Must be a participant, must have moves remaining |
| `move` | `Move` | The move to execute (from_pos, to_pos, timestamp_ms) | Positions must be valid, adjacent |

---

#### `get_match_state(match_id: MatchId, for_player_id: PlayerId | None = None) -> MatchState`

Retrieves the current state of a match.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `match_id` | `MatchId` | The match to retrieve | Must exist |
| `for_player_id` | `PlayerId \| None` | If provided, validates player has access | Must be a participant if provided |

---

#### `get_player_board(match_id: MatchId, player_id: PlayerId) -> PlayerBoardState`

Gets the current board state for a specific player (reflecting their moves).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `match_id` | `MatchId` | The match | Must exist |
| `player_id` | `PlayerId` | The player whose board to retrieve | Must be a participant |

---

#### `forfeit_match(match_id: MatchId, player_id: PlayerId) -> MatchState`

Forfeits a match, awarding victory to the opponent.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `match_id` | `MatchId` | The match to forfeit | Must exist, must be IN_PROGRESS |
| `player_id` | `PlayerId` | The player forfeiting | Must be a participant |

---

#### `get_match_history(player_id: PlayerId, limit: int = 20, offset: int = 0, status: MatchStatus | None = None) -> PaginatedResult[MatchSummary]`

Retrieves a player's match history.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist |
| `limit` | `int` | Maximum results (1-100) | Must be 1-100 |
| `offset` | `int` | Pagination offset | Must be >= 0 |
| `status` | `MatchStatus \| None` | Filter by status | If provided, must be valid |

---

#### `get_move_history(match_id: MatchId, player_id: PlayerId | None = None) -> list[MoveRecord]`

Retrieves the complete move history for a match.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `match_id` | `MatchId` | The match | Must exist |
| `player_id` | `PlayerId \| None` | Filter to specific player's moves | If provided, must be participant |

---

#### `abandon_stale_matches() -> int`

Background operation to abandon matches that have exceeded timeout.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| (none) | - | - | - |

Returns count of matches abandoned.

---

### Outputs

#### `create_match` returns `MatchState`

```python
@dataclass
class MatchState:
    """Complete state of a versus match."""
    match_id: MatchId
    board_seed: int
    initial_board: BoardState
    status: MatchStatus
    match_type: MatchType
    player1: PlayerMatchState
    player2: PlayerMatchState
    winner_id: PlayerId | None
    forfeit_by: PlayerId | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    timeout_at: datetime  # When match will be auto-abandoned
```

```python
@dataclass
class PlayerMatchState:
    """A single player's state within a match."""
    player_id: PlayerId
    player_username: str
    score: int
    moves_made: int
    moves_remaining: int
    current_board: BoardState  # Player's board after their moves
    longest_chain: int
    special_gems_created: int
    special_gems_activated: int
    total_gems_cleared: int
    finished_at: datetime | None  # When player exhausted moves
```

---

#### `submit_move` returns `MoveSubmissionResult`

```python
@dataclass
class MoveSubmissionResult:
    """Result of submitting a move."""
    match_state: MatchState
    move_result: MoveProcessingResult  # From board module
    score_result: MoveScore  # From scoring module
    special_effects: list[SpecialGemEffect]  # Any special gem activations
    points_earned: int
    move_number: int  # This player's move number (1-20)
    moves_remaining: int
    match_completed: bool
    player_finished: bool  # True if this player has no more moves
    winner_id: PlayerId | None  # Set if match_completed
```

---

#### `get_match_state` returns `MatchState`

Returns the current match state as described above.

---

#### `get_player_board` returns `PlayerBoardState`

```python
@dataclass
class PlayerBoardState:
    """Board state for a specific player."""
    player_id: PlayerId
    board: BoardState
    moves_made: int
    moves_remaining: int
    score: int
    has_valid_moves: bool  # False if board is deadlocked
```

---

#### `forfeit_match` returns `MatchState`

Returns the updated match state with `status=COMPLETED`, `winner_id=opponent`, `forfeit_by=player_id`.

---

#### `get_match_history` returns `PaginatedResult[MatchSummary]`

```python
@dataclass
class MatchSummary:
    """Abbreviated match info for history lists."""
    match_id: MatchId
    opponent_id: PlayerId
    opponent_username: str
    player_score: int
    opponent_score: int
    won: bool | None  # None if draw
    status: MatchStatus
    match_type: MatchType
    created_at: datetime
    completed_at: datetime | None
```

---

#### `get_move_history` returns `list[MoveRecord]`

```python
@dataclass
class MoveRecord:
    """Record of a single move."""
    move_number: int
    player_id: PlayerId
    move: Move
    board_before: BoardState
    board_after: BoardState
    score_earned: int
    chain_count: int
    gems_cleared: int
    special_gems_created: list[tuple[Position, GemType]]
    special_gems_activated: list[Position]
    timestamp: datetime
```

---

### Error Cases

| Condition | Error Code | Error Type | Context Fields |
|-----------|------------|------------|----------------|
| Player not found | `NOT_FOUND_PLAYER` | not_found | `player_id` |
| Match not found | `NOT_FOUND_MATCH` | not_found | `match_id` |
| Player1 same as Player2 | `VALIDATION_INVALID_INPUT` | validation | `field="player2_id"`, `reason="Cannot create match against self"` |
| Player not a match participant | `FORBIDDEN_NOT_MATCH_PARTICIPANT` | forbidden | `match_id`, `player_id` |
| No moves remaining | `VALIDATION_NO_MOVES_REMAINING` | validation | `player_id`, `match_id`, `moves_remaining=0` |
| Match already completed | `CONFLICT_MATCH_ALREADY_COMPLETED` | conflict | `match_id`, `completed_at` |
| Player in active match | `CONFLICT_PLAYER_IN_MATCH` | conflict | `player_id`, `active_match_id` |
| Insufficient energy | `FORBIDDEN_INSUFFICIENT_ENERGY` | forbidden | `required=1`, `available` |
| Invalid move positions | `VALIDATION_POSITIONS_NOT_ADJACENT` | validation | `from_pos`, `to_pos` |
| Move position out of bounds | `VALIDATION_OUT_OF_BOUNDS` | validation | `position`, `board_width`, `board_height` |
| Invalid gem swap (empty cell, etc.) | `VALIDATION_INVALID_GEM_SWAP` | validation | `from_gem`, `to_gem`, `reason` |
| Match not in progress | `CONFLICT_MATCH_NOT_IN_PROGRESS` | conflict | `match_id`, `current_status` |
| Pagination limit out of range | `VALIDATION_INVALID_INPUT` | validation | `field="limit"`, `value`, `max=100` |

---

### Async Behavior

**This module is fully asynchronous.**

All public methods except utility helpers are `async def` because they involve:
- Database reads/writes via `MatchRepository`
- Cross-module service calls to `player_service`, `energy_service`
- Board generation and processing (synchronous internally but called in async context)

**Async operations:**
- `create_match` - Reads players, checks energy, consumes energy, generates board, creates match record
- `submit_move` - Reads match, validates player, processes move, updates match state
- `get_match_state` - Reads match from database
- `get_player_board` - Reads match, extracts player board state
- `forfeit_match` - Reads match, updates status, determines winner
- `get_match_history` - Reads match records
- `get_move_history` - Reads move records
- `abandon_stale_matches` - Batch updates stale matches

**Error propagation:** All errors are raised through the injected `ErrorServiceProtocol`. Database errors are caught and wrapped in `INTERNAL_DATABASE_ERROR`. Cross-module errors (`NOT_FOUND_PLAYER`, `FORBIDDEN_INSUFFICIENT_ENERGY`) propagate unchanged.

---

## Mandatory Service Usage

### Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `game.board_width` | int | 8 | Board width |
| `game.board_height` | int | 8 | Board height |
| `match.moves_per_player` | int | 20 | Moves each player gets |
| `match.timeout_hours` | int | 72 | Hours before match is auto-abandoned |
| `match.energy_cost` | int | 1 | Hearts required to start a match |
| `match.allow_concurrent` | bool | false | Whether a player can be in multiple matches |
| `match.max_concurrent` | int | 1 | Maximum concurrent matches per player (if allow_concurrent=true) |
| `match.deadlock_reshuffle` | bool | true | Whether to reshuffle on deadlock |

---

### Logging Events

| Event | Severity | Trigger | Context |
|-------|----------|---------|---------|
| `match.created` | INFO | Match created successfully | `match_id`, `player1_id`, `player2_id`, `board_seed`, `match_type` |
| `match.move_submitted` | DEBUG | Player submits move | `match_id`, `player_id`, `move_number`, `score_earned` |
| `match.player_finished` | INFO | Player exhausts moves | `match_id`, `player_id`, `final_score` |
| `match.completed` | INFO | Match finishes (both done) | `match_id`, `winner_id`, `player1_score`, `player2_score` |
| `match.forfeited` | INFO | Player forfeits | `match_id`, `forfeit_by`, `winner_id` |
| `match.abandoned` | INFO | Match auto-abandoned | `match_id`, `reason="timeout"` |
| `match.deadlock_detected` | WARN | Board has no valid moves | `match_id`, `player_id` |
| `match.deadlock_reshuffled` | INFO | Board reshuffled after deadlock | `match_id`, `player_id`, `reshuffle_seed` |
| `match.special_gem_activated` | DEBUG | Special gem triggered | `match_id`, `player_id`, `gem_type`, `position`, `gems_affected` |
| `match.creation_failed` | WARN | Match creation failed | `player1_id`, `player2_id`, `reason` |
| `match.energy_consumed` | DEBUG | Energy consumed for match | `player_id`, `amount` |
| `match.invalid_move` | WARN | Invalid move rejected | `match_id`, `player_id`, `reason` |

---

### Error Types Used

From the error taxonomy (Interface Agent guidance):

- `NOT_FOUND_PLAYER` - Player ID doesn't exist
- `NOT_FOUND_MATCH` - Match ID doesn't exist
- `VALIDATION_INVALID_INPUT` - Invalid input parameters
- `VALIDATION_POSITIONS_NOT_ADJACENT` - Move positions not adjacent
- `VALIDATION_OUT_OF_BOUNDS` - Position outside grid
- `VALIDATION_INVALID_GEM_SWAP` - Cannot swap these gems
- `VALIDATION_NO_MOVES_REMAINING` - Player has no moves left
- `FORBIDDEN_NOT_MATCH_PARTICIPANT` - Player not in this match
- `FORBIDDEN_INSUFFICIENT_ENERGY` - Not enough hearts
- `CONFLICT_MATCH_ALREADY_COMPLETED` - Match is finished
- `CONFLICT_PLAYER_IN_MATCH` - Player already in active match
- `CONFLICT_MATCH_NOT_IN_PROGRESS` - Match not in IN_PROGRESS status
- `INTERNAL_DATABASE_ERROR` - Database operation failed

All errors created through injected `ErrorServiceProtocol`, never bare raises.

---

## Data Access

### Owned Data

The match module owns these database tables:

#### `matches` Table

```sql
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_seed BIGINT NOT NULL,
    initial_board_state JSONB NOT NULL,  -- Initial 8x8 grid
    match_type VARCHAR(20) NOT NULL DEFAULT 'standard',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, in_progress, completed, abandoned

    player1_id UUID NOT NULL REFERENCES players(id),
    player1_board_state JSONB NOT NULL,  -- Player 1's current board
    player1_score INTEGER NOT NULL DEFAULT 0,
    player1_moves_made INTEGER NOT NULL DEFAULT 0,
    player1_moves_remaining INTEGER NOT NULL DEFAULT 20,
    player1_longest_chain INTEGER NOT NULL DEFAULT 0,
    player1_finished_at TIMESTAMPTZ,

    player2_id UUID NOT NULL REFERENCES players(id),
    player2_board_state JSONB NOT NULL,  -- Player 2's current board
    player2_score INTEGER NOT NULL DEFAULT 0,
    player2_moves_made INTEGER NOT NULL DEFAULT 0,
    player2_moves_remaining INTEGER NOT NULL DEFAULT 20,
    player2_longest_chain INTEGER NOT NULL DEFAULT 0,
    player2_finished_at TIMESTAMPTZ,

    winner_id UUID REFERENCES players(id),
    forfeit_by UUID REFERENCES players(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,  -- When first move was made
    completed_at TIMESTAMPTZ,
    timeout_at TIMESTAMPTZ NOT NULL,  -- Auto-abandon deadline

    CONSTRAINT check_players_different CHECK (player1_id != player2_id)
);

CREATE INDEX idx_matches_player1 ON matches(player1_id) WHERE status IN ('pending', 'in_progress');
CREATE INDEX idx_matches_player2 ON matches(player2_id) WHERE status IN ('pending', 'in_progress');
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_timeout ON matches(timeout_at) WHERE status = 'in_progress';
```

#### `match_moves` Table

```sql
CREATE TABLE match_moves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES players(id),
    move_number INTEGER NOT NULL,  -- 1-20 for this player

    from_row INTEGER NOT NULL,
    from_col INTEGER NOT NULL,
    to_row INTEGER NOT NULL,
    to_col INTEGER NOT NULL,
    client_timestamp_ms BIGINT NOT NULL,  -- Client-provided timestamp

    board_before JSONB NOT NULL,
    board_after JSONB NOT NULL,
    score_earned INTEGER NOT NULL,
    chain_count INTEGER NOT NULL,
    gems_cleared INTEGER NOT NULL,
    special_gems_created JSONB NOT NULL DEFAULT '[]',  -- Array of {position, gem_type}
    special_gems_activated JSONB NOT NULL DEFAULT '[]',  -- Array of positions

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_player_move UNIQUE (match_id, player_id, move_number)
);

CREATE INDEX idx_match_moves_match ON match_moves(match_id);
CREATE INDEX idx_match_moves_player ON match_moves(match_id, player_id);
```

---

### Repository Interfaces Required

```python
# src/data/protocols/match_repository.py
from typing import Protocol
from uuid import UUID
from datetime import datetime

from src.core.types.game import PlayerId, MatchId
from src.core.types.match import MatchStatus


class MatchRepository(Protocol):
    """Repository interface for match data."""

    async def create(self, data: "MatchCreate") -> "MatchRecord":
        """Create a new match record."""
        ...

    async def find_by_id(self, match_id: UUID) -> "MatchRecord | None":
        """Find match by ID."""
        ...

    async def update(self, match_id: UUID, changes: "MatchUpdate") -> "MatchRecord":
        """Update match fields."""
        ...

    async def find_active_by_player(self, player_id: UUID) -> list["MatchRecord"]:
        """Find all active matches (pending/in_progress) for a player."""
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        status: MatchStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list["MatchRecord"], int]:
        """Find matches for a player with optional status filter."""
        ...

    async def find_stale_matches(self, cutoff: datetime) -> list["MatchRecord"]:
        """Find in_progress matches past their timeout."""
        ...

    async def bulk_abandon(self, match_ids: list[UUID]) -> int:
        """Mark multiple matches as abandoned. Returns count updated."""
        ...


class MatchMoveRepository(Protocol):
    """Repository interface for match move data."""

    async def create(self, data: "MoveCreate") -> "MoveRecord":
        """Create a new move record."""
        ...

    async def find_by_match(
        self,
        match_id: UUID,
        player_id: UUID | None = None,
    ) -> list["MoveRecord"]:
        """Find moves for a match, optionally filtered by player."""
        ...

    async def count_by_player(self, match_id: UUID, player_id: UUID) -> int:
        """Count moves made by a player in a match."""
        ...
```

---

### Data Read from Other Modules

| Data | Source Module | Access Method | Purpose |
|------|---------------|---------------|---------|
| Player entity | `player` | `PlayerServiceProtocol.get_player()` | Validate players exist, get usernames |
| Player energy | `energy` | `EnergyServiceProtocol.can_play()`, `consume_heart()` | Check and consume energy |
| Player stats | `player` | `PlayerServiceProtocol.record_match_result()` | Update stats on completion |
| Player ELO | `player` | `PlayerServiceProtocol.calculate_elo_change()`, `update_elo()` | Update ratings on completion |

---

### Transaction Requirements

| Operation | Transaction Scope | Notes |
|-----------|-------------------|-------|
| `create_match` | Single transaction | Creates match + consumes energy for both players atomically |
| `submit_move` | Single transaction | Updates match state + creates move record atomically |
| `forfeit_match` | Single transaction | Updates match status + winner atomically |
| `abandon_stale_matches` | Single transaction | Batch update for efficiency |
| Match completion | Single transaction | Updates match status + both players' stats + ELO atomically |

**Critical: Atomic Match Creation**

Match creation must be atomic to prevent:
1. Energy consumed for player1 but match creation fails
2. Player joins another match between energy check and match creation

Implementation uses SELECT FOR UPDATE or optimistic locking pattern.

---

## Presentation Boundary

### Business Logic API Surface

The match module exposes domain objects and DTOs:
- Input: `PlayerId`, `MatchId`, `Move`, `MatchType`
- Output: `MatchState`, `MoveSubmissionResult`, `MatchSummary`, `MoveRecord`, `PlayerBoardState`

All types are defined in this module (`src/modules/match/types.py`) or imported from `src/core/types/`.

### Adapter Needs

Presentation adapters need to:
1. Convert `MatchState` to perspective-specific response (hide opponent's unrevealed moves if applicable)
2. Format board state from NumPy array to JSON list
3. Convert timestamps to ISO format
4. Calculate derived fields (is_your_turn, your_score vs opponent_score)
5. Format move history for replay visualization

Example adapter output for API:
```python
{
    "match_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "in_progress",
    "match_type": "standard",
    "your_score": 1250,
    "opponent_score": 1100,
    "your_moves_remaining": 15,
    "opponent_moves_remaining": 14,
    "board": [[1, 2, 3, ...], ...],  # Your current board
    "opponent_finished": false,
    "created_at": "2026-02-05T10:30:00Z",
    "timeout_at": "2026-02-08T10:30:00Z"
}
```

### What Does NOT Belong in This Module

- No JSON serialization (adapter responsibility)
- No HTTP response construction
- No terminal formatting
- No animation timing
- No real-time notifications (separate notification system)
- No matchmaking logic (matchmaking module responsibility)
- No ELO calculation logic (player module responsibility)

---

## Internal Design

### State Machine

```
                 create_match()
                      |
                      v
               +-----------+
               |  PENDING  |
               +-----------+
                      |
                      | first move by either player
                      v
             +---------------+
             |  IN_PROGRESS  |<-----+
             +---------------+      |
               /      |      \      | move (if both have moves)
              /       |       \     |
             /        |        \----+
            /         |
    forfeit()    both players
       |         exhaust moves
       v              |
 +-------------+      v
 | COMPLETED   |<-----+
 | (forfeit)   |
 +-------------+

       |         timeout exceeded
       |              |
       v              v
 +-------------+  +-----------+
 | COMPLETED   |  | ABANDONED |
 | (normal)    |  +-----------+
 +-------------+
```

**State transitions:**
- `PENDING -> IN_PROGRESS`: First move submitted by either player
- `IN_PROGRESS -> COMPLETED`: Both players exhaust moves OR one player forfeits
- `IN_PROGRESS -> ABANDONED`: Match timeout exceeded (background job)

---

### Core Data Structures

```python
# src/modules/match/types.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from src.core.types.game import PlayerId, MatchId, Move, Position, GemType
from src.core.types.board import BoardState
from src.modules.board.types import MoveProcessingResult
from src.modules.scoring.types import MoveScore
from src.modules.special_gems.types import SpecialGemEffect


class MatchStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MatchType(Enum):
    STANDARD = "standard"
    COMPETITIVE = "competitive"
    CASUAL = "casual"
    TUTORIAL = "tutorial"


@dataclass
class PlayerMatchState:
    """A player's state within a match."""
    player_id: PlayerId
    player_username: str
    score: int = 0
    moves_made: int = 0
    moves_remaining: int = 20
    current_board: BoardState = field(default=None)
    longest_chain: int = 0
    special_gems_created: int = 0
    special_gems_activated: int = 0
    total_gems_cleared: int = 0
    finished_at: datetime | None = None


@dataclass
class MatchState:
    """Complete state of a match."""
    match_id: MatchId
    board_seed: int
    initial_board: BoardState
    status: MatchStatus
    match_type: MatchType
    player1: PlayerMatchState
    player2: PlayerMatchState
    winner_id: PlayerId | None = None
    forfeit_by: PlayerId | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    timeout_at: datetime = field(default=None)

    def get_player_state(self, player_id: PlayerId) -> PlayerMatchState:
        """Get state for a specific player."""
        if self.player1.player_id == player_id:
            return self.player1
        elif self.player2.player_id == player_id:
            return self.player2
        raise ValueError(f"Player {player_id} not in this match")

    def get_opponent_state(self, player_id: PlayerId) -> PlayerMatchState:
        """Get opponent's state."""
        if self.player1.player_id == player_id:
            return self.player2
        elif self.player2.player_id == player_id:
            return self.player1
        raise ValueError(f"Player {player_id} not in this match")

    @property
    def both_finished(self) -> bool:
        """Check if both players have exhausted their moves."""
        return (
            self.player1.moves_remaining == 0 and
            self.player2.moves_remaining == 0
        )

    def is_participant(self, player_id: PlayerId) -> bool:
        """Check if player is a participant."""
        return player_id in (self.player1.player_id, self.player2.player_id)


@dataclass
class MoveSubmissionResult:
    """Result of submitting a move."""
    match_state: MatchState
    move_result: MoveProcessingResult
    score_result: MoveScore
    special_effects: list[SpecialGemEffect]
    points_earned: int
    move_number: int
    moves_remaining: int
    match_completed: bool
    player_finished: bool
    winner_id: PlayerId | None = None


@dataclass
class MatchSummary:
    """Abbreviated match info for lists."""
    match_id: MatchId
    opponent_id: PlayerId
    opponent_username: str
    player_score: int
    opponent_score: int
    won: bool | None  # None = draw
    status: MatchStatus
    match_type: MatchType
    created_at: datetime
    completed_at: datetime | None


@dataclass
class MoveRecord:
    """Record of a single move."""
    move_number: int
    player_id: PlayerId
    move: Move
    board_before: BoardState
    board_after: BoardState
    score_earned: int
    chain_count: int
    gems_cleared: int
    special_gems_created: list[tuple[Position, GemType]]
    special_gems_activated: list[Position]
    timestamp: datetime


@dataclass
class PlayerBoardState:
    """Board state for a specific player."""
    player_id: PlayerId
    board: BoardState
    moves_made: int
    moves_remaining: int
    score: int
    has_valid_moves: bool
```

---

### Algorithm: Match Creation

```python
async def create_match(
    self,
    player1_id: PlayerId,
    player2_id: PlayerId,
    board_seed: int | None = None,
    match_type: MatchType = MatchType.STANDARD,
) -> MatchState:
    # 1. Validate players are different
    if player1_id == player2_id:
        raise self._errors.validation(
            "Cannot create match against self",
            code="VALIDATION_INVALID_INPUT",
            field="player2_id",
        )

    # 2. Validate both players exist
    player1 = await self._player_service.get_player(player1_id)
    player2 = await self._player_service.get_player(player2_id)

    # 3. Check for active matches (if concurrent not allowed)
    if not self._config.get("match.allow_concurrent", False):
        active_matches = await self._match_repo.find_active_by_player(player1_id)
        if active_matches:
            raise self._errors.conflict(
                "Player already in active match",
                code="CONFLICT_PLAYER_IN_MATCH",
                player_id=str(player1_id),
                active_match_id=str(active_matches[0].id),
            )

        active_matches = await self._match_repo.find_active_by_player(player2_id)
        if active_matches:
            raise self._errors.conflict(
                "Player already in active match",
                code="CONFLICT_PLAYER_IN_MATCH",
                player_id=str(player2_id),
                active_match_id=str(active_matches[0].id),
            )

    # 4. Check and consume energy for both players
    energy_cost = self._config.get("match.energy_cost", 1)

    if not await self._energy_service.can_play(player1_id, energy_cost):
        raise self._errors.forbidden(
            "Insufficient energy",
            code="FORBIDDEN_INSUFFICIENT_ENERGY",
            required=energy_cost,
            player_id=str(player1_id),
        )

    if not await self._energy_service.can_play(player2_id, energy_cost):
        raise self._errors.forbidden(
            "Insufficient energy",
            code="FORBIDDEN_INSUFFICIENT_ENERGY",
            required=energy_cost,
            player_id=str(player2_id),
        )

    # 5. Generate board seed if not provided
    if board_seed is None:
        board_seed = self._generate_seed()

    # 6. Generate the board
    generated_board = self._board_gen_service.generate_board_for_match(
        seed=board_seed,
        match_type=match_type,
    )

    # 7. Calculate timeout
    timeout_hours = self._config.get("match.timeout_hours", 72)
    timeout_at = datetime.utcnow() + timedelta(hours=timeout_hours)

    # 8. Create match record (atomic with energy consumption)
    async with self._data_ctx.session() as session:
        # Consume energy
        await self._energy_service.consume_heart(player1_id, energy_cost)
        await self._energy_service.consume_heart(player2_id, energy_cost)

        # Create match
        moves_per_player = self._config.get("match.moves_per_player", 20)

        match_record = await self._match_repo.create(MatchCreate(
            board_seed=board_seed,
            initial_board_state=generated_board.board_state.to_list(),
            match_type=match_type.value,
            player1_id=player1_id,
            player1_board_state=generated_board.board_state.to_list(),
            player1_moves_remaining=moves_per_player,
            player2_id=player2_id,
            player2_board_state=generated_board.board_state.to_list(),
            player2_moves_remaining=moves_per_player,
            timeout_at=timeout_at,
        ))

    # 9. Log and return
    self._logger.info(
        "Match created",
        match_id=str(match_record.id),
        player1_id=str(player1_id),
        player2_id=str(player2_id),
        board_seed=board_seed,
        match_type=match_type.value,
    )

    return self._build_match_state(match_record, player1, player2)
```

---

### Algorithm: Move Submission

```python
async def submit_move(
    self,
    match_id: MatchId,
    player_id: PlayerId,
    move: Move,
) -> MoveSubmissionResult:
    # 1. Load and validate match
    match_record = await self._match_repo.find_by_id(match_id)
    if match_record is None:
        raise self._errors.not_found(
            "Match not found",
            code="NOT_FOUND_MATCH",
            match_id=str(match_id),
        )

    # 2. Validate player is participant
    if player_id not in (match_record.player1_id, match_record.player2_id):
        raise self._errors.forbidden(
            "Not a participant in this match",
            code="FORBIDDEN_NOT_MATCH_PARTICIPANT",
            match_id=str(match_id),
            player_id=str(player_id),
        )

    # 3. Validate match is active
    if match_record.status == MatchStatus.COMPLETED.value:
        raise self._errors.conflict(
            "Match already completed",
            code="CONFLICT_MATCH_ALREADY_COMPLETED",
            match_id=str(match_id),
            completed_at=match_record.completed_at.isoformat(),
        )

    if match_record.status == MatchStatus.ABANDONED.value:
        raise self._errors.conflict(
            "Match was abandoned",
            code="CONFLICT_MATCH_ALREADY_COMPLETED",
            match_id=str(match_id),
        )

    # 4. Get player's state
    is_player1 = player_id == match_record.player1_id
    moves_remaining = (
        match_record.player1_moves_remaining if is_player1
        else match_record.player2_moves_remaining
    )
    current_board_json = (
        match_record.player1_board_state if is_player1
        else match_record.player2_board_state
    )
    current_board = BoardState.from_list(current_board_json)

    # 5. Validate moves remaining
    if moves_remaining <= 0:
        raise self._errors.validation(
            "No moves remaining",
            code="VALIDATION_NO_MOVES_REMAINING",
            player_id=str(player_id),
            match_id=str(match_id),
            moves_remaining=0,
        )

    # 6. Process the move through board module
    move_seed = self._derive_move_seed(match_record.board_seed, player_id, moves_remaining)

    try:
        move_result = self._board_service.process_move(
            board=current_board,
            move=move,
            seed=move_seed,
        )
    except AppError:
        raise

    # 7. Check if move was valid (created a match)
    if not move_result.was_valid_match:
        raise self._errors.validation(
            "Move does not create a match",
            code="VALIDATION_INVALID_GEM_SWAP",
            from_pos=str(move.from_pos),
            to_pos=str(move.to_pos),
            reason="No match created",
        )

    # 8. Process special gem effects
    special_effects = []
    final_board = move_result.final_board

    for position, gem_type in move_result.special_gems_created:
        # Special gems are already created by board module
        pass

    # Find and process triggered special gems
    for cascade in move_result.cascades:
        triggered = self._special_gems_service.find_triggered_special_gems(
            cascade.board_after_clear,
            set(pos for match in cascade.matches.matches for pos in match.positions),
        )
        for trigger_pos in triggered:
            effect = self._special_gems_service.calculate_effect(
                cascade.board_after_clear,
                trigger_pos,
            )
            special_effects.append(effect)

    # 9. Calculate score
    score_result = self._scoring_service.calculate_move_score(move_result)
    points_earned = score_result.total_points

    # Add special gem bonuses
    for effect in special_effects:
        points_earned += effect.bonus_score.total_bonus

    # 10. Update match state
    move_number = (
        match_record.player1_moves_made + 1 if is_player1
        else match_record.player2_moves_made + 1
    )
    new_moves_remaining = moves_remaining - 1

    # Check for deadlock and reshuffle if needed
    if not self._board_service.has_valid_moves(final_board):
        if self._config.get("match.deadlock_reshuffle", True):
            reshuffle_seed = self._derive_reshuffle_seed(
                match_record.board_seed, player_id, move_number
            )
            reshuffled = self._board_gen_service.regenerate_from_deadlock(
                final_board, reshuffle_seed
            )
            final_board = reshuffled.board_state

            self._logger.info(
                "Deadlock reshuffled",
                match_id=str(match_id),
                player_id=str(player_id),
                reshuffle_seed=reshuffle_seed,
            )
        else:
            self._logger.warn(
                "Deadlock detected",
                match_id=str(match_id),
                player_id=str(player_id),
            )

    # 11. Update database
    async with self._data_ctx.session() as session:
        # Update player's state in match
        if is_player1:
            updates = MatchUpdate(
                player1_board_state=final_board.to_list(),
                player1_score=match_record.player1_score + points_earned,
                player1_moves_made=move_number,
                player1_moves_remaining=new_moves_remaining,
                player1_longest_chain=max(
                    match_record.player1_longest_chain,
                    score_result.chain_count,
                ),
            )
            if new_moves_remaining == 0:
                updates.player1_finished_at = datetime.utcnow()
        else:
            updates = MatchUpdate(
                player2_board_state=final_board.to_list(),
                player2_score=match_record.player2_score + points_earned,
                player2_moves_made=move_number,
                player2_moves_remaining=new_moves_remaining,
                player2_longest_chain=max(
                    match_record.player2_longest_chain,
                    score_result.chain_count,
                ),
            )
            if new_moves_remaining == 0:
                updates.player2_finished_at = datetime.utcnow()

        # Transition to IN_PROGRESS on first move
        if match_record.status == MatchStatus.PENDING.value:
            updates.status = MatchStatus.IN_PROGRESS.value
            updates.started_at = datetime.utcnow()

        # Create move record
        await self._move_repo.create(MoveCreate(
            match_id=match_id,
            player_id=player_id,
            move_number=move_number,
            from_row=move.from_pos.row,
            from_col=move.from_pos.col,
            to_row=move.to_pos.row,
            to_col=move.to_pos.col,
            client_timestamp_ms=move.timestamp_ms,
            board_before=current_board.to_list(),
            board_after=final_board.to_list(),
            score_earned=points_earned,
            chain_count=score_result.chain_count,
            gems_cleared=score_result.total_gems_cleared,
            special_gems_created=[(str(p), gt.value) for p, gt in move_result.special_gems_created],
            special_gems_activated=[str(e.source_position) for e in special_effects],
        ))

        # Check if both players finished
        player_finished = new_moves_remaining == 0

        if is_player1:
            both_finished = player_finished and match_record.player2_moves_remaining == 0
        else:
            both_finished = player_finished and match_record.player1_moves_remaining == 0

        match_completed = both_finished
        winner_id = None

        if match_completed:
            # Determine winner
            final_p1_score = (
                match_record.player1_score + points_earned if is_player1
                else match_record.player1_score
            )
            final_p2_score = (
                match_record.player2_score + points_earned if not is_player1
                else match_record.player2_score
            )

            if final_p1_score > final_p2_score:
                winner_id = match_record.player1_id
            elif final_p2_score > final_p1_score:
                winner_id = match_record.player2_id
            # else: draw (winner_id stays None)

            updates.status = MatchStatus.COMPLETED.value
            updates.completed_at = datetime.utcnow()
            updates.winner_id = winner_id

            # Update player stats and ELO
            await self._finalize_match(
                match_record.player1_id,
                match_record.player2_id,
                final_p1_score,
                final_p2_score,
                winner_id,
            )

        updated_match = await self._match_repo.update(match_id, updates)

    # 12. Log and return
    self._logger.debug(
        "Move submitted",
        match_id=str(match_id),
        player_id=str(player_id),
        move_number=move_number,
        score_earned=points_earned,
    )

    if player_finished:
        self._logger.info(
            "Player finished",
            match_id=str(match_id),
            player_id=str(player_id),
            final_score=match_record.player1_score + points_earned if is_player1 else match_record.player2_score + points_earned,
        )

    if match_completed:
        self._logger.info(
            "Match completed",
            match_id=str(match_id),
            winner_id=str(winner_id) if winner_id else "draw",
            player1_score=final_p1_score,
            player2_score=final_p2_score,
        )

    # Build and return result
    player1 = await self._player_service.get_player(match_record.player1_id)
    player2 = await self._player_service.get_player(match_record.player2_id)

    return MoveSubmissionResult(
        match_state=self._build_match_state(updated_match, player1, player2),
        move_result=move_result,
        score_result=score_result,
        special_effects=special_effects,
        points_earned=points_earned,
        move_number=move_number,
        moves_remaining=new_moves_remaining,
        match_completed=match_completed,
        player_finished=player_finished,
        winner_id=winner_id,
    )
```

---

### Algorithm: Match Finalization

```python
async def _finalize_match(
    self,
    player1_id: PlayerId,
    player2_id: PlayerId,
    player1_score: int,
    player2_score: int,
    winner_id: PlayerId | None,
) -> None:
    """Finalize a completed match: update stats and ELO."""

    is_draw = winner_id is None

    # Update player stats
    await self._player_service.record_match_result(
        player_id=player1_id,
        won=(winner_id == player1_id),
        is_draw=is_draw,
        score=player1_score,
        longest_chain=0,  # Would come from match record
        gems_matched=0,   # Would come from match record
    )

    await self._player_service.record_match_result(
        player_id=player2_id,
        won=(winner_id == player2_id),
        is_draw=is_draw,
        score=player2_score,
        longest_chain=0,
        gems_matched=0,
    )

    # Calculate and apply ELO changes
    if is_draw:
        elo_change_1, elo_change_2 = await self._player_service.calculate_elo_change(
            winner_id=player1_id,  # arbitrary for draw
            loser_id=player2_id,
            is_draw=True,
        )
    else:
        loser_id = player2_id if winner_id == player1_id else player1_id
        elo_change_1, elo_change_2 = await self._player_service.calculate_elo_change(
            winner_id=winner_id,
            loser_id=loser_id,
            is_draw=False,
        )
        elo_change_1, elo_change_2 = (
            (elo_change_1, elo_change_2) if winner_id == player1_id
            else (elo_change_2, elo_change_1)
        )

    # Get current ratings
    player1 = await self._player_service.get_player(player1_id)
    player2 = await self._player_service.get_player(player2_id)

    # Apply ELO changes
    await self._player_service.update_elo(player1_id, player1.elo_rating + elo_change_1)
    await self._player_service.update_elo(player2_id, player2.elo_rating + elo_change_2)
```

---

### Algorithm: Seed Derivation

For deterministic replay, all randomness must be derivable from the match seed.

```python
def _derive_move_seed(self, match_seed: int, player_id: PlayerId, moves_remaining: int) -> int:
    """Derive a unique seed for a specific move."""
    # Combine match seed with player and move number for unique per-move seed
    player_hash = hash(str(player_id)) & 0xFFFFFFFF
    combined = (match_seed ^ player_hash ^ (moves_remaining * 1103515245)) & 0x7FFFFFFF
    return combined

def _derive_reshuffle_seed(self, match_seed: int, player_id: PlayerId, move_number: int) -> int:
    """Derive seed for deadlock reshuffle."""
    player_hash = hash(str(player_id)) & 0xFFFFFFFF
    combined = (match_seed ^ player_hash ^ (move_number * 12345)) & 0x7FFFFFFF
    return combined

def _generate_seed(self) -> int:
    """Generate a random seed for a new match."""
    import secrets
    return secrets.randbits(63)
```

---

## CLI Surface

### Commands

```bash
# Match creation
chromacrush match create --player1 <id> --player2 <id> [--seed SEED] [--type standard|competitive|casual]

# Move submission
chromacrush match move <match-id> --player <id> --from 0,1 --to 0,2

# Match queries
chromacrush match get <match-id>
chromacrush match board <match-id> --player <id>
chromacrush match history <player-id> [--status pending|in_progress|completed] [--limit N]
chromacrush match moves <match-id> [--player <id>]

# Match actions
chromacrush match forfeit <match-id> --player <id>

# Admin
chromacrush match abandon-stale
```

### Example Invocations

```bash
$ chromacrush match create --player1 abc123 --player2 def456 --type standard
Match created!
  Match ID: 550e8400-e29b-41d4-a716-446655440000
  Seed: 9876543210
  Player 1: alice (abc123)
  Player 2: bob (def456)
  Moves each: 20
  Timeout: 2026-02-08 10:30:00 UTC

$ chromacrush match move 550e8400 --player abc123 --from 0,1 --to 0,2
Move accepted!
  Move #1 for alice
  Points earned: 300
  Chain count: 2
  Moves remaining: 19
  Total score: 300

  Board:
    0 1 2 3 4 5 6 7
  0 B G Y P R O B G
  1 R P O B G Y P O
  ...

$ chromacrush match get 550e8400
Match: 550e8400-e29b-41d4-a716-446655440000
  Status: IN_PROGRESS
  Type: standard

  Player 1: alice
    Score: 1250
    Moves made: 5
    Moves remaining: 15

  Player 2: bob
    Score: 1100
    Moves made: 6
    Moves remaining: 14

  Created: 2026-02-05 10:30:00 UTC
  Timeout: 2026-02-08 10:30:00 UTC

$ chromacrush match forfeit 550e8400 --player abc123
Match forfeited!
  Match completed
  Winner: bob (def456)
  Final scores: alice=1250, bob=1100
```

### CLI Composition

Commands in `src/cli/commands/match_commands.py` use the same `MatchService` instance as the main application, injected through the CLI composition root.

---

## Edge Cases & Decisions

### EC-1: Both Players Finish Simultaneously

**Scenario:** Both players have 1 move remaining and submit their final moves at nearly the same time.

**Decision:** Whichever move is processed first updates the match. The second move sees that the first player finished, processes normally, and triggers match completion. Database transactions ensure atomic updates.

**Rationale:** No race condition because each player's state is tracked separately. Both moves are valid until their respective remaining count hits 0.

---

### EC-2: Draw (Equal Scores)

**Scenario:** Both players exhaust moves with identical final scores.

**Decision:** Match completes with `winner_id = None`. This is a valid draw. Both players receive draw ELO adjustments.

**Rationale:** Draws are rare but valid outcomes. The GDD doesn't specify draw handling, so we follow standard competitive game conventions.

---

### EC-3: Player Submits Move After Opponent Forfeits

**Scenario:** Player A forfeits while Player B is mid-move submission.

**Decision:** If forfeit is processed first, Player B's move submission fails with `CONFLICT_MATCH_ALREADY_COMPLETED`. If Player B's move is processed first, it succeeds, then forfeit fails (match may now be completed normally).

**Rationale:** First-to-database wins. Both outcomes are valid.

---

### EC-4: Board Deadlock During Match

**Scenario:** After a cascade, the board has no valid moves remaining.

**Decision:** If `match.deadlock_reshuffle=true` (default), the board is reshuffled deterministically using a derived seed. Special gems are preserved. If `match.deadlock_reshuffle=false`, the player loses their remaining moves (harsh mode).

**Rationale:** Deadlocks are frustrating. Reshuffle maintains engagement while preserving fairness (deterministic seed ensures same behavior for both players on same board).

---

### EC-5: Energy Consumed But Match Creation Fails

**Scenario:** Energy is consumed for both players but match creation fails (database error).

**Decision:** The entire operation is wrapped in a transaction. If match creation fails, energy consumption is rolled back.

**Rationale:** ACID transaction guarantees. No player should lose energy without getting a match.

---

### EC-6: Player in Multiple Active Matches

**Scenario:** Player attempts to join a match while already in one (if `allow_concurrent=false`).

**Decision:** Reject with `CONFLICT_PLAYER_IN_MATCH` and include the active match ID.

**Rationale:** Default is single-match-at-a-time for simpler UX. Configurable for different game modes.

---

### EC-7: Match Timeout While Player Has Moves

**Scenario:** 72 hours pass without either player finishing.

**Decision:** Background job (`abandon_stale_matches`) marks the match as `ABANDONED`. No winner is declared. No ELO changes. Consider refunding energy (future enhancement).

**Rationale:** Stale matches shouldn't block leaderboards or matchmaking. Abandoned status is distinct from completed.

---

### EC-8: Invalid Move (No Match Created)

**Scenario:** Player swaps two gems but the swap doesn't create a 3+ match.

**Decision:** Reject with `VALIDATION_INVALID_GEM_SWAP`. Move is not counted, board is unchanged.

**Rationale:** Standard match-3 behavior. Swaps that don't create matches are invalid.

---

### EC-9: Chromatic Orb Target Color Selection

**Scenario:** Player matches a Chromatic Orb - which color does it clear?

**Decision:** When a Chromatic Orb is matched with a standard gem, the Orb clears all gems of that standard gem's color. This is handled by the `special_gems` module, but the `match` module must pass the target color when calling `calculate_effect`.

**Rationale:** Follows standard match-3 Chromatic Orb behavior. The gem you swap the orb with determines the target.

---

### EC-10: Replay Verification

**Scenario:** Need to verify a match wasn't tampered with.

**Decision:** All moves are stored with `board_before` and `board_after`. Given the match seed, any move sequence can be replayed and verified to produce the same boards and scores.

**Rationale:** Critical for anti-cheat and dispute resolution. Deterministic seeds enable full replay verification.

---

### EC-11: Move Timestamp Validation

**Scenario:** Player submits moves with suspicious timestamps (e.g., negative, far in future).

**Decision:** Client timestamps (`Move.timestamp_ms`) are stored for analytics but not validated. Server timestamps (`MoveRecord.created_at`) are authoritative.

**Rationale:** Client clocks are unreliable. Timestamps are useful for replay visualization but not for game logic.

---

### EC-12: Special Gem Fusion During Match

**Scenario:** Player swaps two special gems together.

**Decision:** The `special_gems` module handles fusion effects. The `match` module calls `calculate_fusion_effect` and `apply_effect`, then continues with normal cascade processing.

**Rationale:** Fusion is a board operation. Match module coordinates but doesn't implement.

---

## Open Questions

None. All design decisions resolved within existing guidance and GDD specifications.

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent (match) |
