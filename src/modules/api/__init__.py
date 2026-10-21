"""API module for ChromaCrush.

Terminal node of the dependency graph. Exposes all game functionality via
REST endpoints and WebSocket real-time updates. This module is the
presentation layer -- it owns no persistent data and delegates all
business logic to injected service protocols.

Exports:
    ApiFactory: Concrete factory for creating the FastAPI application.
    ApiFactoryProtocol: Protocol interface for dependency injection.
"""

from src.modules.api.factory import ApiFactory
from src.modules.api.protocols import ApiFactoryProtocol

__all__ = [
    "ApiFactory",
    "ApiFactoryProtocol",
]
