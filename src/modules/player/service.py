"""Player service implementation.

Fully async service managing player accounts, ELO ratings, statistics,
and energy state data ownership. All dependencies arrive via ``__init__``
injection; no direct imports of core services or environment access.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.types.game import PlayerId
from src.core.types.player import EnergyState, Player, PlayerStats, PlayerType
from src.modules.player.dto import EnergyStateUpdate, PaginatedResult, PlayerUpdate
from src.modules.player.elo import calculate_elo_change as _calc_elo
from src.modules.player.elo import calculate_expected_score as _calc_expected
from src.modules.player.validation import validate_username

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.energy_state_repository import EnergyStateRepositoryProtocol
    from src.data.protocols.player_repository import PlayerRepositoryProtocol
    from src.data.protocols.player_stats_repository import PlayerStatsRepositoryProtocol


class PlayerService:
    """Concrete implementation of ``PlayerServiceProtocol``.

    Manages player accounts, ELO ratings, statistics, and energy state.
    All public methods are ``async def`` as they involve database operations.

    Args:
        config: Configuration service for reading settings.
        logger: Structured logging service.
        errors: Error factory service.
        player_repo: Repository for player CRUD operations.
        stats_repo: Repository for player statistics.
        energy_repo: Repository for energy state data.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_repo: PlayerRepositoryProtocol,
        stats_repo: PlayerStatsRepositoryProtocol,
        energy_repo: EnergyStateRepositoryProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._player_repo = player_repo
        self._stats_repo = stats_repo
        self._energy_repo = energy_repo

        # Cache configuration values read at init time
        self._elo_initial: int = config.get("matchmaking.elo_initial", 1000)
        self._elo_k_factor: int = config.get("matchmaking.elo_k_factor", 32)
        self._max_hearts: int = config.get("energy.max_hearts", 7)
        self._username_min_length: int = config.get("player.username_min_length", 3)
        self._username_max_length: int = config.get("player.username_max_length", 32)
        self._username_pattern: str = config.get(
            "player.username_pattern", r"^[a-zA-Z0-9_]+$"
        )

    # ========== Player Account Operations ==========

    async def create_player(
        self,
        username: str,
        player_type: PlayerType,
        password_hash: str | None = None,
        email: str | None = None,
        apple_user_id: str | None = None,
        auth_provider: str | None = None,
    ) -> Player:
        """Create a new player account.

        Validates username, checks uniqueness, and atomically creates the
        player record along with associated stats and energy state.

        Args:
            username: Unique username (case-insensitive).
            player_type: PlayerType.HUMAN or PlayerType.BOT.
            password_hash: Optional for humans (auth module handles real auth).
                Must be None for bots.
            email: Optional email for humans, None for bots.
            apple_user_id: Apple Sign-In ``sub`` claim (optional).
            auth_provider: Authentication method (``"password"``, ``"apple"``).

        Returns:
            Created Player entity.

        Raises:
            VALIDATION_INVALID_INPUT: If username format is invalid or bot has password_hash.
            CONFLICT_USERNAME_TAKEN: If username already exists (case-insensitive).
        """
        # Validate: bots must not have a password_hash
        if player_type == PlayerType.BOT and password_hash is not None:
            raise self._errors.validation(
                "Bot accounts must not have a password",
                code="VALIDATION_INVALID_INPUT",
                field="password_hash",
            )

        # Validate username format
        is_valid, error_msg = validate_username(
            username,
            self._username_min_length,
            self._username_max_length,
            self._username_pattern,
        )
        if not is_valid:
            raise self._errors.validation(
                error_msg,
                code="VALIDATION_INVALID_INPUT",
                field="username",
                value=username,
            )

        # Check username uniqueness (case-insensitive)
        existing = await self._player_repo.find_by_username(username)
        if existing is not None:
            self._logger.warn(
                "Username conflict",
                username=username,
                existing_player_id=str(existing.id),
            )
            raise self._errors.conflict(
                "Username already exists",
                code="CONFLICT_USERNAME_TAKEN",
                username=username,
            )

        # Create player
        player = await self._player_repo.create(
            username=username,
            player_type=player_type,
            password_hash=password_hash,
            apple_user_id=apple_user_id,
            auth_provider=auth_provider,
        )

        # Create associated stats record
        await self._stats_repo.create(player.id)

        # Initialize energy state
        await self._energy_repo.create(
            player_id=player.id,
            hearts=self._max_hearts,
            max_hearts=self._max_hearts,
        )

        self._logger.info(
            "Player created",
            player_id=str(player.id),
            username=player.username,
            player_type=player_type.value,
        )

        return player

    async def get_player(
        self,
        player_id: PlayerId,
    ) -> Player:
        """Get player by ID.

        Args:
            player_id: The player's unique identifier.

        Returns:
            Player entity.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist or is soft-deleted.
        """
        player = await self._player_repo.find_by_id(player_id)
        if player is None:
            raise self._errors.not_found(
                "Player not found",
                code="NOT_FOUND_PLAYER",
                player_id=str(player_id),
            )
        return player

    async def get_player_by_username(
        self,
        username: str,
    ) -> Player | None:
        """Get player by username (case-insensitive lookup).

        Args:
            username: The username to look up.

        Returns:
            Player if found and not soft-deleted, None otherwise.
        """
        return await self._player_repo.find_by_username(username)

    async def get_player_by_apple_id(
        self,
        apple_user_id: str,
    ) -> Player | None:
        """Get player by Apple user ID.

        Args:
            apple_user_id: The Apple ``sub`` claim.

        Returns:
            Player if found, None otherwise.
        """
        return await self._player_repo.find_by_apple_user_id(apple_user_id)

    async def update_player(
        self,
        player_id: PlayerId,
        updates: PlayerUpdate,
    ) -> Player:
        """Update player profile fields.

        Args:
            player_id: The player to update.
            updates: Fields to update (username, email).

        Returns:
            Updated Player entity.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If new username format is invalid.
            CONFLICT_USERNAME_TAKEN: If new username conflicts with existing.
        """
        # Verify player exists
        player = await self.get_player(player_id)

        changes: dict[str, object] = {}

        if updates.username is not None:
            # Validate new username format
            is_valid, error_msg = validate_username(
                updates.username,
                self._username_min_length,
                self._username_max_length,
                self._username_pattern,
            )
            if not is_valid:
                raise self._errors.validation(
                    error_msg,
                    code="VALIDATION_INVALID_INPUT",
                    field="username",
                    value=updates.username,
                )

            # Check uniqueness only if username is actually changing
            if updates.username.lower() != player.username.lower():
                existing = await self._player_repo.find_by_username(updates.username)
                if existing is not None:
                    self._logger.warn(
                        "Username conflict",
                        username=updates.username,
                        existing_player_id=str(existing.id),
                    )
                    raise self._errors.conflict(
                        "Username already exists",
                        code="CONFLICT_USERNAME_TAKEN",
                        username=updates.username,
                    )

            changes["username"] = updates.username

        if updates.email is not None:
            changes["email"] = updates.email

        if not changes:
            return player

        updated_player = await self._player_repo.update(player_id, **changes)

        changed_fields = list(changes.keys())
        self._logger.info(
            "Player updated",
            player_id=str(player_id),
            changed_fields=str(changed_fields),
        )

        return updated_player

    async def soft_delete_player(
        self,
        player_id: PlayerId,
    ) -> None:
        """Soft-delete a player account.

        Sets deleted_at timestamp. Username is anonymized by appending the
        deletion timestamp to prevent conflicts with future registrations.

        Args:
            player_id: The player to delete.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist or already deleted.
        """
        player = await self.get_player(player_id)

        now = datetime.now(timezone.utc)
        deleted_username = f"{player.username}_deleted_{int(now.timestamp())}"

        await self._player_repo.update(
            player_id,
            username=deleted_username,
            deleted_at=now,
        )

        self._logger.info(
            "Player soft-deleted",
            player_id=str(player_id),
        )

    async def list_players(
        self,
        player_type: PlayerType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[Player]:
        """List players with optional filtering.

        Args:
            player_type: Filter by human or bot (None for all).
            limit: Maximum results (1-100, default 50).
            offset: Pagination offset.

        Returns:
            PaginatedResult containing players and pagination metadata.

        Raises:
            VALIDATION_INVALID_INPUT: If limit out of range.
        """
        if limit < 1 or limit > 100:
            raise self._errors.validation(
                "Limit must be between 1 and 100",
                code="VALIDATION_INVALID_INPUT",
                field="limit",
                value=limit,
            )

        items, total = await self._player_repo.list_players(
            player_type=player_type,
            limit=limit,
            offset=offset,
        )

        return PaginatedResult(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_high_score_leaderboard(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[tuple[PlayerStats, str, int]]:
        """Get players ranked by highest single-match score.

        Returns:
            PaginatedResult of (PlayerStats, username, elo_rating) tuples.
        """
        if limit < 1 or limit > 100:
            raise self._errors.validation(
                "Limit must be between 1 and 100",
                code="VALIDATION_INVALID_INPUT",
                field="limit",
                value=limit,
            )

        items, total = await self._stats_repo.list_by_highest_score(
            limit=limit, offset=offset
        )

        return PaginatedResult(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    # ========== ELO Rating Operations ==========

    async def get_elo(
        self,
        player_id: PlayerId,
    ) -> int:
        """Get player's current ELO rating.

        Args:
            player_id: The player.

        Returns:
            Current ELO rating integer.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        player = await self.get_player(player_id)
        return player.elo_rating

    async def update_elo(
        self,
        player_id: PlayerId,
        new_rating: int,
    ) -> Player:
        """Update player's ELO rating.

        Args:
            player_id: The player to update.
            new_rating: New ELO value (must be >= 0).

        Returns:
            Updated Player entity.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If new_rating < 0.
        """
        if new_rating < 0:
            raise self._errors.validation(
                "ELO rating cannot be negative",
                code="VALIDATION_INVALID_INPUT",
                field="elo_rating",
                value=new_rating,
            )

        player = await self.get_player(player_id)
        old_rating = player.elo_rating

        updated_player = await self._player_repo.update(
            player_id, elo_rating=new_rating
        )

        delta = new_rating - old_rating
        self._logger.info(
            "ELO updated",
            player_id=str(player_id),
            old_rating=old_rating,
            new_rating=new_rating,
            delta=delta,
        )

        return updated_player

    async def calculate_elo_change(
        self,
        winner_id: PlayerId,
        loser_id: PlayerId,
        is_draw: bool = False,
    ) -> tuple[int, int]:
        """Calculate ELO changes for a match outcome (does NOT persist).

        Args:
            winner_id: The winning player (or either player if draw).
            loser_id: The losing player (or other player if draw).
            is_draw: Whether the match was a draw.

        Returns:
            Tuple of (winner_elo_change, loser_elo_change).

        Raises:
            NOT_FOUND_PLAYER: If either player doesn't exist.
            VALIDATION_INVALID_INPUT: If both IDs are the same player.
        """
        if winner_id == loser_id:
            raise self._errors.validation(
                "Cannot calculate ELO change for a player against themselves",
                code="VALIDATION_INVALID_INPUT",
                field="player_ids",
            )

        winner = await self.get_player(winner_id)
        loser = await self.get_player(loser_id)

        return _calc_elo(
            winner_rating=winner.elo_rating,
            loser_rating=loser.elo_rating,
            k_factor=self._elo_k_factor,
            is_draw=is_draw,
        )

    # ========== Statistics Operations ==========

    async def get_stats(
        self,
        player_id: PlayerId,
    ) -> PlayerStats:
        """Get player statistics.

        Args:
            player_id: The player.

        Returns:
            PlayerStats aggregate.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        # Ensure the player exists first
        await self.get_player(player_id)

        stats = await self._stats_repo.find_by_player_id(player_id)
        if stats is None:
            raise self._errors.not_found(
                "Player stats not found",
                code="NOT_FOUND_PLAYER",
                player_id=str(player_id),
            )
        return stats

    async def record_match_result(
        self,
        player_id: PlayerId,
        won: bool,
        is_draw: bool,
        score: int,
        longest_chain: int,
        gems_matched: int,
    ) -> PlayerStats:
        """Record a match result in player statistics.

        Args:
            player_id: The player.
            won: Whether player won (ignored if is_draw).
            is_draw: Whether match was a draw.
            score: Player's final score in the match.
            longest_chain: Longest cascade chain achieved.
            gems_matched: Total gems matched in the match.

        Returns:
            Updated PlayerStats.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        # Ensure the player exists
        await self.get_player(player_id)

        current_stats = await self._stats_repo.find_by_player_id(player_id)
        if current_stats is None:
            raise self._errors.not_found(
                "Player stats not found",
                code="NOT_FOUND_PLAYER",
                player_id=str(player_id),
            )

        # Build the update
        changes: dict[str, object] = {
            "total_matches": current_stats.total_matches + 1,
            "total_gems_matched": current_stats.total_gems_matched + gems_matched,
        }

        if is_draw:
            changes["draws"] = current_stats.draws + 1
            result_label = "draw"
        elif won:
            changes["wins"] = current_stats.wins + 1
            result_label = "win"
        else:
            changes["losses"] = current_stats.losses + 1
            result_label = "loss"

        if score > current_stats.highest_score:
            changes["highest_score"] = score

        if longest_chain > current_stats.longest_chain:
            changes["longest_chain"] = longest_chain

        updated_stats = await self._stats_repo.update(player_id, **changes)

        self._logger.info(
            "Match result recorded",
            player_id=str(player_id),
            result=result_label,
            score=score,
        )

        return updated_stats

    # ========== Energy State Data Access ==========

    async def get_energy_state(
        self,
        player_id: PlayerId,
    ) -> EnergyState:
        """Get player's energy state.

        Args:
            player_id: The player.

        Returns:
            Current EnergyState.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        await self.get_player(player_id)

        energy = await self._energy_repo.find_by_player_id(player_id)
        if energy is None:
            raise self._errors.not_found(
                "Energy state not found",
                code="NOT_FOUND_PLAYER",
                player_id=str(player_id),
            )
        return energy

    async def update_energy_state(
        self,
        player_id: PlayerId,
        energy_update: EnergyStateUpdate,
    ) -> EnergyState:
        """Update player's energy state.

        Args:
            player_id: The player.
            energy_update: Fields to update.

        Returns:
            Updated EnergyState.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If hearts < 0 or > max_hearts.
        """
        current_energy = await self.get_energy_state(player_id)

        changes: dict[str, object] = {}

        if energy_update.hearts is not None:
            if energy_update.hearts < 0:
                raise self._errors.validation(
                    "Hearts cannot be negative",
                    code="VALIDATION_INVALID_INPUT",
                    field="hearts",
                    value=energy_update.hearts,
                )
            if energy_update.hearts > current_energy.max_hearts:
                raise self._errors.validation(
                    "Hearts cannot exceed max_hearts",
                    code="VALIDATION_INVALID_INPUT",
                    field="hearts",
                    value=energy_update.hearts,
                    max_hearts=current_energy.max_hearts,
                )
            changes["hearts"] = energy_update.hearts

        if energy_update.last_regen_at is not None:
            changes["last_regen_at"] = energy_update.last_regen_at

        if energy_update.daily_streak is not None:
            changes["daily_streak"] = energy_update.daily_streak

        if energy_update.last_login_date is not None:
            changes["last_login_date"] = energy_update.last_login_date

        if not changes:
            return current_energy

        updated_energy = await self._energy_repo.update(player_id, **changes)

        self._logger.debug(
            "Energy state updated",
            player_id=str(player_id),
            changes=str(list(changes.keys())),
        )

        return updated_energy

    async def initialize_energy_state(
        self,
        player_id: PlayerId,
    ) -> EnergyState:
        """Initialize energy state for new player.

        Args:
            player_id: The newly created player.

        Returns:
            Initialized EnergyState.
        """
        return await self._energy_repo.create(
            player_id=player_id,
            hearts=self._max_hearts,
            max_hearts=self._max_hearts,
        )
