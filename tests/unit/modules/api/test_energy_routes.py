"""Unit tests for energy route handlers.

Tests all three energy endpoints using the test client with mock services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from starlette.testclient import TestClient

from src.core.errors import AppError

from tests.unit.modules.api.conftest import TEST_PLAYER_ID

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeEnergyInfo:
    """Mimics the EnergyInfo DTO returned by energy_service.get_energy."""

    current_hearts: int = 4
    max_hearts: int = 5
    seconds_to_next_heart: int = 900
    next_heart_at: datetime | None = field(
        default_factory=lambda: datetime(2026, 2, 1, 12, 15, 0, tzinfo=timezone.utc),
    )
    is_full: bool = False
    daily_streak: int = 3


@dataclass
class FakeLoginResult:
    """Mimics the login result from energy_service.record_login."""

    streak_day: int = 4
    streak_continued: bool = True
    streak_broken: bool = False
    bonus_hearts_granted: int = 0
    energy_info: FakeEnergyInfo = field(default_factory=FakeEnergyInfo)


@dataclass
class FakeStreakInfo:
    """Mimics the streak info from energy_service.get_streak."""

    current_streak: int = 5
    last_login_date: datetime | None = field(
        default_factory=lambda: datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc),
    )
    next_reward_threshold: int = 7
    days_until_reward: int = 2
    reward_hearts: int = 3


# ---------------------------------------------------------------------------
# Energy Route Tests
# ---------------------------------------------------------------------------


class TestGetEnergy:
    """Tests for GET /api/v1/energy."""

    def test_get_energy_success(
        self,
        client: TestClient,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Returns current energy state for authenticated player."""
        mock_energy_service.get_energy.return_value = FakeEnergyInfo()

        resp = client.get("/api/v1/energy")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["current_hearts"] == 4
        assert data["data"]["max_hearts"] == 5
        assert data["data"]["seconds_to_next_heart"] == 900
        assert data["data"]["is_full"] is False
        assert data["data"]["daily_streak"] == 3

    def test_get_energy_full_hearts(
        self,
        client: TestClient,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Full hearts state reports is_full=True and null next_heart_at."""
        mock_energy_service.get_energy.return_value = FakeEnergyInfo(
            current_hearts=5,
            max_hearts=5,
            seconds_to_next_heart=0,
            next_heart_at=None,
            is_full=True,
        )

        resp = client.get("/api/v1/energy")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["is_full"] is True
        assert data["data"]["next_heart_at"] is None

    def test_get_energy_player_not_found(
        self,
        client: TestClient,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Energy query for non-existent player returns 404."""
        mock_energy_service.get_energy.side_effect = AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
            http_status=404,
        )

        resp = client.get("/api/v1/energy")

        assert resp.status_code == 404


class TestRecordLogin:
    """Tests for POST /api/v1/energy/login."""

    def test_record_login_success(
        self,
        client: TestClient,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Successful login recording returns streak and energy state."""
        mock_energy_service.record_login.return_value = FakeLoginResult()

        resp = client.post("/api/v1/energy/login")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["streak_day"] == 4
        assert data["data"]["streak_continued"] is True
        assert data["data"]["streak_broken"] is False
        assert data["data"]["bonus_hearts_granted"] == 0
        assert data["data"]["energy"]["current_hearts"] == 4

    def test_record_login_streak_broken(
        self,
        client: TestClient,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Login after missed day reports streak_broken=True."""
        mock_energy_service.record_login.return_value = FakeLoginResult(
            streak_day=1,
            streak_continued=False,
            streak_broken=True,
        )

        resp = client.post("/api/v1/energy/login")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["streak_broken"] is True
        assert data["data"]["streak_continued"] is False

    def test_record_login_bonus_hearts(
        self,
        client: TestClient,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Login at milestone streak grants bonus hearts."""
        mock_energy_service.record_login.return_value = FakeLoginResult(
            streak_day=7,
            streak_continued=True,
            streak_broken=False,
            bonus_hearts_granted=3,
            energy_info=FakeEnergyInfo(current_hearts=5, is_full=True),
        )

        resp = client.post("/api/v1/energy/login")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["bonus_hearts_granted"] == 3
        assert data["data"]["streak_day"] == 7

    def test_record_login_service_error(
        self,
        client: TestClient,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Service error during login recording propagates correctly."""
        mock_energy_service.record_login.side_effect = AppError(
            code="CONFLICT_ALREADY_LOGGED_IN_TODAY",
            message="Already logged in today",
            http_status=409,
        )

        resp = client.post("/api/v1/energy/login")

        assert resp.status_code == 409


class TestGetStreak:
    """Tests for GET /api/v1/energy/streak."""

    def test_get_streak_success(
        self,
        client: TestClient,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Returns streak info for authenticated player."""
        mock_energy_service.get_streak.return_value = FakeStreakInfo()

        resp = client.get("/api/v1/energy/streak")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["current_streak"] == 5
        assert data["data"]["next_reward_threshold"] == 7
        assert data["data"]["days_until_reward"] == 2
        assert data["data"]["reward_hearts"] == 3
        assert data["data"]["last_login_date"] is not None

    def test_get_streak_no_login_history(
        self,
        client: TestClient,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Player with no login history gets null last_login_date."""
        mock_energy_service.get_streak.return_value = FakeStreakInfo(
            current_streak=0,
            last_login_date=None,
            next_reward_threshold=7,
            days_until_reward=7,
            reward_hearts=3,
        )

        resp = client.get("/api/v1/energy/streak")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["current_streak"] == 0
        assert data["data"]["last_login_date"] is None

    def test_get_streak_player_not_found(
        self,
        client: TestClient,
        mock_energy_service: AsyncMock,
    ) -> None:
        """Streak query for non-existent player returns 404."""
        mock_energy_service.get_streak.side_effect = AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
            http_status=404,
        )

        resp = client.get("/api/v1/energy/streak")

        assert resp.status_code == 404
