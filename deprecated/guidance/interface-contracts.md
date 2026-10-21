# Interface Contracts Guidance

**Version:** 1.6 — Updated per Karen Stage 2 P0 review
**Date:** 2026-02-06
**Author:** Interface Agent (updated by Orchestrator)
**Status:** Final
**Framework:** LLM-Orchestrated Multi-Agent Development Framework v4

---

## 1. Type Registry

All shared domain types live in `src/core/types/`. Modules import these types but NEVER define their own versions of shared concepts.

### 1.1 Core Domain Types

```python
# src/core/types/game.py
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import NewType
from uuid import UUID

# Opaque identifiers
PlayerId = NewType("PlayerId", UUID)
MatchId = NewType("MatchId", UUID)
ArtifactId = NewType("ArtifactId", UUID)
EventId = NewType("EventId", UUID)


class GemType(IntEnum):
    """
    Gem colors represented as integers for NumPy compatibility.
    Values 1-6 are standard gems, 0 is empty, negatives are special gems.
    """
    EMPTY = 0
    RED = 1
    BLUE = 2
    GREEN = 3
    YELLOW = 4
    PURPLE = 5
    ORANGE = 6
    # Special gems use negative values
    LINE_BLAST_H = -1
    LINE_BLAST_V = -2
    RADIAL_BOMB = -3
    CHROMATIC_ORB = -4


@dataclass(frozen=True)
class Position:
    """Zero-indexed board position. Origin (0,0) is top-left."""
    row: int
    col: int

    def __post_init__(self) -> None:
        if self.row < 0 or self.col < 0:
            raise ValueError("Position coordinates must be non-negative")

    def is_adjacent_to(self, other: "Position") -> bool:
        """Check if positions are orthogonally adjacent (not diagonal)."""
        row_diff = abs(self.row - other.row)
        col_diff = abs(self.col - other.col)
        return (row_diff == 1 and col_diff == 0) or (row_diff == 0 and col_diff == 1)


@dataclass(frozen=True)
class Move:
    """A player's move: swap two adjacent gems."""
    from_pos: Position
    to_pos: Position
    timestamp_ms: int  # Client timestamp for replay

    def __post_init__(self) -> None:
        if not self.from_pos.is_adjacent_to(self.to_pos):
            raise ValueError("Move positions must be adjacent")
```

### 1.2 Board State Types

```python
# src/core/types/board.py
from dataclasses import dataclass, field
from typing import Sequence
import numpy as np
from numpy.typing import NDArray

from src.core.types.game import GemType, Position


# Type alias for the board grid
BoardGrid = NDArray[np.int8]  # Shape: (height, width), dtype: int8


@dataclass
class BoardState:
    """
    Immutable snapshot of the board at a point in time.
    Use BoardState.copy() before mutation operations.
    """
    grid: BoardGrid
    width: int = field(init=False)
    height: int = field(init=False)

    def __post_init__(self) -> None:
        self.height, self.width = self.grid.shape

    def get(self, pos: Position) -> GemType:
        """Get gem at position."""
        return GemType(self.grid[pos.row, pos.col])

    def copy(self) -> "BoardState":
        """Create a mutable copy."""
        return BoardState(grid=self.grid.copy())

    def to_list(self) -> list[list[int]]:
        """Convert to JSON-serializable list."""
        return self.grid.tolist()

    @classmethod
    def from_list(cls, data: list[list[int]]) -> "BoardState":
        """Create from JSON data."""
        return cls(grid=np.array(data, dtype=np.int8))


@dataclass(frozen=True)
class MatchGroup:
    """A group of matched gems (3+ in a row/column)."""
    positions: frozenset[Position]
    gem_type: GemType
    is_horizontal: bool
    length: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "length", len(self.positions))


@dataclass(frozen=True)
class MatchResult:
    """Result of match detection on a board."""
    matches: tuple[MatchGroup, ...]
    total_gems_matched: int
    creates_special_gem: bool
    special_gem_type: GemType | None = None
    special_gem_position: Position | None = None
```

### 1.3 Match/Game State Types

The core types below define the base enumerations. The match module extends these
with richer dataclass types (`MatchType`, `PlayerMatchState`, `MatchState`) that
carry additional fields required for gameplay. See Section 4.2 for the match
module's full type definitions.

```python
# src/core/types/match.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Sequence
from uuid import UUID

from src.core.types.game import PlayerId, MatchId, Move
from src.core.types.board import BoardState


class MatchStatus(Enum):
    PENDING = "pending"          # Waiting for opponent
    IN_PROGRESS = "in_progress"  # Active gameplay
    COMPLETED = "completed"      # Finished
    ABANDONED = "abandoned"      # Player disconnected/forfeited


@dataclass
class PlayerMatchState:
    """A single player's state within a match (core base)."""
    player_id: PlayerId
    score: int = 0
    moves_made: list[Move] = field(default_factory=list)
    moves_remaining: int = 20


@dataclass
class MatchState:
    """
    Complete state of a versus match (core base).
    Both players share the same board and seed.
    """
    match_id: MatchId
    board_seed: int
    board: BoardState
    status: MatchStatus
    player1: PlayerMatchState
    player2: PlayerMatchState
    current_player_id: PlayerId | None  # None if match not started
    winner_id: PlayerId | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
```

> **Note:** The match module defines its own richer versions of `MatchStatus`,
> `MatchType`, `PlayerMatchState`, and `MatchState` in `src/modules/match/types.py`.
> These extend the core types with additional fields needed for gameplay (board per
> player, chain stats, special gem tracking, timeouts, etc.). The match module types
> are authoritative for match operations. See Section 4.2.

### 1.4 Player Types

```python
# src/core/types/player.py
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from uuid import UUID

from src.core.types.game import PlayerId


class PlayerType(Enum):
    HUMAN = "human"
    BOT = "bot"


@dataclass
class Player:
    """Core player entity."""
    id: PlayerId
    username: str
    player_type: PlayerType
    elo_rating: int = 1000
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_bot(self) -> bool:
        return self.player_type == PlayerType.BOT


@dataclass
class PlayerStats:
    """Aggregate statistics for a player."""
    player_id: PlayerId
    total_matches: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    highest_score: int = 0
    longest_chain: int = 0
    total_gems_matched: int = 0

    @property
    def win_rate(self) -> float:
        if self.total_matches == 0:
            return 0.0
        return self.wins / self.total_matches


@dataclass
class EnergyState:
    """Player's energy (hearts) state."""
    player_id: PlayerId
    hearts: int = 5
    max_hearts: int = 5
    last_regen_at: datetime = field(default_factory=datetime.utcnow)
    daily_streak: int = 0
    last_login_date: date | None = None
```

### 1.5 Auth Types

```python
# src/core/types/auth.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from src.core.types.game import PlayerId


class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


@dataclass
class AuthToken:
    """Validated authentication token."""
    token_type: TokenType
    player_id: PlayerId
    issued_at: datetime
    expires_at: datetime | None  # None for API keys (no expiry)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


@dataclass
class ApiKeyInfo:
    """API key metadata (does not contain the actual key)."""
    key_id: UUID
    player_id: PlayerId
    prefix: str  # First 8 chars for identification
    created_at: datetime
    last_used_at: datetime | None = None
    revoked: bool = False
```

---

## 2. Error Taxonomy

All errors flow through the injected `ErrorService`. No bare `raise Exception()` or `raise ValueError()`.

### 2.1 Error Base Class

```python
# src/core/errors.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class AppError(Exception):
    """
    Base error type for all application errors.
    Contains structured context for logging and API responses.
    """
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    http_status: int = 500

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API response."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp.isoformat(),
            }
        }
```

### 2.2 Error Categories

#### Validation Errors (400)

| Code | Message Template | Context Fields | When to Use |
|------|------------------|----------------|-------------|
| `VALIDATION_INVALID_INPUT` | `"Invalid input: {field}"` | `field`, `value`, `reason` | Malformed request data |
| `VALIDATION_POSITIONS_NOT_ADJACENT` | `"Positions must be adjacent"` | `from_pos`, `to_pos` | Non-adjacent swap attempt |
| `VALIDATION_OUT_OF_BOUNDS` | `"Position out of bounds"` | `position`, `board_width`, `board_height` | Position outside grid |
| `VALIDATION_NO_MOVES_REMAINING` | `"No moves remaining"` | `player_id`, `match_id` | Move attempt when depleted |
| `VALIDATION_INVALID_GEM_SWAP` | `"Cannot swap these gems"` | `from_gem`, `to_gem`, `reason` | Invalid swap (e.g., empty cell) |
| `VALIDATION_WEAK_PASSWORD` | `"Password does not meet requirements"` | `requirements` | Password validation failure |
| `VALIDATION_RECEIPT_INVALID` | `"Receipt validation failed"` | `provider`, `reason` | Payment receipt invalid |
| `VALIDATION_RECEIPT_WRONG_PRODUCT` | `"Receipt for different product"` | `expected_product`, `actual_product` | Receipt product mismatch |
| `VALIDATION_RECEIPT_WRONG_PLAYER` | `"Receipt tied to different user"` | `player_id` | Receipt player mismatch |
| `VALIDATION_INVALID_REFUND_NOTIFICATION` | `"Malformed refund notification"` | `provider`, `reason` | Bad refund webhook data |
| `VALIDATION_INSUFFICIENT_BALANCE` | `"Insufficient earnings balance"` | `available_cents`, `requested_cents` | Bot payout exceeds balance |
| `VALIDATION_BELOW_PAYOUT_THRESHOLD` | `"Balance below minimum payout threshold"` | `available_cents`, `minimum_cents` | Bot balance too low for payout |
| `VALIDATION_DATE_RANGE_TOO_LARGE` | `"Date range exceeds maximum"` | `days_requested`, `max_days` | Query date range too wide |
| `VALIDATION_REWARDED_AD_NOT_COMPLETED` | `"Rewarded ad was not fully completed"` | `ad_request_id`, `watched_duration_ms` | Rewarded video not watched to completion |
| `VALIDATION_NOT_IN_QUEUE` | `"Player is not in the matchmaking queue"` | `player_id` | Queue operation on non-queued player |

