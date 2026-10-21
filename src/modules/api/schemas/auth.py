"""Auth request and response schemas.

Pydantic v2 models for the ``/api/v1/auth`` endpoint group.
Request schemas are mutable (accept user input), response schemas
are frozen (immutable output).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# -- Request schemas ----------------------------------------------------------


class RegisterRequest(BaseModel):
    """Human player registration request."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Unique username (3-32 chars, alphanumeric + underscore).",
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Account password (minimum 8 characters).",
    )
    email: str | None = Field(
        default=None,
        description="Optional email address.",
    )


class LoginRequest(BaseModel):
    """Human player login request."""

    username: str = Field(..., description="Player username.")
    password: str = Field(..., description="Account password.")


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(..., description="Valid refresh token.")


class BotRegisterRequest(BaseModel):
    """Bot account registration request."""

    bot_name: str = Field(
        ...,
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Unique bot name (3-32 chars, alphanumeric + underscore).",
    )
    owner_contact: str = Field(
        ...,
        description="Contact information for the bot owner.",
    )


class AppleLoginRequest(BaseModel):
    """Apple Sign-In authentication request."""

    identity_token: str = Field(
        ...,
        description="JWT identity token from Apple Sign-In.",
    )
    authorization_code: str | None = Field(
        default=None,
        description="Authorization code from Apple Sign-In.",
    )
    display_name: str | None = Field(
        default=None,
        max_length=64,
        description="User's display name (given + family name).",
    )


class ApiKeyCreateRequest(BaseModel):
    """API key creation request."""

    description: str | None = Field(
        default=None,
        max_length=255,
        description="Optional description for the API key.",
    )


# -- Response schemas ---------------------------------------------------------


class LoginResponse(BaseModel):
    """Authentication token response (login or register)."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class PlayerResponse(BaseModel):
    """Minimal player info returned with auth responses."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    username: str
    player_type: str
    elo_rating: int
    created_at: str


class RegisterResponse(BaseModel):
    """Registration response with player info and tokens."""

    model_config = ConfigDict(frozen=True)

    player: PlayerResponse
    auth: LoginResponse


class BotRegisterResponse(BaseModel):
    """Bot registration response with player info (no tokens)."""

    model_config = ConfigDict(frozen=True)

    player: PlayerResponse


class ApiKeyResponse(BaseModel):
    """API key creation response (includes the raw key once)."""

    model_config = ConfigDict(frozen=True)

    key_id: str
    api_key: str
    created_at: str
    description: str | None = None


class ApiKeyListItem(BaseModel):
    """API key metadata for listing (no raw key)."""

    model_config = ConfigDict(frozen=True)

    key_id: str
    description: str | None = None
    prefix: str
    created_at: str
    is_revoked: bool
