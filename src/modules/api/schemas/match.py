"""Match-related Pydantic v2 schemas for API request/response models.

Defines request bodies for move submission and response models for
match state, board state, move results, and match history.

Bot hints are included in MatchStateResponse when the requesting client
authenticates via API key and ``api.bot_hints_enabled`` is true.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class MoveRequest(BaseModel):
    """Request body for submitting a move (gem swap).

    Coordinates are zero-indexed, matching the 8x8 board grid.
    Positions must be orthogonally adjacent.
    """

    from_row: int = Field(ge=0, lt=8, description="Source row (0-7).")
    from_col: int = Field(ge=0, lt=8, description="Source column (0-7).")
    to_row: int = Field(ge=0, lt=8, description="Destination row (0-7).")
    to_col: int = Field(ge=0, lt=8, description="Destination column (0-7).")
    timestamp_ms: int = Field(
        gt=0, description="Client-side timestamp in milliseconds."
    )

    @model_validator(mode="after")
    def positions_must_be_adjacent(self) -> "MoveRequest":
        """Validate that from and to positions are orthogonally adjacent."""
        row_diff = abs(self.to_row - self.from_row)
        col_diff = abs(self.to_col - self.from_col)
        if not ((row_diff == 1 and col_diff == 0) or (row_diff == 0 and col_diff == 1)):
            msg = "Positions must be orthogonally adjacent"
            raise ValueError(msg)
        return self


class MegaActivationRequest(BaseModel):
    """Request body for activating a banked mega gem or shuffle.

    Slot indices 0-3 correspond to mega gem types (14, 24, 34, 44).
    Slot index 4 triggers a board shuffle.
    """

    slot_index: int = Field(
        ..., ge=0, le=4, description="Inventory slot (0-3 mega, 4 shuffle)."
    )
    timestamp_ms: int = Field(
        ..., gt=0, description="Client-side timestamp in milliseconds."
    )
    source: str | None = Field(
        default=None,
        description="Optional source tag (e.g. 'void_instability' for card-triggered).",
    )


class MatchHistoryQuery(BaseModel):
    """Query parameters for match history pagination."""

    limit: int = Field(default=20, ge=1, le=100, description="Maximum results.")
    offset: int = Field(default=0, ge=0, description="Pagination offset.")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PlayerMatchStateResponse(BaseModel):
    """A single player's state within a match."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    username: str
    score: int
    moves_made: int
    moves_remaining: int


class MatchSummaryResponse(BaseModel):
    """Summary of a match for history/list views."""

    model_config = ConfigDict(frozen=True)

    match_id: str
    status: str
    match_type: str
    opponent_id: str
    opponent_username: str
    player_score: int
    opponent_score: int
    won: bool | None
    created_at: str
    completed_at: str | None


class MatchStateResponse(BaseModel):
    """Full match state response, optionally including bot hints.

    ``bot_hints`` is populated only when the request is authenticated
    via API key and the server has ``api.bot_hints_enabled`` set to true.
    """

    model_config = ConfigDict(frozen=True)

    match_id: str
    status: str
    match_type: str
    player1: PlayerMatchStateResponse
    player2: PlayerMatchStateResponse
    is_my_turn: bool
    my_score: int
    opponent_score: int
    turns_remaining: int | None
    bot_hints: dict[str, Any] | None = None


class BoardStateResponse(BaseModel):
    """Response for a player's board view."""

    model_config = ConfigDict(frozen=True)

    cells: list[list[int]]
    size: int = 8
    moves_made: int
    moves_remaining: int
    score: int
    has_valid_moves: bool


class CascadeRemovalResponse(BaseModel):
    """A gem position removed during a cascade step."""

    model_config = ConfigDict(frozen=True)

    row: int
    col: int


class CascadeDropResponse(BaseModel):
    """A gem that fell due to gravity during a cascade step."""

    model_config = ConfigDict(frozen=True)

    gem_type: int
    from_row: int
    from_col: int
    to_row: int
    to_col: int


class CascadeSpawnResponse(BaseModel):
    """A new gem spawned to fill an empty cell during a cascade step."""

    model_config = ConfigDict(frozen=True)

    gem_type: int
    row: int
    col: int


class SpecialActivationResponse(BaseModel):
    """A special gem that was triggered during a cascade step."""

    model_config = ConfigDict(frozen=True)

    gem_type: int
    row: int
    col: int
    affected: list[CascadeRemovalResponse]
    is_mega: bool = False
    mega_func: int | None = None


class SpecialAttractionResponse(BaseModel):
    """Two special gems attracted toward a center gem, forming a mega gem."""

    model_config = ConfigDict(frozen=True)

    pos_a_row: int
    pos_a_col: int
    pos_b_row: int
    pos_b_col: int
    center_row: int
    center_col: int
    func_a: int
    func_b: int
    mega_func: int


class CascadeStepResponse(BaseModel):
    """One step in the cascade animation buffer (detect → clear → gravity → fill)."""

    model_config = ConfigDict(frozen=True)

    step_number: int
    removals: list[CascadeRemovalResponse]
    drops: list[CascadeDropResponse]
    spawns: list[CascadeSpawnResponse]
    special_gem_created: dict[str, int] | None = None
    special_activations: list[SpecialActivationResponse] = []
    special_attractions: list[SpecialAttractionResponse] = []
    injected_special: dict[str, int] | None = None


class MoveResultResponse(BaseModel):
    """Response after submitting a move."""

    model_config = ConfigDict(frozen=True)

    valid: bool
    score_gained: int
    new_board: BoardStateResponse | None = None
    matches_found: int
    cascades: int
    special_gems_created: int
    match_completed: bool
    match_status: str
    moves_remaining: int
    move_number: int
    cascade_steps: list[CascadeStepResponse] = []


class MoveHistoryEntry(BaseModel):
    """Single entry in move history for a match."""

    model_config = ConfigDict(frozen=True)

    move_number: int
    player_id: str
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    score_gained: int
    timestamp: str