#### Not Found Errors (404)

| Code | Message Template | Context Fields | When to Use |
|------|------------------|----------------|-------------|
| `NOT_FOUND_PLAYER` | `"Player not found"` | `player_id` | Player ID doesn't exist |
| `NOT_FOUND_MATCH` | `"Match not found"` | `match_id` | Match ID doesn't exist |
| `NOT_FOUND_ARTIFACT` | `"Artifact not found"` | `artifact_id` | Vault artifact missing |
| `NOT_FOUND_EVENT` | `"Event not found"` | `event_id` | Event doesn't exist |
| `NOT_FOUND_QUEUE_ENTRY` | `"Player not in matchmaking queue"` | `player_id`, `queue_type` | Leaving queue when not queued |
| `NOT_FOUND_PRODUCT` | `"Product not found"` | `product_id` | Payment product doesn't exist |
| `NOT_FOUND_PURCHASE` | `"Purchase not found"` | `purchase_id` | Purchase record missing |
| `NOT_FOUND_PAYOUT_REQUEST` | `"Payout request not found"` | `payout_request_id` | Bot payout request missing |
| `NOT_FOUND_AD_REQUEST` | `"Ad request not found"` | `ad_request_id` | Ad request ID doesn't exist |
| `NOT_FOUND_AD_OPPORTUNITY` | `"Ad opportunity not found"` | `opportunity_id` | Event ad opportunity missing |

#### Authentication Errors (401)

| Code | Message Template | Context Fields | When to Use |
|------|------------------|----------------|-------------|
| `AUTH_INVALID_CREDENTIALS` | `"Invalid username or password"` | - | Login failure |
| `AUTH_TOKEN_EXPIRED` | `"Token has expired"` | `expired_at` | JWT past expiry |
| `AUTH_TOKEN_INVALID` | `"Invalid token"` | `reason` | Malformed/tampered token |
| `AUTH_API_KEY_INVALID` | `"Invalid API key"` | - | API key not found |
| `AUTH_API_KEY_REVOKED` | `"API key has been revoked"` | `key_id` | Revoked API key used |
| `AUTH_INVALID_WEBHOOK_SIGNATURE` | `"Webhook signature verification failed"` | `provider` | Payment webhook auth failed |
| `AUTH_API_KEY_NOT_FOUND` | `"API key not found"` | `key_id` | API key doesn't exist |

#### Authorization Errors (403)

| Code | Message Template | Context Fields | When to Use |
|------|------------------|----------------|-------------|
| `FORBIDDEN_NOT_YOUR_TURN` | `"Not your turn"` | `match_id`, `current_player_id` | Wrong player attempting move |
| `FORBIDDEN_NOT_MATCH_PARTICIPANT` | `"You are not a participant in this match"` | `match_id`, `player_id` | Accessing match without permission |
| `FORBIDDEN_VAULT_PROTECTED` | `"Vault is protected by shield"` | `shield_expires_at` | Raid blocked by shield |
| `FORBIDDEN_INSUFFICIENT_ENERGY` | `"Not enough hearts"` | `required`, `available` | Action requires more energy |
| `FORBIDDEN_NOT_BOT_OWNER` | `"Not authorized for this bot"` | `bot_player_id`, `requester_id` | Non-owner requesting bot payout |
| `FORBIDDEN_NOT_BOT` | `"Action requires bot account"` | `player_id` | Human trying bot-only action |
| `FORBIDDEN_BOT_NOT_ALLOWED` | `"This endpoint is for human players only"` | `player_id` | Bot accessing human-only endpoint |
| `FORBIDDEN_NOT_KEY_OWNER` | `"Not authorized for this API key"` | `key_id`, `requester_id` | Non-owner managing API key |
| `FORBIDDEN_PLAYER_AD_FREE` | `"Player has ad-free status"` | `player_id` | Ad shown to ad-free player |
| `FORBIDDEN_NOT_EVENT_PARTICIPANT` | `"Not a participant in this event"` | `player_id`, `event_id` | Action requires event participation |
| `FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET` | `"Event entry requirements not met"` | `player_id`, `event_id`, `requirements` | Player doesn't meet event prerequisites |
| `FORBIDDEN_CANNOT_LEAVE_EVENT` | `"Cannot leave this event"` | `player_id`, `event_id`, `reason` | Event leave not allowed (e.g., in-progress match) |
| `FORBIDDEN_POOL_RESTRICTED` | `"Player not eligible for this matchmaking pool"` | `player_id`, `pool_type`, `reason` | Player doesn't meet pool requirements |
| `FORBIDDEN_NOT_ADMIN` | `"Admin privileges required"` | `requester_id`, `operation` | Non-admin attempting admin-only operation |

#### Conflict Errors (409)

| Code | Message Template | Context Fields | When to Use |
|------|------------------|----------------|-------------|
| `CONFLICT_MATCH_ALREADY_COMPLETED` | `"Match has already completed"` | `match_id`, `completed_at` | Action on finished match |
| `CONFLICT_PLAYER_IN_MATCH` | `"Player already in active match"` | `player_id`, `active_match_id` | Starting new match while in one |
| `CONFLICT_USERNAME_TAKEN` | `"Username already exists"` | `username` | Registration with existing name |
| `CONFLICT_DUPLICATE_MOVE` | `"Move already submitted"` | `move_index` | Re-submitting same move |
| `CONFLICT_ALREADY_IN_QUEUE` | `"Player already in matchmaking queue"` | `player_id`, `queue_type` | Joining queue when already queued |
| `CONFLICT_RECEIPT_ALREADY_PROCESSED` | `"Receipt already processed"` | `transaction_id` | Duplicate payment receipt |
| `CONFLICT_PURCHASE_ALREADY_REFUNDED` | `"Purchase already refunded"` | `purchase_id` | Double refund attempt |
| `CONFLICT_PLAYER_ALREADY_AD_FREE` | `"Player already has ad-free status"` | `player_id` | Redundant ad-free purchase |
| `CONFLICT_PURCHASE_INTENT_EXPIRED` | `"Purchase intent has expired"` | `intent_id`, `expired_at` | Purchase timeout |
| `CONFLICT_PENDING_PAYOUT_EXISTS` | `"Pending payout request exists"` | `bot_player_id`, `existing_request_id` | Bot already has pending payout |
| `CONFLICT_PAYOUT_NOT_PENDING` | `"Payout request not in pending status"` | `payout_request_id`, `current_status` | Process/cancel non-pending payout |
| `CONFLICT_SYNC_IN_PROGRESS` | `"Attribution sync already in progress"` | `bot_player_id`, `started_at` | Concurrent bot earnings sync |
| `CONFLICT_DUPLICATE_BONUS` | `"Daily bonus already claimed"` | `player_id`, `bonus_type`, `claimed_at` | Duplicate daily bonus claim |
| `CONFLICT_MAX_MATCHES_REACHED` | `"Maximum event matches reached"` | `player_id`, `event_id`, `max_matches` | Event participation limit hit |
| `CONFLICT_EVENT_NOT_ACTIVE` | `"Event is not currently active"` | `event_id`, `status` | Action on inactive event |
| `CONFLICT_EVENT_ALREADY_FINALIZED` | `"Event has already been finalized"` | `event_id` | Modifying finalized event |
| `CONFLICT_ALREADY_PARTICIPANT` | `"Already a participant in this event"` | `player_id`, `event_id` | Duplicate event join |
| `CONFLICT_EVENT_AT_CAPACITY` | `"Event has reached maximum participants"` | `event_id`, `max_participants` | Event full |
| `CONFLICT_AD_ALREADY_RECORDED` | `"Ad impression already recorded"` | `ad_request_id` | Duplicate ad impression |
| `CONFLICT_AD_REQUEST_EXPIRED` | `"Ad request has expired"` | `ad_request_id`, `expired_at` | Ad request timeout |
| `CONFLICT_OPPORTUNITY_ALREADY_CLAIMED` | `"Ad opportunity already claimed"` | `opportunity_id`, `player_id` | Duplicate event ad claim |
| `CONFLICT_SHIELD_ALREADY_ACTIVE` | `"Vault shield is already active"` | `player_id`, `shield_expires_at` | Activating shield when one exists |
| `CONFLICT_RAID_COOLDOWN` | `"Raid cooldown has not expired"` | `player_id`, `cooldown_expires_at` | Raiding before cooldown ends |

