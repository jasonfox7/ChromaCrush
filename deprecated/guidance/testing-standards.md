# Testing Standards Guidance

**Version:** 1.0
**Date:** 2026-02-05
**Author:** Testing Agent
**Status:** Final
**Framework:** LLM-Orchestrated Multi-Agent Development Framework v4

---

## 1. Test Organization

### 1.1 Directory Structure

```
tests/
├── unit/                          # Fast, isolated tests
│   ├── modules/                   # Business logic tests
│   │   ├── board/
│   │   │   ├── test_board_service.py
│   │   │   └── test_match_detection.py
│   │   ├── scoring/
│   │   ├── match/
│   │   └── ...
│   ├── data/                      # Repository unit tests
│   │   ├── test_player_repository.py
│   │   └── ...
│   └── core/                      # Core service tests
│       ├── test_config_service.py
│       └── test_error_service.py
├── integration/                   # Tests with real dependencies
│   ├── data/                      # Database integration tests
│   │   ├── conftest.py            # PostgreSQL fixtures
│   │   └── test_player_repository_integration.py
│   ├── redis/                     # Redis integration tests
│   │   ├── conftest.py            # Redis fixtures
│   │   └── test_leaderboard_integration.py
│   └── api/                       # API integration tests
│       ├── conftest.py
│       └── test_game_api.py
├── e2e/                           # End-to-end tests
│   ├── test_match_flow.py
│   └── test_bot_api_flow.py
├── fixtures/                      # Shared test data
│   ├── boards.py
│   ├── players.py
│   └── matches.py
├── mocks/                         # Reusable mock implementations
│   ├── repositories.py
│   ├── services.py
│   └── protocols.py
└── conftest.py                    # Root pytest configuration
```

### 1.2 Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test files | `test_{module}.py` | `test_board_service.py` |
| Test classes | `Test{ClassName}` | `TestBoardService` |
| Test methods | `test_{method}_{scenario}_{expected}` | `test_detect_matches_horizontal_returns_match` |
| Fixtures | `snake_case` descriptive | `mock_board_repository` |
| Mock classes | `Mock{ProtocolName}` | `MockBoardRepository` |

### 1.3 Test Types

| Type | Location | Database | Redis | External | Speed |
|------|----------|----------|-------|----------|-------|
| Unit | `tests/unit/` | Mocked | Mocked | Mocked | < 100ms |
| Integration | `tests/integration/` | Real (SQLite/PostgreSQL) | Real | Mocked | < 5s |
| E2E | `tests/e2e/` | Real (PostgreSQL) | Real | Stubbed | < 30s |

---

## 2. Mocking Standards

### 2.1 Protocol-Based Mocks

All mocks implement the same `Protocol` interfaces used in production code.

```python
# tests/mocks/repositories.py
from typing import Protocol
from uuid import UUID
from src.data.protocols.player_repository import PlayerRepository
from tests.fixtures.players import make_player


class MockPlayerRepository:
    """Mock implementation of PlayerRepository protocol."""

    def __init__(self) -> None:
        self._players: dict[UUID, Player] = {}
        self._call_log: list[tuple[str, tuple, dict]] = []

    async def find_by_id(self, player_id: UUID) -> Player | None:
        self._call_log.append(("find_by_id", (player_id,), {}))
        return self._players.get(player_id)

    async def create(self, data: PlayerCreate) -> Player:
        self._call_log.append(("create", (data,), {}))
        player = make_player(**data.model_dump())
        self._players[player.id] = player
        return player

    async def update(self, player_id: UUID, changes: PlayerUpdate) -> Player:
        self._call_log.append(("update", (player_id, changes), {}))
        player = self._players[player_id]
        for key, value in changes.model_dump(exclude_unset=True).items():
            setattr(player, key, value)
        return player

    async def delete(self, player_id: UUID) -> None:
        self._call_log.append(("delete", (player_id,), {}))
        del self._players[player_id]

    # Test helpers
    def seed(self, *players: Player) -> None:
        """Pre-populate mock with test data."""
        for player in players:
            self._players[player.id] = player

    def assert_called(self, method: str, times: int | None = None) -> None:
        """Assert a method was called."""
        calls = [c for c in self._call_log if c[0] == method]
        if times is not None:
            assert len(calls) == times, f"Expected {times} calls to {method}, got {len(calls)}"
        else:
            assert len(calls) > 0, f"Expected at least one call to {method}"
```

### 2.2 Factory Functions for Test Doubles

