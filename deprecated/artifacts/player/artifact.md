# Player Module Artifact

> **Module:** player
> **Author:** Scout Agent
> **Date:** 2026-02-05
> **Version:** 1.0
> **Status:** Draft
> **Build Wave:** 1 (Leaf Node)

---

## Dependencies

### Module Dependencies
None. The player module is a Wave 1 leaf node with no inter-module dependencies.

### Core Service Dependencies
| Service | Injected Via | Usage |
|---------|--------------|-------|
| `ConfigProtocol` | `__init__` | ELO initial rating, energy settings, username constraints |
| `LoggerProtocol` | `__init__` | Player creation, updates, stats changes |
| `ErrorServiceProtocol` | `__init__` | Validation errors, not found, conflicts |
| `DataContext` | `__init__` | Database session management for all async operations |

### Repository Dependencies
| Repository | Ownership | Access Type |
|------------|-----------|-------------|
| `PlayerRepository` | Owns | Read/Write |
| `PlayerStatsRepository` | Owns | Read/Write |
| `EnergyStateRepository` | Owns | Read/Write (business logic owned by energy module) |

---

## 1. Purpose

The player module manages player accounts and profiles for both human and bot players in ChromaCrush. It provides:

1. **Player Account Management** - Creation, retrieval, updates, and soft-deletion of player accounts
2. **Bot vs Human Distinction** - Different creation flows and validation rules for each player type
3. **ELO Rating Tracking** - Maintaining and updating player skill ratings
4. **Player Statistics** - Aggregate win/loss records, highest scores, and match statistics
5. **Energy State Data Ownership** - Storing energy/hearts data (business logic delegated to energy module)

The module serves as the foundation for all player-related operations and is a dependency for auth, match, matchmaking, vault, energy, events, ads, and payments modules.

---

## 2. Public Interface

### 2.1 PlayerService Protocol

```python
# src/modules/player/protocols.py
from typing import Protocol
from uuid import UUID
from datetime import datetime

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
        email: str | None = None,
    ) -> Player:
        """
        Create a new player account.

        Args:
            username: Unique username (case-insensitive, 3-32 chars, alphanumeric + underscore).
            player_type: PlayerType.HUMAN or PlayerType.BOT.
            password_hash: Required for humans, must be None for bots.
            email: Optional email for humans, None for bots.

        Returns:
            Created Player entity.

        Raises:
            VALIDATION_INVALID_INPUT: If username format is invalid.
            VALIDATION_INVALID_INPUT: If human missing password_hash.
            VALIDATION_INVALID_INPUT: If bot provided password_hash.
            CONFLICT_USERNAME_TAKEN: If username already exists (case-insensitive).

        Logs:
            INFO: "Player created" with player_id, username, player_type.
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

        Logs:
            INFO: "Player updated" with player_id, changed_fields.
        """
        ...

    async def soft_delete_player(
        self,
        player_id: PlayerId,
    ) -> None:
        """
        Soft-delete a player account (GDPR compliance).

        Sets deleted_at timestamp. Player data retained but inaccessible via normal queries.
        Username is released for reuse by appending deletion timestamp.

        Args:
            player_id: The player to delete.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist or already deleted.

        Logs:
            INFO: "Player soft-deleted" with player_id.
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

        Logs:
            INFO: "ELO updated" with player_id, old_rating, new_rating, delta.
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

        Uses standard ELO formula with configurable K-factor.

        Args:
            winner_id: The winning player (or either player if draw).
            loser_id: The losing player (or other player if draw).
            is_draw: Whether the match was a draw.

        Returns:
            Tuple of (winner_elo_change, loser_elo_change).
            For draws, returns symmetric adjustments.

        Raises:
            NOT_FOUND_PLAYER: If either player doesn't exist.

        Note:
            This method calculates but does NOT apply changes.
            Caller (match module) is responsible for applying via update_elo.
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
            player_id: The player.

        Returns:
            PlayerStats aggregate (wins, losses, draws, highest_score, etc.).

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

        Logs:
            INFO: "Match result recorded" with player_id, result, score.
        """
        ...

    # ========== Energy State Data Access ==========

    async def get_energy_state(
        self,
        player_id: PlayerId,
    ) -> EnergyState:
        """
        Get player's energy state (data access only).

        Business logic for energy regeneration is in the energy module.
        This method provides data layer access.

        Args:
            player_id: The player.

        Returns:
            Current EnergyState (hearts, last_regen_at, streak, etc.).

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
        Update player's energy state (data access only).

        Business logic for when/how to update is in the energy module.
        This method provides data layer access.

        Args:
            player_id: The player.
            energy_update: Fields to update.

        Returns:
            Updated EnergyState.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If hearts < 0 or > max_hearts.

        Logs:
            DEBUG: "Energy state updated" with player_id, changes.
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
```

