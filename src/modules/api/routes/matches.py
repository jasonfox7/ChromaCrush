"""Match route handlers.

Provides ``/api/v1/matches/*`` endpoints for match lifecycle:
active matches, match details, full match state (with bot hints),
board view, move submission, forfeit, match history, and move history.

All handlers delegate to ``match_service`` retrieved from ``request.app.state``.
Responses flow through the ``ResponseAdapter`` envelope. ``AppError``
exceptions propagate to the error handler middleware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.core.types.game import MatchId, Move, PlayerId, Position
from src.modules.api.dependencies import (
    get_auth_type,
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)
from src.modules.api.adapters.cascade_serializer import (
    serialize_applied_modifiers,
    serialize_cascade_steps,
)
from src.modules.api.schemas.match import (
    MatchHistoryQuery,
    MegaActivationRequest,
    MoveRequest,
)

if TYPE_CHECKING:
    from src.modules.api.adapters.bot_hints import BotHintGenerator, ValidMoveHint
    from src.modules.api.adapters.response import ResponseAdapter
    from src.modules.match.protocols import MatchServiceProtocol
    from src.modules.match.types import (
        MatchState,
        MatchSummary,
        MoveRecord,
        MoveSubmissionResult,
        PlayerBoardState,
    )

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _match_state_to_dict(
    state: MatchState,
    player_id: str,
) -> dict[str, Any]:
    """Convert a MatchState to a JSON-serializable dict relative to a player.

    Args:
        state: The full match state.
        player_id: The requesting player's ID (as str).

    Returns:
        Dict suitable for embedding in an API response.
    """
    p1 = state.player1
    p2 = state.player2

    # Determine which player is "me"
    if str(p1.player_id) == player_id:
        my_state, opp_state = p1, p2
    else:
        my_state, opp_state = p2, p1

    result = {
        "match_id": str(state.match_id),
        "status": state.status.value,
        "match_type": state.match_type.value,
        "player1": {
            "player_id": str(p1.player_id),
            "username": p1.player_username,
            "is_bot": p1.is_bot,
            "score": p1.score,
            "moves_made": p1.moves_made,
            "moves_remaining": p1.moves_remaining,
        },
        "player2": {
            "player_id": str(p2.player_id),
            "username": p2.player_username,
            "is_bot": p2.is_bot,
            "score": p2.score,
            "moves_made": p2.moves_made,
            "moves_remaining": p2.moves_remaining,
        },
        "is_my_turn": my_state.moves_remaining > 0,
        "my_score": my_state.score,
        "opponent_score": opp_state.score,
        "turns_remaining": my_state.moves_remaining,
        "opponent_is_bot": opp_state.is_bot,
        "winner_id": str(state.winner_id) if state.winner_id else None,
    }

    # Include raid data if match has completed with a card raid.
    if state.raid_data:
        result["raid_result"] = state.raid_data
    else:
        result["raid_result"] = None

    # Include reward data if match has completed with a card reward.
    if state.reward_data:
        result["reward_result"] = state.reward_data
    else:
        result["reward_result"] = None

    return result


def _match_summary_to_dict(summary: MatchSummary) -> dict[str, Any]:
    """Convert a MatchSummary to a JSON-serializable dict.

    Args:
        summary: Match summary from service.

    Returns:
        Dict suitable for embedding in an API response.
    """
    return {
        "match_id": str(summary.match_id),
        "status": summary.status.value,
        "match_type": summary.match_type.value,
        "opponent_id": str(summary.opponent_id),
        "opponent_username": summary.opponent_username,
        "player_score": summary.player_score,
        "opponent_score": summary.opponent_score,
        "won": summary.won,
        "created_at": summary.created_at.isoformat(),
        "completed_at": (
            summary.completed_at.isoformat() if summary.completed_at else None
        ),
    }


def _move_record_to_dict(record: MoveRecord) -> dict[str, Any]:
    """Convert a MoveRecord to a JSON-serializable dict.

    Args:
        record: Single historical move record.

    Returns:
        Dict suitable for embedding in an API response.
    """
    return {
        "move_number": record.move_number,
        "player_id": str(record.player_id),
        "from_row": record.move.from_pos.row,
        "from_col": record.move.from_pos.col,
        "to_row": record.move.to_pos.row,
        "to_col": record.move.to_pos.col,
        "score_gained": record.score_earned,
        "timestamp": record.timestamp.isoformat(),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/active")
async def get_active_matches(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get all active matches for the authenticated player.

    Returns matches with PENDING or IN_PROGRESS status.
    """
    player_id = get_current_player_id(request)
    svc: MatchServiceProtocol = request.app.state.match_service

    matches: list[MatchState] = await svc.get_active_matches(
        PlayerId(UUID(player_id)),
    )

    items = [_match_state_to_dict(m, player_id) for m in matches]
    return response.success(data={"matches": items}, correlation_id=correlation_id)