#### Rate Limit Errors (429)

| Code | Message Template | Context Fields | When to Use |
|------|------------------|----------------|-------------|
| `RATE_LIMIT_EXCEEDED` | `"Rate limit exceeded"` | `limit`, `window_seconds`, `retry_after` | Too many requests |
| `RATE_LIMIT_API_KEY` | `"API key rate limit exceeded"` | `key_id`, `retry_after` | Bot API throttled |
| `RATE_LIMIT_QUEUE_FULL` | `"Matchmaking queue is at capacity"` | `queue_type`, `retry_after` | Queue full, try again later |
| `RATE_LIMIT_AD_COOLDOWN` | `"Ad cooldown has not expired"` | `player_id`, `ad_type`, `retry_after` | Ad requested too soon |
| `RATE_LIMIT_OPPORTUNITY_COOLDOWN` | `"Event ad opportunity cooldown active"` | `opportunity_id`, `retry_after` | Event ad claimed too recently |

#### Internal Errors (500)

| Code | Message Template | Context Fields | When to Use |
|------|------------------|----------------|-------------|
| `INTERNAL_DATABASE_ERROR` | `"Database operation failed"` | `operation` | DB query failure |
| `INTERNAL_CACHE_ERROR` | `"Cache operation failed"` | `operation` | Redis failure |
| `INTERNAL_MATCHMAKING_EXPANSION_FAILED` | `"Matchmaking ELO expansion failed"` | `player_id`, `current_range` | ELO expansion algorithm error |
| `INTERNAL_PAYMENT_PROVIDER_ERROR` | `"Payment provider error"` | `provider`, `operation` | External payment API failure |
| `INTERNAL_ADS_SERVICE_ERROR` | `"Ads service error"` | `operation`, `error` | Ads module call failed |
| `INTERNAL_AD_PROVIDER_ERROR` | `"Ad provider error"` | `provider`, `operation`, `error` | External ad provider API failure |
| `INTERNAL_UNEXPECTED` | `"An unexpected error occurred"` | `original_error` | Catch-all for unhandled |

### 2.3 Error Service Protocol

```python
# src/core/protocols/error_service.py
from typing import Protocol, Any, NoReturn

from src.core.errors import AppError


class ErrorServiceProtocol(Protocol):
    """Protocol for the error service. Injected into all modules."""

    def validation(
        self,
        message: str,
        code: str = "VALIDATION_INVALID_INPUT",
        **context: Any,
    ) -> AppError:
        """Create a validation error (400)."""
        ...

    def not_found(
        self,
        message: str,
        code: str = "NOT_FOUND_RESOURCE",
        **context: Any,
    ) -> AppError:
        """Create a not found error (404)."""
        ...

    def unauthorized(
        self,
        message: str,
        code: str = "AUTH_INVALID_CREDENTIALS",
        **context: Any,
    ) -> AppError:
        """Create an authentication error (401)."""
        ...

    def forbidden(
        self,
        message: str,
        code: str = "FORBIDDEN_ACCESS_DENIED",
        **context: Any,
    ) -> AppError:
        """Create an authorization error (403)."""
        ...

    def conflict(
        self,
        message: str,
        code: str = "CONFLICT_STATE",
        **context: Any,
    ) -> AppError:
        """Create a conflict error (409)."""
        ...

    def rate_limited(
        self,
        message: str,
        retry_after: int,
        code: str = "RATE_LIMIT_EXCEEDED",
        **context: Any,
    ) -> AppError:
        """Create a rate limit error (429)."""
        ...

    def internal(
        self,
        message: str,
        code: str = "INTERNAL_UNEXPECTED",
        **context: Any,
    ) -> AppError:
        """Create an internal error (500)."""
        ...
```

### 2.4 Error Usage Examples

```python
# DO: Use error service with specific codes
class BoardService:
    def __init__(self, errors: ErrorServiceProtocol, ...):
        self._errors = errors

    def swap_gems(self, board: BoardState, move: Move) -> BoardState:
        if not self._is_in_bounds(board, move.from_pos):
            raise self._errors.validation(
                "Position out of bounds",
                code="VALIDATION_OUT_OF_BOUNDS",
                position=move.from_pos,
                board_width=board.width,
                board_height=board.height,
            )

        if not move.from_pos.is_adjacent_to(move.to_pos):
            raise self._errors.validation(
                "Positions must be adjacent",
                code="VALIDATION_POSITIONS_NOT_ADJACENT",
                from_pos=move.from_pos,
                to_pos=move.to_pos,
            )

        # ... proceed with swap


# DON'T: Bare raises
def swap_gems(self, board: BoardState, move: Move) -> BoardState:
    if not self._is_in_bounds(board, move.from_pos):
        raise ValueError("Position out of bounds")  # VIOLATION
```

---

## 3. Correlation ID Contract

Every request gets a correlation ID that flows through all operations for tracing and debugging.

### 3.1 Correlation ID Format

```
cc_{timestamp_hex}_{random_hex}
```

Example: `cc_18d4f2a8_7b3e9c1d`

### 3.2 Correlation Context Protocol

```python
# src/core/protocols/correlation.py
from typing import Protocol
from contextvars import ContextVar

# Context variable for async-safe correlation ID propagation
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationContextProtocol(Protocol):
    """Protocol for correlation ID management."""

    def get_id(self) -> str:
        """Get current correlation ID. Creates one if none exists."""
        ...

    def set_id(self, correlation_id: str) -> None:
        """Set correlation ID for current context."""
        ...

    def clear(self) -> None:
        """Clear correlation ID from context."""
        ...
```

### 3.3 Middleware Integration

```python
# src/presentation/middleware/correlation.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import secrets


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Attaches correlation ID to every request."""

    HEADER_NAME = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next):
        # Use provided correlation ID or generate new one
        correlation_id = request.headers.get(self.HEADER_NAME)
        if not correlation_id:
            correlation_id = self._generate_id()

        # Set in context for downstream services
        correlation_id_var.set(correlation_id)

        # Proceed with request
        response = await call_next(request)

        # Include in response headers
        response.headers[self.HEADER_NAME] = correlation_id

        return response

    def _generate_id(self) -> str:
        timestamp_hex = format(int(time.time()), "x")
        random_hex = secrets.token_hex(4)
        return f"cc_{timestamp_hex}_{random_hex}"
```

### 3.4 Logging with Correlation ID

```python
# All log entries automatically include correlation ID
logger.info(
    "Match started",
    match_id=match.id,
    players=[p1.id, p2.id],
    # correlation_id is automatically injected by logger service
)

# Output:
# {"level": "INFO", "message": "Match started", "match_id": "...",
#  "players": ["...", "..."], "correlation_id": "cc_18d4f2a8_7b3e9c1d", ...}
```

### 3.5 Error Responses Include Correlation ID

```json
{
    "error": {
        "code": "VALIDATION_POSITIONS_NOT_ADJACENT",
        "message": "Positions must be adjacent",
        "correlation_id": "cc_18d4f2a8_7b3e9c1d",
        "timestamp": "2026-02-05T12:34:56.789Z"
    }
}
```

---

## 4. Module Interface Schemas

### 4.1 Board Module

