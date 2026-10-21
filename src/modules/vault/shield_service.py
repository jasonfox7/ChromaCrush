"""Shield sub-service for the vault module.

Handles shield activation, deactivation, status queries, and protection
checks. All dependencies arrive via ``__init__`` injection.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from src.core.types.game import PlayerId
from src.modules.vault.dto import Shield

if TYPE_CHECKING:
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.vault_shield_repository import (
        VaultShieldRepositoryProtocol,
    )
    from src.modules.player.protocols import PlayerServiceProtocol


class ShieldService:
    """Internal sub-service for shield operations.

    Not exported from the vault module -- used only by ``VaultService``.
    """

    def __init__(
        self,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        vault_shield_repo: VaultShieldRepositoryProtocol,
        shield_duration_hours: int,
    ) -> None:
        self._logger = logger
        self._errors = errors
        self._player_service = player_service
        self._vault_shield_repo = vault_shield_repo
        self._shield_duration_hours = shield_duration_hours

    # ========== Shield System ==========

    async def activate_shield(
        self,
        player_id: PlayerId,
        duration_hours: int | None = None,
    ) -> Shield:
        """Activate raid protection shield for a player.

        Raises:
            NOT_FOUND_PLAYER: If player doesn't exist.
            CONFLICT_SHIELD_ALREADY_ACTIVE: If player already has active shield.
            VALIDATION_INVALID_INPUT: If duration_hours <= 0.
        """
        # Verify player exists
        await self._player_service.get_player(player_id)

        hours = (
            duration_hours
            if duration_hours is not None
            else self._shield_duration_hours
        )

        if hours <= 0:
            raise self._errors.validation(
                "Shield duration must be positive",
                code="VALIDATION_INVALID_INPUT",
                field="duration_hours",
                value=hours,
            )

        # Check for existing active shield
        existing = await self._vault_shield_repo.find_by_player(player_id)
        if existing is not None:
            existing_shield = _record_to_shield(existing)
            if existing_shield.is_active:
                raise self._errors.conflict(
                    "Player already has an active shield",
                    code="CONFLICT_SHIELD_ALREADY_ACTIVE",
                    player_id=str(player_id),
                    expires_at=existing.expires_at.isoformat(),
                )
            else:
                # Expired shield record; clean it up
                await self._vault_shield_repo.delete(player_id)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=hours)

        record = await self._vault_shield_repo.create(
            player_id=player_id,
            activated_at=now,
            expires_at=expires_at,
            duration_hours=hours,
        )

        shield = _record_to_shield(record)

        self._logger.info(
            "Shield activated",
            player_id=str(player_id),
            expires_at=expires_at.isoformat(),
            duration_hours=hours,
        )

        return shield

    async def get_shield_status(
        self,
        player_id: PlayerId,
    ) -> Shield | None:
        """Get a player's current shield status.

        Returns active Shield if protected, None if unprotected.
        Cleans up expired shields automatically.
        """
        record = await self._vault_shield_repo.find_by_player(player_id)
        if record is None:
            return None

        shield = _record_to_shield(record)
        if not shield.is_active:
            # Expired -- clean up
            await self._vault_shield_repo.delete(player_id)
            self._logger.info(
                "Shield deactivated",
                player_id=str(player_id),
                reason="expired",
            )
            return None

        return shield

    async def deactivate_shield(
        self,
        player_id: PlayerId,
    ) -> None:
        """Manually deactivate a player's shield.

        Raises:
            VALIDATION_INVALID_INPUT: If no active shield exists.
        """
        record = await self._vault_shield_repo.find_by_player(player_id)
        if record is None:
            raise self._errors.validation(
                "No active shield to deactivate",
                code="VALIDATION_INVALID_INPUT",
                field="shield",
                player_id=str(player_id),
            )

        shield = _record_to_shield(record)
        if not shield.is_active:
            # Expired -- clean up and report as no active shield
            await self._vault_shield_repo.delete(player_id)
            raise self._errors.validation(
                "No active shield to deactivate",
                code="VALIDATION_INVALID_INPUT",
                field="shield",
                player_id=str(player_id),
            )

        await self._vault_shield_repo.delete(player_id)

        self._logger.info(
            "Shield deactivated",
            player_id=str(player_id),
            reason="manual",
        )

    async def is_protected(
        self,
        player_id: PlayerId,
    ) -> bool:
        """Check if a player is currently protected by a shield."""
        shield = await self.get_shield_status(player_id)
        return shield is not None


# ========== Module-level Helper ==========


def _record_to_shield(record: object) -> Shield:
    """Convert a shield record to a Shield DTO."""
    return Shield(
        player_id=PlayerId(record.player_id),
        activated_at=record.activated_at,
        expires_at=record.expires_at,
        duration_hours=record.duration_hours,
    )
