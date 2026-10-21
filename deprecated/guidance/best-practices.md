# Best Practices Guidance

> **Version:** 1.0
> **Date:** 2026-02-05
> **Author:** Best Practices Agent
> **Status:** Final
> **Framework:** v4.0

---

## 1. `__init__` Injection Pattern

All dependencies must be explicitly passed through constructor parameters.

### 1.1 Python Service Pattern

```python
# DO: Correct service implementation
from typing import Protocol


class LoggerProtocol(Protocol):
    def info(self, message: str, **context: object) -> None: ...
    def error(self, message: str, **context: object) -> None: ...


class BoardService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        board_repository: BoardRepositoryProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._board_repo = board_repository
```

```python
# DON'T: Direct imports of core services
from core.logger import logger  # VIOLATION
from core.config import config  # VIOLATION
```

### 1.2 Composition Root

The composition root (`src/core/composition_root.py`) is the **only** location where services are instantiated.

---

## 2. Concurrency & Async Patterns

### 2.1 Async Interface Rule

If a method performs async work, it **must** be declared `async def`.

```python
# DO
async def get_match_state(self, match_id: str) -> MatchState:
    match = await self._match_repo.find_by_id(match_id)
    return self._build_match_state(match)

# DON'T: Hidden async
def get_match_state(self, match_id: str) -> MatchState:
    match = asyncio.run(self._match_repo.find_by_id(match_id))  # VIOLATION
```

### 2.2 No Fire-and-Forget

Every async operation must be awaited or explicitly logged if detached.

```python
# DO
await self._update_elo(result)

# DON'T
asyncio.create_task(self._update_elo(result))  # VIOLATION: Silent fire-and-forget
```

### 2.3 Async Error Handling

```python
async def process_move(self, match_id: str, move: Move) -> MoveResult:
    try:
        match = await self._match_repo.find_by_id(match_id)
        if match is None:
            raise self._errors.not_found("Match not found", match_id=match_id)
        return await self._execute_move(match, move)
    except AppError:
        raise
    except Exception as e:
        raise self._errors.internal("Failed to process move", original_error=str(e)) from e
```

---

## 3. Code Quality Rules

### 3.1 No Magic Numbers

```python
# DO
class BoardConstants:
    MIN_MATCH_LENGTH = 3

def is_valid_match(self, gems: list[Gem]) -> bool:
    return len(gems) >= BoardConstants.MIN_MATCH_LENGTH

# DON'T
def is_valid_match(self, gems: list[Gem]) -> bool:
    return len(gems) >= 3  # VIOLATION
```

### 3.2 No Direct Environment Access

```python
# DO
def __init__(self, config: ConfigProtocol):
    self._db_url = config.require("database.connection_string")

# DON'T
import os
self._db_url = os.environ["DATABASE_URL"]  # VIOLATION
```

### 3.3 No Bare Raises

```python
# DO
raise self._errors.validation("Positions must be adjacent", from_pos=move.from_pos)

# DON'T
raise ValueError("Positions must be adjacent")  # VIOLATION
```

### 3.4 No UI in Business Logic

Modules in `src/modules/` must not reference rendering or display concerns.

### 3.5 No Raw Data Access in Business Logic

No direct SQL or ORM calls in `src/modules/`. All data through repository interfaces.

---

## 4. Naming Conventions

### Python

| Element | Convention | Example |
|---------|------------|---------|
| Files/modules | `snake_case` | `board_service.py` |
| Classes | `PascalCase` | `BoardService` |
| Functions/methods | `snake_case` | `detect_matches()` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_BOARD_SIZE` |
| Protocols | `PascalCase` + `Protocol` | `LoggerProtocol` |

### TypeScript

| Element | Convention | Example |
|---------|------------|---------|
| Files (components) | `PascalCase.tsx` | `BoardCanvas.tsx` |
| Files (utilities) | `camelCase.ts` | `gameUtils.ts` |
| React components | `PascalCase` | `BoardCanvas` |
| Hooks | `use` prefix | `useGameState` |

---

## 5. File Organization

### Maximum File Length

| File Type | Soft Limit | Hard Limit |
|-----------|------------|------------|
| Python service | 300 lines | 500 lines |
| TypeScript component | 200 lines | 300 lines |

### Function Complexity

- Maximum cyclomatic complexity: 10
- Maximum function length: 50 lines
- Maximum parameters: 6
- Maximum nesting depth: 4

---

## 6. Logging Severity Guidelines

| Level | When to Use | Example |
|-------|-------------|---------|
| TRACE | Step-by-step execution | `Checking cell row=r col=c` |
| DEBUG | Developer diagnostics | `Board generated seed=123` |
| INFO | Normal operations | `Match started match_id=abc` |
| WARN | Unexpected but recoverable | `Retry succeeded attempt=3` |
| ERROR | Operation failed | `Database query failed` |
| FATAL | Unrecoverable failure | `Connection pool exhausted` |

---

## 7. Documentation Standards

### Docstring Format (Google Style)

```python
def calculate_cascade_potential(self, board: Board, depth: int = 3) -> float:
    """Calculate the cascade potential for a board state.

    Args:
        board: The current board state to analyze.
        depth: How many levels of cascades to simulate.

    Returns:
        A float between 0.0 and 1.0 representing cascade likelihood.

    Raises:
        ValidationError: If board is invalid.
    """
```

### Type Hints Required

```python
# DO
def find_matches(self, board: list[list[Gem]], min_length: int = 3) -> list[Match]:
    ...

# DON'T
def find_matches(self, board, min_length=3):  # VIOLATION
    ...
```

---

## 8. Version Control

### Commit Format

```
[phase].[step] [role]: [concise description]
```

Examples:
- `1.0 best-practices-agent: initial guidance document`
- `2.2 coder: module-board implementation`

### Branch Strategy

- `main` - Stable, merges at phase gates only
- `develop` - All agent work

---

## Changelog

| Date | Version | Author | Change |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Best Practices Agent | Initial guidance |
