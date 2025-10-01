"""
receipt_verifier.py
Server-side receipt verification for Apple App Store and Google Play.

This module supports sandbox/production selection via environment variables.
For Apple: use App Store Server API (JWT) or legacy verifyReceipt if needed.
For Google: use Android Publisher API access token (service account).
"""

import os
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
import httpx


class ReceiptVerifier:
    def __init__(self) -> None:
        self.test_mode = os.getenv("PREMIUM_TEST_MODE", "false").lower() == "true"
        # Apple
        self.apple_api_base = os.getenv("APPLE_API_BASE", "https://api.storekit.itunes.apple.com")
        self.apple_issuer_id = os.getenv("APPLE_ISSUER_ID")
        self.apple_key_id = os.getenv("APPLE_KEY_ID")
        self.apple_private_key = os.getenv("APPLE_PRIVATE_KEY")

        # Google
        self.google_token = os.getenv("GOOGLE_PLAY_TOKEN")
        self.google_package = os.getenv("GOOGLE_PACKAGE_NAME")

    async def verify(self, platform: str, receipt_data: str, product_id: str, transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        if self.test_mode:
            # Simulated verification for development/testing
            return True, {
                "subscriptionStatus": "active",
                "expiresAt": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z",
                "raw": {"testMode": True}
            }

        if platform == "ios":
            return await self._verify_apple(receipt_data, product_id, transaction_id)
        elif platform == "android":
            return await self._verify_google(receipt_data, product_id, transaction_id)
        else:
            return False, {"error": "Unsupported platform"}

    async def _verify_apple(self, receipt_data: str, product_id: str, transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        # Placeholder: implement App Store Server API token generation and calls.
        # To avoid blocking deployment, return a failure if creds are missing.
        if not (self.apple_issuer_id and self.apple_key_id and self.apple_private_key):
            return False, {"error": "Apple credentials not configured"}
        # TODO: Implement JWT creation and lookup call.
        return False, {"error": "Apple verification not implemented"}

    async def _verify_google(self, purchase_token: str, product_id: str, subscription_id: str) -> Tuple[bool, Dict[str, Any]]:
        if not (self.google_token and self.google_package):
            return False, {"error": "Google credentials not configured"}
        # Minimal validation placeholder
        async with httpx.AsyncClient(timeout=10) as client:
            # The endpoint will vary based on product type (subscription vs one-time)
            # This is a stub to show intended structure
            return False, {"error": "Google verification not implemented"}


# Singleton instance
receipt_verifier = ReceiptVerifier()


