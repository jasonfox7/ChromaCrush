"""Unit tests for the PlayerService.

Uses mock repositories to test business logic without a real database.
All tests are async using ``pytest-asyncio``.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.core.types.player import EnergyState, Player, PlayerStats, PlayerType
from src.modules.player.dto import EnergyStateUpdate, PlayerUpdate
from src.modules.player.service import PlayerService
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ---------------------------------------------------------------------------
# Mock repositories
# ---------------------------------------------------------------------------


class MockPlayerRepository:
    """In-memory mock for PlayerRepositoryProtocol."""

    def __init__(self) -> None:
        self._players: dict[UUID, Player] = {}
        self._raw_data: dict[UUID, dict] = {}  # extra fields like deleted_at

    async def find_by_id(self, player_id: UUID) -> Player | None:
        player = self._players.get(player_id)
        if player is not None:
            raw = self._raw_data.get(player_id, {})
            if raw.get("deleted_at") is not None:
                return None
        return player

    async def find_by_username(self, username: str) -> Player | None:
        lower = username.lower()
        for pid, player in self._players.items():
            raw = self._raw_data.get(pid, {})
            if raw.get("deleted_at") is not None:
                continue
            if player.username.lower() == lower:
                return player
        return None

    async def create(
        self,
        username: str,
        player_type: PlayerType,
        password_hash: str | None = None,
        apple_user_id: str | None = None,
        auth_provider: str | None = None,
    ) -> Player:
        pid = PlayerId(uuid4())
        player = Player(
            id=pid,
            username=username,
            player_type=player_type,
            elo_rating=1000,
            created_at=datetime.now(timezone.utc),
        )
        self._players[pid] = player
        self._raw_data[pid] = {}
        return player

    async def update(self, player_id: UUID, **changes: object) -> Player:
        player = self._players.get(player_id)
        if player is None:
            msg = f"Player not found: {player_id}"
            raise AppError(
                code="NOT_FOUND_PLAYER",
                message=msg,
                http_status=404,
            )

        # Handle extra raw fields (deleted_at, email, etc.)
        raw = self._raw_data.setdefault(player_id, {})

        for key, value in changes.items():
            if key in ("deleted_at", "email", "username_lower"):
                raw[key] = value
            elif hasattr(player, key):
                # Recreate player dataclass since it's not frozen but
                # we want to simulate update
                object.__setattr__(player, key, value)
            else:
                raw[key] = value

        return player

    async def delete(self, player_id: UUID) -> None:
        if player_id not in self._players:
            msg = f"Player not found: {player_id}"
            raise AppError(
                code="NOT_FOUND_PLAYER",
                message=msg,
                http_status=404,
            )
        del self._players[player_id]
        self._raw_data.pop(player_id, None)

    async def list_players(
        self,
        player_type: PlayerType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Player], int]:
        items = []
        for pid, player in self._players.items():
            raw = self._raw_data.get(pid, {})
            if raw.get("deleted_at") is not None:
                continue
            if player_type is not None and player.player_type != player_type:
                continue
            items.append(player)
        total = len(items)
        return items[offset : offset + limit], total


class MockPlayerStatsRepository:
    """In-memory mock for PlayerStatsRepositoryProtocol."""

    def __init__(self) -> None:
        self._stats: dict[UUID, PlayerStats] = {}

    async def find_by_player_id(self, player_id: UUID) -> PlayerStats | None:
        return self._stats.get(player_id)

    async def create(self, player_id: UUID) -> PlayerStats:
        stats = PlayerStats(player_id=PlayerId(player_id))
        self._stats[player_id] = stats
        return stats

    async def update(self, player_id: UUID, **changes: object) -> PlayerStats:
        stats = self._stats.get(player_id)
        if stats is None:
            msg = f"Player stats not found: {player_id}"
            raise AppError(
                code="NOT_FOUND_PLAYER",
                message=msg,
                http_status=404,
            )

        for key, value in changes.items():
            if hasattr(stats, key):
                object.__setattr__(stats, key, value)

        return stats


class MockEnergyStateRepository:
    """In-memory mock for EnergyStateRepositoryProtocol."""

    def __init__(self) -> None:
        self._states: dict[UUID, EnergyState] = {}

    async def find_by_player_id(self, player_id: UUID) -> EnergyState | None:
        return self._states.get(player_id)

    async def create(
        self,
        player_id: UUID,
        hearts: int,
        max_hearts: int,
    ) -> EnergyState:
        state = EnergyState(
            player_id=PlayerId(player_id),
            hearts=hearts,
            max_hearts=max_hearts,
            last_regen_at=datetime.now(timezone.utc),
        )
        self._states[player_id] = state
        return state

    async def update(self, player_id: UUID, **changes: object) -> EnergyState:
        state = self._states.get(player_id)
        if state is None:
            msg = f"Energy state not found: {player_id}"
            raise AppError(
                code="NOT_FOUND_PLAYER",
                message=msg,
                http_status=404,
            )

        for key, value in changes.items():
            if hasattr(state, key):
                object.__setattr__(state, key, value)

        return state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config() -> MockConfigService:
    return MockConfigService()


@pytest.fixture
def mock_logger() -> MockLogService:
    return MockLogService()


@pytest.fixture
def mock_errors(mock_logger: MockLogService) -> MockErrorService:
    return MockErrorService(mock_logger)


@pytest.fixture
def player_repo() -> MockPlayerRepository:
    return MockPlayerRepository()


@pytest.fixture
def stats_repo() -> MockPlayerStatsRepository:
    return MockPlayerStatsRepository()


@pytest.fixture
def energy_repo() -> MockEnergyStateRepository:
    return MockEnergyStateRepository()


@pytest.fixture
def player_service(
    mock_config: MockConfigService,
    mock_logger: MockLogService,
    mock_errors: MockErrorService,
    player_repo: MockPlayerRepository,
    stats_repo: MockPlayerStatsRepository,
    energy_repo: MockEnergyStateRepository,
) -> PlayerService:
    return PlayerService(
        config=mock_config,
        logger=mock_logger,
        errors=mock_errors,
        player_repo=player_repo,
        stats_repo=stats_repo,
        energy_repo=energy_repo,
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _create_test_player(
    service: PlayerService,
    username: str = "testplayer",
    player_type: PlayerType = PlayerType.HUMAN,
) -> Player:
    """Helper to create a player through the service."""
    return await service.create_player(
        username=username,
        player_type=player_type,
    )


# ---------------------------------------------------------------------------
# Tests — Player Account Operations
# ---------------------------------------------------------------------------


class TestCreatePlayer:
    """Tests for ``PlayerService.create_player``."""

    @pytest.mark.asyncio
    async def test_create_player_human(self, player_service: PlayerService) -> None:
        """Human player creation succeeds with valid username."""
        player = await player_service.create_player(
            username="hero123",
            player_type=PlayerType.HUMAN,
        )

        assert player.username == "hero123"
        assert player.player_type == PlayerType.HUMAN
        assert player.elo_rating == 1000
        assert player.id is not None

    @pytest.mark.asyncio
    async def test_create_player_bot(self, player_service: PlayerService) -> None:
        """Bot player creation succeeds."""
        player = await player_service.create_player(
            username="bot_alpha",
            player_type=PlayerType.BOT,
        )

        assert player.username == "bot_alpha"
        assert player.player_type == PlayerType.BOT

    @pytest.mark.asyncio
    async def test_create_player_bot_with_password_rejected(
        self, player_service: PlayerService
    ) -> None:
        """Bot player with password_hash is rejected."""
        with pytest.raises(AppError) as exc_info:
            await player_service.create_player(
                username="bad_bot",
                player_type=PlayerType.BOT,
                password_hash="some_hash",
            )
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_create_player_duplicate_username(
        self, player_service: PlayerService
    ) -> None:
        """Duplicate username (case-insensitive) raises conflict error."""
        await player_service.create_player(
            username="UniquePlayer",
            player_type=PlayerType.HUMAN,
        )

        with pytest.raises(AppError) as exc_info:
            await player_service.create_player(
                username="uniqueplayer",  # Same name, different case
                player_type=PlayerType.HUMAN,
            )
        assert exc_info.value.code == "CONFLICT_USERNAME_TAKEN"

    @pytest.mark.asyncio
    async def test_create_player_invalid_username(
        self, player_service: PlayerService
    ) -> None:
        """Invalid username format raises validation error."""
        with pytest.raises(AppError) as exc_info:
            await player_service.create_player(
                username="a!",
                player_type=PlayerType.HUMAN,
            )
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_create_player_initializes_stats(
        self,
        player_service: PlayerService,
        stats_repo: MockPlayerStatsRepository,
    ) -> None:
        """Creating a player also creates stats record."""
        player = await player_service.create_player(
            username="statsplayer",
            player_type=PlayerType.HUMAN,
        )

        stats = await stats_repo.find_by_player_id(player.id)
        assert stats is not None
        assert stats.total_matches == 0
        assert stats.wins == 0

    @pytest.mark.asyncio
    async def test_create_player_initializes_energy(
        self,
        player_service: PlayerService,
        energy_repo: MockEnergyStateRepository,
    ) -> None:
        """Creating a player also creates energy state record."""
        player = await player_service.create_player(
            username="energyplayer",
            player_type=PlayerType.HUMAN,
        )

        energy = await energy_repo.find_by_player_id(player.id)
        assert energy is not None
        assert energy.hearts == 5
        assert energy.max_hearts == 5


class TestGetPlayer:
    """Tests for ``PlayerService.get_player``."""

    @pytest.mark.asyncio
    async def test_get_player_found(self, player_service: PlayerService) -> None:
        """Existing player is returned successfully."""
        created = await _create_test_player(player_service, "findme")
        found = await player_service.get_player(created.id)
        assert found.id == created.id
        assert found.username == "findme"

    @pytest.mark.asyncio
    async def test_get_player_not_found(self, player_service: PlayerService) -> None:
        """Non-existent player raises NOT_FOUND_PLAYER."""
        fake_id = PlayerId(uuid4())
        with pytest.raises(AppError) as exc_info:
            await player_service.get_player(fake_id)
        assert exc_info.value.code == "NOT_FOUND_PLAYER"


class TestGetPlayerByUsername:
    """Tests for ``PlayerService.get_player_by_username``."""

    @pytest.mark.asyncio
    async def test_found(self, player_service: PlayerService) -> None:
        """Existing player found by username."""
        await _create_test_player(player_service, "findbyname")
        found = await player_service.get_player_by_username("findbyname")
        assert found is not None
        assert found.username == "findbyname"

    @pytest.mark.asyncio
    async def test_not_found(self, player_service: PlayerService) -> None:
        """Non-existent username returns None."""
        found = await player_service.get_player_by_username("nonexistent")
        assert found is None


class TestUpdatePlayer:
    """Tests for ``PlayerService.update_player``."""

    @pytest.mark.asyncio
    async def test_update_username(self, player_service: PlayerService) -> None:
        """Username can be updated."""
        player = await _create_test_player(player_service, "oldname")
        updated = await player_service.update_player(
            player.id,
            PlayerUpdate(username="newname"),
        )
        assert updated.username == "newname"

    @pytest.mark.asyncio
    async def test_update_no_changes(self, player_service: PlayerService) -> None:
        """Update with no changes returns original player."""
        player = await _create_test_player(player_service, "nochange")
        updated = await player_service.update_player(
            player.id,
            PlayerUpdate(),
        )
        assert updated.username == "nochange"


class TestSoftDeletePlayer:
    """Tests for ``PlayerService.soft_delete_player``."""

    @pytest.mark.asyncio
    async def test_soft_delete(self, player_service: PlayerService) -> None:
        """Soft-deleted player cannot be found by get_player."""
        player = await _create_test_player(player_service, "deleteme")
        await player_service.soft_delete_player(player.id)

        with pytest.raises(AppError) as exc_info:
            await player_service.get_player(player.id)
        assert exc_info.value.code == "NOT_FOUND_PLAYER"


class TestListPlayers:
    """Tests for ``PlayerService.list_players``."""

    @pytest.mark.asyncio
    async def test_list_all(self, player_service: PlayerService) -> None:
        """Lists all active players."""
        await _create_test_player(player_service, "list_one")
        await _create_test_player(player_service, "list_two")

        result = await player_service.list_players()
        assert result.total == 2
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_list_with_type_filter(self, player_service: PlayerService) -> None:
        """Filter by player type."""
        await _create_test_player(player_service, "human1", PlayerType.HUMAN)
        await _create_test_player(player_service, "bot1", PlayerType.BOT)

        result = await player_service.list_players(player_type=PlayerType.BOT)
        assert result.total == 1
        assert result.items[0].player_type == PlayerType.BOT

    @pytest.mark.asyncio
    async def test_list_invalid_limit(self, player_service: PlayerService) -> None:
        """Limit out of range raises validation error."""
        with pytest.raises(AppError) as exc_info:
            await player_service.list_players(limit=200)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ---------------------------------------------------------------------------
# Tests — ELO Rating Operations
# ---------------------------------------------------------------------------


class TestEloOperations:
    """Tests for ELO-related service methods."""

    @pytest.mark.asyncio
    async def test_get_elo(self, player_service: PlayerService) -> None:
        """Get ELO returns the player's rating."""
        player = await _create_test_player(player_service, "elocheck")
        elo = await player_service.get_elo(player.id)
        assert elo == 1000

    @pytest.mark.asyncio
    async def test_update_elo(self, player_service: PlayerService) -> None:
        """ELO can be updated to a new valid value."""
        player = await _create_test_player(player_service, "eloupdate")
        updated = await player_service.update_elo(player.id, 1200)
        assert updated.elo_rating == 1200

    @pytest.mark.asyncio
    async def test_update_elo_negative_rejected(
        self, player_service: PlayerService
    ) -> None:
        """Negative ELO is rejected."""
        player = await _create_test_player(player_service, "eloneg")
        with pytest.raises(AppError) as exc_info:
            await player_service.update_elo(player.id, -100)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_calculate_elo_change(self, player_service: PlayerService) -> None:
        """Calculate ELO change returns expected deltas."""
        p1 = await _create_test_player(player_service, "elop1")
        p2 = await _create_test_player(player_service, "elop2")

        winner_change, loser_change = await player_service.calculate_elo_change(
            p1.id, p2.id, is_draw=False
        )

        # Equal ratings: winner +16, loser -16 (k=32)
        assert winner_change == 16
        assert loser_change == -16

    @pytest.mark.asyncio
    async def test_calculate_elo_change_same_player(
        self, player_service: PlayerService
    ) -> None:
        """Calculating ELO against self is rejected."""
        p = await _create_test_player(player_service, "eloself")
        with pytest.raises(AppError) as exc_info:
            await player_service.calculate_elo_change(p.id, p.id)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ---------------------------------------------------------------------------
