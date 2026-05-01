"""
validators.py
-------------
Input validation logic for CLI arguments before they reach the API layer.
"""

from __future__ import annotations

SUPPORTED_SYMBOLS = {
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
    "XRPUSDT", "DOGEUSDT", "ADAUSDT", "LTCUSDT",
}

VALID_SIDES = {"BUY", "SELL"}
# NOTE: STOP_MARKET / TAKE_PROFIT_MARKET require Algo endpoints which are
# unavailable on the Binance Futures Testnet. MARKET and LIMIT are fully supported.
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


class ValidationError(ValueError):
    """Raised when user-supplied input fails validation."""


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalise the trading symbol.

    Args:
        symbol: Raw symbol string from user input.

    Returns:
        Upper-cased symbol string.

    Raises:
        ValidationError: If the symbol is not in the supported set.
    """
    symbol = symbol.strip().upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise ValidationError(
            f"Unsupported symbol '{symbol}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_SYMBOLS))}"
        )
    return symbol


def validate_side(side: str) -> str:
    """
    Validate order side.

    Args:
        side: 'BUY' or 'SELL' (case-insensitive).

    Returns:
        Upper-cased side string.

    Raises:
        ValidationError: If side is not BUY or SELL.
    """
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}"
        )
    return side


def validate_order_type(order_type: str) -> str:
    """
    Validate order type.

    Args:
        order_type: 'MARKET' or 'LIMIT' (case-insensitive).
            Note: STOP_MARKET / TAKE_PROFIT_MARKET require Algo API endpoints
            which are not available on the Binance Futures Testnet.

    Returns:
        Upper-cased order type string.

    Raises:
        ValidationError: If order type is not supported.
    """
    order_type = order_type.strip().upper()
    conditional_types = {"STOP_MARKET", "STOP", "TAKE_PROFIT_MARKET", "TAKE_PROFIT"}
    if order_type in conditional_types:
        raise ValidationError(
            f"'{order_type}' orders require the Binance Algo Order API which is "
            f"not available on the Futures Testnet. Supported types: "
            f"{', '.join(sorted(VALID_ORDER_TYPES))}"
        )
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}"
        )
    return order_type


def validate_quantity(quantity: str | float) -> float:
    """
    Validate order quantity.

    Args:
        quantity: Quantity as string or float.

    Returns:
        Positive float quantity.

    Raises:
        ValidationError: If quantity is not a positive number.
    """
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got: '{quantity}'")
    if qty <= 0:
        raise ValidationError(f"Quantity must be greater than 0, got: {qty}")
    return qty


def validate_price(price: str | float | None, order_type: str) -> float | None:
    """
    Validate order price.

    Args:
        price: Price as string, float, or None.
        order_type: The order type — price is required for LIMIT orders.

    Returns:
        Positive float price, or None for MARKET orders.

    Raises:
        ValidationError: If price is required but missing/invalid.
    """
    if order_type in ("MARKET", "STOP_MARKET"):
        return None  # Price not needed for market or stop-market orders

    if price is None:
        raise ValidationError(
            f"Price is required for '{order_type}' orders."
        )

    try:
        p = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got: '{price}'")
    if p <= 0:
        raise ValidationError(f"Price must be greater than 0, got: {p}")
    return p


def validate_stop_price(stop_price: str | float | None, order_type: str) -> float | None:
    """
    Validate stop price for STOP_MARKET orders.

    Args:
        stop_price: Stop price value or None.
        order_type: The order type.

    Returns:
        Positive float stop price, or None.

    Raises:
        ValidationError: If stop price is required but missing/invalid.
    """
    if order_type != "STOP_MARKET":
        return None

    if stop_price is None:
        raise ValidationError("Stop price (--stop-price) is required for STOP_MARKET orders.")

    try:
        sp = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a number, got: '{stop_price}'")
    if sp <= 0:
        raise ValidationError(f"Stop price must be greater than 0, got: {sp}")
    return sp