@router.get("/history")
async def get_match_history(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get paginated match history for the authenticated player."""
    player_id = get_current_player_id(request)
    svc: MatchServiceProtocol = request.app.state.match_service

    result = await svc.get_match_history(
        PlayerId(UUID(player_id)),
        limit=limit,
        offset=offset,
    )

    items = [_match_summary_to_dict(s) for s in result.items]
    return response.success(
        data={
            "matches": items,
            "total": result.total,
            "limit": result.limit,
            "offset": result.offset,
            "has_more": result.has_more,
        },
        correlation_id=correlation_id,
    )


@router.get("/{match_id}")
async def get_match(
    match_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get match details by ID."""
    player_id = get_current_player_id(request)
    svc: MatchServiceProtocol = request.app.state.match_service

    state: MatchState = await svc.get_match(MatchId(UUID(match_id)))
    data = _match_state_to_dict(state, player_id)
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/{match_id}/state")
async def get_match_state(
    match_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get full match state, including bot hints for API key auth.

    Bot hints are only included when the request is authenticated via
    API key and ``api.bot_hints_enabled`` is true.
    """
    player_id = get_current_player_id(request)
    svc: MatchServiceProtocol = request.app.state.match_service

    state: MatchState = await svc.get_match(MatchId(UUID(match_id)))
    data = _match_state_to_dict(state, player_id)

    # Determine requesting player's state and opponent state.
    if str(state.player1.player_id) == player_id:
        my_state = state.player1
        opp_state = state.player2
    else:
        my_state = state.player2
        opp_state = state.player1

    # Include bot hints for API key auth OR JWT-authenticated bot players.
    bot_hints = None
    auth_type = get_auth_type(request)
    is_bot_player = my_state.is_bot

    if auth_type == "api_key" or is_bot_player:
        config = request.app.state.config
        if config.get("api.bot_hints_enabled", True):
            hint_gen: BotHintGenerator = request.app.state.bot_hint_generator

            board_as_list: list[list[int]] = (
                my_state.current_board.grid.tolist()
                if my_state.current_board is not None
                else []
            )
            func_as_list: list[list[int]] = (
                my_state.current_board.func_grid.tolist()  # type: ignore[union-attr]
                if my_state.current_board is not None
                else []
            )

            # Find all valid moves on the bot's board.
            valid_move_hints = hint_gen.find_valid_moves(board_as_list)

            hints = hint_gen.generate_match_hints(
                board=board_as_list,
                valid_moves=valid_move_hints,
                my_score=my_state.score,
                opponent_score=opp_state.score,
                turns_remaining=my_state.moves_remaining,
            )

            bot_hints = {
                "best_moves": [
                    {
                        "move": {
                            "from_row": rm.move.from_row,
                            "from_col": rm.move.from_col,
                            "to_row": rm.move.to_row,
                            "to_col": rm.move.to_col,
                            "estimated_score": rm.move.estimated_score,
                        },
                        "expected_score": rm.expected_score,
                        "cascade_potential": rm.cascade_potential,
                        "special_gem_chance": rm.special_gem_chance,
                    }
                    for rm in hints.best_moves
                ],
                "board_analysis": {
                    "gem_distribution": hints.board_analysis.gem_distribution,
                    "special_gems_available": hints.board_analysis.special_gems_available,
                    "chain_opportunities": hints.board_analysis.chain_opportunities,
                    "board_volatility": hints.board_analysis.board_volatility,
                },
                "strategic_context": {
                    "score_differential": hints.strategic_context.score_differential,
                    "recommended_strategy": hints.strategic_context.recommended_strategy,
                    "risk_tolerance": hints.strategic_context.risk_tolerance,
                    "game_phase": hints.strategic_context.game_phase,
                },
            }

    data["bot_hints"] = bot_hints

    # Generate a per-match bot token if the opponent is a bot.
    if is_bot_player is False and data.get("opponent_is_bot"):
        # The requesting player is human, opponent is bot — generate token.
        opp_id = opp_state.player_id
        auth_service = getattr(request.app.state, "auth_service", None)
        if auth_service is not None:
            try:
                bot_token = await auth_service.create_bot_match_token(
                    bot_player_id=opp_id,
                    match_id=str(state.match_id),
                )
                data["bot_token"] = bot_token
                data["bot_player_id"] = str(opp_id)
            except Exception:
                data["bot_token"] = None
                data["bot_player_id"] = str(opp_id)
        else:
            data["bot_token"] = None
            data["bot_player_id"] = str(opp_id)

    return response.success(data=data, correlation_id=correlation_id)


@router.get("/{match_id}/board")
async def get_board(
    match_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the authenticated player's board view for a match."""
    player_id = get_current_player_id(request)
    svc: MatchServiceProtocol = request.app.state.match_service

    board_state: PlayerBoardState = await svc.get_player_board(
        MatchId(UUID(match_id)),
        PlayerId(UUID(player_id)),
    )

    data = {
        "cells": board_state.board.grid.tolist(),
        "functions": board_state.board.func_grid.tolist(),  # type: ignore[union-attr]
        "size": board_state.board.width,
        "moves_made": board_state.moves_made,
        "moves_remaining": board_state.moves_remaining,
        "score": board_state.score,
        "has_valid_moves": board_state.has_valid_moves,
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/{match_id}/move")
async def submit_move(
    match_id: str,
    body: MoveRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Submit a move (gem swap) in an active match."""
    player_id = get_current_player_id(request)
    svc: MatchServiceProtocol = request.app.state.match_service

    move = Move(
        from_pos=Position(row=body.from_row, col=body.from_col),
        to_pos=Position(row=body.to_row, col=body.to_col),
        timestamp_ms=body.timestamp_ms,
    )

    result: MoveSubmissionResult = await svc.submit_move(
        MatchId(UUID(match_id)),
        PlayerId(UUID(player_id)),
        move,
    )

    # Build new board data if available
    new_board = None
    if result.move_result.final_board is not None:
        new_board = {
            "cells": result.move_result.final_board.grid.tolist(),
            "functions": result.move_result.final_board.func_grid.tolist(),  # type: ignore[union-attr]
            "size": result.move_result.final_board.width,
            "moves_made": (
                result.match_state.get_player_state(
                    PlayerId(UUID(player_id)),
                ).moves_made
                if result.match_state.get_player_state(
                    PlayerId(UUID(player_id)),
                )
                else 0
            ),
            "moves_remaining": result.moves_remaining,
            "score": (
                result.match_state.get_player_state(
                    PlayerId(UUID(player_id)),
                ).score
                if result.match_state.get_player_state(
                    PlayerId(UUID(player_id)),
                )
                else 0
            ),
            "has_valid_moves": True,
        }

    # Build cascade animation buffer from intermediate cascade steps.
    cascade_steps = serialize_cascade_steps(result.move_result.cascades)

    # Serialize applied card modifiers from the move result.
    applied_modifiers = serialize_applied_modifiers(result.move_result)

    data = {
        "valid": result.move_result.was_valid_match,
        "score_gained": result.points_earned,
        "new_board": new_board,
        "matches_found": result.move_result.total_matches,
        "cascades": result.move_result.chain_count,
        "special_gems_created": len(result.move_result.special_gems_created),
        "match_completed": result.match_completed,
        "match_status": result.match_state.status.value,
        "moves_remaining": result.moves_remaining,
        "move_number": result.move_number,
        "cascade_steps": cascade_steps,
        "applied_modifiers": applied_modifiers,
        "raid_result": (
            {
                "occurred": result.raid_result.occurred,
                "stolen_card_id": result.raid_result.stolen_card_id,
                "stolen_card_name": result.raid_result.stolen_card_name,
                "was_shielded": result.raid_result.was_shielded,
                "card_unequipped": result.raid_result.card_unequipped,
                "blocked_by_card": result.raid_result.blocked_by_card,
                "blocked_by_card_name": result.raid_result.blocked_by_card_name,
            }
            if result.raid_result and result.raid_result.occurred
            else None
        ),
        "reward_result": (
            {
                "awarded": result.reward_result.awarded,
                "cards": result.reward_result.cards,
                "tier": result.reward_result.tier,
            }
            if result.reward_result and result.reward_result.awarded
            else None
        ),
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/{match_id}/mega")
async def activate_mega_gem(
    match_id: str,
    body: MegaActivationRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Activate a banked mega gem or shuffle in the player's inventory.

    Slot 0-3: Places a mega gem on the board, fires it, cascades, and scores.
    Slot 4: Shuffles the board without consuming a move.
    """
    player_id = get_current_player_id(request)
    svc: MatchServiceProtocol = request.app.state.match_service

    result: MoveSubmissionResult = await svc.activate_mega(
        MatchId(UUID(match_id)),
        PlayerId(UUID(player_id)),
        slot_index=body.slot_index,
        source=body.source,
    )

    # Build new board data if available.
    new_board = None
    if result.move_result.final_board is not None:
        new_board = {
            "cells": result.move_result.final_board.grid.tolist(),
            "functions": result.move_result.final_board.func_grid.tolist(),  # type: ignore[union-attr]
            "size": result.move_result.final_board.width,
            "moves_made": (
                result.match_state.get_player_state(
                    PlayerId(UUID(player_id)),
                ).moves_made
                if result.match_state.get_player_state(
                    PlayerId(UUID(player_id)),
                )
                else 0
            ),
            "moves_remaining": result.moves_remaining,
            "score": (
                result.match_state.get_player_state(
                    PlayerId(UUID(player_id)),
                ).score
                if result.match_state.get_player_state(
                    PlayerId(UUID(player_id)),
                )
                else 0
            ),
            "has_valid_moves": True,
        }

    # Build cascade animation buffer (same format as submit_move).
    cascade_steps = []
    for step in result.move_result.cascades:
        protected = {
            (att.center_pos.row, att.center_pos.col) for att in step.special_attractions
        }
        removals = []
        for match_group in step.matches.matches:
            for pos in match_group.positions:
                if (pos.row, pos.col) not in protected:
                    removals.append({"row": pos.row, "col": pos.col})

        drops = [
            {
                "gem_type": int(d.gem_type),
                "from_row": d.from_pos.row,
                "from_col": d.from_pos.col,
                "to_row": d.to_pos.row,
                "to_col": d.to_pos.col,
            }
            for d in step.gems_dropped
        ]

        spawns = [
            {
                "gem_type": int(s.gem_type),
                "row": s.position.row,
                "col": s.position.col,
            }
            for s in step.gems_spawned
        ]

        special = None
        if step.matches.creates_special_gem and step.matches.special_gem_position:
            sp = step.matches.special_gem_position
            special = {
                "row": sp.row,
                "col": sp.col,
                "gem_type": int(step.matches.special_gem_type),
                "color": (
                    int(step.matches.matches[0].gem_type) if step.matches.matches else 0
                ),
            }

        activations = [
            {
                "gem_type": int(act.gem_type),
                "row": act.position.row,
                "col": act.position.col,
                "affected": [
                    {"row": p.row, "col": p.col}
                    for p in sorted(
                        act.affected_positions, key=lambda p: (p.row, p.col)
                    )
                ],
                "is_mega": act.mega_func_value is not None,
                "mega_func": act.mega_func_value,
            }
            for act in step.special_activations
        ]

        attractions = [
            {
                "pos_a_row": att.pos_a.row,
                "pos_a_col": att.pos_a.col,
                "pos_b_row": att.pos_b.row,
                "pos_b_col": att.pos_b.col,
                "center_row": att.center_pos.row,
                "center_col": att.center_pos.col,
                "func_a": int(att.func_a),
                "func_b": int(att.func_b),
                "mega_func": att.mega_func,
            }
            for att in step.special_attractions
        ]

        injected = None
        if step.injected_special is not None:
            inj_pos, inj_func = step.injected_special
            injected = {"row": inj_pos.row, "col": inj_pos.col, "function": inj_func}

        injected_act = None
        if step.injected_activation is not None:
            act = step.injected_activation
            injected_act = {
                "gem_type": int(act.gem_type),
                "row": act.position.row,
                "col": act.position.col,
                "affected": [
                    {"row": p.row, "col": p.col}
                    for p in sorted(
                        act.affected_positions, key=lambda p: (p.row, p.col)
                    )
                ],
                "is_mega": act.mega_func_value is not None,
                "mega_func": act.mega_func_value,
            }

        injected_drops = [
            {
                "gem_type": int(d.gem_type),
                "from_row": d.from_pos.row,
                "from_col": d.from_pos.col,
                "to_row": d.to_pos.row,
                "to_col": d.to_pos.col,
            }
            for d in step.injected_drops
        ]

        injected_spawns = [
            {
                "gem_type": int(s.gem_type),
                "row": s.position.row,
                "col": s.position.col,
            }
            for s in step.injected_spawns
        ]

        cascade_steps.append(
            {
                "step_number": step.step_number,
                "removals": removals,
                "drops": drops,
                "spawns": spawns,
                "special_gem_created": special,
                "special_activations": activations,
                "special_attractions": attractions,
                "injected_special": injected,
                "injected_activation": injected_act,
                "injected_drops": injected_drops,
                "injected_spawns": injected_spawns,
            }
        )

    # Serialize applied card modifiers.
    applied_modifiers = [
        {
            "card_id": m.card_id,
            "card_name": m.card_name,
            "hook": m.hook,
            "description": m.description,
        }
        for m in (
            result.move_result.applied_modifiers
            if hasattr(result.move_result, "applied_modifiers")
            else []
        )
    ]

    data = {
        "valid": result.move_result.was_valid_match,
        "score_gained": result.points_earned,
        "new_board": new_board,
        "matches_found": result.move_result.total_matches,
        "cascades": result.move_result.chain_count,
        "special_gems_created": len(result.move_result.special_gems_created),
        "match_completed": result.match_completed,
        "match_status": result.match_state.status.value,
        "moves_remaining": result.moves_remaining,
        "move_number": result.move_number,
        "cascade_steps": cascade_steps,
        "applied_modifiers": applied_modifiers,
        "slot_index": body.slot_index,
        "is_shuffle": body.slot_index == 4,
        "raid_result": (
            {
                "occurred": result.raid_result.occurred,
                "stolen_card_id": result.raid_result.stolen_card_id,
                "stolen_card_name": result.raid_result.stolen_card_name,
                "was_shielded": result.raid_result.was_shielded,
                "card_unequipped": result.raid_result.card_unequipped,
                "blocked_by_card": result.raid_result.blocked_by_card,
                "blocked_by_card_name": result.raid_result.blocked_by_card_name,
            }
            if result.raid_result and result.raid_result.occurred
            else None
        ),
        "reward_result": (
            {
                "awarded": result.reward_result.awarded,
                "cards": result.reward_result.cards,
                "tier": result.reward_result.tier,
            }
            if result.reward_result and result.reward_result.awarded
            else None
        ),
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.post("/{match_id}/forfeit")
async def forfeit_match(
    match_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Forfeit an active match, awarding the win to the opponent."""
    player_id = get_current_player_id(request)
    svc: MatchServiceProtocol = request.app.state.match_service

    state: MatchState = await svc.forfeit_match(
        MatchId(UUID(match_id)),
        PlayerId(UUID(player_id)),
    )

    data = _match_state_to_dict(state, player_id)
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/{match_id}/debug-board")
async def debug_board(
    match_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Debug endpoint: return board state with ASCII view and valid moves."""
    player_id = get_current_player_id(request)
    svc: MatchServiceProtocol = request.app.state.match_service

    board_state: PlayerBoardState = await svc.get_player_board(
        MatchId(UUID(match_id)),
        PlayerId(UUID(player_id)),
    )
    board = board_state.board

    # ASCII representation
    gem_chars = {0: ".", 1: "R", 2: "B", 3: "G", 4: "Y", 5: "P", 6: "O"}
    ascii_rows = []
    for r in range(board.height):
        row_str = " ".join(
            gem_chars.get(int(board.grid[r, c]), "?") for c in range(board.width)
        )
        ascii_rows.append(f"{r}: {row_str}")

    # Find all valid moves using board_service
    board_svc = request.app.state.board_service
    valid_moves = []
    for r in range(board.height):
        for c in range(board.width):
            for dr, dc in [(0, 1), (1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < board.height and 0 <= nc < board.width:
                    test = board_svc._swap_positions(
                        board, Position(r, c), Position(nr, nc)
                    )
                    match_result = board_svc.detect_matches(test)
                    if match_result.matches:
                        valid_moves.append(
                            {
                                "from": [r, c],
                                "to": [nr, nc],
                                "gem_from": int(board.grid[r, c]),
                                "gem_to": int(board.grid[nr, nc]),
                                "matches": len(match_result.matches),
                                "gems_matched": match_result.total_gems_matched,
                            }
                        )

    data = {
        "cells": board.grid.tolist(),
        "functions": board.func_grid.tolist(),  # type: ignore[union-attr]
        "ascii": ascii_rows,
        "valid_moves": valid_moves,
        "valid_moves_count": len(valid_moves),
        "has_valid_moves": len(valid_moves) > 0,
        "score": board_state.score,
        "moves_remaining": board_state.moves_remaining,
    }
    return response.success(data=data, correlation_id=correlation_id)


@router.get("/{match_id}/moves")
async def get_move_history(
    match_id: str,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Get the move history for a match."""
    player_id = get_current_player_id(request)
    svc: MatchServiceProtocol = request.app.state.match_service

    moves: list[MoveRecord] = await svc.get_move_history(
        MatchId(UUID(match_id)),
    )

    items = [_move_record_to_dict(m) for m in moves]
    return response.success(data={"moves": items}, correlation_id=correlation_id)
