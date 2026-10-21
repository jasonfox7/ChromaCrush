"""Artifact sub-service for the vault module.

Handles artifact CRUD, catalog queries, collection progress, and vault
summaries. All dependencies arrive via ``__init__`` injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.types.game import ArtifactId, PlayerId
from src.modules.vault.collection import calculate_collection_progress
from src.modules.vault.dto import (
    ArtifactDefinition,
    ArtifactRarity,
    CollectionProgress,
    PaginatedResult,
    VaultArtifact,
    VaultSummary,
)

if TYPE_CHECKING:
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.artifact_definition_repository import (
        ArtifactDefinitionRepositoryProtocol,
    )
    from src.data.protocols.vault_artifact_repository import (
        VaultArtifactRepositoryProtocol,
    )
    from src.modules.player.protocols import PlayerServiceProtocol

# Maximum page size for paginated artifact queries.
_MAX_PAGE_LIMIT: int = 100


class ArtifactService:
    """Internal sub-service for artifact management and catalog operations.

    Not exported from the vault module -- used only by ``VaultService``.
    """

    def __init__(
        self,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        vault_artifact_repo: VaultArtifactRepositoryProtocol,
        artifact_definition_repo: ArtifactDefinitionRepositoryProtocol,
        max_artifacts_per_player: int,
    ) -> None:
        self._logger = logger
        self._errors = errors
        self._player_service = player_service
        self._vault_artifact_repo = vault_artifact_repo
        self._artifact_definition_repo = artifact_definition_repo
        self._max_artifacts_per_player = max_artifacts_per_player

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
            VALIDATION_INVALID_INPUT: If artifact_type_id is not in catalog
                or max artifacts reached.
        """
        # Verify player exists
        await self._player_service.get_player(player_id)

        # Verify artifact type exists in catalog
        definition_record = await self._artifact_definition_repo.find_by_type_id(
            artifact_type_id
        )
        if definition_record is None:
            raise self._errors.validation(
                f"Artifact type not found in catalog: {artifact_type_id}",
                code="VALIDATION_INVALID_INPUT",
                field="artifact_type_id",
                value=artifact_type_id,
            )

        # Check max artifacts limit
        current_count = await self._vault_artifact_repo.count_by_owner(player_id)
        if current_count >= self._max_artifacts_per_player:
            raise self._errors.validation(
                f"Vault is full ({self._max_artifacts_per_player} artifacts max)",
                code="VALIDATION_INVALID_INPUT",
                field="vault_capacity",
                current=current_count,
                max=self._max_artifacts_per_player,
            )

        # Create the artifact
        record = await self._vault_artifact_repo.create(
            owner_id=player_id,
            artifact_type_id=artifact_type_id,
            source=source,
            source_id=source_id,
        )

        definition = _record_to_definition(definition_record)
        artifact = _record_to_vault_artifact(record, definition)

        self._logger.info(
            "Artifact acquired",
            player_id=str(player_id),
            artifact_type_id=artifact_type_id,
            rarity=definition.rarity.value,
            source=source,
        )

        return artifact

    async def get_artifact(
        self,
        artifact_id: ArtifactId,
    ) -> VaultArtifact:
        """Get a specific artifact by ID.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact doesn't exist.
        """
        record = await self._vault_artifact_repo.find_by_id(artifact_id)
        if record is None:
            raise self._errors.not_found(
                f"Artifact not found: {artifact_id}",
                code="NOT_FOUND_ARTIFACT",
                artifact_id=str(artifact_id),
            )

        definition_record = await self._artifact_definition_repo.find_by_type_id(
            record.artifact_type_id
        )
        if definition_record is None:
            raise self._errors.internal(
                f"Artifact definition missing for type: {record.artifact_type_id}",
                code="INTERNAL_UNEXPECTED",
                artifact_type_id=record.artifact_type_id,
            )

        definition = _record_to_definition(definition_record)
        return _record_to_vault_artifact(record, definition)

    async def get_player_artifacts(
        self,
        player_id: PlayerId,
        rarity: ArtifactRarity | None = None,
        artifact_set: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[VaultArtifact]:
        """Get all artifacts in a player's vault with optional filtering."""
        if limit < 1 or limit > _MAX_PAGE_LIMIT:
            raise self._errors.validation(
                f"Limit must be between 1 and {_MAX_PAGE_LIMIT}",
                code="VALIDATION_INVALID_INPUT",
                field="limit",
                value=limit,
            )

        rarity_str = rarity.value if rarity is not None else None
        records, total = await self._vault_artifact_repo.find_by_owner(
            owner_id=player_id,
            rarity=rarity_str,
            artifact_set=artifact_set,
            limit=limit,
            offset=offset,
        )

        # Attach definitions
        artifacts = []
        for rec in records:
            def_record = await self._artifact_definition_repo.find_by_type_id(
                rec.artifact_type_id
            )
            if def_record is not None:
                definition = _record_to_definition(def_record)
                artifacts.append(_record_to_vault_artifact(rec, definition))

        return PaginatedResult(
            items=artifacts,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_vault_summary(
        self,
        player_id: PlayerId,
    ) -> VaultSummary:
        """Get a summary of a player's vault contents.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        # Verify player exists
        await self._player_service.get_player(player_id)

        total_artifacts = await self._vault_artifact_repo.count_by_owner(player_id)
        rarity_counts = await self._vault_artifact_repo.count_by_owner_and_rarity(
            player_id
        )

        # Map string rarity to ArtifactRarity enum
        by_rarity: dict[ArtifactRarity, int] = {}
        total_value = 0
        for rarity_str, count in rarity_counts.items():
            try:
                rarity_enum = ArtifactRarity(rarity_str)
                by_rarity[rarity_enum] = count
            except ValueError:
                pass

        # Calculate total value from owned artifacts
        all_records, _ = await self._vault_artifact_repo.find_by_owner(
            owner_id=player_id, limit=self._max_artifacts_per_player
        )
        for rec in all_records:
            def_record = await self._artifact_definition_repo.find_by_type_id(
                rec.artifact_type_id
            )
            if def_record is not None:
                total_value += def_record.base_value

        # Check collection completion
        all_sets = await self._artifact_definition_repo.list_all_sets()
        complete_sets: list[str] = []
        sets_in_progress: list[str] = []

        for artifact_set in all_sets:
            set_type_ids = await self._artifact_definition_repo.get_set_type_ids(
                artifact_set
            )
            owned_type_ids = await self._vault_artifact_repo.list_owned_type_ids(
                owner_id=player_id, artifact_set=artifact_set
            )

            owned_in_set = set(owned_type_ids) & set(set_type_ids)
            if len(owned_in_set) >= len(set_type_ids) and len(set_type_ids) > 0:
                complete_sets.append(artifact_set)
            elif len(owned_in_set) > 0:
                sets_in_progress.append(artifact_set)

        return VaultSummary(
            player_id=player_id,
            total_artifacts=total_artifacts,
            by_rarity=by_rarity,
            total_value=total_value,
            complete_sets=complete_sets,
            sets_in_progress=sets_in_progress,
        )

    async def remove_artifact(
        self,
        artifact_id: ArtifactId,
        reason: str,
    ) -> None:
        """Remove an artifact from vault.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact doesn't exist.
        """
        record = await self._vault_artifact_repo.find_by_id(artifact_id)
        if record is None:
            raise self._errors.not_found(
                f"Artifact not found: {artifact_id}",
                code="NOT_FOUND_ARTIFACT",
                artifact_id=str(artifact_id),
            )

        previous_owner = record.owner_id
        await self._vault_artifact_repo.delete(artifact_id)

        self._logger.info(
            "Artifact removed",
            artifact_id=str(artifact_id),
            previous_owner=str(previous_owner),
            reason=reason,
        )

    async def transfer_artifact(
        self,
        artifact_id: ArtifactId,
        from_player_id: PlayerId,
        to_player_id: PlayerId,
        reason: str,
    ) -> VaultArtifact:
        """Transfer an artifact between players atomically.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact doesn't exist.
            NOT_FOUND_PLAYER: If either player doesn't exist.
            VALIDATION_INVALID_INPUT: If from_player_id doesn't match owner.
        """
        # Verify both players exist
        await self._player_service.get_player(from_player_id)
        await self._player_service.get_player(to_player_id)

        # Get artifact and verify ownership
        record = await self._vault_artifact_repo.find_by_id(artifact_id)
        if record is None:
            raise self._errors.not_found(
                f"Artifact not found: {artifact_id}",
                code="NOT_FOUND_ARTIFACT",
                artifact_id=str(artifact_id),
            )

        if record.owner_id != from_player_id:
            raise self._errors.validation(
                "Artifact is not owned by the specified player",
                code="VALIDATION_INVALID_INPUT",
                field="from_player_id",
                artifact_owner=str(record.owner_id),
                expected_owner=str(from_player_id),
            )

        # Transfer
        updated_record = await self._vault_artifact_repo.update_owner(
            artifact_id, to_player_id
        )

        definition_record = await self._artifact_definition_repo.find_by_type_id(
            updated_record.artifact_type_id
        )
        if definition_record is None:
            raise self._errors.internal(
                f"Artifact definition missing for type: {updated_record.artifact_type_id}",
                code="INTERNAL_UNEXPECTED",
            )

        definition = _record_to_definition(definition_record)
        artifact = _record_to_vault_artifact(updated_record, definition)

        self._logger.info(
            "Artifact transferred",
            artifact_id=str(artifact_id),
            from_player=str(from_player_id),
            to_player=str(to_player_id),
            reason=reason,
        )

        return artifact

    # ========== Artifact Catalog ==========

    async def get_artifact_definition(
        self,
        artifact_type_id: str,
    ) -> ArtifactDefinition:
        """Get the definition for an artifact type.

        Raises:
            NOT_FOUND_ARTIFACT: If artifact type not in catalog.
        """
        record = await self._artifact_definition_repo.find_by_type_id(artifact_type_id)
        if record is None:
            raise self._errors.not_found(
                f"Artifact type not found: {artifact_type_id}",
                code="NOT_FOUND_ARTIFACT",
                artifact_type_id=artifact_type_id,
            )
        return _record_to_definition(record)

    async def list_artifact_definitions(
        self,
        rarity: ArtifactRarity | None = None,
        artifact_set: str | None = None,
    ) -> list[ArtifactDefinition]:
        """List all artifact definitions with optional filtering."""
        rarity_str = rarity.value if rarity is not None else None
        records = await self._artifact_definition_repo.list_all(
            rarity=rarity_str,
            artifact_set=artifact_set,
        )
        return [_record_to_definition(r) for r in records]

    # ========== Collection System ==========

    async def get_collection_progress(
        self,
        player_id: PlayerId,
        artifact_set: str | None = None,
    ) -> list[CollectionProgress]:
        """Get player's progress toward completing artifact sets.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
        """
        # Verify player exists
        await self._player_service.get_player(player_id)

        if artifact_set is not None:
            sets_to_check = [artifact_set]
        else:
            sets_to_check = await self._artifact_definition_repo.list_all_sets()

        progress_list: list[CollectionProgress] = []
        for a_set in sets_to_check:
            set_type_ids = await self._artifact_definition_repo.get_set_type_ids(a_set)
            owned_type_ids = await self._vault_artifact_repo.list_owned_type_ids(
                owner_id=player_id, artifact_set=a_set
            )

            progress = calculate_collection_progress(
                owned_type_ids=owned_type_ids,
                set_type_ids=set_type_ids,
                set_name=a_set,
                artifact_set=a_set,
            )
            progress_list.append(progress)

        return progress_list


# ========== Module-level Helpers ==========


def _record_to_definition(record: object) -> ArtifactDefinition:
    """Convert a definition record to an ArtifactDefinition DTO."""
    return ArtifactDefinition(
        type_id=record.type_id,
        name=record.name,
        description=record.description or "",
        rarity=ArtifactRarity(record.rarity),
        artifact_set=record.artifact_set,
        set_position=record.set_position,
        base_value=record.base_value,
        image_url=record.image_url,
    )


def _record_to_vault_artifact(
    record: object, definition: ArtifactDefinition
) -> VaultArtifact:
    """Convert a vault artifact record + definition to a VaultArtifact DTO."""
    return VaultArtifact(
        id=ArtifactId(record.id),
        owner_id=PlayerId(record.owner_id),
        artifact_type_id=record.artifact_type_id,
        definition=definition,
        acquired_at=record.acquired_at,
        source=record.source,
        source_id=record.source_id,
    )
