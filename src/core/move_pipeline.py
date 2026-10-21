"""Shared board processing pipeline for moves and mega activations.

Both ``MoveProcessor`` (PvP) and ``CampaignService`` (campaign) delegate
here for: board move / mega processing, scoring with card modifiers, card
hooks (instant-win, energy grant), and deadlock detection + reshuffle.

All functions in this module are **CPU-bound pure functions** — callers wrap
them in ``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # All service types are duck-typed (protocol-based)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

# Linear Congruential Generator multiplier used to derive per-move seeds.
_LCG_MULTIPLIER = 1103515245

# Multiplier used to derive deterministic reshuffle seeds on deadlock.
_RESHUFFLE_MULTIPLIER = 12345


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class BoardProcessingResult:
    """Result from the shared processing pipeline."""

    move_result: object       # MoveProcessingResult
    result_board: object      # BoardState
    score_result: object      # ScoreResult | None
    points_earned: int
    reshuffled: bool
    instant_win: bool
    hearts_earned: int


# ---------------------------------------------------------------------------
# Seed derivation
# ---------------------------------------------------------------------------

def derive_move_seed(
    board_seed: int, player_id: object, moves_remaining: int
) -> int:
    """Derive a deterministic seed for move processing.

    Combines the board/match seed with player identity and move count
    to produce a unique, reproducible seed per move.
    """
    player_hash = hash(str(player_id)) & 0xFFFFFFFF
    return (
        board_seed ^ player_hash ^ (moves_remaining * _LCG_MULTIPLIER)
    ) & 0x7FFFFFFF


def derive_reshuffle_seed(
    board_seed: int, player_id: object, move_number: int
) -> int:
    """Derive a deterministic seed for deadlock reshuffle.

    Args:
        board_seed: The match/attempt board seed.
        player_id: The player whose board is deadlocked.
        move_number: 1-based move number (moves_made + 1).
    """
    player_hash = hash(str(player_id)) & 0xFFFFFFFF
    return (
        board_seed ^ player_hash ^ (move_number * _RESHUFFLE_MULTIPLIER)
    ) & 0x7FFFFFFF


# ---------------------------------------------------------------------------
# Move pipeline
# ---------------------------------------------------------------------------

def process_move_pipeline(
    board: object,
    move: object,
    seed: int,
    *,
    board_service: object,
    scoring_service: object,
    board_gen_service: object,
    board_seed: int,
    player_id: object,
    moves_made: int,
    moves_remaining: int,
    modifiers: object | None = None,
    deadlock_reshuffle: bool = True,
    enable_instant_win: bool = True,
) -> BoardProcessingResult:
    """Process a swap move: board cascade, scoring, card hooks, deadlock.

    Args:
        board: Current BoardState.
        move: The Move (swap coordinates).
        seed: Pre-derived via ``derive_move_seed``.
        board_service: BoardServiceProtocol — ``process_move``, ``has_valid_moves``.
        scoring_service: ScoringServiceProtocol — ``calculate_move_score``.
        board_gen_service: BoardGenServiceProtocol — ``regenerate_from_deadlock``.
        board_seed: Raw board/match seed (for reshuffle seed derivation).
        player_id: Player making the move.
        moves_made: Number of moves already made (for reshuffle seed).
        moves_remaining: Moves remaining *before* this move.
        modifiers: Card modifier engine (optional).
        deadlock_reshuffle: Whether to reshuffle on deadlock.
        enable_instant_win: Whether Hook 7 (Lucky Rabbit) is active.
            Set ``False`` for campaign mode.
    """
    # 1. Process move through board service.
    move_result = board_service.process_move(
        board, move, seed, modifiers=modifiers
    )

    if not move_result.was_valid_match:
        return BoardProcessingResult(
            move_result=move_result,
            result_board=board,
            score_result=None,
            points_earned=0,
            reshuffled=False,
            instant_win=False,
            hearts_earned=0,
        )

    result_board = move_result.final_board

    # 2–5. Scoring, hooks, deadlock (shared with mega).
    return _score_and_finalize(
        move_result,
        result_board,
        board_service=board_service,
        scoring_service=scoring_service,
        board_gen_service=board_gen_service,
        board_seed=board_seed,
        player_id=player_id,
        moves_made=moves_made,
        moves_remaining=moves_remaining,
        modifiers=modifiers,
        deadlock_reshuffle=deadlock_reshuffle,
        enable_instant_win=enable_instant_win,
    )


# ---------------------------------------------------------------------------
# Mega pipeline
# ---------------------------------------------------------------------------

def process_mega_pipeline(
    board: object,
    mega_value: int,
    seed: int,
    *,
    board_service: object,
    scoring_service: object,
    board_gen_service: object,
    board_seed: int,
    player_id: object,
    moves_made: int,
    moves_remaining: int,
    modifiers: object | None = None,
    deadlock_reshuffle: bool = True,
    enable_instant_win: bool = True,
) -> BoardProcessingResult:
    """Process a mega gem activation: place + cascade, scoring, hooks, deadlock.

    Args:
        board: Current BoardState.
        mega_value: Mega gem value (e.g. 11, 22, 33, 44).
        seed: Pre-derived seed (includes slot + score XOR for uniqueness).
        board_service: BoardServiceProtocol — ``process_mega_activation``,
            ``has_valid_moves``.
        scoring_service: ScoringServiceProtocol.
        board_gen_service: BoardGenServiceProtocol.
        board_seed: Raw board/match seed (for reshuffle seed derivation).
        player_id: Player activating the mega gem.
        moves_made: Number of moves already made.
        moves_remaining: Moves remaining (megas don't consume moves).
        modifiers: Card modifier engine (optional).
        deadlock_reshuffle: Whether to reshuffle on deadlock.
        enable_instant_win: Whether Hook 7 (Lucky Rabbit) is active.
            Set ``False`` for campaign mode.
    """
    move_result = board_service.process_mega_activation(
        board, mega_value, seed, modifiers=modifiers
    )
    result_board = move_result.final_board

    return _score_and_finalize(
        move_result,
        result_board,
        board_service=board_service,
        scoring_service=scoring_service,
        board_gen_service=board_gen_service,
        board_seed=board_seed,
        player_id=player_id,
        moves_made=moves_made,
        moves_remaining=moves_remaining,
        modifiers=modifiers,
        deadlock_reshuffle=deadlock_reshuffle,
        enable_instant_win=enable_instant_win,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _score_and_finalize(
    move_result: object,
    result_board: object,
    *,
    board_service: object,
    scoring_service: object,
    board_gen_service: object,
    board_seed: int,
    player_id: object,
    moves_made: int,
    moves_remaining: int,
    modifiers: object | None,
    deadlock_reshuffle: bool,
    enable_instant_win: bool,
) -> BoardProcessingResult:
    """Score a move result, run card hooks, handle deadlock.

    Shared tail logic for both move and mega pipelines.
    """
    # Hook 6: extract score modifiers from card system.
    score_modifiers = None
    if modifiers is not None and not modifiers.is_empty:
        score_modifiers, _ = modifiers.get_score_modifiers()

    score_result = scoring_service.calculate_move_score(
        move_result, score_modifiers=score_modifiers
    )
    points_earned = score_result.total_points

    # Hook 7: instant win condition (Lucky Rabbit O+O).
    # Disabled in campaign mode (enable_instant_win=False) to prevent
    # players cheesing levels.
    instant_win = False
    if enable_instant_win and modifiers is not None and not modifiers.is_empty:
        instant_win, win_mods = modifiers.check_win_condition(
            move_result.cascades
        )
        if win_mods:
            move_result.applied_modifiers.extend(win_mods)

    # Hook 8: energy grant (Heart of Fire).
    hearts_earned = 0
    if modifiers is not None and not modifiers.is_empty:
        hearts_earned, energy_mods = modifiers.check_energy_grant(
            move_result.chain_count
        )
        if energy_mods:
            move_result.applied_modifiers.extend(energy_mods)

    # Deadlock detection and reshuffle.
    result_board, reshuffled = _handle_deadlock(
        result_board,
        board_seed,
        player_id,
        moves_made,
        moves_remaining,
        board_service,
        board_gen_service,
        deadlock_reshuffle,
    )

    return BoardProcessingResult(
        move_result=move_result,
        result_board=result_board,
        score_result=score_result,
        points_earned=points_earned,
        reshuffled=reshuffled,
        instant_win=instant_win,
        hearts_earned=hearts_earned,
    )


def _handle_deadlock(
    result_board: object,
    board_seed: int,
    player_id: object,
    moves_made: int,
    moves_remaining: int,
    board_service: object,
    board_gen_service: object,
    deadlock_reshuffle: bool,
) -> tuple:
    """Check for deadlock and reshuffle if needed.

    Uses ``BoardGenService.regenerate_from_deadlock`` which preserves
    special gem positions (unlike the retired ``shuffle_board`` approach).

    Returns:
        ``(result_board, reshuffled)`` tuple.
    """
    has_valid = board_service.has_valid_moves(result_board)
    if has_valid or not deadlock_reshuffle or (moves_remaining - 1) <= 0:
        return result_board, False

    move_number = moves_made + 1
    reshuffle_seed = derive_reshuffle_seed(
        board_seed, player_id, move_number
    )
    reshuffle_result = board_gen_service.regenerate_from_deadlock(
        result_board, reshuffle_seed
    )
    return reshuffle_result.board_state, True
