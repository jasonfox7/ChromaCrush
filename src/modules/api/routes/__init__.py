"""API route registration.

Exports all routers for registration in the ``ApiFactory``.

Wave 9a (foundation) created health and WebSocket routers.
Wave 9b created the ten domain route modules.
Wave 9c wires all routers together here.
"""

from src.modules.api.routes.ads import router as ads_router
from src.modules.api.routes.auth import router as auth_router
from src.modules.api.routes.bot_earnings import router as bot_earnings_router
from src.modules.api.routes.energy import router as energy_router
from src.modules.api.routes.events import router as events_router
from src.modules.api.routes.health import router as health_router
from src.modules.api.routes.inventory import router as inventory_router
from src.modules.api.routes.matchmaking import router as matchmaking_router
from src.modules.api.routes.matches import router as matches_router
from src.modules.api.routes.payments import router as payments_router
from src.modules.api.routes.players import router as players_router
from src.modules.api.routes.vault import router as vault_router
from src.modules.api.routes.cards import router as cards_router
from src.modules.api.routes.ws import router as ws_router
from src.modules.api.routes.economy import router as economy_router
from src.modules.api.routes.campaign import router as campaign_router

__all__ = [
    "ads_router",
    "auth_router",
    "bot_earnings_router",
    "economy_router",
    "energy_router",
    "events_router",
    "health_router",
    "inventory_router",
    "matchmaking_router",
    "matches_router",
    "payments_router",
    "players_router",
    "vault_router",
    "cards_router",
    "ws_router",
    "campaign_router",
]
