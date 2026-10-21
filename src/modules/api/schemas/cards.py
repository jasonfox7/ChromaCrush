"""Card-related Pydantic v2 schemas for API request/response models.

Defines request bodies for equip, unequip, and reorder operations,
and response models for card definitions, player cards, and loadouts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CardEquipRequest(BaseModel):
    """Request body for equipping a card into a slot."""

    card_instance_id: str = Field(description="UUID of the player card to equip.")
    slot: int = Field(ge=1, le=3, description="Target equip slot (1-3).")


class CardUnequipRequest(BaseModel):
    """Request body for unequipping a card."""

    card_instance_id: str = Field(description="UUID of the player card to unequip.")


class CardReorderRequest(BaseModel):
    """Request body for moving a card to a new position."""

    card_instance_id: str = Field(description="UUID of the player card to move.")
    new_position: int = Field(ge=1, description="Target position.")
