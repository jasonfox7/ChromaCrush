"""Cascade potential analysis — pure static board evaluation.

All functions are pure computation on BoardState with no I/O or side effects.
Called by ``BoardGenService`` to evaluate cascade potential scores.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from src.core.types.board import BoardState

if TYPE_CHECKING:
    pass

# Cascade factor weights (must match service.py constants).
_CASCADE_WEIGHT_PATTERNS = 0.4
_CASCADE_WEIGHT_VERTICAL = 0.3
_CASCADE_WEIGHT_CLUSTERING = 0.2
_CASCADE_WEIGHT_MOVE_DENSITY = 0.1


def calculate_cascade_potential(
    board: BoardState,
    count_valid_moves: Callable[[BoardState], int],
) -> float:
    """Analyse a board and return a cascade potential score (0.0-1.0).

    Weighted factors:
    - Favourable patterns (40%): XX_X gaps, vertical pairs
    - Vertical alignment (30%): same-colour stacking with gaps
    - Colour clustering (20%): tightly grouped same-colour gems
    - Valid move density (10%): ratio of valid moves to max possible

    Args:
        board: Board to analyse.
        count_valid_moves: Callable that counts valid moves on a board.

    Returns:
        A float between 0.0 and 1.0.
    """
    # Factor 1: Favourable patterns (40%).
    patterns = count_favorable_patterns(board)
    max_patterns = max(1, (board.width * board.height) // 4)
    f1 = min(1.0, patterns / max_patterns)

    # Factor 2: Vertical alignment (30%).
    f2 = calculate_vertical_alignment(board)

    # Factor 3: Colour clustering (20%).
    f3 = calculate_color_clustering(board)

    # Factor 4: Valid move density (10%).
    valid_moves = count_valid_moves(board)
    max_moves = (board.width - 1) * board.height + board.width * (board.height - 1)
    f4 = valid_moves / max(1, max_moves)

    score = (
        _CASCADE_WEIGHT_PATTERNS * f1
        + _CASCADE_WEIGHT_VERTICAL * f2
        + _CASCADE_WEIGHT_CLUSTERING * f3
        + _CASCADE_WEIGHT_MOVE_DENSITY * f4
    )
    return min(1.0, max(0.0, score))


def count_favorable_patterns(board: BoardState) -> int:
    """Count patterns likely to produce cascades."""
    count = 0
    grid = board.grid

    # Horizontal gap pattern: XX_X (same gem at 0,1,3 but different at 2).
    for row in range(board.height):
        for col in range(board.width - 3):
            if (
                grid[row, col] == grid[row, col + 1]
                and grid[row, col] == grid[row, col + 3]
                and grid[row, col + 2] != grid[row, col]
                and grid[row, col] > 0
            ):
                count += 1

    # Vertical pairs with different gem above.
    for col in range(board.width):
        for row in range(1, board.height - 1):
            if (
                grid[row, col] == grid[row + 1, col]
                and grid[row - 1, col] != grid[row, col]
                and grid[row, col] > 0
            ):
                count += 1

    return count


def calculate_vertical_alignment(board: BoardState) -> float:
    """Score how many same-colour gems are stacked vertically with gaps."""
    score = 0
    total_checks = 0
    grid = board.grid

    for col in range(board.width):
        for row in range(board.height - 2):
            if grid[row, col] > 0 and grid[row + 2, col] > 0:
                total_checks += 1
                if (
                    grid[row, col] == grid[row + 2, col]
                    and grid[row + 1, col] != grid[row, col]
                ):
                    score += 1

    return score / max(1, total_checks)


def calculate_color_clustering(board: BoardState) -> float:
    """Score how tightly grouped same-colour gems are."""
    adjacency_matches = 0
    total_adjacencies = 0
    grid = board.grid

    for row in range(board.height):
        for col in range(board.width):
            gem = grid[row, col]
            if gem <= 0:
                continue
            # Check right neighbour.
            if col < board.width - 1 and grid[row, col + 1] > 0:
                total_adjacencies += 1
                if grid[row, col + 1] == gem:
                    adjacency_matches += 1
            # Check bottom neighbour.
            if row < board.height - 1 and grid[row + 1, col] > 0:
                total_adjacencies += 1
                if grid[row + 1, col] == gem:
                    adjacency_matches += 1

    return adjacency_matches / max(1, total_adjacencies)
