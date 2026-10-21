"""Bot hint generator for match state responses.

This is presentation-layer logic -- it operates on data already fetched
from the match and board services. It does NOT perform business logic;
it merely analyses the board state and ranks moves for bot consumption.

Bot hints are only included when:
1. The request is authenticated via API key (not JWT).
2. The endpoint returns match state data.
3. The ``api.bot_hints_enabled`` config flag is true.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# -- Lightweight hint data classes (presentation-only) ---------------------


@dataclass(frozen=True)
class ValidMoveHint:
    """A valid move on the board with estimated score."""

    from_row: int
    from_col: int
    to_row: int
    to_col: int
    estimated_score: int


@dataclass(frozen=True)
class RankedMove:
    """A move ranked by expected value."""

    move: ValidMoveHint
    expected_score: int
    cascade_potential: Literal["low", "medium", "high"]
    special_gem_chance: float  # 0.0 - 1.0


@dataclass(frozen=True)
class BoardAnalysis:
    """Analysis of the current board state."""

    gem_distribution: dict[str, int]
    special_gems_available: int
    chain_opportunities: int
    board_volatility: Literal["stable", "moderate", "volatile"]


@dataclass(frozen=True)
class StrategicContext:
    """Strategic situation analysis for a match."""

    score_differential: int
    recommended_strategy: Literal["aggressive", "defensive", "balanced"]
    risk_tolerance: Literal["low", "medium", "high"]
    game_phase: Literal["early", "mid", "late"]


@dataclass(frozen=True)
class MatchBotHints:
    """Complete bot hints for a match state response."""

    best_moves: list[RankedMove]
    board_analysis: BoardAnalysis
    strategic_context: StrategicContext


# -- Thresholds -----------------------------------------------------------

_CHAIN_HIGH_THRESHOLD = 20
_CHAIN_MODERATE_THRESHOLD = 10
_TOP_MOVES_COUNT = 5
_LATE_GAME_THRESHOLD = 5
_MID_GAME_THRESHOLD = 20
_LARGE_DEFICIT_THRESHOLD = -100
_LARGE_LEAD_THRESHOLD = 100
_SPECIAL_GEM_NEGATIVE_THRESHOLD = 0


class BotHintGenerator:
    """Generates strategic hints for bot players.

    All methods are synchronous -- hint generation is a pure computation
    over data already retrieved from services.
    """

    def generate_match_hints(
        self,
        board: list[list[int]],
        valid_moves: list[ValidMoveHint],
        my_score: int,
        opponent_score: int,
        turns_remaining: int | None,
    ) -> MatchBotHints:
        """Generate hints for the current match state.

        Args:
            board: 2-D grid of gem type integers (8x8).
            valid_moves: All legal moves with minimum estimated scores.
            my_score: Requesting player's current score.
            opponent_score: Opponent's current score.
            turns_remaining: Moves left, or None if time-based.

        Returns:
            MatchBotHints with ranked moves, board analysis, and strategy.
        """
        board_analysis = self._analyze_board(board)
        ranked_moves = self._rank_moves(board, valid_moves)
        strategic_context = self._determine_strategy(
            my_score,
            opponent_score,
            turns_remaining,
            board_analysis,
        )

        return MatchBotHints(
            best_moves=ranked_moves[:_TOP_MOVES_COUNT],
            board_analysis=board_analysis,
            strategic_context=strategic_context,
        )

    # -- Private helpers --------------------------------------------------

    def _analyze_board(self, board: list[list[int]]) -> BoardAnalysis:
        """Analyse the board for gem distribution and chain opportunities."""
        gem_counts: dict[str, int] = {}
        special_count = 0

        for row in board:
            for gem in row:
                key = str(gem)
                gem_counts[key] = gem_counts.get(key, 0) + 1
                if gem < _SPECIAL_GEM_NEGATIVE_THRESHOLD:
                    special_count += 1

        chain_opportunities = self._count_chain_opportunities(board)

        if chain_opportunities > _CHAIN_HIGH_THRESHOLD:
            volatility: Literal["stable", "moderate", "volatile"] = "volatile"
        elif chain_opportunities > _CHAIN_MODERATE_THRESHOLD:
            volatility = "moderate"
        else:
            volatility = "stable"

        return BoardAnalysis(
            gem_distribution=gem_counts,
            special_gems_available=special_count,
            chain_opportunities=chain_opportunities,
            board_volatility=volatility,
        )

    def _count_chain_opportunities(self, board: list[list[int]]) -> int:
        """Count adjacent same-colour pairs as a proxy for chain potential."""
        count = 0
        rows = len(board)
        cols = len(board[0]) if rows > 0 else 0

        for r in range(rows):
            for c in range(cols):
                # Horizontal pair
                if c < cols - 1 and board[r][c] == board[r][c + 1]:
                    count += 1
                # Vertical pair
                if r < rows - 1 and board[r][c] == board[r + 1][c]:
                    count += 1

        return count

    def _rank_moves(
        self,
        board: list[list[int]],
        valid_moves: list[ValidMoveHint],
    ) -> list[RankedMove]:
        """Rank valid moves by expected value using lightweight heuristics."""
        ranked: list[RankedMove] = []
        cascade_bonus_factor = 10

        for move in valid_moves:
            cascade_potential = self._estimate_cascade(board, move)

            if cascade_potential > 2:
                cascade_label: Literal["low", "medium", "high"] = "high"
            elif cascade_potential > 0:
                cascade_label = "medium"
            else:
                cascade_label = "low"

            expected = move.estimated_score + (cascade_potential * cascade_bonus_factor)
            special_chance = min(0.3 * cascade_potential, 1.0)

            ranked.append(
                RankedMove(
                    move=move,
                    expected_score=expected,
                    cascade_potential=cascade_label,
                    special_gem_chance=round(special_chance, 2),
                )
            )

        ranked.sort(key=lambda r: r.expected_score, reverse=True)
        return ranked

    def _estimate_cascade(
        self,
        board: list[list[int]],
        move: ValidMoveHint,
    ) -> int:
        """Estimate cascade potential for a move via adjacent-match counting.

        This is a lightweight heuristic -- it counts how many same-colour
        neighbours surround the destination cells after a conceptual swap.
        """
        rows = len(board)
        cols = len(board[0]) if rows > 0 else 0

        fr, fc = move.from_row, move.from_col
        tr, tc = move.to_row, move.to_col

        # Conceptual swap
        from_gem = board[fr][fc]
        to_gem = board[tr][tc]

        score = 0

        # Check neighbours of 'to' position (which will hold from_gem)
        score += self._count_aligned(board, tr, tc, from_gem, rows, cols, fr, fc)
        # Check neighbours of 'from' position (which will hold to_gem)
        score += self._count_aligned(board, fr, fc, to_gem, rows, cols, tr, tc)

        return score

    @staticmethod
    def _count_aligned(
        board: list[list[int]],
        row: int,
        col: int,
        gem: int,
        rows: int,
        cols: int,
        exclude_row: int,
        exclude_col: int,
    ) -> int:
        """Count same-colour neighbours around a position (excluding the swap partner)."""
        count = 0
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = row + dr, col + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if (nr, nc) != (exclude_row, exclude_col) and board[nr][nc] == gem:
                    count += 1
        return count

    @staticmethod
    def find_valid_moves(board: list[list[int]]) -> list[ValidMoveHint]:
        """Scan the board for all adjacent swaps that produce a match of 3+.

        Checks every horizontal and vertical adjacent pair. After a
        conceptual swap, scans for runs of 3+ along rows and columns.
        Returns ValidMoveHint list with estimated_score = matched_count * 50.
        """
        rows = len(board)
        cols = len(board[0]) if rows > 0 else 0
        moves: list[ValidMoveHint] = []
        seen: set[tuple[int, int, int, int]] = set()

        def _has_match(b: list[list[int]], r: int, c: int) -> int:
            """Count gems matched by runs through (r, c) after swap."""
            gem = b[r][c]
            if gem == 0:
                return 0
            total = 0
            # Horizontal run through (r, c).
            count = 1
            for dc in (1, -1):
                nc = c + dc
                while 0 <= nc < cols and b[r][nc] == gem:
                    count += 1
                    nc += dc
            if count >= 3:
                total += count
            # Vertical run through (r, c).
            count = 1
            for dr in (1, -1):
                nr = r + dr
                while 0 <= nr < rows and b[nr][c] == gem:
                    count += 1
                    nr += dr
            if count >= 3:
                total += count
            return total

        directions = [(0, 1), (1, 0)]  # right, down
        for r in range(rows):
            for c in range(cols):
                for dr, dc in directions:
                    nr, nc = r + dr, c + dc
                    if nr >= rows or nc >= cols:
                        continue
                    key = (r, c, nr, nc)
                    if key in seen:
                        continue
                    seen.add(key)
                    seen.add((nr, nc, r, c))

                    # Conceptual swap.
                    board[r][c], board[nr][nc] = board[nr][nc], board[r][c]
                    matched = _has_match(board, r, c) + _has_match(board, nr, nc)
                    # Undo swap.
                    board[r][c], board[nr][nc] = board[nr][nc], board[r][c]

                    if matched > 0:
                        moves.append(
                            ValidMoveHint(
                                from_row=r,
                                from_col=c,
                                to_row=nr,
                                to_col=nc,
                                estimated_score=matched * 50,
                            )
                        )
        return moves

    def _determine_strategy(
        self,
        my_score: int,
        opponent_score: int,
        turns_remaining: int | None,
        analysis: BoardAnalysis,
    ) -> StrategicContext:
        """Determine the recommended strategic posture."""
        diff = my_score - opponent_score

        # Game phase
        if turns_remaining is None:
            phase: Literal["early", "mid", "late"] = "mid"
        elif turns_remaining > _MID_GAME_THRESHOLD:
            phase = "early"
        elif turns_remaining > _LATE_GAME_THRESHOLD:
            phase = "mid"
        else:
            phase = "late"

        # Strategy based on score differential and game phase
        if diff < _LARGE_DEFICIT_THRESHOLD and phase == "late":
            strategy: Literal["aggressive", "defensive", "balanced"] = "aggressive"
            risk: Literal["low", "medium", "high"] = "high"
        elif diff > _LARGE_LEAD_THRESHOLD:
            strategy = "defensive"
            risk = "low"
        else:
            strategy = "balanced"
            risk = "medium"

        return StrategicContext(
            score_differential=diff,
            recommended_strategy=strategy,
            risk_tolerance=risk,
            game_phase=phase,
        )
