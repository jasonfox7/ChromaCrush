"""FastAPI dependency injection providers.

The ``ApiFactory`` stores all injected services on the FastAPI
``app.state`` during application creation. These dependency functions
retrieve services from ``request.app.state``, making them available
to route handlers via ``Depends()``.

Usage in route handlers::

    @router.get("/some-endpoint")
    async def handler(
        request: Request,
        player_service: PlayerServiceProtocol = Depends(get_player_service),
    ):
        ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from src.modules.api.adapters.bot_hints import BotHintGenerator
from src.modules.api.adapters.response import ResponseAdapter

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.ads.protocols import AdServiceProtocol
    from src.modules.auth.protocols import AuthServiceProtocol
    from src.modules.bot_earnings.protocols import BotEarningsServiceProtocol
    from src.modules.energy.protocols import EnergyServiceProtocol
    from src.modules.events.protocols import EventServiceProtocol
    from src.modules.match.protocols import MatchServiceProtocol
    from src.modules.matchmaking.protocols import MatchmakingServiceProtocol
    from src.modules.payments.protocols import PaymentServiceProtocol
    from src.modules.player.protocols import PlayerServiceProtocol
    from src.modules.vault.protocols import VaultServiceProtocol


# -- Core service dependencies ------------------------------------------------


def get_config(request: Request) -> ConfigProtocol:
    """Retrieve the configuration service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected ConfigProtocol instance.
    """
    return request.app.state.config


def get_logger(request: Request) -> LoggerProtocol:
    """Retrieve the logger service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected LoggerProtocol instance.
    """
    return request.app.state.logger


def get_errors(request: Request) -> ErrorServiceProtocol:
    """Retrieve the error service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected ErrorServiceProtocol instance.
    """
    return request.app.state.errors


# -- Module service dependencies -----------------------------------------------


def get_auth_service(request: Request) -> AuthServiceProtocol:
    """Retrieve the auth service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected AuthServiceProtocol instance.
    """
    return request.app.state.auth_service


def get_player_service(request: Request) -> PlayerServiceProtocol:
    """Retrieve the player service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected PlayerServiceProtocol instance.
    """
    return request.app.state.player_service


def get_energy_service(request: Request) -> EnergyServiceProtocol:
    """Retrieve the energy service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected EnergyServiceProtocol instance.
    """
    return request.app.state.energy_service


def get_matchmaking_service(request: Request) -> MatchmakingServiceProtocol:
    """Retrieve the matchmaking service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected MatchmakingServiceProtocol instance.
    """
    return request.app.state.matchmaking_service


def get_match_service(request: Request) -> MatchServiceProtocol:
    """Retrieve the match service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected MatchServiceProtocol instance.
    """
    return request.app.state.match_service


def get_vault_service(request: Request) -> VaultServiceProtocol:
    """Retrieve the vault service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected VaultServiceProtocol instance.
    """
    return request.app.state.vault_service


def get_event_service(request: Request) -> EventServiceProtocol:
    """Retrieve the event service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected EventServiceProtocol instance.
    """
    return request.app.state.event_service


def get_ad_service(request: Request) -> AdServiceProtocol:
    """Retrieve the ad service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected AdServiceProtocol instance.
    """
    return request.app.state.ad_service


def get_payment_service(request: Request) -> PaymentServiceProtocol:
    """Retrieve the payment service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected PaymentServiceProtocol instance.
    """
    return request.app.state.payment_service


def get_card_service(request: Request) -> Any:
    """Retrieve the card service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected CardService instance.
    """
    return request.app.state.card_service


def get_bot_earnings_service(request: Request) -> BotEarningsServiceProtocol:
    """Retrieve the bot earnings service from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The injected BotEarningsServiceProtocol instance.
    """
    return request.app.state.bot_earnings_service


# -- Adapter dependencies -----------------------------------------------------


def get_response_adapter(request: Request) -> ResponseAdapter:
    """Retrieve the response adapter from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The ResponseAdapter instance.
    """
    return request.app.state.response_adapter


def get_bot_hint_generator(request: Request) -> BotHintGenerator:
    """Retrieve the bot hint generator from app state.

    Args:
        request: The current HTTP request.

    Returns:
        The BotHintGenerator instance.
    """
    return request.app.state.bot_hint_generator


# -- Request context helpers ---------------------------------------------------


def get_correlation_id(request: Request) -> str:
    """Get the correlation ID for the current request.

    Falls back to 'unknown' if the correlation middleware has not run.

    Args:
        request: The current HTTP request.

    Returns:
        The correlation ID string.
    """
    return getattr(request.state, "correlation_id", "unknown")


def get_current_player_id(request: Request) -> str:
    """Get the authenticated player ID for the current request.

    Args:
        request: The current HTTP request.

    Returns:
        The player ID as a string from auth middleware.

    Raises:
        AttributeError: If no player has been authenticated.
    """
    return str(request.state.player_id)


def get_auth_type(request: Request) -> str:
    """Get the authentication type for the current request.

    Args:
        request: The current HTTP request.

    Returns:
        Either "jwt" or "api_key".
    """
    return getattr(request.state, "auth_type", "unknown")
