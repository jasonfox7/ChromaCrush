"""Unit tests for player route handlers.

Tests all six player endpoints using the test client with mock services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from starlette.testclient import TestClient

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.core.types.player import Player, PlayerStats, PlayerType
from src.modules.player.dto import PaginatedResult

from tests.unit.modules.api.conftest import TEST_PLAYER_ID

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------


def _make_player(
    player_id: UUID | None = None,
    username: str = "testuser",
    player_type: PlayerType = PlayerType.HUMAN,
    elo_rating: int = 1000,
    email: str | None = None,
) -> Player:
    """Create a Player entity for mock return values."""
    player = Player(
        id=PlayerId(player_id or UUID(TEST_PLAYER_ID)),
        username=username,
        player_type=player_type,
        elo_rating=elo_rating,
        created_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    if email is not None:
        player.email = email
    return player


def _make_player_stats(
    player_id: UUID | None = None,
) -> PlayerStats:
    """Create PlayerStats for mock return values."""
    return PlayerStats(
        player_id=PlayerId(player_id or UUID(TEST_PLAYER_ID)),
        total_matches=100,
        wins=60,
        losses=35,
        draws=5,
        highest_score=15000,
        longest_chain=12,
        total_gems_matched=5000,
    )


# ---------------------------------------------------------------------------
# Player Route Tests
# ---------------------------------------------------------------------------


class TestGetCurrentPlayer:
    """Tests for GET /api/v1/players/me."""

    def test_get_current_player_success(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Returns the authenticated player's profile including email."""
        player = _make_player(username="currentuser", email="me@example.com")
        mock_player_service.get_player.return_value = player

        resp = client.get("/api/v1/players/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["username"] == "currentuser"
        assert data["data"]["player_id"] == TEST_PLAYER_ID
        assert data["data"]["email"] == "me@example.com"

    def test_get_current_player_not_found(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Player not found returns 404."""
        mock_player_service.get_player.side_effect = AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
            http_status=404,
        )

        resp = client.get("/api/v1/players/me")

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND_PLAYER"


class TestGetPlayerById:
    """Tests for GET /api/v1/players/{target_player_id}."""

    def test_get_player_by_id_success(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Returns a player's public profile without email."""
        target_id = str(uuid4())
        player = _make_player(
            player_id=UUID(target_id),
            username="otherplayer",
            email="private@example.com",
        )
        mock_player_service.get_player.return_value = player

        resp = client.get(f"/api/v1/players/{target_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["username"] == "otherplayer"
        # Email should NOT be included in public profile
        assert data["data"].get("email") is None

    def test_get_player_by_id_not_found(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Non-existent player returns 404."""
        target_id = str(uuid4())
        mock_player_service.get_player.side_effect = AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
            http_status=404,
        )

        resp = client.get(f"/api/v1/players/{target_id}")

        assert resp.status_code == 404

    def test_get_player_by_id_invalid_uuid_format(
        self,
        client: TestClient,
    ) -> None:
        """Invalid UUID format causes a server error (UUID conversion fails)."""
        resp = client.get("/api/v1/players/not-a-uuid")

        # The route will try UUID(target_player_id), which will raise ValueError
        # Error handler should catch it and return 500
        assert resp.status_code == 500


class TestUpdateCurrentPlayer:
    """Tests for PATCH /api/v1/players/me."""

    def test_update_username_success(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Updating username returns updated profile."""
        updated_player = _make_player(username="newname")
        mock_player_service.update_player.return_value = updated_player

        resp = client.patch(
            "/api/v1/players/me",
            json={
                "username": "newname",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["username"] == "newname"

    def test_update_email_success(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Updating email returns updated profile."""
        updated_player = _make_player(email="newemail@example.com")
        mock_player_service.update_player.return_value = updated_player

        resp = client.patch(
            "/api/v1/players/me",
            json={
                "email": "newemail@example.com",
            },
        )

        assert resp.status_code == 200

    def test_update_invalid_username_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Username with invalid characters fails Pydantic validation."""
        resp = client.patch(
            "/api/v1/players/me",
            json={
                "username": "bad name!",
            },
        )

        assert resp.status_code == 422

    def test_update_username_too_short_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Username shorter than 3 chars fails validation."""
        resp = client.patch(
            "/api/v1/players/me",
            json={
                "username": "ab",
            },
        )

        assert resp.status_code == 422

    def test_update_conflict_username(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Duplicate username returns 409."""
        mock_player_service.update_player.side_effect = AppError(
            code="CONFLICT_USERNAME_EXISTS",
            message="Username already taken",
            http_status=409,
        )

        resp = client.patch(
            "/api/v1/players/me",
            json={
                "username": "taken_name",
            },
        )

        assert resp.status_code == 409


class TestDeleteCurrentPlayer:
    """Tests for DELETE /api/v1/players/me."""

    def test_delete_success(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Soft-delete returns acknowledgement."""
        mock_player_service.soft_delete_player.return_value = None

        resp = client.delete("/api/v1/players/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "deleted" in data["data"]["message"].lower()

    def test_delete_player_not_found(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Deleting non-existent player returns 404."""
        mock_player_service.soft_delete_player.side_effect = AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
            http_status=404,
        )

        resp = client.delete("/api/v1/players/me")

        assert resp.status_code == 404


class TestGetPlayerStats:
    """Tests for GET /api/v1/players/{target_player_id}/stats."""

    def test_get_stats_success(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Returns player statistics."""
        target_id = str(uuid4())
        stats = _make_player_stats(player_id=UUID(target_id))
        mock_player_service.get_stats.return_value = stats

        resp = client.get(f"/api/v1/players/{target_id}/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["matches_played"] == 100
        assert data["data"]["matches_won"] == 60
        assert data["data"]["matches_lost"] == 35
        assert data["data"]["matches_drawn"] == 5
        assert data["data"]["highest_score"] == 15000
        assert data["data"]["longest_chain"] == 12
        assert data["data"]["total_gems_matched"] == 5000
        assert data["data"]["win_rate"] == 0.6

    def test_get_stats_not_found(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Non-existent player stats returns 404."""
        target_id = str(uuid4())
        mock_player_service.get_stats.side_effect = AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
            http_status=404,
        )

        resp = client.get(f"/api/v1/players/{target_id}/stats")

        assert resp.status_code == 404


class TestGetLeaderboard:
    """Tests for GET /api/v1/players/leaderboard."""

    def test_leaderboard_success(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Returns sorted leaderboard entries with pagination."""
        players = [
            _make_player(player_id=uuid4(), username="top_player", elo_rating=1500),
            _make_player(player_id=uuid4(), username="mid_player", elo_rating=1200),
            _make_player(player_id=uuid4(), username="low_player", elo_rating=900),
        ]
        mock_player_service.list_players.return_value = PaginatedResult(
            items=players,
            total=3,
            limit=50,
            offset=0,
        )

        resp = client.get("/api/v1/players/leaderboard")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        entries = data["data"]["entries"]
        assert len(entries) == 3
        # Should be sorted by elo descending
        assert entries[0]["elo_rating"] == 1500
        assert entries[0]["rank"] == 1
        assert entries[1]["elo_rating"] == 1200
        assert entries[1]["rank"] == 2
        assert entries[2]["elo_rating"] == 900
        assert entries[2]["rank"] == 3

    def test_leaderboard_empty(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Empty leaderboard returns empty entries list."""
        mock_player_service.list_players.return_value = PaginatedResult(
            items=[],
            total=0,
            limit=50,
            offset=0,
        )

        resp = client.get("/api/v1/players/leaderboard")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["entries"] == []
        assert data["data"]["total"] == 0

    def test_leaderboard_pagination_params(
        self,
        client: TestClient,
        mock_player_service: AsyncMock,
    ) -> None:
        """Pagination parameters are passed through to the service."""
        mock_player_service.list_players.return_value = PaginatedResult(
            items=[],
            total=0,
            limit=10,
            offset=5,
        )

        resp = client.get("/api/v1/players/leaderboard?limit=10&offset=5")

        assert resp.status_code == 200
        mock_player_service.list_players.assert_called_once_with(
            player_type=None,
            limit=10,
            offset=5,
        )

    def test_leaderboard_invalid_limit_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Limit exceeding 100 fails FastAPI query validation."""
        resp = client.get("/api/v1/players/leaderboard?limit=200")

        assert resp.status_code == 422
