# Data Layer Guidance

**Version:** 1.0
**Date:** 2026-02-05
**Author:** Data Agent
**Status:** Final
**Phase:** 1.0

---

## 1. Overview

### Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Primary Database | PostgreSQL | 15 |
| ORM | SQLAlchemy | 2.0+ (async) |
| Cache/Queue | Redis | 7 |
| Migrations | Alembic | Latest |

---

## 2. Repository Pattern

### 2.1 Core Principle

All data access flows through injected `Protocol` interfaces. Business logic in `src/modules/` NEVER imports SQLAlchemy, Redis, or any storage API directly.

### 2.2 Protocol Interface

```python
# src/data/protocols/player_repository.py
from typing import Protocol
from uuid import UUID

class PlayerRepository(Protocol):
    async def find_by_id(self, player_id: UUID) -> Player | None: ...
    async def create(self, data: PlayerCreate) -> Player: ...
    async def update(self, player_id: UUID, changes: PlayerUpdate) -> Player: ...
    async def delete(self, player_id: UUID) -> None: ...
```

### 2.3 Directory Structure

```
src/data/
├── protocols/           # Protocol interfaces
├── repositories/        # Concrete implementations
├── models/              # SQLAlchemy ORM models
├── migrations/          # Alembic migrations
├── seeds/               # Seed/fixture data
└── redis/               # Redis implementations
```

---

## 3. Data Ownership Rules

### 3.1 Ownership Matrix

| Module | Owns (Write Access) | Reads From |
|--------|---------------------|------------|
| `player` | `players`, `energy_states` | - |
| `auth` | `api_keys`, `sessions` | `players` |
| `match` | `matches` | `players`, `board_gen` |
| `vault` | `vault_artifacts` | `players`, `matches` |
| `matchmaking` | `matchmaking_queue` (Redis) | `players`, `matches` |
| `events` | `events`, `event_participants` | `players`, `vault` |

### 3.2 Cross-Module Access

**DO:** Request through owning module's service interface
```python
player = await self._player_service.get_player(player_id)
```

**DON'T:** Access another module's tables directly
```python
# VIOLATION
player = await session.execute(select(PlayerModel).where(...))
```

---

## 4. Transaction Boundaries

### 4.1 Core Principle

Transactions live at the service level, NOT inside repository methods.

### 4.2 Session Management

```python
# src/core/data_context.py
class DataContext:
    @asynccontextmanager
    async def session(self):
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 4.3 Service Usage

```python
async def complete_match(self, match_id: UUID, winner_id: UUID) -> MatchResult:
    async with self._data_ctx.session() as session:
        match_repo = self._match_repo.with_session(session)
        match = await match_repo.find_by_id(match_id)
        match.status = MatchStatus.COMPLETED
        await match_repo.update(match)
        # Commits automatically on context exit
```

---

## 5. PostgreSQL Patterns

### 5.1 Primary Keys

All tables use UUID primary keys.

```python
from sqlalchemy.dialects.postgresql import UUID
import uuid

id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

### 5.2 Timestamps

All timestamps in UTC.

```python
from datetime import datetime, timezone

created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
```

### 5.3 JSONB for Board State

```python
from sqlalchemy.dialects.postgresql import JSONB

board_state = Column(JSONB, nullable=False, default=list)
# Example: [[1,2,3,4,5,6,7,8], [2,3,4,5,6,7,8,1], ...]

player1_moves = Column(JSONB, nullable=False, default=list)
# Example: [{"from": [0,0], "to": [0,1], "score": 150}, ...]
```

---

## 6. Redis Patterns

### 6.1 Key Naming

```
{service}:{entity}:{identifier}:{field}
```

Examples:
- `chromacrush:leaderboard:elo:global`
- `chromacrush:matchmaking:queue:1000`
- `chromacrush:match:{match_id}:cache`

### 6.2 Sorted Sets for Leaderboards

```python
async def add_score(self, leaderboard_key: str, player_id: str, score: float):
    await self._redis.zadd(self._key(leaderboard_key), {player_id: score})

async def get_rank(self, leaderboard_key: str, player_id: str) -> int | None:
    return await self._redis.zrevrank(self._key(leaderboard_key), player_id)
```

### 6.3 TTL for Energy Timers

```python
async def schedule_regen(self, player_id: str, hearts_to_add: int = 1):
    await self._redis.setex(
        f"chromacrush:energy:regen:{player_id}",
        self._regen_seconds,  # 20 minutes
        str(hearts_to_add)
    )
```

---

## 7. Migration Strategy

### 7.1 File Naming

`{sequence}_{description}.py`
- `001_initial_schema.py`
- `002_add_vault_artifacts.py`

### 7.2 Migration Template

```python
def upgrade() -> None:
    op.create_table("players", ...)
    op.create_index("idx_players_elo", "players", ["elo_rating"])

def downgrade() -> None:
    op.drop_index("idx_players_elo")
    op.drop_table("players")
```

### 7.3 Rules

- Every migration MUST have `downgrade()`
- Additive changes: Safe anytime
- Column removal: Two-phase deployment
- Create indexes concurrently in production

---

## 8. Seed Data

### 8.1 Structure

```
src/data/seeds/
├── dev/
│   ├── players.json
│   └── matches.json
└── test/
    └── minimal.json
```

### 8.2 Test Isolation

```python
@pytest.fixture
async def test_session():
    async with engine.begin() as conn:
        session = AsyncSession(bind=conn)
        yield session
        await conn.rollback()  # Always rollback
```

---

## 9. Query Standards

### 9.1 Repository Methods Only

```python
# DO
players = await self._player_repo.list_by_elo_range(900, 1100)

# DON'T
result = await session.execute(text("SELECT * FROM players WHERE ..."))
```

### 9.2 Pagination

```python
async def list_matches(
    self,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedResult[Match]:
    ...

@dataclass
class PaginatedResult[T]:
    items: list[T]
    total: int
    has_more: bool
```

---

## 10. Summary

### DO

- Define repository interfaces as `Protocol`
- Use UUID primary keys
- Store timestamps in UTC
- Use JSONB for board state
- Manage transactions at service layer
- Use async/await for all DB operations

### DON'T

- Import SQLAlchemy in `src/modules/`
- Write raw SQL in business logic
- Access another module's tables
- Manage transactions in repositories
- Store local timestamps
- Use sequential integer primary keys

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial guidance | Data Agent |
