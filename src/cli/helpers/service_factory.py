"""Sync service builder for CLI commands.

Builds the four synchronous game services (board, scoring, special_gems,
board_gen) without requiring an async ApplicationContext.  These services
operate entirely in-memory on NumPy arrays and never perform I/O.

For async commands that need database/Redis access, use
``run_cli_async`` from ``src.cli.helpers.async_bridge`` instead --
it creates a full ``ApplicationContext`` with ALL services pre-wired.
"""

from __future__ import annotations

from src.core.composition_root import load_config
from src.core.error_service import ErrorService
from src.core.logger import LogService


def build_sync_services(config_path: str = "config/app.toml"):
    """Build the sync-only game services (board, scoring, special_gems, board_gen).

    Returns:
        A tuple of (BoardService, ScoringService, SpecialGemsService, BoardGenService).
    """
    config = load_config(config_path)
    logger = LogService(config)
    errors = ErrorService(logger)

    from src.modules.board.service import BoardService
    from src.modules.scoring.service import ScoringService
    from src.modules.special_gems.service import SpecialGemsService
    from src.modules.board_gen.service import BoardGenService

    board_svc = BoardService(config, logger, errors)
    scoring_svc = ScoringService(config, logger, errors)
    special_gems_svc = SpecialGemsService(config, logger, errors, scoring_svc)
    board_gen_svc = BoardGenService(config, logger, errors, board_svc, special_gems_svc)

    return board_svc, scoring_svc, special_gems_svc, board_gen_svc
