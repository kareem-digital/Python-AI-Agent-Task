"""
cli.py
------
Command-line entry point for the Binance Futures Testnet Trading Bot.

Note: stdout is reconfigured to UTF-8 so box-drawing chars render correctly
on Windows terminals.

Usage examples:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
    python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3000
    python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 58000
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap

import io

from dotenv import load_dotenv

# Force UTF-8 output on Windows so Unicode chars render correctly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bot.client import BinanceClient, BinanceAPIError
from bot.logging_config import setup_logging
from bot.orders import place_order
from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

# ── Load .env if present ──────────────────────────────────────────────────────
load_dotenv()

logger = setup_logging()

# ── ANSI colour helpers (graceful fallback on Windows) ────────────────────────
_USE_COLOR = sys.stdout.isatty()


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def green(t: str) -> str:  return _c(t, "32")
def red(t: str) -> str:    return _c(t, "31")
def cyan(t: str) -> str:   return _c(t, "36")
def yellow(t: str) -> str: return _c(t, "33")
def bold(t: str) -> str:   return _c(t, "1")


# ── CLI argument parser ───────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            +--------------------------------------------------+
            |   Binance Futures Testnet -- Trading Bot CLI     |
            +--------------------------------------------------+
            Place MARKET, LIMIT, or STOP_MARKET orders on the
            Binance Futures Testnet (USDT-M perpetual contracts).
            """
        ),
        epilog=textwrap.dedent(
            """\
            examples:
              # Market buy 0.01 BTC
              python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

              # Limit sell 0.1 ETH at $3 000
              python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3000

              # Stop-market sell 0.01 BTC if price drops to $58 000
              python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 58000
            """
        ),
    )

    # ── Core order arguments ─────────────────────────────────────────────────
    order_group = parser.add_argument_group("order parameters")
    order_group.add_argument(
        "--symbol", "-s",
        required=True,
        metavar="SYMBOL",
        help="Trading pair symbol, e.g. BTCUSDT, ETHUSDT",
    )
    order_group.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        metavar="SIDE",
        help="Order side: BUY or SELL",
    )
    order_group.add_argument(
        "--type", "-t",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "market", "limit"],
        metavar="TYPE",
        help="Order type: MARKET | LIMIT  (STOP_MARKET requires Algo API, unavailable on testnet)",
    )
    order_group.add_argument(
        "--quantity", "-q",
        required=True,
        metavar="QTY",
        help="Number of contracts (e.g. 0.01 for 0.01 BTC)",
    )
    order_group.add_argument(
        "--price", "-p",
        default=None,
        metavar="PRICE",
        help="Limit price — required for LIMIT orders",
    )
    order_group.add_argument(
        "--stop-price",
        default=None,
        metavar="STOP_PRICE",
        help="Stop trigger price — required for STOP_MARKET orders",
    )

    # ── Auth overrides (optional; fall back to env vars) ─────────────────────
    auth_group = parser.add_argument_group("authentication (overrides .env / environment)")
    auth_group.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help="Binance Testnet API key (default: BINANCE_API_KEY env var)",
    )
    auth_group.add_argument(
        "--api-secret",
        default=None,
        metavar="SECRET",
        help="Binance Testnet API secret (default: BINANCE_API_SECRET env var)",
    )

    return parser


# ── Pretty printing helpers ───────────────────────────────────────────────────

def _print_banner() -> None:
    print()
    print(bold(cyan("+--------------------------------------------------+")))
    print(bold(cyan("|       Binance Futures Testnet -- Trading Bot     |")))
    print(bold(cyan("+--------------------------------------------------+")))
    print()


def _print_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None,
    stop_price: float | None,
) -> None:
    print(bold("📋 Order Request Summary"))
    print("  " + "─" * 42)
    print(f"  Symbol    : {bold(symbol)}")
    print(f"  Side      : {(green if side == 'BUY' else red)(bold(side))}")
    print(f"  Type      : {bold(order_type)}")
    print(f"  Quantity  : {bold(str(quantity))}")
    if price is not None:
        print(f"  Price     : {bold(str(price))}")
    if stop_price is not None:
        print(f"  Stop Price: {bold(str(stop_price))}")
    print("  " + "─" * 42)
    print()


def _print_order_response(result: dict) -> None:
    print(bold("✅ Order Response Details"))
    print("  " + "─" * 42)
    fields = [
        ("Order ID",     "orderId"),
        ("Symbol",       "symbol"),
        ("Side",         "side"),
        ("Type",         "type"),
        ("Status",       "status"),
        ("Orig Qty",     "origQty"),
        ("Executed Qty", "executedQty"),
        ("Avg Price",    "avgPrice"),
        ("Price",        "price"),
        ("Stop Price",   "stopPrice"),
        ("Time In Force","timeInForce"),
    ]
    for label, key in fields:
        value = result.get(key)
        if value not in (None, "", "0", "0.00000000", "0.000"):
            print(f"  {label:<14}: {bold(str(value))}")
    print("  " + "─" * 42)


# ── Main entry point ──────────────────────────────────────────────────────────

def main() -> int:
    """Run the CLI. Returns 0 on success, 1 on error."""
    parser = build_parser()
    args = parser.parse_args()

    _print_banner()

    # ── Resolve API credentials ───────────────────────────────────────────────
    api_key = args.api_key or os.getenv("BINANCE_TESTNET_API_KEY", "")
    api_secret = args.api_secret or os.getenv("BINANCE_TESTNET_API_SECRET", "")

    if not api_key or not api_secret:
        print(
            red(
                "✖  API key or secret is missing.\n"
                "   Set BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET in your .env file\n"
                "   or pass --api-key / --api-secret on the command line."
            )
        )
        logger.error("Missing API credentials — aborting.")
        return 1

    # ── Validate inputs ───────────────────────────────────────────────────────
    try:
        symbol     = validate_symbol(args.symbol)
        side       = validate_side(args.side)
        order_type = validate_order_type(args.order_type)
        quantity   = validate_quantity(args.quantity)
        price      = validate_price(args.price, order_type)
        stop_price = validate_stop_price(args.stop_price, order_type)
    except ValidationError as exc:
        print(red(f"✖  Validation error: {exc}"))
        logger.error("Validation error: %s", exc)
        return 1

    # ── Print order summary ───────────────────────────────────────────────────
    _print_order_request(symbol, side, order_type, quantity, price, stop_price)

    # ── Execute order ─────────────────────────────────────────────────────────
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        result = place_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except BinanceAPIError as exc:
        print(red(f"\n✖  Binance API Error [{exc.code}]: {exc.message}"))
        logger.error("Binance API Error: %s", exc)
        return 1
    except Exception as exc:
        print(red(f"\n✖  Unexpected error: {exc}"))
        logger.exception("Unexpected error during order placement")
        return 1

    # ── Print response ────────────────────────────────────────────────────────
    _print_order_response(result)
    print()
    print(green("✔  Order placed successfully on Binance Futures Testnet!"))
    print(yellow(f"   Log file: logs/trading_bot.log"))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
