"""
orders.py
---------
High-level order placement logic built on top of BinanceClient.

Translates validated user input into Binance API calls and formats
the response into a human-readable summary dict.
"""

from __future__ import annotations

from typing import Any

from bot.client import BinanceClient, BinanceAPIError
from bot.logging_config import setup_logging

logger = setup_logging()


def _build_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None = None,
    stop_price: float | None = None,
) -> dict[str, Any]:
    """
    Build the parameter dict to send to Binance.

    Args:
        symbol:     Trading pair, e.g. 'BTCUSDT'.
        side:       'BUY' or 'SELL'.
        order_type: 'MARKET', 'LIMIT', or 'STOP_MARKET'.
        quantity:   Number of contracts.
        price:      Limit price (LIMIT orders only).
        stop_price: Trigger price (STOP_MARKET orders only).

    Returns:
        Dict of parameters ready for BinanceClient.place_order().
    """
    params: dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
    }

    if order_type == "LIMIT":
        if price is None:
            raise ValueError("Price is required for LIMIT orders.")
        params["price"] = price
        params["timeInForce"] = "GTC"  # Good-Till-Cancelled

    elif order_type == "STOP_MARKET":
        if stop_price is None:
            raise ValueError("Stop price is required for STOP_MARKET orders.")
        params["stopPrice"] = stop_price

    return params


def _format_response(response: dict[str, Any]) -> dict[str, Any]:
    """
    Extract the most relevant fields from the Binance order response.

    Args:
        response: Raw JSON response dict from Binance.

    Returns:
        Clean summary dict with key order details.
    """
    return {
        "orderId": response.get("orderId"),
        "symbol": response.get("symbol"),
        "side": response.get("side"),
        "type": response.get("type"),
        "status": response.get("status"),
        "origQty": response.get("origQty"),
        "executedQty": response.get("executedQty"),
        "avgPrice": response.get("avgPrice"),
        "price": response.get("price"),
        "stopPrice": response.get("stopPrice"),
        "timeInForce": response.get("timeInForce"),
        "updateTime": response.get("updateTime"),
    }


def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None = None,
    stop_price: float | None = None,
) -> dict[str, Any]:
    """
    Place an order on Binance Futures Testnet and return a formatted summary.

    Args:
        client:     Initialised BinanceClient instance.
        symbol:     Trading pair (e.g. 'BTCUSDT').
        side:       'BUY' or 'SELL'.
        order_type: 'MARKET', 'LIMIT', or 'STOP_MARKET'.
        quantity:   Contract quantity.
        price:      Limit price — required for LIMIT orders.
        stop_price: Trigger price — required for STOP_MARKET orders.

    Returns:
        Formatted order summary dict.

    Raises:
        BinanceAPIError: Propagated from the client on API-level errors.
        requests.RequestException: On network failures.
        ValueError: If required parameters are missing.
    """
    params = _build_order_params(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )

    logger.info(
        "Placing %s %s order | symbol=%s qty=%s price=%s stop_price=%s",
        side,
        order_type,
        symbol,
        quantity,
        price,
        stop_price,
    )

    try:
        raw_response = client.place_order(**params)
    except BinanceAPIError as exc:
        logger.error("Order placement failed: %s", exc)
        raise
    except Exception as exc:
        logger.error("Unexpected error during order placement: %s", exc)
        raise

    formatted = _format_response(raw_response)
    logger.info("Order placed successfully: %s", formatted)
    return formatted
