"""Unit tests for shared core types.

Verifies enum values, Position validation and adjacency, Move validation,
BoardState serialisation round-trips, and match/player type enums.
"""

from __future__ import annotations

import pytest

from src.core.types.game import GemType, Move, Position
from src.core.types.board import BoardState
from src.core.types.player import PlayerType
from src.core.types.match import MatchStatus


class TestGemType:
    """Tests for the GemType enum."""

    def test_gem_type_values(self) -> None:
        """Standard gem types have the expected integer values."""
        assert GemType.EMPTY == 0
        assert GemType.RED == 1
        assert GemType.BLUE == 2
        assert GemType.GREEN == 3
        assert GemType.YELLOW == 4
        assert GemType.PURPLE == 5
        assert GemType.ORANGE == 6

    def test_special_gem_negative_values(self) -> None:
        """Special gem types use negative integer values."""
        assert GemType.LINE_BLAST_H == -1
        assert GemType.LINE_BLAST_V == -2
        assert GemType.RADIAL_BOMB == -3
        assert GemType.CHROMATIC_ORB == -4

    def test_gem_type_int_conversion(self) -> None:
        """GemType values can be used as plain integers."""
        assert int(GemType.RED) == 1
        assert GemType.RED + GemType.BLUE == 3


class TestPosition:
    """Tests for the Position frozen dataclass."""

    def test_position_creation(self) -> None:
        """Valid positions are created successfully."""
        pos = Position(row=3, col=5)
        assert pos.row == 3
        assert pos.col == 5

    def test_position_non_negative(self) -> None:
        """Negative coordinates raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            Position(row=-1, col=0)

        with pytest.raises(ValueError, match="non-negative"):
            Position(row=0, col=-1)

    def test_position_adjacency(self) -> None:
        """Orthogonally adjacent positions are detected correctly."""
        origin = Position(0, 0)

        # Right
        assert origin.is_adjacent_to(Position(0, 1)) is True
        # Down
        assert origin.is_adjacent_to(Position(1, 0)) is True

    def test_position_not_adjacent_diagonal(self) -> None:
        """Diagonal positions are NOT adjacent."""
        origin = Position(0, 0)
        assert origin.is_adjacent_to(Position(1, 1)) is False

    def test_position_not_adjacent_distance(self) -> None:
        """Positions more than 1 step away are NOT adjacent."""
        origin = Position(0, 0)
        assert origin.is_adjacent_to(Position(0, 2)) is False
        assert origin.is_adjacent_to(Position(2, 0)) is False

    def test_position_not_adjacent_same(self) -> None:
        """A position is NOT adjacent to itself."""
        pos = Position(3, 3)
        assert pos.is_adjacent_to(Position(3, 3)) is False

    def test_position_frozen(self) -> None:
        """Position is immutable (frozen dataclass)."""
        pos = Position(1, 2)
        with pytest.raises(AttributeError):
            pos.row = 5  # type: ignore[misc]


class TestMove:
    """Tests for the Move frozen dataclass."""

    def test_move_requires_adjacent(self) -> None:
        """Move with non-adjacent positions raises ValueError."""
        with pytest.raises(ValueError, match="adjacent"):
            Move(
                from_pos=Position(0, 0),
                to_pos=Position(2, 2),
                timestamp_ms=1000,
            )

    def test_valid_move(self) -> None:
        """Move with adjacent positions is created successfully."""
        move = Move(
            from_pos=Position(3, 4),
            to_pos=Position(3, 5),
            timestamp_ms=1000,
        )
        assert move.from_pos.col == 4
        assert move.to_pos.col == 5

    def test_move_frozen(self) -> None:
        """Move is immutable (frozen dataclass)."""
        move = Move(
            from_pos=Position(0, 0),
            to_pos=Position(0, 1),
            timestamp_ms=100,
        )
        with pytest.raises(AttributeError):
            move.timestamp_ms = 200  # type: ignore[misc]


class TestBoardState:
    """Tests for the BoardState data class."""

    def test_board_state_from_list(self) -> None:
        """BoardState.from_list() creates a correct grid from nested lists."""
        data = [[1, 2], [3, 4]]
        board = BoardState.from_list(data)

        assert board.width == 2
        assert board.height == 2
        assert board.get(Position(0, 0)) == GemType.RED
        assert board.get(Position(0, 1)) == GemType.BLUE
        assert board.get(Position(1, 0)) == GemType.GREEN
        assert board.get(Position(1, 1)) == GemType.YELLOW

    def test_board_state_to_list(self) -> None:
        """Round-trip: from_list -> to_list returns the original data."""
        data = [[1, 2, 3], [4, 5, 6]]
        board = BoardState.from_list(data)
        result = board.to_list()

        assert result == data

    def test_board_state_copy(self) -> None:
        """copy() creates an independent snapshot."""
        original = BoardState.from_list([[1, 2], [3, 4]])
        copied = original.copy()

        # Mutate the copy's grid directly.
        copied.grid[0, 0] = 0

        # Original is unchanged.
        assert original.get(Position(0, 0)) == GemType.RED
        assert copied.get(Position(0, 0)) == GemType.EMPTY

    def test_board_state_dimensions(self) -> None:
        """Width and height are derived from the grid shape."""
        board = BoardState.from_list([[1, 2, 3, 4, 5, 6, 7, 0]] * 8)
        assert board.width == 8
        assert board.height == 8


class TestPlayerType:
    """Tests for the PlayerType enum."""

    def test_player_type_enum(self) -> None:
        """PlayerType values match the expected strings."""
        assert PlayerType.HUMAN.value == "human"
        assert PlayerType.BOT.value == "bot"

    def test_player_type_members(self) -> None:
        """PlayerType has exactly two members."""
        assert len(PlayerType) == 2


class TestMatchStatus:
    """Tests for the MatchStatus enum."""

    def test_match_status_enum(self) -> None:
        """MatchStatus values match the expected strings."""
        assert MatchStatus.PENDING.value == "pending"
        assert MatchStatus.IN_PROGRESS.value == "in_progress"
        assert MatchStatus.COMPLETED.value == "completed"
        assert MatchStatus.ABANDONED.value == "abandoned"

    def test_match_status_members(self) -> None:
        """MatchStatus has exactly four members."""
        assert len(MatchStatus) == 4
