# 🚀 CryptoSentinel AI — Local Development Setup Guide

> Run the full trading bot dashboard on your own machine in under 5 minutes.

---

## Prerequisites

| Requirement | Minimum Version | Check Command |
|-------------|----------------|---------------|
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Git | Any | `git --version` |

> **Windows users**: Use **PowerShell** or **Command Prompt** — not Git Bash,
> which can have issues with the `py` launcher used internally by the bot.

---

## Step 1 — Clone or Locate the Project

If you already have the folder (e.g. `C:\Users\oladips\Downloads\Bot`), skip this step.

```bash
git clone <your-repo-url>
cd Bot
```

All commands from this point forward assume **your terminal is at the project root** —
the folder that contains `Procfile`, `requirements.txt`, and the `scripts/` directory.

---

## Step 2 — Create a Virtual Environment

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
python -m venv .venv
.venv\Scripts\activate.bat

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` at the start of your prompt when the environment is active.

---

## Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `pandas >= 2.0.0` — OHLCV data frames, strategy calculations
- `numpy >= 1.24.0` — Indicator math
- `openpyxl >= 3.1.0` — Excel report generation

> **Note**: No `flask`, `fastapi`, or `django` is required. The server uses Python's
> built-in `http.server` module — nothing extra to install for the web layer.

---

## Step 4 — Set Up Environment Variables (Optional)

Public market data (prices, candles, fear & greed) works **without any API keys**.
You only need keys if you want to pull authenticated Bitget account data.

```bash
# Copy the example file
copy .env.bitget.example .env        # Windows
cp .env.bitget.example .env          # macOS / Linux
```

Then open `.env` in any text editor and fill in your values:

```ini
# Get from: bitget.com → Settings → API Management
# Use READ-ONLY keys — the bot only simulates trades locally
BITGET_API_KEY=your_api_key_here
BITGET_SECRET_KEY=your_secret_key_here
BITGET_PASSPHRASE=your_passphrase_here
```

> **Safe to skip**: If you leave the `.env` empty, all live signal features still work
> using the public Bitget v2 API. Only authenticated endpoints (account info, real orders)
> require keys — and those are never used in simulation mode.

---

## Step 5 — Launch the Dashboard Server

```bash
python scripts/server.py
```

You should see:

```
[OK] CryptoSentinel Dashboard Server starting...
[*] Listening on http://0.0.0.0:8000
[*] Workspace: C:\Users\oladips\Downloads\Bot
[*] Serving web assets from: C:\Users\oladips\Downloads\Bot\web
[*] Endpoints: /  |  /api/state  |  /api/logs  |  /api/nl (POST)  |  /health
[*] NEW: Full AI natural language interface is now available directly on the website!
```

Open your browser and go to:

```
http://localhost:8000
```

---

## Available Endpoints

| URL | Method | Description |
|-----|--------|-------------|
| `http://localhost:8000/` | GET | Main dashboard UI |
| `http://localhost:8000/health` | GET | Health check — returns `OK` |
| `http://localhost:8000/api/state` | GET | Portfolio state JSON |
| `http://localhost:8000/api/logs` | GET | Backtest trade log (CSV → JSON) |
| `http://localhost:8000/api/scan` | GET | Latest market scan results |
| `http://localhost:8000/api/signals?symbol=BTCUSDT` | GET | Live signal for a symbol |
| `http://localhost:8000/api/nl` | POST | Natural language command interface |

### Example: Query the NL Interface with curl

```bash
# Get a live signal for BTC
curl -X POST http://localhost:8000/api/nl \
     -H "Content-Type: application/json" \
     -d "{\"command\": \"give me a signal on BTC\"}"

# Check portfolio status
curl -X POST http://localhost:8000/api/nl \
     -H "Content-Type: application/json" \
     -d "{\"command\": \"show my portfolio\"}"

# Execute a paper trade
curl -X POST http://localhost:8000/api/nl \
     -H "Content-Type: application/json" \
     -d "{\"command\": \"long ETH 100 3x\"}"
```

---

## Optional: Run the Auto-Trader Daemon

To run the trading agent on a recurring schedule (every N seconds), open a
**second terminal** while the dashboard server is running:

