"""API factory protocol.

Defines the protocol interface for creating and configuring the FastAPI
application. The composition root wires this via ``ApiFactory``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from fastapi import FastAPI


class ApiFactoryProtocol(Protocol):
    """Factory for creating the FastAPI application.

    The composition root instantiates an ``ApiFactory`` with all required
    service protocols injected, then calls ``create_app()`` to produce
    the configured FastAPI application.
    """

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application.

        Returns:
            Configured FastAPI app with all routes, middleware, and
            exception handlers registered.
        """
        ...