```python
# src/modules/board/protocols.py
from typing import Protocol

from src.core.types.board import BoardState, MatchResult, MatchGroup
from src.core.types.game import GemType, Move, Position


class BoardServiceProtocol(Protocol):
    """Public interface for the board module."""

    def create_board(
        self,
        width: int,
        height: int,
        seed: int,
    ) -> BoardState:
        """
        Create a new board with random gem placement.

        Args:
            width: Board width (typically 8).
            height: Board height (typically 8).
            seed: RNG seed for deterministic generation.

        Returns:
            BoardState with no initial matches.
        """
        ...

    def swap_gems(
        self,
        board: BoardState,
        move: Move,
    ) -> BoardState:
        """
        Swap two adjacent gems.

        Args:
            board: Current board state.
            move: The swap move to execute.

        Returns:
            New BoardState with gems swapped.

        Raises:
            VALIDATION_OUT_OF_BOUNDS: If position outside grid.
            VALIDATION_POSITIONS_NOT_ADJACENT: If not adjacent.
            VALIDATION_INVALID_GEM_SWAP: If swapping empty cell.
        """
        ...

    def detect_matches(
        self,
        board: BoardState,
        min_length: int = 3,
    ) -> MatchResult:
        """
        Find all matches on the board.

        Args:
            board: Board state to analyze.
            min_length: Minimum gems for a match (default 3).

        Returns:
            MatchResult with all found matches.
        """
        ...

    def clear_matches(
        self,
        board: BoardState,
        matches: MatchResult,
    ) -> BoardState:
        """
        Set all matched positions to EMPTY, returning a new board.

        Args:
            board: Current board state (unmodified).
            matches: The match result whose positions should be cleared.

        Returns:
            New BoardState with matched cells set to GemType.EMPTY.
        """
        ...

    def apply_gravity(
        self,
        board: BoardState,
    ) -> tuple[BoardState, list["GemDrop"]]:
        """
        Drop gems down to fill empty spaces within each column.

        Args:
            board: Board with empty cells after match clearing.

        Returns:
            Tuple of (new BoardState, list of GemDrop records).
        """
        ...

    def fill_empty(
        self,
        board: BoardState,
        seed: int,
    ) -> tuple[BoardState, list["GemSpawn"]]:
        """
        Fill empty cells with new random standard gems.

        Args:
            board: Board with empty cells (typically after gravity).
            seed: RNG seed for reproducible gem generation.

        Returns:
            Tuple of (new BoardState, list of GemSpawn records).
        """
        ...

    def process_move(
        self,
        board: BoardState,
        move: Move,
        seed: int,
    ) -> "MoveProcessingResult":
        """
        Full move processing: swap, match, cascade until stable.

        Args:
            board: Starting board state.
            move: The move to process.
            seed: RNG seed for cascades.

        Returns:
            Complete result including all cascade steps.

        Raises:
            VALIDATION_OUT_OF_BOUNDS: If position outside grid.
            VALIDATION_POSITIONS_NOT_ADJACENT: If not adjacent.
            VALIDATION_INVALID_GEM_SWAP: If swapping empty cell.
        """
        ...

    def validate_board(
        self,
        board: BoardState,
    ) -> bool:
        """
        Check whether a board has valid dimensions and gem values.

        Args:
            board: The board to validate.

        Returns:
            True if valid, False otherwise.
        """
        ...

    def has_valid_moves(
        self,
        board: BoardState,
    ) -> bool:
        """
        Check whether at least one adjacent swap produces a match.

        Args:
            board: Board to check for deadlock.

        Returns:
            True if at least one valid move exists, False if deadlocked.
        """
        ...


# --- Board Module Types (src/modules/board/types.py) ---


@dataclass(frozen=True)
class GemDrop:
    """Record of a gem falling due to gravity."""
    gem_type: GemType
    from_pos: Position
    to_pos: Position
    distance: int


@dataclass(frozen=True)
class GemSpawn:
    """Record of a new gem spawned to fill an empty cell."""
    gem_type: GemType
    position: Position
    column: int


@dataclass
class CascadeStep:
    """One step in the cascade loop after a move.

    Each step represents: detect matches -> clear -> gravity -> fill.
    """
    step_number: int
    matches: MatchResult
    board_after_clear: BoardState
    gems_dropped: list[GemDrop]
    board_after_gravity: BoardState
    gems_spawned: list[GemSpawn]
    board_after_fill: BoardState


@dataclass
class MoveProcessingResult:
    """Complete result of processing a player's move.

    Includes the full cascade history, special gem creation records,
    and aggregate statistics.
    """
    initial_board: BoardState
    final_board: BoardState
    move: Move
    was_valid_match: bool
    cascades: list[CascadeStep]
    total_matches: int
    total_gems_cleared: int
    chain_count: int
    special_gems_created: list[tuple[Position, GemType]]
```

### 4.2 Match Module

```python
# src/modules/match/protocols.py
from typing import Protocol
from uuid import UUID

from src.core.types.board import BoardState
from src.core.types.game import PlayerId, MatchId, Move


class MatchServiceProtocol(Protocol):
    """Public interface for the match module."""

    async def create_match(
        self,
        player1_id: PlayerId,
        player2_id: PlayerId,
        board_seed: int | None = None,
        match_type: "MatchType" = MatchType.STANDARD,
    ) -> "MatchState":
        """
        Create a new versus match.

        Args:
            player1_id: First player.
            player2_id: Second player.
            board_seed: Optional seed for board generation (random if None).
            match_type: Rule set variant (default: STANDARD).

        Returns:
            Initial MatchState with PENDING status.

        Raises:
            VALIDATION_INVALID_INPUT: If player1_id == player2_id.
            NOT_FOUND_PLAYER: If either player doesn't exist.
        """
        ...

    async def submit_move(
        self,
        match_id: MatchId,
        player_id: PlayerId,
        move: Move,
    ) -> "MoveSubmissionResult":
        """
        Submit a move for a player in an active match.

        Args:
            match_id: The match.
            player_id: Who is making the move.
            move: The swap to perform.

        Returns:
            MoveSubmissionResult with updated match state and move details.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
            VALIDATION_INVALID_INPUT: If player not in match or out of moves.
            CONFLICT_MATCH_ALREADY_COMPLETED: If match already finished.
            VALIDATION_INVALID_GEM_SWAP: If move is invalid.
        """
        ...

    async def get_match(
        self,
        match_id: MatchId,
    ) -> "MatchState":
        """
        Get current state of a match.

        Args:
            match_id: The match to retrieve.

        Returns:
            Current MatchState.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
        """
        ...

    async def get_player_board(
        self,
        match_id: MatchId,
        player_id: PlayerId,
    ) -> "PlayerBoardState":
        """
        Get a player's current board state and progress.

        Args:
            match_id: The match.
            player_id: The player.

        Returns:
            PlayerBoardState with current board and move counts.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
            VALIDATION_INVALID_INPUT: If player not in match.
        """
        ...

    async def get_active_matches(
        self,
        player_id: PlayerId,
    ) -> list["MatchState"]:
        """
        Get all active matches for a player (PENDING or IN_PROGRESS).

        Args:
            player_id: The player.

        Returns:
            List of active MatchState objects.
        """
        ...

    async def get_match_history(
        self,
        player_id: PlayerId,
        limit: int = 20,
        offset: int = 0,
    ) -> "PaginatedResult[MatchSummary]":
        """
        Get match history for a player.

        Args:
            player_id: The player.
            limit: Maximum results (1-100, default 20).
            offset: Pagination offset.

        Returns:
            PaginatedResult containing MatchSummary objects.
        """
        ...

    async def get_move_history(
        self,
        match_id: MatchId,
        player_id: PlayerId | None = None,
    ) -> list["MoveRecord"]:
        """
        Get move history for a match, optionally filtered by player.

        Args:
            match_id: The match.
            player_id: If provided, return only moves by this player.

        Returns:
            List of MoveRecord objects in chronological order.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
        """
        ...

    async def forfeit_match(
        self,
        match_id: MatchId,
        player_id: PlayerId,
    ) -> "MatchState":
        """
        Forfeit a match, marking the opponent as winner.

        Args:
            match_id: The match.
            player_id: Who is forfeiting.

        Returns:
            Updated MatchState with COMPLETED status.

        Raises:
            NOT_FOUND_MATCH: If match doesn't exist.
            VALIDATION_INVALID_INPUT: If player not in match.
            CONFLICT_MATCH_ALREADY_COMPLETED: If match already finished.
        """
        ...

    async def abandon_stale_matches(self) -> int:
        """
        Abandon matches that have exceeded their timeout.

        Returns:
            Number of matches abandoned.
        """
        ...


# --- Match Module Types (src/modules/match/types.py) ---

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class MatchStatus(Enum):
    """Match lifecycle states (match-module version)."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MatchType(Enum):
    """Match types with different rule sets."""
    STANDARD = "standard"
    COMPETITIVE = "competitive"
    CASUAL = "casual"
    TUTORIAL = "tutorial"


@dataclass
class PlayerMatchState:
    """Individual player's state within a match (match-module version).

    Extended with per-player board, chain stats, and special gem tracking.
    """
    player_id: PlayerId
    player_username: str
    score: int = 0
    moves_made: int = 0
    moves_remaining: int = 20
    current_board: BoardState | None = None
    longest_chain: int = 0
    special_gems_created: int = 0
    special_gems_activated: int = 0
    total_gems_cleared: int = 0
    finished_at: datetime | None = None


@dataclass
class MatchState:
    """Complete state of a versus match (match-module version).

    Extended with match_type, per-player boards, forfeit tracking, and timeout.
    """
    match_id: MatchId
    board_seed: int
    initial_board: BoardState
    status: MatchStatus
    match_type: MatchType
    player1: PlayerMatchState
    player2: PlayerMatchState
    winner_id: PlayerId | None = None
    forfeit_by: PlayerId | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    timeout_at: datetime | None = None


@dataclass
class MoveSubmissionResult:
    """Result of submitting a move in a match.

    Contains updated match state, move processing results, scoring,
    and metadata about match progression.
    """
    match_state: MatchState
    move_result: MoveProcessingResult  # from src.modules.board.types
    score_result: MoveScore            # from src.modules.scoring.types
    special_effects: list[SpecialGemEffect]  # from src.modules.special_gems.types
    points_earned: int
    move_number: int
    moves_remaining: int
    match_completed: bool
    player_finished: bool
    winner_id: PlayerId | None = None


@dataclass
class MatchSummary:
    """Summary for match history and profile views."""
    match_id: MatchId
    opponent_id: PlayerId
    opponent_username: str
    player_score: int
    opponent_score: int
    won: bool | None  # None = draw or in-progress
    status: MatchStatus
    match_type: MatchType
    created_at: datetime
    completed_at: datetime | None


@dataclass
class MoveRecord:
    """Historical record of a single move in a match."""
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
    """Current board state and progress for a player in a match."""
    player_id: PlayerId
    board: BoardState
    moves_made: int
    moves_remaining: int
    score: int
    has_valid_moves: bool
```

