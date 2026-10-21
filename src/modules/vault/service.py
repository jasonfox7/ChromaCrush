"""Vault service implementation.

Thin facade that delegates to internal sub-services for artifact
management, raids, and shields. All dependencies arrive via ``__init__``
injection; no direct imports of core services or environment access.

The public interface of ``VaultService`` is unchanged -- each method is
a one-line delegation to the appropriate sub-service.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.core.types.game import ArtifactId, PlayerId
from src.modules.vault.artifact_service import ArtifactService
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
from src.modules.vault.raid_service import RaidService
from src.modules.vault.shield_service import ShieldService

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.data_context import DataContextProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.artifact_definition_repository import (
        ArtifactDefinitionRepositoryProtocol,
    )
    from src.data.protocols.raid_log_repository import RaidLogRepositoryProtocol
    from src.data.protocols.vault_artifact_repository import (
        VaultArtifactRepositoryProtocol,
    )
    from src.data.protocols.vault_shield_repository import (
        VaultShieldRepositoryProtocol,
    )
    from src.modules.player.protocols import PlayerServiceProtocol


class VaultService:
    """Concrete implementation of ``VaultServiceProtocol``.

    Manages artifact collection, raids, shields, and collection tracking.
    All public methods are ``async def`` as they involve database operations.

    Args:
        config: Configuration service for reading settings.
        logger: Structured logging service.
        errors: Error factory service.
        player_service: Player module for existence checks.
        vault_artifact_repo: Repository for vault artifacts.
        vault_shield_repo: Repository for vault shields.
        artifact_definition_repo: Repository for artifact catalog.
        raid_log_repo: Repository for raid history.
        data_ctx: Data context for transaction boundaries (optional).
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        vault_artifact_repo: VaultArtifactRepositoryProtocol,
        vault_shield_repo: VaultShieldRepositoryProtocol,
        artifact_definition_repo: ArtifactDefinitionRepositoryProtocol,
        raid_log_repo: RaidLogRepositoryProtocol,
        data_ctx: DataContextProtocol | None = None,
        card_service: object | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._player_service = player_service
        self._vault_artifact_repo = vault_artifact_repo
        self._vault_shield_repo = vault_shield_repo
        self._artifact_definition_repo = artifact_definition_repo
        self._raid_log_repo = raid_log_repo
        # Transaction boundary context for atomic operations (e.g. attempt_raid,
        # transfer_artifact). TODO: wrap multi-step mutations in
        # async with self._data_ctx.session() once service-layer transaction
        # orchestration pattern is established.
        self._data_ctx = data_ctx

        # Cache configuration values read at init time
        shield_duration_hours: int = config.get("vault.shield_duration_hours", 8)
        raid_cooldown_hours: int = config.get("vault.raid_cooldown_hours", 24)
        raid_energy_cost: int = config.get("vault.raid_energy_cost", 1)
        raid_success_base_chance: float = config.get(
            "vault.raid_success_base_chance", 0.7
        )
        empty_vault_protection: bool = config.get("vault.empty_vault_protection", True)
        legendary_steal_chance_modifier: float = config.get(
            "vault.legendary_steal_chance_modifier", 0.5
        )
        max_artifacts_per_player: int = config.get(
            "vault.max_artifacts_per_player", 500
        )

        # ----- Build internal sub-services -----

        self._artifact_service = ArtifactService(
            logger=logger,
            errors=errors,
            player_service=player_service,
            vault_artifact_repo=vault_artifact_repo,
            artifact_definition_repo=artifact_definition_repo,
            max_artifacts_per_player=max_artifacts_per_player,
        )

        self._shield_service = ShieldService(
            logger=logger,
            errors=errors,
            player_service=player_service,
            vault_shield_repo=vault_shield_repo,
            shield_duration_hours=shield_duration_hours,
        )

        # Extract build_modifier_engine callable from card service if available.
        build_engine = None
        if card_service is not None and hasattr(card_service, "build_modifier_engine"):
            build_engine = card_service.build_modifier_engine

        self._raid_service = RaidService(
            logger=logger,
            errors=errors,
            player_service=player_service,
            vault_artifact_repo=vault_artifact_repo,
            artifact_definition_repo=artifact_definition_repo,
            raid_log_repo=raid_log_repo,
            shield_service=self._shield_service,
            raid_cooldown_hours=raid_cooldown_hours,
            raid_energy_cost=raid_energy_cost,
            raid_success_base_chance=raid_success_base_chance,
            empty_vault_protection=empty_vault_protection,
            legendary_steal_chance_modifier=legendary_steal_chance_modifier,
            max_artifacts_per_player=max_artifacts_per_player,
            build_modifier_engine=build_engine,
        )

    # ========== Artifact Management ==========

    async def add_artifact(
        self,
        player_id: PlayerId,
        artifact_type_id: str,
        source: str,
        source_id: str | None = None,
    ) -> VaultArtifact:
        return await self._artifact_service.add_artifact(
            player_id, artifact_type_id, source, source_id
        )

    async def get_artifact(
        self,
        artifact_id: ArtifactId,
    ) -> VaultArtifact:
        return await self._artifact_service.get_artifact(artifact_id)

    async def get_player_artifacts(
        self,
        player_id: PlayerId,
        rarity: ArtifactRarity | None = None,
        artifact_set: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[VaultArtifact]:
        return await self._artifact_service.get_player_artifacts(
            player_id, rarity, artifact_set, limit, offset
        )

    async def get_vault_summary(
        self,
        player_id: PlayerId,
    ) -> VaultSummary:
        return await self._artifact_service.get_vault_summary(player_id)

    async def remove_artifact(
        self,
        artifact_id: ArtifactId,
        reason: str,
    ) -> None:
        return await self._artifact_service.remove_artifact(artifact_id, reason)

    async def transfer_artifact(
        self,
        artifact_id: ArtifactId,
        from_player_id: PlayerId,
        to_player_id: PlayerId,
        reason: str,
    ) -> VaultArtifact:
        return await self._artifact_service.transfer_artifact(
            artifact_id, from_player_id, to_player_id, reason
        )

    # ========== Artifact Catalog ==========

    async def get_artifact_definition(
        self,
        artifact_type_id: str,
    ) -> ArtifactDefinition:
        return await self._artifact_service.get_artifact_definition(artifact_type_id)

    async def list_artifact_definitions(
        self,
        rarity: ArtifactRarity | None = None,
        artifact_set: str | None = None,
    ) -> list[ArtifactDefinition]:
        return await self._artifact_service.list_artifact_definitions(
            rarity, artifact_set
        )

    # ========== Collection System ==========

    async def get_collection_progress(
        self,
        player_id: PlayerId,
        artifact_set: str | None = None,
    ) -> list[CollectionProgress]:
        return await self._artifact_service.get_collection_progress(
            player_id, artifact_set
        )

    # ========== Shield System ==========

    async def activate_shield(
        self,
        player_id: PlayerId,
        duration_hours: int | None = None,
    ) -> Shield:
        return await self._shield_service.activate_shield(player_id, duration_hours)

    async def get_shield_status(
        self,
        player_id: PlayerId,
    ) -> Shield | None:
        return await self._shield_service.get_shield_status(player_id)

    async def deactivate_shield(
        self,
        player_id: PlayerId,
    ) -> None:
        return await self._shield_service.deactivate_shield(player_id)

    async def is_protected(
        self,
        player_id: PlayerId,
    ) -> bool:
        return await self._shield_service.is_protected(player_id)

    # ========== Raid System ==========

    async def attempt_raid(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> RaidResult:
        return await self._raid_service.attempt_raid(attacker_id, defender_id)

    async def can_raid(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> RaidEligibility:
        return await self._raid_service.can_raid(attacker_id, defender_id)

    async def get_raid_history(
        self,
        player_id: PlayerId,
        as_attacker: bool = True,
        as_defender: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResult[RaidLog]:
        return await self._raid_service.get_raid_history(
            player_id, as_attacker, as_defender, limit, offset
        )

    async def get_raid_cooldown(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> datetime | None:
        return await self._raid_service.get_raid_cooldown(attacker_id, defender_id)
