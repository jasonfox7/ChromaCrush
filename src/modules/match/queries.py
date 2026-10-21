"""Read-only query methods (mixin for MatchService)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from src.core.types.board import BoardState
from src.core.types.game import GemType, MatchId, Move, PlayerId, Position
from src.modules.match.dto import PaginatedResult
from src.modules.match.types import (
    MatchState,
    MatchStatus,
    MatchSummary,
    MatchType,
    MoveRecord,
    PlayerBoardState,
    PlayerMatchState,
)

if TYPE_CHECKING:
    pass

# Maximum number of results allowed in paginated history queries.
_MAX_PAGINATION_LIMIT = 100


class _MatchQueriesMixin:
    """Read-only match and move query methods."""

    async def get_match(
        self,
        match_id: MatchId,
    ) -> MatchState:
        """Get current state of a match.

        Args:
            match_id: The match to retrieve.

        Returns:
            Current MatchState.

        Raises:
            AppError: NOT_FOUND_MATCH if match doesn't exist.
        """
        match_record = await self._match_repo.find_by_id(UUID(str(match_id)))
        if match_record is None:
            raise self._errors.not_found(
                f"Match {match_id} not found",
                code="NOT_FOUND_MATCH",
                match_id=str(match_id),
            )

        player1 = await self._player_service.get_player(
            PlayerId(match_record.player1_id),
        )
        player2 = await self._player_service.get_player(
            PlayerId(match_record.player2_id),
        )

        return self._build_match_state(match_record, player1, player2)

    async def get_match_state(
        self,
        match_id: MatchId,
        for_player_id: PlayerId | None = None,
    ) -> MatchState:
        """Get current state of a match, optionally validating player access.

        Args:
            match_id: The match to retrieve.
            for_player_id: If provided, validate that this player is a participant.

        Returns:
            Current MatchState.

        Raises:
            AppError: NOT_FOUND_MATCH if match doesn't exist.
            AppError: FORBIDDEN_NOT_MATCH_PARTICIPANT if player not in match.
        """
        match_state = await self.get_match(match_id)

        if for_player_id is not None and not match_state.is_participant(for_player_id):
            raise self._errors.forbidden(
                "Player is not a participant in this match",
                code="FORBIDDEN_NOT_MATCH_PARTICIPANT",
                match_id=str(match_id),
                player_id=str(for_player_id),
            )

        return match_state

    async def get_player_board(
        self,
        match_id: MatchId,
        player_id: PlayerId,
    ) -> PlayerBoardState:
        """Get a player's current board state and progress.

        Args:
            match_id: The match.
            player_id: The player.

        Returns:
            PlayerBoardState with current board, moves, and score.

        Raises:
            AppError: NOT_FOUND_MATCH if match doesn't exist.
            AppError: FORBIDDEN_NOT_MATCH_PARTICIPANT if player not in match.
        """
        match_record = await self._match_repo.find_by_id(UUID(str(match_id)))
        if match_record is None:
            raise self._errors.not_found(
                f"Match {match_id} not found",
                code="NOT_FOUND_MATCH",
                match_id=str(match_id),
            )

        player_uuid = UUID(str(player_id))
        if player_uuid == match_record.player1_id:
            board_data = match_record.player1_board_state
            moves_made = match_record.player1_moves_made
            moves_remaining = match_record.player1_moves_remaining
            score = match_record.player1_score
        elif player_uuid == match_record.player2_id:
            board_data = match_record.player2_board_state
            moves_made = match_record.player2_moves_made
            moves_remaining = match_record.player2_moves_remaining
            score = match_record.player2_score
        else:
            raise self._errors.forbidden(
                "Player is not a participant in this match",
                code="FORBIDDEN_NOT_MATCH_PARTICIPANT",
                match_id=str(match_id),
                player_id=str(player_id),
            )

        # Board data may be None after post-match cleanup.
        if board_data is None:
            raise self._errors.not_found(
                "Board data has been cleaned up for this completed match",
                code="NOT_FOUND_BOARD_DATA",
                match_id=str(match_id),
            )

        board = BoardState.from_list(board_data)
        has_valid = self._board_service.has_valid_moves(board)

        return PlayerBoardState(
            player_id=player_id,
            board=board,
            moves_made=moves_made,
            moves_remaining=moves_remaining,
            score=score,
            has_valid_moves=has_valid,
        )

    async def get_active_matches(
        self,
        player_id: PlayerId,
    ) -> list[MatchState]:
        """Get all active matches for a player.

        Returns matches with status PENDING or IN_PROGRESS.

        Args:
            player_id: The player.

        Returns:
            List of active MatchState objects.
        """
        player_uuid = UUID(str(player_id))
        records = await self._match_repo.find_active_by_player(player_uuid)

        states: list[MatchState] = []
        for record in records:
            player1 = await self._player_service.get_player(
                PlayerId(record.player1_id),
            )
            player2 = await self._player_service.get_player(
                PlayerId(record.player2_id),
            )
            states.append(self._build_match_state(record, player1, player2))

        return states

    async def get_match_history(
        self,
        player_id: PlayerId,
        limit: int = 20,
        offset: int = 0,
        status: MatchStatus | None = None,
    ) -> PaginatedResult[MatchSummary]:
        """Get match history for a player.

        Args:
            player_id: The player.
            limit: Maximum results (1-100, default 20).
            offset: Pagination offset.
            status: Optional status filter.

        Returns:
            PaginatedResult containing MatchSummary objects.

        Raises:
            AppError: VALIDATION_INVALID_INPUT if limit out of range.
        """
        # Validate limit.
        if limit < 1 or limit > _MAX_PAGINATION_LIMIT:
            raise self._errors.validation(
                f"Limit must be between 1 and {_MAX_PAGINATION_LIMIT}, got {limit}",
                code="VALIDATION_INVALID_INPUT",
                field="limit",
                value=limit,
            )

        status_str = status.value if status is not None else None
        player_uuid = UUID(str(player_id))

        records, total = await self._match_repo.find_by_player(
            player_uuid,
            status=status_str,
            limit=limit,
            offset=offset,
        )

        # Build MatchSummary for each record relative to requesting player.
        summaries: list[MatchSummary] = []
        for record in records:
            is_player1 = player_uuid == record.player1_id

            if is_player1:
                opponent_id = PlayerId(record.player2_id)
                player_score = record.player1_score
                opponent_score = record.player2_score
            else:
                opponent_id = PlayerId(record.player1_id)
                player_score = record.player2_score
                opponent_score = record.player1_score

            # Determine opponent username.
            try:
                opponent = await self._player_service.get_player(opponent_id)
                opponent_username = opponent.username
            except Exception:
                opponent_username = "Unknown"

            # Determine win/loss/draw.
            record_status = MatchStatus(record.status)
            won: bool | None = None
            if record_status == MatchStatus.COMPLETED:
                if record.winner_id is None:
                    won = None  # Draw
                elif (is_player1 and record.winner_id == record.player1_id) or (
                    not is_player1 and record.winner_id == record.player2_id
                ):
                    won = True
                else:
                    won = False

            summaries.append(
                MatchSummary(
                    match_id=MatchId(record.id),
                    opponent_id=opponent_id,
                    opponent_username=opponent_username,
                    player_score=player_score,
                    opponent_score=opponent_score,
                    won=won,
                    status=record_status,
                    match_type=MatchType(record.match_type),
                    created_at=record.created_at,
                    completed_at=record.completed_at,
                )
            )

        return PaginatedResult(
            items=summaries,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_move_history(
        self,
        match_id: MatchId,
        player_id: PlayerId | None = None,
    ) -> list[MoveRecord]:
        """Get move history for a match, optionally filtered by player.

        Args:
            match_id: The match.
            player_id: If provided, return only moves by this player.

        Returns:
            List of MoveRecord objects in chronological order.

        Raises:
            AppError: NOT_FOUND_MATCH if match doesn't exist.
        """
        # Validate match exists.
        match_record = await self._match_repo.find_by_id(UUID(str(match_id)))
        if match_record is None:
            raise self._errors.not_found(
                f"Match {match_id} not found",
                code="NOT_FOUND_MATCH",
                match_id=str(match_id),
            )

        player_uuid = UUID(str(player_id)) if player_id is not None else None
        move_records = await self._move_repo.find_by_match(
            UUID(str(match_id)),
            player_id=player_uuid,
        )

        # Convert ORM models to MoveRecord domain objects.
        result: list[MoveRecord] = []
        for mr in move_records:
            from_pos = Position(mr.from_row, mr.from_col)
            to_pos = Position(mr.to_row, mr.to_col)
            move_obj = Move(
                from_pos=from_pos,
                to_pos=to_pos,
                timestamp_ms=mr.client_timestamp_ms,
            )

            # Parse special_gems_created from JSON.
            created: list[tuple[Position, GemType]] = []
            for entry in mr.special_gems_created or []:
                pos = Position(entry["row"], entry["col"])
                gem = GemType(entry["gem_type"])
                created.append((pos, gem))

            # Parse special_gems_activated from JSON.
            activated: list[Position] = []
            for entry in mr.special_gems_activated or []:
                activated.append(Position(entry["row"], entry["col"]))

            result.append(
                MoveRecord(
                    move_number=mr.move_number,
                    player_id=PlayerId(mr.player_id),
                    move=move_obj,
                    board_before=BoardState.from_list(mr.board_before),
                    board_after=BoardState.from_list(mr.board_after),
                    score_earned=mr.score_earned,
                    chain_count=mr.chain_count,
                    gems_cleared=mr.gems_cleared,
                    special_gems_created=created,
                    special_gems_activated=activated,
                    timestamp=mr.created_at,
                )
            )

        return result

    def _build_match_state(
        self,
        match_record: object,
        player1: object,
        player2: object,
    ) -> MatchState:
        """Convert a MatchModel + Player objects into a MatchState domain object.

        Args:
            match_record: MatchModel ORM instance.
            player1: Player domain object for player1.
            player2: Player domain object for player2.

        Returns:
            Fully populated MatchState.
        """
        # Extract board states from JSONB (None after post-match cleanup).
        raw_initial = match_record.initial_board_state  # type: ignore[attr-defined]
        raw_p1 = match_record.player1_board_state  # type: ignore[attr-defined]
        raw_p2 = match_record.player2_board_state  # type: ignore[attr-defined]
        initial_board = BoardState.from_list(raw_initial) if raw_initial else None
        p1_board = BoardState.from_list(raw_p1) if raw_p1 else None
        p2_board = BoardState.from_list(raw_p2) if raw_p2 else None

        p1_state = PlayerMatchState(
            player_id=PlayerId(match_record.player1_id),  # type: ignore[attr-defined]
            player_username=player1.username,  # type: ignore[attr-defined]
            is_bot=getattr(player1, "is_bot", False),  # type: ignore[attr-defined]
            score=match_record.player1_score,  # type: ignore[attr-defined]
            moves_made=match_record.player1_moves_made,  # type: ignore[attr-defined]
            moves_remaining=match_record.player1_moves_remaining,  # type: ignore[attr-defined]
            current_board=p1_board,
            longest_chain=match_record.player1_longest_chain,  # type: ignore[attr-defined]
            finished_at=match_record.player1_finished_at,  # type: ignore[attr-defined]
        )

        p2_state = PlayerMatchState(
            player_id=PlayerId(match_record.player2_id),  # type: ignore[attr-defined]
            player_username=player2.username,  # type: ignore[attr-defined]
            is_bot=getattr(player2, "is_bot", False),  # type: ignore[attr-defined]
            score=match_record.player2_score,  # type: ignore[attr-defined]
            moves_made=match_record.player2_moves_made,  # type: ignore[attr-defined]
            moves_remaining=match_record.player2_moves_remaining,  # type: ignore[attr-defined]
            current_board=p2_board,
            longest_chain=match_record.player2_longest_chain,  # type: ignore[attr-defined]
            finished_at=match_record.player2_finished_at,  # type: ignore[attr-defined]
        )

        winner_id = (
            PlayerId(match_record.winner_id)  # type: ignore[attr-defined]
            if match_record.winner_id is not None  # type: ignore[attr-defined]
            else None
        )
        forfeit_by = (
            PlayerId(match_record.forfeit_by)  # type: ignore[attr-defined]
            if match_record.forfeit_by is not None  # type: ignore[attr-defined]
            else None
        )

        return MatchState(
            match_id=MatchId(match_record.id),  # type: ignore[attr-defined]
            board_seed=match_record.board_seed,  # type: ignore[attr-defined]
            initial_board=initial_board,
            status=MatchStatus(match_record.status),  # type: ignore[attr-defined]
            match_type=MatchType(match_record.match_type),  # type: ignore[attr-defined]
            player1=p1_state,
            player2=p2_state,
            winner_id=winner_id,
            forfeit_by=forfeit_by,
            raid_data=getattr(match_record, "raid_data", None),  # type: ignore[attr-defined]
            reward_data=getattr(match_record, "reward_data", None),  # type: ignore[attr-defined]
            created_at=match_record.created_at,  # type: ignore[attr-defined]
            started_at=match_record.started_at,  # type: ignore[attr-defined]
            completed_at=match_record.completed_at,  # type: ignore[attr-defined]
            timeout_at=match_record.timeout_at,  # type: ignore[attr-defined]
        )
