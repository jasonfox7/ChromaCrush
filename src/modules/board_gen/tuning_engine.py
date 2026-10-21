"""Board tuning algorithms — cascade and near-miss transformations.

Takes board state + configuration parameters and returns modified boards.
No I/O or service state — all dependencies passed explicitly.
Called by ``BoardGenService`` to tune generated boards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import numpy as np

from src.core.types.board import BoardState

if TYPE_CHECKING:
    from numpy.random import Generator

# Tuning constants (must match service.py originals).
_CASCADE_TUNING_TOLERANCE = 0.05
_CASCADE_TUNING_MAX_ITERATIONS = 50
_NEAR_MISS_DENSITY_FACTOR = 0.1
_NEAR_MISS_MAX_TRIES_MULTIPLIER = 10


def apply_cascade_tuning(
    board: BoardState,
    target: float,
    rng: Generator,
    gem_types: int,
    special_gem_values: frozenset[int],
    calculate_cascade_potential: Callable[[BoardState], float],
) -> BoardState:
    """Iteratively adjust board toward target cascade potential.

    Makes up to 50 single-gem swaps, each time moving cascade
    potential closer to target without creating any matches.

    Args:
        board: Board to tune.
        target: Desired cascade potential (0.0-1.0).
        rng: NumPy random generator for deterministic behaviour.
        gem_types: Number of standard gem types (e.g. 6).
        special_gem_values: Set of int values representing special gems.
        calculate_cascade_potential: Callable that scores a board's cascade potential.

    Returns:
        A new BoardState tuned toward the target cascade potential.
    """
    current = calculate_cascade_potential(board)
    tolerance = _CASCADE_TUNING_TOLERANCE
    max_iterations = _CASCADE_TUNING_MAX_ITERATIONS
    grid = board.grid.copy()

    all_gems = list(range(1, gem_types + 1))

    for _ in range(max_iterations):
        if abs(current - target) < tolerance:
            break

        # Pick a random position to adjust.
        row = int(rng.integers(0, board.height))
        col = int(rng.integers(0, board.width))
        old_gem = int(grid[row, col])

        # Skip special gems.
        if old_gem in special_gem_values or old_gem == 0:
            continue

        # Try a different gem.
        candidates = [g for g in all_gems if g != old_gem]
        rng.shuffle(candidates)

        for new_gem in candidates:
            grid[row, col] = new_gem
            test_board = BoardState(grid=grid.copy())

            # Ensure no match created.
            if not _would_create_match(grid, row, col, board.height, board.width):
                new_potential = calculate_cascade_potential(test_board)
                # Accept if it moves closer to target.
                if abs(new_potential - target) < abs(current - target):
                    current = new_potential
                    break
            # Revert.
            grid[row, col] = old_gem
        else:
            grid[row, col] = old_gem

    return BoardState(grid=grid)


def apply_near_miss_tuning(
    board: BoardState,
    factor: float,
    rng: Generator,
    special_gem_values: frozenset[int],
) -> tuple[BoardState, int]:
    """Place near-miss patterns on the board.

    A near-miss is two same-colour gems that are one swap away from
    forming a 3-in-a-row match.

    Args:
        board: Board to tune.
        factor: Near-miss density factor (0.0-1.0).
        rng: NumPy random generator for deterministic behaviour.
        special_gem_values: Set of int values representing special gems.

    Returns:
        Tuple of (tuned board, number of near-misses placed).
    """
    target_count = int(board.width * board.height * factor * _NEAR_MISS_DENSITY_FACTOR)
    if target_count <= 0:
        return board, 0

    grid = board.grid.copy()
    placed = 0
    max_tries = target_count * _NEAR_MISS_MAX_TRIES_MULTIPLIER  # Avoid infinite loops.

    for _ in range(max_tries):
        if placed >= target_count:
            break

        # Pick a random starting position.
        row = int(rng.integers(0, board.height))
        col = int(rng.integers(0, board.width))

        # Try horizontal near-miss: place same gem at col and col+1
        # (the third would need to be swapped in — a "near miss").
        if col < board.width - 2:
            gem = int(grid[row, col])
            if gem <= 0 or gem in special_gem_values:
                continue

            old_next = int(grid[row, col + 1])
            if old_next == gem or old_next <= 0:
                continue

            # Set col+1 to same gem.
            grid[row, col + 1] = gem
            if not _would_create_match(grid, row, col + 1, board.height, board.width):
                placed += 1
            else:
                grid[row, col + 1] = old_next
            continue

        # Try vertical near-miss.
        if row < board.height - 2:
            gem = int(grid[row, col])
            if gem <= 0 or gem in special_gem_values:
                continue

            old_below = int(grid[row + 1, col])
            if old_below == gem or old_below <= 0:
                continue

            grid[row + 1, col] = gem
            if not _would_create_match(grid, row + 1, col, board.height, board.width):
                placed += 1
            else:
                grid[row + 1, col] = old_below

    return BoardState(grid=grid), placed


def _would_create_match(
    grid: np.ndarray, row: int, col: int, height: int, width: int
) -> bool:
    """Check if the gem at (row, col) creates a 3-in-a-row.

    Faster than full detect_matches -- only checks the local neighbourhood
    of the modified cell.
    """
    gem = int(grid[row, col])
    if gem <= 0:
        return False

    # Check horizontal run through this cell.
    h_count = 1
    # Left.
    c = col - 1
    while c >= 0 and int(grid[row, c]) == gem:
        h_count += 1
        c -= 1
    # Right.
    c = col + 1
    while c < width and int(grid[row, c]) == gem:
        h_count += 1
        c += 1
    if h_count >= 3:
        return True

    # Check vertical run through this cell.
    v_count = 1
    # Up.
    r = row - 1
    while r >= 0 and int(grid[r, col]) == gem:
        v_count += 1
        r -= 1
    # Down.
    r = row + 1
    while r < height and int(grid[r, col]) == gem:
        v_count += 1
        r += 1
    if v_count >= 3:
        return True

    return False
