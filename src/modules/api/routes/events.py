"""Event route handlers.

Provides ``/api/v1/events/*`` endpoints for event management:
listing active events, event details, joining events, leaderboard
retrieval, and player event status.

All handlers delegate to ``event_service`` retrieved from
``request.app.state``. Responses flow through the ``ResponseAdapter``
envelope. ``AppError`` exceptions propagate to the error handler
middleware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.core.types.game import EventId, PlayerId
from src.modules.api.dependencies import (
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)

from src.modules.events.types import EventStatus

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter
    from src.modules.events.protocols import EventServiceProtocol
    from src.modules.events.types import (
        Event,
        EventLeaderboard,
        EventParticipant,
        EventSummary,
        LeaderboardEntry,
    )

router = APIRouter(prefix="/api/v1/events", tags=["events"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event_to_dict(event: Event) -> dict[str, Any]:
    """Convert an Event to a JSON-serializable dict.

    Args:
        event: The full event domain object.

    Returns:
        Dict matching the EventResponse schema.
    """
    return {
        "event_id": str(event.id),
        "name": event.name,
        "event_type": event.event_type.value,
        "status": event.status.value,
        "start_time": event.start_at.isoformat(),
        "end_time": event.end_at.isoformat(),
        "max_participants": event.max_participants,
        "current_participants": event.participant_count,
        "description": event.description,
    }


def _summary_to_dict(summary: EventSummary) -> dict[str, Any]:
    """Convert an EventSummary to a JSON-serializable dict.

    Args:
        summary: The abbreviated event summary object.

    Returns:
        Dict matching the event list response schema.
    """
    return {
        "event_id": str(summary.id),
        "name": summary.name,
        "event_type": summary.event_type.value,
        "status": summary.status.value,
        "start_time": summary.start_at.isoformat(),
        "end_time": summary.end_at.isoformat(),
        "current_participants": summary.participant_count,
        "time_remaining_seconds": summary.time_remaining_seconds,
    }


def _participant_to_dict(participant: EventParticipant) -> dict[str, Any]:
    """Convert an EventParticipant to a JSON-serializable dict.

    Args:
        participant: Participant domain object.

    Returns:
        Dict matching the EventParticipantResponse schema.
    """
    return {
        "event_id": str(participant.event_id),
        "player_id": str(participant.player_id),
        "score": participant.total_score,
        "rank": participant.current_rank,
        "matches_played": participant.matches_played,
        "joined_at": participant.joined_at.isoformat(),
    }


def _leaderboard_entry_to_dict(entry: LeaderboardEntry) -> dict[str, Any]:
    """Convert a LeaderboardEntry to a JSON-serializable dict.

    Args:
        entry: Single leaderboard entry.

    Returns:
        Dict matching the LeaderboardEntryResponse schema.
    """
    return {
        "rank": entry.rank,
        "player_id": str(entry.player_id),
        "username": entry.player_username,
        "score": entry.score,
        "matches_played": entry.matches_played,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_events(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """List currently active events with pagination."""
    svc: EventServiceProtocol = request.app.state.event_service

    result = await svc.list_events(
        status=EventStatus.ACTIVE, limit=limit, offset=offset,
    )

    items = [_summary_to_dict(e) for e in result.items]
    return response.success(
        data={
            "events": items,
            "total": result.total,
            "limit": result.limit,
            "offset": result.offset,
        },
        correlation_id=correlation_id,
    )


@router.get("/{event_id}")
async def get_event(
    event_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get details for a specific event."""
    svc: EventServiceProtocol = request.app.state.event_service

    event: Event = await svc.get_event(EventId(UUID(event_id)))
    data = _event_to_dict(event)
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/{event_id}/join")
async def join_event(
    event_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Join an event as the authenticated player."""
    player_id = get_current_player_id(request)
    svc: EventServiceProtocol = request.app.state.event_service

    participant: EventParticipant = await svc.join_event(
        EventId(UUID(event_id)),
        PlayerId(UUID(player_id)),
    )

    data = _participant_to_dict(participant)
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/{event_id}/leaderboard")
async def get_leaderboard(
    event_id: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the leaderboard for an event.

    Includes the requesting player's rank if they are a participant.
    """
    player_id = get_current_player_id(request)
    svc: EventServiceProtocol = request.app.state.event_service

    leaderboard: EventLeaderboard = await svc.get_leaderboard(
        EventId(UUID(event_id)),
        limit=limit,
        offset=offset,
    )

    entries = [_leaderboard_entry_to_dict(e) for e in leaderboard.entries]

    # Determine the requesting player's rank if they are a participant
    player_rank: int | None = None
    try:
        participant = await svc.get_event_participant(
            EventId(UUID(event_id)),
            PlayerId(UUID(player_id)),
        )
        player_rank = participant.current_rank
    except Exception:
        # Player is not a participant -- rank stays None
        pass

    data = {
        "event_id": str(leaderboard.event_id),
        "entries": entries,
        "total_participants": leaderboard.total_participants,
        "player_rank": player_rank,
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/{event_id}/status")
async def get_player_event_status(
    event_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the authenticated player's status in an event."""
    player_id = get_current_player_id(request)
    svc: EventServiceProtocol = request.app.state.event_service

    participant: EventParticipant = await svc.get_event_participant(
        EventId(UUID(event_id)),
        PlayerId(UUID(player_id)),
    )

    # Determine if the event is currently active
    event: Event = await svc.get_event(EventId(UUID(event_id)))

    from src.modules.events.types import EventStatus

    is_active = event.status == EventStatus.ACTIVE

    data = {
        "event_id": str(participant.event_id),
        "player_id": str(participant.player_id),
        "score": participant.total_score,
        "rank": participant.current_rank,
        "matches_played": participant.matches_played,
        "is_active": is_active,
    }
    return response.success(data=data, correlation_id=correlation_id)