# Tests — Statistics Operations
# ---------------------------------------------------------------------------


class TestStatsOperations:
    """Tests for statistics-related service methods."""

    @pytest.mark.asyncio
    async def test_get_stats(self, player_service: PlayerService) -> None:
        """Stats for new player are all zeros."""
        player = await _create_test_player(player_service, "statsguy")
        stats = await player_service.get_stats(player.id)

        assert stats.total_matches == 0
        assert stats.wins == 0
        assert stats.losses == 0
        assert stats.draws == 0
        assert stats.win_rate == 0.0

    @pytest.mark.asyncio
    async def test_record_match_result_win(self, player_service: PlayerService) -> None:
        """Recording a win increments wins and total_matches."""
        player = await _create_test_player(player_service, "winner")
        stats = await player_service.record_match_result(
            player_id=player.id,
            won=True,
            is_draw=False,
            score=500,
            longest_chain=4,
            gems_matched=50,
        )

        assert stats.total_matches == 1
        assert stats.wins == 1
        assert stats.losses == 0
        assert stats.highest_score == 500
        assert stats.longest_chain == 4
        assert stats.total_gems_matched == 50

    @pytest.mark.asyncio
    async def test_record_match_result_loss(
        self, player_service: PlayerService
    ) -> None:
        """Recording a loss increments losses and total_matches."""
        player = await _create_test_player(player_service, "loser")
        stats = await player_service.record_match_result(
            player_id=player.id,
            won=False,
            is_draw=False,
            score=200,
            longest_chain=2,
            gems_matched=20,
        )

        assert stats.total_matches == 1
        assert stats.losses == 1
        assert stats.wins == 0

    @pytest.mark.asyncio
    async def test_record_match_result_draw(
        self, player_service: PlayerService
    ) -> None:
        """Recording a draw increments draws and total_matches."""
        player = await _create_test_player(player_service, "drawer")
        stats = await player_service.record_match_result(
            player_id=player.id,
            won=False,
            is_draw=True,
            score=300,
            longest_chain=3,
            gems_matched=30,
        )

        assert stats.total_matches == 1
        assert stats.draws == 1
        assert stats.wins == 0
        assert stats.losses == 0

    @pytest.mark.asyncio
    async def test_record_match_result_updates_highest_score(
        self, player_service: PlayerService
    ) -> None:
        """Highest score is updated only when new score exceeds it."""
        player = await _create_test_player(player_service, "scorer")

        await player_service.record_match_result(
            player.id,
            won=True,
            is_draw=False,
            score=500,
            longest_chain=3,
            gems_matched=40,
        )
        stats = await player_service.record_match_result(
            player.id,
            won=True,
            is_draw=False,
            score=300,
            longest_chain=2,
            gems_matched=30,
        )

        # Highest score should still be 500
        assert stats.highest_score == 500

    @pytest.mark.asyncio
    async def test_record_match_result_accumulates_gems(
        self, player_service: PlayerService
    ) -> None:
        """Total gems matched accumulates across matches."""
        player = await _create_test_player(player_service, "gemmaster")

        await player_service.record_match_result(
            player.id,
            won=True,
            is_draw=False,
            score=100,
            longest_chain=2,
            gems_matched=25,
        )
        stats = await player_service.record_match_result(
            player.id,
            won=False,
            is_draw=False,
            score=80,
            longest_chain=1,
            gems_matched=20,
        )

        assert stats.total_gems_matched == 45