```python
# tests/fixtures/players.py
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.modules.player.models import Player


def make_player(
    id: UUID | None = None,
    username: str = "test_player",
    email: str | None = "test@example.com",
    is_bot: bool = False,
    elo_rating: int = 1000,
    created_at: datetime | None = None,
) -> Player:
    """Factory function for creating test Player instances."""
    return Player(
        id=id or uuid4(),
        username=username,
        email=email,
        is_bot=is_bot,
        elo_rating=elo_rating,
        created_at=created_at or datetime.now(timezone.utc),
    )


def make_bot_player(**kwargs) -> Player:
    """Factory for bot players with sensible defaults."""
    defaults = {
        "username": f"bot_{uuid4().hex[:8]}",
        "email": None,
        "is_bot": True,
    }
    defaults.update(kwargs)
    return make_player(**defaults)
```

```python
# tests/fixtures/boards.py
import numpy as np
from src.modules.board.models import Board


def make_board(
    width: int = 8,
    height: int = 8,
    seed: int | None = None,
    state: list[list[int]] | None = None,
) -> Board:
    """Factory function for creating test Board instances."""
    if state is not None:
        return Board(state=np.array(state))

    rng = np.random.default_rng(seed)
    grid = rng.integers(0, 6, size=(height, width))
    return Board(state=grid)


def make_board_with_horizontal_match() -> Board:
    """Creates a board with a guaranteed horizontal match at row 0."""
    state = [
        [1, 1, 1, 2, 3, 4, 5, 6],  # Match at (0,0), (0,1), (0,2)
        [2, 3, 4, 5, 6, 1, 2, 3],
        [3, 4, 5, 6, 1, 2, 3, 4],
        [4, 5, 6, 1, 2, 3, 4, 5],
        [5, 6, 1, 2, 3, 4, 5, 6],
        [6, 1, 2, 3, 4, 5, 6, 1],
        [1, 2, 3, 4, 5, 6, 1, 2],
        [2, 3, 4, 5, 6, 1, 2, 3],
    ]
    return make_board(state=state)
```

### 2.3 Mock Service Injection

```python
# tests/mocks/services.py
from typing import Any


class MockConfigService:
    """Mock implementation of ConfigProtocol."""

    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self._values = values or {}
        self._defaults = {
            "game.board_width": 8,
            "game.board_height": 8,
            "game.gem_types": 6,
            "game.moves_per_match": 20,
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, self._defaults.get(key, default))

    def require(self, key: str) -> Any:
        if key in self._values:
            return self._values[key]
        if key in self._defaults:
            return self._defaults[key]
        raise KeyError(f"Required config key not found: {key}")

    def set(self, key: str, value: Any) -> None:
        """Test helper to override config values."""
        self._values[key] = value


class MockLogService:
    """Mock implementation of LoggerProtocol with call recording."""

    def __init__(self) -> None:
        self.logs: list[tuple[str, str, dict]] = []

    def trace(self, message: str, **context: object) -> None:
        self.logs.append(("TRACE", message, context))

    def debug(self, message: str, **context: object) -> None:
        self.logs.append(("DEBUG", message, context))

    def info(self, message: str, **context: object) -> None:
        self.logs.append(("INFO", message, context))

    def warn(self, message: str, **context: object) -> None:
        self.logs.append(("WARN", message, context))

    def error(self, message: str, **context: object) -> None:
        self.logs.append(("ERROR", message, context))

    def fatal(self, message: str, **context: object) -> None:
        self.logs.append(("FATAL", message, context))

    def assert_logged(self, level: str, message_contains: str) -> None:
        """Assert a log entry exists."""
        for log_level, log_message, _ in self.logs:
            if log_level == level and message_contains in log_message:
                return
        raise AssertionError(
            f"No {level} log containing '{message_contains}' found. "
            f"Logs: {self.logs}"
        )


class MockErrorService:
    """Mock implementation of ErrorServiceProtocol."""

    def __init__(self) -> None:
        self._raised_errors: list[AppError] = []

    def validation(self, message: str, **context: object) -> AppError:
        error = AppError("VALIDATION", message, context)
        self._raised_errors.append(error)
        return error

    def not_found(self, message: str, **context: object) -> AppError:
        error = AppError("NOT_FOUND", message, context)
        self._raised_errors.append(error)
        return error

    def unauthorized(self, message: str, **context: object) -> AppError:
        error = AppError("UNAUTHORIZED", message, context)
        self._raised_errors.append(error)
        return error

    def forbidden(self, message: str, **context: object) -> AppError:
        error = AppError("FORBIDDEN", message, context)
        self._raised_errors.append(error)
        return error

    def conflict(self, message: str, **context: object) -> AppError:
        error = AppError("CONFLICT", message, context)
        self._raised_errors.append(error)
        return error

    def internal(self, message: str, **context: object) -> AppError:
        error = AppError("INTERNAL", message, context)
        self._raised_errors.append(error)
        return error
```

### 2.4 No Global State Manipulation

