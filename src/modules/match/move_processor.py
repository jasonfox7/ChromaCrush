"""Move processing pipeline for match module.

Encapsulates the full move submission flow: precondition validation,
board processing, deadlock handling, score calculation, move persistence,
and match completion checks. Delegated to by ``MatchService.submit_move``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from src.core.move_pipeline import (
    BoardProcessingResult,
    derive_move_seed,
    process_mega_pipeline,
    process_move_pipeline,
)
from src.core.types.board import BoardState
from src.core.types.game import MatchId, Move, PlayerId
from src.modules.match.dto import MatchUpdate, MoveCreate
from src.modules.match.types import (
    MatchStatus,
    MoveSubmissionResult,
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.board_gen.protocols import BoardGenServiceProtocol
    from src.modules.match.match_finalizer import MatchFinalizer
    from src.modules.match.protocols import (
        BoardServiceProtocol,
        ScoringServiceProtocol,
    )
    from src.modules.match.service import MatchRepositoryBundle
    from src.modules.player.protocols import PlayerServiceProtocol

class MoveProcessor:
    """Processes move submissions for active matches.

    Handles the full pipeline: precondition validation, board move
    processing, deadlock detection/reshuffle, scoring, move record
    persistence, and match completion checks.

    Created by ``MatchService.__init__`` and called via delegation.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        board_service: BoardServiceProtocol,
        scoring_service: ScoringServiceProtocol,
        board_gen_service: BoardGenServiceProtocol,
        repos: MatchRepositoryBundle,
        finalizer: MatchFinalizer,
        *,
        card_service: object | None = None,
        energy_service: object | None = None,
        player_service: PlayerServiceProtocol | None = None,
        debug_logger: object | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._board_service = board_service
        self._scoring_service = scoring_service
        self._board_gen_service = board_gen_service
        self._match_repo = repos.match_repository
        self._move_repo = repos.match_move_repository
        self._finalizer = finalizer
        self._card_service = card_service
        self._energy_service = energy_service
        self._player_service = player_service
        self._debug = debug_logger

        # Cache configuration values.
        self._deadlock_reshuffle: bool = config.get("match.deadlock_reshuffle", True)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def submit_move(
        self,
        match_id: MatchId,
        player_id: PlayerId,
        move: Move,
    ) -> tuple[MoveSubmissionResult, object]:
        """Submit a move for a player in an active match.

        Processes the move through board, special gems, and scoring
        services. Persists move history, updates match state, and
        handles match completion.

        Called by ``MatchService.submit_move`` which fills in the
        ``match_state`` field and builds the final result.

        Args:
            match_id: The match.
            player_id: Who is making the move.
            move: The swap to perform.

        Returns:
            Tuple of (partial MoveSubmissionResult with match_state=None,
            updated match DB record).

        Raises:
            AppError: NOT_FOUND_MATCH if match doesn't exist.
            AppError: FORBIDDEN_NOT_MATCH_PARTICIPANT if player not in match.
            AppError: CONFLICT_MATCH_ALREADY_COMPLETED if finished/abandoned.
            AppError: CONFLICT_MATCH_NOT_IN_PROGRESS for wrong status on non-pending.
            AppError: VALIDATION_NO_MOVES_REMAINING if out of moves.
            AppError: VALIDATION_INVALID_GEM_SWAP if move is invalid.
        """
        # 1. Validate preconditions and extract player context.
        ctx = await self._validate_move_preconditions(match_id, player_id)
        match_record = ctx["match_record"]
        is_player1 = ctx["is_player1"]
        moves_remaining = ctx["moves_remaining"]
        current_score = ctx["current_score"]
        moves_made = ctx["moves_made"]
        longest_chain = ctx["longest_chain"]
        current_board_data = ctx["current_board_data"]
        status = ctx["status"]

        # 2a. Build card modifier engine for this player's equipped cards.
        # Skip modifier building for bot players — bots own cards cosmetically
        # but their effects don't apply during gameplay.
        modifiers = None
        if self._card_service is not None:
            try:
                is_bot = False
                if self._player_service is not None:
                    player = await self._player_service.get_player(player_id)
                    is_bot = player.is_bot
                if not is_bot:
                    modifiers = await self._card_service.build_modifier_engine(
                        player_id
                    )
            except Exception:
                pass  # If card/player lookup fails, proceed without modifiers

        # 2-4. CPU-bound: board processing, scoring, deadlock — run off event loop.
        current_board = BoardState.from_list(current_board_data)

        # Debug logging before processing.
        if self._debug:
            try:
                self._debug.log_board_loaded_from_db(
                    board_cells=current_board.grid.tolist(),
                    match_id=str(match_id),
                    player_id=str(player_id),
                    source="db_before_process_move",
                )
                self._debug.log_move_attempt(
                    match_id=str(match_id),
                    player_id=str(player_id),
                    from_row=move.from_pos.row,
                    from_col=move.from_pos.col,
                    to_row=move.to_pos.row,
                    to_col=move.to_pos.col,
                    board_before=current_board.grid.tolist(),
                )
            except Exception:
                pass

        move_seed = derive_move_seed(
            match_record.board_seed,  # type: ignore[attr-defined]
            player_id,
            moves_remaining,
        )
        pipeline_result: BoardProcessingResult = await asyncio.to_thread(
            process_move_pipeline,
            current_board,
            move,
            move_seed,
            board_service=self._board_service,
            scoring_service=self._scoring_service,
            board_gen_service=self._board_gen_service,
            board_seed=match_record.board_seed,  # type: ignore[attr-defined]
            player_id=player_id,
            moves_made=moves_made,
            moves_remaining=moves_remaining,
            modifiers=modifiers,
            deadlock_reshuffle=self._deadlock_reshuffle,
            enable_instant_win=True,
        )

        # Pipeline returns early on invalid move (was_valid_match=False).
        if not pipeline_result.move_result.was_valid_match:
            if self._debug:
                try:
                    self._debug.log_move_result(
                        valid=False,
                        chain_count=0,
                        total_cleared=0,
                        board_after=None,
                        match_id=str(match_id),
                        player_id=str(player_id),
                        error=f"VALIDATION_INVALID_GEM_SWAP: ({move.from_pos.row},{move.from_pos.col})->({move.to_pos.row},{move.to_pos.col})",
                    )
                except Exception:
                    pass
            raise self._errors.validation(
                "Invalid gem swap: no matches created",
                code="VALIDATION_INVALID_GEM_SWAP",
                match_id=str(match_id),
                player_id=str(player_id),
                from_pos=f"({move.from_pos.row},{move.from_pos.col})",
                to_pos=f"({move.to_pos.row},{move.to_pos.col})",
            )

        move_result = pipeline_result.move_result
        result_board = pipeline_result.result_board
        score_result = pipeline_result.score_result
        points_earned = pipeline_result.points_earned
        reshuffled = pipeline_result.reshuffled
        instant_win = pipeline_result.instant_win
        hearts_earned = pipeline_result.hearts_earned

        # Hook 8: Grant bonus hearts from energy cards (async, after thread).
        if hearts_earned > 0 and self._energy_service is not None:
            try:
                await self._energy_service.grant_bonus_hearts(
                    UUID(str(player_id)), hearts_earned
                )
            except Exception:
                pass  # Energy grant failure must not crash move processing

        # Legacy placeholder — special_effects pipeline not yet wired.
        special_effects: list = []

        # 5. Build MatchUpdate with updated player state.
        new_moves_remaining = moves_remaining - 1
        new_moves_made = moves_made + 1
        new_score = current_score + points_earned
        new_chain = max(longest_chain, move_result.chain_count)
        now = datetime.now(timezone.utc)

        update = MatchUpdate()
        if is_player1:
            update.player1_board_state = result_board.to_dict()
            update.player1_score = new_score
            update.player1_moves_made = new_moves_made
            update.player1_moves_remaining = new_moves_remaining
            update.player1_longest_chain = new_chain
            if new_moves_remaining == 0:
                update.player1_finished_at = now
        else:
            update.player2_board_state = result_board.to_dict()
            update.player2_score = new_score
            update.player2_moves_made = new_moves_made
            update.player2_moves_remaining = new_moves_remaining
            update.player2_longest_chain = new_chain
            if new_moves_remaining == 0:
                update.player2_finished_at = now

        # Debug: log the board being saved to DB after valid move
        if self._debug:
            try:
                self._debug.log_move_result(
                    valid=True,
                    chain_count=move_result.chain_count,
                    total_cleared=move_result.total_gems_cleared,
                    board_after=result_board.to_list(),
                    match_id=str(match_id),
                    player_id=str(player_id),
                )
                self._debug.log_board_state(
                    "saving_to_db",
                    result_board.to_list(),
                    match_id=str(match_id),
                    player_id=str(player_id),
                )
            except Exception:
                pass  # Debug logging must never crash move processing

        # 6. Transition PENDING -> IN_PROGRESS on first move.
        if status == MatchStatus.PENDING:
            update.status = MatchStatus.IN_PROGRESS.value
            update.started_at = now

        # 7. Persist move record.
        move_number = new_moves_made
        special_gems_created_json = [
            {"row": pos.row, "col": pos.col, "gem_type": int(gt)}
            for pos, gt in move_result.special_gems_created
        ]
        special_gems_activated_json = [
            {"row": eff.source_position.row, "col": eff.source_position.col}
            for eff in special_effects
        ]
        move_create = MoveCreate(
            match_id=UUID(str(match_id)),
            player_id=UUID(str(player_id)),
            move_number=move_number,
            from_row=move.from_pos.row,
            from_col=move.from_pos.col,
            to_row=move.to_pos.row,
            to_col=move.to_pos.col,
            client_timestamp_ms=move.timestamp_ms,
            board_before=current_board.to_list(),
            board_after=result_board.to_list(),
            score_earned=points_earned,
            chain_count=move_result.chain_count,
            gems_cleared=move_result.total_gems_cleared,
            special_gems_created=special_gems_created_json,
            special_gems_activated=special_gems_activated_json,
        )
        await self._move_repo.create(move_create)

        # 8. Check completion, finalize if both players done.
        #    Hook 7: instant_win from Lucky Rabbit overrides normal completion.
        if instant_win:
            match_completed = True
            winner_id = player_id
            update.status = MatchStatus.COMPLETED.value
            update.completed_at = now
            update.winner_id = UUID(str(player_id))
            p1_id = PlayerId(match_record.player1_id)  # type: ignore[attr-defined]
            p2_id = PlayerId(match_record.player2_id)  # type: ignore[attr-defined]
            p1_s = new_score if is_player1 else match_record.player1_score  # type: ignore[attr-defined]
            p2_s = match_record.player2_score if is_player1 else new_score  # type: ignore[attr-defined]
            raid_result, reward_result = await self._finalizer.finalize_match(
                p1_id, p2_id, p1_s, p2_s, winner_id,
            )
            # Persist raid/reward on match record (same as _check_and_finalize).
            if raid_result.occurred:
                update.raid_data = {
                    "occurred": raid_result.occurred,
                    "stolen_card_id": raid_result.stolen_card_id,
                    "stolen_card_name": raid_result.stolen_card_name,
                    "was_shielded": raid_result.was_shielded,
                    "card_unequipped": raid_result.card_unequipped,
                    "blocked_by_card": raid_result.blocked_by_card,
                    "blocked_by_card_name": raid_result.blocked_by_card_name,
                }
            if reward_result.awarded:
                update.reward_data = {
                    "awarded": reward_result.awarded,
                    "cards": reward_result.cards,
                    "tier": reward_result.tier,
                }
        else:
            match_completed, winner_id, raid_result, reward_result = (
                await self._check_and_finalize(
                    match_record,
                    update,
                    is_player1,
                    new_moves_remaining,
                    new_score,
                    new_chain,
                    move_result,
                    now,
                )
            )

        # 9. Persist match update and return result.
        updated_record = await self._match_repo.update(
            UUID(str(match_id)),
            update,
        )

        self._logger.info(
            "match.move_submitted",
            match_id=str(match_id),
            player_id=str(player_id),
            move_number=move_number,
            points_earned=points_earned,
            moves_remaining=new_moves_remaining,
            chain_count=move_result.chain_count,
            match_completed=match_completed,
            reshuffled=reshuffled,
        )

        return (
            MoveSubmissionResult(
                match_state=None,  # Caller fills this in
                move_result=move_result,
                score_result=score_result,
                special_effects=special_effects,
                points_earned=points_earned,
                move_number=move_number,
                moves_remaining=new_moves_remaining,
                match_completed=match_completed,
                player_finished=new_moves_remaining == 0,
                winner_id=winner_id,
                raid_result=raid_result,
                reward_result=reward_result,
            ),
            updated_record,
        )

    # ------------------------------------------------------------------
    # Mega activation entry point
    # ------------------------------------------------------------------

    async def process_mega_activation(
        self,
        match_id: MatchId,
        player_id: PlayerId,
        slot_index: int,
        mega_value: int,
    ) -> tuple[MoveSubmissionResult, object]:
        """Process a mega gem activation (does not consume a move).

        Places a banked mega gem on the board, fires it, cascades, and
        scores the result. Moves remaining and moves made are NOT updated.

        Args:
            match_id: The match.
            player_id: Who is activating the mega gem.
            slot_index: Inventory slot index (0-3).
            mega_value: Mega gem value to place (14, 24, 34, or 44).

        Returns:
            Tuple of (partial MoveSubmissionResult with match_state=None,
            updated match DB record).
        """
        # 1. Validate preconditions (match exists, player is participant, etc.).
        ctx = await self._validate_move_preconditions(match_id, player_id)
        match_record = ctx["match_record"]
        is_player1 = ctx["is_player1"]
        moves_remaining = ctx["moves_remaining"]
        current_score = ctx["current_score"]
        moves_made = ctx["moves_made"]
        longest_chain = ctx["longest_chain"]
        current_board_data = ctx["current_board_data"]
        status = ctx["status"]

        # 2. Build card modifier engine (skip for bots).
        modifiers = None
        if self._card_service is not None:
            try:
                is_bot = False
                if self._player_service is not None:
                    player = await self._player_service.get_player(player_id)
                    is_bot = player.is_bot
                if not is_bot:
                    modifiers = await self._card_service.build_modifier_engine(
                        player_id
                    )
            except Exception:
                pass

        # 3. Derive seed — XOR with slot_index and current_score so each
        #    mega activation lands on a different cell (moves_remaining is
        #    constant for megas, but score always differs).
        derived_seed = (
            derive_move_seed(
                match_record.board_seed,  # type: ignore[attr-defined]
                player_id,
                moves_remaining,
            )
            ^ (slot_index * 7919)
            ^ (current_score * 104729)
        )

        # 4. Run in thread: board processing is CPU-bound.
        current_board = BoardState.from_list(current_board_data)
        pipeline_result: BoardProcessingResult = await asyncio.to_thread(
            process_mega_pipeline,
            current_board,
            mega_value,
            derived_seed,
            board_service=self._board_service,
            scoring_service=self._scoring_service,
            board_gen_service=self._board_gen_service,
            board_seed=match_record.board_seed,  # type: ignore[attr-defined]
            player_id=player_id,
            moves_made=moves_made,
            moves_remaining=moves_remaining,
            modifiers=modifiers,
            deadlock_reshuffle=self._deadlock_reshuffle,
            enable_instant_win=True,
        )

        move_result = pipeline_result.move_result
        result_board = pipeline_result.result_board
        score_result = pipeline_result.score_result
        points_earned = pipeline_result.points_earned
        reshuffled = pipeline_result.reshuffled
        instant_win = pipeline_result.instant_win
        hearts_earned = pipeline_result.hearts_earned

        # Hook 8: Grant bonus hearts from energy cards (async, after thread).
        if hearts_earned > 0 and self._energy_service is not None:
            try:
                await self._energy_service.grant_bonus_hearts(
                    UUID(str(player_id)), hearts_earned
                )
            except Exception:
                pass  # Energy grant failure must not crash move processing

        # 5. Build MatchUpdate — update board + score.
        #    Increment moves_made (for unique move_number tracking) but
        #    do NOT decrement moves_remaining (the move is "refunded").
        new_moves_made = moves_made + 1
        new_score = current_score + points_earned
        new_chain = max(longest_chain, move_result.chain_count)
        now = datetime.now(timezone.utc)

        update = MatchUpdate()
        if is_player1:
            update.player1_board_state = result_board.to_dict()
            update.player1_score = new_score
            update.player1_longest_chain = new_chain
            update.player1_moves_made = new_moves_made
        else:
            update.player2_board_state = result_board.to_dict()
            update.player2_score = new_score
            update.player2_longest_chain = new_chain
            update.player2_moves_made = new_moves_made

        # 6. Transition PENDING -> IN_PROGRESS on first action.
        if status == MatchStatus.PENDING:
            update.status = MatchStatus.IN_PROGRESS.value
            update.started_at = now

        # 7. Persist move record (from_row/to_row = -1 to indicate mega activation).
        move_number = moves_made + 1
        special_gems_created_json = [
            {"row": pos.row, "col": pos.col, "gem_type": int(gt)}
            for pos, gt in move_result.special_gems_created
        ]
        move_create = MoveCreate(
            match_id=UUID(str(match_id)),
            player_id=UUID(str(player_id)),
            move_number=move_number,
            from_row=-1,
            from_col=slot_index,
            to_row=-1,
            to_col=mega_value,
            client_timestamp_ms=0,
            board_before=current_board.to_list(),
            board_after=result_board.to_list(),
            score_earned=points_earned,
            chain_count=move_result.chain_count,
            gems_cleared=move_result.total_gems_cleared,
            special_gems_created=special_gems_created_json,
            special_gems_activated=[],
        )
        await self._move_repo.create(move_create)

        # 8. Check completion (mega doesn't consume moves, but check anyway).
        #    Hook 7: instant_win from Lucky Rabbit overrides normal completion.
        if instant_win:
            match_completed = True
            winner_id = player_id
            update.status = MatchStatus.COMPLETED.value
            update.completed_at = now
            update.winner_id = UUID(str(player_id))
            p1_id = PlayerId(match_record.player1_id)  # type: ignore[attr-defined]
            p2_id = PlayerId(match_record.player2_id)  # type: ignore[attr-defined]
            p1_s = new_score if is_player1 else match_record.player1_score  # type: ignore[attr-defined]
            p2_s = match_record.player2_score if is_player1 else new_score  # type: ignore[attr-defined]
            raid_result, reward_result = await self._finalizer.finalize_match(
                p1_id, p2_id, p1_s, p2_s, winner_id,
            )
            # Persist raid/reward on match record (same as _check_and_finalize).
            if raid_result.occurred:
                update.raid_data = {
                    "occurred": raid_result.occurred,
                    "stolen_card_id": raid_result.stolen_card_id,
                    "stolen_card_name": raid_result.stolen_card_name,
                    "was_shielded": raid_result.was_shielded,
                    "card_unequipped": raid_result.card_unequipped,
                    "blocked_by_card": raid_result.blocked_by_card,
                    "blocked_by_card_name": raid_result.blocked_by_card_name,
                }
            if reward_result.awarded:
                update.reward_data = {
                    "awarded": reward_result.awarded,
                    "cards": reward_result.cards,
                    "tier": reward_result.tier,
                }
        else:
            match_completed, winner_id, raid_result, reward_result = (
                await self._check_and_finalize(
                    match_record,
                    update,
                    is_player1,
                    moves_remaining,
                    new_score,
                    new_chain,
                    move_result,
                    now,
                )
            )

        # 9. Persist match update and return result.
        updated_record = await self._match_repo.update(
            UUID(str(match_id)),
            update,
        )

        self._logger.info(
            "match.mega_activation",
            match_id=str(match_id),
            player_id=str(player_id),
            slot_index=slot_index,
            mega_value=mega_value,
            points_earned=points_earned,
            chain_count=move_result.chain_count,
        )

        return (
            MoveSubmissionResult(
                match_state=None,  # Caller fills this in
                move_result=move_result,
                score_result=score_result,
                special_effects=[],
                points_earned=points_earned,
                move_number=move_number,
                moves_remaining=moves_remaining,  # Not decremented
                match_completed=match_completed,
                player_finished=moves_remaining == 0,
                winner_id=winner_id,
                raid_result=raid_result,
                reward_result=reward_result,
            ),
            updated_record,
        )

    # ------------------------------------------------------------------
    # Pipeline helpers
    # ------------------------------------------------------------------

    async def _validate_move_preconditions(
        self,
        match_id: MatchId,
        player_id: PlayerId,
    ) -> dict:
        """Load match, validate participant/status/moves, extract player context.

        Returns a dict with keys: match_record, is_player1, moves_remaining,
        current_board_data, current_score, moves_made, longest_chain, status.
        """
        match_record = await self._match_repo.find_by_id(UUID(str(match_id)))
        if match_record is None:
            raise self._errors.not_found(
                f"Match {match_id} not found",
                code="NOT_FOUND_MATCH",
                match_id=str(match_id),
            )

        player_uuid = UUID(str(player_id))
        if player_uuid not in (match_record.player1_id, match_record.player2_id):
            raise self._errors.forbidden(
                "Player is not a participant in this match",
                code="FORBIDDEN_NOT_MATCH_PARTICIPANT",
                match_id=str(match_id),
                player_id=str(player_id),
            )

        status = MatchStatus(match_record.status)
        if status in (MatchStatus.COMPLETED, MatchStatus.ABANDONED):
            raise self._errors.conflict(
                "Match is already completed or abandoned",
                code="CONFLICT_MATCH_ALREADY_COMPLETED",
                match_id=str(match_id),
                status=status.value,
            )
        if status not in (MatchStatus.PENDING, MatchStatus.IN_PROGRESS):
            raise self._errors.conflict(
                "Match is not in a valid state for moves",
                code="CONFLICT_MATCH_NOT_IN_PROGRESS",
                match_id=str(match_id),
                status=status.value,
            )

        is_player1 = player_uuid == match_record.player1_id
        if is_player1:
            moves_remaining = match_record.player1_moves_remaining
            current_board_data = match_record.player1_board_state
            current_score = match_record.player1_score
            moves_made = match_record.player1_moves_made
            longest_chain = match_record.player1_longest_chain
        else:
            moves_remaining = match_record.player2_moves_remaining
            current_board_data = match_record.player2_board_state
            current_score = match_record.player2_score
            moves_made = match_record.player2_moves_made
            longest_chain = match_record.player2_longest_chain

        if moves_remaining <= 0:
            raise self._errors.validation(
                "No moves remaining for this player",
                code="VALIDATION_NO_MOVES_REMAINING",
                match_id=str(match_id),
                player_id=str(player_id),
            )

        return {
            "match_record": match_record,
            "is_player1": is_player1,
            "moves_remaining": moves_remaining,
            "current_board_data": current_board_data,
            "current_score": current_score,
            "moves_made": moves_made,
            "longest_chain": longest_chain,
            "status": status,
        }

    async def _check_and_finalize(
        self,
        match_record: object,
        update: MatchUpdate,
        is_player1: bool,
        new_moves_remaining: int,
        new_score: int,
        new_chain: int,
        move_result: object,
        now: datetime,
    ) -> tuple[bool, PlayerId | None, object, object]:
        """Check if both players finished and finalize match if so.

        Returns (match_completed, winner_id, raid_result, reward_result).
        """
        from src.modules.match.types import CardRaidResult, MatchRewardResult

        player_finished = new_moves_remaining == 0
        winner_id: PlayerId | None = None

        if is_player1:
            opponent_moves_remaining = match_record.player2_moves_remaining  # type: ignore[attr-defined]
        else:
            opponent_moves_remaining = match_record.player1_moves_remaining  # type: ignore[attr-defined]

        both_finished = player_finished and opponent_moves_remaining == 0

        if not both_finished:
            return False, None, None, None

        update.status = MatchStatus.COMPLETED.value
        update.completed_at = now

        if is_player1:
            p1_score = new_score
            p2_score = match_record.player2_score  # type: ignore[attr-defined]
        else:
            p1_score = match_record.player1_score  # type: ignore[attr-defined]
            p2_score = new_score

        # --- Hook 6: opponent_score_reduction (Thick Skin) ---
        # Each player's reduction fraction is applied to the OTHER player's score.
        if self._card_service is not None:
            p1_id_uuid = match_record.player1_id  # type: ignore[attr-defined]
            p2_id_uuid = match_record.player2_id  # type: ignore[attr-defined]
            p1_mods = await self._card_service.build_modifier_engine(p1_id_uuid)
            p2_mods = await self._card_service.build_modifier_engine(p2_id_uuid)
            p1_score_mods, _ = p1_mods.get_score_modifiers()
            p2_score_mods, _ = p2_mods.get_score_modifiers()
            if p1_score_mods.opponent_score_reduction > 0:
                p2_score = int(p2_score * (1.0 - p1_score_mods.opponent_score_reduction))
            if p2_score_mods.opponent_score_reduction > 0:
                p1_score = int(p1_score * (1.0 - p2_score_mods.opponent_score_reduction))

        if p1_score > p2_score:
            winner_id = PlayerId(match_record.player1_id)  # type: ignore[attr-defined]
        elif p2_score > p1_score:
            winner_id = PlayerId(match_record.player2_id)  # type: ignore[attr-defined]

        if winner_id is not None:
            update.winner_id = UUID(str(winner_id))

        p1_id = PlayerId(match_record.player1_id)  # type: ignore[attr-defined]
        p2_id = PlayerId(match_record.player2_id)  # type: ignore[attr-defined]
        raid_result, reward_result = await self._finalizer.finalize_match(
            p1_id,
            p2_id,
            p1_score,
            p2_score,
            winner_id,
        )

        # Persist raid result on match record for later retrieval.
        if raid_result.occurred:
            update.raid_data = {
                "occurred": raid_result.occurred,
                "stolen_card_id": raid_result.stolen_card_id,
                "stolen_card_name": raid_result.stolen_card_name,
                "was_shielded": raid_result.was_shielded,
                "card_unequipped": raid_result.card_unequipped,
                "blocked_by_card": raid_result.blocked_by_card,
                "blocked_by_card_name": raid_result.blocked_by_card_name,
            }

        # Persist reward result on match record for later retrieval.
        if reward_result.awarded:
            update.reward_data = {
                "awarded": reward_result.awarded,
                "cards": reward_result.cards,
                "tier": reward_result.tier,
            }

        return True, winner_id, raid_result, reward_result
