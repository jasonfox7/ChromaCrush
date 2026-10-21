"""Auth module for ChromaCrush.

Manages JWT authentication for humans, API key authentication for bots,
session lifecycle, and rate limiting support. This module is fully async
(except ``hash_password`` and ``verify_password`` which are sync/CPU-bound).

Exports:
    AuthService: Concrete service implementation.
    AuthServiceProtocol: Protocol interface for dependency injection.
    PasswordStoreProtocol: Protocol for password hash access.
    AuthResult: Authentication result DTO.
    ApiKeyCreationResult: API key creation result DTO.
    SessionInfo: Session information DTO.
    RateLimitStatus: Rate limit status DTO.
    TokenPayload: Decoded JWT payload DTO.
"""

from src.modules.auth.dto import (
    ApiKeyCreationResult,
    AuthResult,
    RateLimitStatus,
    SessionInfo,
    TokenPayload,
)
from src.modules.auth.protocols import AuthServiceProtocol, PasswordStoreProtocol
from src.modules.auth.service import AuthService

__all__ = [
    "AuthService",
    "AuthServiceProtocol",
    "PasswordStoreProtocol",
    "AuthResult",
    "ApiKeyCreationResult",
    "SessionInfo",
    "RateLimitStatus",
    "TokenPayload",
]
