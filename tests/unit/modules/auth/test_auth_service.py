"""Unit tests for the AuthService.

Uses mock repositories, mock player service, and mock Redis to test
business logic without a real database or Redis instance. All tests
are async using ``pytest-asyncio``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from src.core.errors import AppError
from src.core.types.auth import ApiKeyInfo, AuthToken, TokenType
from src.core.types.game import PlayerId
from src.core.types.player import Player, PlayerType
from src.modules.auth.api_key_generator import hash_api_key
from src.modules.auth.dto import AuthResult, RateLimitStatus
from src.modules.auth.password_handler import hash_password
from src.modules.auth.service import AuthService
from src.data.protocols.api_key_repository import ApiKeyRecord
from src.data.protocols.session_repository import SessionRecord
from tests.mocks.redis import MockRedis
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ---------------------------------------------------------------------------
# Mock Classes
# ---------------------------------------------------------------------------


class MockPlayerService:
    """In-memory mock for PlayerServiceProtocol."""

    def __init__(self) -> None:
        self._players: dict[UUID, Player] = {}

    def add_player(self, player: Player) -> None:
        """Test helper: add a player to the mock store."""
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

    async def get_player_by_username(self, username: str) -> Player | None:
        lower = username.lower()
        for player in self._players.values():
            if player.username.lower() == lower:
                return player
        return None


class MockPasswordStore:
    """In-memory mock for PasswordStoreProtocol."""

    def __init__(self) -> None:
        self._hashes: dict[UUID, str] = {}

    def set_hash(self, player_id: UUID, password_hash: str) -> None:
        """Test helper: store a password hash."""
        self._hashes[player_id] = password_hash

    async def get_password_hash(self, player_id: UUID) -> str | None:
        return self._hashes.get(player_id)

    async def set_password_hash(self, player_id: UUID, password_hash: str) -> None:
        self._hashes[player_id] = password_hash


class MockSessionRepository:
    """In-memory mock for SessionRepositoryProtocol."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, SessionRecord] = {}

    async def create(
        self,
        player_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        device_info: str | None = None,
        session_id: UUID | None = None,
    ) -> SessionRecord:
        sid = session_id or uuid4()
        now = datetime.now(timezone.utc)
        record = SessionRecord(
            id=sid,
            player_id=player_id,
            refresh_token_hash=refresh_token_hash,
            device_info=device_info,
            created_at=now,
            last_used_at=now,
            expires_at=expires_at,
        )
        self._sessions[sid] = record
        return record

    async def find_by_id(self, session_id: UUID) -> SessionRecord | None:
        return self._sessions.get(session_id)

    async def find_by_player_id(
        self,
        player_id: UUID,
        include_revoked: bool = False,
    ) -> list[SessionRecord]:
        results = []
        for s in self._sessions.values():
            if s.player_id != player_id:
                continue
            if not include_revoked and s.revoked_at is not None:
                continue
            results.append(s)
        # Sort by created_at descending
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    async def update_last_used(self, session_id: UUID) -> None:
        if session_id in self._sessions:
            s = self._sessions[session_id]
            self._sessions[session_id] = SessionRecord(
                id=s.id,
                player_id=s.player_id,
                refresh_token_hash=s.refresh_token_hash,
                device_info=s.device_info,
                created_at=s.created_at,
                last_used_at=datetime.now(timezone.utc),
                expires_at=s.expires_at,
                revoked_at=s.revoked_at,
            )

    async def revoke(self, session_id: UUID) -> None:
        if session_id in self._sessions:
            s = self._sessions[session_id]
            self._sessions[session_id] = SessionRecord(
                id=s.id,
                player_id=s.player_id,
                refresh_token_hash=s.refresh_token_hash,
                device_info=s.device_info,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
                expires_at=s.expires_at,
                revoked_at=datetime.now(timezone.utc),
            )

    async def revoke_all_for_player(self, player_id: UUID) -> int:
        count = 0
        now = datetime.now(timezone.utc)
        for sid, s in list(self._sessions.items()):
            if s.player_id == player_id and s.revoked_at is None:
                self._sessions[sid] = SessionRecord(
                    id=s.id,
                    player_id=s.player_id,
                    refresh_token_hash=s.refresh_token_hash,
                    device_info=s.device_info,
                    created_at=s.created_at,
                    last_used_at=s.last_used_at,
                    expires_at=s.expires_at,
                    revoked_at=now,
                )
                count += 1
        return count

    async def count_active_for_player(self, player_id: UUID) -> int:
        now = datetime.now(timezone.utc)
        return sum(
            1
            for s in self._sessions.values()
            if s.player_id == player_id and s.revoked_at is None and s.expires_at > now
        )

    async def cleanup_expired(self) -> int:
        return 0


