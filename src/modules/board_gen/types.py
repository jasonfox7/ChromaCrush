"""Board generation types — options, metadata, and result dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.types.board import BoardState
from src.core.types.game import GemType, Position
from src.core.types.match import MatchType as MatchType  # noqa: F401


@dataclass(frozen=True)
class StartingSpecial:
    """Specification for a starting special gem."""

    gem_type: GemType
    position: Position | None = None


@dataclass(frozen=True)
class BoardGenOptions:
    """Options for board generation.

    All fields are optional — ``None`` means use config defaults.
    """

    width: int | None = None
    height: int | None = None
    cascade_potential: float | None = None
    near_miss_factor: float | None = None
    starting_specials: list[StartingSpecial] | None = None
    gem_distribution: dict[int, float] | None = None


@dataclass
class GenerationMetadata:
    """Metadata about how the board was generated."""

    width: int
    height: int
    cascade_potential_target: float
    cascade_potential_actual: float
    near_miss_factor: float
    near_miss_count: int
    starting_specials_placed: list[tuple[Position, GemType]]
    valid_moves_count: int
    generation_attempts: int
    generation_time_ms: float


@dataclass
class GeneratedBoard:
    """Complete generation result."""

    board_state: BoardState
    seed: int
    generation_metadata: GenerationMetadata
