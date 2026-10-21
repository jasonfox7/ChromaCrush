"""Campaign request and response schemas.

Pydantic v2 models for the ``/api/v1/campaign`` endpoint group.
All response schemas are frozen (immutable).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StartAttemptRequest(BaseModel):
    """Request to start a campaign level attempt."""

    model_config = ConfigDict(frozen=True)

    level_number: int


class CampaignMoveRequest(BaseModel):
    """Request to submit a move in a campaign attempt."""

    model_config = ConfigDict(frozen=True)

    from_row: int
    from_col: int
    to_row: int
    to_col: int


class CampaignMegaRequest(BaseModel):
    """Request to activate a mega gem in a campaign attempt."""

    model_config = ConfigDict(frozen=True)

    slot_index: int
    source: str | None = None