```python
# DON'T: Patching global state
import unittest.mock as mock

@mock.patch("src.core.config.config")  # VIOLATION
def test_something(mock_config):
    ...

# DON'T: Modifying module-level variables
import src.modules.board.service
src.modules.board.service.SOME_GLOBAL = "test"  # VIOLATION


# DO: Inject mocks through __init__
def test_board_service_detects_horizontal_match():
    # Arrange
    mock_config = MockConfigService()
    mock_logger = MockLogService()
    mock_errors = MockErrorService()
    mock_repo = MockBoardRepository()

    service = BoardService(
        config=mock_config,
        logger=mock_logger,
        errors=mock_errors,
        board_repository=mock_repo,
    )

    board = make_board_with_horizontal_match()

    # Act
    matches = service.detect_matches(board)

    # Assert
    assert len(matches) == 1
    assert matches[0].length == 3
```

---

## 3. Error Path Coverage

### 3.1 Error Taxonomy Test Requirements

Every error type defined in the interface guidance must have at least one test.

```python
# tests/unit/modules/match/test_match_service_errors.py
import pytest
from src.core.errors import AppError


class TestMatchServiceErrors:
    """Tests for all error conditions in MatchService."""

    @pytest.fixture
    def service(self, mock_config, mock_logger, mock_errors, mock_match_repo):
        return MatchService(
            config=mock_config,
            logger=mock_logger,
            errors=mock_errors,
            match_repository=mock_match_repo,
        )

    # VALIDATION errors
    async def test_process_move_invalid_position_raises_validation_error(
        self, service, mock_match_repo
    ):
        """VALIDATION_INVALID_MOVE: Positions not adjacent."""
        match = make_match(status=MatchStatus.IN_PROGRESS)
        mock_match_repo.seed(match)

        move = Move(from_pos=(0, 0), to_pos=(5, 5))  # Not adjacent

        with pytest.raises(AppError) as exc_info:
            await service.process_move(match.id, move)

        assert exc_info.value.error_type == "VALIDATION"
        assert "adjacent" in exc_info.value.message.lower()

    async def test_process_move_out_of_bounds_raises_validation_error(
        self, service, mock_match_repo
    ):
        """VALIDATION_OUT_OF_BOUNDS: Position outside board."""
        match = make_match(status=MatchStatus.IN_PROGRESS)
        mock_match_repo.seed(match)

        move = Move(from_pos=(0, 0), to_pos=(-1, 0))  # Out of bounds

        with pytest.raises(AppError) as exc_info:
            await service.process_move(match.id, move)

        assert exc_info.value.error_type == "VALIDATION"

    # NOT_FOUND errors
    async def test_process_move_nonexistent_match_raises_not_found(
        self, service, mock_match_repo
    ):
        """NOT_FOUND_MATCH: Match does not exist."""
        nonexistent_id = uuid4()
        move = Move(from_pos=(0, 0), to_pos=(0, 1))

        with pytest.raises(AppError) as exc_info:
            await service.process_move(nonexistent_id, move)

        assert exc_info.value.error_type == "NOT_FOUND"

    # CONFLICT errors
    async def test_process_move_completed_match_raises_conflict(
        self, service, mock_match_repo
    ):
        """CONFLICT_MATCH_COMPLETED: Match already finished."""
        match = make_match(status=MatchStatus.COMPLETED)
        mock_match_repo.seed(match)

        move = Move(from_pos=(0, 0), to_pos=(0, 1))

        with pytest.raises(AppError) as exc_info:
            await service.process_move(match.id, move)

        assert exc_info.value.error_type == "CONFLICT"

    # FORBIDDEN errors
    async def test_process_move_wrong_player_raises_forbidden(
        self, service, mock_match_repo
    ):
        """FORBIDDEN_NOT_YOUR_TURN: Player cannot move."""
        match = make_match(current_player_id=uuid4())
        mock_match_repo.seed(match)

        other_player_id = uuid4()
        move = Move(from_pos=(0, 0), to_pos=(0, 1))

        with pytest.raises(AppError) as exc_info:
            await service.process_move(match.id, move, player_id=other_player_id)

        assert exc_info.value.error_type == "FORBIDDEN"
```

### 3.2 Async Error Propagation Testing

