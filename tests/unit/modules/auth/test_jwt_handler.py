"""Unit tests for the JWT handler.

Tests JWT token creation and decoding using PyJWT.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import uuid4

import jwt
import pytest

from src.core.errors import AppError
from src.modules.auth.jwt_handler import JwtHandler

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SECRET = "test-jwt-secret-for-unit-tests"
ALGORITHM = "HS256"


@pytest.fixture
def handler() -> JwtHandler:
    """Provide a JwtHandler with a test secret."""
    return JwtHandler(secret=SECRET, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Access Token Tests
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    """Tests for access token creation."""

    def test_creates_valid_jwt(self, handler: JwtHandler) -> None:
        """Access token can be decoded by PyJWT."""
        player_id = uuid4()
        session_id = uuid4()

        token = handler.create_access_token(
            player_id=player_id,
            session_id=session_id,
            expiry_minutes=60,
        )

        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])

        assert payload["sub"] == str(player_id)
        assert payload["sid"] == str(session_id)
        assert payload["typ"] == "access"
        assert "iat" in payload
        assert "exp" in payload

    def test_expiry_is_correct(self, handler: JwtHandler) -> None:
        """Access token expires at the correct time."""
        player_id = uuid4()
        session_id = uuid4()

        token = handler.create_access_token(
            player_id=player_id,
            session_id=session_id,
            expiry_minutes=30,
        )

        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        diff = payload["exp"] - payload["iat"]

        # Should be 30 minutes = 1800 seconds
        assert diff == 30 * 60


# ---------------------------------------------------------------------------
# Refresh Token Tests
# ---------------------------------------------------------------------------


class TestCreateRefreshToken:
    """Tests for refresh token creation."""

    def test_creates_refresh_type(self, handler: JwtHandler) -> None:
        """Refresh token has type 'refresh'."""
        player_id = uuid4()
        session_id = uuid4()

        token = handler.create_refresh_token(
            player_id=player_id,
            session_id=session_id,
            expiry_days=30,
        )

        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])

        assert payload["typ"] == "refresh"
        assert payload["sub"] == str(player_id)
        assert payload["sid"] == str(session_id)

    def test_expiry_is_correct(self, handler: JwtHandler) -> None:
        """Refresh token expires at the correct time."""
        player_id = uuid4()
        session_id = uuid4()

        token = handler.create_refresh_token(
            player_id=player_id,
            session_id=session_id,
            expiry_days=7,
        )

        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        diff = payload["exp"] - payload["iat"]

        # Should be 7 days = 604800 seconds
        assert diff == 7 * 24 * 60 * 60


# ---------------------------------------------------------------------------
# Decode Token Tests
# ---------------------------------------------------------------------------


class TestDecodeToken:
    """Tests for token decoding and validation."""

    def test_decode_valid_access_token(self, handler: JwtHandler) -> None:
        """Successfully decodes a valid access token."""
        player_id = uuid4()
        session_id = uuid4()

        token = handler.create_access_token(
            player_id=player_id,
            session_id=session_id,
            expiry_minutes=60,
        )

        payload = handler.decode_token(token)

        assert payload.player_id == player_id
        assert payload.session_id == session_id
        assert payload.token_type == "access"
        assert isinstance(payload.issued_at, datetime)
        assert isinstance(payload.expires_at, datetime)

    def test_decode_valid_refresh_token(self, handler: JwtHandler) -> None:
        """Successfully decodes a valid refresh token."""
        player_id = uuid4()
        session_id = uuid4()

        token = handler.create_refresh_token(
            player_id=player_id,
            session_id=session_id,
            expiry_days=30,
        )

        payload = handler.decode_token(token)

        assert payload.player_id == player_id
        assert payload.session_id == session_id
        assert payload.token_type == "refresh"

    def test_decode_expired_token_raises(self, handler: JwtHandler) -> None:
        """Expired token raises AUTH_TOKEN_EXPIRED."""
        # Create a token that's already expired
        payload = {
            "sub": str(uuid4()),
            "sid": str(uuid4()),
            "typ": "access",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,  # expired 1 hour ago
        }
        token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)

        with pytest.raises(AppError) as exc_info:
            handler.decode_token(token)

        assert exc_info.value.code == "AUTH_TOKEN_EXPIRED"
        assert exc_info.value.http_status == 401

    def test_decode_invalid_signature_raises(self, handler: JwtHandler) -> None:
        """Token with wrong signature raises AUTH_TOKEN_INVALID."""
        payload = {
            "sub": str(uuid4()),
            "sid": str(uuid4()),
            "typ": "access",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        # Sign with a different secret
        token = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)

        with pytest.raises(AppError) as exc_info:
            handler.decode_token(token)

        assert exc_info.value.code == "AUTH_TOKEN_INVALID"
        assert exc_info.value.http_status == 401

    def test_decode_malformed_token_raises(self, handler: JwtHandler) -> None:
        """Malformed token string raises AUTH_TOKEN_INVALID."""
        with pytest.raises(AppError) as exc_info:
            handler.decode_token("not-a-valid-jwt")

        assert exc_info.value.code == "AUTH_TOKEN_INVALID"
        assert exc_info.value.http_status == 401