### 2.2 Data Transfer Objects

```python
# src/modules/player/dto.py
from dataclasses import dataclass
from typing import Generic, TypeVar
from datetime import datetime, date

T = TypeVar("T")


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
    """Paginated query result."""
    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total
```

---

## 3. Mandatory Service Usage

### 3.1 Configuration Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `matchmaking.elo_initial` | int | 1000 | Starting ELO for new players |
| `matchmaking.elo_k_factor` | int | 32 | K-factor for ELO calculations |
| `energy.max_hearts` | int | 5 | Maximum hearts for energy state |
| `player.username_min_length` | int | 3 | Minimum username length |
| `player.username_max_length` | int | 32 | Maximum username length |
| `player.username_pattern` | str | `^[a-zA-Z0-9_]+$` | Valid username regex |

### 3.2 Logging Events

| Level | Event | Context Fields | When |
|-------|-------|----------------|------|
| INFO | "Player created" | `player_id`, `username`, `player_type` | After successful creation |
| INFO | "Player updated" | `player_id`, `changed_fields` | After profile update |
| INFO | "Player soft-deleted" | `player_id` | After soft deletion |
| INFO | "ELO updated" | `player_id`, `old_rating`, `new_rating`, `delta` | After ELO change |
| INFO | "Match result recorded" | `player_id`, `result`, `score` | After stats update |
| DEBUG | "Energy state updated" | `player_id`, `changes` | After energy state change |
| WARN | "Username conflict" | `username`, `existing_player_id` | On duplicate username attempt |

### 3.3 Error Types Used

| Error Code | HTTP | When Raised |
|------------|------|-------------|
| `VALIDATION_INVALID_INPUT` | 400 | Invalid username format, missing required fields |
| `NOT_FOUND_PLAYER` | 404 | Player ID doesn't exist or soft-deleted |
| `CONFLICT_USERNAME_TAKEN` | 409 | Username already in use (case-insensitive) |

---

## 4. Data Access

### 4.1 Owned Data

The player module owns these database tables:

#### `players` Table
```sql
CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(32) NOT NULL,
    username_lower VARCHAR(32) NOT NULL UNIQUE,  -- For case-insensitive lookup
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),  -- NULL for bots
    player_type VARCHAR(10) NOT NULL,  -- 'human' or 'bot'
    elo_rating INTEGER NOT NULL DEFAULT 1000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- NULL if not deleted (soft delete)
);

CREATE INDEX idx_players_elo ON players(elo_rating) WHERE deleted_at IS NULL;
CREATE INDEX idx_players_type ON players(player_type) WHERE deleted_at IS NULL;
```