```python
# tests/unit/modules/match/test_async_error_propagation.py
import pytest
from unittest.mock import AsyncMock


class TestAsyncErrorPropagation:
    """Verify errors propagate correctly through async boundaries."""

    async def test_repository_error_propagates_as_internal(
        self, service, mock_match_repo
    ):
        """Database errors become INTERNAL errors."""
        mock_match_repo.find_by_id = AsyncMock(
            side_effect=Exception("Database connection lost")
        )

        with pytest.raises(AppError) as exc_info:
            await service.get_match_state(uuid4())

        assert exc_info.value.error_type == "INTERNAL"
        assert "Database connection lost" in str(exc_info.value.__cause__)

    async def test_nested_async_error_preserves_context(self, service):
        """Errors from nested async calls preserve error chain."""
        match_id = uuid4()

        with pytest.raises(AppError) as exc_info:
            await service.complete_match_with_rewards(match_id)

        # Verify error chain is preserved
        assert exc_info.value.__cause__ is not None

    async def test_concurrent_errors_handled_independently(self, service):
        """Multiple concurrent operations fail independently."""
        import asyncio

        match_ids = [uuid4() for _ in range(5)]

        results = await asyncio.gather(
            *[service.get_match_state(mid) for mid in match_ids],
            return_exceptions=True,
        )

        # Each should fail independently
        for result in results:
            assert isinstance(result, AppError)
            assert result.error_type == "NOT_FOUND"
```

### 3.3 Error Context Validation

```python
async def test_error_includes_required_context(self, service, mock_match_repo):
    """Errors must include relevant context for debugging."""
    match_id = uuid4()

    with pytest.raises(AppError) as exc_info:
        await service.get_match_state(match_id)

    error = exc_info.value

    # Verify context includes identifiers
    assert "match_id" in error.context
    assert error.context["match_id"] == match_id
```

---

## 4. Async Testing

### 4.1 pytest-asyncio Configuration

```python
# tests/conftest.py
import pytest

# Use auto mode to automatically detect async tests
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


# pyproject.toml
# [tool.pytest.ini_options]
# asyncio_mode = "auto"
# asyncio_default_fixture_loop_scope = "function"
```

### 4.2 Async Service Fixtures

```python
# tests/conftest.py
import pytest
from tests.mocks.services import MockConfigService, MockLogService, MockErrorService
from tests.mocks.repositories import MockPlayerRepository, MockMatchRepository


@pytest.fixture
def mock_config() -> MockConfigService:
    return MockConfigService()


@pytest.fixture
def mock_logger() -> MockLogService:
    return MockLogService()


@pytest.fixture
def mock_errors() -> MockErrorService:
    return MockErrorService()


@pytest.fixture
def mock_player_repo() -> MockPlayerRepository:
    return MockPlayerRepository()


@pytest.fixture
def mock_match_repo() -> MockMatchRepository:
    return MockMatchRepository()


@pytest.fixture
def board_service(
    mock_config,
    mock_logger,
    mock_errors,
    mock_board_repo,
) -> BoardService:
    """Fully injected BoardService for testing."""
    return BoardService(
        config=mock_config,
        logger=mock_logger,
        errors=mock_errors,
        board_repository=mock_board_repo,
    )


@pytest.fixture
async def match_service(
    mock_config,
    mock_logger,
    mock_errors,
    mock_match_repo,
    mock_player_repo,
) -> MatchService:
    """Fully injected MatchService for testing."""
    return MatchService(
        config=mock_config,
        logger=mock_logger,
        errors=mock_errors,
        match_repository=mock_match_repo,
        player_repository=mock_player_repo,
    )
```

### 4.3 Testing Async Context Managers

```python
# tests/unit/core/test_data_context.py
import pytest


class TestDataContext:
    """Tests for async context manager behavior."""

    async def test_session_commits_on_success(self, data_ctx, mock_session):
        """Successful operations commit automatically."""
        async with data_ctx.session() as session:
            await session.execute("INSERT INTO players ...")

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    async def test_session_rollbacks_on_exception(self, data_ctx, mock_session):
        """Exceptions trigger rollback."""
        with pytest.raises(ValueError):
            async with data_ctx.session() as session:
                await session.execute("INSERT INTO players ...")
                raise ValueError("Intentional failure")

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    async def test_session_closes_always(self, data_ctx, mock_session):
        """Session closes even on exception."""
        try:
            async with data_ctx.session() as session:
                raise ValueError("Intentional failure")
        except ValueError:
            pass

        mock_session.close.assert_called_once()

    async def test_nested_sessions_independent(self, data_ctx):
        """Nested context managers are independent."""
        async with data_ctx.session() as outer:
            async with data_ctx.session() as inner:
                # Inner failure shouldn't affect outer
                pass
            # Outer should still work
            assert outer is not None
```

### 4.4 Timeout Handling

