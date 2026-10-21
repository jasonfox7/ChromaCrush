"""Raid sub-service for the vault module.

Handles raid attempts, eligibility checks, raid history, and cooldown
queries. Uses ``raid_engine.py`` for pure computation. All dependencies
arrive via ``__init__`` injection.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Awaitable

from src.core.types.game import ArtifactId, PlayerId
from src.modules.vault.dto import (
    ArtifactDefinition,
    ArtifactRarity,
    PaginatedResult,
    RaidEligibility,
    RaidLog,
    RaidResult,
    VaultArtifact,
)
from src.modules.vault.raid_engine import (
    calculate_raid_success,
    is_raid_on_cooldown,
    select_raid_target_artifact,
)

if TYPE_CHECKING:
    from uuid import UUID

    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.artifact_definition_repository import (
        ArtifactDefinitionRepositoryProtocol,
    )
    from src.data.protocols.raid_log_repository import RaidLogRepositoryProtocol
    from src.data.protocols.vault_artifact_repository import (
        VaultArtifactRepositoryProtocol,
    )
    from src.modules.player.protocols import PlayerServiceProtocol
    from src.modules.vault.shield_service import ShieldService


class RaidService:
    """Internal sub-service for raid operations.

    Not exported from the vault module -- used only by ``VaultService``.
    """

    def __init__(
        self,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        vault_artifact_repo: VaultArtifactRepositoryProtocol,
        artifact_definition_repo: ArtifactDefinitionRepositoryProtocol,
        raid_log_repo: RaidLogRepositoryProtocol,
        shield_service: ShieldService,
        raid_cooldown_hours: int,
        raid_energy_cost: int,
        raid_success_base_chance: float,
        empty_vault_protection: bool,
        legendary_steal_chance_modifier: float,
        max_artifacts_per_player: int,
        build_modifier_engine: Callable[[UUID], Awaitable[object]] | None = None,
    ) -> None:
        self._logger = logger
        self._errors = errors
        self._player_service = player_service
        self._vault_artifact_repo = vault_artifact_repo
        self._artifact_definition_repo = artifact_definition_repo
        self._raid_log_repo = raid_log_repo
        self._shield_service = shield_service
        self._raid_cooldown_hours = raid_cooldown_hours
        self._raid_energy_cost = raid_energy_cost
        self._raid_success_base_chance = raid_success_base_chance
        self._empty_vault_protection = empty_vault_protection
        self._legendary_steal_chance_modifier = legendary_steal_chance_modifier
        self._max_artifacts_per_player = max_artifacts_per_player
        self._build_modifier_engine = build_modifier_engine

    # ========== Raid System ==========

    async def attempt_raid(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> RaidResult:
        """Attempt to raid another player's vault.

        Raises:
            VALIDATION_INVALID_INPUT: If attacker == defender.
            FORBIDDEN_VAULT_PROTECTED: If defender has active shield.
            CONFLICT_RAID_COOLDOWN: If raided same player too recently.
        """
        now = datetime.now(timezone.utc)

        # 1. Validate attacker != defender
        if attacker_id == defender_id:
            raise self._errors.validation(
                "Cannot raid your own vault",
                code="VALIDATION_INVALID_INPUT",
                field="defender_id",
            )

        # 2. Verify both players exist
        await self._player_service.get_player(attacker_id)
        await self._player_service.get_player(defender_id)

        # 3. Check defender protection (shield)
        defender_protected = await self._shield_service.is_protected(defender_id)
        if defender_protected:
            shield = await self._shield_service.get_shield_status(defender_id)
            expires_at = shield.expires_at if shield else None
            self._logger.warn(
                "Raid blocked by shield",
                attacker_id=str(attacker_id),
                defender_id=str(defender_id),
                shield_expires_at=expires_at.isoformat() if expires_at else "unknown",
            )
            raise self._errors.forbidden(
                "Defender is protected by an active shield",
                code="FORBIDDEN_VAULT_PROTECTED",
                defender_id=str(defender_id),
                shield_expires_at=expires_at.isoformat() if expires_at else None,
            )

        # 3b. Check defender's equipped cards for raid protection
        if self._build_modifier_engine is not None:
            engine = await self._build_modifier_engine(defender_id)
            if hasattr(engine, "check_raid_protection"):
                seed = int(time.time() * 1000) & 0x7FFFFFFF
                blocked, applied = engine.check_raid_protection(seed)
                if blocked:
                    desc = applied[0].description if applied else "Card protection"
                    self._logger.info(
                        "Raid blocked by card protection",
                        attacker_id=str(attacker_id),
                        defender_id=str(defender_id),
                        card_effect=desc,
                    )
                    raise self._errors.forbidden(
                        f"Raid blocked: {desc}",
                        code="FORBIDDEN_CARD_PROTECTION",
                        defender_id=str(defender_id),
                    )

        # 4. Check cooldown between attacker and defender
        last_raid_record = await self._raid_log_repo.find_last_raid_between(
            attacker_id, defender_id
        )
        last_raid_ts = last_raid_record.timestamp if last_raid_record else None
        on_cooldown, cooldown_expires = is_raid_on_cooldown(
            last_raid_ts, self._raid_cooldown_hours
        )
        if on_cooldown:
            self._logger.warn(
                "Raid blocked by cooldown",
                attacker_id=str(attacker_id),
                defender_id=str(defender_id),
                cooldown_expires_at=(
                    cooldown_expires.isoformat() if cooldown_expires else "unknown"
                ),
            )
            raise self._errors.conflict(
                "Raid cooldown active for this target",
                code="CONFLICT_RAID_COOLDOWN",
                attacker_id=str(attacker_id),
                defender_id=str(defender_id),
                cooldown_expires_at=(
                    cooldown_expires.isoformat() if cooldown_expires else None
                ),
            )

        # 5. Check empty vault protection
        defender_count = await self._vault_artifact_repo.count_by_owner(defender_id)
        if self._empty_vault_protection and defender_count == 0:
            # Empty vault -- raid fails automatically
            raid_record = await self._raid_log_repo.create(
                attacker_id=attacker_id,
                defender_id=defender_id,
                success=False,
            )

            self._logger.info(
                "Raid attempted",
                attacker_id=str(attacker_id),
                defender_id=str(defender_id),
                success=False,
                artifact_id="none",
            )

            return RaidResult(
                raid_id=raid_record.id,
                attacker_id=attacker_id,
                defender_id=defender_id,
                success=False,
                stolen_artifact=None,
                timestamp=now,
                message="Defender's vault is empty",
            )

        # 6. Select random artifact from defender's vault (fetch all for weighting)
        defender_artifacts, _ = await self._vault_artifact_repo.find_by_owner(
            owner_id=defender_id, limit=self._max_artifacts_per_player
        )

        # Enrich with rarity for weighting
        enriched_artifacts = []
        for rec in defender_artifacts:
            def_record = await self._artifact_definition_repo.find_by_type_id(
                rec.artifact_type_id
            )
            rarity_str = def_record.rarity if def_record else "common"
            rec.rarity = rarity_str
            enriched_artifacts.append(rec)

        target_artifact = select_raid_target_artifact(enriched_artifacts)

        if target_artifact is None:
            # No artifacts to steal
            raid_record = await self._raid_log_repo.create(
                attacker_id=attacker_id,
                defender_id=defender_id,
                success=False,
            )

            self._logger.info(
                "Raid attempted",
                attacker_id=str(attacker_id),
                defender_id=str(defender_id),
                success=False,
                artifact_id="none",
            )

            return RaidResult(
                raid_id=raid_record.id,
                attacker_id=attacker_id,
                defender_id=defender_id,
                success=False,
                stolen_artifact=None,
                timestamp=now,
                message="No artifacts available to steal",
            )

        # 7. Calculate raid success
        target_rarity = getattr(target_artifact, "rarity", "common")
        success = calculate_raid_success(
            self._raid_success_base_chance,
            target_rarity,
            self._legendary_steal_chance_modifier,
        )

        stolen_artifact: VaultArtifact | None = None
        artifact_id_for_log = None
        artifact_type_for_log = None

        if success:
            # Transfer artifact from defender to attacker
            updated_record = await self._vault_artifact_repo.update_owner(
                target_artifact.id, attacker_id
            )

            def_record = await self._artifact_definition_repo.find_by_type_id(
                updated_record.artifact_type_id
            )
            if def_record is not None:
                definition = _record_to_definition(def_record)
                stolen_artifact = _record_to_vault_artifact(updated_record, definition)

            artifact_id_for_log = target_artifact.id
            artifact_type_for_log = target_artifact.artifact_type_id

            self._logger.info(
                "Artifact transferred",
                artifact_id=str(target_artifact.id),
                from_player=str(defender_id),
                to_player=str(attacker_id),
                reason="raid_stolen",
            )

        # 8. Create raid log
        raid_record = await self._raid_log_repo.create(
            attacker_id=attacker_id,
            defender_id=defender_id,
            success=success,
            artifact_id=artifact_id_for_log,
            artifact_type_id=artifact_type_for_log,
        )

        self._logger.info(
            "Raid attempted",
            attacker_id=str(attacker_id),
            defender_id=str(defender_id),
            success=success,
            artifact_id=str(artifact_id_for_log) if artifact_id_for_log else "none",
        )

        if success and stolen_artifact:
            message = f"Raid successful! Stole {stolen_artifact.definition.name} ({stolen_artifact.definition.rarity.value})"
        elif success:
            message = "Raid successful!"
        else:
            message = "Raid failed. The artifact was too well guarded."

        return RaidResult(
            raid_id=raid_record.id,
            attacker_id=attacker_id,
            defender_id=defender_id,
            success=success,
            stolen_artifact=stolen_artifact,
            timestamp=now,
            message=message,
        )

    async def can_raid(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> RaidEligibility:
        """Check if a raid is possible (without executing).

        Returns:
            RaidEligibility with can_raid bool and reason if not.
        """
        # Self-raid check
        if attacker_id == defender_id:
            self._logger.debug(
                "Raid eligibility check",
                attacker_id=str(attacker_id),
                defender_id=str(defender_id),
                can_raid=False,
                reason="self_raid",
            )
            return RaidEligibility(
                can_raid=False,
                reason="Cannot raid your own vault",
            )

        # Verify both players exist
        try:
            await self._player_service.get_player(attacker_id)
            await self._player_service.get_player(defender_id)
        except Exception:
            return RaidEligibility(
                can_raid=False,
                reason="One or both players not found",
            )

        # Shield check
        if await self._shield_service.is_protected(defender_id):
            shield = await self._shield_service.get_shield_status(defender_id)
            self._logger.debug(
                "Raid eligibility check",
                attacker_id=str(attacker_id),
                defender_id=str(defender_id),
                can_raid=False,
                reason="shield_active",
            )
            return RaidEligibility(
                can_raid=False,
                reason="Defender is protected by a shield",
                cooldown_expires_at=shield.expires_at if shield else None,
            )

        # Card protection check (Eternal Guardian = always, Resilient Shield = chance)
        if self._build_modifier_engine is not None:
            engine = await self._build_modifier_engine(defender_id)
            if hasattr(engine, "check_raid_protection"):
                # For eligibility check, use seed=0 (deterministic preview).
                blocked, applied = engine.check_raid_protection(seed=0)
                if blocked:
                    desc = applied[0].description if applied else "Card protection"
                    self._logger.debug(
                        "Raid eligibility check",
                        attacker_id=str(attacker_id),
                        defender_id=str(defender_id),
                        can_raid=False,
                        reason="card_protection",
                    )
                    return RaidEligibility(
                        can_raid=False,
                        reason=f"Defender is protected by card: {desc}",
                    )

        # Cooldown check
        last_raid_record = await self._raid_log_repo.find_last_raid_between(
            attacker_id, defender_id
        )
        last_raid_ts = last_raid_record.timestamp if last_raid_record else None
        on_cooldown, cooldown_expires = is_raid_on_cooldown(
            last_raid_ts, self._raid_cooldown_hours
        )
        if on_cooldown:
            self._logger.debug(
                "Raid eligibility check",
                attacker_id=str(attacker_id),
                defender_id=str(defender_id),
                can_raid=False,
                reason="cooldown",
            )
            return RaidEligibility(
                can_raid=False,
                reason="Raid cooldown active for this target",
                cooldown_expires_at=cooldown_expires,
            )

        # Empty vault check
        if self._empty_vault_protection:
            defender_count = await self._vault_artifact_repo.count_by_owner(defender_id)
            if defender_count == 0:
                self._logger.debug(
                    "Raid eligibility check",
                    attacker_id=str(attacker_id),
                    defender_id=str(defender_id),
                    can_raid=False,
                    reason="empty_vault",
                )
                return RaidEligibility(
                    can_raid=False,
                    reason="Defender's vault is empty",
                )

        self._logger.debug(
            "Raid eligibility check",
            attacker_id=str(attacker_id),
            defender_id=str(defender_id),
            can_raid=True,
            reason="eligible",
        )
        return RaidEligibility(can_raid=True)

    async def get_raid_history(
        self,
        player_id: PlayerId,
        as_attacker: bool = True,
        as_defender: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResult[RaidLog]:
        """Get raid history for a player."""
        # Verify player exists
        await self._player_service.get_player(player_id)

        records, total = await self._raid_log_repo.find_by_player(
            player_id=player_id,
            as_attacker=as_attacker,
            as_defender=as_defender,
            limit=limit,
            offset=offset,
        )

        items = [
            RaidLog(
                raid_id=r.id,
                attacker_id=PlayerId(r.attacker_id),
                defender_id=PlayerId(r.defender_id),
                success=r.success,
                artifact_id=ArtifactId(r.artifact_id) if r.artifact_id else None,
                artifact_type_id=r.artifact_type_id,
                timestamp=r.timestamp,
            )
            for r in records
        ]

        return PaginatedResult(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_raid_cooldown(
        self,
        attacker_id: PlayerId,
        defender_id: PlayerId,
    ) -> datetime | None:
        """Get when the cooldown expires for raiding a specific player.

        Returns:
            Cooldown expiration datetime, or None if no cooldown.
        """
        last_raid_record = await self._raid_log_repo.find_last_raid_between(
            attacker_id, defender_id
        )
        if last_raid_record is None:
            return None

        _, cooldown_expires = is_raid_on_cooldown(
            last_raid_record.timestamp, self._raid_cooldown_hours
        )
        return cooldown_expires


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
