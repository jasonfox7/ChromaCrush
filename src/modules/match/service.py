"""Match service — asynchronous versus match coordination.

Orchestrates two-player matches: creation, move submission, scoring,
special gem processing, forfeit handling, and match history retrieval.
All public methods are ``async def``. Dependencies are injected via
``__init__``. No direct imports from ``src.core`` concrete implementations.

Move processing is delegated to ``MoveProcessor``, and match finalization
(result recording + ELO) is delegated to ``MatchFinalizer``.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from src.core.entity_lock import EntityBusyError, EntityLockManager
from src.core.types.game import MatchId, Move, PlayerId
from src.modules.match.dto import MatchCreate, MatchUpdate
from src.modules.match.match_finalizer import MatchFinalizer
from src.modules.match.move_processor import MoveProcessor
from src.modules.match.queries import _MatchQueriesMixin
from src.modules.match.types import (
    MatchState,
    MatchStatus,
    MatchType,
    MoveSubmissionResult,
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.auth.protocols import AuthServiceProtocol
    from src.modules.board_gen.protocols import BoardGenServiceProtocol
    from src.modules.energy.protocols import EnergyServiceProtocol
    from src.modules.match.protocols import (
        BoardServiceProtocol,
        MatchMoveRepositoryProtocol,
        MatchRepositoryProtocol,
        ScoringServiceProtocol,
    )
    from src.modules.player.protocols import PlayerServiceProtocol
    from src.modules.special_gems.protocols import SpecialGemsServiceProtocol

# ---------------------------------------------------------------------------
# Named constants (P3-04 compliance)
# ---------------------------------------------------------------------------


class MatchRepositoryBundle:
    """Groups match-related repositories into a single injectable.

    Reduces the ``MatchService`` constructor parameter count by bundling
    the two repository dependencies. Follows the same pattern as
    ``AdRepositoryBundle`` in the ads module.
    """

    def __init__(
        self,
        match_repository: MatchRepositoryProtocol,
        match_move_repository: MatchMoveRepositoryProtocol,
    ) -> None:
        self.match_repository = match_repository
        self.match_move_repository = match_move_repository


class MatchService(_MatchQueriesMixin):
    """Core match coordination service.

    Manages the full lifecycle of two-player asynchronous matches:
    creation, move processing, scoring, forfeit, history, and
    stale-match abandonment.

    All public methods are ``async def`` because they involve database
    operations and cross-module coordination. Dependencies arrive via
    ``__init__`` injection from the composition root.

    Move processing is delegated to ``MoveProcessor`` and match
    finalization to ``MatchFinalizer`` (composition, not inheritance).
    """

    # ------------------------------------------------------------------
    # Construction and configuration
    # ------------------------------------------------------------------

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        data_ctx: DataContextProtocol,
        board_gen_service: BoardGenServiceProtocol,
        board_service: BoardServiceProtocol,
        scoring_service: ScoringServiceProtocol,
        special_gems_service: SpecialGemsServiceProtocol,
        player_service: PlayerServiceProtocol,
        auth_service: AuthServiceProtocol,
        energy_service: EnergyServiceProtocol,
        repos: MatchRepositoryBundle,
        *,
        card_service: object | None = None,
        vault_service: object | None = None,
        inventory_service: object | None = None,
        debug_logger: object | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._data_ctx = data_ctx
        self._board_gen_service = board_gen_service
        self._board_service = board_service
        self._scoring_service = scoring_service
        self._special_gems_service = special_gems_service
        self._player_service = player_service
        self._auth_service = auth_service
        self._energy_service = energy_service
        self._match_repo = repos.match_repository
        self._move_repo = repos.match_move_repository
        self._inventory_service = inventory_service
        self._debug = debug_logger

        # Cache configuration values.
        self._moves_per_player: int = config.get("match.moves_per_player", 20)
        self._timeout_hours: int = config.get("match.timeout_hours", 72)
        self._energy_cost: int = config.get("match.energy_cost", 1)
        self._allow_concurrent: bool = config.get("match.allow_concurrent", False)
        self._max_concurrent: int = config.get("match.max_concurrent", 1)
        self._cleanup_delay: int = config.get("match.cleanup_delay_seconds", 60)

        self._entity_locks = EntityLockManager()

        # Delegates — composition over inheritance.
        self._finalizer = MatchFinalizer(
            logger=logger,
            player_service=player_service,
            card_service=card_service,
            vault_service=vault_service,
        )
        self._move_processor = MoveProcessor(
            config=config,
            logger=logger,
            errors=errors,
            board_service=board_service,
            scoring_service=scoring_service,
            board_gen_service=board_gen_service,
            repos=repos,
            finalizer=self._finalizer,
            card_service=card_service,
            energy_service=energy_service,
            player_service=player_service,
            debug_logger=debug_logger,
        )

    # ------------------------------------------------------------------
    # 1. create_match
    # ------------------------------------------------------------------

    async def create_match(
        self,
        player1_id: PlayerId,
        player2_id: PlayerId,
        board_seed: int | None = None,
        match_type: MatchType = MatchType.STANDARD,
    ) -> MatchState:
        """Create a new versus match between two players.

        Validates players, checks energy, generates a board, consumes
        energy, and persists the match record.

        Args:
            player1_id: First player.
            player2_id: Second player.
            board_seed: Optional deterministic seed (random if None).
            match_type: Rule set variant (default: STANDARD).

        Returns:
            Initial MatchState with PENDING status.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if same player.
            AppError: NOT_FOUND_PLAYER if either player missing.
            AppError: CONFLICT_CONCURRENT_MATCH if concurrent not allowed.
            AppError: FORBIDDEN_INSUFFICIENT_ENERGY if not enough energy.
        """
        # 1. Validate distinct players.
        if player1_id == player2_id:
            raise self._errors.validation(
                "Cannot create a match against yourself",
                code="VALIDATION_INVALID_INPUT",
                player1_id=str(player1_id),
                player2_id=str(player2_id),
            )

        # 2. Validate both players exist (raises NOT_FOUND_PLAYER internally).
        player1 = await self._player_service.get_player(player1_id)
        player2 = await self._player_service.get_player(player2_id)

        # 3. Check concurrent match limits.
        if not self._allow_concurrent:
            p1_active = await self._match_repo.find_active_by_player(
                UUID(str(player1_id))
            )
            p2_active = await self._match_repo.find_active_by_player(
                UUID(str(player2_id))
            )
            if len(p1_active) >= self._max_concurrent:
                raise self._errors.conflict(
                    f"Player {player1.username} already has {len(p1_active)} active match(es)",
                    code="CONFLICT_CONCURRENT_MATCH",
                    player_id=str(player1_id),
                    active_count=len(p1_active),
                    max_concurrent=self._max_concurrent,
                )
            if len(p2_active) >= self._max_concurrent:
                raise self._errors.conflict(
                    f"Player {player2.username} already has {len(p2_active)} active match(es)",
                    code="CONFLICT_CONCURRENT_MATCH",
                    player_id=str(player2_id),
                    active_count=len(p2_active),
                    max_concurrent=self._max_concurrent,
                )

        # 4. Check energy for both players.
        p1_can_play = await self._energy_service.can_play(
            player1_id,
            hearts_required=self._energy_cost,
        )
        if not p1_can_play:
            raise self._errors.forbidden(
                f"Player {player1.username} does not have enough energy",
                code="FORBIDDEN_INSUFFICIENT_ENERGY",
                player_id=str(player1_id),
                energy_cost=self._energy_cost,
            )
        p2_can_play = await self._energy_service.can_play(
            player2_id,
            hearts_required=self._energy_cost,
        )
        if not p2_can_play:
            raise self._errors.forbidden(
                f"Player {player2.username} does not have enough energy",
                code="FORBIDDEN_INSUFFICIENT_ENERGY",
                player_id=str(player2_id),
                energy_cost=self._energy_cost,
            )

        # 5. Generate seed if not supplied.
        seed = board_seed if board_seed is not None else self._generate_seed()

        # 6. Generate board via board_gen service.
        generated = self._board_gen_service.generate_board_for_match(
            seed,
            match_type=match_type,
        )
        initial_board = generated.board_state

        # 7. Calculate timeout.
        now = datetime.now(timezone.utc)
        timeout_at = now + timedelta(hours=self._timeout_hours)

        # 8. Consume energy for both players.
        await self._energy_service.consume_heart(player1_id, amount=self._energy_cost)
        await self._energy_service.consume_heart(player2_id, amount=self._energy_cost)

        # 9. Persist match record.
        board_data = initial_board.to_dict()
        match_create = MatchCreate(
            board_seed=seed,
            initial_board_state=board_data,
            match_type=match_type.value,
            player1_id=UUID(str(player1_id)),
            player1_board_state=board_data,
            player1_moves_remaining=self._moves_per_player,
            player2_id=UUID(str(player2_id)),
            player2_board_state=board_data,
            player2_moves_remaining=self._moves_per_player,
            timeout_at=timeout_at,
        )
        match_record = await self._match_repo.create(match_create)

        # 10. Build and return MatchState.
        match_state = self._build_match_state(match_record, player1, player2)

        self._logger.info(
            "match.created",
            match_id=str(match_state.match_id),
            player1=player1.username,
            player2=player2.username,
            match_type=match_type.value,
            seed=seed,
        )

        return match_state

    # ------------------------------------------------------------------
    # 2. submit_move (delegates to MoveProcessor)
    # ------------------------------------------------------------------

    async def submit_move(
        self,
        match_id: MatchId,
        player_id: PlayerId,
        move: Move,
    ) -> MoveSubmissionResult:
        """Submit a move for a player in an active match.

        Processes the move through board, special gems, and scoring
        services. Persists move history, updates match state, and
        handles match completion.

        Args:
            match_id: The match.
            player_id: Who is making the move.
            move: The swap to perform.

        Returns:
            MoveSubmissionResult with updated state and move details.

        Raises:
            AppError: NOT_FOUND_MATCH if match doesn't exist.
            AppError: FORBIDDEN_NOT_MATCH_PARTICIPANT if player not in match.
            AppError: CONFLICT_MATCH_ALREADY_COMPLETED if finished/abandoned.
            AppError: CONFLICT_MATCH_NOT_IN_PROGRESS for wrong status on non-pending.
            AppError: VALIDATION_NO_MOVES_REMAINING if out of moves.
            AppError: VALIDATION_INVALID_GEM_SWAP if move is invalid.
            AppError: CONFLICT_ENTITY_BUSY if another request is processing.
        """
        # Lock key: uuid5(match_id, player_id) — allows concurrent moves
        # from different players in the same match.
        lock_key = uuid5(UUID(str(match_id)), str(player_id))
        try:
            async with self._entity_locks.acquire(lock_key):
                return await self._submit_move_locked(
                    match_id, player_id, move
                )
        except EntityBusyError:
            raise self._errors.conflict(
                "Another request is already processing for this player",
                code="CONFLICT_ENTITY_BUSY",
                match_id=str(match_id),
                player_id=str(player_id),
            )

    async def _submit_move_locked(
        self,
        match_id: MatchId,
        player_id: PlayerId,
        move: Move,
    ) -> MoveSubmissionResult:
        """Inner submit_move body — called under entity lock."""
        # Delegate pipeline to MoveProcessor; it returns the partial result
        # and the updated DB record so we can build the MatchState here.
        partial_result, updated_record = await self._move_processor.submit_move(
            match_id,
            player_id,
            move,
        )

        # Build match state from the updated record (requires player lookups
        # which need _player_service + _build_match_state from the mixin).
        player1 = await self._player_service.get_player(
            PlayerId(updated_record.player1_id),
        )
        player2 = await self._player_service.get_player(
            PlayerId(updated_record.player2_id),
        )
        match_state = self._build_match_state(updated_record, player1, player2)

        # Schedule deferred cleanup if match just completed.
        if partial_result.match_completed:
            self._schedule_cleanup(match_id)

        # Fill in the match_state that MoveProcessor left as None.
        return MoveSubmissionResult(
            match_state=match_state,
            move_result=partial_result.move_result,
            score_result=partial_result.score_result,
            special_effects=partial_result.special_effects,
            points_earned=partial_result.points_earned,
            move_number=partial_result.move_number,
            moves_remaining=partial_result.moves_remaining,
            match_completed=partial_result.match_completed,
            player_finished=partial_result.player_finished,
            winner_id=partial_result.winner_id,
        )

    # ------------------------------------------------------------------
    # 2b. activate_mega
    # ------------------------------------------------------------------

    async def activate_mega(
        self,
        match_id: MatchId,
        player_id: PlayerId,
        slot_index: int,
        source: str | None = None,
    ) -> MoveSubmissionResult:
        """Activate a banked mega gem or shuffle.

        Consumes one item from the player's inventory (unless source is
        ``"void_instability"``), places the mega on the board, fires it,
        cascades, and scores — all without consuming a move.

        Args:
            match_id: The match.
            player_id: Who is activating.
            slot_index: 0-3 for mega gems, 4 for shuffle.
            source: Optional source tag (e.g. ``"void_instability"`` for
                card-triggered activations that skip inventory consumption).

        Returns:
            MoveSubmissionResult with updated match state.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if slot_index invalid.
            AppError: CONFLICT_INSUFFICIENT_INVENTORY if slot is empty.
            AppError: CONFLICT_ENTITY_BUSY if another request is processing.
        """
        lock_key = uuid5(UUID(str(match_id)), str(player_id))
        try:
            async with self._entity_locks.acquire(lock_key):
                return await self._activate_mega_locked(
                    match_id, player_id, slot_index, source
                )
        except EntityBusyError:
            raise self._errors.conflict(
                "Another request is already processing for this player",
                code="CONFLICT_ENTITY_BUSY",
                match_id=str(match_id),
                player_id=str(player_id),
            )

    async def _activate_mega_locked(
        self,
        match_id: MatchId,
        player_id: PlayerId,
        slot_index: int,
        source: str | None = None,
    ) -> MoveSubmissionResult:
        """Inner activate_mega body — called under entity lock."""
        # Slot-to-mega-value mapping.
        SLOT_MEGA_VALUES = {0: 11, 1: 22, 2: 33, 3: 44}

        # Consume from inventory unless card-triggered (no inventory cost).
        # InventoryService.consume_mega raises INSUFFICIENT_MEGA_GEMS if empty.
        _FREE_SOURCES = {"void_instability", "card_shuffle"}
        if source not in _FREE_SOURCES and self._inventory_service is not None:
            await self._inventory_service.consume_mega(player_id, slot_index)

        # --- Shuffle branch (slot 4) ---
        if slot_index == 4:
            match_record = await self._match_repo.find_by_id(
                UUID(str(match_id)),
            )
            if match_record is None:
                raise self._errors.not_found(
                    f"Match {match_id} not found",
                    code="NOT_FOUND_MATCH",
                    match_id=str(match_id),
                )

            player_uuid = UUID(str(player_id))
            is_player1 = player_uuid == match_record.player1_id

            if is_player1:
                board_data = match_record.player1_board_state
                current_score = match_record.player1_score
                moves_remaining = match_record.player1_moves_remaining
            else:
                board_data = match_record.player2_board_state
                current_score = match_record.player2_score
                moves_remaining = match_record.player2_moves_remaining

            from src.core.types.board import BoardState

            board = BoardState.from_list(board_data)

            # Derive seed for shuffle.
            player_hash = hash(str(player_id)) & 0xFFFFFFFF
            shuffle_seed = (
                match_record.board_seed ^ player_hash ^ (moves_remaining * 1103515245)
            ) & 0x7FFFFFFF

            shuffled = self._board_service.shuffle_board(board, shuffle_seed)

            # Persist new board.
            update = MatchUpdate()
            if is_player1:
                update.player1_board_state = shuffled.to_dict()
            else:
                update.player2_board_state = shuffled.to_dict()

            updated_record = await self._match_repo.update(
                UUID(str(match_id)),
                update,
            )

            # Build match state.
            player1 = await self._player_service.get_player(
                PlayerId(updated_record.player1_id),
            )
            player2 = await self._player_service.get_player(
                PlayerId(updated_record.player2_id),
            )
            match_state = self._build_match_state(updated_record, player1, player2)

            from src.core.types.game import Move, Position
            from src.modules.board.types import MoveProcessingResult
            from src.modules.scoring.types import MoveScore

            dummy_move = Move(
                from_pos=Position(0, 0),
                to_pos=Position(0, 1),
                timestamp_ms=0,
            )
            empty_move_result = MoveProcessingResult(
                initial_board=board,
                final_board=shuffled,
                move=dummy_move,
                was_valid_match=True,
                cascades=[],
                total_matches=0,
                total_gems_cleared=0,
                chain_count=0,
                special_gems_created=[],
            )

            self._logger.info(
                "match.shuffle_activated",
                match_id=str(match_id),
                player_id=str(player_id),
            )

            return MoveSubmissionResult(
                match_state=match_state,
                move_result=empty_move_result,
                score_result=MoveScore(
                    total_points=0,
                    cascade_scores=(),
                    chain_count=0,
                    total_gems_cleared=0,
                    highest_chain_multiplier=1.0,
                    special_gems_created=0,
                    special_gems_activated=0,
                ),
                special_effects=[],
                points_earned=0,
                move_number=0,
                moves_remaining=moves_remaining,
                match_completed=False,
                player_finished=False,
            )

        # --- Mega gem branch (slots 0-3) ---
        mega_value = SLOT_MEGA_VALUES.get(slot_index)
        if mega_value is None:
            raise self._errors.validation(
                f"Invalid slot_index: {slot_index}",
                code="VALIDATION_INVALID_INPUT",
                slot_index=slot_index,
            )

        partial_result, updated_record = (
            await self._move_processor.process_mega_activation(
                match_id,
                player_id,
                slot_index,
                mega_value,
            )
        )

        # Build match state from the updated record.
        player1 = await self._player_service.get_player(
            PlayerId(updated_record.player1_id),
        )
        player2 = await self._player_service.get_player(
            PlayerId(updated_record.player2_id),
        )
        match_state = self._build_match_state(updated_record, player1, player2)

        # Schedule deferred cleanup if match just completed.
        if partial_result.match_completed:
            self._schedule_cleanup(match_id)

        return MoveSubmissionResult(
            match_state=match_state,
            move_result=partial_result.move_result,
            score_result=partial_result.score_result,
            special_effects=partial_result.special_effects,
            points_earned=partial_result.points_earned,
            move_number=partial_result.move_number,
            moves_remaining=partial_result.moves_remaining,
            match_completed=partial_result.match_completed,
            player_finished=partial_result.player_finished,
            winner_id=partial_result.winner_id,
            raid_result=partial_result.raid_result,
            reward_result=partial_result.reward_result,
        )

    # ------------------------------------------------------------------
    # 3. forfeit_match
    # ------------------------------------------------------------------

    async def forfeit_match(
        self,
        match_id: MatchId,
        player_id: PlayerId,
    ) -> MatchState:
        """Forfeit a match, marking the opponent as winner.

        Args:
            match_id: The match.
            player_id: Who is forfeiting.

        Returns:
            Updated MatchState with COMPLETED status.

        Raises:
            AppError: NOT_FOUND_MATCH if match doesn't exist.
            AppError: FORBIDDEN_NOT_MATCH_PARTICIPANT if player not in match.
            AppError: CONFLICT_MATCH_ALREADY_COMPLETED if match already finished.
        """
        match_record = await self._match_repo.find_by_id(UUID(str(match_id)))
        if match_record is None:
            raise self._errors.not_found(
                f"Match {match_id} not found",
                code="NOT_FOUND_MATCH",
                match_id=str(match_id),
            )

        # Validate participant.
        player_uuid = UUID(str(player_id))
        if player_uuid not in (match_record.player1_id, match_record.player2_id):
            raise self._errors.forbidden(
                "Player is not a participant in this match",
                code="FORBIDDEN_NOT_MATCH_PARTICIPANT",
                match_id=str(match_id),
                player_id=str(player_id),
            )

        # Validate match is still active.
        status = MatchStatus(match_record.status)
        if status in (MatchStatus.COMPLETED, MatchStatus.ABANDONED):
            raise self._errors.conflict(
                "Match is already completed or abandoned",
                code="CONFLICT_MATCH_ALREADY_COMPLETED",
                match_id=str(match_id),
                status=status.value,
            )

        # Determine opponent as winner.
        is_player1 = player_uuid == match_record.player1_id
        if is_player1:
            winner_uuid = match_record.player2_id
        else:
            winner_uuid = match_record.player1_id
        winner_player_id = PlayerId(winner_uuid)

        # Finalize match stats, ELO, and card raids first.
        p1_id = PlayerId(match_record.player1_id)
        p2_id = PlayerId(match_record.player2_id)
        p1_score = match_record.player1_score
        p2_score = match_record.player2_score
        raid_result, reward_result = await self._finalizer.finalize_match(
            p1_id,
            p2_id,
            p1_score,
            p2_score,
            winner_player_id,
        )

        now = datetime.now(timezone.utc)
        update = MatchUpdate(
            status=MatchStatus.COMPLETED.value,
            completed_at=now,
            winner_id=winner_uuid,
            forfeit_by=player_uuid,
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

        updated_record = await self._match_repo.update(UUID(str(match_id)), update)

        player1 = await self._player_service.get_player(p1_id)
        player2 = await self._player_service.get_player(p2_id)
        match_state = self._build_match_state(updated_record, player1, player2)

        self._logger.info(
            "match.forfeited",
            match_id=str(match_id),
            forfeit_by=str(player_id),
            winner_id=str(winner_player_id),
        )

        # Schedule deferred cleanup of match data.
        self._schedule_cleanup(match_id)

        return match_state

    # ------------------------------------------------------------------
    # 4. abandon_stale_matches
    # ------------------------------------------------------------------

    async def abandon_stale_matches(self) -> int:
        """Abandon matches that have exceeded their timeout.

        Returns:
            Number of matches abandoned.
        """
        now = datetime.now(timezone.utc)
        stale_records = await self._match_repo.find_stale_matches(now)

        if not stale_records:
            return 0

        match_ids = [record.id for record in stale_records]
        count = await self._match_repo.bulk_abandon(match_ids)

        self._logger.info(
            "match.stale_matches_abandoned",
            count=count,
            match_ids=[str(mid) for mid in match_ids],
        )

        return count

    # ------------------------------------------------------------------
    # Post-match cleanup
    # ------------------------------------------------------------------

    def _schedule_cleanup(self, match_id: MatchId) -> None:
        """Schedule deferred cleanup of match data after completion.

        Fires an asyncio task that waits ``_cleanup_delay`` seconds then
        purges board states, raid data, and move records.  The delay
        ensures the client has time to fetch the final match state even
        on flaky connections with retries.
        """
        import asyncio

        asyncio.create_task(self._delayed_cleanup(match_id))

    async def _delayed_cleanup(self, match_id: MatchId) -> None:
        """Wait then purge board states, raid data, and move records."""
        import asyncio

        await asyncio.sleep(self._cleanup_delay)
        try:
            await self._match_repo.cleanup_match_data(UUID(str(match_id)))
            await self._move_repo.delete_by_match_id(UUID(str(match_id)))
            self._logger.info(
                "match.cleanup_complete",
                match_id=str(match_id),
            )
        except Exception as exc:
            self._logger.warning(
                "match.cleanup_failed",
                match_id=str(match_id),
                error=str(exc),
            )

    async def cleanup_completed_matches(self, older_than_hours: int = 1) -> int:
        """Bulk cleanup of completed/abandoned matches older than threshold.

        Used by CLI for manual cleanup of matches that missed the
        deferred cleanup (e.g., server restart before task fired).

        Args:
            older_than_hours: Only clean matches completed more than
                this many hours ago.

        Returns:
            Number of matches cleaned.
        """
        from sqlalchemy import select

        from src.data.models.match import MatchModel

        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        cleaned = 0

        async with self._data_ctx.session() as session:
            stmt = (
                select(MatchModel.id)
                .where(MatchModel.status.in_(["completed", "abandoned"]))
                .where(MatchModel.completed_at < cutoff)
                .where(MatchModel.initial_board_state.isnot(None))
            )
            result = await session.execute(stmt)
            match_ids = [row[0] for row in result.all()]

        for mid in match_ids:
            try:
                await self._match_repo.cleanup_match_data(mid)
                await self._move_repo.delete_by_match_id(mid)
                cleaned += 1
            except Exception as exc:
                self._logger.warning(
                    "match.bulk_cleanup_failed",
                    match_id=str(mid),
                    error=str(exc),
                )

        if cleaned:
            self._logger.info(
                "match.bulk_cleanup_complete",
                cleaned_count=cleaned,
                total_found=len(match_ids),
            )

        return cleaned

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_seed() -> int:
        """Generate a cryptographically random board seed.

        Returns:
            63-bit positive integer.
        """
        return secrets.randbits(63)