```python
# tests/unit/modules/matchmaking/test_queue_timeout.py
import pytest
import asyncio


class TestMatchmakingTimeout:
    """Tests for async timeout behavior."""

    async def test_find_opponent_respects_timeout(self, matchmaking_service):
        """Matchmaking respects configured timeout."""
        player_id = uuid4()

        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):  # 100ms timeout
                await matchmaking_service.find_opponent(player_id)

    async def test_match_creation_timeout_cleanup(self, matchmaking_service):
        """Timeout during match creation cleans up queue entry."""
        player_id = uuid4()

        try:
            async with asyncio.timeout(0.01):  # Very short timeout
                await matchmaking_service.find_opponent(player_id)
        except asyncio.TimeoutError:
            pass

        # Player should not be stuck in queue
        queue_status = await matchmaking_service.get_queue_status(player_id)
        assert queue_status is None

    async def test_concurrent_operations_timeout_independently(self, service):
        """Multiple concurrent ops timeout independently."""
        async def slow_operation(delay: float) -> str:
            await asyncio.sleep(delay)
            return "completed"

        results = await asyncio.gather(
            asyncio.wait_for(slow_operation(0.01), timeout=0.1),  # Should complete
            asyncio.wait_for(slow_operation(1.0), timeout=0.1),   # Should timeout
            return_exceptions=True,
        )

        assert results[0] == "completed"
        assert isinstance(results[1], asyncio.TimeoutError)
```

---

## 5. Data Layer Testing

### 5.1 Test Database Setup

```python
# tests/integration/data/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.data.models.base import Base


# SQLite for unit tests (fast, in-memory)
@pytest.fixture(scope="session")
def sqlite_engine():
    """In-memory SQLite for fast unit tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    return engine


# PostgreSQL for integration tests (real behavior)
@pytest_asyncio.fixture(scope="session")
async def postgres_engine():
    """PostgreSQL for integration tests."""
    engine = create_async_engine(
        "postgresql+asyncpg://test:test@localhost:5432/chromacrush_test",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(postgres_engine):
    """Individual test session with automatic rollback."""
    async with postgres_engine.connect() as conn:
        await conn.begin()  # Start transaction

        async_session = AsyncSession(bind=conn)

        yield async_session

        await async_session.close()
        await conn.rollback()  # Rollback all changes
```

### 5.2 Transaction Rollback Pattern

```python
# tests/integration/data/test_player_repository_integration.py
import pytest
from uuid import uuid4

from src.data.repositories.player_repository import PlayerRepositoryImpl
from tests.fixtures.players import make_player


class TestPlayerRepositoryIntegration:
    """Integration tests for PlayerRepository with real database."""

    @pytest.fixture
    def repo(self, db_session):
        return PlayerRepositoryImpl(session=db_session)

    async def test_create_player_persists(self, repo, db_session):
        """Created player can be retrieved."""
        player_data = PlayerCreate(
            username="integration_test_user",
            email="integration@test.com",
            is_bot=False,
        )

        created = await repo.create(player_data)

        # Verify persisted
        found = await repo.find_by_id(created.id)
        assert found is not None
        assert found.username == "integration_test_user"

        # Note: This will be rolled back after test

    async def test_update_player_modifies(self, repo, db_session):
        """Updated player reflects changes."""
        # Arrange
        player_data = PlayerCreate(username="original", email="test@test.com")
        created = await repo.create(player_data)

        # Act
        changes = PlayerUpdate(username="updated")
        updated = await repo.update(created.id, changes)

        # Assert
        assert updated.username == "updated"

        # Verify in database
        found = await repo.find_by_id(created.id)
        assert found.username == "updated"

    async def test_delete_player_removes(self, repo, db_session):
        """Deleted player cannot be found."""
        player_data = PlayerCreate(username="to_delete", email="delete@test.com")
        created = await repo.create(player_data)

        await repo.delete(created.id)

        found = await repo.find_by_id(created.id)
        assert found is None

    async def test_concurrent_updates_handle_correctly(self, repo, db_session):
        """Concurrent updates don't corrupt data."""
        import asyncio

        player_data = PlayerCreate(username="concurrent", email="concurrent@test.com")
        created = await repo.create(player_data)

        async def increment_elo():
            player = await repo.find_by_id(created.id)
            changes = PlayerUpdate(elo_rating=player.elo_rating + 10)
            await repo.update(created.id, changes)

        # Run 10 concurrent updates
        await asyncio.gather(*[increment_elo() for _ in range(10)])

        # Verify final state (may not be exactly +100 due to race conditions)
        final = await repo.find_by_id(created.id)
        assert final.elo_rating >= 1010  # At least one update succeeded
```

### 5.3 Redis Mocking

