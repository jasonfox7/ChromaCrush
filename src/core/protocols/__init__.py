"""Protocol interfaces for core services.

All injectable service interfaces are defined here as typing.Protocol classes.
Modules depend on these protocols, never on concrete implementations.
"""

from src.core.protocols.config import ConfigProtocol
from src.core.protocols.correlation import (
    CorrelationContextProtocol,
    correlation_id_var,
)
from src.core.protocols.data_context import DataContextProtocol
from src.core.protocols.error_service import ErrorServiceProtocol
from src.core.protocols.logger import LoggerProtocol

__all__ = [
    "ConfigProtocol",
    "LoggerProtocol",
    "ErrorServiceProtocol",
    "CorrelationContextProtocol",
    "correlation_id_var",
    "DataContextProtocol",
]
