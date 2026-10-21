"""Integration tests for move submission flow.

Validates the full submit_move pipeline using real PostgreSQL and Redis.
Tests cover: valid moves, cascade scoring, status transitions, move
remaining decrement, invalid swaps, wrong player, no moves remaining,
match completion, forfeit, and get_match_state.
"""

from __future__ import annotations

import time
import pytest
from uuid import UUID

from src.core.errors import AppError
from src.core.types.board import BoardState
from src.core.types.game import MatchId, Move, PlayerId, Position
from src.core.types.player import PlayerType
from src.modules.match.types import MatchStatus, MatchType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_match(factory, seed=42):
    """Create two players and a match, returning (p1_id, p2_id, match_state)."""
    p1 = await factory.player_service.create_player(
        username="alice",
        player_type=PlayerType.HUMAN,
    )
    p2 = await factory.player_service.create_player(
        username="bob",
        player_type=PlayerType.HUMAN,
    )
    p1_id = PlayerId(p1.id)
    p2_id = PlayerId(p2.id)
    match_state = await factory.match_service.create_match(
        p1_id,
        p2_id,
        board_seed=seed,
    )
    return p1_id, p2_id, match_state


def _find_valid_move(board: BoardState, board_service) -> Move | None:
    """Scan the board for the first swap that produces at least one match.

    Tries every adjacent pair (right and down) until a valid one is found.
    Returns a Move or None if no valid move exists.
    """
    grid = board.grid
    rows, cols = grid.shape
    ts = int(time.time() * 1000)

    for r in range(rows):
        for c in range(cols):
            # Try right swap
            if c + 1 < cols:
                from_pos = Position(r, c)
                to_pos = Position(r, c + 1)
                move = Move(from_pos=from_pos, to_pos=to_pos, timestamp_ms=ts)
                result = board_service.process_move(board, move, seed=999)
                if result.was_valid_match:
                    return move
            # Try down swap
            if r + 1 < rows:
                from_pos = Position(r, c)
                to_pos = Position(r + 1, c)
                move = Move(from_pos=from_pos, to_pos=to_pos, timestamp_ms=ts)
                result = board_service.process_move(board, move, seed=999)
                if result.was_valid_match:
                    return move
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMoveSubmissionHappyPath:
    """Tests for successful move submission."""

    async def test_submit_valid_move_returns_result(self, factory):
        """A valid move returns MoveSubmissionResult with points earned."""
        p1_id, p2_id, match_state = await _setup_match(factory)

        # Find a valid move on player1 board
        board = match_state.player1.current_board
        move = _find_valid_move(board, factory.board_service)
        assert move is not None, "No valid move found on board"

        result = await factory.match_service.submit_move(
            match_state.match_id,
            p1_id,
            move,
        )

        assert result.points_earned >= 0
        assert result.move_number == 1
        assert result.moves_remaining == 19
        assert result.match_completed is False
        assert result.player_finished is False

    async def test_submit_move_cascades_earn_points(self, factory):
        """Move that creates cascades earns positive points."""
        p1_id, p2_id, match_state = await _setup_match(factory)

        board = match_state.player1.current_board
        move = _find_valid_move(board, factory.board_service)
        assert move is not None, "No valid move found on board"

        result = await factory.match_service.submit_move(
            match_state.match_id,
            p1_id,
            move,
        )

        # A valid move should produce matches and earn points
        assert result.move_result.was_valid_match is True
        assert result.move_result.total_gems_cleared > 0
        assert result.points_earned > 0

    async def test_first_move_transitions_to_in_progress(self, factory):
        """First move changes match status from PENDING to IN_PROGRESS."""
        p1_id, p2_id, match_state = await _setup_match(factory)
        assert match_state.status == MatchStatus.PENDING

        board = match_state.player1.current_board
        move = _find_valid_move(board, factory.board_service)
        assert move is not None

        result = await factory.match_service.submit_move(
            match_state.match_id,
            p1_id,
            move,
        )

        assert result.match_state.status == MatchStatus.IN_PROGRESS

    async def test_submit_move_decrements_moves_remaining(self, factory):
        """Each move decrements moves_remaining by 1."""
        p1_id, p2_id, match_state = await _setup_match(factory)

        assert match_state.player1.moves_remaining == 20

        board = match_state.player1.current_board
        move = _find_valid_move(board, factory.board_service)
        assert move is not None

        result = await factory.match_service.submit_move(
            match_state.match_id,
            p1_id,
            move,
        )

        assert result.moves_remaining == 19
        p1_state = result.match_state.get_player_state(p1_id)
        assert p1_state is not None
        assert p1_state.moves_remaining == 19