```bash
# Run every 60 seconds on BTC (default)
python scripts/auto_runner.py

# Run every 5 minutes on BTC + ETH + SOL
python scripts/auto_runner.py --asset BTC,ETH,SOL --interval 300 --timeframe 1h

# Run exactly 10 cycles then stop
python scripts/auto_runner.py --asset BTC --iterations 10
```

Logs are written to `auto_runner.log` in the project root.

---

## Optional: Run a Backtest

```bash
python scripts/backtest.py
```

After the backtest completes, generate the Excel report:

```bash
python scripts/generate_report.py
```

Output is saved to `report.xlsx` in the project root.

---

## Optional: Fetch Fresh Market Data

```bash
# Fetch latest BTC 7-day candle data
python scripts/fetch_btc_data.py

# Run a full market scan (all symbols)
python scripts/fetch_signals.py
```

---

## Changing the Port

The default port is **8000**. To use a different port, set the `PORT` environment
variable before starting the server:

```bash
# Windows PowerShell
$env:PORT = "8080"
python scripts/server.py

# Windows Command Prompt
set PORT=8080
python scripts/server.py

# macOS / Linux
PORT=8080 python scripts/server.py
```

Then open: `http://localhost:8080`

---

## Troubleshooting

### ❌ `ModuleNotFoundError: No module named 'pandas'`
You are not inside the virtual environment, or `pip install` was not run.
```bash
# Activate the venv first:
.venv\Scripts\Activate.ps1       # Windows
source .venv/bin/activate        # macOS/Linux

# Then install:
pip install -r requirements.txt
```

### ❌ `NameError: name 'Optional' is not defined`
This was a known bug — already fixed. Make sure you have the latest code with the
`from typing import Optional` import in `utils/symbol_registry.py`.

### ❌ `Address already in use` / Port 8000 in use
Another process is using port 8000. Either stop it or use a different port:
```bash
# Find what's using port 8000 (Windows)
netstat -ano | findstr :8000

# Kill it (replace PID with the number shown above)
taskkill /PID <PID> /F

# Or simply use a different port
$env:PORT = "8081"; python scripts/server.py
```

### ❌ Dashboard loads but signals return errors
The Bitget public API may be temporarily unreachable. The bot has a full fallback chain:
1. Live Bitget API
2. In-memory price cache (60-second TTL)
3. Hard-coded fallback prices (BTC, ETH, SOL only)

Wait 30 seconds and try again, or check your internet connection.

### ❌ `py: command not found` (Git Bash on Windows)
Switch to PowerShell or Command Prompt. The bot's internal subprocess launcher
detects your Python executable automatically, but Git Bash can have PATH conflicts.

---

## Project Structure (Quick Reference)

```
Bot/
├── scripts/
│   ├── server.py           ← Main entry point — dashboard + API
│   ├── fetch_signals.py    ← Live market data & signal computation
│   ├── strategy_framework.py ← 24-strategy engine + regime detection
│   ├── sim_trader.py       ← Paper trading simulation
│   ├── agent_cycle.py      ← Autonomous trade cycle
│   ├── auto_runner.py      ← Daemon scheduler
│   ├── backtest.py         ← Backtesting engine
│   └── generate_report.py  ← Excel report generator
├── utils/
│   ├── price_validator.py  ← Price sanity checks + floor limits
│   ├── price_fallback.py   ← Fallback price chain
│   ├── price_cache_manager.py ← In-memory price cache (thread-safe)
│   ├── symbol_registry.py  ← Dynamic Bitget symbol list + normalizer
│   ├── fallback_signal.py  ← Minimal signal payload for API failures
│   └── error_handler.py    ← Decorator + context manager for errors
├── web/                    ← Static dashboard frontend (HTML/CSS/JS)
├── requirements.txt        ← Python dependencies
├── Procfile                ← Render/Heroku launch command
├── render.yaml             ← Render deployment config
└── .env.bitget.example     ← API key template
```

---

## Quick-Start Cheatsheet

```bash
# 1. Activate environment
.venv\Scripts\Activate.ps1

# 2. Install deps (first time only)
pip install -r requirements.txt

# 3. Launch dashboard
python scripts/server.py

# 4. Open browser
start http://localhost:8000

# 5. Stop server
Ctrl+C
```