```python
# tests/mocks/redis.py
from typing import Any


class MockRedis:
    """Mock Redis client for unit tests."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._sorted_sets: dict[str, dict[str, float]] = {}
        self._ttls: dict[str, int] = {}
        self._call_log: list[tuple[str, tuple, dict]] = []

    async def get(self, key: str) -> str | None:
        self._call_log.append(("get", (key,), {}))
        return self._data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._call_log.append(("set", (key, value), {"ex": ex}))
        self._data[key] = value
        if ex:
            self._ttls[key] = ex

    async def setex(self, key: str, seconds: int, value: str) -> None:
        self._call_log.append(("setex", (key, seconds, value), {}))
        self._data[key] = value
        self._ttls[key] = seconds

    async def delete(self, *keys: str) -> int:
        self._call_log.append(("delete", keys, {}))
        deleted = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                deleted += 1
        return deleted

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        self._call_log.append(("zadd", (key, mapping), {}))
        if key not in self._sorted_sets:
            self._sorted_sets[key] = {}
        self._sorted_sets[key].update(mapping)
        return len(mapping)

    async def zrevrank(self, key: str, member: str) -> int | None:
        self._call_log.append(("zrevrank", (key, member), {}))
        if key not in self._sorted_sets:
            return None
        sorted_members = sorted(
            self._sorted_sets[key].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        for i, (m, _) in enumerate(sorted_members):
            if m == member:
                return i
        return None

    async def zrevrange(
        self, key: str, start: int, stop: int, withscores: bool = False
    ) -> list:
        self._call_log.append(("zrevrange", (key, start, stop), {"withscores": withscores}))
        if key not in self._sorted_sets:
            return []
        sorted_members = sorted(
            self._sorted_sets[key].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        result = sorted_members[start:stop + 1]
        if withscores:
            return result
        return [m for m, _ in result]

    # Test helpers
    def seed_sorted_set(self, key: str, data: dict[str, float]) -> None:
        """Pre-populate a sorted set."""
        self._sorted_sets[key] = data

    def assert_key_exists(self, key: str) -> None:
        """Assert a key was set."""
        assert key in self._data, f"Key {key} not found. Keys: {list(self._data.keys())}"

    def assert_zadd_called(self, key: str) -> None:
        """Assert zadd was called for a key."""
        calls = [c for c in self._call_log if c[0] == "zadd" and c[1][0] == key]
        assert len(calls) > 0, f"No zadd calls for key {key}"


# tests/integration/redis/conftest.py
import pytest
import pytest_asyncio
from redis.asyncio import Redis


@pytest_asyncio.fixture
async def redis_client():
    """Real Redis connection for integration tests."""
    client = Redis(host="localhost", port=6379, db=15)  # Use separate test DB
    await client.flushdb()  # Clean before test
    yield client
    await client.flushdb()  # Clean after test
    await client.close()
```

---

## 6. Frontend Testing

### 6.1 React Component Testing

```typescript
// web/src/components/game/__tests__/BoardCanvas.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { BoardCanvas } from "../BoardCanvas";
import { useGameStore } from "../../../stores/gameStore";

// Mock Pixi.js
vi.mock("@pixi/react", () => ({
  Stage: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pixi-stage">{children}</div>
  ),
  Container: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pixi-container">{children}</div>
  ),
  Sprite: () => <div data-testid="pixi-sprite" />,
}));

// Mock Zustand store
vi.mock("../../../stores/gameStore");

describe("BoardCanvas", () => {
  const mockGameState = {
    board: [
      [1, 2, 3, 4, 5, 6, 7, 8],
      [2, 3, 4, 5, 6, 7, 8, 1],
      // ... 8x8 grid
    ],
    selectedGem: null,
    selectGem: vi.fn(),
    swapGems: vi.fn(),
    isAnimating: false,
  };

  beforeEach(() => {
    vi.mocked(useGameStore).mockReturnValue(mockGameState);
  });

  it("renders the game stage", () => {
    render(<BoardCanvas />);
    expect(screen.getByTestId("pixi-stage")).toBeInTheDocument();
  });

  it("renders correct number of gem sprites", () => {
    render(<BoardCanvas />);
    const sprites = screen.getAllByTestId("pixi-sprite");
    expect(sprites).toHaveLength(64); // 8x8 board
  });

  it("handles gem selection on click", () => {
    render(<BoardCanvas />);
    const firstGem = screen.getAllByTestId("pixi-sprite")[0];

    fireEvent.click(firstGem);

    expect(mockGameState.selectGem).toHaveBeenCalledWith({ row: 0, col: 0 });
  });

  it("disables interaction during animation", () => {
    vi.mocked(useGameStore).mockReturnValue({
      ...mockGameState,
      isAnimating: true,
    });

    render(<BoardCanvas />);
    const firstGem = screen.getAllByTestId("pixi-sprite")[0];

    fireEvent.click(firstGem);

    expect(mockGameState.selectGem).not.toHaveBeenCalled();
  });
});
```

### 6.2 Canvas/WebGL Mocking