class MockApiKeyRepository:
    """In-memory mock for ApiKeyRepositoryProtocol."""

    def __init__(self) -> None:
        self._keys: dict[UUID, ApiKeyRecord] = {}

    async def create(
        self,
        player_id: UUID,
        key_hash: str,
        key_prefix: str,
        description: str | None = None,
    ) -> ApiKeyRecord:
        kid = uuid4()
        now = datetime.now(timezone.utc)
        record = ApiKeyRecord(
            id=kid,
            player_id=player_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            description=description,
            created_at=now,
        )
        self._keys[kid] = record
        return record

    async def find_by_id(self, key_id: UUID) -> ApiKeyRecord | None:
        return self._keys.get(key_id)

    async def find_by_prefix(self, prefix: str) -> list[ApiKeyRecord]:
        return [k for k in self._keys.values() if k.key_prefix == prefix]

    async def find_by_player_id(
        self,
        player_id: UUID,
        include_revoked: bool = False,
    ) -> list[ApiKeyRecord]:
        results = []
        for k in self._keys.values():
            if k.player_id != player_id:
                continue
            if not include_revoked and k.revoked_at is not None:
                continue
            results.append(k)
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    async def update_last_used(self, key_id: UUID) -> None:
        if key_id in self._keys:
            k = self._keys[key_id]
            self._keys[key_id] = ApiKeyRecord(
                id=k.id,
                player_id=k.player_id,
                key_hash=k.key_hash,
                key_prefix=k.key_prefix,
                description=k.description,
                created_at=k.created_at,
                last_used_at=datetime.now(timezone.utc),
                revoked_at=k.revoked_at,
            )

    async def revoke(self, key_id: UUID) -> None:
        if key_id in self._keys:
            k = self._keys[key_id]
            self._keys[key_id] = ApiKeyRecord(
                id=k.id,
                player_id=k.player_id,
                key_hash=k.key_hash,
                key_prefix=k.key_prefix,
                description=k.description,
                created_at=k.created_at,
                last_used_at=k.last_used_at,
                revoked_at=datetime.now(timezone.utc),
            )

    async def count_active_for_player(self, player_id: UUID) -> int:
        return sum(
            1
            for k in self._keys.values()
            if k.player_id == player_id and k.revoked_at is None
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_human_player(
    player_id: UUID | None = None,
    username: str = "testuser",
) -> Player:
    """Create a human player for tests."""
    return Player(
        id=PlayerId(player_id or uuid4()),
        username=username,
        player_type=PlayerType.HUMAN,
        elo_rating=1000,
        created_at=datetime.now(timezone.utc),
    )


def _make_bot_player(
    player_id: UUID | None = None,
    username: str = "testbot",
) -> Player:
    """Create a bot player for tests."""
    return Player(
        id=PlayerId(player_id or uuid4()),
        username=username,
        player_type=PlayerType.BOT,
        elo_rating=1000,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_config() -> MockConfigService:
    """Config with auth defaults."""
    return MockConfigService(
        {
            "auth.jwt_secret": "test-secret-key-for-unit-tests",
            "auth.jwt_algorithm": "HS256",
            "auth.access_token_expiry_minutes": 60,
            "auth.refresh_token_expiry_days": 30,
            "auth.api_key_prefix": "cc_",
            "auth.api_key_length": 32,
            "auth.bcrypt_rounds": 4,  # Low for fast tests
            "auth.password_min_length": 8,
            "auth.rate_limit_requests": 100,
            "auth.rate_limit_window_seconds": 60,
            "auth.max_sessions_per_player": 5,
        }
    )


@pytest.fixture
def mock_logger() -> MockLogService:
    return MockLogService()


@pytest.fixture
def mock_errors(mock_logger: MockLogService) -> MockErrorService:
    return MockErrorService(mock_logger)


@pytest.fixture
def mock_player_service() -> MockPlayerService:
    return MockPlayerService()


@pytest.fixture
def mock_session_repo() -> MockSessionRepository:
    return MockSessionRepository()


@pytest.fixture
def mock_api_key_repo() -> MockApiKeyRepository:
    return MockApiKeyRepository()


@pytest.fixture
def mock_password_store() -> MockPasswordStore:
    return MockPasswordStore()


@pytest.fixture
def mock_redis() -> MockRedis:
    return MockRedis()


@pytest.fixture
def auth_service(
    mock_config: MockConfigService,
    mock_logger: MockLogService,
    mock_errors: MockErrorService,
    mock_player_service: MockPlayerService,
    mock_session_repo: MockSessionRepository,
    mock_api_key_repo: MockApiKeyRepository,
    mock_password_store: MockPasswordStore,
    mock_redis: MockRedis,
) -> AuthService:
    """Build an AuthService with all mock dependencies."""
    return AuthService(
        config=mock_config,
        logger=mock_logger,
        errors=mock_errors,
        player_service=mock_player_service,
        session_repo=mock_session_repo,
        api_key_repo=mock_api_key_repo,
        password_store=mock_password_store,
        redis=mock_redis,
    )


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------


class TestAuthenticate:
    """Tests for username/password authentication."""

    @pytest.mark.asyncio
    async def test_successful_login(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_password_store: MockPasswordStore,
    ) -> None:
        """Valid credentials return AuthResult with tokens."""
        player = _make_human_player(username="alice")
        mock_player_service.add_player(player)
        pw_hash = hash_password("ValidPass1", rounds=4)
        mock_password_store.set_hash(player.id, pw_hash)

        result = await auth_service.authenticate("alice", "ValidPass1")

        assert isinstance(result, AuthResult)
        assert result.token_type == "Bearer"
        assert len(result.access_token) > 0
        assert len(result.refresh_token) > 0
        assert result.expires_in == 3600

    @pytest.mark.asyncio
    async def test_username_not_found(
        self,
        auth_service: AuthService,
    ) -> None:
        """Non-existent username raises AUTH_INVALID_CREDENTIALS."""
        with pytest.raises(AppError) as exc_info:
            await auth_service.authenticate("nonexistent", "password")

        assert exc_info.value.code == "AUTH_INVALID_CREDENTIALS"
        assert exc_info.value.http_status == 401

    @pytest.mark.asyncio
    async def test_wrong_password(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_password_store: MockPasswordStore,
    ) -> None:
        """Wrong password raises AUTH_INVALID_CREDENTIALS."""
        player = _make_human_player(username="bob")
        mock_player_service.add_player(player)
        pw_hash = hash_password("Correct1Pass", rounds=4)
        mock_password_store.set_hash(player.id, pw_hash)

        with pytest.raises(AppError) as exc_info:
            await auth_service.authenticate("bob", "WrongPass1")

        assert exc_info.value.code == "AUTH_INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_bot_cannot_use_password(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Bot player trying password auth raises AUTH_INVALID_CREDENTIALS."""
        bot = _make_bot_player(username="bot1")
        mock_player_service.add_player(bot)

        with pytest.raises(AppError) as exc_info:
            await auth_service.authenticate("bot1", "Password1")

        assert exc_info.value.code == "AUTH_INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_no_password_set(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Player without password hash raises AUTH_INVALID_CREDENTIALS."""
        player = _make_human_player(username="carol")
        mock_player_service.add_player(player)
        # No password hash set in mock store

        with pytest.raises(AppError) as exc_info:
            await auth_service.authenticate("carol", "SomePass1")

        assert exc_info.value.code == "AUTH_INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_authorization_header_format(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_password_store: MockPasswordStore,
    ) -> None:
        """AuthResult.authorization_header has correct format."""
        player = _make_human_player(username="dave")
        mock_player_service.add_player(player)
        pw_hash = hash_password("ValidPass1", rounds=4)
        mock_password_store.set_hash(player.id, pw_hash)

        result = await auth_service.authenticate("dave", "ValidPass1")

        assert result.authorization_header.startswith("Bearer ")
        assert result.access_token in result.authorization_header


# ---------------------------------------------------------------------------
# Token Validation Tests
# ---------------------------------------------------------------------------


class TestValidateToken:
    """Tests for JWT and API key validation."""

    @pytest.mark.asyncio
    async def test_valid_jwt_access_token(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_password_store: MockPasswordStore,
    ) -> None:
        """Valid JWT returns AuthToken with correct fields."""
        player = _make_human_player(username="eve")
        mock_player_service.add_player(player)
        pw_hash = hash_password("ValidPass1", rounds=4)
        mock_password_store.set_hash(player.id, pw_hash)

        login_result = await auth_service.authenticate("eve", "ValidPass1")

        auth_token = await auth_service.validate_token(login_result.access_token)

        assert isinstance(auth_token, AuthToken)
        assert auth_token.token_type == TokenType.ACCESS
        assert auth_token.player_id == player.id
        assert auth_token.expires_at is not None

    @pytest.mark.asyncio
    async def test_invalid_jwt(self, auth_service: AuthService) -> None:
        """Invalid JWT raises AUTH_TOKEN_INVALID."""
        with pytest.raises(AppError) as exc_info:
            await auth_service.validate_token("totally-invalid-jwt-token")

        assert exc_info.value.code == "AUTH_TOKEN_INVALID"
        assert exc_info.value.http_status == 401

    @pytest.mark.asyncio
    async def test_jwt_with_revoked_session(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_password_store: MockPasswordStore,
        mock_session_repo: MockSessionRepository,
    ) -> None:
        """JWT for a revoked session raises AUTH_TOKEN_INVALID."""
        player = _make_human_player(username="frank")
        mock_player_service.add_player(player)
        pw_hash = hash_password("ValidPass1", rounds=4)
        mock_password_store.set_hash(player.id, pw_hash)

        login_result = await auth_service.authenticate("frank", "ValidPass1")

        # Revoke all sessions
        await mock_session_repo.revoke_all_for_player(player.id)

        with pytest.raises(AppError) as exc_info:
            await auth_service.validate_token(login_result.access_token)

        assert exc_info.value.code == "AUTH_TOKEN_INVALID"

    @pytest.mark.asyncio
    async def test_valid_api_key(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_api_key_repo: MockApiKeyRepository,
    ) -> None:
        """Valid API key returns AuthToken with API_KEY type."""
        bot = _make_bot_player(username="apibot")
        mock_player_service.add_player(bot)

        # Create an API key through the service
        result = await auth_service.create_api_key(bot.id)

        # Validate the raw key
        auth_token = await auth_service.validate_token(result.raw_key)

        assert isinstance(auth_token, AuthToken)
        assert auth_token.token_type == TokenType.API_KEY
        assert auth_token.player_id == bot.id
        assert auth_token.expires_at is None  # API keys don't expire

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, auth_service: AuthService) -> None:
        """Non-existent API key raises AUTH_API_KEY_INVALID."""
        with pytest.raises(AppError) as exc_info:
            await auth_service.validate_token("cc_nonexistent_key_abcdef12")

        assert exc_info.value.code == "AUTH_API_KEY_INVALID"

    @pytest.mark.asyncio
    async def test_revoked_api_key(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Revoked API key raises AUTH_API_KEY_REVOKED."""
        bot = _make_bot_player(username="revokebot")
        mock_player_service.add_player(bot)

        # Create and revoke
        result = await auth_service.create_api_key(bot.id)
        await auth_service.revoke_api_key(result.key_info.key_id, bot.id)

        with pytest.raises(AppError) as exc_info:
            await auth_service.validate_token(result.raw_key)

        assert exc_info.value.code == "AUTH_API_KEY_REVOKED"


# ---------------------------------------------------------------------------
# Token Refresh Tests
# ---------------------------------------------------------------------------


class TestRefreshToken:
    """Tests for refresh token rotation."""

    @pytest.mark.asyncio
    async def test_successful_refresh(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_password_store: MockPasswordStore,
    ) -> None:
        """Valid refresh token returns new tokens."""
        player = _make_human_player(username="grace")
        mock_player_service.add_player(player)
        pw_hash = hash_password("ValidPass1", rounds=4)
        mock_password_store.set_hash(player.id, pw_hash)

        login_result = await auth_service.authenticate("grace", "ValidPass1")

        new_result = await auth_service.refresh_token(login_result.refresh_token)

        assert isinstance(new_result, AuthResult)
        assert new_result.access_token != login_result.access_token
        assert new_result.refresh_token != login_result.refresh_token

    @pytest.mark.asyncio
    async def test_refresh_with_already_used_token(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_password_store: MockPasswordStore,
    ) -> None:
        """Reusing a refresh token raises AUTH_TOKEN_INVALID."""
        player = _make_human_player(username="henry")
        mock_player_service.add_player(player)
        pw_hash = hash_password("ValidPass1", rounds=4)
        mock_password_store.set_hash(player.id, pw_hash)

        login_result = await auth_service.authenticate("henry", "ValidPass1")

        # First refresh succeeds
        await auth_service.refresh_token(login_result.refresh_token)

        # Second refresh with same token fails (session was revoked)
        with pytest.raises(AppError) as exc_info:
            await auth_service.refresh_token(login_result.refresh_token)

        assert exc_info.value.code == "AUTH_TOKEN_INVALID"

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_password_store: MockPasswordStore,
    ) -> None:
        """Using an access token for refresh raises AUTH_TOKEN_INVALID."""
        player = _make_human_player(username="iris")
        mock_player_service.add_player(player)
        pw_hash = hash_password("ValidPass1", rounds=4)
        mock_password_store.set_hash(player.id, pw_hash)

        login_result = await auth_service.authenticate("iris", "ValidPass1")

        with pytest.raises(AppError) as exc_info:
            await auth_service.refresh_token(login_result.access_token)

        assert exc_info.value.code == "AUTH_TOKEN_INVALID"


# ---------------------------------------------------------------------------
# Logout Tests
# ---------------------------------------------------------------------------


class TestLogout:
    """Tests for session invalidation."""

    @pytest.mark.asyncio
    async def test_logout_all_sessions(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_password_store: MockPasswordStore,
        mock_session_repo: MockSessionRepository,
    ) -> None:
        """Logout without session_id revokes all sessions."""
        player = _make_human_player(username="jack")
        mock_player_service.add_player(player)
        pw_hash = hash_password("ValidPass1", rounds=4)
        mock_password_store.set_hash(player.id, pw_hash)

        # Create multiple sessions
        await auth_service.authenticate("jack", "ValidPass1")
        await auth_service.authenticate("jack", "ValidPass1")

        # Logout all
        await auth_service.logout(player.id)

        active = await mock_session_repo.count_active_for_player(player.id)
        assert active == 0

    @pytest.mark.asyncio
    async def test_logout_nonexistent_player(
        self,
        auth_service: AuthService,
    ) -> None:
        """Logout for non-existent player raises NOT_FOUND_PLAYER."""
        fake_id = PlayerId(uuid4())

        with pytest.raises(AppError) as exc_info:
            await auth_service.logout(fake_id)

        assert exc_info.value.code == "NOT_FOUND_PLAYER"


# ---------------------------------------------------------------------------
# API Key Management Tests
# ---------------------------------------------------------------------------


class TestCreateApiKey:
    """Tests for API key creation."""

    @pytest.mark.asyncio
    async def test_create_for_bot(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Bot can create an API key."""
        bot = _make_bot_player(username="keybot")
        mock_player_service.add_player(bot)

        result = await auth_service.create_api_key(bot.id, description="Test key")

        assert result.raw_key.startswith("cc_")
        assert result.key_info.player_id == bot.id
        assert result.key_info.revoked is False

    @pytest.mark.asyncio
    async def test_create_for_human_fails(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Human cannot create an API key (FORBIDDEN_NOT_BOT)."""
        human = _make_human_player(username="humanuser")
        mock_player_service.add_player(human)

        with pytest.raises(AppError) as exc_info:
            await auth_service.create_api_key(human.id)

        assert exc_info.value.code == "FORBIDDEN_NOT_BOT"
        assert exc_info.value.http_status == 403

    @pytest.mark.asyncio
    async def test_create_with_long_description_fails(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Description exceeding 255 chars raises VALIDATION_INVALID_INPUT."""
        bot = _make_bot_player(username="longbot")
        mock_player_service.add_player(bot)

        with pytest.raises(AppError) as exc_info:
            await auth_service.create_api_key(bot.id, description="x" * 256)

        assert exc_info.value.code == "VALIDATION_INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_create_for_nonexistent_player_fails(
        self,
        auth_service: AuthService,
    ) -> None:
        """Creating key for non-existent player raises NOT_FOUND_PLAYER."""
        with pytest.raises(AppError) as exc_info:
            await auth_service.create_api_key(PlayerId(uuid4()))

        assert exc_info.value.code == "NOT_FOUND_PLAYER"


class TestRevokeApiKey:
    """Tests for API key revocation."""

    @pytest.mark.asyncio
    async def test_revoke_own_key(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Owner can revoke their own key."""
        bot = _make_bot_player(username="revokebot2")
        mock_player_service.add_player(bot)

        result = await auth_service.create_api_key(bot.id)
        await auth_service.revoke_api_key(result.key_info.key_id, bot.id)

        # Key should appear revoked in list
        keys = await auth_service.list_api_keys(bot.id, include_revoked=True)
        revoked_key = next(k for k in keys if k.key_id == result.key_info.key_id)
        assert revoked_key.revoked is True

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(
        self,
        auth_service: AuthService,
    ) -> None:
        """Revoking non-existent key raises NOT_FOUND_API_KEY."""
        with pytest.raises(AppError) as exc_info:
            await auth_service.revoke_api_key(uuid4(), PlayerId(uuid4()))

        assert exc_info.value.code == "NOT_FOUND_API_KEY"

    @pytest.mark.asyncio
    async def test_revoke_not_owner(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """Non-owner cannot revoke a key (FORBIDDEN_NOT_KEY_OWNER)."""
        bot1 = _make_bot_player(username="bot1_owner")
        bot2 = _make_bot_player(username="bot2_thief")
        mock_player_service.add_player(bot1)
        mock_player_service.add_player(bot2)

        result = await auth_service.create_api_key(bot1.id)

        with pytest.raises(AppError) as exc_info:
            await auth_service.revoke_api_key(result.key_info.key_id, bot2.id)

        assert exc_info.value.code == "FORBIDDEN_NOT_KEY_OWNER"


class TestListApiKeys:
    """Tests for API key listing."""

    @pytest.mark.asyncio
    async def test_list_active_keys(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """List returns only active keys by default."""
        bot = _make_bot_player(username="listbot")
        mock_player_service.add_player(bot)

        await auth_service.create_api_key(bot.id, description="Key 1")
        result2 = await auth_service.create_api_key(bot.id, description="Key 2")
        await auth_service.revoke_api_key(result2.key_info.key_id, bot.id)

        keys = await auth_service.list_api_keys(bot.id)
        assert len(keys) == 1
        assert keys[0].revoked is False

    @pytest.mark.asyncio
    async def test_list_including_revoked(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """List with include_revoked returns all keys."""
        bot = _make_bot_player(username="listbot2")
        mock_player_service.add_player(bot)

        await auth_service.create_api_key(bot.id, description="Key A")
        result2 = await auth_service.create_api_key(bot.id, description="Key B")
        await auth_service.revoke_api_key(result2.key_info.key_id, bot.id)

        keys = await auth_service.list_api_keys(bot.id, include_revoked=True)
        assert len(keys) == 2


# ---------------------------------------------------------------------------
# Rate Limiting Tests
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Tests for rate limiting support."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_api_key_repo: MockApiKeyRepository,
    ) -> None:
        """check_rate_limit returns status within limit."""
        bot = _make_bot_player(username="ratebot")
        mock_player_service.add_player(bot)

        result = await auth_service.create_api_key(bot.id)
        status = await auth_service.check_rate_limit(result.key_info.key_id)

        assert isinstance(status, RateLimitStatus)
        assert status.requests_remaining == 100
        assert status.is_exceeded is False

    @pytest.mark.asyncio
    async def test_record_request_decrements_remaining(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
    ) -> None:
        """record_api_request decrements remaining requests."""
        bot = _make_bot_player(username="ratebot2")
        mock_player_service.add_player(bot)

        result = await auth_service.create_api_key(bot.id)
        status = await auth_service.record_api_request(result.key_info.key_id)

        assert status.requests_remaining == 99
        assert status.is_exceeded is False

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_redis: MockRedis,
    ) -> None:
        """Exceeding rate limit raises RATE_LIMIT_API_KEY."""
        bot = _make_bot_player(username="ratebot3")
        mock_player_service.add_player(bot)

        result = await auth_service.create_api_key(bot.id)
        key_id = result.key_info.key_id

        # Simulate being at the limit
        redis_key = f"chromacrush:ratelimit:{key_id}"
        await mock_redis.set(redis_key, "100")

        with pytest.raises(AppError) as exc_info:
            await auth_service.record_api_request(key_id)

        assert exc_info.value.code == "RATE_LIMIT_API_KEY"
        assert exc_info.value.http_status == 429

    @pytest.mark.asyncio
    async def test_check_rate_limit_nonexistent_key(
        self,
        auth_service: AuthService,
    ) -> None:
        """check_rate_limit for non-existent key raises NOT_FOUND_API_KEY."""
        with pytest.raises(AppError) as exc_info:
            await auth_service.check_rate_limit(uuid4())

        assert exc_info.value.code == "NOT_FOUND_API_KEY"


# ---------------------------------------------------------------------------
# Password Operations Tests
# ---------------------------------------------------------------------------


class TestPasswordOperations:
    """Tests for password hashing and verification via the service."""

    def test_hash_password_valid(self, auth_service: AuthService) -> None:
        """Valid password is hashed successfully."""
        hashed = auth_service.hash_password("ValidPass1")
        assert hashed.startswith("$2b$")

    def test_hash_password_weak_fails(self, auth_service: AuthService) -> None:
        """Weak password raises VALIDATION_WEAK_PASSWORD."""
        with pytest.raises(AppError) as exc_info:
            auth_service.hash_password("short")

        assert exc_info.value.code == "VALIDATION_WEAK_PASSWORD"

    def test_verify_password_correct(self, auth_service: AuthService) -> None:
        """Correct password verifies."""
        hashed = auth_service.hash_password("ValidPass1")
        assert auth_service.verify_password("ValidPass1", hashed) is True

    def test_verify_password_incorrect(self, auth_service: AuthService) -> None:
        """Incorrect password fails verification."""
        hashed = auth_service.hash_password("ValidPass1")
        assert auth_service.verify_password("WrongPass1", hashed) is False


# ---------------------------------------------------------------------------
# Session Management Tests
# ---------------------------------------------------------------------------


class TestGetActiveSessions:
    """Tests for active session listing."""

    @pytest.mark.asyncio
    async def test_returns_active_sessions(
        self,
        auth_service: AuthService,
        mock_player_service: MockPlayerService,
        mock_password_store: MockPasswordStore,
    ) -> None:
        """get_active_sessions returns non-expired sessions."""
        player = _make_human_player(username="sessionuser")
        mock_player_service.add_player(player)
        pw_hash = hash_password("ValidPass1", rounds=4)
        mock_password_store.set_hash(player.id, pw_hash)

        await auth_service.authenticate("sessionuser", "ValidPass1")

        sessions = await auth_service.get_active_sessions(player.id)

        assert len(sessions) == 1
        assert sessions[0].player_id == player.id

    @pytest.mark.asyncio
    async def test_nonexistent_player_raises(
        self,
        auth_service: AuthService,
    ) -> None:
        """get_active_sessions for non-existent player raises NOT_FOUND_PLAYER."""
        with pytest.raises(AppError) as exc_info:
            await auth_service.get_active_sessions(PlayerId(uuid4()))

        assert exc_info.value.code == "NOT_FOUND_PLAYER"