class TestMoveSubmissionErrors:
    """Tests for error conditions during move submission."""

    async def test_submit_invalid_swap_no_matches(self, factory):
        """Raises VALIDATION_INVALID_GEM_SWAP for a swap that creates no matches."""
        p1_id, p2_id, match_state = await _setup_match(factory)

        # Try every adjacent pair until we find one that does NOT match
        board = match_state.player1.current_board
        grid = board.grid
        rows, cols = grid.shape
        ts = int(time.time() * 1000)
        invalid_move = None

        for r in range(rows):
            for c in range(cols):
                if c + 1 < cols:
                    from_pos = Position(r, c)
                    to_pos = Position(r, c + 1)
                    m = Move(from_pos=from_pos, to_pos=to_pos, timestamp_ms=ts)
                    res = factory.board_service.process_move(board, m, seed=999)
                    if not res.was_valid_match:
                        invalid_move = m
                        break
            if invalid_move is not None:
                break

        assert invalid_move is not None, "Could not find an invalid move"

        with pytest.raises(AppError) as exc_info:
            await factory.match_service.submit_move(
                match_state.match_id,
                p1_id,
                invalid_move,
            )

        assert exc_info.value.code == "VALIDATION_INVALID_GEM_SWAP"

    async def test_submit_move_wrong_player(self, factory):
        """Raises FORBIDDEN_NOT_MATCH_PARTICIPANT for a non-participant."""
        p1_id, p2_id, match_state = await _setup_match(factory)

        # Create a third player who is not in the match
        p3 = await factory.player_service.create_player(
            username="charlie",
            player_type=PlayerType.HUMAN,
        )
        p3_id = PlayerId(p3.id)

        board = match_state.player1.current_board
        move = _find_valid_move(board, factory.board_service)
        assert move is not None

        with pytest.raises(AppError) as exc_info:
            await factory.match_service.submit_move(
                match_state.match_id,
                p3_id,
                move,
            )

        assert exc_info.value.code == "FORBIDDEN_NOT_MATCH_PARTICIPANT"

    async def test_submit_move_no_moves_remaining(self, factory):
        """Raises VALIDATION_NO_MOVES_REMAINING when all moves are used."""
        p1_id, p2_id, match_state = await _setup_match(factory)

        # Set player1 moves_remaining to 0 directly via repo
        from src.modules.match.dto import MatchUpdate

        update = MatchUpdate(player1_moves_remaining=0)
        await factory.match_repo.update(
            UUID(str(match_state.match_id)),
            update,
        )

        board = match_state.player1.current_board
        move = _find_valid_move(board, factory.board_service)
        assert move is not None

        with pytest.raises(AppError) as exc_info:
            await factory.match_service.submit_move(
                match_state.match_id,
                p1_id,
                move,
            )

        assert exc_info.value.code == "VALIDATION_NO_MOVES_REMAINING"


class TestMatchCompletionAndForfeit:
    """Tests for match completion and forfeit flows."""

    async def test_match_completion_when_both_finish(self, factory):
        """Match status becomes COMPLETED when both players use all moves."""
        p1_id, p2_id, match_state = await _setup_match(factory)

        # Set both players to 1 move remaining via repo
        from src.modules.match.dto import MatchUpdate

        update = MatchUpdate(
            player1_moves_remaining=1,
            player1_moves_made=19,
            player2_moves_remaining=1,
            player2_moves_made=19,
            status="in_progress",
        )
        await factory.match_repo.update(
            UUID(str(match_state.match_id)),
            update,
        )

        # Reload match state to get updated boards
        updated = await factory.match_service.get_match(match_state.match_id)

        # P1 makes their last move
        board1 = updated.player1.current_board
        move1 = _find_valid_move(board1, factory.board_service)
        assert move1 is not None, "No valid move for p1"

        result1 = await factory.match_service.submit_move(
            match_state.match_id,
            p1_id,
            move1,
        )
        assert result1.player_finished is True
        assert result1.match_completed is False  # P2 still has 1 move

        # Reload again to get P2 board after P1 finished
        updated2 = await factory.match_service.get_match(match_state.match_id)

        # P2 makes their last move
        board2 = updated2.player2.current_board
        move2 = _find_valid_move(board2, factory.board_service)
        assert move2 is not None, "No valid move for p2"

        result2 = await factory.match_service.submit_move(
            match_state.match_id,
            p2_id,
            move2,
        )
        assert result2.player_finished is True
        assert result2.match_completed is True
        assert result2.match_state.status == MatchStatus.COMPLETED

    async def test_forfeit_match(self, factory):
        """Forfeit sets status to COMPLETED and records winner."""
        p1_id, p2_id, match_state = await _setup_match(factory)

        # P1 forfeits; P2 should be the winner
        result = await factory.match_service.forfeit_match(
            match_state.match_id,
            p1_id,
        )

        assert result.status == MatchStatus.COMPLETED
        assert result.winner_id == p2_id
        assert result.forfeit_by == p1_id

    async def test_get_match_state_returns_current_state(self, factory):
        """get_match returns the current state after moves."""
        p1_id, p2_id, match_state = await _setup_match(factory)

        # Submit a move
        board = match_state.player1.current_board
        move = _find_valid_move(board, factory.board_service)
        assert move is not None

        await factory.match_service.submit_move(
            match_state.match_id,
            p1_id,
            move,
        )

        # Retrieve state
        state = await factory.match_service.get_match(match_state.match_id)

        assert state.status == MatchStatus.IN_PROGRESS
        p1_state = state.get_player_state(p1_id)
        assert p1_state is not None
        assert p1_state.moves_made == 1
        assert p1_state.moves_remaining == 19
        assert p1_state.score > 0
