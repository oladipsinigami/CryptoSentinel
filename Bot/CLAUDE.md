# CryptoSentinel AI — Developer Guide

This is the workspace for the Bitget AI Hackathon S1 trading agent project (Track 1).

## Developer Commands

### Setup
* Install Python dependencies: `pip install -r requirements.txt`

### Execution
**Important for Windows users (Git Bash, WSL, VSCode terminals, etc.):**
`py` (the Windows launcher) is **not** available in every shell. Use `python` or `python3` instead:

* Fetch current market signals: `python scripts/fetch_signals.py`
* Run simulated backtest: `python scripts/backtest.py`
* Render CLI Dashboard: `python scripts/dashboard.py`
* Generate Excel Report: `python scripts/generate_report.py`
* **Run the Web Dashboard (recommended way to use the AI now):**  
  `python scripts/server.py`  
  Then open http://localhost:8000 in your browser.  
  Scroll to the **"Command the AI Agent"** box at the bottom — this is the full natural language interface (no terminal needed anymore).  
  Example: type `analyze the market and take trade where it's most profitable based on your strategy`

* New backend endpoint (used by the web UI): `POST /api/nl` with JSON body `{ "command": "your instruction here" }`

All scripts now use a robust launcher that prefers `sys.executable` + falls back gracefully, so you should no longer see "py: command not found".

### Trading Operations
* Execute simulated Buy/Sell paper trades:
  `python scripts/sim_trader.py trade --action BUY --asset BTC --amount_usdt 100 --entry_price 60000 --stop_loss 58500 --take_profit 63000`
* Check simulation portfolio status:
  `python scripts/sim_trader.py status`
* Check SL/TP triggers for positions:
  `python scripts/sim_trader.py update --asset BTC --current_price 63500`

---
*Deadline: June 25, 2026 at 24:00 UTC+8*