# ---------------------------------------------------------------------------
# Tests — Energy State
# ---------------------------------------------------------------------------


class TestEnergyStateOperations:
    """Tests for energy state data access methods."""

    @pytest.mark.asyncio
    async def test_get_energy_state(self, player_service: PlayerService) -> None:
        """Energy state is initialized with create_player."""
        player = await _create_test_player(player_service, "energyget")
        energy = await player_service.get_energy_state(player.id)

        assert energy.hearts == 5
        assert energy.max_hearts == 5
        assert energy.daily_streak == 0

    @pytest.mark.asyncio
    async def test_update_energy_state(self, player_service: PlayerService) -> None:
        """Energy state fields can be updated."""
        player = await _create_test_player(player_service, "energyupd")
        updated = await player_service.update_energy_state(
            player.id,
            EnergyStateUpdate(hearts=3, daily_streak=5),
        )

        assert updated.hearts == 3
        assert updated.daily_streak == 5

    @pytest.mark.asyncio
    async def test_update_energy_state_negative_hearts_rejected(
        self, player_service: PlayerService
    ) -> None:
        """Negative hearts value is rejected."""
        player = await _create_test_player(player_service, "energyneg")
        with pytest.raises(AppError) as exc_info:
            await player_service.update_energy_state(
                player.id,
                EnergyStateUpdate(hearts=-1),
            )
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_update_energy_state_over_max_rejected(
        self, player_service: PlayerService
    ) -> None:
        """Hearts exceeding max_hearts is rejected."""
        player = await _create_test_player(player_service, "energymax")
        with pytest.raises(AppError) as exc_info:
            await player_service.update_energy_state(
                player.id,
                EnergyStateUpdate(hearts=99),
            )
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_update_energy_state_no_changes(
        self, player_service: PlayerService
    ) -> None:
        """Update with no changes returns current state."""
        player = await _create_test_player(player_service, "energynoop")
        energy = await player_service.update_energy_state(
            player.id,
            EnergyStateUpdate(),
        )
        assert energy.hearts == 5

    @pytest.mark.asyncio
    async def test_initialize_energy_state(self, player_service: PlayerService) -> None:
        """Initialize energy state creates with configured max hearts."""
        # create_player already calls initialize, so test via get
        player = await _create_test_player(player_service, "energyinit")
        energy = await player_service.get_energy_state(player.id)
        assert energy.hearts == 5
        assert energy.max_hearts == 5