### 4.3 Player Module

```python
# src/modules/player/protocols.py
from typing import Protocol

from src.core.types.game import PlayerId
from src.core.types.player import Player, PlayerStats, PlayerType, EnergyState


class PlayerServiceProtocol(Protocol):
    """Public interface for the player module."""

    # ========== Player Account Operations ==========

    async def create_player(
        self,
        username: str,
        player_type: PlayerType,
        password_hash: str | None = None,
    ) -> Player:
        """
        Create a new player account.

        Args:
            username: Unique username (case-insensitive, 3-32 chars, alphanumeric + underscore).
            player_type: PlayerType.HUMAN or PlayerType.BOT.
            password_hash: Required for humans (None allowed for CLI/testing), must be None for bots.

        Returns:
            Created Player entity.

        Raises:
            VALIDATION_INVALID_INPUT: If username format invalid or bot has password_hash.
            CONFLICT_USERNAME_TAKEN: If username already exists (case-insensitive).
        """
        ...

    async def get_player(
        self,
        player_id: PlayerId,
    ) -> Player:
        """
        Get player by ID.

        Args:
            player_id: The player's unique identifier.

        Returns:
            Player entity.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist or is soft-deleted.
        """
        ...

    async def get_player_by_username(
        self,
        username: str,
    ) -> Player | None:
        """
        Get player by username (case-insensitive lookup).

        Args:
            username: The username to look up.

        Returns:
            Player if found and not soft-deleted, None otherwise.
        """
        ...

    async def update_player(
        self,
        player_id: PlayerId,
        updates: "PlayerUpdate",
    ) -> Player:
        """
        Update player profile fields.

        Args:
            player_id: The player to update.
            updates: Fields to update (username, email).

        Returns:
            Updated Player entity.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If new username format is invalid.
            CONFLICT_USERNAME_TAKEN: If new username conflicts with existing.
        """
        ...

    async def soft_delete_player(
        self,
        player_id: PlayerId,
    ) -> None:
        """
        Soft-delete a player account.

        Sets deleted_at timestamp. Username is released by appending
        deletion timestamp suffix.

        Args:
            player_id: The player to delete.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist or already deleted.
        """
        ...

    async def list_players(
        self,
        player_type: PlayerType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> "PaginatedResult[Player]":
        """
        List players with optional filtering.

        Args:
            player_type: Filter by human or bot (None for all).
            limit: Maximum results (1-100, default 50).
            offset: Pagination offset.

        Returns:
            PaginatedResult containing players and pagination metadata.

        Raises:
            VALIDATION_INVALID_INPUT: If limit out of range.
        """
        ...

    # ========== ELO Rating Operations ==========

    async def get_elo(
        self,
        player_id: PlayerId,
    ) -> int:
        """
        Get player's current ELO rating.

        Args:
            player_id: The player.

        Returns:
            Current ELO rating integer.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def update_elo(
        self,
        player_id: PlayerId,
        new_rating: int,
    ) -> Player:
        """
        Update player's ELO rating.

        Args:
            player_id: The player to update.
            new_rating: New ELO value (must be >= 0).

        Returns:
            Updated Player entity.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If new_rating < 0.
        """
        ...

    async def calculate_elo_change(
        self,
        winner_id: PlayerId,
        loser_id: PlayerId,
        is_draw: bool = False,
    ) -> tuple[int, int]:
        """
        Calculate ELO changes for a match outcome (does NOT persist).

        Args:
            winner_id: The winning player (or either player if draw).
            loser_id: The losing player (or other player if draw).
            is_draw: Whether the match was a draw.

        Returns:
            Tuple of (winner_elo_change, loser_elo_change).

        Raises:
            NOT_FOUND_PLAYER: If either player doesn't exist.
            VALIDATION_INVALID_INPUT: If both IDs are the same player.
        """
        ...

    # ========== Statistics Operations ==========

    async def get_stats(
        self,
        player_id: PlayerId,
    ) -> PlayerStats:
        """
        Get player statistics.

        Args:
            player_id: The player to get stats for.

        Returns:
            PlayerStats aggregate.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def record_match_result(
        self,
        player_id: PlayerId,
        won: bool,
        is_draw: bool,
        score: int,
        longest_chain: int,
        gems_matched: int,
    ) -> PlayerStats:
        """
        Record a match result in player statistics.

        Args:
            player_id: The player.
            won: Whether player won (ignored if is_draw).
            is_draw: Whether match was a draw.
            score: Player's final score in the match.
            longest_chain: Longest cascade chain achieved.
            gems_matched: Total gems matched in the match.

        Returns:
            Updated PlayerStats.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Energy State Data Access ==========

    async def get_energy_state(
        self,
        player_id: PlayerId,
    ) -> EnergyState:
        """
        Get player's energy state (raw data access).

        Args:
            player_id: The player.

        Returns:
            Current EnergyState.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def update_energy_state(
        self,
        player_id: PlayerId,
        energy_update: "EnergyStateUpdate",
    ) -> EnergyState:
        """
        Update player's energy state.

        Args:
            player_id: The player.
            energy_update: Fields to update.

        Returns:
            Updated EnergyState.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If hearts < 0 or > max_hearts.
        """
        ...

    async def initialize_energy_state(
        self,
        player_id: PlayerId,
    ) -> EnergyState:
        """
        Initialize energy state for new player.

        Called internally during player creation. Sets up default
        energy state (max hearts, current timestamp, zero streak).

        Args:
            player_id: The newly created player.

        Returns:
            Initialized EnergyState.
        """
        ...


# --- Player Module DTOs (src/modules/player/dto.py) ---


@dataclass
class PlayerUpdate:
    """Fields that can be updated on a player profile."""
    username: str | None = None
    email: str | None = None


@dataclass
class EnergyStateUpdate:
    """Fields that can be updated on energy state."""
    hearts: int | None = None
    last_regen_at: datetime | None = None
    daily_streak: int | None = None
    last_login_date: date | None = None


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated query result with metadata."""
    items: list[T]
    total: int
    limit: int
    offset: int
```

### 4.4 Auth Module

