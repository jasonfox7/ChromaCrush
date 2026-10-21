"""Unit tests for the VaultService.

Uses mock repositories to test business logic without a real database.
All tests are async using ``pytest-asyncio``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from src.core.errors import AppError
from src.core.types.game import ArtifactId, PlayerId
from src.core.types.player import Player, PlayerType
from src.modules.vault.dto import ArtifactRarity
from src.modules.vault.service import VaultService
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ---------------------------------------------------------------------------
# Mock data classes for repository records
# ---------------------------------------------------------------------------


@dataclass
class FakeArtifactRecord:
    """Minimal vault artifact record for mock repository."""

    id: UUID
    owner_id: UUID
    artifact_type_id: str
    acquired_at: datetime
    source: str
    source_id: str | None
    created_at: datetime
    rarity: str | None = None


@dataclass
class FakeDefinitionRecord:
    """Minimal artifact definition record for mock repository."""

    type_id: str
    name: str
    description: str | None
    rarity: str
    artifact_set: str
    set_position: int
    base_value: int
    image_url: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FakeShieldRecord:
    """Minimal vault shield record for mock repository."""

    player_id: UUID
    activated_at: datetime
    expires_at: datetime
    duration_hours: int


@dataclass
class FakeRaidLogRecord:
    """Minimal raid log record for mock repository."""

    id: UUID
    attacker_id: UUID
    defender_id: UUID
    success: bool
    artifact_id: UUID | None
    artifact_type_id: str | None
    timestamp: datetime


# ---------------------------------------------------------------------------
# Mock repositories
# ---------------------------------------------------------------------------


class MockPlayerService:
    """In-memory mock for PlayerServiceProtocol."""

    def __init__(self) -> None:
        self._players: dict[UUID, Player] = {}

    def add_player(self, player: Player) -> None:
        self._players[player.id] = player

    async def get_player(self, player_id: PlayerId) -> Player:
        player = self._players.get(player_id)
        if player is None:
            raise AppError(
                code="NOT_FOUND_PLAYER",
                message=f"Player not found: {player_id}",
                http_status=404,
            )
        return player


class MockVaultArtifactRepository:
    """In-memory mock for VaultArtifactRepositoryProtocol."""

    def __init__(self) -> None:
        self._artifacts: dict[UUID, FakeArtifactRecord] = {}

    async def find_by_id(self, artifact_id: UUID) -> FakeArtifactRecord | None:
        return self._artifacts.get(artifact_id)

    async def find_by_owner(
        self,
        owner_id: UUID,
        rarity: str | None = None,
        artifact_set: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[FakeArtifactRecord], int]:
        items = [a for a in self._artifacts.values() if a.owner_id == owner_id]
        # Filtering by rarity/set would require definition lookup; skip for mock
        total = len(items)
        return items[offset : offset + limit], total

    async def count_by_owner(self, owner_id: UUID) -> int:
        return sum(1 for a in self._artifacts.values() if a.owner_id == owner_id)

    async def count_by_owner_and_rarity(self, owner_id: UUID) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in self._artifacts.values():
            if a.owner_id == owner_id and a.rarity:
                counts[a.rarity] = counts.get(a.rarity, 0) + 1
        return counts

    async def find_by_owner_and_type(
        self, owner_id: UUID, artifact_type_id: str
    ) -> FakeArtifactRecord | None:
        for a in self._artifacts.values():
            if a.owner_id == owner_id and a.artifact_type_id == artifact_type_id:
                return a
        return None

    async def list_owned_type_ids(
        self, owner_id: UUID, artifact_set: str | None = None
    ) -> list[str]:
        return list(
            {
                a.artifact_type_id
                for a in self._artifacts.values()
                if a.owner_id == owner_id
            }
        )

    async def create(
        self,
        owner_id: UUID,
        artifact_type_id: str,
        source: str,
        source_id: str | None = None,
    ) -> FakeArtifactRecord:
        now = datetime.now(timezone.utc)
        record = FakeArtifactRecord(
            id=uuid4(),
            owner_id=owner_id,
            artifact_type_id=artifact_type_id,
            acquired_at=now,
            source=source,
            source_id=source_id,
            created_at=now,
        )
        self._artifacts[record.id] = record
        return record

    async def update_owner(
        self, artifact_id: UUID, new_owner_id: UUID
    ) -> FakeArtifactRecord:
        record = self._artifacts.get(artifact_id)
        if record is None:
            raise AppError(
                code="NOT_FOUND_ARTIFACT",
                message=f"Artifact not found: {artifact_id}",
                http_status=404,
            )
        record.owner_id = new_owner_id
        return record

    async def delete(self, artifact_id: UUID) -> None:
        if artifact_id not in self._artifacts:
            raise AppError(
                code="NOT_FOUND_ARTIFACT",
                message=f"Artifact not found: {artifact_id}",
                http_status=404,
            )
        del self._artifacts[artifact_id]

    async def get_random_artifact(
        self, owner_id: UUID, exclude_legendary: bool = False
    ) -> FakeArtifactRecord | None:
        items = [a for a in self._artifacts.values() if a.owner_id == owner_id]
        if exclude_legendary:
            items = [a for a in items if a.rarity != "legendary"]
        return items[0] if items else None


class MockArtifactDefinitionRepository:
    """In-memory mock for ArtifactDefinitionRepositoryProtocol."""

    def __init__(self) -> None:
        self._definitions: dict[str, FakeDefinitionRecord] = {}

    def add_definition(self, record: FakeDefinitionRecord) -> None:
        self._definitions[record.type_id] = record

    async def find_by_type_id(self, type_id: str) -> FakeDefinitionRecord | None:
        return self._definitions.get(type_id)

    async def list_all(
        self, rarity: str | None = None, artifact_set: str | None = None
    ) -> list[FakeDefinitionRecord]:
        items = list(self._definitions.values())
        if rarity:
            items = [d for d in items if d.rarity == rarity]
        if artifact_set:
            items = [d for d in items if d.artifact_set == artifact_set]
        return items

    async def list_by_set(self, artifact_set: str) -> list[FakeDefinitionRecord]:
        return [d for d in self._definitions.values() if d.artifact_set == artifact_set]

    async def get_set_type_ids(self, artifact_set: str) -> list[str]:
        return [
            d.type_id
            for d in self._definitions.values()
            if d.artifact_set == artifact_set
        ]

    async def list_all_sets(self) -> list[str]:
        return list({d.artifact_set for d in self._definitions.values()})


class MockVaultShieldRepository:
    """In-memory mock for VaultShieldRepositoryProtocol."""

    def __init__(self) -> None:
        self._shields: dict[UUID, FakeShieldRecord] = {}

    async def find_by_player(self, player_id: UUID) -> FakeShieldRecord | None:
        return self._shields.get(player_id)

    async def create(
        self,
        player_id: UUID,
        activated_at: datetime,
        expires_at: datetime,
        duration_hours: int,
    ) -> FakeShieldRecord:
        record = FakeShieldRecord(
            player_id=player_id,
            activated_at=activated_at,
            expires_at=expires_at,
            duration_hours=duration_hours,
        )
        self._shields[player_id] = record
        return record

    async def delete(self, player_id: UUID) -> None:
        if player_id in self._shields:
            del self._shields[player_id]

    async def delete_expired(self) -> int:
        now = datetime.now(timezone.utc)
        expired = [pid for pid, s in self._shields.items() if s.expires_at < now]
        for pid in expired:
            del self._shields[pid]
        return len(expired)


class MockRaidLogRepository:
    """In-memory mock for RaidLogRepositoryProtocol."""

    def __init__(self) -> None:
        self._logs: list[FakeRaidLogRecord] = []

    async def create(
        self,
        attacker_id: UUID,
        defender_id: UUID,
        success: bool,
        artifact_id: UUID | None = None,
        artifact_type_id: str | None = None,
    ) -> FakeRaidLogRecord:
        record = FakeRaidLogRecord(
            id=uuid4(),
            attacker_id=attacker_id,
            defender_id=defender_id,
            success=success,
            artifact_id=artifact_id,
            artifact_type_id=artifact_type_id,
            timestamp=datetime.now(timezone.utc),
        )
        self._logs.append(record)
        return record

    async def find_by_player(
        self,
        player_id: UUID,
        as_attacker: bool = True,
        as_defender: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[FakeRaidLogRecord], int]:
        items = []
        for log in self._logs:
            if as_attacker and log.attacker_id == player_id:
                items.append(log)
            elif as_defender and log.defender_id == player_id:
                items.append(log)
        items.sort(key=lambda x: x.timestamp, reverse=True)
        total = len(items)
        return items[offset : offset + limit], total

    async def find_last_raid_between(
        self, attacker_id: UUID, defender_id: UUID
    ) -> FakeRaidLogRecord | None:
        matching = [
            log
            for log in self._logs
            if log.attacker_id == attacker_id and log.defender_id == defender_id
        ]
        if not matching:
            return None
        return max(matching, key=lambda x: x.timestamp)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config() -> MockConfigService:
    return MockConfigService(
        {
            "vault.shield_duration_hours": 8,
            "vault.raid_cooldown_hours": 24,
            "vault.raid_energy_cost": 1,
            "vault.raid_success_base_chance": 0.7,
            "vault.empty_vault_protection": True,
            "vault.legendary_steal_chance_modifier": 0.5,
            "vault.max_artifacts_per_player": 500,
        }
    )


@pytest.fixture
def mock_logger() -> MockLogService:
    return MockLogService()


@pytest.fixture
def mock_errors(mock_logger: MockLogService) -> MockErrorService:
    return MockErrorService(mock_logger)


@pytest.fixture
def player_service() -> MockPlayerService:
    return MockPlayerService()


@pytest.fixture
def vault_artifact_repo() -> MockVaultArtifactRepository:
    return MockVaultArtifactRepository()


@pytest.fixture
def vault_shield_repo() -> MockVaultShieldRepository:
    return MockVaultShieldRepository()


@pytest.fixture
def artifact_definition_repo() -> MockArtifactDefinitionRepository:
    return MockArtifactDefinitionRepository()


@pytest.fixture
def raid_log_repo() -> MockRaidLogRepository:
    return MockRaidLogRepository()


@pytest.fixture
def vault_service(
    mock_config: MockConfigService,
    mock_logger: MockLogService,
    mock_errors: MockErrorService,
    player_service: MockPlayerService,
    vault_artifact_repo: MockVaultArtifactRepository,
    vault_shield_repo: MockVaultShieldRepository,
    artifact_definition_repo: MockArtifactDefinitionRepository,
    raid_log_repo: MockRaidLogRepository,
) -> VaultService:
    return VaultService(
        config=mock_config,
        logger=mock_logger,
        errors=mock_errors,
        player_service=player_service,
        vault_artifact_repo=vault_artifact_repo,
        vault_shield_repo=vault_shield_repo,
        artifact_definition_repo=artifact_definition_repo,
        raid_log_repo=raid_log_repo,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(name: str = "testplayer") -> Player:
    """Create a fake player for testing."""
    return Player(
        id=PlayerId(uuid4()),
        username=name,
        player_type=PlayerType.HUMAN,
        elo_rating=1000,
        created_at=datetime.now(timezone.utc),
    )


def _make_definition(
    type_id: str = "gem_ruby",
    name: str = "Ruby Gem",
    rarity: str = "common",
    artifact_set: str = "gems",
    set_position: int = 1,
    base_value: int = 100,
) -> FakeDefinitionRecord:
    """Create a fake artifact definition for testing."""
    return FakeDefinitionRecord(
        type_id=type_id,
        name=name,
        description="A test artifact",
        rarity=rarity,
        artifact_set=artifact_set,
        set_position=set_position,
        base_value=base_value,
    )


async def _setup_player_with_artifact(
    player_service: MockPlayerService,
    artifact_definition_repo: MockArtifactDefinitionRepository,
    vault_service: VaultService,
    player_name: str = "owner",
    type_id: str = "gem_ruby",
    rarity: str = "common",
) -> tuple[Player, object]:
    """Helper to create a player with one artifact in their vault."""
    player = _make_player(player_name)
    player_service.add_player(player)

    definition = _make_definition(type_id=type_id, rarity=rarity)
    artifact_definition_repo.add_definition(definition)

    artifact = await vault_service.add_artifact(
        player_id=player.id,
        artifact_type_id=type_id,
        source="test",
    )
    return player, artifact


# ---------------------------------------------------------------------------
# Tests — add_artifact
# ---------------------------------------------------------------------------


class TestAddArtifact:
    """Tests for ``VaultService.add_artifact``."""

    @pytest.mark.asyncio
    async def test_add_artifact_happy_path(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Successfully adding an artifact."""
        player = _make_player("adder")
        player_service.add_player(player)
        artifact_definition_repo.add_definition(_make_definition())

        artifact = await vault_service.add_artifact(
            player_id=player.id,
            artifact_type_id="gem_ruby",
            source="match_reward",
            source_id="match_123",
        )

        assert artifact.owner_id == player.id
        assert artifact.artifact_type_id == "gem_ruby"
        assert artifact.source == "match_reward"
        assert artifact.source_id == "match_123"
        assert artifact.definition.name == "Ruby Gem"
        assert artifact.definition.rarity == ArtifactRarity.COMMON

    @pytest.mark.asyncio
    async def test_add_artifact_invalid_type(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Adding an artifact with invalid type_id raises validation error."""
        player = _make_player("invalid_type_player")
        player_service.add_player(player)

        with pytest.raises(AppError) as exc_info:
            await vault_service.add_artifact(
                player_id=player.id,
                artifact_type_id="nonexistent_type",
                source="test",
            )
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_add_artifact_player_not_found(
        self,
        vault_service: VaultService,
    ) -> None:
        """Adding an artifact for non-existent player raises not found."""
        fake_id = PlayerId(uuid4())
        with pytest.raises(AppError) as exc_info:
            await vault_service.add_artifact(
                player_id=fake_id,
                artifact_type_id="gem_ruby",
                source="test",
            )
        assert exc_info.value.code == "NOT_FOUND_PLAYER"

    @pytest.mark.asyncio
    async def test_add_artifact_max_limit(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
        vault_artifact_repo: MockVaultArtifactRepository,
        mock_config: MockConfigService,
    ) -> None:
        """Cannot exceed max artifacts per player."""
        player = _make_player("full_vault")
        player_service.add_player(player)
        artifact_definition_repo.add_definition(_make_definition())

        # Override config to have a very low limit
        mock_config._set_nested("vault.max_artifacts_per_player", 2)
        # Recreate service with new config
        svc = VaultService(
            config=mock_config,
            logger=MockLogService(),
            errors=MockErrorService(),
            player_service=player_service,
            vault_artifact_repo=vault_artifact_repo,
            vault_shield_repo=MockVaultShieldRepository(),
            artifact_definition_repo=artifact_definition_repo,
            raid_log_repo=MockRaidLogRepository(),
        )

        # Add two artifacts (the limit)
        await svc.add_artifact(player.id, "gem_ruby", "test")
        await svc.add_artifact(player.id, "gem_ruby", "test")

        # Third should fail
        with pytest.raises(AppError) as exc_info:
            await svc.add_artifact(player.id, "gem_ruby", "test")
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ---------------------------------------------------------------------------
# Tests — get_artifact
# ---------------------------------------------------------------------------


class TestGetArtifact:
    """Tests for ``VaultService.get_artifact``."""

    @pytest.mark.asyncio
    async def test_get_artifact_found(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Successfully retrieving an existing artifact."""
        player, artifact = await _setup_player_with_artifact(
            player_service, artifact_definition_repo, vault_service
        )

        found = await vault_service.get_artifact(artifact.id)
        assert found.id == artifact.id
        assert found.definition.name == "Ruby Gem"

    @pytest.mark.asyncio
    async def test_get_artifact_not_found(
        self,
        vault_service: VaultService,
    ) -> None:
        """Getting a non-existent artifact raises NOT_FOUND_ARTIFACT."""
        fake_id = ArtifactId(uuid4())
        with pytest.raises(AppError) as exc_info:
            await vault_service.get_artifact(fake_id)
        assert exc_info.value.code == "NOT_FOUND_ARTIFACT"


# ---------------------------------------------------------------------------
# Tests — get_player_artifacts
# ---------------------------------------------------------------------------


class TestGetPlayerArtifacts:
    """Tests for ``VaultService.get_player_artifacts``."""

    @pytest.mark.asyncio
    async def test_get_player_artifacts(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Listing a player's artifacts returns paginated results."""
        player, _ = await _setup_player_with_artifact(
            player_service, artifact_definition_repo, vault_service
        )

        result = await vault_service.get_player_artifacts(player.id)
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].owner_id == player.id

    @pytest.mark.asyncio
    async def test_get_player_artifacts_empty(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Empty vault returns empty results."""
        player = _make_player("empty_vault")
        player_service.add_player(player)

        result = await vault_service.get_player_artifacts(player.id)
        assert result.total == 0
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_get_player_artifacts_invalid_limit(
        self,
        vault_service: VaultService,
    ) -> None:
        """Invalid limit raises validation error."""
        fake_id = PlayerId(uuid4())
        with pytest.raises(AppError) as exc_info:
            await vault_service.get_player_artifacts(fake_id, limit=200)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ---------------------------------------------------------------------------
# Tests — get_vault_summary
# ---------------------------------------------------------------------------


class TestGetVaultSummary:
    """Tests for ``VaultService.get_vault_summary``."""

    @pytest.mark.asyncio
    async def test_vault_summary(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
        vault_artifact_repo: MockVaultArtifactRepository,
    ) -> None:
        """Summary returns correct aggregate data."""
        player = _make_player("summary_player")
        player_service.add_player(player)

        defn = _make_definition(type_id="gem_ruby", rarity="common", base_value=100)
        artifact_definition_repo.add_definition(defn)

        artifact = await vault_service.add_artifact(player.id, "gem_ruby", "test")

        # Manually set rarity on the record for count_by_owner_and_rarity
        vault_artifact_repo._artifacts[artifact.id].rarity = "common"

        summary = await vault_service.get_vault_summary(player.id)
        assert summary.player_id == player.id
        assert summary.total_artifacts == 1
        assert summary.total_value == 100


# ---------------------------------------------------------------------------
# Tests — remove_artifact
# ---------------------------------------------------------------------------


class TestRemoveArtifact:
    """Tests for ``VaultService.remove_artifact``."""

    @pytest.mark.asyncio
    async def test_remove_artifact(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Successfully removing an artifact."""
        player, artifact = await _setup_player_with_artifact(
            player_service, artifact_definition_repo, vault_service
        )

        await vault_service.remove_artifact(artifact.id, "admin_action")

        with pytest.raises(AppError) as exc_info:
            await vault_service.get_artifact(artifact.id)
        assert exc_info.value.code == "NOT_FOUND_ARTIFACT"

    @pytest.mark.asyncio
    async def test_remove_artifact_not_found(
        self,
        vault_service: VaultService,
    ) -> None:
        """Removing a non-existent artifact raises error."""
        with pytest.raises(AppError) as exc_info:
            await vault_service.remove_artifact(ArtifactId(uuid4()), "test")
        assert exc_info.value.code == "NOT_FOUND_ARTIFACT"


# ---------------------------------------------------------------------------
# Tests — transfer_artifact
# ---------------------------------------------------------------------------


class TestTransferArtifact:
    """Tests for ``VaultService.transfer_artifact``."""

    @pytest.mark.asyncio
    async def test_transfer_artifact_happy_path(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Successfully transferring an artifact to another player."""
        owner, artifact = await _setup_player_with_artifact(
            player_service, artifact_definition_repo, vault_service
        )

        recipient = _make_player("recipient")
        player_service.add_player(recipient)

        transferred = await vault_service.transfer_artifact(
            artifact.id, owner.id, recipient.id, "trade"
        )
        assert transferred.owner_id == recipient.id

    @pytest.mark.asyncio
    async def test_transfer_artifact_wrong_owner(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Transferring from wrong owner raises validation error."""
        owner, artifact = await _setup_player_with_artifact(
            player_service, artifact_definition_repo, vault_service
        )

        other = _make_player("other")
        player_service.add_player(other)

        with pytest.raises(AppError) as exc_info:
            await vault_service.transfer_artifact(
                artifact.id, other.id, owner.id, "trade"
            )
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ---------------------------------------------------------------------------
# Tests — Shield operations
# ---------------------------------------------------------------------------


class TestShieldOperations:
    """Tests for shield-related service methods."""

    @pytest.mark.asyncio
    async def test_activate_shield(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Activating a shield succeeds."""
        player = _make_player("shielded")
        player_service.add_player(player)

        shield = await vault_service.activate_shield(player.id)
        assert shield.player_id == player.id
        assert shield.duration_hours == 8
        assert shield.is_active is True

    @pytest.mark.asyncio
    async def test_activate_shield_custom_duration(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Activating a shield with custom duration."""
        player = _make_player("custom_shield")
        player_service.add_player(player)

        shield = await vault_service.activate_shield(player.id, duration_hours=12)
        assert shield.duration_hours == 12

    @pytest.mark.asyncio
    async def test_activate_shield_already_active(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Cannot activate a shield when one is already active."""
        player = _make_player("double_shield")
        player_service.add_player(player)

        await vault_service.activate_shield(player.id)

        with pytest.raises(AppError) as exc_info:
            await vault_service.activate_shield(player.id)
        assert exc_info.value.code == "CONFLICT_SHIELD_ALREADY_ACTIVE"

    @pytest.mark.asyncio
    async def test_activate_shield_invalid_duration(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Cannot activate shield with non-positive duration."""
        player = _make_player("bad_duration")
        player_service.add_player(player)

        with pytest.raises(AppError) as exc_info:
            await vault_service.activate_shield(player.id, duration_hours=0)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_get_shield_status_active(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Shield status returns the active shield."""
        player = _make_player("status_check")
        player_service.add_player(player)

        await vault_service.activate_shield(player.id)

        shield = await vault_service.get_shield_status(player.id)
        assert shield is not None
        assert shield.is_active is True

    @pytest.mark.asyncio
    async def test_get_shield_status_none(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Shield status returns None when no shield exists."""
        player = _make_player("no_shield")
        player_service.add_player(player)

        shield = await vault_service.get_shield_status(player.id)
        assert shield is None

    @pytest.mark.asyncio
    async def test_get_shield_status_expired(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        vault_shield_repo: MockVaultShieldRepository,
    ) -> None:
        """Shield status cleans up and returns None for expired shields."""
        player = _make_player("expired_shield")
        player_service.add_player(player)

        # Create an already-expired shield directly in the mock
        await vault_shield_repo.create(
            player_id=player.id,
            activated_at=datetime.now(timezone.utc) - timedelta(hours=10),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
            duration_hours=8,
        )

        shield = await vault_service.get_shield_status(player.id)
        assert shield is None

    @pytest.mark.asyncio
    async def test_deactivate_shield(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Manually deactivating a shield succeeds."""
        player = _make_player("deactivate_me")
        player_service.add_player(player)

        await vault_service.activate_shield(player.id)
        await vault_service.deactivate_shield(player.id)

        shield = await vault_service.get_shield_status(player.id)
        assert shield is None

    @pytest.mark.asyncio
    async def test_deactivate_shield_none_exists(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Deactivating when no shield exists raises error."""
        player = _make_player("no_shield_deact")
        player_service.add_player(player)

        with pytest.raises(AppError) as exc_info:
            await vault_service.deactivate_shield(player.id)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_is_protected(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """is_protected returns True when shield is active."""
        player = _make_player("protected")
        player_service.add_player(player)

        assert await vault_service.is_protected(player.id) is False

        await vault_service.activate_shield(player.id)
        assert await vault_service.is_protected(player.id) is True


# ---------------------------------------------------------------------------
# Tests — Raid operations
# ---------------------------------------------------------------------------


class TestRaidOperations:
    """Tests for raid-related service methods."""

    @pytest.mark.asyncio
    async def test_attempt_raid_success(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Successful raid transfers artifact."""
        attacker = _make_player("raider")
        player_service.add_player(attacker)

        defender, _ = await _setup_player_with_artifact(
            player_service,
            artifact_definition_repo,
            vault_service,
            player_name="victim",
            type_id="gem_ruby",
            rarity="common",
        )

        with patch(
            "src.modules.vault.raid_service.calculate_raid_success", return_value=True
        ):
            result = await vault_service.attempt_raid(attacker.id, defender.id)

        assert result.success is True
        assert result.stolen_artifact is not None
        assert result.stolen_artifact.owner_id == attacker.id

    @pytest.mark.asyncio
    async def test_attempt_raid_failure(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Failed raid does not transfer artifact."""
        attacker = _make_player("failed_raider")
        player_service.add_player(attacker)

        defender, artifact = await _setup_player_with_artifact(
            player_service,
            artifact_definition_repo,
            vault_service,
            player_name="safe_victim",
        )

        with patch(
            "src.modules.vault.raid_service.calculate_raid_success", return_value=False
        ):
            result = await vault_service.attempt_raid(attacker.id, defender.id)

        assert result.success is False
        assert result.stolen_artifact is None

        # Artifact should still belong to defender
        found = await vault_service.get_artifact(artifact.id)
        assert found.owner_id == defender.id

    @pytest.mark.asyncio
    async def test_attempt_raid_self_raid(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Self-raid is rejected."""
        player = _make_player("self_raider")
        player_service.add_player(player)

        with pytest.raises(AppError) as exc_info:
            await vault_service.attempt_raid(player.id, player.id)
        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_attempt_raid_shielded(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Raiding a shielded player is rejected."""
        attacker = _make_player("shield_raider")
        player_service.add_player(attacker)

        defender, _ = await _setup_player_with_artifact(
            player_service,
            artifact_definition_repo,
            vault_service,
            player_name="shielded_victim",
        )

        await vault_service.activate_shield(defender.id)

        with pytest.raises(AppError) as exc_info:
            await vault_service.attempt_raid(attacker.id, defender.id)
        assert exc_info.value.code == "FORBIDDEN_VAULT_PROTECTED"

    @pytest.mark.asyncio
    async def test_attempt_raid_cooldown(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
        raid_log_repo: MockRaidLogRepository,
    ) -> None:
        """Raiding same player within cooldown is rejected."""
        attacker = _make_player("cooldown_raider")
        player_service.add_player(attacker)

        defender, _ = await _setup_player_with_artifact(
            player_service,
            artifact_definition_repo,
            vault_service,
            player_name="cooldown_victim",
        )

        # Create a recent raid log
        await raid_log_repo.create(
            attacker_id=attacker.id,
            defender_id=defender.id,
            success=False,
        )

        with pytest.raises(AppError) as exc_info:
            await vault_service.attempt_raid(attacker.id, defender.id)
        assert exc_info.value.code == "CONFLICT_RAID_COOLDOWN"

    @pytest.mark.asyncio
    async def test_attempt_raid_empty_vault_protection(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Raiding a player with empty vault returns failure (not error)."""
        attacker = _make_player("empty_vault_raider")
        player_service.add_player(attacker)

        defender = _make_player("empty_defender")
        player_service.add_player(defender)

        result = await vault_service.attempt_raid(attacker.id, defender.id)
        assert result.success is False
        assert "empty" in result.message.lower()


# ---------------------------------------------------------------------------
# Tests — can_raid
# ---------------------------------------------------------------------------


class TestCanRaid:
    """Tests for ``VaultService.can_raid``."""

    @pytest.mark.asyncio
    async def test_can_raid_eligible(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Eligible raid returns can_raid=True."""
        attacker = _make_player("eligible_raider")
        player_service.add_player(attacker)

        defender, _ = await _setup_player_with_artifact(
            player_service,
            artifact_definition_repo,
            vault_service,
            player_name="eligible_target",
        )

        eligibility = await vault_service.can_raid(attacker.id, defender.id)
        assert eligibility.can_raid is True

    @pytest.mark.asyncio
    async def test_can_raid_self(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Self-raid returns can_raid=False."""
        player = _make_player("self_check")
        player_service.add_player(player)

        eligibility = await vault_service.can_raid(player.id, player.id)
        assert eligibility.can_raid is False
        assert "own vault" in eligibility.reason.lower()

    @pytest.mark.asyncio
    async def test_can_raid_shielded(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Shielded target returns can_raid=False."""
        attacker = _make_player("check_raider")
        player_service.add_player(attacker)

        defender = _make_player("check_defender")
        player_service.add_player(defender)
        await vault_service.activate_shield(defender.id)

        eligibility = await vault_service.can_raid(attacker.id, defender.id)
        assert eligibility.can_raid is False
        assert "shield" in eligibility.reason.lower()

    @pytest.mark.asyncio
    async def test_can_raid_cooldown(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        raid_log_repo: MockRaidLogRepository,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Cooldown returns can_raid=False."""
        attacker = _make_player("cd_check_raider")
        player_service.add_player(attacker)

        defender, _ = await _setup_player_with_artifact(
            player_service,
            artifact_definition_repo,
            vault_service,
            player_name="cd_check_defender",
        )

        await raid_log_repo.create(
            attacker_id=attacker.id,
            defender_id=defender.id,
            success=False,
        )

        eligibility = await vault_service.can_raid(attacker.id, defender.id)
        assert eligibility.can_raid is False
        assert "cooldown" in eligibility.reason.lower()

    @pytest.mark.asyncio
    async def test_can_raid_empty_vault(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Empty vault returns can_raid=False."""
        attacker = _make_player("empty_check_raider")
        player_service.add_player(attacker)

        defender = _make_player("empty_check_defender")
        player_service.add_player(defender)

        eligibility = await vault_service.can_raid(attacker.id, defender.id)
        assert eligibility.can_raid is False
        assert "empty" in eligibility.reason.lower()


# ---------------------------------------------------------------------------
# Tests — get_raid_history
# ---------------------------------------------------------------------------


class TestGetRaidHistory:
    """Tests for ``VaultService.get_raid_history``."""

    @pytest.mark.asyncio
    async def test_get_raid_history_empty(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """Empty raid history returns empty results."""
        player = _make_player("history_player")
        player_service.add_player(player)

        result = await vault_service.get_raid_history(player.id)
        assert result.total == 0
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_get_raid_history_with_entries(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        raid_log_repo: MockRaidLogRepository,
    ) -> None:
        """Raid history returns existing entries."""
        attacker = _make_player("hist_attacker")
        player_service.add_player(attacker)

        defender = _make_player("hist_defender")
        player_service.add_player(defender)

        await raid_log_repo.create(attacker.id, defender.id, True)
        await raid_log_repo.create(attacker.id, defender.id, False)

        result = await vault_service.get_raid_history(attacker.id)
        assert result.total == 2


# ---------------------------------------------------------------------------
# Tests — get_raid_cooldown
# ---------------------------------------------------------------------------


class TestGetRaidCooldown:
    """Tests for ``VaultService.get_raid_cooldown``."""

    @pytest.mark.asyncio
    async def test_no_cooldown(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
    ) -> None:
        """No previous raid means no cooldown."""
        a = _make_player("cd_a")
        b = _make_player("cd_b")
        player_service.add_player(a)
        player_service.add_player(b)

        cooldown = await vault_service.get_raid_cooldown(a.id, b.id)
        assert cooldown is None

    @pytest.mark.asyncio
    async def test_active_cooldown(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        raid_log_repo: MockRaidLogRepository,
    ) -> None:
        """Recent raid creates an active cooldown."""
        a = _make_player("cd_active_a")
        b = _make_player("cd_active_b")
        player_service.add_player(a)
        player_service.add_player(b)

        await raid_log_repo.create(a.id, b.id, False)

        cooldown = await vault_service.get_raid_cooldown(a.id, b.id)
        assert cooldown is not None
        assert cooldown > datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Tests — Collection progress
# ---------------------------------------------------------------------------


class TestCollectionProgress:
    """Tests for ``VaultService.get_collection_progress``."""

    @pytest.mark.asyncio
    async def test_collection_progress_complete(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Complete collection shows 100% progress."""
        player = _make_player("collector")
        player_service.add_player(player)

        # Define a set of 2
        artifact_definition_repo.add_definition(
            _make_definition(type_id="set_a_1", artifact_set="setA", set_position=1)
        )
        artifact_definition_repo.add_definition(
            _make_definition(type_id="set_a_2", artifact_set="setA", set_position=2)
        )

        await vault_service.add_artifact(player.id, "set_a_1", "test")
        await vault_service.add_artifact(player.id, "set_a_2", "test")

        progress_list = await vault_service.get_collection_progress(
            player.id, artifact_set="setA"
        )
        assert len(progress_list) == 1
        assert progress_list[0].is_complete is True

    @pytest.mark.asyncio
    async def test_collection_progress_partial(
        self,
        vault_service: VaultService,
        player_service: MockPlayerService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Partial collection shows correct progress."""
        player = _make_player("partial_collector")
        player_service.add_player(player)

        artifact_definition_repo.add_definition(
            _make_definition(type_id="set_b_1", artifact_set="setB", set_position=1)
        )
        artifact_definition_repo.add_definition(
            _make_definition(type_id="set_b_2", artifact_set="setB", set_position=2)
        )

        await vault_service.add_artifact(player.id, "set_b_1", "test")

        progress_list = await vault_service.get_collection_progress(
            player.id, artifact_set="setB"
        )
        assert len(progress_list) == 1
        assert progress_list[0].is_complete is False
        assert progress_list[0].owned_count == 1
        assert progress_list[0].total_in_set == 2


# ---------------------------------------------------------------------------
# Tests — Artifact catalog
# ---------------------------------------------------------------------------


class TestArtifactCatalog:
    """Tests for catalog-related service methods."""

    @pytest.mark.asyncio
    async def test_get_definition(
        self,
        vault_service: VaultService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Get a definition by type_id."""
        artifact_definition_repo.add_definition(_make_definition())

        defn = await vault_service.get_artifact_definition("gem_ruby")
        assert defn.type_id == "gem_ruby"
        assert defn.name == "Ruby Gem"
        assert defn.rarity == ArtifactRarity.COMMON

    @pytest.mark.asyncio
    async def test_get_definition_not_found(
        self,
        vault_service: VaultService,
    ) -> None:
        """Non-existent definition raises NOT_FOUND_ARTIFACT."""
        with pytest.raises(AppError) as exc_info:
            await vault_service.get_artifact_definition("nonexistent")
        assert exc_info.value.code == "NOT_FOUND_ARTIFACT"

    @pytest.mark.asyncio
    async def test_list_definitions(
        self,
        vault_service: VaultService,
        artifact_definition_repo: MockArtifactDefinitionRepository,
    ) -> None:
        """Listing definitions returns all or filtered."""
        artifact_definition_repo.add_definition(
            _make_definition(type_id="a", rarity="common")
        )
        artifact_definition_repo.add_definition(
            _make_definition(type_id="b", rarity="rare")
        )

        all_defs = await vault_service.list_artifact_definitions()
        assert len(all_defs) == 2

        common_defs = await vault_service.list_artifact_definitions(
            rarity=ArtifactRarity.COMMON
        )
        assert len(common_defs) == 1
        assert common_defs[0].rarity == ArtifactRarity.COMMON
