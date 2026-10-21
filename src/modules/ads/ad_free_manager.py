"""Ad-free status manager.

Handles checking, granting, and revoking ad-free status for players.
Internal module — not exported from ``__init__.py``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from src.core.types.game import PlayerId
from src.modules.ads._helpers import build_ad_free_status
from src.modules.ads.dto import AdFreeStatusUpsert
from src.modules.ads.types import AdFreeReason, AdFreeStatus

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.protocols import (
        AdFreeStatusRepositoryProtocol,
        PlayerServiceProtocol,
    )


class AdFreeManager:
    """Manages ad-free status lifecycle."""

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        free_repo: AdFreeStatusRepositoryProtocol,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._players = player_service
        self._free_repo = free_repo

    async def check_ad_free_status(self, player_id: PlayerId) -> AdFreeStatus:
        await self._players.get_player(player_id)
        rec = await self._free_repo.find_by_player(player_id)
        st = build_ad_free_status(rec, player_id)
        self._logger.debug(
            "Ad-free status checked", player_id=str(player_id), is_ad_free=st.is_ad_free
        )
        return st

    async def grant_ad_free_status(
        self,
        player_id: PlayerId,
        reason: AdFreeReason,
        duration_days: int | None = None,
        granted_by: PlayerId | None = None,
    ) -> AdFreeStatus:
        await self._players.get_player(player_id)
        if duration_days is not None and duration_days <= 0:
            raise self._errors.validation(
                "Duration must be positive",
                code="VALIDATION_INVALID_INPUT",
                field="duration_days",
                value=duration_days,
            )
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=duration_days) if duration_days else None
        rec = await self._free_repo.upsert(
            AdFreeStatusUpsert(
                player_id=player_id,
                is_ad_free=True,
                reason=reason.value,
                granted_at=now,
                expires_at=exp,
                granted_by=granted_by,
            )
        )
        self._logger.info(
            "Ad-free status granted",
            player_id=str(player_id),
            reason=reason.value,
            duration_days=duration_days,
        )
        return build_ad_free_status(rec, player_id)

    async def revoke_ad_free_status(self, player_id: PlayerId, reason: str) -> None:
        await self._players.get_player(player_id)
        if len(reason) > 500:
            raise self._errors.validation(
                "Reason too long", code="VALIDATION_INVALID_INPUT", field="reason"
            )
        rec = await self._free_repo.find_by_player(player_id)
        st = build_ad_free_status(rec, player_id)
        if not st.is_ad_free:
            raise self._errors.not_found(
                "Player does not have ad-free status",
                code="NOT_FOUND_PLAYER",
                player_id=str(player_id),
            )
        await self._free_repo.revoke(player_id, reason)
        self._logger.warn(
            "Ad-free status revoked", player_id=str(player_id), reason=reason
        )
