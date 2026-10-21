"""Auth endpoints.

Handles human registration/login, JWT refresh/logout, bot registration,
and bot API key management. Public endpoints (register, login, bot/register)
skip auth middleware. All other endpoints require JWT authentication.

Eight endpoints total:

- ``POST /api/v1/auth/register``     -- register human account
- ``POST /api/v1/auth/login``        -- login (returns JWT)
- ``POST /api/v1/auth/refresh``      -- refresh JWT token
- ``POST /api/v1/auth/logout``       -- invalidate session
- ``POST /api/v1/auth/bot/register`` -- register bot account
- ``POST /api/v1/auth/bot/api-key``  -- generate API key
- ``DELETE /api/v1/auth/bot/api-key/{key_id}`` -- revoke API key
- ``GET /api/v1/auth/bot/api-keys``  -- list API keys
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.core.types.game import PlayerId
from src.core.types.player import PlayerType
from src.modules.api.dependencies import (
    get_auth_service,
    get_correlation_id,
    get_current_player_id,
    get_response_adapter,
)
from src.modules.api.schemas.auth import (
    ApiKeyCreateRequest,
    ApiKeyListItem,
    ApiKeyResponse,
    AppleLoginRequest,
    BotRegisterRequest,
    BotRegisterResponse,
    LoginRequest,
    LoginResponse,
    PlayerResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
)

if TYPE_CHECKING:
    from src.modules.api.adapters.response import ResponseAdapter
    from src.modules.auth.protocols import AuthServiceProtocol

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# -- Helper -------------------------------------------------------------------


def _player_to_response(player: Any) -> dict[str, Any]:
    """Convert a Player domain object to a PlayerResponse-compatible dict.

    Args:
        player: Player domain entity.

    Returns:
        Dict suitable for PlayerResponse schema.
    """
    return {
        "player_id": str(player.id),
        "username": player.username,
        "player_type": player.player_type.value,
        "elo_rating": player.elo_rating,
        "created_at": player.created_at.isoformat(),
    }


def _auth_result_to_response(auth_result: Any) -> dict[str, Any]:
    """Convert an AuthResult DTO to a LoginResponse-compatible dict.

    Args:
        auth_result: AuthResult dataclass.

    Returns:
        Dict suitable for LoginResponse schema.
    """
    return {
        "access_token": auth_result.access_token,
        "refresh_token": auth_result.refresh_token,
        "token_type": auth_result.token_type,
        "expires_in": auth_result.expires_in,
    }


async def _onboard_new_player(request: Request, player: Any) -> None:
    """Grant starter cards and create a pool bot for a new human player."""
    card_service = getattr(request.app.state, "card_service", None)
    player_service = getattr(request.app.state, "player_service", None)
    logger = getattr(request.app.state, "logger", None)

    # Starter cards (15 cards: 97% common, 3% rare).
    if card_service is not None:
        try:
            await card_service.grant_starter_pack(player.id)
        except Exception:
            if logger:
                logger.warning("onboard.starter_pack_failed", player_id=str(player.id))

    # Create an independent pool bot to keep the bot pool sized right.
    if player_service is not None and card_service is not None:
        try:
            from src.modules.player.bot_names import generate_unique_bot_name

            bot_name = await generate_unique_bot_name(player_service)
            bot = await player_service.create_player(
                username=bot_name,
                player_type=PlayerType.BOT,
            )
            await card_service.grant_bot_full_loadout(bot.id)
        except Exception:
            if logger:
                logger.warning("onboard.bot_creation_failed", player_id=str(player.id))


# -- Public endpoints (no auth required) -------------------------------------


@router.post("/register")
async def register(
    body: RegisterRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
) -> dict[str, Any]:
    """Register a new human player account.

    Creates the player via the player service, then authenticates
    to return access and refresh tokens.

    Args:
        body: Registration fields (username, password, optional email).
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        auth_service: Injected auth service.

    Returns:
        Player info and auth tokens.
    """
    player_service = request.app.state.player_service

    # Hash password via auth service (sync, CPU-bound)
    password_hash = auth_service.hash_password(body.password)

    # Create the player account
    player = await player_service.create_player(
        username=body.username,
        player_type=PlayerType.HUMAN,
        password_hash=password_hash,
        email=body.email,
    )

    # Authenticate to get tokens
    auth_result = await auth_service.authenticate(body.username, body.password)

    # Grant starter cards and create a pool bot (non-critical).
    await _onboard_new_player(request, player)

    data = RegisterResponse(
        player=PlayerResponse(**_player_to_response(player)),
        auth=LoginResponse(**_auth_result_to_response(auth_result)),
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.post("/login")
async def login(
    body: LoginRequest,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
) -> dict[str, Any]:
    """Authenticate a human player and return JWT tokens.

    Args:
        body: Login credentials (username, password).
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        auth_service: Injected auth service.

    Returns:
        Access and refresh tokens.
    """
    auth_result = await auth_service.authenticate(body.username, body.password)

    data = LoginResponse(**_auth_result_to_response(auth_result)).model_dump(
        mode="json",
    )

    return response.success(data=data, correlation_id=correlation_id)


@router.post("/apple")
async def apple_login(
    body: AppleLoginRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
) -> dict[str, Any]:
    """Authenticate via Apple Sign-In.

    If the Apple user ID is new, auto-registers a player account, grants
    starter cards, and creates a pool bot. Returns JWT tokens regardless.

    Args:
        body: Apple Sign-In tokens (identity_token, optional display_name).
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        auth_service: Injected auth service.

    Returns:
        Auth tokens (and player info if newly registered).
    """
    auth_result, is_new = await auth_service.authenticate_apple(
        identity_token=body.identity_token,
        authorization_code=body.authorization_code,
        display_name=body.display_name,
    )

    # Decode the token to find the player (needed for response + onboarding).
    token_info = await auth_service.validate_token(auth_result.access_token)
    player_service = request.app.state.player_service
    player = await player_service.get_player(token_info.player_id)

    # If this is a brand new player, onboard them (starter cards + pool bot).
    if is_new:
        await _onboard_new_player(request, player)

    data = {
        "player": PlayerResponse(**_player_to_response(player)).model_dump(
            mode="json",
        ),
        "auth": LoginResponse(**_auth_result_to_response(auth_result)).model_dump(
            mode="json",
        ),
        "is_new_player": is_new,
    }

    return response.success(data=data, correlation_id=correlation_id)


@router.post("/bot/register")
async def register_bot(
    body: BotRegisterRequest,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
) -> dict[str, Any]:
    """Register a new bot player account.

    Bots authenticate via API keys, not passwords. After registration
    the owner should generate an API key via ``POST /auth/bot/api-key``.

    Args:
        body: Bot registration fields (bot_name, owner_contact).
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.

    Returns:
        Created bot player info.
    """
    player_service = request.app.state.player_service

    player = await player_service.create_player(
        username=body.bot_name,
        player_type=PlayerType.BOT,
    )

    data = BotRegisterResponse(
        player=PlayerResponse(**_player_to_response(player)),
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


# -- Authenticated endpoints -------------------------------------------------


@router.post("/refresh")
async def refresh_token(
    body: RefreshRequest,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
) -> dict[str, Any]:
    """Refresh an access token using a valid refresh token.

    Implements refresh token rotation: the provided refresh token
    is invalidated and a new token pair is returned.

    Args:
        body: Refresh token payload.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        auth_service: Injected auth service.

    Returns:
        New access and refresh tokens.
    """
    auth_result = await auth_service.refresh_token(body.refresh_token)

    data = LoginResponse(**_auth_result_to_response(auth_result)).model_dump(
        mode="json",
    )

    return response.success(data=data, correlation_id=correlation_id)


@router.post("/logout")
async def logout(
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Invalidate the current session (or all sessions).

    Args:
        request: The current HTTP request.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        auth_service: Injected auth service.
        player_id: Authenticated player ID.

    Returns:
        Success acknowledgement.
    """
    session_id = getattr(request.state, "session_id", None)

    await auth_service.logout(
        player_id=PlayerId(UUID(str(player_id))),
        session_id=session_id,
    )

    return response.success(
        data={"message": "Logged out successfully"},
        correlation_id=correlation_id,
    )


