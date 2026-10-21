"""Vault route handlers.

Provides ``/api/v1/vault/*`` endpoints for vault management:
listing artifacts, artifact details, shield activation/status,
raid attempts, collection progress, and raid targets (bot-only).

All handlers delegate to ``vault_service`` (and optionally
``player_service``) retrieved from ``request.app.state``.
Responses flow through the ``ResponseAdapter`` envelope.
``AppError`` exceptions propagate to the error handler middleware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.core.types.game import ArtifactId, PlayerId
from src.modules.api.dependencies import (
    get_auth_type,
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)
from src.modules.api.schemas.vault import RaidRequest, ShieldRequest

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter
    from src.modules.vault.dto import (
        CollectionProgress,
        RaidResult,
        Shield,
        VaultArtifact,
        VaultSummary,
    )
    from src.modules.vault.protocols import VaultServiceProtocol

router = APIRouter(prefix="/api/v1/vault", tags=["vault"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _artifact_to_dict(artifact: VaultArtifact) -> dict[str, Any]:
    """Convert a VaultArtifact to a JSON-serializable dict.

    Args:
        artifact: The vault artifact domain object.

    Returns:
        Dict matching the ArtifactResponse schema.
    """
    return {
        "artifact_id": str(artifact.id),
        "artifact_type_id": artifact.artifact_type_id,
        "rarity": artifact.definition.rarity.value,
        "artifact_set": artifact.definition.artifact_set,
        "name": artifact.definition.name,
        "description": artifact.definition.description,
        "acquired_at": artifact.acquired_at.isoformat(),
        "source": artifact.source,
    }


def _shield_to_dict(shield: Shield | None) -> dict[str, Any]:
    """Convert a Shield (or None) to a JSON-serializable dict.

    Args:
        shield: Active shield or None if unprotected.

    Returns:
        Dict matching the ShieldResponse schema.
    """
    if shield is None:
        return {
            "is_active": False,
            "expires_at": None,
            "remaining_hours": None,
        }
    remaining_seconds = shield.remaining_seconds
    remaining_hours = (
        round(remaining_seconds / 3600, 2) if remaining_seconds > 0 else 0.0
    )
    return {
        "is_active": shield.is_active,
        "expires_at": shield.expires_at.isoformat(),
        "remaining_hours": remaining_hours,
    }


def _collection_to_dict(progress: CollectionProgress) -> dict[str, Any]:
    """Convert a CollectionProgress to a JSON-serializable dict.

    Args:
        progress: Set collection progress domain object.

    Returns:
        Dict matching the CollectionProgressResponse schema.
    """
    return {
        "set_name": progress.set_name,
        "total_in_set": progress.total_in_set,
        "collected": progress.owned_count,
        "completion_percentage": round(progress.completion_percent, 2),
        "missing_artifacts": progress.missing_type_ids,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/artifacts")
async def get_artifacts(
    request: Request,
    rarity: str | None = Query(default=None),
    artifact_set: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the authenticated player's vault artifacts with optional filters."""
    player_id = get_current_player_id(request)
    svc: VaultServiceProtocol = request.app.state.vault_service

    # Convert string rarity to enum if provided
    rarity_enum = None
    if rarity is not None:
        from src.modules.vault.dto import ArtifactRarity

        rarity_enum = ArtifactRarity(rarity)

    result = await svc.get_player_artifacts(
        PlayerId(UUID(player_id)),
        rarity=rarity_enum,
        artifact_set=artifact_set,
        limit=limit,
        offset=offset,
    )

    items = [_artifact_to_dict(a) for a in result.items]
    return response.success(
        data={
            "artifacts": items,
            "total": result.total,
            "limit": result.limit,
            "offset": result.offset,
            "has_more": result.has_more,
        },
        correlation_id=correlation_id,
    )


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get a specific artifact by ID."""
    svc: VaultServiceProtocol = request.app.state.vault_service

    artifact: VaultArtifact = await svc.get_artifact(ArtifactId(UUID(artifact_id)))
    data = _artifact_to_dict(artifact)
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/shield")
async def activate_shield(
    request: Request,
    body: ShieldRequest | None = None,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Activate raid protection shield for the authenticated player."""
    player_id = get_current_player_id(request)
    svc: VaultServiceProtocol = request.app.state.vault_service

    duration_hours = body.duration_hours if body is not None else None

    shield: Shield = await svc.activate_shield(
        PlayerId(UUID(player_id)),
        duration_hours=duration_hours,
    )

    data = _shield_to_dict(shield)
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/shield")
async def get_shield_status(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the authenticated player's current shield status."""
    player_id = get_current_player_id(request)
    svc: VaultServiceProtocol = request.app.state.vault_service

    shield: Shield | None = await svc.get_shield_status(
        PlayerId(UUID(player_id)),
    )

    data = _shield_to_dict(shield)
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/raid")
async def attempt_raid(
    body: RaidRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Attempt to raid another player's vault."""
    player_id = get_current_player_id(request)
    svc: VaultServiceProtocol = request.app.state.vault_service

    result: RaidResult = await svc.attempt_raid(
        attacker_id=PlayerId(UUID(player_id)),
        defender_id=PlayerId(UUID(body.defender_id)),
    )

    stolen_list = []
    if result.stolen_artifact is not None:
        stolen_list.append(_artifact_to_dict(result.stolen_artifact))

    data = {
        "success": result.success,
        "artifacts_stolen": stolen_list,
        "defender_id": str(result.defender_id),
        "message": result.message,
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/collection")
async def get_collection_progress(
    request: Request,
    artifact_set: str | None = Query(default=None),
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the authenticated player's artifact collection progress."""
    player_id = get_current_player_id(request)
    svc: VaultServiceProtocol = request.app.state.vault_service

    progress_list: list[CollectionProgress] = await svc.get_collection_progress(
        PlayerId(UUID(player_id)),
        artifact_set=artifact_set,
    )

    items = [_collection_to_dict(p) for p in progress_list]
    return response.success(data={"collections": items}, correlation_id=correlation_id)


@router.get("/targets")
async def get_raid_targets(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get raidable targets for the authenticated bot player.

    This is a bot-specific endpoint. It lists potential raid targets
    with vault summary information and protection status.
    Requires API key authentication.
    """
    player_id = get_current_player_id(request)
    vault_svc: VaultServiceProtocol = request.app.state.vault_service
    player_svc = request.app.state.player_service

    # Fetch a list of players
    from src.core.types.player import PlayerType

    players_result = await player_svc.list_players(
        player_type=PlayerType.HUMAN,
        limit=50,
        offset=0,
    )

    targets: list[dict[str, Any]] = []
    for player in players_result.items:
        pid = player.id
        # Skip self
        if str(pid) == player_id:
            continue

        # Check protection status
        is_protected = await vault_svc.is_protected(pid)

        # Get vault summary for size info
        summary: VaultSummary = await vault_svc.get_vault_summary(pid)

        targets.append(
            {
                "player_id": str(pid),
                "username": player.username,
                "vault_size": summary.total_artifacts,
                "is_protected": is_protected,
            }
        )

    return response.success(data={"targets": targets}, correlation_id=correlation_id)
