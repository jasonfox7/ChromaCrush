"""Repository protocol interfaces for the data layer.

Modules depend on these protocol interfaces; concrete implementations
live in ``src.data.repositories``.
"""

from src.data.protocols.api_key_repository import ApiKeyRepositoryProtocol
from src.data.protocols.energy_state_repository import EnergyStateRepositoryProtocol
from src.data.protocols.player_repository import PlayerRepositoryProtocol
from src.data.protocols.player_stats_repository import PlayerStatsRepositoryProtocol
from src.data.protocols.session_repository import SessionRepositoryProtocol
from src.data.protocols.gold_balance_repository import GoldBalanceRepositoryProtocol

__all__ = [
    "PlayerRepositoryProtocol",
    "PlayerStatsRepositoryProtocol",
    "EnergyStateRepositoryProtocol",
    "SessionRepositoryProtocol",
    "ApiKeyRepositoryProtocol",
    "GoldBalanceRepositoryProtocol",
]