```typescript
// web/src/test/setup.ts
import { vi } from "vitest";

// Mock WebGL context
class MockWebGLRenderingContext {
  canvas = document.createElement("canvas");
  drawingBufferWidth = 800;
  drawingBufferHeight = 600;

  getParameter() {
    return 1;
  }
  getExtension() {
    return {};
  }
  createShader() {
    return {};
  }
  createProgram() {
    return {};
  }
  createBuffer() {
    return {};
  }
  createTexture() {
    return {};
  }
  bindBuffer() {}
  bufferData() {}
  bindTexture() {}
  texImage2D() {}
  viewport() {}
  clear() {}
  enable() {}
  disable() {}
  useProgram() {}
  // Add other methods as needed
}

// Mock canvas getContext
HTMLCanvasElement.prototype.getContext = vi.fn((contextId: string) => {
  if (contextId === "webgl" || contextId === "webgl2") {
    return new MockWebGLRenderingContext();
  }
  return null;
}) as any;

// Mock requestAnimationFrame
vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
  return setTimeout(() => cb(performance.now()), 16);
});

vi.stubGlobal("cancelAnimationFrame", (id: number) => {
  clearTimeout(id);
});

// Mock ResizeObserver
vi.stubGlobal("ResizeObserver", class {
  observe() {}
  unobserve() {}
  disconnect() {}
});
```

### 6.3 State Management Testing

```typescript
// web/src/stores/__tests__/gameStore.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { useGameStore } from "../gameStore";
import { act } from "@testing-library/react";

describe("gameStore", () => {
  beforeEach(() => {
    // Reset store state between tests
    useGameStore.setState({
      board: null,
      score: 0,
      movesRemaining: 20,
      selectedGem: null,
      isAnimating: false,
      matchId: null,
    });
  });

  describe("initializeBoard", () => {
    it("sets board from API response", () => {
      const boardData = [
        [1, 2, 3, 4, 5, 6, 7, 8],
        [2, 3, 4, 5, 6, 7, 8, 1],
      ];

      act(() => {
        useGameStore.getState().initializeBoard(boardData);
      });

      expect(useGameStore.getState().board).toEqual(boardData);
    });

    it("resets score and moves on new board", () => {
      useGameStore.setState({ score: 500, movesRemaining: 5 });

      act(() => {
        useGameStore.getState().initializeBoard([]);
      });

      expect(useGameStore.getState().score).toBe(0);
      expect(useGameStore.getState().movesRemaining).toBe(20);
    });
  });

  describe("selectGem", () => {
    beforeEach(() => {
      useGameStore.setState({
        board: [[1, 2], [3, 4]],
        selectedGem: null,
      });
    });

    it("selects gem when none selected", () => {
      act(() => {
        useGameStore.getState().selectGem({ row: 0, col: 0 });
      });

      expect(useGameStore.getState().selectedGem).toEqual({ row: 0, col: 0 });
    });

    it("deselects when same gem clicked", () => {
      useGameStore.setState({ selectedGem: { row: 0, col: 0 } });

      act(() => {
        useGameStore.getState().selectGem({ row: 0, col: 0 });
      });

      expect(useGameStore.getState().selectedGem).toBeNull();
    });

    it("triggers swap when adjacent gem selected", () => {
      useGameStore.setState({ selectedGem: { row: 0, col: 0 } });

      act(() => {
        useGameStore.getState().selectGem({ row: 0, col: 1 });
      });

      // Should trigger swap and clear selection
      expect(useGameStore.getState().selectedGem).toBeNull();
      expect(useGameStore.getState().isAnimating).toBe(true);
    });

    it("changes selection when non-adjacent gem selected", () => {
      useGameStore.setState({ selectedGem: { row: 0, col: 0 } });

      act(() => {
        useGameStore.getState().selectGem({ row: 1, col: 1 });
      });

      expect(useGameStore.getState().selectedGem).toEqual({ row: 1, col: 1 });
    });
  });

  describe("applyMoveResult", () => {
    it("updates board, score, and moves from API response", () => {
      const moveResult = {
        board: [[5, 6], [7, 8]],
        scoreGained: 150,
        movesRemaining: 19,
        matches: [{ positions: [[0, 0], [0, 1], [0, 2]], gemType: 1 }],
      };

      act(() => {
        useGameStore.getState().applyMoveResult(moveResult);
      });

      expect(useGameStore.getState().board).toEqual([[5, 6], [7, 8]]);
      expect(useGameStore.getState().score).toBe(150);
      expect(useGameStore.getState().movesRemaining).toBe(19);
    });
  });
});
```

### 6.4 Hook Testing

