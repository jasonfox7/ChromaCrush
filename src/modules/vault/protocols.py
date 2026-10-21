"""Vault service protocol.

Defines the public interface for the vault module. All methods are
``async def`` because they involve database operations.

Other modules and the presentation layer depend on this protocol
interface; the concrete ``VaultService`` implementation lives in
``src.modules.vault.service``.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from src.core.types.game import ArtifactId, PlayerId
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


class VaultServiceProtocol(Protocol):
    """Public interface for the vault module."""

    # ========== Artifact Management ==========

    async def add_artifact(
        self,
        player_id: PlayerId,
        artifact_type_id: str,
        source: str,
        source_id: str | None = None,
    ) -> VaultArtifact:
        """Add an artifact to a player's vault.

        Args:
            player_id: The owner's player ID.
            artifact_type_id: The artifact type from the definition catalog.
            source: How acquired (match_reward, event_reward, raid, purchase).
            source_id: Optional reference (match_id, event_id, raid_id).

        Returns:
            The created VaultArtifact.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            VALIDATION_INVALID_INPUT: If artifact_type_id not in catalog
                or max artifacts reached.
        """
        ...

    async def get_artifact(
        self,
        artifact_id: ArtifactId,
    ) -> VaultArtifact:
        """Get a specific artifact by ID.

        Args:
            artifact_id: The artifact's unique identifier.

        Returns:
            VaultArtifact entity.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact doesn't exist.
        """
        ...

    async def get_player_artifacts(
        self,
        player_id: PlayerId,
        rarity: ArtifactRarity | None = None,
        artifact_set: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[VaultArtifact]:
        """Get all artifacts in a player's vault with optional filtering.

        Args:
            player_id: The vault owner.
            rarity: Filter by rarity tier.
            artifact_set: Filter by set name.
            limit: Maximum results (1-100, default 50).
            offset: Pagination offset.

        Returns:
            PaginatedResult containing artifacts and pagination metadata.
        """
        ...

    async def get_vault_summary(
        self,
        player_id: PlayerId,
    ) -> VaultSummary:
        """Get a summary of a player's vault contents.

        Args:
            player_id: The vault owner.

        Returns:
            VaultSummary with counts by rarity and total value.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    async def remove_artifact(
        self,
        artifact_id: ArtifactId,
        reason: str,
    ) -> None:
        """Remove an artifact from vault.

        Args:
            artifact_id: The artifact to remove.
            reason: Why removed.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact doesn't exist.
        """
        ...

    async def transfer_artifact(
        self,
        artifact_id: ArtifactId,
        from_player_id: PlayerId,
        to_player_id: PlayerId,
        reason: str,
    ) -> VaultArtifact:
        """Transfer an artifact between players atomically.

        Args:
            artifact_id: The artifact to transfer.
            from_player_id: Current owner (for verification).
            to_player_id: New owner.
            reason: Why transferred.

        Returns:
            Updated VaultArtifact with new owner.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact doesn't exist.
            NOT_FOUND_PLAYER: If either player doesn't exist.
            VALIDATION_INVALID_INPUT: If from_player_id doesn't match owner.
        """
        ...

    # ========== Artifact Catalog ==========

    async def get_artifact_definition(
        self,
        artifact_type_id: str,
    ) -> ArtifactDefinition:
        """Get the definition for an artifact type.

        Args:
            artifact_type_id: The type identifier.

        Returns:
            ArtifactDefinition.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact type not in catalog.
        """
        ...

    async def list_artifact_definitions(
        self,
        rarity: ArtifactRarity | None = None,
        artifact_set: str | None = None,
    ) -> list[ArtifactDefinition]:
        """List all artifact definitions with optional filtering.

        Args:
            rarity: Filter by rarity tier.
            artifact_set: Filter by set name.

        Returns:
            List of matching ArtifactDefinitions.
        """
        ...

    # ========== Collection System ==========

    async def get_collection_progress(
        self,
        player_id: PlayerId,
        artifact_set: str | None = None,
    ) -> list[CollectionProgress]:
        """Get player's progress toward completing artifact sets.

        Args:
            player_id: The player.
            artifact_set: Specific set to check, or None for all.

        Returns:
            List of CollectionProgress entries.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        ...

    # ========== Shield System ==========

    async def activate_shield(
        self,
        player_id: PlayerId,
        duration_hours: int | None = None,
    ) -> Shield:
        """Activate raid protection shield for a player.

        Args:
            player_id: The player to protect.
            duration_hours: Override default duration.

        Returns:
            Shield entity with expiration time.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            CONFLICT_SHIELD_ALREADY_ACTIVE: If player already has active shield.
            VALIDATION_INVALID_INPUT: If duration_hours <= 0.
        """
        ...

    async def get_shield_status(
        self,
        player_id: PlayerId,
    ) -> Shield | None:
        """Get a player's current shield status.

        Args:
            player_id: The player.

        Returns:
            Active Shield if protected, None if unprotected.
        """
        ...

    async def deactivate_shield(
        self,
        player_id: PlayerId,
    ) -> None:
        """Manually deactivate a player's shield.

        Args:
            player_id: The player.

        Raises:
            VALIDATION_INVALID_INPUT: If no active shield exists.
        """
        ...

    async def is_protected(
        self,
        player_id: PlayerId,
    ) -> bool:
        """Check if a player is currently protected by a shield.

        Args:
            player_id: The player to check.

        Returns:
            True if shield is active and not expired.
        """
        ...

    # ========== Raid System ==========

    async def attempt_raid(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> RaidResult:
        """Attempt to raid another player's vault.

        Args:
            attacker_id: The raiding player.
            defender_id: The target player.

        Returns:
            RaidResult with success status and details.

        Raises:
            VALIDATION_INVALID_INPUT: If attacker == defender.
            FORBIDDEN_VAULT_PROTECTED: If defender has active shield.
            CONFLICT_RAID_COOLDOWN: If raided same player too recently.
        """
        ...

    async def can_raid(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> RaidEligibility:
        """Check if a raid is possible (without executing).

        Args:
            attacker_id: The potential attacker.
            defender_id: The potential target.

        Returns:
            RaidEligibility with can_raid bool and reason if not.
        """
        ...

    async def get_raid_history(
        self,
        player_id: PlayerId,
        as_attacker: bool = True,
        as_defender: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResult[RaidLog]:
        """Get raid history for a player.

        Args:
            player_id: The player.
            as_attacker: Include raids where player was attacker.
            as_defender: Include raids where player was defender.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            PaginatedResult containing raid log entries.
        """
        ...

    async def get_raid_cooldown(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> datetime | None:
        """Get when the cooldown expires for raiding a specific player.

        Args:
            attacker_id: The attacker.
            defender_id: The target.

        Returns:
            Cooldown expiration datetime, or None if no cooldown.
        """
        ...
