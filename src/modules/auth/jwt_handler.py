"""JWT token creation and decoding helper.

Encapsulates PyJWT operations for creating and validating JWT tokens.
Used internally by AuthService; not part of the public module interface.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt

from src.core.errors import AppError
from src.modules.auth.dto import TokenPayload


class JwtHandler:
    """Helper class for JWT token operations.

    Creates and decodes JWT tokens with standardized payload structure.
    Token payloads use short claim names per JWT convention:
    - ``sub``: player_id (subject)
    - ``sid``: session_id
    - ``typ``: token type ("access" or "refresh")
    - ``iat``: issued at (Unix timestamp)
    - ``exp``: expires at (Unix timestamp)

    Args:
        secret: The secret key for HS256 signing.
        algorithm: The JWT signing algorithm (default HS256).
    """

    def __init__(self, secret: str, algorithm: str = "HS256") -> None:
        self._secret = secret
        self._algorithm = algorithm

    def create_access_token(
        self,
        player_id: UUID,
        session_id: UUID,
        expiry_minutes: int,
    ) -> str:
        """Create a JWT access token.

        Args:
            player_id: The authenticated player's ID.
            session_id: The session ID to embed.
            expiry_minutes: Token lifetime in minutes.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(player_id),
            "sid": str(session_id),
            "typ": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=expiry_minutes)).timestamp()),
        }

        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_refresh_token(
        self,
        player_id: UUID,
        session_id: UUID,
        expiry_days: int,
    ) -> str:
        """Create a JWT refresh token.

        Args:
            player_id: The authenticated player's ID.
            session_id: The session ID to embed.
            expiry_days: Token lifetime in days.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(player_id),
            "sid": str(session_id),
            "typ": "refresh",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=expiry_days)).timestamp()),
        }

        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT token.

        Args:
            token: The encoded JWT string.

        Returns:
            Decoded TokenPayload with structured claim data.

        Raises:
            AppError: AUTH_TOKEN_EXPIRED if token has expired.
            AppError: AUTH_TOKEN_INVALID if token is malformed or signature invalid.
        """
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise AppError(
                code="AUTH_TOKEN_EXPIRED",
                message="Token has expired",
                http_status=401,
            )
        except jwt.InvalidTokenError as exc:
            raise AppError(
                code="AUTH_TOKEN_INVALID",
                message="Invalid token",
                context={"reason": str(exc)},
                http_status=401,
            )

        return TokenPayload(
            player_id=UUID(payload["sub"]),
            session_id=UUID(payload["sid"]),
            token_type=payload["typ"],
            issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
