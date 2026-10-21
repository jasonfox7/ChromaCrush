"""Matchmaking service implementation.

Fully async service managing matchmaking queues, ELO-based pairing, and
match creation. All dependencies arrive via ``__init__`` injection; no
direct imports of core services or environment access.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from src.core.errors import AppError
from src.core.types.game import MatchId, PlayerId
from src.core.types.player import PlayerType
from src.modules.matchmaking._helpers import (
    calculate_queue_position,
    estimate_wait_time,
    maybe_expand_elo_range,
    try_create_match,
)
from src.modules.matchmaking.types import (
    MatchmakingResult,
    MatchmakingStatus,
    PoolType,
    QueueEntry,
    QueueEntryData,
    QueueStats,
    QueueStatus,
)

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.matchmaking.protocols import (
        MatchmakingQueueRepositoryProtocol,
        MatchServiceProtocol,
        PlayerServiceProtocol,
    )

_STATUS_OPPONENT_SEARCH_LIMIT = 100
_MATCH_OPPONENT_SEARCH_LIMIT = 10


class MatchmakingService:
    """Concrete implementation of ``MatchmakingServiceProtocol``.

    Manages matchmaking queues with ELO-based pairing and progressive
    range expansion. All public methods are ``async def`` as they involve
    Redis operations and cross-module service calls.

    Args:
        config: Configuration service for reading settings.
        logger: Structured logging service.
        errors: Error factory service.
        match_service: Match module for creating matches and checking active matches.
        player_service: Player module for player lookups and ELO queries.
        matchmaking_queue_repository: Redis-backed queue repository.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        match_service: MatchServiceProtocol,
        player_service: PlayerServiceProtocol,
        matchmaking_queue_repository: MatchmakingQueueRepositoryProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._match_service = match_service
        self._player_service = player_service
        self._queue_repo = matchmaking_queue_repository

        # Cache configuration values read at init time
        self._initial_elo_range: int = config.get("matchmaking.initial_elo_range", 50)
        self._elo_range_expansion: int = config.get(
            "matchmaking.elo_range_expansion", 50
        )
        self._elo_range_expansion_interval_seconds: int = config.get(
            "matchmaking.elo_range_expansion_interval_seconds", 30
        )
        self._max_elo_range: int = config.get("matchmaking.max_elo_range", 500)
        self._queue_timeout_seconds: int = config.get(
            "matchmaking.queue_timeout_seconds", 300
        )
        self._min_wait_before_expansion: int = config.get(
            "matchmaking.min_wait_before_expansion", 10
        )
        self._bot_fallback_seconds: int = config.get(
            "matchmaking.bot_fallback_seconds", 15
        )

    # ========== Public Methods ==========

    async def join_queue(
        self,
        player_id: PlayerId,
        pool_type: PoolType = PoolType.MIXED,
    ) -> QueueEntry:
        """Add a player to the matchmaking queue.

        Validates the player exists, checks pool type restrictions,
        ensures the player is not already queued or in an active match,
        then adds them to the appropriate Redis queue.
        """
        # 1. Validate player exists and get details
        player = await self._player_service.get_player(player_id)

        # 2. Validate pool type matches player type
        if pool_type == PoolType.HUMAN and player.is_bot:
            raise self._errors.forbidden(
                "Bot players cannot join human-only queue",
                code="FORBIDDEN_POOL_RESTRICTED",
                player_id=str(player_id),
                pool_type=pool_type.value,
                player_type="bot",
            )

        if pool_type == PoolType.BOT and not player.is_bot:
            raise self._errors.forbidden(
                "Human players cannot join bot-only queue",
                code="FORBIDDEN_POOL_RESTRICTED",
                player_id=str(player_id),
                pool_type=pool_type.value,
                player_type="human",
            )

        # 3. Check not already in queue
        if await self._queue_repo.is_in_queue(player_id):
            existing = await self._queue_repo.get_player_queue_state(player_id)
            raise self._errors.conflict(
                "Player already in matchmaking queue",
                code="CONFLICT_ALREADY_IN_QUEUE",
                player_id=str(player_id),
                pool_type=existing.pool_type.value if existing else None,
                joined_at=existing.joined_at.isoformat() if existing else None,
            )

        # 4. Check not in active match
        active_matches = await self._match_service.get_active_matches(player_id)
        if active_matches:
            raise self._errors.conflict(
                "Player is in an active match",
                code="CONFLICT_PLAYER_IN_MATCH",
                player_id=str(player_id),
                active_match_id=str(active_matches[0].match_id),
            )

        # 5. Get current ELO
        elo_rating = await self._player_service.get_elo(player_id)

        # 6. Add to queue
        entry_data = await self._queue_repo.add_to_queue(
            player_id=player_id,
            elo_rating=elo_rating,
            pool_type=pool_type,
            initial_elo_range=self._initial_elo_range,
        )

        # 7. Log
        self._logger.info(
            "Player joined matchmaking queue",
            player_id=str(player_id),
            pool_type=pool_type.value,
            elo_rating=elo_rating,
        )

        # 8. Calculate position and estimate
        position = await self._calculate_queue_position(player_id, pool_type)
        estimate = await self._estimate_wait_time(elo_rating, pool_type)

        return QueueEntry(
            player_id=player_id,
            player_username=player.username,
            elo_rating=elo_rating,
            pool_type=pool_type,
            joined_at=entry_data.joined_at,
            current_elo_range=(entry_data.current_min_elo, entry_data.current_max_elo),
            estimated_wait_seconds=estimate,
            position_in_queue=position,
        )

    async def leave_queue(self, player_id: PlayerId) -> bool:
        """Remove a player from the matchmaking queue.

        Returns True if removed, False if they were not in queue.
        """
        # Get state before removal for logging
        queue_state = await self._queue_repo.get_player_queue_state(player_id)

        removed = await self._queue_repo.remove_from_queue(player_id)

        if removed and queue_state is not None:
            wait_seconds = int(
                (datetime.now(timezone.utc) - queue_state.joined_at).total_seconds()
            )
            self._logger.info(
                "Player left matchmaking queue",
                player_id=str(player_id),
                pool_type=queue_state.pool_type.value,
                wait_time_seconds=wait_seconds,
            )

        return removed

    async def get_queue_status(self, player_id: PlayerId) -> QueueStatus | None:
        """Get the current queue status for a player.

        Returns None if the player is not in any queue.
        """
        queue_state = await self._queue_repo.get_player_queue_state(player_id)
        if queue_state is None:
            return None

        now = datetime.now(timezone.utc)
        wait_seconds = int((now - queue_state.joined_at).total_seconds())

        # Count potential opponents in range
        opponents = await self._queue_repo.find_opponents_in_range(
            pool_type=queue_state.pool_type,
            min_elo=queue_state.current_min_elo,
            max_elo=queue_state.current_max_elo,
            exclude_player_id=player_id,
            limit=_STATUS_OPPONENT_SEARCH_LIMIT,
        )

        position = await self._calculate_queue_position(
            player_id, queue_state.pool_type
        )
        estimate = await self._estimate_wait_time(
            queue_state.elo_rating, queue_state.pool_type
        )

        return QueueStatus(
            player_id=player_id,
            pool_type=queue_state.pool_type,
            elo_rating=queue_state.elo_rating,
            joined_at=queue_state.joined_at,
            wait_time_seconds=wait_seconds,
            current_elo_range=(
                queue_state.current_min_elo,
                queue_state.current_max_elo,
            ),
            potential_opponents=len(opponents),
            position_in_queue=position,
            estimated_wait_seconds=estimate,
        )

    async def find_match(self, player_id: PlayerId) -> MatchmakingResult:
        """Attempt to find and create a match for a queued player.

        Checks the player's queue state, handles timeout, expands ELO
        range if needed, and attempts to pair with an opponent.
        """
        # 1. Get player's queue state
        queue_state = await self._queue_repo.get_player_queue_state(player_id)
        if queue_state is None:
            raise self._errors.validation(
                "Player not in matchmaking queue",
                code="VALIDATION_NOT_IN_QUEUE",
                player_id=str(player_id),
            )

        # 2. Check for timeout
        now = datetime.now(timezone.utc)
        wait_seconds = (now - queue_state.joined_at).total_seconds()

        if wait_seconds > self._queue_timeout_seconds:
            await self._queue_repo.remove_from_queue(player_id)
            self._logger.info(
                "Player queue timeout",
                player_id=str(player_id),
                pool_type=queue_state.pool_type.value,
                wait_time_seconds=int(wait_seconds),
            )
            return MatchmakingResult(
                status=MatchmakingStatus.EXPIRED,
                player_id=player_id,
                wait_time_seconds=int(wait_seconds),
                pool_type=queue_state.pool_type,
                message="Queue timeout exceeded",
            )

        # 3. Expand ELO range if needed
        await self._maybe_expand_elo_range(player_id, queue_state)

        # Refresh state after potential expansion
        queue_state = await self._queue_repo.get_player_queue_state(player_id)
        if queue_state is None:
            return MatchmakingResult(
                status=MatchmakingStatus.NOT_IN_QUEUE,
                player_id=player_id,
                wait_time_seconds=int(wait_seconds),
                pool_type=PoolType.MIXED,
                message="Player no longer in queue",
            )

        # 4. Find opponents in range
        opponents = await self._queue_repo.find_opponents_in_range(
            pool_type=queue_state.pool_type,
            min_elo=queue_state.current_min_elo,
            max_elo=queue_state.current_max_elo,
            exclude_player_id=player_id,
            limit=_MATCH_OPPONENT_SEARCH_LIMIT,
        )

        if not opponents:
            # Bot fallback: if human has waited long enough, match against a pool bot.
            if wait_seconds >= self._bot_fallback_seconds:
                bot_result = await self._try_bot_fallback(
                    player_id,
                    queue_state,
                    wait_seconds,
                )
                if bot_result is not None:
                    return bot_result

            self._logger.debug(
                "No opponent found",
                player_id=str(player_id),
                elo_rating=queue_state.elo_rating,
                elo_range=(queue_state.current_min_elo, queue_state.current_max_elo),
                potential_count=0,
            )
            return MatchmakingResult(
                status=MatchmakingStatus.SEARCHING,
                player_id=player_id,
                wait_time_seconds=int(wait_seconds),
                pool_type=queue_state.pool_type,
                message="Searching for opponent",
            )

        # 5. Try to match with best opponent (FIFO, then closest ELO)
        for opponent_id, opponent_elo in opponents:
            match_result = await self._try_create_match(
                player_id=player_id,
                player_elo=queue_state.elo_rating,
                opponent_id=opponent_id,
                opponent_elo=opponent_elo,
                pool_type=queue_state.pool_type,
                wait_seconds=wait_seconds,
            )
            if match_result is not None:
                return match_result

        # 6. All opponents were taken
        return MatchmakingResult(
            status=MatchmakingStatus.SEARCHING,
            player_id=player_id,
            wait_time_seconds=int(wait_seconds),
            pool_type=queue_state.pool_type,
            message="Opponent selection in progress",
        )

    async def process_queue(self, pool_type: PoolType) -> list[MatchmakingResult]:
        """Process all players in a queue, attempting to create matches.

        Called periodically by a background worker. Processes players
        in FIFO order, expanding ranges and creating matches as possible.
        """
        results: list[MatchmakingResult] = []

        # 1. Get all queued players, ordered by join time (FIFO)
        players = await self._queue_repo.get_all_queued_players(pool_type)

        # 2. Track matched players to avoid double-processing
        matched_ids: set[PlayerId] = set()

        # 3. Process each player
        for entry in players:
            if entry.player_id in matched_ids:
                continue

            # 4. Expand range if needed
            await self._maybe_expand_elo_range(entry.player_id, entry)

            # Re-read state after potential expansion
            refreshed = await self._queue_repo.get_player_queue_state(entry.player_id)
            if refreshed is None:
                continue
            entry = refreshed

            # 5. Find opponents
            opponents = await self._queue_repo.find_opponents_in_range(
                pool_type=pool_type,
                min_elo=entry.current_min_elo,
                max_elo=entry.current_max_elo,
                exclude_player_id=entry.player_id,
                limit=_MATCH_OPPONENT_SEARCH_LIMIT,
            )

            # 6. Filter out already-matched opponents
            opponents = [(oid, elo) for oid, elo in opponents if oid not in matched_ids]

            if not opponents:
                continue

            # 7. Try to match (FIFO priority)
            now = datetime.now(timezone.utc)
            wait_seconds = (now - entry.joined_at).total_seconds()

            for opponent_id, opponent_elo in opponents:
                if opponent_id in matched_ids:
                    continue

                result = await self._try_create_match(
                    player_id=entry.player_id,
                    player_elo=entry.elo_rating,
                    opponent_id=opponent_id,
                    opponent_elo=opponent_elo,
                    pool_type=pool_type,
                    wait_seconds=wait_seconds,
                )

                if result is not None:
                    results.append(result)
                    matched_ids.add(entry.player_id)
                    matched_ids.add(opponent_id)
                    break

        self._logger.debug(
            "Queue processed",
            pool_type=pool_type.value,
            players_processed=len(players),
            matches_created=len(results),
        )

        return results

    async def cleanup_stale_entries(self) -> int:
        """Remove players who have exceeded queue timeout.

        Returns the count of stale entries removed.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=self._queue_timeout_seconds
        )

        removed = await self._queue_repo.remove_stale_entries(cutoff)

        if removed > 0:
            self._logger.info(
                "Stale entries cleaned up",
                entries_removed=removed,
            )

        return removed

    async def get_queue_stats(self, pool_type: PoolType | None = None) -> QueueStats:
        """Get statistics about queue status.

        If pool_type is None, returns aggregate stats across all pools.
        """
        total_players = 0
        all_buckets: dict[str, int] = {}
        all_wait_seconds: list[float] = []
        longest_wait = 0
        now = datetime.now(timezone.utc)

        pools = [pool_type] if pool_type is not None else list(PoolType)

        for pt in pools:
            count = await self._queue_repo.get_queue_count(pt)
            total_players += count

            buckets = await self._queue_repo.get_players_by_elo_bucket(pt)
            for label, cnt in buckets.items():
                all_buckets[label] = all_buckets.get(label, 0) + cnt

            # Calculate wait times from all players
            all_players = await self._queue_repo.get_all_queued_players(pt)
            for player_entry in all_players:
                wait = (now - player_entry.joined_at).total_seconds()
                all_wait_seconds.append(wait)
                if int(wait) > longest_wait:
                    longest_wait = int(wait)

        avg_wait = (
            sum(all_wait_seconds) / len(all_wait_seconds) if all_wait_seconds else 0.0
        )

        return QueueStats(
            pool_type=pool_type,
            total_players=total_players,
            players_by_elo_bucket=all_buckets,
            average_wait_seconds=avg_wait,
            longest_wait_seconds=longest_wait,
            matches_created_last_hour=0,
            average_elo_difference=0.0,
        )

    # ========== Private Helpers (delegated to _helpers.py) ==========

    async def _maybe_expand_elo_range(
        self,
        player_id: PlayerId,
        queue_state: QueueEntryData,
    ) -> None:
        """Expand ELO search range based on wait time."""
        await maybe_expand_elo_range(
            player_id,
            queue_state,
            min_wait_before_expansion=self._min_wait_before_expansion,
            elo_range_expansion_interval_seconds=self._elo_range_expansion_interval_seconds,
            max_elo_range=self._max_elo_range,
            elo_range_expansion=self._elo_range_expansion,
            queue_repo=self._queue_repo,
            logger=self._logger,
        )

    async def _try_create_match(
        self,
        player_id: PlayerId,
        player_elo: int,
        opponent_id: PlayerId,
        opponent_elo: int,
        pool_type: PoolType,
        wait_seconds: float,
    ) -> MatchmakingResult | None:
        """Attempt to create a match with the opponent.

        Returns None if the opponent was already taken.
        """
        return await try_create_match(
            player_id=player_id,
            player_elo=player_elo,
            opponent_id=opponent_id,
            opponent_elo=opponent_elo,
            pool_type=pool_type,
            wait_seconds=wait_seconds,
            initial_elo_range=self._initial_elo_range,
            queue_repo=self._queue_repo,
            match_service=self._match_service,
            logger=self._logger,
            errors=self._errors,
        )

    async def _calculate_queue_position(
        self,
        player_id: PlayerId,
        pool_type: PoolType,
    ) -> int:
        """Calculate a player's position in the queue (1-indexed)."""
        return await calculate_queue_position(
            player_id,
            pool_type,
            queue_repo=self._queue_repo,
        )

    async def _estimate_wait_time(
        self,
        elo_rating: int,
        pool_type: PoolType,
    ) -> int | None:
        """Estimate wait time in seconds based on queue density.

        Returns None if estimation is not possible (empty queue).
        """
        return await estimate_wait_time(
            elo_rating,
            pool_type,
            queue_repo=self._queue_repo,
        )

    async def _try_bot_fallback(
        self,
        player_id: PlayerId,
        queue_state: QueueEntryData,
        wait_seconds: float,
    ) -> MatchmakingResult | None:
        """Match a waiting human against a random bot from the pool.

        Returns a MatchmakingResult if a bot match was created, None otherwise.
        """
        import random

        try:
            result = await self._player_service.list_players(  # type: ignore[attr-defined]
                player_type=PlayerType.BOT,
                limit=100,
                offset=0,
            )
            bots = list(result.items) if hasattr(result, "items") else []
            if not bots:
                return None

            # Pick a bot not currently in an active match.
            random.shuffle(bots)
            bot = None
            for candidate in bots:
                active = await self._match_service.get_active_matches(candidate.id)
                if not active:
                    bot = candidate
                    break
            if bot is None:
                return None
            bot_id = bot.id

            # Remove the human from the queue.
            await self._queue_repo.remove_from_queue(player_id)

            # Create match directly.
            match_state = await self._match_service.create_match(
                player1_id=player_id,
                player2_id=PlayerId(bot_id),
            )

            self._logger.info(
                "matchmaking.bot_fallback",
                player_id=str(player_id),
                bot_id=str(bot_id),
                bot_username=bot.username,
                wait_seconds=int(wait_seconds),
            )

            return MatchmakingResult(
                status=MatchmakingStatus.MATCHED,
                player_id=player_id,
                opponent_id=PlayerId(bot_id),
                match_id=MatchId(match_state.match_id),
                wait_time_seconds=int(wait_seconds),
                pool_type=queue_state.pool_type,
                elo_difference=abs(queue_state.elo_rating - bot.elo_rating),
                message="Matched with bot opponent",
            )
        except Exception:
            self._logger.warn(
                "matchmaking.bot_fallback_failed",
                player_id=str(player_id),
            )
            return None