```python
# src/modules/auth/protocols.py
from typing import Protocol
from uuid import UUID

from src.core.types.game import PlayerId
from src.core.types.auth import AuthToken, ApiKeyInfo


class AuthServiceProtocol(Protocol):
    """Public interface for the auth module."""

    # ========== Human Authentication ==========

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> "AuthResult":
        """
        Authenticate human user with credentials.

        Args:
            username: Player's username (case-insensitive lookup).
            password: Plain-text password to verify against stored hash.

        Returns:
            AuthResult containing access_token, refresh_token, expiry info.

        Raises:
            AUTH_INVALID_CREDENTIALS: If username not found or password incorrect.
            AUTH_INVALID_CREDENTIALS: If player is a bot (bots use API keys).
        """
        ...

    async def validate_token(
        self,
        token: str,
    ) -> AuthToken:
        """
        Validate a JWT access token or API key.

        Args:
            token: The token string (JWT or API key).

        Returns:
            Validated AuthToken with player_id, token_type, expiry info.

        Raises:
            AUTH_TOKEN_INVALID: If JWT signature invalid or malformed.
            AUTH_TOKEN_EXPIRED: If JWT has expired.
            AUTH_API_KEY_INVALID: If API key not found in database.
            AUTH_API_KEY_REVOKED: If API key has been revoked.
        """
        ...

    async def refresh_token(
        self,
        refresh_token: str,
    ) -> "AuthResult":
        """
        Get new access token using refresh token.

        Validates the refresh token, invalidates it (single-use), and issues
        a new access/refresh token pair (refresh token rotation).

        Args:
            refresh_token: Valid refresh token from previous authentication.

        Returns:
            New AuthResult with fresh access_token and refresh_token.

        Raises:
            AUTH_TOKEN_INVALID: If refresh token format invalid or already used.
            AUTH_TOKEN_EXPIRED: If refresh token has expired.
        """
        ...

    async def logout(
        self,
        player_id: PlayerId,
        session_id: UUID | None = None,
    ) -> None:
        """
        Invalidate a session or all sessions for a player.

        Args:
            player_id: The player logging out.
            session_id: Specific session to invalidate. If None, invalidates all.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def get_active_sessions(
        self,
        player_id: PlayerId,
    ) -> list["SessionInfo"]:
        """
        List all active sessions for a player.

        Args:
            player_id: The player to list sessions for.

        Returns:
            List of SessionInfo with session details.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== API Key Management (Bots) ==========

    async def create_api_key(
        self,
        player_id: PlayerId,
        description: str | None = None,
    ) -> "ApiKeyCreationResult":
        """
        Create a new API key for a bot player.

        Args:
            player_id: The bot player's ID.
            description: Optional description for the key.

        Returns:
            ApiKeyCreationResult containing key_info and raw_key.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            FORBIDDEN_NOT_BOT: If player is not a bot.
            VALIDATION_INVALID_INPUT: If description exceeds 255 characters.
        """
        ...

    async def revoke_api_key(
        self,
        key_id: UUID,
        player_id: PlayerId,
    ) -> None:
        """
        Revoke an API key.

        Args:
            key_id: The key to revoke.
            player_id: Owner of the key (for authorization check).

        Raises:
            AUTH_API_KEY_NOT_FOUND: If key doesn't exist.
            FORBIDDEN_NOT_KEY_OWNER: If player_id doesn't own the key.
        """
        ...

    async def list_api_keys(
        self,
        player_id: PlayerId,
        include_revoked: bool = False,
    ) -> list[ApiKeyInfo]:
        """
        List all API keys for a player.

        Args:
            player_id: The player (must be a bot).
            include_revoked: Whether to include revoked keys in results.

        Returns:
            List of ApiKeyInfo (metadata only, no actual keys).

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Rate Limiting Support ==========

    async def check_rate_limit(
        self,
        key_id: UUID,
    ) -> "RateLimitStatus":
        """
        Check rate limit status for an API key.

        Args:
            key_id: The API key to check.

        Returns:
            RateLimitStatus with remaining requests, reset_at, limit.

        Raises:
            AUTH_API_KEY_NOT_FOUND: If key doesn't exist.
        """
        ...

    async def record_api_request(
        self,
        key_id: UUID,
    ) -> "RateLimitStatus":
        """
        Record an API request for rate limiting.

        Args:
            key_id: The API key making the request.

        Returns:
            Updated RateLimitStatus after recording the request.

        Raises:
            AUTH_API_KEY_NOT_FOUND: If key doesn't exist.
            RATE_LIMIT_API_KEY: If rate limit exceeded.
        """
        ...

    # ========== Password Operations ==========

    def hash_password(
        self,
        password: str,
    ) -> str:
        """
        Hash a password for storage using bcrypt.

        This is a sync method (CPU-bound, no I/O).

        Args:
            password: Plain-text password.

        Returns:
            Bcrypt hash string.

        Raises:
            VALIDATION_WEAK_PASSWORD: If password doesn't meet requirements.
        """
        ...

    def verify_password(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        """
        Verify a password against its hash.

        Uses constant-time comparison to prevent timing attacks.
        This is a sync method (CPU-bound, no I/O).

        Args:
            password: Plain-text password to verify.
            password_hash: Stored bcrypt hash.

        Returns:
            True if password matches, False otherwise.
        """
        ...


class PasswordStoreProtocol(Protocol):
    """Protocol for accessing password hashes.

    The Player domain type does not include password_hash. This protocol
    provides a clean way for the auth service to access password data
    without leaking password hashes into the Player type.
    """

    async def get_password_hash(self, player_id: UUID) -> str | None:
        """Get the stored password hash for a player."""
        ...

    async def set_password_hash(self, player_id: UUID, password_hash: str) -> None:
        """Set the password hash for a player."""
        ...


# --- Auth Module DTOs (src/modules/auth/dto.py) ---


@dataclass
class AuthResult:
    """Result of successful authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # seconds until access token expires


@dataclass
class ApiKeyCreationResult:
    """Result of creating an API key."""
    key_info: ApiKeyInfo
    raw_key: str  # Only returned once, never stored


@dataclass
class SessionInfo:
    """Information about an active session."""
    session_id: UUID
    player_id: UUID
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    device_info: str | None = None


@dataclass
class RateLimitStatus:
    """Rate limit status for an API key."""
    key_id: UUID
    requests_remaining: int
    requests_limit: int
    window_seconds: int
    reset_at: datetime
    is_exceeded: bool  # True when requests_remaining <= 0


@dataclass
class TokenPayload:
    """Decoded JWT token payload (internal use)."""
    player_id: UUID
    session_id: UUID
    token_type: str  # "access" or "refresh"
    issued_at: datetime
    expires_at: datetime
```

### 4.5 Energy Module

```python
# src/modules/energy/protocols.py
from typing import Protocol

from src.core.types.game import PlayerId


class EnergyServiceProtocol(Protocol):
    """Public interface for the energy module."""

    # ========== Core Energy Operations ==========

    async def get_energy(
        self,
        player_id: PlayerId,
    ) -> "EnergyInfo":
        """
        Get player's current energy state with real-time calculations.

        Calculates current hearts based on stored hearts plus any
        hearts that have regenerated since last_regen_at.

        Args:
            player_id: The player to query.

        Returns:
            EnergyInfo with current hearts, max hearts, time to next
            heart, streak info, and whether full.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def consume_energy(
        self,
        player_id: PlayerId,
        amount: int = 1,
    ) -> "EnergyConsumeResult":
        """
        Consume hearts for an action (e.g., starting a match).

        Applies pending regeneration first, then validates and
        deducts the requested amount atomically.

        Note: Implementation method is named consume_heart; the
        contract name is consume_energy. Coders must rename to match.

        Args:
            player_id: The player consuming energy.
            amount: Hearts to consume (default 1).

        Returns:
            EnergyConsumeResult with new state and consumption details.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            FORBIDDEN_INSUFFICIENT_ENERGY: If hearts < amount after regen.
            VALIDATION_INVALID_INPUT: If amount < 1.
        """
        ...

    async def can_play(
        self,
        player_id: PlayerId,
        hearts_required: int = 1,
    ) -> bool:
        """
        Check if player has enough hearts to play (non-consuming).

        Includes real-time regeneration calculation.

        Args:
            player_id: The player to check.
            hearts_required: Hearts needed (default 1).

        Returns:
            True if player has >= hearts_required after regen calc.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Regeneration Operations ==========

    async def apply_pending_regeneration(
        self,
        player_id: PlayerId,
    ) -> "RegenResult":
        """
        Calculate and persist any hearts that have regenerated.

        Args:
            player_id: The player.

        Returns:
            RegenResult with hearts_added and new state.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def get_time_to_next_heart(
        self,
        player_id: PlayerId,
    ) -> "TimeToHeartResult":
        """
        Get time remaining until next heart regenerates.

        Args:
            player_id: The player.

        Returns:
            TimeToHeartResult with seconds_remaining, next_regen_at, is_full.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Streak Operations ==========

    async def record_login(
        self,
        player_id: PlayerId,
    ) -> "LoginResult":
        """
        Record a player login for streak tracking.

        Compares last_login_date with today (UTC) and updates
        the streak accordingly. Grants bonus hearts at milestones.

        Args:
            player_id: The player logging in.

        Returns:
            LoginResult with streak info and any bonus granted.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def get_streak(
        self,
        player_id: PlayerId,
    ) -> "StreakInfo":
        """
        Get player's current streak information.

        Args:
            player_id: The player.

        Returns:
            StreakInfo with current streak, last login, next reward.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Bonus Heart Operations ==========

    async def grant_bonus_hearts(
        self,
        player_id: PlayerId,
        amount: int,
        source: "BonusSource",
        idempotency_key: str | None = None,
    ) -> "BonusGrantResult":
        """
        Grant bonus hearts from various sources.

        Bonus hearts can exceed max_hearts up to
        max_hearts + bonus_overflow_limit.

        Args:
            player_id: The player receiving bonus.
            amount: Hearts to grant.
            source: Source of bonus.
            idempotency_key: Optional key to prevent duplicate grants.

        Returns:
            BonusGrantResult with new heart count and grant status.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If amount < 1.
        """
        ...

    async def refund_heart(
        self,
        player_id: PlayerId,
        amount: int = 1,
        reason: str = "match_cancelled",
    ) -> "EnergyInfo":
        """
        Refund hearts (e.g., match cancelled). Respects max_hearts cap.

        Args:
            player_id: The player to refund.
            amount: Hearts to refund.
            reason: Reason for refund (for logging).

        Returns:
            Updated EnergyInfo.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...


# --- Energy Module DTOs (src/modules/energy/dto.py) ---

from enum import Enum
from dataclasses import dataclass
from datetime import date, datetime


class BonusSource(Enum):
    """Sources of bonus hearts."""
    AD_REWARD = "ad_reward"
    STREAK_BONUS = "streak_bonus"
    EVENT_REWARD = "event_reward"
    REFERRAL = "referral"
    COMPENSATION = "compensation"
    PROMOTION = "promotion"


@dataclass
class EnergyInfo:
    """Complete energy state with real-time calculations."""
    player_id: str
    current_hearts: int
    max_hearts: int
    seconds_to_next_heart: int | None  # None if at max
    next_heart_at: datetime | None     # None if at max
    is_full: bool
    daily_streak: int
    last_login_date: date | None


@dataclass
class EnergyConsumeResult:
    """Result of consuming hearts."""
    success: bool
    hearts_consumed: int
    hearts_remaining: int
    hearts_regenerated_before_consume: int
    energy_info: EnergyInfo


@dataclass
class RegenResult:
    """Result of applying regeneration."""
    hearts_added: int
    hearts_before: int
    hearts_after: int
    last_regen_at: datetime
    energy_info: EnergyInfo


@dataclass
class TimeToHeartResult:
    """Time until next heart regenerates."""
    seconds_remaining: int
    next_regen_at: datetime | None
    is_full: bool
    current_hearts: int
    max_hearts: int


@dataclass
class LoginResult:
    """Result of recording a login."""
    streak_day: int
    streak_continued: bool
    streak_broken: bool
    bonus_hearts_granted: int
    next_streak_reward_at: int
    energy_info: EnergyInfo


@dataclass
class StreakInfo:
    """Player's streak information."""
    current_streak: int
    last_login_date: date | None
    streak_started_at: date | None
    next_reward_threshold: int
    days_until_reward: int
    reward_hearts: int


@dataclass
class BonusGrantResult:
    """Result of granting bonus hearts."""
    granted: bool
    hearts_granted: int
    hearts_before: int
    hearts_after: int
    source: BonusSource
    already_claimed: bool
    energy_info: EnergyInfo
```

