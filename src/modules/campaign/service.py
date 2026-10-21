"""Campaign service — single-player obstacle-clearing progression.

Manages campaign attempts: starting levels, processing moves against
obstacles, tracking win/lose conditions, and handling checkpoint
rewards and regression.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID

import numpy as np

from src.core.entity_lock import EntityBusyError, EntityLockManager
from src.core.move_pipeline import (
    derive_move_seed,
    process_mega_pipeline,
    process_move_pipeline,
)
from src.modules.board._constants import OBSTACLE_COLOR, WALL_FUNC_THRESHOLD
from src.modules.board.types import BoardState, Move, Position
from src.modules.campaign.level_loader import LevelLoader

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.campaign_attempt_repository import (
        CampaignAttemptRecord,
        CampaignAttemptRepositoryProtocol,
    )
    from src.data.repositories.player_repository import SQLAlchemyPlayerRepository
    from src.modules.board.service import BoardService
    from src.modules.board_gen.protocols import BoardGenServiceProtocol
    from src.modules.cards.service import CardService
    from src.modules.economy.service import EconomyService
    from src.modules.energy.protocols import EnergyServiceProtocol
    from src.modules.scoring.service import ScoringService

# LCG multiplier for deterministic seed derivation (matches MoveProcessor).
_LCG_MULTIPLIER = 1103515245


def _count_clearable_obstacles(board: BoardState) -> int:
    """Count obstacles excluding invincible walls (func >= WALL_FUNC_THRESHOLD)."""
    obstacle_mask = board.grid == OBSTACLE_COLOR
    wall_mask = board.func_grid >= WALL_FUNC_THRESHOLD
    return int(np.count_nonzero(obstacle_mask & ~wall_mask))


def _apply_obstacle_spread(
    board: BoardState,
    level_def: dict,
    move_seed: int,
) -> list[dict]:
    """Spread obstacles to adjacent regular gem cells.

    Returns list of spread events: [{"type": "spread", "row": r, "col": c, "func": f}].
    No-op if level_def has no 'obstacle_spread' config.
    """
    config = level_def.get("obstacle_spread")
    if not config:
        return []

    chance = config.get("chance", 0.3)
    spread_func = config.get("func", 0)
    max_per_turn = config.get("max_per_turn", 2)

    rows, cols = board.grid.shape
    # Collect current obstacle positions.
    obs_positions = set()
    for r in range(rows):
        for c in range(cols):
            if board.grid[r, c] == OBSTACLE_COLOR:
                obs_positions.add((r, c))

    # Collect candidate neighbors: orthogonal cells with regular gems (1-6, func=0).
    candidates = []
    for r, c in obs_positions:
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                cell = int(board.grid[nr, nc])
                func = int(board.func_grid[nr, nc])
                if 1 <= cell <= 6 and func == 0 and (nr, nc) not in obs_positions:
                    candidates.append((nr, nc))

    # Deduplicate.
    candidates = list(set(candidates))
    if not candidates:
        return []

    # Deterministic shuffle.
    rng = np.random.default_rng(move_seed ^ 0xDEAD_BEEF)
    rng.shuffle(candidates)

    # Convert candidates to obstacles.
    events: list[dict] = []
    for r, c in candidates:
        if len(events) >= max_per_turn:
            break
        if rng.random() < chance:
            board.grid[r, c] = OBSTACLE_COLOR
            board.func_grid[r, c] = spread_func
            events.append({"type": "spread", "row": int(r), "col": int(c), "func": spread_func})

    return events


def _apply_obstacle_regen(
    board: BoardState,
    level_def: dict,
    regen_counters: dict[str, dict],
    tick: bool = True,
) -> tuple[dict[str, dict], list[dict]]:
    """Regenerate cleared obstacles after N moves.

    Args:
        board: Current board state (mutated in-place on regen).
        level_def: Level definition with obstacle positions and regen config.
        regen_counters: Mutable dict tracking cleared obstacle timers.
        tick: Whether to increment counters (True for moves, False for megas).

    Returns:
        (updated_counters, regen_events) where regen_events is a list of
        {"type": "regen", "row": r, "col": c, "func": f} dicts.
    """
    config = level_def.get("obstacle_regen")
    if not config:
        return regen_counters, []

    after_moves = config.get("after_moves", 3)

    # Build map of original obstacle positions from level def.
    # Exclude walls (func >= WALL_FUNC_THRESHOLD) — they never need regen.
    original_obstacles: dict[str, int] = {}
    for obs in level_def.get("obstacles", []):
        f = obs.get("func", 0)
        if f < WALL_FUNC_THRESHOLD:
            key = f"{obs['row']},{obs['col']}"
            original_obstacles[key] = f

    events: list[dict] = []
    keys_to_remove: list[str] = []

    for key, func in original_obstacles.items():
        r, c = [int(x) for x in key.split(",")]

        is_still_obstacle = int(board.grid[r, c]) == OBSTACLE_COLOR
        if is_still_obstacle:
            # Obstacle intact — remove from regen tracking.
            if key in regen_counters:
                keys_to_remove.append(key)
            continue

        # Obstacle was cleared — track or increment counter.
        if key not in regen_counters:
            regen_counters[key] = {"original_func": func, "moves_since_cleared": 0}

        if tick:
            regen_counters[key]["moves_since_cleared"] += 1

        # Check if ready to respawn.
        if regen_counters[key]["moves_since_cleared"] >= after_moves:
            # Only respawn if cell is a regular gem (not empty, not another obstacle).
            cell_val = int(board.grid[r, c])
            if 1 <= cell_val <= 6:
                board.grid[r, c] = OBSTACLE_COLOR
                board.func_grid[r, c] = 0  # Always regen as basic glass
                events.append({"type": "regen", "row": r, "col": c, "func": 0})
            keys_to_remove.append(key)

    for key in keys_to_remove:
        regen_counters.pop(key, None)

    return regen_counters, events


class CampaignService:
    """Manages single-player campaign level attempts.

    Args:
        config: Application configuration.
        logger: Structured logging service.
        errors: Error factory service.
        board_service: Board processing service.
        energy_service: Energy/hearts service for checkpoint costs.
        card_service: Card service for modifier construction.
        player_repo: Player repository for campaign_level reads/writes.
        campaign_repo: Campaign attempt repository.
    """

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        board_service: BoardService,
        energy_service: EnergyServiceProtocol,
        player_repo: SQLAlchemyPlayerRepository,
        campaign_repo: CampaignAttemptRepositoryProtocol,
        *,
        card_service: CardService | None = None,
        scoring_service: ScoringService | None = None,
        economy_service: EconomyService | None = None,
        board_gen_service: BoardGenServiceProtocol | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._board_service = board_service
        self._energy_service = energy_service
        self._player_repo = player_repo
        self._campaign_repo = campaign_repo
        self._card_service = card_service
        self._scoring_service = scoring_service
        self._economy_service = economy_service
        self._board_gen_service = board_gen_service
        self._level_loader = LevelLoader()
        self._entity_locks = EntityLockManager()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_level_definition(self, level_number: int) -> dict:
        """Get a level definition by number.

        Raises:
            AppError (NOT_FOUND): If level doesn't exist.
        """
        level_def = self._level_loader.get(level_number)
        if level_def is None:
            raise self._errors.not_found(
                f"Campaign level {level_number} not found",
                code="NOT_FOUND_CAMPAIGN_LEVEL",
                level_number=level_number,
            )
        return level_def

    @property
    def max_level(self) -> int:
        """Highest available campaign level."""
        return self._level_loader.max_level

    async def start_attempt(
        self,
        player_id: UUID,
        level_number: int,
    ) -> tuple[CampaignAttemptRecord, BoardState]:
        """Start a new campaign level attempt.

        Validates level unlock, checks heart cost for checkpoints,
        generates the board with obstacles, and persists the attempt.

        Args:
            player_id: The player starting the attempt.
            level_number: Campaign level to attempt.

        Returns:
            Tuple of (attempt record, initial board state).

        Raises:
            AppError (FORBIDDEN): If level is locked or insufficient hearts.
            AppError (NOT_FOUND): If level doesn't exist.
            AppError (CONFLICT): If player already has an active attempt.
        """
        level_def = self.get_level_definition(level_number)

        # Validate player has unlocked this level.
        player = await self._player_repo.find_by_id(player_id)
        if player is None:
            raise self._errors.not_found(
                f"Player not found: {player_id}",
                code="NOT_FOUND_PLAYER",
                player_id=str(player_id),
            )

        campaign_level = getattr(player, "campaign_level", 1)
        if level_number > campaign_level:
            raise self._errors.forbidden(
                f"Level {level_number} is locked (current: {campaign_level})",
                code="FORBIDDEN_LEVEL_LOCKED",
                level_number=level_number,
                campaign_level=campaign_level,
            )

        # Abandon any existing active attempt.
        active = await self._campaign_repo.find_active_by_player(player_id)
        if active is not None:
            await self._campaign_repo.update(active.id, status="abandoned")

        # Deduct heart for checkpoint levels.
        if level_def.get("is_checkpoint"):
            heart_cost = level_def.get("heart_cost", 1)
            can_play = await self._energy_service.can_play(
                player_id, hearts_required=heart_cost
            )
            if not can_play:
                raise self._errors.forbidden(
                    f"Insufficient hearts for checkpoint level {level_number}",
                    code="FORBIDDEN_INSUFFICIENT_ENERGY",
                    level_number=level_number,
                    heart_cost=heart_cost,
                )
            await self._energy_service.consume_heart(player_id, amount=heart_cost)

        # Generate board with obstacles.
        seed = _derive_board_seed(player_id, level_number)
        board = self._board_service.create_board_with_obstacles(
            width=8,
            height=8,
            seed=seed,
            obstacles=level_def["obstacles"],
            gem_colors=level_def.get("gem_colors", 6),
        )

        obstacles_remaining = _count_clearable_obstacles(board)
        board_state_dict = {
            "cells": board.grid.tolist(),
            "functions": board.func_grid.tolist(),
        }

        # Persist attempt.
        attempt = await self._campaign_repo.create(
            player_id=player_id,
            level_number=level_number,
            board_seed=seed,
            board_state=board_state_dict,
            moves_remaining=level_def["moves"],
            obstacles_remaining=obstacles_remaining,
        )

        self._logger.info(
            "Campaign attempt started",
            player_id=str(player_id),
            level_number=level_number,
            attempt_id=str(attempt.id),
            obstacles=obstacles_remaining,
        )

        return attempt, board

    async def submit_move(
        self,
        attempt_id: UUID,
        player_id: UUID,
        move: Move,
    ) -> dict:
        """Submit a move for a campaign attempt.

        Processes the move through the board service, updates obstacle
        count, checks win/lose conditions, and persists state.

        Args:
            attempt_id: The attempt to submit the move for.
            player_id: The player making the move.
            move: The swap move to execute.

        Returns:
            Dict with move_result, obstacles_remaining, status, and
            obstacle_events (transmutations and clearings).

        Raises:
            AppError (NOT_FOUND): If attempt not found.
            AppError (FORBIDDEN): If attempt doesn't belong to player.
            AppError (CONFLICT): If attempt is not in_progress.
            AppError (VALIDATION): If move is invalid.
            AppError (CONFLICT): If another request is already processing.
        """
        try:
            async with self._entity_locks.acquire(attempt_id):
                return await self._submit_move_locked(
                    attempt_id, player_id, move
                )
        except EntityBusyError:
            raise self._errors.conflict(
                "Another request is already processing this attempt",
                code="CONFLICT_ENTITY_BUSY",
                attempt_id=str(attempt_id),
            )

    async def _submit_move_locked(
        self,
        attempt_id: UUID,
        player_id: UUID,
        move: Move,
    ) -> dict:
        """Inner submit_move body — called under entity lock."""
        attempt = await self._campaign_repo.find_by_id(attempt_id)
        if attempt is None:
            raise self._errors.not_found(
                f"Campaign attempt not found: {attempt_id}",
                code="NOT_FOUND_CAMPAIGN_ATTEMPT",
                attempt_id=str(attempt_id),
            )

        if attempt.player_id != player_id:
            raise self._errors.forbidden(
                "Attempt does not belong to this player",
                code="FORBIDDEN_NOT_OWNER",
                attempt_id=str(attempt_id),
            )

        if attempt.status != "in_progress":
            raise self._errors.conflict(
                f"Attempt is {attempt.status}, not in_progress",
                code="CONFLICT_ATTEMPT_FINISHED",
                attempt_id=str(attempt_id),
                status=attempt.status,
            )

        # Reconstruct board from stored state.
        board_data = attempt.board_state
        grid = np.array(board_data["cells"], dtype=np.int8)
        func_grid = np.array(board_data["functions"], dtype=np.int8)
        board = BoardState(grid=grid, func_grid=func_grid)
        regen_counters = board_data.get("regen_counters", {})

        # Build card modifiers (optional).
        modifiers = None
        if self._card_service is not None:
            try:
                modifiers = await self._card_service.build_modifier_engine(
                    player_id
                )
            except Exception:
                pass  # Proceed without modifiers if lookup fails.

        # Compute moves_made for reshuffle seed derivation.
        level_def = self._level_loader.get(attempt.level_number)
        initial_moves = level_def["moves"] if level_def else attempt.moves_remaining
        moves_made = initial_moves - attempt.moves_remaining

        # Derive seed using shared function.
        move_seed = derive_move_seed(
            attempt.board_seed, player_id, attempt.moves_remaining
        )

        # Process through shared pipeline (CPU-bound, off event loop).
        pipeline_result = await asyncio.to_thread(
            process_move_pipeline,
            board,
            move,
            move_seed,
            board_service=self._board_service,
            scoring_service=self._scoring_service,
            board_gen_service=self._board_gen_service,
            board_seed=attempt.board_seed,
            player_id=player_id,
            moves_made=moves_made,
            moves_remaining=attempt.moves_remaining,
            modifiers=modifiers,
            deadlock_reshuffle=True,
            enable_instant_win=False,  # Lucky Rabbit disabled in campaign
        )

        if not pipeline_result.move_result.was_valid_match:
            raise self._errors.validation(
                "Invalid gem swap: no matches created",
                code="VALIDATION_INVALID_GEM_SWAP",
                attempt_id=str(attempt_id),
                from_pos=f"({move.from_pos.row},{move.from_pos.col})",
                to_pos=f"({move.to_pos.row},{move.to_pos.col})",
            )

        move_result = pipeline_result.move_result
        result_board = pipeline_result.result_board
        score_gained = pipeline_result.points_earned
        reshuffled = pipeline_result.reshuffled

        # Extract obstacle events from move result.
        obstacle_events = []
        for pos in move_result.obstacle_clearings:
            obstacle_events.append({
                "type": "clear",
                "row": pos.row,
                "col": pos.col,
            })
        for pos, from_func, to_func in move_result.obstacle_transmutations:
            obstacle_events.append({
                "type": "transmute",
                "row": pos.row,
                "col": pos.col,
                "from_func": from_func,
                "to_func": to_func,
            })

        # Check win BEFORE spread/regen so clearing all obstacles is a clean win.
        obstacles_remaining = _count_clearable_obstacles(result_board)
        moves_remaining = attempt.moves_remaining - 1

        if obstacles_remaining == 0:
            status = "won"
        else:
            # Apply post-move mechanics only if game continues.
            spread_events = _apply_obstacle_spread(result_board, level_def, move_seed)
            obstacle_events.extend(spread_events)

            regen_counters, regen_events = _apply_obstacle_regen(
                result_board, level_def, regen_counters, tick=True
            )
            obstacle_events.extend(regen_events)

            if spread_events or regen_events:
                if not self._board_service.has_valid_moves(result_board):
                    reshuffle_seed = move_seed ^ 0xBEEF_CAFE
                    result_board = self._board_service.shuffle_board(
                        result_board, reshuffle_seed
                    )
                    reshuffled = True

            # Recount after spread/regen.
            obstacles_remaining = _count_clearable_obstacles(result_board)

            if moves_remaining <= 0:
                status = "lost"
            else:
                status = "in_progress"

        # Persist updated state (including cumulative score for mega seed uniqueness).
        new_score = (attempt.score or 0) + score_gained
        board_state_dict = {
            "cells": result_board.grid.tolist(),
            "functions": result_board.func_grid.tolist(),
            "regen_counters": regen_counters,
        }
        await self._campaign_repo.update(
            attempt_id,
            board_state=board_state_dict,
            moves_remaining=moves_remaining,
            obstacles_remaining=obstacles_remaining,
            status=status,
            score=new_score,
        )

        # Handle level completion / failure.
        if status == "won":
            await self._on_level_won(player_id, attempt.level_number)
        elif status == "lost":
            await self._on_level_lost(player_id, attempt.level_number)

        self._logger.info(
            "Campaign move processed",
            attempt_id=str(attempt_id),
            obstacles_remaining=obstacles_remaining,
            moves_remaining=moves_remaining,
            status=status,
        )

        return {
            "move_result": move_result,
            "obstacles_remaining": obstacles_remaining,
            "moves_remaining": moves_remaining,
            "status": status,
            "obstacle_events": obstacle_events,
            "score_gained": score_gained,
            "reshuffled": reshuffled,
            "reshuffled_board": board_state_dict if reshuffled else None,
        }

    async def activate_mega(
        self,
        attempt_id: UUID,
        player_id: UUID,
        slot_index: int,
        source: str | None = None,
    ) -> dict:
        """Activate a banked mega gem or shuffle in a campaign attempt.

        Does NOT consume a move. Consumes from inventory (unless free source).
        Places the mega on the board, fires it, cascades, counts obstacles,
        and persists state.

        Args:
            attempt_id: The attempt to activate the mega in.
            player_id: The player activating.
            slot_index: 0-3 for mega gems, 4 for shuffle.
            source: Optional source tag (e.g. ``"card_shuffle"``).

        Returns:
            Dict with move_result, obstacles_remaining, moves_remaining,
            status, and obstacle_events.

        Raises:
            AppError (CONFLICT): If another request is already processing.
        """
        try:
            async with self._entity_locks.acquire(attempt_id):
                return await self._activate_mega_locked(
                    attempt_id, player_id, slot_index, source
                )
        except EntityBusyError:
            raise self._errors.conflict(
                "Another request is already processing this attempt",
                code="CONFLICT_ENTITY_BUSY",
                attempt_id=str(attempt_id),
            )

    async def _activate_mega_locked(
        self,
        attempt_id: UUID,
        player_id: UUID,
        slot_index: int,
        source: str | None = None,
    ) -> dict:
        """Inner activate_mega body — called under entity lock."""
        SLOT_MEGA_VALUES = {0: 11, 1: 22, 2: 33, 3: 44}

        attempt = await self._campaign_repo.find_by_id(attempt_id)
        if attempt is None:
            raise self._errors.not_found(
                f"Campaign attempt not found: {attempt_id}",
                code="NOT_FOUND_CAMPAIGN_ATTEMPT",
                attempt_id=str(attempt_id),
            )

        if attempt.player_id != player_id:
            raise self._errors.forbidden(
                "Attempt does not belong to this player",
                code="FORBIDDEN_NOT_OWNER",
                attempt_id=str(attempt_id),
            )

        if attempt.status != "in_progress":
            raise self._errors.conflict(
                f"Attempt is {attempt.status}, not in_progress",
                code="CONFLICT_ATTEMPT_FINISHED",
                attempt_id=str(attempt_id),
                status=attempt.status,
            )

        if slot_index < 0 or slot_index > 4:
            raise self._errors.validation(
                f"Invalid slot_index: {slot_index}",
                code="VALIDATION_INVALID_INPUT",
                slot_index=slot_index,
            )

        # Reconstruct board from stored state.
        board_data = attempt.board_state
        grid = np.array(board_data["cells"], dtype=np.int8)
        func_grid = np.array(board_data["functions"], dtype=np.int8)
        board = BoardState(grid=grid, func_grid=func_grid)
        regen_counters = board_data.get("regen_counters", {})

        # Build card modifiers (optional).
        modifiers = None
        if self._card_service is not None:
            try:
                modifiers = await self._card_service.build_modifier_engine(
                    player_id
                )
            except Exception:
                pass

        # Compute moves_made for reshuffle seed derivation.
        level_def = self._level_loader.get(attempt.level_number)
        initial_moves = level_def["moves"] if level_def else attempt.moves_remaining
        moves_made = initial_moves - attempt.moves_remaining

        # Derive seed with slot and score XOR for uniqueness.
        # The score XOR (FIXES THE BUG!) ensures each mega activation at
        # different cumulative scores produces a different placement seed.
        derived_seed = (
            derive_move_seed(
                attempt.board_seed, player_id, attempt.moves_remaining
            )
            ^ (slot_index * 7919)
            ^ ((attempt.score or 0) * 104729)
        )

        if slot_index == 4:
            # Shuffle branch.
            shuffled = await asyncio.to_thread(
                self._board_service.shuffle_board, board, derived_seed
            )

            board_state_dict = {
                "cells": shuffled.grid.tolist(),
                "functions": shuffled.func_grid.tolist(),
                "regen_counters": regen_counters,
            }

            obstacles_remaining = _count_clearable_obstacles(shuffled)

            await self._campaign_repo.update(
                attempt_id,
                board_state=board_state_dict,
                obstacles_remaining=obstacles_remaining,
            )

            # Build a dummy MoveProcessingResult for the shuffle.
            from src.modules.board.types import MoveProcessingResult

            dummy_move = Move(
                from_pos=Position(0, 0),
                to_pos=Position(0, 1),
                timestamp_ms=0,
            )
            move_result = MoveProcessingResult(
                initial_board=board,
                final_board=shuffled,
                move=dummy_move,
                was_valid_match=True,
                cascades=[],
                total_matches=0,
                total_gems_cleared=0,
                chain_count=0,
                special_gems_created=[],
            )

            self._logger.info(
                "Campaign shuffle activated",
                attempt_id=str(attempt_id),
                player_id=str(player_id),
            )

            return {
                "move_result": move_result,
                "obstacles_remaining": obstacles_remaining,
                "moves_remaining": attempt.moves_remaining,
                "status": attempt.status,
                "obstacle_events": [],
                "score_gained": 0,
            }

        # Mega gem branch (slots 0-3).
        mega_value = SLOT_MEGA_VALUES[slot_index]

        pipeline_result = await asyncio.to_thread(
            process_mega_pipeline,
            board,
            mega_value,
            derived_seed,
            board_service=self._board_service,
            scoring_service=self._scoring_service,
            board_gen_service=self._board_gen_service,
            board_seed=attempt.board_seed,
            player_id=player_id,
            moves_made=moves_made,
            moves_remaining=attempt.moves_remaining,
            modifiers=modifiers,
            deadlock_reshuffle=True,
            enable_instant_win=False,  # Lucky Rabbit disabled in campaign
        )

        move_result = pipeline_result.move_result
        result_board = pipeline_result.result_board
        score_gained = pipeline_result.points_earned
        reshuffled = pipeline_result.reshuffled

        # Extract obstacle events.
        obstacle_events = []
        for pos in move_result.obstacle_clearings:
            obstacle_events.append({
                "type": "clear",
                "row": pos.row,
                "col": pos.col,
            })
        for pos, from_func, to_func in move_result.obstacle_transmutations:
            obstacle_events.append({
                "type": "transmute",
                "row": pos.row,
                "col": pos.col,
                "from_func": from_func,
                "to_func": to_func,
            })

        # Check win BEFORE spread/regen so clearing all obstacles is a clean win.
        obstacles_remaining = _count_clearable_obstacles(result_board)

        if obstacles_remaining == 0:
            status = "won"
        else:
            # Apply post-mega mechanics only if game continues.
            spread_events = _apply_obstacle_spread(result_board, level_def, derived_seed)
            obstacle_events.extend(spread_events)

            regen_counters, regen_events = _apply_obstacle_regen(
                result_board, level_def, regen_counters, tick=False
            )
            obstacle_events.extend(regen_events)

            if spread_events or regen_events:
                if not self._board_service.has_valid_moves(result_board):
                    reshuffle_seed = derived_seed ^ 0xBEEF_CAFE
                    result_board = self._board_service.shuffle_board(
                        result_board, reshuffle_seed
                    )
                    reshuffled = True

            # Recount after spread/regen.
            obstacles_remaining = _count_clearable_obstacles(result_board)
            status = attempt.status  # stays in_progress

        # Persist updated state (including cumulative score for mega seed uniqueness).
        new_score = (attempt.score or 0) + score_gained
        board_state_dict = {
            "cells": result_board.grid.tolist(),
            "functions": result_board.func_grid.tolist(),
            "regen_counters": regen_counters,
        }
        await self._campaign_repo.update(
            attempt_id,
            board_state=board_state_dict,
            obstacles_remaining=obstacles_remaining,
            status=status,
            score=new_score,
        )

        if status == "won":
            await self._on_level_won(player_id, attempt.level_number)

        self._logger.info(
            "Campaign mega activated",
            attempt_id=str(attempt_id),
            slot_index=slot_index,
            mega_value=mega_value,
            obstacles_remaining=obstacles_remaining,
            status=status,
        )

        return {
            "move_result": move_result,
            "obstacles_remaining": obstacles_remaining,
            "moves_remaining": attempt.moves_remaining,
            "status": status,
            "obstacle_events": obstacle_events,
            "score_gained": score_gained,
            "reshuffled": reshuffled,
            "reshuffled_board": board_state_dict if reshuffled else None,
        }

    async def abandon_attempt(
        self, attempt_id: UUID, player_id: UUID
    ) -> CampaignAttemptRecord:
        """Abandon an active campaign attempt.

        Args:
            attempt_id: The attempt to abandon.
            player_id: The player abandoning.

        Returns:
            Updated attempt record.
        """
        attempt = await self._campaign_repo.find_by_id(attempt_id)
        if attempt is None:
            raise self._errors.not_found(
                f"Campaign attempt not found: {attempt_id}",
                code="NOT_FOUND_CAMPAIGN_ATTEMPT",
                attempt_id=str(attempt_id),
            )
        if attempt.player_id != player_id:
            raise self._errors.forbidden(
                "Attempt does not belong to this player",
                code="FORBIDDEN_NOT_OWNER",
            )
        if attempt.status != "in_progress":
            raise self._errors.conflict(
                f"Attempt is {attempt.status}, cannot abandon",
                code="CONFLICT_ATTEMPT_FINISHED",
            )

        return await self._campaign_repo.update(attempt_id, status="abandoned")

    async def abandon_stale_attempts(self, timeout_hours: int = 24) -> int:
        """Abandon campaign attempts that have been in-progress too long.

        Called periodically by the background cleanup task.

        Args:
            timeout_hours: Attempts older than this are considered stale.

        Returns:
            Number of attempts abandoned.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)
        stale_ids = await self._campaign_repo.find_stale_attempts(cutoff)

        if not stale_ids:
            return 0

        count = await self._campaign_repo.bulk_abandon(stale_ids)

        self._logger.info(
            "Stale campaign attempts abandoned",
            count=count,
            timeout_hours=timeout_hours,
        )

        return count

    async def get_player_progress(self, player_id: UUID) -> dict:
        """Get a player's campaign progress.

        Returns:
            Dict with campaign_level, max_level, active_attempt (if any).
        """
        player = await self._player_repo.find_by_id(player_id)
        if player is None:
            raise self._errors.not_found(
                f"Player not found: {player_id}",
                code="NOT_FOUND_PLAYER",
            )

        campaign_level = getattr(player, "campaign_level", 1)
        active = await self._campaign_repo.find_active_by_player(player_id)

        return {
            "campaign_level": campaign_level,
            "max_level": self._level_loader.max_level,
            "active_attempt_id": str(active.id) if active else None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _on_level_won(self, player_id: UUID, level_number: int) -> None:
        """Handle a level win: advance campaign_level and grant rewards."""
        player = await self._player_repo.find_by_id(player_id)
        if player is None:
            return

        campaign_level = getattr(player, "campaign_level", 1)

        # Only advance if this is the furthest unlocked level.
        if level_number >= campaign_level and level_number < self._level_loader.max_level:
            new_level = level_number + 1
            await self._player_repo.update(player_id, campaign_level=new_level)
            self._logger.info(
                "Campaign level advanced",
                player_id=str(player_id),
                from_level=campaign_level,
                to_level=new_level,
            )

        # Grant checkpoint reward (only on first clear).
        if level_number >= campaign_level:
            await self._grant_level_reward(player_id, level_number)

    async def _on_level_lost(self, player_id: UUID, level_number: int) -> None:
        """Handle a level loss: regress on checkpoint failure."""
        level_def = self._level_loader.get(level_number)
        if level_def is None or not level_def.get("is_checkpoint"):
            return  # Non-checkpoint: no regression.

        player = await self._player_repo.find_by_id(player_id)
        if player is None:
            return

        campaign_level = getattr(player, "campaign_level", 1)
        new_level = max(1, campaign_level - 5)

        if new_level < campaign_level:
            await self._player_repo.update(player_id, campaign_level=new_level)
            self._logger.info(
                "Campaign checkpoint regression",
                player_id=str(player_id),
                level_number=level_number,
                from_level=campaign_level,
                to_level=new_level,
            )

    async def _grant_level_reward(
        self, player_id: UUID, level_number: int
    ) -> None:
        """Grant the reward defined for a campaign level (if any).

        Uses the public EconomyService methods (credit_gold, grant_card_pack,
        grant_mega_reward) — the same path used by the barter marketplace.
        """
        level_def = self._level_loader.get(level_number)
        if level_def is None:
            return

        reward = level_def.get("reward")
        if not reward:
            return

        eco = self._economy_service
        if eco is None:
            self._logger.warning(
                "Economy service not available, skipping reward",
                player_id=str(player_id),
                campaign_level=level_number,
            )
            return

        reward_type = reward.get("type")
        source = f"campaign_level_{level_number}"

        if reward_type == "gold":
            amount = reward.get("amount", 0)
            if amount > 0:
                await eco.credit_gold(str(player_id), amount, source)
                self._logger.info(
                    "Campaign gold reward granted",
                    player_id=str(player_id),
                    campaign_level=level_number,
                    gold=amount,
                )

        elif reward_type == "card_pack":
            rarity = reward.get("rarity", "common")
            count = reward.get("count", 1)
            await eco.grant_card_pack(str(player_id), rarity, count, source)
            self._logger.info(
                "Campaign card pack reward granted",
                player_id=str(player_id),
                campaign_level=level_number,
                rarity=rarity,
                count=count,
            )

        elif reward_type == "mega_gem":
            from src.modules.economy.service import _MARKETPLACE_BY_ID

            item_id = reward.get("item_id")
            count = reward.get("count", 1)
            if item_id:
                item = _MARKETPLACE_BY_ID.get(item_id)
                if item:
                    slot_index = item.item_params["slot_index"]
                    await eco.grant_mega_reward(
                        str(player_id), slot_index, count
                    )
                    self._logger.info(
                        "Campaign mega gem reward granted",
                        player_id=str(player_id),
                        campaign_level=level_number,
                        item_id=item_id,
                        count=count,
                    )


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------


def _derive_board_seed(player_id: UUID, level_number: int) -> int:
    """Derive a deterministic board seed from player + level."""
    player_hash = hash(str(player_id)) & 0xFFFFFFFF
    return (player_hash ^ (level_number * _LCG_MULTIPLIER)) & 0x7FFFFFFF
