"""Card route handlers.

Provides ``/api/v1/cards/*`` endpoints for card management:
listing definitions, player card collection, equip/unequip, reorder, and merge.

All handlers delegate to ``card_service`` retrieved from ``request.app.state``.
Responses flow through the ``ResponseAdapter`` envelope.
``AppError`` exceptions propagate to the error handler middleware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.core.types.game import PlayerId
from src.modules.api.dependencies import (
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)
from src.modules.api.schemas.cards import (
    CardEquipRequest,
    CardReorderRequest,
    CardUnequipRequest,
)

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter
    from src.modules.cards.dto import CardDefinition, EquippedLoadout, PlayerCard
    from src.modules.cards.service import CardService
    from src.modules.match.types import MatchState

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _reject_if_active_match(request: Request, player_id: str) -> None:
    """Raise CONFLICT_ACTIVE_MATCH if the player has a match in progress."""
    match_service = request.app.state.match_service
    active: list[MatchState] = await match_service.get_active_matches(
        PlayerId(UUID(player_id))
    )
    if active:
        errors = request.app.state.errors
        raise errors.conflict(
            "Cannot modify card loadout while a match is active",
            code="CONFLICT_ACTIVE_MATCH",
        )


def _definition_to_dict(defn: CardDefinition) -> dict[str, Any]:
    """Convert a CardDefinition to a JSON-serializable dict."""
    return {
        "card_id": defn.card_id,
        "name": defn.name,
        "description": defn.description,
        "rarity": defn.rarity,
        "card_set": defn.card_set,
        "set_position": defn.set_position,
        "base_value": defn.base_value,
        "tags": defn.tags,
        "trigger": defn.trigger,
        "effect": defn.effect,
        "effect_params": defn.effect_params,
        "trigger_condition": defn.trigger_condition,
    }


def _player_card_to_dict(card: PlayerCard) -> dict[str, Any]:
    """Convert a PlayerCard to a JSON-serializable dict."""
    return {
        "id": str(card.id),
        "card_id": card.card_id,
        "definition": _definition_to_dict(card.definition),
        "position": card.position,
        "level": card.level,
        "acquired_at": card.acquired_at.isoformat(),
        "source": card.source,
        "source_id": card.source_id,
    }


def _loadout_to_dict(loadout: EquippedLoadout) -> dict[str, Any]:
    """Convert an EquippedLoadout to a JSON-serializable dict."""
    return {
        "player_id": str(loadout.player_id),
        "cards": [_player_card_to_dict(c) for c in loadout.cards],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/definitions")
async def list_definitions(
    request: Request,
    rarity: str | None = Query(default=None),
    card_set: str | None = Query(default=None),
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """List all card definitions with optional filters."""
    svc: CardService = request.app.state.card_service

    definitions = await svc.list_card_definitions(rarity=rarity, card_set=card_set)

    items = [_definition_to_dict(d) for d in definitions]
    return response.success(data=items, correlation_id=correlation_id)


@router.get("/definitions/{card_id}")
async def get_definition(
    card_id: int,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get a specific card definition by ID."""
    svc: CardService = request.app.state.card_service

    defn: CardDefinition = await svc.get_card_definition(card_id)
    data = _definition_to_dict(defn)
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/mine")
async def get_my_cards(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the authenticated player's card collection."""
    player_id = get_current_player_id(request)
    svc: CardService = request.app.state.card_service

    result = await svc.get_player_cards(
        PlayerId(UUID(player_id)),
        limit=limit,
        offset=offset,
    )

    items = [_player_card_to_dict(c) for c in result.items]
    return response.success(
        data={
            "cards": items,
            "total": result.total,
            "limit": result.limit,
            "offset": result.offset,
            "has_more": result.has_more,
        },
        correlation_id=correlation_id,
    )


@router.get("/equipped")
async def get_equipped(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the authenticated player's equipped card loadout."""
    player_id = get_current_player_id(request)
    svc: CardService = request.app.state.card_service

    loadout: EquippedLoadout = await svc.get_equipped_cards(
        PlayerId(UUID(player_id)),
    )

    data = _loadout_to_dict(loadout)
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/equip")
async def equip_card(
    body: CardEquipRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Equip a card into a specific slot (1-3)."""
    player_id = get_current_player_id(request)
    await _reject_if_active_match(request, player_id)
    svc: CardService = request.app.state.card_service

    loadout: EquippedLoadout = await svc.equip_card(
        player_id=PlayerId(UUID(player_id)),
        card_instance_id=UUID(body.card_instance_id),
        slot=body.slot,
    )

    data = _loadout_to_dict(loadout)
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/unequip")
async def unequip_card(
    body: CardUnequipRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Unequip a card from its slot back to the vault."""
    player_id = get_current_player_id(request)
    await _reject_if_active_match(request, player_id)
    svc: CardService = request.app.state.card_service

    loadout: EquippedLoadout = await svc.unequip_card(
        player_id=PlayerId(UUID(player_id)),
        card_instance_id=UUID(body.card_instance_id),
    )

    data = _loadout_to_dict(loadout)
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/reorder")
async def reorder_card(
    body: CardReorderRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Move a card to a new position."""
    player_id = get_current_player_id(request)
    await _reject_if_active_match(request, player_id)
    svc: CardService = request.app.state.card_service

    card: PlayerCard = await svc.reorder_card(
        player_id=PlayerId(UUID(player_id)),
        card_instance_id=UUID(body.card_instance_id),
        new_position=body.new_position,
    )

    data = _player_card_to_dict(card)
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/merge")
async def merge_cards(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Merge all 3 equipped cards into a random higher-tier card.

    All 3 equip slots must be filled, and all cards must share the
    same rarity. Legendary cards cannot be merged.
    """
    player_id = get_current_player_id(request)
    await _reject_if_active_match(request, player_id)
    svc: CardService = request.app.state.card_service

    result = await svc.merge_equipped(PlayerId(UUID(player_id)))

    data = {
        "new_card": _player_card_to_dict(result.new_card),
        "consumed_card_ids": [str(cid) for cid in result.consumed_card_ids],
        "source_rarity": result.source_rarity,
        "target_rarity": result.target_rarity,
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/equipped/{player_id}")
async def get_player_equipped(
    player_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get any player's equipped card loadout (for opponent preview)."""
    svc: CardService = request.app.state.card_service

    loadout: EquippedLoadout = await svc.get_equipped_cards(
        PlayerId(UUID(player_id)),
    )

    data = _loadout_to_dict(loadout)
    return response.success(data=data, correlation_id=correlation_id)