---

## 5. Presentation Boundary

### 5.1 Core Principle

Business logic modules in `src/modules/` return **domain objects** or **DTOs**. The presentation layer (`src/presentation/`) handles all formatting, serialization, and protocol-specific concerns.

### 5.2 Boundary Rules

| Location | Returns | Handles |
|----------|---------|---------|
| `src/modules/` | Domain types, DTOs | Business logic only |
| `src/presentation/adapters/` | Response models | JSON shaping, field selection |
| `src/presentation/routes/` | HTTP responses | Status codes, headers, errors |
| `src/cli/commands/` | Exit codes | Terminal formatting, colors |

### 5.3 DO and DON'T Examples

```python
# DO: Module returns domain object
# src/modules/match/service.py
class MatchService:
    async def get_match_state(self, match_id: MatchId) -> MatchState:
        match = await self._match_repo.find_by_id(match_id)
        if match is None:
            raise self._errors.not_found("Match not found", match_id=match_id)
        return self._build_match_state(match)


# DO: Adapter shapes for API
# src/presentation/adapters/match_adapter.py
class MatchApiAdapter:
    def to_response(self, state: MatchState) -> MatchStateResponse:
        return MatchStateResponse(
            match_id=str(state.match_id),
            board=state.board.to_list(),
            status=state.status.value,
            your_score=state.player1.score,  # Perspective-adjusted
            opponent_score=state.player2.score,
            moves_remaining=state.player1.moves_remaining,
        )


# DO: Route handles HTTP concerns
# src/presentation/routes/match_routes.py
@router.get("/matches/{match_id}")
async def get_match(
    match_id: str,
    current_player: Player = Depends(get_current_player),
    match_service: MatchServiceProtocol = Depends(get_match_service),
    adapter: MatchApiAdapter = Depends(get_match_adapter),
) -> MatchStateResponse:
    state = await match_service.get_match_state(
        MatchId(UUID(match_id)),
        for_player_id=current_player.id,
    )
    return adapter.to_response(state)
```

```python
# DON'T: Module doing HTTP formatting
# src/modules/match/service.py
class MatchService:
    async def get_match_state(self, match_id: MatchId) -> dict:  # VIOLATION
        match = await self._match_repo.find_by_id(match_id)
        return {
            "match_id": str(match_id),  # VIOLATION: JSON formatting
            "status": match.status.value,  # VIOLATION: Serialization
        }


# DON'T: Module returning JSON/HTTP concerns
class BoardService:
    def process_move(self, board: BoardState, move: Move) -> JSONResponse:  # VIOLATION
        ...
```

### 5.4 CLI Presentation

```python
# DO: CLI commands format for terminal
# src/cli/commands/match_commands.py
import click
from rich.console import Console
from rich.table import Table


@click.command()
@click.argument("match_id")
@click.pass_context
async def show_match(ctx, match_id: str):
    """Show match state in terminal."""
    match_service = ctx.obj["match_service"]

    # Get domain object from service
    state = await match_service.get_match_state(MatchId(UUID(match_id)))

    # Format for terminal (presentation concern)
    console = Console()
    table = Table(title=f"Match {match_id[:8]}...")

    table.add_column("Player", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Moves Left", justify="right")

    table.add_row("Player 1", str(state.player1.score), str(state.player1.moves_remaining))
    table.add_row("Player 2", str(state.player2.score), str(state.player2.moves_remaining))

    console.print(table)

    # Print board grid
    _print_board(console, state.board)
```

---

## 6. DTO Standards

### 6.1 Input DTOs

Input DTOs validate and carry data from the presentation layer into services.

```python
# src/core/types/dto/input.py
from dataclasses import dataclass
from typing import Annotated
from pydantic import BaseModel, Field, validator


# For FastAPI/Pydantic routes
class MoveRequest(BaseModel):
    """Input DTO for move submission."""
    from_row: Annotated[int, Field(ge=0, lt=8)]
    from_col: Annotated[int, Field(ge=0, lt=8)]
    to_row: Annotated[int, Field(ge=0, lt=8)]
    to_col: Annotated[int, Field(ge=0, lt=8)]
    timestamp_ms: Annotated[int, Field(gt=0)]

    @validator("to_row", "to_col")
    def positions_must_be_adjacent(cls, v, values):
        # Pydantic validation at API boundary
        ...

    def to_move(self) -> Move:
        """Convert to domain Move type."""
        return Move(
            from_pos=Position(row=self.from_row, col=self.from_col),
            to_pos=Position(row=self.to_row, col=self.to_col),
            timestamp_ms=self.timestamp_ms,
        )


class CreateMatchRequest(BaseModel):
    """Input DTO for match creation."""
    opponent_id: str
    board_seed: int | None = None


class CreatePlayerRequest(BaseModel):
    """Input DTO for player registration."""
    username: Annotated[str, Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")]
    password: Annotated[str, Field(min_length=8)] | None = None
    is_bot: bool = False


class LoginRequest(BaseModel):
    """Input DTO for authentication."""
    username: str
    password: str
```

### 6.2 Output DTOs

Output DTOs shape data for API responses. They live in the presentation layer.

```python
# src/presentation/dto/responses.py
from pydantic import BaseModel
from datetime import datetime


class MatchStateResponse(BaseModel):
    """API response for match state."""
    match_id: str
    status: str
    board: list[list[int]]
    your_score: int
    opponent_score: int
    your_moves_remaining: int
    opponent_moves_remaining: int
    is_your_turn: bool
    winner_id: str | None = None


class MoveResultResponse(BaseModel):
    """API response after submitting a move."""
    match_state: MatchStateResponse
    score_earned: int
    chains: int
    special_gems_created: list[dict]
    match_completed: bool


class PlayerResponse(BaseModel):
    """API response for player data."""
    id: str
    username: str
    is_bot: bool
    elo_rating: int
    created_at: datetime


class PlayerStatsResponse(BaseModel):
    """API response for player statistics."""
    player_id: str
    total_matches: int
    wins: int
    losses: int
    draws: int
    win_rate: float
    highest_score: int


class AuthResponse(BaseModel):
    """API response for authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class ApiKeyResponse(BaseModel):
    """API response for API key creation."""
    key_id: str
    prefix: str
    created_at: datetime
    raw_key: str | None = None  # Only on creation


class ErrorResponse(BaseModel):
    """API response for errors."""
    code: str
    message: str
    correlation_id: str
    timestamp: datetime
```

### 6.3 DTO Conversion Pattern

```python
# src/presentation/adapters/player_adapter.py
from src.core.types.player import Player, PlayerStats
from src.presentation.dto.responses import PlayerResponse, PlayerStatsResponse


class PlayerAdapter:
    """Converts domain objects to API responses."""

    def to_response(self, player: Player) -> PlayerResponse:
        return PlayerResponse(
            id=str(player.id),
            username=player.username,
            is_bot=player.is_bot,
            elo_rating=player.elo_rating,
            created_at=player.created_at,
        )

    def stats_to_response(self, stats: PlayerStats) -> PlayerStatsResponse:
        return PlayerStatsResponse(
            player_id=str(stats.player_id),
            total_matches=stats.total_matches,
            wins=stats.wins,
            losses=stats.losses,
            draws=stats.draws,
            win_rate=stats.win_rate,
            highest_score=stats.highest_score,
        )
```

---

## 7. WebSocket Contract

WebSocket provides real-time updates alongside REST. REST remains the primary API; WebSocket is additive for subscriptions and live updates.

