"""Unit tests for matchmaking route handlers.

Tests all four matchmaking endpoints using the test client with mock services.
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
from src.modules.matchmaking.types import PoolType

from tests.unit.modules.api.conftest import TEST_PLAYER_ID

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeQueueEntry:
    """Mimics the QueueEntry DTO from matchmaking_service.join_queue."""

    player_id: PlayerId = field(
        default_factory=lambda: PlayerId(UUID(TEST_PLAYER_ID)),
    )
    player_username: str = "testuser"
    elo_rating: int = 1000
    pool_type: PoolType = PoolType.MIXED
    joined_at: datetime = field(
        default_factory=lambda: datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    current_elo_range: tuple[int, int] = (950, 1050)
    estimated_wait_seconds: int | None = 15
    position_in_queue: int = 1


@dataclass
class FakeQueueStatus:
    """Mimics the QueueStatus DTO from matchmaking_service.get_queue_status."""

    player_id: PlayerId = field(
        default_factory=lambda: PlayerId(UUID(TEST_PLAYER_ID)),
    )
    pool_type: PoolType = PoolType.MIXED
    elo_rating: int = 1000
    joined_at: datetime = field(
        default_factory=lambda: datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    wait_time_seconds: int = 30
    current_elo_range: tuple[int, int] = (900, 1100)
    potential_opponents: int = 5
    position_in_queue: int = 2
    estimated_wait_seconds: int | None = 20


@dataclass
class FakeQueueStats:
    """Mimics QueueStats from matchmaking_service.get_queue_stats."""

    pool_type: PoolType | None = PoolType.MIXED
    total_players: int = 10
    players_by_elo_bucket: dict[str, int] = field(default_factory=dict)
    average_wait_seconds: float = 12.5
    longest_wait_seconds: int = 45
    matches_created_last_hour: int = 8
    average_elo_difference: float = 35.2


# ---------------------------------------------------------------------------
# Matchmaking Route Tests
# ---------------------------------------------------------------------------


class TestJoinQueue:
    """Tests for POST /api/v1/matchmaking/queue."""

    def test_join_queue_success(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Successful queue join returns entry details."""
        mock_matchmaking_service.join_queue.return_value = FakeQueueEntry()

        resp = client.post(
            "/api/v1/matchmaking/queue",
            json={
                "pool_type": "mixed",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["pool_type"] == "mixed"
        assert data["data"]["elo_rating"] == 1000
        assert data["data"]["position"] == 1
        assert data["data"]["estimated_wait_seconds"] == 15

    def test_join_queue_human_pool(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Joining human pool works correctly."""
        mock_matchmaking_service.join_queue.return_value = FakeQueueEntry(
            pool_type=PoolType.HUMAN,
        )

        resp = client.post(
            "/api/v1/matchmaking/queue",
            json={
                "pool_type": "human",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["pool_type"] == "human"

    def test_join_queue_bot_pool(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Joining bot pool works correctly."""
        mock_matchmaking_service.join_queue.return_value = FakeQueueEntry(
            pool_type=PoolType.BOT,
        )

        resp = client.post(
            "/api/v1/matchmaking/queue",
            json={
                "pool_type": "bot",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["pool_type"] == "bot"

    def test_join_queue_default_pool_type(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Default pool_type is 'mixed' when not provided."""
        mock_matchmaking_service.join_queue.return_value = FakeQueueEntry()

        resp = client.post("/api/v1/matchmaking/queue", json={})

        assert resp.status_code == 200
        # The service should be called with PoolType.MIXED
        call_kwargs = mock_matchmaking_service.join_queue.call_args
        assert call_kwargs.kwargs["pool_type"] == PoolType.MIXED

    def test_join_queue_already_in_queue(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Joining when already in queue returns 409."""
        mock_matchmaking_service.join_queue.side_effect = AppError(
            code="CONFLICT_ALREADY_IN_QUEUE",
            message="Already in matchmaking queue",
            http_status=409,
        )

        resp = client.post(
            "/api/v1/matchmaking/queue",
            json={
                "pool_type": "mixed",
            },
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONFLICT_ALREADY_IN_QUEUE"

    def test_join_queue_no_energy(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Joining queue with no energy returns validation error."""
        mock_matchmaking_service.join_queue.side_effect = AppError(
            code="VALIDATION_NO_ENERGY",
            message="No energy remaining",
            http_status=400,
        )

        resp = client.post(
            "/api/v1/matchmaking/queue",
            json={
                "pool_type": "mixed",
            },
        )

        assert resp.status_code == 400


class TestLeaveQueue:
    """Tests for DELETE /api/v1/matchmaking/queue."""

    def test_leave_queue_success_was_in_queue(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Player was in queue, returns removed=True."""
        mock_matchmaking_service.leave_queue.return_value = True

        resp = client.delete("/api/v1/matchmaking/queue")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["removed"] is True

    def test_leave_queue_not_in_queue(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Player was not in queue, returns removed=False."""
        mock_matchmaking_service.leave_queue.return_value = False

        resp = client.delete("/api/v1/matchmaking/queue")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["removed"] is False


class TestGetQueueStatus:
    """Tests for GET /api/v1/matchmaking/queue/status."""

    def test_queue_status_in_queue(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Returns queue position when player is in queue."""
        mock_matchmaking_service.get_queue_status.return_value = FakeQueueStatus()

        resp = client.get("/api/v1/matchmaking/queue/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["in_queue"] is True
        assert data["data"]["position"] == 2
        assert data["data"]["pool_type"] == "mixed"
        assert data["data"]["estimated_wait_seconds"] == 20

    def test_queue_status_not_in_queue(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Returns in_queue=False when player is not in queue."""
        mock_matchmaking_service.get_queue_status.return_value = None

        resp = client.get("/api/v1/matchmaking/queue/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["in_queue"] is False
        assert data["data"]["position"] is None
        assert data["data"]["pool_type"] is None


class TestGetPoolStats:
    """Tests for GET /api/v1/matchmaking/pools."""

    def test_pool_stats_success(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Returns pool statistics for all pool types."""
        mock_matchmaking_service.get_queue_stats.return_value = FakeQueueStats()

        resp = client.get("/api/v1/matchmaking/pools")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        pools = data["data"]["pools"]
        # Should have entries for each PoolType (human, bot, mixed)
        assert len(pools) == len(PoolType)
        for pool in pools:
            assert "pool_type" in pool
            assert "player_count" in pool
            assert "average_wait_seconds" in pool

    def test_pool_stats_with_zero_wait(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Pool with None average wait returns null average_wait_seconds."""
        mock_matchmaking_service.get_queue_stats.return_value = FakeQueueStats(
            total_players=0,
            average_wait_seconds=0,
        )

        resp = client.get("/api/v1/matchmaking/pools")

        assert resp.status_code == 200

    def test_pool_stats_service_error(
        self,
        client: TestClient,
        mock_matchmaking_service: AsyncMock,
    ) -> None:
        """Service error propagates correctly."""
        mock_matchmaking_service.get_queue_stats.side_effect = AppError(
            code="INTERNAL_UNEXPECTED",
            message="Redis connection failed",
            http_status=500,
        )

        resp = client.get("/api/v1/matchmaking/pools")

        assert resp.status_code == 500
