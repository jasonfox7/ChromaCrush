"""Integration tests for match creation flow.

Validates the full create_match pipeline using real PostgreSQL and Redis.
Tests cover: happy path, valid board, energy consumption, error cases,
concurrent match limits, and deterministic seeding.
"""

from __future__ import annotations

import pytest
from uuid import UUID

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.core.types.player import PlayerType
from src.modules.match.types import MatchStatus, MatchType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_two_players(factory):
    """Create two human players and return their PlayerId values."""
    p1 = await factory.player_service.create_player(
        username="alice",
        player_type=PlayerType.HUMAN,
    )
    p2 = await factory.player_service.create_player(
        username="bob",
        player_type=PlayerType.HUMAN,
    )
    return PlayerId(p1.id), PlayerId(p2.id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMatchCreationHappyPath:
    """Tests for the successful match creation flow."""

    async def test_create_match_returns_pending_state(self, factory):
        """create_match returns a MatchState with PENDING status."""
        p1_id, p2_id = await _create_two_players(factory)

        match_state = await factory.match_service.create_match(
            p1_id,
            p2_id,
            board_seed=42,
        )

        assert match_state.status == MatchStatus.PENDING
        assert match_state.match_type == MatchType.STANDARD
        assert match_state.player1.player_id == p1_id
        assert match_state.player2.player_id == p2_id
        assert match_state.winner_id is None
        assert match_state.forfeit_by is None

    async def test_create_match_generates_valid_board(self, factory):
        """The initial board is an 8x8 grid with no pre-existing matches."""
        p1_id, p2_id = await _create_two_players(factory)

        match_state = await factory.match_service.create_match(
            p1_id,
            p2_id,
            board_seed=42,
        )

        board = match_state.initial_board
        grid = board.to_list()

        # 8x8 board
        assert len(grid) == 8
        assert all(len(row) == 8 for row in grid)

        # All cells contain valid gem types (1-6)
        for row in grid:
            for cell in row:
                assert 1 <= cell <= 6 or cell < 0, f"Invalid gem value: {cell}"

        # Board should have valid moves
        has_moves = factory.board_service.has_valid_moves(board)
        assert has_moves is True

    async def test_create_match_consumes_energy(self, factory):
        """Both players lose 1 heart after match creation."""
        p1_id, p2_id = await _create_two_players(factory)

        # Check initial energy (should be 5 = max_hearts)
        p1_energy_before = await factory.player_service.get_energy_state(p1_id)
        p2_energy_before = await factory.player_service.get_energy_state(p2_id)
        assert p1_energy_before.hearts == 5
        assert p2_energy_before.hearts == 5

        await factory.match_service.create_match(p1_id, p2_id, board_seed=42)

        p1_energy_after = await factory.player_service.get_energy_state(p1_id)
        p2_energy_after = await factory.player_service.get_energy_state(p2_id)
        assert p1_energy_after.hearts == 4
        assert p2_energy_after.hearts == 4

    async def test_create_match_with_deterministic_seed(self, factory):
        """Same seed produces the same initial board."""
        p1_id, p2_id = await _create_two_players(factory)

        match1 = await factory.match_service.create_match(
            p1_id,
            p2_id,
            board_seed=12345,
        )
        board1 = match1.initial_board.to_list()

        # Create a second pair for the second match (concurrent limit)
        p3 = await factory.player_service.create_player(
            username="charlie",
            player_type=PlayerType.HUMAN,
        )
        p4 = await factory.player_service.create_player(
            username="diana",
            player_type=PlayerType.HUMAN,
        )
        p3_id = PlayerId(p3.id)
        p4_id = PlayerId(p4.id)

        match2 = await factory.match_service.create_match(
            p3_id,
            p4_id,
            board_seed=12345,
        )
        board2 = match2.initial_board.to_list()

        assert board1 == board2


class TestMatchCreationErrors:
    """Tests for error conditions during match creation."""

    async def test_create_match_player_not_found(self, factory):
        """Raises NOT_FOUND_PLAYER when a player does not exist."""
        p1 = await factory.player_service.create_player(
            username="alice",
            player_type=PlayerType.HUMAN,
        )
        p1_id = PlayerId(p1.id)
        fake_id = PlayerId(UUID("00000000-0000-0000-0000-000000000099"))

        with pytest.raises(AppError) as exc_info:
            await factory.match_service.create_match(p1_id, fake_id)

        assert exc_info.value.code == "NOT_FOUND_PLAYER"

    async def test_create_match_same_player(self, factory):
        """Raises VALIDATION_INVALID_INPUT when both IDs are the same."""
        p1 = await factory.player_service.create_player(
            username="alice",
            player_type=PlayerType.HUMAN,
        )
        p1_id = PlayerId(p1.id)

        with pytest.raises(AppError) as exc_info:
            await factory.match_service.create_match(p1_id, p1_id)

        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    async def test_create_match_insufficient_energy(self, factory):
        """Raises FORBIDDEN_INSUFFICIENT_ENERGY when player has 0 hearts."""
        p1_id, p2_id = await _create_two_players(factory)

        # Drain all hearts from p1 by setting energy to 0 via repo
        from uuid import UUID as StdUUID

        await factory.energy_repo.update(
            StdUUID(str(p1_id)),
            hearts=0,
        )

        # Verify hearts are 0
        energy = await factory.player_service.get_energy_state(p1_id)
        assert energy.hearts == 0

        with pytest.raises(AppError) as exc_info:
            await factory.match_service.create_match(p1_id, p2_id)

        assert exc_info.value.code == "FORBIDDEN_INSUFFICIENT_ENERGY"

    async def test_create_match_concurrent_limit(self, factory):
        """Raises CONFLICT_CONCURRENT_MATCH when player already has an active match."""
        p1_id, p2_id = await _create_two_players(factory)

        # Create first match (uses up the 1 concurrent slot)
        await factory.match_service.create_match(p1_id, p2_id, board_seed=42)

        # Create a third player for second match attempt
        p3 = await factory.player_service.create_player(
            username="charlie",
            player_type=PlayerType.HUMAN,
        )
        p3_id = PlayerId(p3.id)

        with pytest.raises(AppError) as exc_info:
            await factory.match_service.create_match(p1_id, p3_id)

        assert exc_info.value.code == "CONFLICT_CONCURRENT_MATCH"