### 7.1 Connection Flow

```
1. Client opens WebSocket to /ws
2. Client sends AUTH message with token (JWT or API key)
3. Server validates, responds with AUTH_OK or AUTH_FAILED
4. Client subscribes to channels (match, energy, matchmaking)
5. Server pushes events as they occur
6. Client can send commands (ping, subscribe, unsubscribe)
```

### 7.2 Message Types

```python
# src/core/types/websocket.py
from dataclasses import dataclass
from enum import Enum
from typing import Any
from datetime import datetime


class WSMessageType(Enum):
    # Client → Server
    AUTH = "auth"
    PING = "ping"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"

    # Server → Client
    AUTH_OK = "auth_ok"
    AUTH_FAILED = "auth_failed"
    PONG = "pong"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    ERROR = "error"

    # Event pushes (Server → Client)
    MATCH_UPDATE = "match_update"
    MATCH_STARTED = "match_started"
    MATCH_ENDED = "match_ended"
    OPPONENT_MOVED = "opponent_moved"
    ENERGY_UPDATE = "energy_update"
    MATCHMAKING_FOUND = "matchmaking_found"
    MATCHMAKING_TIMEOUT = "matchmaking_timeout"
    EVENT_STARTED = "event_started"
    EVENT_ENDED = "event_ended"


class WSChannel(Enum):
    MATCH = "match"           # Match state updates
    ENERGY = "energy"         # Energy regeneration
    MATCHMAKING = "matchmaking"  # Queue status
    EVENTS = "events"         # Event notifications


@dataclass
class WSMessage:
    """Base WebSocket message structure."""
    type: WSMessageType
    payload: dict[str, Any]
    correlation_id: str | None = None
    timestamp: datetime = None

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class WSAuthMessage:
    """Client authentication message."""
    token: str  # JWT or API key


@dataclass
class WSSubscribeMessage:
    """Subscribe to a channel."""
    channel: WSChannel
    params: dict[str, Any] | None = None  # e.g., {"match_id": "..."}


@dataclass
class WSMatchUpdate:
    """Real-time match state push."""
    match_id: str
    board: list[list[int]]
    scores: dict[str, int]
    current_turn: str
    moves_remaining: dict[str, int]
    last_move: dict | None = None
```

### 7.3 Channel Subscriptions

| Channel | Subscription Params | Events Pushed |
|---------|---------------------|---------------|
| `match` | `match_id` | MATCH_UPDATE, OPPONENT_MOVED, MATCH_ENDED |
| `energy` | (none) | ENERGY_UPDATE (on regen tick) |
| `matchmaking` | (none) | MATCHMAKING_FOUND, MATCHMAKING_TIMEOUT |
| `events` | (none) | EVENT_STARTED, EVENT_ENDED |

### 7.4 WebSocket Error Codes

| Code | Message | When |
|------|---------|------|
| `WS_AUTH_REQUIRED` | "Authentication required" | No auth message sent |
| `WS_AUTH_INVALID` | "Invalid authentication" | Bad token |
| `WS_CHANNEL_INVALID` | "Invalid channel" | Unknown channel name |
| `WS_SUBSCRIPTION_DENIED` | "Cannot subscribe to this resource" | Not authorized for match |
| `WS_RATE_LIMITED` | "Message rate limit exceeded" | Too many messages |
| `WS_MESSAGE_TOO_LARGE` | "Message exceeds size limit" | Payload too big |
| `WS_INVALID_MESSAGE` | "Malformed message" | JSON parse error |

### 7.5 WebSocket Service Protocol

```python
# src/presentation/websocket/protocols.py
from typing import Protocol
from uuid import UUID


class WSConnectionManagerProtocol(Protocol):
    """Manages WebSocket connections and subscriptions."""

    async def authenticate(
        self,
        connection_id: str,
        token: str,
    ) -> "WSAuthResult":
        """Authenticate a WebSocket connection."""
        ...

    async def subscribe(
        self,
        connection_id: str,
        channel: WSChannel,
        params: dict | None = None,
    ) -> None:
        """Subscribe connection to a channel."""
        ...

    async def unsubscribe(
        self,
        connection_id: str,
        channel: WSChannel,
    ) -> None:
        """Unsubscribe connection from a channel."""
        ...

    async def broadcast_to_match(
        self,
        match_id: UUID,
        message: WSMessage,
    ) -> None:
        """Push message to all connections subscribed to a match."""
        ...

    async def send_to_player(
        self,
        player_id: UUID,
        message: WSMessage,
    ) -> None:
        """Push message to all connections for a player."""
        ...

    async def disconnect(
        self,
        connection_id: str,
        reason: str | None = None,
    ) -> None:
        """Close a WebSocket connection."""
        ...
```

### 7.6 Integration with Modules

Modules do NOT import WebSocket code. Instead, the presentation layer listens to domain events and pushes via WebSocket:

```python
# DO: Presentation layer handles WebSocket push
# src/presentation/websocket/handlers.py
class MatchWebSocketHandler:
    def __init__(
        self,
        ws_manager: WSConnectionManagerProtocol,
        match_adapter: MatchApiAdapter,
    ):
        self._ws = ws_manager
        self._adapter = match_adapter

    async def on_move_processed(self, match_state: MatchState) -> None:
        """Called by match service event. Pushes to subscribers."""
        message = WSMessage(
            type=WSMessageType.MATCH_UPDATE,
            payload=self._adapter.to_response(match_state).dict(),
        )
        await self._ws.broadcast_to_match(match_state.match_id, message)


# DON'T: Module code importing WebSocket
# src/modules/match/service.py
class MatchService:
    async def submit_move(self, ...):
        # VIOLATION: Module should not know about WebSocket
        await self._ws_manager.broadcast(...)  # NO!
```

---

## 8. Summary: DO and DON'T

### DO

- Define shared types in `src/core/types/`
- Use `typing.Protocol` for all service interfaces
- Raise errors through the injected `ErrorService`
- Include correlation ID in all errors and logs
- Return domain objects from modules
- Format responses in the presentation layer
- Use Pydantic for API input validation
- Define clear input/output DTOs

### DON'T

- Define duplicate types in modules
- Import concrete services directly
- Use bare `raise Exception()` or `raise ValueError()`
- Format JSON or HTTP responses in modules
- Access another module's internal types
- Skip correlation ID propagation
- Mix presentation concerns with business logic

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-06 | 1.6 | Karen Stage 2 P0 review: added 24 missing error codes (events, ads, vault, matchmaking, bot_earnings); amended §4.1 Board (richer types: GemDrop, GemSpawn, CascadeStep, MoveProcessingResult; added clear_matches, fill_empty, validate_board, has_valid_moves); amended §4.2 Match (richer MatchState, PlayerMatchState, MoveSubmissionResult, MatchType, MatchSummary, MoveRecord, PlayerBoardState; added get_match, get_player_board, get_active_matches, get_match_history, get_move_history, abandon_stale_matches; note on §1.3 core type extension); amended §4.3 Player (added soft_delete_player, list_players, get_elo, calculate_elo_change, record_match_result, initialize_energy_state, get_energy_state, update_energy_state; removed get_energy/consume_energy to §4.5; added PaginatedResult, EnergyStateUpdate DTOs; fixed PlayerUpdate to include email); added §4.5 Energy (new EnergyServiceProtocol with get_energy, consume_energy, can_play, apply_pending_regeneration, get_time_to_next_heart, record_login, get_streak, grant_bonus_hearts, refund_heart; DTOs: EnergyInfo, EnergyConsumeResult, RegenResult, TimeToHeartResult, LoginResult, StreakInfo, BonusGrantResult, BonusSource); amended §4.4 Auth (added logout, get_active_sessions, check_rate_limit, record_api_request, hash_password, verify_password, PasswordStoreProtocol; DTOs: SessionInfo, RateLimitStatus, TokenPayload; error code fix: NOT_FOUND_API_KEY -> AUTH_API_KEY_NOT_FOUND) | Orchestrator |
| 2026-02-05 | 1.5 | Added WebSocket contract (Section 7): message types, channels, error codes, service protocol | Orchestrator |
| 2026-02-05 | 1.4 | Added Phase 1.5 audit findings (CONFLICT_DUPLICATE_BONUS, CONFLICT_MAX_MATCHES_REACHED) | Orchestrator |
| 2026-02-05 | 1.3 | Added Phase 1.3 review recommendations (AUTH_API_KEY_NOT_FOUND, FORBIDDEN_NOT_BOT, FORBIDDEN_NOT_KEY_OWNER) | Orchestrator |
| 2026-02-05 | 1.2 | Added payments + bot_earnings error types (21 new codes) | Orchestrator |
| 2026-02-05 | 1.1 | Added matchmaking error types (ALREADY_IN_QUEUE, NOT_FOUND_QUEUE_ENTRY, RATE_LIMIT_QUEUE_FULL, EXPANSION_FAILED) | Orchestrator |
| 2026-02-05 | 1.0 | Initial guidance | Interface Agent |