```typescript
// web/src/hooks/__tests__/useGameState.test.ts
import { renderHook, act, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { useGameState } from "../useGameState";
import { apiClient } from "../../api/client";

vi.mock("../../api/client");

describe("useGameState", () => {
  const mockMatchData = {
    matchId: "test-match-123",
    board: [[1, 2, 3, 4, 5, 6, 7, 8]],
    score: 0,
    movesRemaining: 20,
    opponentScore: 0,
  };

  beforeEach(() => {
    vi.mocked(apiClient.getMatchState).mockResolvedValue(mockMatchData);
    vi.mocked(apiClient.submitMove).mockResolvedValue({
      board: [[2, 3, 4, 5, 6, 7, 8, 1]],
      scoreGained: 100,
      movesRemaining: 19,
      matches: [],
    });
  });

  it("fetches match state on mount", async () => {
    const { result } = renderHook(() => useGameState("test-match-123"));

    await waitFor(() => {
      expect(result.current.board).toEqual([[1, 2, 3, 4, 5, 6, 7, 8]]);
    });

    expect(apiClient.getMatchState).toHaveBeenCalledWith("test-match-123");
  });

  it("submits move and updates state", async () => {
    const { result } = renderHook(() => useGameState("test-match-123"));

    await waitFor(() => {
      expect(result.current.board).toBeDefined();
    });

    await act(async () => {
      await result.current.submitMove({ from: [0, 0], to: [0, 1] });
    });

    expect(apiClient.submitMove).toHaveBeenCalled();
    expect(result.current.score).toBe(100);
    expect(result.current.movesRemaining).toBe(19);
  });

  it("handles API errors gracefully", async () => {
    vi.mocked(apiClient.getMatchState).mockRejectedValue(
      new Error("Network error")
    );

    const { result } = renderHook(() => useGameState("test-match-123"));

    await waitFor(() => {
      expect(result.current.error).toBe("Network error");
    });

    expect(result.current.board).toBeNull();
  });
});
```

---

## 7. Coverage Expectations

### 7.1 Minimum Coverage by Component Type

| Component Type | Line Coverage | Branch Coverage | Required Tests |
|----------------|---------------|-----------------|----------------|
| Core services (`src/core/`) | 95% | 90% | Unit |
| Module services (`src/modules/`) | 90% | 85% | Unit + Integration |
| Repository implementations | 85% | 80% | Unit + Integration |
| CLI commands | 80% | 75% | Unit |
| API endpoints | 85% | 80% | Integration |
| React components | 80% | 75% | Unit |
| Zustand stores | 90% | 85% | Unit |
| Hooks | 85% | 80% | Unit |

### 7.2 Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = [
    "src/data/migrations/*",
    "src/data/seeds/*",
    "*/test*",
    "*/__pycache__/*",
]
branch = true

[tool.coverage.report]
fail_under = 85
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "@abstractmethod",
]
show_missing = true
```

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      exclude: [
        "node_modules/",
        "src/test/",
        "**/*.d.ts",
        "**/*.config.ts",
      ],
      thresholds: {
        lines: 80,
        branches: 75,
        functions: 80,
        statements: 80,
      },
    },
  },
});
```

### 7.3 Required Test Types Per Module

| Module | Unit Tests | Integration Tests | E2E Tests |
|--------|------------|-------------------|-----------|
| `board` | Match detection, cascades, validity | - | Match flow |
| `scoring` | Point calculation, multipliers | - | Match flow |
| `special_gems` | Effect calculation, fusions | - | Match flow |
| `board_gen` | Seeded generation, cascade potential | - | - |
| `match` | State transitions, move validation | Full match lifecycle | Bot API flow |
| `matchmaking` | Queue logic, ELO calculation | Redis queue | - |
| `player` | CRUD, stats calculation | PostgreSQL | Account creation |
| `vault` | Raid logic, artifact grants | PostgreSQL | - |
| `energy` | Timer calculation, regen | Redis TTL | - |
| `auth` | Token validation, API key | JWT flow | Login flow |

### 7.4 CI Pipeline Requirements

```yaml
# .github/workflows/test.yml
test:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_USER: test
        POSTGRES_PASSWORD: test
        POSTGRES_DB: chromacrush_test
      ports:
        - 5432:5432
    redis:
      image: redis:7
      ports:
        - 6379:6379
  steps:
    - name: Run unit tests
      run: pytest tests/unit -v --cov=src --cov-report=xml

    - name: Run integration tests
      run: pytest tests/integration -v --cov=src --cov-append --cov-report=xml

    - name: Check coverage threshold
      run: coverage report --fail-under=85

    - name: Run frontend tests
      working-directory: web
      run: npm run test:coverage
```

---

## 8. Test Execution Commands

### 8.1 Python Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests
pytest tests/unit

# Run only integration tests (requires running services)
pytest tests/integration

# Run tests for specific module
pytest tests/unit/modules/board

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x

# Run tests matching pattern
pytest -k "test_detect_matches"

# Run marked tests
pytest -m "slow"
pytest -m "not slow"
```

### 8.2 Frontend Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run specific file
npm test -- BoardCanvas.test.tsx

# Run with UI
npm run test:ui
```

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial guidance | Testing Agent |
