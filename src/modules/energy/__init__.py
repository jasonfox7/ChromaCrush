"""Energy module for ChromaCrush.

Manages the hearts/energy system that gates match play. Implements
heart consumption, regeneration, daily login streaks, and bonus heart
grants. This module is fully async -- all public service methods are
``async def``.

Exports:
    EnergyService: Concrete service implementation.
    EnergyServiceProtocol: Protocol interface for dependency injection.
    BonusSource: Enum of bonus heart sources.
    EnergyInfo: Complete energy state DTO.
    EnergyConsumeResult: Result of consuming hearts.
    RegenResult: Result of applying regeneration.
    TimeToHeartResult: Time until next heart regenerates.
    LoginResult: Result of recording a login.
    StreakInfo: Player's streak information.
    BonusGrantResult: Result of granting bonus hearts.
"""

from src.modules.energy.dto import (
    BonusGrantResult,
    BonusSource,
    EnergyConsumeResult,
    EnergyInfo,
    LoginResult,
    RegenResult,
    StreakInfo,
    TimeToHeartResult,
)
from src.modules.energy.protocols import EnergyServiceProtocol
from src.modules.energy.service import EnergyService

__all__ = [
    "BonusGrantResult",
    "BonusSource",
    "EnergyConsumeResult",
    "EnergyInfo",
    "EnergyService",
    "EnergyServiceProtocol",
    "LoginResult",
    "RegenResult",
    "StreakInfo",
    "TimeToHeartResult",
]
