"""Debug logger for end-to-end move tracing.

Captures structured events at every step of the board/move pipeline
so frontend and backend state can be compared side-by-side.

Controlled by ``app.debug`` in config. When disabled, all methods
are no-ops. When enabled, writes JSON events to a log file and
optionally to stdout.

Usage:
    debug = DebugLogger(config)
    debug.log_board_state("before_swap", board, match_id=mid)
    debug.log_move_attempt(match_id, player_id, from_pos, to_pos, board)
    debug.log_move_result(match_id, valid, matches, board_after)
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.core.protocols.config import ConfigProtocol


class DebugCategory(str, Enum):
    """Categories for debug events."""

    BOARD = "BOARD"
    MOVE = "MOVE"
    MATCH = "MATCH"
    CASCADE = "CASCADE"
    SYNC = "SYNC"
    API = "API"
    ERROR = "ERROR"


def _board_to_ascii(cells: list[list[int]] | dict) -> list[str]:
    """Convert board grid to ASCII rows for readable logging."""
    if isinstance(cells, dict):
        cells = cells.get("cells", [])
    gem_chars = {0: ".", 1: "R", 2: "B", 3: "G", 4: "Y", 5: "P", 6: "O"}
    rows = []
    for r, row in enumerate(cells):
        chars = " ".join(gem_chars.get(int(v), "?") for v in row)
        rows.append(f"  {r}: {chars}")
    return rows


class DebugLogger:
    """Structured debug logger for game state tracing.

    Created once in the composition root. Injected into services
    via ``__init__``. All operations are no-ops when ``app.debug``
    is false.
    """

    def __init__(self, config: ConfigProtocol) -> None:
        self._enabled: bool = bool(config.get("app.debug", False))
        self._events: list[dict[str, Any]] = []
        self._log_file: str | None = None

        if self._enabled:
            log_dir = config.get("app.debug_log_dir", "logs")
            os.makedirs(log_dir, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            self._log_file = os.path.join(log_dir, f"debug_{ts}.jsonl")

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ------------------------------------------------------------------
    # Core log method
    # ------------------------------------------------------------------

    def _log(
        self,
        category: DebugCategory,
        action: str,
        data: dict[str, Any],
        *,
        match_id: str | None = None,
        player_id: str | None = None,
    ) -> None:
        """Write a structured debug event."""
        if not self._enabled:
            return

        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "epoch_ms": int(time.time() * 1000),
            "cat": category.value,
            "action": action,
            "match_id": match_id,
            "player_id": player_id,
            **data,
        }

        self._events.append(event)

        # Write to JSONL file
        if self._log_file:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, default=str) + "\n")

        # Also print for immediate visibility
        print(f"[DEBUG:{category.value}] {action}", flush=True)

    # ------------------------------------------------------------------
    # Board state logging
    # ------------------------------------------------------------------

    def log_board_state(
        self,
        label: str,
        board_cells: list[list[int]],
        *,
        match_id: str | None = None,
        player_id: str | None = None,
    ) -> None:
        """Log a complete board state snapshot."""
        if not self._enabled:
            return

        ascii_rows = _board_to_ascii(board_cells)
        self._log(
            DebugCategory.BOARD,
            f"board_state:{label}",
            {
                "board": board_cells,
                "ascii": ascii_rows,
            },
            match_id=match_id,
            player_id=player_id,
        )
        # Also print the ASCII board for immediate console visibility
        for row in ascii_rows:
            print(f"  {row}", flush=True)

    def log_board_loaded_from_db(
        self,
        board_cells: list[list[int]],
        *,
        match_id: str | None = None,
        player_id: str | None = None,
        source: str = "db",
    ) -> None:
        """Log the exact board state as loaded from the database."""
        if not self._enabled:
            return

        self._log(
            DebugCategory.BOARD,
            f"board_loaded:{source}",
            {
                "board": board_cells,
                "ascii": _board_to_ascii(board_cells),
            },
            match_id=match_id,
            player_id=player_id,
        )

    # ------------------------------------------------------------------
    # Move logging
    # ------------------------------------------------------------------

    def log_move_attempt(
        self,
        match_id: str,
        player_id: str,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
        board_before: list[list[int]],
    ) -> None:
        """Log a move attempt with full board context."""
        if not self._enabled:
            return

        from_gem = board_before[from_row][from_col]
        to_gem = board_before[to_row][to_col]

        self._log(
            DebugCategory.MOVE,
            "move_attempt",
            {
                "from": [from_row, from_col],
                "to": [to_row, to_col],
                "from_gem": from_gem,
                "to_gem": to_gem,
                "board_before": board_before,
                "ascii": _board_to_ascii(board_before),
            },
            match_id=match_id,
            player_id=player_id,
        )

        # Print key info
        print(
            f"  Move ({from_row},{from_col})[gem={from_gem}] -> "
            f"({to_row},{to_col})[gem={to_gem}]",
            flush=True,
        )

    def log_post_swap_board(
        self,
        board_after_swap: list[list[int]],
        *,
        match_id: str | None = None,
    ) -> None:
        """Log the board state immediately after the swap (before match detection)."""
        if not self._enabled:
            return

        self._log(
            DebugCategory.MOVE,
            "post_swap_board",
            {
                "board": board_after_swap,
                "ascii": _board_to_ascii(board_after_swap),
            },
            match_id=match_id,
        )

    # ------------------------------------------------------------------
    # Match detection logging
    # ------------------------------------------------------------------

    def log_match_detection(
        self,
        matches_found: int,
        total_gems: int,
        match_details: list[dict[str, Any]],
        board: list[list[int]],
        *,
        match_id: str | None = None,
    ) -> None:
        """Log match detection results with full detail."""
        if not self._enabled:
            return

        self._log(
            DebugCategory.MATCH,
            "match_detection",
            {
                "matches_found": matches_found,
                "total_gems": total_gems,
                "match_details": match_details,
                "board": board,
            },
            match_id=match_id,
        )

        if matches_found > 0:
            for m in match_details:
                print(
                    f"  Match: gem={m.get('gem_type')} "
                    f"{'H' if m.get('horizontal') else 'V'} "
                    f"len={m.get('length')} "
                    f"positions={m.get('positions')}",
                    flush=True,
                )
        else:
            print("  No matches found!", flush=True)

    # ------------------------------------------------------------------
    # Cascade logging
    # ------------------------------------------------------------------

    def log_cascade_step(
        self,
        step: int,
        matches_found: int,
        gems_cleared: int,
        board_after: list[list[int]],
        *,
        match_id: str | None = None,
    ) -> None:
        """Log a single cascade step."""
        if not self._enabled:
            return

        self._log(
            DebugCategory.CASCADE,
            f"cascade_step:{step}",
            {
                "step": step,
                "matches_found": matches_found,
                "gems_cleared": gems_cleared,
                "board_after": board_after,
                "ascii": _board_to_ascii(board_after),
            },
            match_id=match_id,
        )

    # ------------------------------------------------------------------
    # Move result logging
    # ------------------------------------------------------------------

    def log_move_result(
        self,
        valid: bool,
        chain_count: int,
        total_cleared: int,
        board_after: list[list[int]] | None,
        *,
        match_id: str | None = None,
        player_id: str | None = None,
        error: str | None = None,
    ) -> None:
        """Log the final result of a move."""
        if not self._enabled:
            return

        data: dict[str, Any] = {
            "valid": valid,
            "chain_count": chain_count,
            "total_cleared": total_cleared,
        }
        if board_after is not None:
            data["board_after"] = board_after
            data["ascii"] = _board_to_ascii(board_after)
        if error:
            data["error"] = error

        self._log(
            DebugCategory.MOVE,
            "move_result",
            data,
            match_id=match_id,
            player_id=player_id,
        )

        status = "VALID" if valid else "INVALID"
        print(
            f"  Result: {status} chains={chain_count} cleared={total_cleared}",
            flush=True,
        )

    # ------------------------------------------------------------------
    # API layer logging
    # ------------------------------------------------------------------

    def log_api_request(
        self,
        endpoint: str,
        method: str,
        *,
        match_id: str | None = None,
        player_id: str | None = None,
        body: dict[str, Any] | None = None,
    ) -> None:
        """Log an incoming API request."""
        if not self._enabled:
            return

        self._log(
            DebugCategory.API,
            f"{method} {endpoint}",
            {"body": body or {}},
            match_id=match_id,
            player_id=player_id,
        )

    def log_api_response(
        self,
        endpoint: str,
        status: str,
        *,
        match_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Log an outgoing API response."""
        if not self._enabled:
            return

        self._log(
            DebugCategory.API,
            f"response:{endpoint}",
            {"status": status, "data": data or {}},
            match_id=match_id,
        )

    # ------------------------------------------------------------------
    # Error logging
    # ------------------------------------------------------------------

    def log_error(
        self,
        message: str,
        *,
        match_id: str | None = None,
        player_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log a debug-level error with context."""
        if not self._enabled:
            return

        self._log(
            DebugCategory.ERROR,
            message,
            {"context": context or {}},
            match_id=match_id,
            player_id=player_id,
        )

    # ------------------------------------------------------------------
    # Query / export
    # ------------------------------------------------------------------

    def get_events(
        self,
        category: DebugCategory | None = None,
        match_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query stored events for inspection."""
        events = self._events
        if category:
            events = [e for e in events if e["cat"] == category.value]
        if match_id:
            events = [e for e in events if e.get("match_id") == match_id]
        return events

    def get_log_file_path(self) -> str | None:
        """Return the path to the current debug log file."""
        return self._log_file

    def clear(self) -> None:
        """Clear in-memory events."""
        self._events.clear()