#### `player_stats` Table
```sql
CREATE TABLE player_stats (
    player_id UUID PRIMARY KEY REFERENCES players(id),
    total_matches INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    highest_score INTEGER NOT NULL DEFAULT 0,
    longest_chain INTEGER NOT NULL DEFAULT 0,
    total_gems_matched BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `energy_states` Table
```sql
CREATE TABLE energy_states (
    player_id UUID PRIMARY KEY REFERENCES players(id),
    hearts INTEGER NOT NULL DEFAULT 5,
    max_hearts INTEGER NOT NULL DEFAULT 5,
    last_regen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    daily_streak INTEGER NOT NULL DEFAULT 0,
    last_login_date DATE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.2 Repository Interfaces

```python
# src/data/protocols/player_repository.py
from typing import Protocol
from uuid import UUID

from src.core.types.game import PlayerId
from src.core.types.player import Player, PlayerType


class PlayerRepository(Protocol):
    """Repository interface for player data access."""

    async def find_by_id(self, player_id: UUID) -> Player | None:
        """Find player by ID, excluding soft-deleted."""
        ...

    async def find_by_username(self, username: str) -> Player | None:
        """Find player by username (case-insensitive), excluding soft-deleted."""
        ...

    async def exists_username(self, username: str) -> bool:
        """Check if username exists (case-insensitive), excluding soft-deleted."""
        ...

    async def create(self, data: "PlayerCreate") -> Player:
        """Create new player record."""
        ...

    async def update(self, player_id: UUID, changes: "PlayerDbUpdate") -> Player:
        """Update player fields."""
        ...

    async def soft_delete(self, player_id: UUID) -> None:
        """Set deleted_at timestamp and anonymize username."""
        ...

    async def list_players(
        self,
        player_type: PlayerType | None = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> tuple[list[Player], int]:
        """List players with filtering, returns (items, total_count)."""
        ...


class PlayerStatsRepository(Protocol):
    """Repository interface for player statistics."""

    async def find_by_player_id(self, player_id: UUID) -> "PlayerStatsRecord | None":
        ...

    async def create(self, player_id: UUID) -> "PlayerStatsRecord":
        ...

    async def update(self, player_id: UUID, changes: "StatsUpdate") -> "PlayerStatsRecord":
        ...


class EnergyStateRepository(Protocol):
    """Repository interface for energy state data."""

    async def find_by_player_id(self, player_id: UUID) -> "EnergyStateRecord | None":
        ...

    async def create(self, player_id: UUID, initial_state: "EnergyStateCreate") -> "EnergyStateRecord":
        ...

    async def update(self, player_id: UUID, changes: "EnergyStateDbUpdate") -> "EnergyStateRecord":
        ...
```

### 4.3 Transaction Requirements

| Operation | Transaction Scope | Notes |
|-----------|-------------------|-------|
| `create_player` | Single transaction | Creates player + stats + energy_state atomically |
| `update_player` | Single transaction | Simple update |
| `soft_delete_player` | Single transaction | Updates deleted_at and username |
| `update_elo` | Single transaction | Simple update |
| `record_match_result` | Single transaction | Updates stats fields |
| `update_energy_state` | Single transaction | Simple update |

---

## 5. Presentation Boundary

### 5.1 What This Module Returns

The player module returns domain objects (`Player`, `PlayerStats`, `EnergyState`) and DTOs (`PaginatedResult`). It does NOT return:
- JSON objects
- HTTP responses
- Formatted strings for display
- Error response dictionaries

### 5.2 Presentation Layer Responsibility

The presentation layer (`src/presentation/adapters/player_adapter.py`) handles:
- Converting `Player` to `PlayerResponse` (hiding password_hash, deleted_at)
- Converting `PlayerStats` to `PlayerStatsResponse` (calculating win_rate)
- Formatting timestamps for API responses
- Selecting which fields to expose based on requester (e.g., bots don't see email)

### 5.3 Example Boundary

```python
# Module returns domain object
player = await player_service.get_player(player_id)
# player is a Player dataclass with all fields

# Adapter converts for API
response = player_adapter.to_response(player, for_player_id=requester_id)
# response is PlayerResponse Pydantic model for JSON serialization
```

---

## 6. Internal Design

### 6.1 Service Implementation Structure

```
src/modules/player/
    __init__.py           # Exports PlayerService, protocols
    service.py            # PlayerService implementation
    protocols.py          # PlayerServiceProtocol
    dto.py                # PlayerUpdate, EnergyStateUpdate, PaginatedResult
    elo.py                # ELO calculation helpers
    validation.py         # Username validation helpers
```

### 6.2 Component Diagram

```
                    PlayerService
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
  PlayerRepository  PlayerStatsRepo  EnergyStateRepo
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
                   DataContext
                   (PostgreSQL)
```

### 6.3 ELO Calculation

Standard ELO formula with configurable K-factor:

```python
def calculate_expected_score(rating_a: int, rating_b: int) -> float:
    """Calculate expected score for player A against player B."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def calculate_elo_change(
    winner_rating: int,
    loser_rating: int,
    k_factor: int,
    is_draw: bool = False,
) -> tuple[int, int]:
    """
    Calculate ELO changes for both players.

    Returns (winner_change, loser_change).
    For draws, winner_change and loser_change are symmetric adjustments.
    """
    expected_winner = calculate_expected_score(winner_rating, loser_rating)
    expected_loser = 1 - expected_winner

    if is_draw:
        # Draw: actual score is 0.5 for both
        winner_change = round(k_factor * (0.5 - expected_winner))
        loser_change = round(k_factor * (0.5 - expected_loser))
    else:
        # Win: winner gets 1.0, loser gets 0.0
        winner_change = round(k_factor * (1.0 - expected_winner))
        loser_change = round(k_factor * (0.0 - expected_loser))

    return winner_change, loser_change
```

### 6.4 Username Validation

```python
import re

def validate_username(
    username: str,
    min_length: int,
    max_length: int,
    pattern: str,
) -> tuple[bool, str | None]:
    """
    Validate username format.

    Returns (is_valid, error_message or None).
    """
    if len(username) < min_length:
        return False, f"Username must be at least {min_length} characters"

    if len(username) > max_length:
        return False, f"Username must be at most {max_length} characters"

    if not re.match(pattern, username):
        return False, "Username can only contain letters, numbers, and underscores"

    return True, None
```

---

## 7. CLI Surface

### 7.1 Commands

```bash
# Player CRUD operations
chromacrush player create --username <name> [--is-bot] [--email <email>]
chromacrush player get <player-id>
chromacrush player get-by-username <username>
chromacrush player update <player-id> [--username <name>] [--email <email>]
chromacrush player delete <player-id>
chromacrush player list [--type human|bot] [--limit N] [--offset N]

# ELO operations
chromacrush player elo <player-id>
chromacrush player set-elo <player-id> <rating>
chromacrush player calc-elo <winner-id> <loser-id> [--draw]

# Statistics operations
chromacrush player stats <player-id>
chromacrush player record-result <player-id> --won|--lost|--draw --score <N>

# Energy state (data view)
chromacrush player energy <player-id>
```

### 7.2 CLI Command Implementation

```python
# src/cli/commands/player_commands.py
import click
from uuid import UUID

@click.group()
def player():
    """Player management commands."""
    pass

@player.command()
@click.option("--username", required=True, help="Unique username")
@click.option("--is-bot", is_flag=True, help="Create as bot account")
@click.option("--email", help="Email address (humans only)")
@click.pass_context
async def create(ctx, username: str, is_bot: bool, email: str | None):
    """Create a new player account."""
    player_service = ctx.obj["player_service"]
    player_type = PlayerType.BOT if is_bot else PlayerType.HUMAN

    # For CLI testing, we don't require password_hash
    # In production, auth module handles password hashing
    player = await player_service.create_player(
        username=username,
        player_type=player_type,
        email=email,
    )

    click.echo(f"Created player: {player.id}")
    click.echo(f"  Username: {player.username}")
    click.echo(f"  Type: {player.player_type.value}")
    click.echo(f"  ELO: {player.elo_rating}")

@player.command()
@click.argument("player_id")
@click.pass_context
async def get(ctx, player_id: str):
    """Get player by ID."""
    player_service = ctx.obj["player_service"]
    player = await player_service.get_player(PlayerId(UUID(player_id)))

    click.echo(f"Player: {player.id}")
    click.echo(f"  Username: {player.username}")
    click.echo(f"  Type: {player.player_type.value}")
    click.echo(f"  ELO: {player.elo_rating}")
    click.echo(f"  Created: {player.created_at}")

@player.command()
@click.argument("player_id")
@click.pass_context
async def stats(ctx, player_id: str):
    """Get player statistics."""
    player_service = ctx.obj["player_service"]
    stats = await player_service.get_stats(PlayerId(UUID(player_id)))

    click.echo(f"Stats for player {player_id}:")
    click.echo(f"  Total matches: {stats.total_matches}")
    click.echo(f"  Wins: {stats.wins}")
    click.echo(f"  Losses: {stats.losses}")
    click.echo(f"  Draws: {stats.draws}")
    click.echo(f"  Win rate: {stats.win_rate:.1%}")
    click.echo(f"  Highest score: {stats.highest_score}")
    click.echo(f"  Longest chain: {stats.longest_chain}")

@player.command("calc-elo")
@click.argument("winner_id")
@click.argument("loser_id")
@click.option("--draw", is_flag=True, help="Calculate as draw")
@click.pass_context
async def calc_elo(ctx, winner_id: str, loser_id: str, draw: bool):
    """Calculate ELO change for a match result (does not apply)."""
    player_service = ctx.obj["player_service"]

    winner_change, loser_change = await player_service.calculate_elo_change(
        winner_id=PlayerId(UUID(winner_id)),
        loser_id=PlayerId(UUID(loser_id)),
        is_draw=draw,
    )

    if draw:
        click.echo(f"Draw result:")
        click.echo(f"  Player 1 change: {winner_change:+d}")
        click.echo(f"  Player 2 change: {loser_change:+d}")
    else:
        click.echo(f"Win/Loss result:")
        click.echo(f"  Winner change: {winner_change:+d}")
        click.echo(f"  Loser change: {loser_change:+d}")
```

---

## 8. Edge Cases & Decisions

### 8.1 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Username case sensitivity | Case-insensitive storage and lookup | Prevents confusion (user1, User1, USER1 all conflict) |
| Soft delete vs hard delete | Soft delete with `deleted_at` | GDPR compliance, enables recovery, preserves match history |
| Username release on delete | Append timestamp suffix | Allows username reuse while preserving audit trail |
| Bot password | None (null) | Bots authenticate via API keys managed by auth module |
| Human email | Optional | Not all games require email; auth module handles verification |
| ELO floor | 0 (no negative ELO) | Prevents negative ratings from demoralizing new players |
| Stats initialization | Created with player | Ensures stats always exist, simplifies queries |
| Energy state ownership | Player owns data, energy owns logic | Clean separation; player module is Wave 1, energy is Wave 2 |

### 8.2 Edge Cases

| Scenario | Handling |
|----------|----------|
| Create bot with password_hash | Reject with VALIDATION_INVALID_INPUT |
| Create human without password_hash | Reject with VALIDATION_INVALID_INPUT |
| Get soft-deleted player | Return NOT_FOUND_PLAYER |
| Update username to existing (case-insensitive) | Reject with CONFLICT_USERNAME_TAKEN |
| Update username to same value | Accept (no-op) |
| Set ELO to negative | Reject with VALIDATION_INVALID_INPUT |
| Set hearts > max_hearts | Reject with VALIDATION_INVALID_INPUT |
| List players with limit > 100 | Reject with VALIDATION_INVALID_INPUT |
| Record match result for deleted player | Reject with NOT_FOUND_PLAYER |
| Calculate ELO for same player vs self | Reject with VALIDATION_INVALID_INPUT |

### 8.3 Escalation Required

None. All edge cases are covered by existing error taxonomy and guidance.

---

## 9. Open Questions

None. All design decisions have been resolved based on:
- Feasibility report specifications
- Interface contracts guidance
- Data layer guidance
- Configuration guidance

---

## Async Behavior Summary

All public methods are `async def` because they involve database operations. This module follows the async contract:

- All repository calls are awaited
- No fire-and-forget operations
- Transaction boundaries managed via DataContext
- Errors propagate correctly through async chain

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent |
