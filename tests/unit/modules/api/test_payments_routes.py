"""Unit tests for payments route handlers (/api/v1/payments/*).

Self-contained test file -- creates its own FastAPI app, mock services,
and test client.  No shared conftest dependency.

Covers:
- POST /payments/purchase/initiate  -- success (JWT), forbidden (API key)
- POST /payments/purchase/validate  -- success, invalid receipt
- POST /payments/restore            -- success
- GET  /payments/status             -- success
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.core.errors import AppError
from src.modules.api.adapters.bot_hints import BotHintGenerator
from src.modules.api.adapters.response import ResponseAdapter
from src.modules.api.middleware.error_handler import register_error_handlers

# ---------------------------------------------------------------------------
# Fake domain types
# ---------------------------------------------------------------------------


class _PurchaseStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class _PaymentProvider(Enum):
    APPLE = "apple"
    GOOGLE = "google"


@dataclass
class _PurchaseIntent:
    intent_id: UUID = field(default_factory=uuid4)
    product_id: str = "chromacrush_ad_free"
    status: _PurchaseStatus = _PurchaseStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class _ValidationResult:
    success: bool = True
    purchase_id: UUID | None = field(default_factory=uuid4)
    product_id: str = "chromacrush_ad_free"
    error_message: str | None = None


@dataclass
class _RestoredPurchase:
    id: UUID | None = field(default_factory=uuid4)
    product_id: str = "chromacrush_ad_free"
    status: _PurchaseStatus = _PurchaseStatus.COMPLETED


@dataclass
class _RestoreResult:
    restored_count: int = 1
    invalid_count: int = 0
    restored_purchases: list[_RestoredPurchase] = field(
        default_factory=lambda: [_RestoredPurchase()],
    )


@dataclass
class _PurchaseStatusResult:
    has_purchased_ad_free: bool = True
    is_refunded: bool = False
    purchase_date: datetime | None = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    provider: _PaymentProvider | None = _PaymentProvider.APPLE


@dataclass
class _PurchaseHistoryResult:
    items: list[Any] = field(default_factory=list)
    total: int = 3
    limit: int = 0
    offset: int = 0
    has_more: bool = False


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

_PLAYER_ID = "00000000-0000-0000-0000-000000000001"


class _TestAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app: FastAPI, player_id: str = _PLAYER_ID, auth_type: str = "jwt"
    ):
        super().__init__(app)
        self._player_id = player_id
        self._auth_type = auth_type

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.player_id = self._player_id
        request.state.auth_type = self._auth_type
        request.state.correlation_id = "test-correlation-id"
        return await call_next(request)


def _create_mock_error_service() -> MagicMock:
    errors = MagicMock()
    errors.forbidden.side_effect = (
        lambda message, code="FORBIDDEN_ACCESS_DENIED", **ctx: AppError(
            code=code,
            message=message,
            context=ctx,
            http_status=403,
        )
    )
    errors.not_found.side_effect = (
        lambda message, code="NOT_FOUND_RESOURCE", **ctx: AppError(
            code=code,
            message=message,
            context=ctx,
            http_status=404,
        )
    )
    errors.conflict.side_effect = (
        lambda message, code="CONFLICT_STATE", **ctx: AppError(
            code=code,
            message=message,
            context=ctx,
            http_status=409,
        )
    )
    errors.validation.side_effect = (
        lambda message, code="VALIDATION_INVALID_INPUT", **ctx: AppError(
            code=code,
            message=message,
            context=ctx,
            http_status=400,
        )
    )
    return errors


def _create_test_app(
    *,
    payment_service: AsyncMock | None = None,
    auth_type: str = "jwt",
    player_id: str = _PLAYER_ID,
) -> FastAPI:
    from src.modules.api.routes.payments import router

    app = FastAPI()
    app.add_middleware(_TestAuthMiddleware, player_id=player_id, auth_type=auth_type)

    app.state.config = MagicMock()
    app.state.config.get = MagicMock(return_value=True)
    app.state.logger = MagicMock()
    app.state.errors = _create_mock_error_service()
    app.state.response_adapter = ResponseAdapter()
    app.state.bot_hint_generator = BotHintGenerator()

    if payment_service is not None:
        app.state.payment_service = payment_service

    register_error_handlers(app)
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInitiatePurchase:
    """POST /api/v1/payments/purchase/initiate"""

    def test_success_jwt(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.initiate_purchase.return_value = _PurchaseIntent()

        app = _create_test_app(payment_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/payments/purchase/initiate",
            json={"product_id": "chromacrush_ad_free"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["product_id"] == "chromacrush_ad_free"
        assert data["status"] == "pending"
        assert data["intent_id"] is not None
        assert data["created_at"] is not None

    def test_forbidden_api_key(self) -> None:
        mock_svc = AsyncMock()

        app = _create_test_app(payment_service=mock_svc, auth_type="api_key")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/payments/purchase/initiate",
            json={"product_id": "chromacrush_ad_free"},
        )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN_BOT_NOT_ALLOWED"


class TestValidatePurchase:
    """POST /api/v1/payments/purchase/validate"""

    def test_success(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.validate_purchase.return_value = _ValidationResult(success=True)

        app = _create_test_app(payment_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/payments/purchase/validate",
            json={
                "receipt_data": "base64encodedreceipt==",
                "product_id": "chromacrush_ad_free",
                "transaction_id": "txn_123",
                "provider": "apple",
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["success"] is True
        assert data["message"] == "Purchase validated successfully"
        assert data["purchase_id"] is not None

    def test_invalid_receipt(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.validate_purchase.return_value = _ValidationResult(
            success=False,
            purchase_id=None,
            error_message="Receipt signature invalid",
        )

        app = _create_test_app(payment_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/payments/purchase/validate",
            json={
                "receipt_data": "invalidreceipt",
                "product_id": "chromacrush_ad_free",
                "transaction_id": "txn_bad",
                "provider": "apple",
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["success"] is False
        assert data["message"] == "Receipt signature invalid"
        assert data["purchase_id"] is None


class TestRestorePurchases:
    """POST /api/v1/payments/restore"""

    def test_success(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.restore_purchases.return_value = _RestoreResult()

        app = _create_test_app(payment_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/payments/restore",
            json={
                "receipts": [
                    {
                        "receipt_data": "base64receipt==",
                        "product_id": "chromacrush_ad_free",
                        "transaction_id": "txn_restore",
                        "provider": "apple",
                    },
                ],
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["restored_count"] == 1
        assert data["failed_count"] == 0
        assert len(data["results"]) == 1
        assert data["results"][0]["success"] is True
        assert data["results"][0]["message"] == "Restored"


class TestGetPurchaseStatus:
    """GET /api/v1/payments/status"""

    def test_success(self) -> None:
        mock_svc = AsyncMock()
        mock_svc.get_purchase_status.return_value = _PurchaseStatusResult()
        mock_svc.get_purchase_history.return_value = _PurchaseHistoryResult()

        app = _create_test_app(payment_service=mock_svc, auth_type="jwt")
        client = TestClient(app)
        resp = client.get("/api/v1/payments/status")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_ad_free"] is True
        assert len(data["active_purchases"]) == 1
        assert data["active_purchases"][0]["product_id"] == "ad_free"
        assert data["active_purchases"][0]["is_active"] is True
        assert data["purchase_history_count"] == 3
