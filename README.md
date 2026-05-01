# Binance Futures Testnet — Trading Bot

A clean, production-style Python CLI that places **MARKET**, **LIMIT**, and **STOP_MARKET** orders on the [Binance Futures Testnet](https://testnet.binancefuture.com) (USDT-M perpetual contracts).

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py         # Package marker
│   ├── client.py           # Binance REST client (signing, HTTP, error handling)
│   ├── orders.py           # Order placement logic & response formatting
│   ├── validators.py       # Input validation (symbol, side, qty, price …)
│   └── logging_config.py   # Structured logging → console + rotating log file
├── logs/                   # Auto-created; holds trading_bot.log
├── cli.py                  # CLI entry point (argparse)
├── .env.example            # Template for API credentials
├── requirements.txt
└── README.md
```

---

## Setup

### 1 — Get a Binance Futures Testnet Account

1. Visit <https://testnet.binancefuture.com>
2. Register / log in with your GitHub account.
3. Generate API credentials: **API Management → Create API Key**.

### 2 — Clone / Download the Project

```bash
git clone https://github.com/<your-username>/trading-bot.git
cd trading-bot/trading_bot
```

### 3 — Create a Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

### 5 — Configure Credentials

```bash
cp .env.example .env
```

Open `.env` and fill in your testnet API key and secret:

```dotenv
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

> **Never** commit your real `.env` file to version control.

---

## How to Run

All commands are run from inside the `trading_bot/` directory.

### Market Order

```bash
# BUY 0.01 BTC at market price
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# SELL 0.05 ETH at market price
python cli.py --symbol ETHUSDT --side SELL --type MARKET --quantity 0.05
```

### Limit Order

```bash
# BUY 0.01 BTC with a limit price of $60,000
python cli.py --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01 --price 60000

# SELL 0.1 ETH with a limit price of $3,000
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3000
```

### Stop-Market Order *(Bonus)*

```bash
# SELL 0.01 BTC if price drops to $58,000
python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 58000
```

### Override Credentials on the CLI

```bash
python cli.py \
  --api-key  YOUR_KEY \
  --api-secret YOUR_SECRET \
  --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Get Help

```bash
python cli.py --help
```

---

## Example Output

```
╔══════════════════════════════════════════════════╗
║       Binance Futures Testnet — Trading Bot      ║
╚══════════════════════════════════════════════════╝

📋 Order Request Summary
  ──────────────────────────────────────────
  Symbol    : BTCUSDT
  Side      : BUY
  Type      : MARKET
  Quantity  : 0.01
  ──────────────────────────────────────────

✅ Order Response Details
  ──────────────────────────────────────────
  Order ID      : 3492847562
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Status        : FILLED
  Orig Qty      : 0.01000000
  Executed Qty  : 0.01000000
  Avg Price     : 62341.50000
  ──────────────────────────────────────────

✔  Order placed successfully on Binance Futures Testnet!
   Log file: logs/trading_bot.log
```

---

## Logging

Logs are written to **`logs/trading_bot.log`** (auto-created).

- **File** — DEBUG level: full request/response bodies, timestamps, order details.
- **Console** — INFO level: key events only (placing order, success, errors).

Log rotation: max **5 MB** per file, **3** backups kept.

---

## Supported Symbols

| Symbol    | Description          |
|-----------|----------------------|
| BTCUSDT   | Bitcoin / USDT       |
| ETHUSDT   | Ethereum / USDT      |
| BNBUSDT   | BNB / USDT           |
| SOLUSDT   | Solana / USDT        |
| XRPUSDT   | XRP / USDT           |
| DOGEUSDT  | Dogecoin / USDT      |
| ADAUSDT   | Cardano / USDT       |
| LTCUSDT   | Litecoin / USDT      |

---

## Assumptions & Design Decisions

- **Testnet only** — the base URL is hard-coded to `https://testnet.binancefuture.com`. No real funds are at risk.
- **Direct REST calls** — uses `requests` directly (no `python-binance` dependency) for transparency and minimal dependencies.
- **Quantity precision** — the bot passes the quantity as-is. Binance testnet is lenient; a production bot would query `exchangeInfo` to enforce `stepSize`.
- **TimeInForce** — LIMIT orders default to `GTC` (Good-Till-Cancelled).
- **STOP_MARKET** (bonus) — implements a basic stop-market order as the third order type.
- **Credentials** — resolved in priority order: CLI flags → `.env` file → environment variables.

---

## Requirements

- Python 3.9+
- See `requirements.txt`

```
requests>=2.31.0
python-dotenv>=1.0.0
```

---

## License

MIT — free to use and modify.
