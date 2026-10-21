"""Vault-related Pydantic v2 schemas for API request/response models.

Defines request bodies for shield activation and raid attempts, and
response models for artifacts, shields, raids, collection progress,
and raid targets.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ShieldRequest(BaseModel):
    """Request body for activating a vault shield.

    ``duration_hours`` is optional; omit to use the server default
    from ``vault.shield_duration_hours``.
    """

    duration_hours: int | None = Field(
        default=None,
        gt=0,
        description="Custom shield duration in hours (server default if omitted).",
    )


class RaidRequest(BaseModel):
    """Request body for attempting a vault raid."""

    defender_id: str = Field(description="Target player ID to raid.")


class ArtifactListQuery(BaseModel):
    """Query parameters for listing vault artifacts."""

    rarity: str | None = Field(default=None, description="Filter by rarity tier.")
    artifact_set: str | None = Field(default=None, description="Filter by set name.")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum results.")
    offset: int = Field(default=0, ge=0, description="Pagination offset.")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ArtifactResponse(BaseModel):
    """Single artifact in a player's vault."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    artifact_type_id: str
    rarity: str
    artifact_set: str
    name: str
    description: str
    acquired_at: str
    source: str


class ShieldResponse(BaseModel):
    """Shield status for a player's vault."""

    model_config = ConfigDict(frozen=True)

    is_active: bool
    expires_at: str | None = None
    remaining_hours: float | None = None


class RaidResponse(BaseModel):
    """Result of a vault raid attempt."""

    model_config = ConfigDict(frozen=True)

    success: bool
    artifacts_stolen: list[ArtifactResponse]
    defender_id: str
    message: str


class CollectionProgressResponse(BaseModel):
    """Progress toward completing an artifact set."""

    model_config = ConfigDict(frozen=True)

    set_name: str
    total_in_set: int
    collected: int
    completion_percentage: float
    missing_artifacts: list[str]


class RaidTargetResponse(BaseModel):
    """Potential raid target for bot API consumers."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    username: str
    vault_size: int
    is_protected: bool
