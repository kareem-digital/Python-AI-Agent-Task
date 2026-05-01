"""
client.py
---------
Low-level Binance Futures Testnet REST client.

Handles:
  - HMAC-SHA256 request signing
  - Timestamp & recvWindow management
  - HTTP request execution with retry-on-timeout
  - Raw response logging (request + response bodies)
"""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from typing import Any

import requests

from bot.logging_config import setup_logging

logger = setup_logging()

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000  # milliseconds
REQUEST_TIMEOUT = 10  # seconds


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx response or an error payload."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class BinanceClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.

    Args:
        api_key: Testnet API key.
        api_secret: Testnet API secret.
        base_url: Override the default testnet base URL (useful for testing).
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("API key and secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceClient initialised (base_url=%s)", self._base_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """Append HMAC-SHA256 signature to the parameter dict."""
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _get_timestamp(self) -> int:
        """Return current UTC timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        signed: bool = True,
    ) -> dict[str, Any]:
        """
        Execute an HTTP request against the Binance Futures Testnet.

        Args:
            method:   HTTP verb ('GET', 'POST', 'DELETE').
            endpoint: API path, e.g. '/fapi/v1/order'.
            params:   Query / body parameters.
            signed:   Whether to add timestamp + signature (default True).

        Returns:
            Parsed JSON response dict.

        Raises:
            BinanceAPIError: On non-2xx or error payload from Binance.
            requests.RequestException: On network-level failures.
        """
        params = params or {}

        if signed:
            params["timestamp"] = self._get_timestamp()
            params["recvWindow"] = RECV_WINDOW
            params = self._sign(params)

        url = f"{self._base_url}{endpoint}"

        logger.debug(
            "→ REQUEST  method=%s url=%s params=%s",
            method,
            url,
            {k: v for k, v in params.items() if k != "signature"},
        )

        try:
            if method.upper() in ("GET", "DELETE"):
                response = self._session.request(
                    method, url, params=params, timeout=REQUEST_TIMEOUT
                )
            else:  # POST / PUT
                response = self._session.request(
                    method, url, data=params, timeout=REQUEST_TIMEOUT
                )
        except requests.Timeout:
            logger.error("Request timed out: %s %s", method, url)
            raise
        except requests.ConnectionError as exc:
            logger.error("Network error: %s", exc)
            raise

        logger.debug(
            "← RESPONSE status=%s body=%s", response.status_code, response.text[:500]
        )

        try:
            data = response.json()
        except ValueError:
            data = {"msg": response.text, "code": response.status_code}

        # Binance returns errors as JSON with a negative 'code' field
        if isinstance(data, dict) and data.get("code", 0) < 0:
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

        if not response.ok:
            raise BinanceAPIError(
                response.status_code,
                data.get("msg", response.text) if isinstance(data, dict) else response.text,
            )

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_server_time(self) -> dict[str, Any]:
        """Fetch Binance server time (unsigned)."""
        return self._request("GET", "/fapi/v1/time", signed=False)

    def get_exchange_info(self) -> dict[str, Any]:
        """Fetch exchange info including symbol precision rules (unsigned)."""
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def get_account_info(self) -> dict[str, Any]:
        """Fetch futures account balance and position information."""
        return self._request("GET", "/fapi/v2/account")

    def place_order(self, **order_params: Any) -> dict[str, Any]:
        """
        Place a new futures order.

        Keyword Args:
            symbol (str):      e.g. 'BTCUSDT'
            side (str):        'BUY' or 'SELL'
            type (str):        'MARKET', 'LIMIT', 'STOP_MARKET', …
            quantity (float):  Contract quantity
            price (float):     Required for LIMIT orders
            stopPrice (float): Required for STOP_MARKET orders
            timeInForce (str): e.g. 'GTC' — required for LIMIT orders

        Returns:
            Order response dict from Binance.
        """
        # STOP_MARKET is not available on testnet via the regular endpoint.
        # Workaround: use STOP (stop-limit) with price = stopPrice ± 0.5% offset,
        # which IS supported and behaves similarly (fills near the stop trigger).
        if order_params.get("type") == "STOP_MARKET":
            order_params["type"] = "STOP"
            stop = float(order_params["stopPrice"])
            side = order_params.get("side", "SELL")
            # For SELL: limit price slightly below stop so it fills quickly after trigger
            # For BUY:  limit price slightly above stop
            offset = round(stop * 0.005, 2)  # 0.5% buffer
            order_params["price"] = round(stop - offset if side == "SELL" else stop + offset, 2)
            order_params["timeInForce"] = "GTC"

        return self._request("POST", "/fapi/v1/order", params=order_params)

    def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Fetch all open orders, optionally filtered by symbol."""
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params)

    def cancel_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Cancel an existing order by order ID."""
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
        )
