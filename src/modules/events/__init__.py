"""Events module for ChromaCrush.

Manages time-limited events, competitive seasons, leaderboards, and
reward distribution. This module is fully async -- all public service
methods are ``async def``.

Exports:
    EventService: Concrete service implementation.
    EventServiceProtocol: Protocol interface for dependency injection.
"""

from src.modules.events.dto import (
    EventCreate,
    EventDbUpdate,
    EventMatchCreate,
    EventUpdate,
    PaginatedResult,
    ParticipantCreate,
    ParticipantUpdate,
)
from src.modules.events.protocols import EventServiceProtocol
from src.modules.events.service import EventService
from src.modules.events.types import (
    BonusCondition,
    EntryRequirements,
    Event,
    EventFinalizationResult,
    EventLeaderboard,
    EventParticipant,
    EventRules,
    EventStatus,
    EventSummary,
    EventType,
    LeaderboardEntry,
    MatchEventStats,
    PlayerEventRank,
    PlayerEventSummary,
    RewardItem,
    RewardTier,
    ScheduledEventResult,
    ScoringType,
)

__all__ = [
    "BonusCondition",
    "EntryRequirements",
    "Event",
    "EventCreate",
    "EventDbUpdate",
    "EventFinalizationResult",
    "EventLeaderboard",
    "EventMatchCreate",
    "EventParticipant",
    "EventRules",
    "EventService",
    "EventServiceProtocol",
    "EventStatus",
    "EventSummary",
    "EventType",
    "EventUpdate",
    "LeaderboardEntry",
    "MatchEventStats",
    "PaginatedResult",
    "ParticipantCreate",
    "ParticipantUpdate",
    "PlayerEventRank",
    "PlayerEventSummary",
    "RewardItem",
    "RewardTier",
    "ScheduledEventResult",
    "ScoringType",
]