# -- Bot API key management --------------------------------------------------


@router.post("/bot/api-key")
async def create_api_key(
    body: ApiKeyCreateRequest,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Generate a new API key for an authenticated bot player.

    The raw API key is returned only once in this response.

    Args:
        body: Optional description for the key.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        auth_service: Injected auth service.
        player_id: Authenticated player ID (must be a bot).

    Returns:
        API key details including the raw key.
    """
    result = await auth_service.create_api_key(
        player_id=PlayerId(UUID(str(player_id))),
        description=body.description,
    )

    data = ApiKeyResponse(
        key_id=str(result.key_info.key_id),
        api_key=result.raw_key,
        created_at=result.key_info.created_at.isoformat(),
        description=body.description,
    ).model_dump(mode="json")

    return response.success(data=data, correlation_id=correlation_id)


@router.delete("/bot/api-key/{key_id}")
async def revoke_api_key(
    key_id: str,
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """Revoke an API key.

    Only the key owner can revoke their keys.

    Args:
        key_id: The API key identifier to revoke.
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        auth_service: Injected auth service.
        player_id: Authenticated player ID (must own the key).

    Returns:
        Success acknowledgement.
    """
    await auth_service.revoke_api_key(
        key_id=UUID(key_id),
        player_id=PlayerId(UUID(str(player_id))),
    )

    return response.success(
        data={"message": "API key revoked"},
        correlation_id=correlation_id,
    )


@router.get("/bot/api-keys")
async def list_api_keys(
    correlation_id: str = Depends(get_correlation_id),
    response: ResponseAdapter = Depends(get_response_adapter),
    auth_service: AuthServiceProtocol = Depends(get_auth_service),
    player_id: str = Depends(get_current_player_id),
) -> dict[str, Any]:
    """List all API keys for the authenticated bot player.

    Args:
        correlation_id: Request trace identifier.
        response: Standard response adapter.
        auth_service: Injected auth service.
        player_id: Authenticated player ID.

    Returns:
        List of API key metadata (no raw keys).
    """
    keys = await auth_service.list_api_keys(
        player_id=PlayerId(UUID(str(player_id))),
        include_revoked=False,
    )

    items = [
        ApiKeyListItem(
            key_id=str(key.key_id),
            description=None,
            prefix=key.prefix,
            created_at=key.created_at.isoformat(),
            is_revoked=key.revoked,
        ).model_dump(mode="json")
        for key in keys
    ]

    return response.success(data={"keys": items}, correlation_id=correlation_id)
