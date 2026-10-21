"""Apple App Store Server API v2 payment provider.

Validates StoreKit receipts by decoding the client-side JWS transaction
and verifying it against Apple's Get Transaction Info endpoint.

Requires:
- A `.p8` private key from App Store Connect (In-App Purchase key)
- Key ID, Issuer ID, and Bundle ID configured in app settings
- `cryptography` package installed (via `pyjwt[crypto]`)

Apple docs:
https://developer.apple.com/documentation/appstoreserverapi
"""

from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import jwt

from src.modules.payments.types import PaymentProvider, ReceiptValidationResult

_PRODUCTION_BASE = "https://api.storekit.itunes.apple.com"
_SANDBOX_BASE = "https://api.storekit-sandbox.itunes.apple.com"


class AppleAppStoreProvider:
    """Validates receipts using Apple's App Store Server API v2."""

    def __init__(
        self,
        *,
        key_id: str,
        issuer_id: str,
        bundle_id: str,
        private_key_path: str,
        is_sandbox: bool = False,
    ) -> None:
        self._key_id = key_id
        self._issuer_id = issuer_id
        self._bundle_id = bundle_id
        self._is_sandbox = is_sandbox
        self._private_key = Path(private_key_path).read_text()

    # ------------------------------------------------------------------
    # PaymentProviderProtocol
    # ------------------------------------------------------------------

    async def validate_receipt(
        self,
        receipt_data: str,
        product_id: str,
        is_sandbox: bool = False,
    ) -> ReceiptValidationResult:
        """Validate a StoreKit receipt (JWS) against Apple's API.

        Args:
            receipt_data: The ``serverVerificationData`` from StoreKit
                (a JWS string signed by Apple).
            product_id: Expected product ID to verify against.
            is_sandbox: Whether this is a sandbox purchase.
        """
        use_sandbox = is_sandbox or self._is_sandbox

        try:
            # 1. Decode the client JWS to extract the transaction ID.
            #    We don't verify Apple's signature here — the server API
            #    call below is the authoritative check.
            transaction_info = _decode_jws_payload(receipt_data)
            transaction_id = transaction_info.get("transactionId")

            if not transaction_id:
                return ReceiptValidationResult(
                    valid=False,
                    provider=PaymentProvider.APPLE,
                    transaction_id=None,
                    product_id=product_id,
                    purchase_date=None,
                    is_duplicate=False,
                    is_sandbox=use_sandbox,
                    error_code="MISSING_TRANSACTION_ID",
                    raw_response=transaction_info,
                )

            # 2. Call Apple's Get Transaction Info endpoint.
            base_url = _SANDBOX_BASE if use_sandbox else _PRODUCTION_BASE
            url = f"{base_url}/inApps/v1/transactions/{transaction_id}"
            server_jwt = self._create_server_jwt()

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {server_jwt}"},
                )

            if resp.status_code == 404:
                return ReceiptValidationResult(
                    valid=False,
                    provider=PaymentProvider.APPLE,
                    transaction_id=str(transaction_id),
                    product_id=product_id,
                    purchase_date=None,
                    is_duplicate=False,
                    is_sandbox=use_sandbox,
                    error_code="TRANSACTION_NOT_FOUND",
                    raw_response={"status_code": 404},
                )

            if resp.status_code != 200:
                return ReceiptValidationResult(
                    valid=False,
                    provider=PaymentProvider.APPLE,
                    transaction_id=str(transaction_id),
                    product_id=product_id,
                    purchase_date=None,
                    is_duplicate=False,
                    is_sandbox=use_sandbox,
                    error_code=f"APPLE_API_{resp.status_code}",
                    raw_response={
                        "status_code": resp.status_code,
                        "body": resp.text[:500],
                    },
                )

            # 3. Decode Apple's response JWS.
            resp_body = resp.json()
            signed_transaction = resp_body.get("signedTransactionInfo", "")
            apple_txn = _decode_jws_payload(signed_transaction)

            # 4. Verify product and bundle match.
            apple_product_id = apple_txn.get("productId", "")
            apple_bundle_id = apple_txn.get("bundleId", "")
            apple_txn_id = apple_txn.get("transactionId", str(transaction_id))
            revocation_date = apple_txn.get("revocationDate")

            if apple_bundle_id != self._bundle_id:
                return ReceiptValidationResult(
                    valid=False,
                    provider=PaymentProvider.APPLE,
                    transaction_id=str(apple_txn_id),
                    product_id=apple_product_id,
                    purchase_date=None,
                    is_duplicate=False,
                    is_sandbox=use_sandbox,
                    error_code="BUNDLE_ID_MISMATCH",
                    raw_response={"expected": self._bundle_id, "got": apple_bundle_id},
                )

            if apple_product_id != product_id:
                return ReceiptValidationResult(
                    valid=False,
                    provider=PaymentProvider.APPLE,
                    transaction_id=str(apple_txn_id),
                    product_id=apple_product_id,
                    purchase_date=None,
                    is_duplicate=False,
                    is_sandbox=use_sandbox,
                    error_code="PRODUCT_ID_MISMATCH",
                    raw_response={"expected": product_id, "got": apple_product_id},
                )

            if revocation_date is not None:
                return ReceiptValidationResult(
                    valid=False,
                    provider=PaymentProvider.APPLE,
                    transaction_id=str(apple_txn_id),
                    product_id=apple_product_id,
                    purchase_date=None,
                    is_duplicate=False,
                    is_sandbox=use_sandbox,
                    error_code="TRANSACTION_REVOKED",
                    raw_response={"revocationDate": revocation_date},
                )

            # 5. Parse purchase date.
            purchase_date_ms = apple_txn.get("purchaseDate")
            purchase_date = None
            if purchase_date_ms is not None:
                purchase_date = datetime.fromtimestamp(
                    purchase_date_ms / 1000,
                    tz=timezone.utc,
                )

            apple_environment = apple_txn.get("environment", "")
            is_sandbox_txn = apple_environment.lower() == "sandbox"

            return ReceiptValidationResult(
                valid=True,
                provider=PaymentProvider.APPLE,
                transaction_id=str(apple_txn_id),
                product_id=apple_product_id,
                purchase_date=purchase_date,
                is_duplicate=False,
                is_sandbox=is_sandbox_txn,
                error_code=None,
                raw_response=apple_txn,
            )

        except Exception as e:
            return ReceiptValidationResult(
                valid=False,
                provider=PaymentProvider.APPLE,
                transaction_id=None,
                product_id=product_id,
                purchase_date=None,
                is_duplicate=False,
                is_sandbox=use_sandbox,
                error_code="PROVIDER_ERROR",
                raw_response={"error": str(e)},
            )

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify App Store Server Notifications v2 signature.

        The notification body itself is a JWS — decode and verify it
        was signed by Apple. For now, returns True and logs. Full
        verification can be added when webhook endpoint is built.
        """
        try:
            _decode_jws_payload(payload.decode("utf-8"))
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _create_server_jwt(self) -> str:
        """Create a short-lived JWT for authenticating with Apple's API.

        Uses ES256 algorithm with the .p8 private key from App Store
        Connect. Token is valid for 30 minutes.
        """
        now = int(time.time())
        payload: dict[str, Any] = {
            "iss": self._issuer_id,
            "iat": now,
            "exp": now + 1800,  # 30 minutes
            "aud": "appstoreconnect-v1",
            "bid": self._bundle_id,
        }
        return jwt.encode(
            payload,
            self._private_key,
            algorithm="ES256",
            headers={"kid": self._key_id},
        )


def _decode_jws_payload(jws_string: str) -> dict[str, Any]:
    """Decode a JWS payload without signature verification.

    Apple's JWS tokens are signed with their own keys. We extract
    the payload for reading — the server API call provides the
    authoritative verification.
    """
    parts = jws_string.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid JWS format: expected 3 parts, got {len(parts)}")

    # Base64url decode the payload (part 2).
    payload_b64 = parts[1]
    # Add padding if needed.
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding

    payload_bytes = base64.urlsafe_b64decode(payload_b64)
    return json.loads(payload_bytes)
