"""Vault module for ChromaCrush.

Manages artifact collection, raids, shields, and collection tracking.
This module is fully async -- all public service methods are ``async def``.

Exports:
    VaultService: Concrete service implementation.
    VaultServiceProtocol: Protocol interface for dependency injection.
"""

from src.modules.vault.dto import (
    ArtifactDefinition,
    ArtifactRarity,
    CollectionProgress,
    PaginatedResult,
    RaidEligibility,
    RaidLog,
    RaidResult,
    Shield,
    VaultArtifact,
    VaultSummary,
)
from src.modules.vault.protocols import VaultServiceProtocol
from src.modules.vault.service import VaultService

__all__ = [
    "ArtifactDefinition",
    "ArtifactRarity",
    "CollectionProgress",
    "PaginatedResult",
    "RaidEligibility",
    "RaidLog",
    "RaidResult",
    "Shield",
    "VaultArtifact",
    "VaultService",
    "VaultServiceProtocol",
    "VaultSummary",
]
