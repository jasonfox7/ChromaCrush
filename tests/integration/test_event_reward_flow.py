"""Integration tests for event reward flow.

Validates the EventService cross-module workflow using real PostgreSQL
and Redis. Tests cover: event creation, joining, leaving, leaderboard,
finalization, error cases, and listing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from src.core.errors import AppError
from src.core.types.game import EventId, PlayerId
from src.core.types.player import PlayerType
from src.modules.events.dto import EventCreate, EventDbUpdate
from src.modules.events.types import EventStatus, EventType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_player(factory, username: str = "alice") -> PlayerId:
    """Create a human player and return their PlayerId."""
    p = await factory.player_service.create_player(
        username=username,
        player_type=PlayerType.HUMAN,
    )
    return PlayerId(p.id)


def _make_event_data(
    *,
    name: str = "Test Flash Event",
    description: str = "A test event",
    event_type: str = "flash",
    scoring_type: str = "total_score",
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    entry_requirements: dict | None = None,
    reward_tiers: list[dict] | None = None,
    rules: dict | None = None,
    max_participants: int | None = None,
) -> EventCreate:
    """Build an EventCreate DTO with sensible defaults."""
    now = datetime.now(timezone.utc)
    return EventCreate(
        name=name,
        description=description,
        event_type=event_type,
        scoring_type=scoring_type,
        start_at=start_at or (now + timedelta(hours=1)),
        end_at=end_at or (now + timedelta(hours=5)),
        entry_requirements=entry_requirements or {},
        reward_tiers=reward_tiers or [],
        rules=rules or {},
        max_participants=max_participants,
    )


async def _create_active_event(factory, **kwargs) -> EventId:
    """Create an event and transition it to ACTIVE status."""
    now = datetime.now(timezone.utc)
    data = _make_event_data(
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=4),
        **kwargs,
    )
    event = await factory.event_service.create_event(data)
    await factory.event_repo.update(
        event.id,
        EventDbUpdate(status=EventStatus.ACTIVE.value),
    )
    return event.id


async def _create_ended_event(factory, **kwargs) -> EventId:
    """Create an event and transition it to ENDED status."""
    now = datetime.now(timezone.utc)
    data = _make_event_data(
        start_at=now - timedelta(hours=5),
        end_at=now - timedelta(hours=1),
        **kwargs,
    )
    event = await factory.event_service.create_event(data)
    await factory.event_repo.update(
        event.id,
        EventDbUpdate(status=EventStatus.ENDED.value),
    )
    return event.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEventWorkflow:
    """Integration tests for the event lifecycle."""

    async def test_create_event_happy_path(self, factory):
        """create_event returns an event with SCHEDULED status."""
        now = datetime.now(timezone.utc)
        data = _make_event_data(
            name="Weekend Flash",
            start_at=now + timedelta(hours=2),
            end_at=now + timedelta(hours=6),
        )

        event = await factory.event_service.create_event(data)

        assert event.status == EventStatus.SCHEDULED
        assert event.name == "Weekend Flash"
        assert event.event_type == EventType.FLASH
        assert event.participant_count == 0
        assert event.finalized_at is None

    async def test_join_event_happy_path(self, factory):
        """A player can join an ACTIVE event and gets a participant record."""
        player_id = await _create_player(factory, "joiner")
        event_id = await _create_active_event(factory)

        participant = await factory.event_service.join_event(event_id, player_id)

        assert participant.event_id == event_id
        assert participant.player_id == player_id
        assert participant.total_score == 0
        assert participant.matches_played == 0
        assert participant.rewards_claimed is False

    async def test_join_event_not_found_raises(self, factory):
        """Joining a nonexistent event raises NOT_FOUND_EVENT."""
        player_id = await _create_player(factory, "ghost_joiner")
        fake_event_id = EventId(UUID("00000000-0000-0000-0000-000000000099"))

        with pytest.raises(AppError) as exc_info:
            await factory.event_service.join_event(fake_event_id, player_id)

        assert exc_info.value.code == "NOT_FOUND_EVENT"

    async def test_leave_event_happy_path(self, factory):
        """A player can leave an event they joined."""
        player_id = await _create_player(factory, "leaver")
        event_id = await _create_active_event(factory)

        await factory.event_service.join_event(event_id, player_id)
        await factory.event_service.leave_event(event_id, player_id)

        raw = await factory.event_participant_repo.find_by_event_and_player(
            event_id,
            player_id,
        )
        assert raw is not None
        assert raw.left_at is not None

    async def test_get_leaderboard_empty(self, factory):
        """Leaderboard for an event with no participants returns empty entries."""
        event_id = await _create_active_event(factory, name="Empty Board Event")

        leaderboard = await factory.event_service.get_leaderboard(event_id)

        assert leaderboard.event_id == event_id
        assert leaderboard.total_participants == 0
        assert leaderboard.entries == []

    async def test_finalize_event_already_finalized_raises(self, factory):
        """Finalizing an already-finalized event raises CONFLICT_EVENT_ALREADY_FINALIZED."""
        event_id = await _create_ended_event(factory, name="Double Finalize")

        await factory.event_service.finalize_event(event_id)

        with pytest.raises(AppError) as exc_info:
            await factory.event_service.finalize_event(event_id)

        assert exc_info.value.code == "CONFLICT_EVENT_ALREADY_FINALIZED"

    async def test_finalize_event_not_ended_raises(self, factory):
        """Finalizing a SCHEDULED event raises an error."""
        now = datetime.now(timezone.utc)
        data = _make_event_data(
            name="Future Event",
            start_at=now + timedelta(hours=10),
            end_at=now + timedelta(hours=14),
        )
        event = await factory.event_service.create_event(data)

        with pytest.raises(AppError) as exc_info:
            await factory.event_service.finalize_event(event.id)

        assert exc_info.value.code == "CONFLICT_EVENT_NOT_ACTIVE"

    async def test_list_events_returns_created(self, factory):
        """list_events returns events after creation."""
        now = datetime.now(timezone.utc)
        data = _make_event_data(
            name="Listable Event",
            start_at=now + timedelta(hours=1),
            end_at=now + timedelta(hours=5),
        )
        await factory.event_service.create_event(data)

        result = await factory.event_service.list_events()

        assert result.total >= 1
        names = [e.name for e in result.items]
        assert "Listable Event" in names
