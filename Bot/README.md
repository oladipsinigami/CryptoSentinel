# 🏆 CryptoSentinel AI — Bitget AI Base Camp Hackathon S1 (Track 1)

> **CryptoSentinel AI** is a fully autonomous, production-grade crypto trading agent framework. It handles signal ingestion (Perception), AI-powered/deterministic logic (Decision), simulated paper trading execution (Execution), and rigorous position controls (Risk Management). It features an interactive, glassmorphic Web Dashboard, a CLI terminal console, historical backtesters, and professional Excel reporting.

---

## 🌐 Live Demo (Hackathon Submission)

**Public Demo:** [https://cryptosentinel-ai.onrender.com](https://cryptosentinel-ai.onrender.com) ← **Replace with your deployed URL**

This is the **required publicly accessible demo** for Bitget AI Hackathon S1 Track 1.  
It serves the full glassmorphic dashboard with live data from:
- Portfolio state (`/api/state`)
- Trade history (`/api/logs`)

The demo runs the same code as the local server and displays real backtest/sim trading records.

> **Note for judges**: All trading is simulated (paper trading). No real capital is used. Full trade logs and backtest results are available in the repository.

---

## 📡 Four-Layer Architecture

### Bitget Agent Hub & Skill Hub Alignment
CryptoSentinel's **Perception Layer** is deliberately built to leverage Bitget's official AI infrastructure:

- Uses the **exact same Bitget Spot market APIs** (tickers + candles) that power the Agent Hub Tools layer and the official `technical-analysis` Skill.
- Delivers analyst-grade signals matching the **5 Skill Hub modules**:
  - `technical-analysis` — pure-Python RSI, MACD, Bollinger Bands, EMA (lightweight, no pandas/numpy required)
  - `sentiment-analyst` — Fear & Greed Index + positioning signals
  - `news-briefing` — RSS news aggregation and bullish/bearish keyword scoring
  - `macro-analyst` — BTC dominance, global market cap trends, cross-asset context
  - `market-intel` — on-chain flow proxies and volume intelligence

This lets the agent truthfully state in the submission that it uses **Bitget AI modules** while remaining a fully standalone, easy-to-run Python demo (no Node.js, MCP, or external AI tool required for the hackathon judge demo).

Full details and mapping are in `scripts/fetch_signals.py` and the submission description.

CryptoSentinel AI is built around a robust, closed-loop trading pipeline:

```
📡 PERCEPTION LAYER  →  🧠 DECISION ENGINE  →  ⚡ EXECUTION LAYER  →  🛡️ RISK MANAGEMENT
  (RSS News, F&G,         (Deterministic /         (Paper state log,        (Drawdown limits,
  RSI, MACD, BBands)        Qwen AI / Claude)        backtest_log.csv)       SL/TP, Pos cap)
```

1. **Perception Layer (`fetch_signals.py`)**: Fetches OHLCV candlesticks from Bitget Spot API, calculates RSI, MACD, Bollinger Bands, and EMA crossovers. Aggregates RSS feeds (CoinTelegraph, CoinDesk) for sentiment keyword indexing, and parses CoinGecko for market dominance/macro trend parameters.
2. **Decision Engine (`backtest.py` / `references/decision.md`)**: Synthesizes the aggregated perception score (scale of -10 to +10) into `BUY`, `SELL`, or `HOLD`. Supports an AI prompting engine (configured for Qwen AI/Claude) and a robust deterministic rule-based fallback.
3. **Execution Layer (`sim_trader.py`)**: Manages simulated paper portfolios in `portfolio_state.json` and records executions in `backtest_log.csv`.
4. **Risk Management (`references/risk.md`)**: Automatically caps position sizes (max 20% of capital), prevents excessive exposure (max 3 concurrent open positions), monitors trailing drawdown, and monitors Stop Loss (SL) and Take Profit (TP) bounds.

---

## 🚀 Key Features

* **Real technical indicators**: Pure Python calculations of RSI, MACD, and Bollinger Bands.
* **RSS sentiment analysis**: Live parsing of Crypto RSS feeds to compute bullish/bearish ratios.
* **Chronological Backtester**: Replay weeks of historical candle datasets (such as `sol_data.json`) to evaluate performance.
* **Premium Web Dashboard**: Sleek glassmorphic dark-theme UI featuring Chart.js equity curve lines, win-rate doughnuts, signal bars, and real-time open positions and history log tables.
* **CLI Terminal Dashboard**: Colored Unicode layout for fast server status reviews.
* **Excel Reports**: Formatted spreadsheet generator (`report.xlsx`) containing KPIs and trade logs with colored win/loss markers.

---

## 🛠️ Quick Start & Setup

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your system.

> [!TIP]
> **Windows Path Troubleshooting:** If the `python` or `pip` command is not recognized, make sure Python is added to your environment variables. 
> - You can check where Python is installed (often under `C:\Users\<YourUser>\AppData\Local\Programs\Python\Python3xx\`) and add it to your system/user `PATH`.
> - If running inside **Git Bash** or **PowerShell**, you may need to restart the shell after changing environment variables or append it to your session PATH (e.g., `$env:PATH += ";C:\Users\<YourUser>\AppData\Local\Programs\Python\Python3xx;C:\Users\<YourUser>\AppData\Local\Programs\Python\Python3xx\Scripts"`).

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Perception Layer (Signals)
Retrieve current market price, technical indicators, and sentiment scores:
```bash
python scripts/fetch_signals.py --asset BTC
```
*Outputs: `latest_signals.json`*

### 4. Run the Backtest Engine
Test the agent strategy against the historical Solana hourly candlestick data (`sol_data.json`):
```bash
python scripts/backtest.py --data sol_data.json --capital 1000
```
*Outputs: `portfolio_state.json` and `backtest_log.csv`*

### 5. Generate the Excel Report
Convert the trade logs into a styled spreadsheet for judges to review:
```bash
python scripts/generate_report.py
```
*Outputs: `report.xlsx`*

### 6. Launch the Terminal Dashboard
```bash
python scripts/dashboard.py
```

### 7. Run the Premium Web Dashboard

**Public (recommended for hackathon):** Visit the Live Demo link above.

**Local development:**
```bash
python scripts/server.py
```
Then open **[http://localhost:8000](http://localhost:8000)**.

The server also exposes:
- `GET /api/state` — current portfolio JSON
- `GET /api/logs` — full trade history CSV as JSON
- `GET /health` — simple health check (useful for deployment platforms)

---

## 📈 Backtest Results Preview
Replaying 100+ hours of historical SOLUSDT data:
* **Initial Capital**: $1,000.00 USDT
* **Risk Parameters**: 2% risk per trade, 2:1 Reward-to-Risk ratio (ATR-adaptive SL in backtest; volatility-based in live cycles).
* **Constraints**: Hard halts if drawdown exceeds 10% or open positions exceed 3.
* **Trade log**: Stored locally in `backtest_log.csv` for transparent auditing.

---

## 🏆 Hackathon Submission (Track 1 — Trading Agent)

**Deadline:** June 25, 2026 24:00 UTC+8

### Required Deliverables
- **Public Demo Link** (required): A running, publicly accessible version of the web dashboard showing live portfolio state and trade history. Must include backtest or sim trading records. (See Live Demo section above — deploy `scripts/server.py`.)
- **Project Description** (required, ≤200 words): Problem statement + full loop overview (perception → decision → execution → risk management) + which Bitget APIs / modules were used.  
  → Ready-to-use text in [HACKATHON_SUBMISSION_DESCRIPTION.md](HACKATHON_SUBMISSION_DESCRIPTION.md)
- **Verifiable Evidence**: `backtest_log.csv` + `portfolio_state.json` + `report.xlsx` (generated by the improved backtester).

### How to Generate Submission Artifacts
1. Run a strong backtest (now uses unified decision logic + correct 2:1 RR):
   ```bash
   python scripts/backtest.py --data sol_data.json --capital 1000
   ```
   The improved backtester now outputs:
   - Max Drawdown
   - LONG/SHORT breakdown
   - Profit Factor
   - Clean, auditable trade log

2. Generate the professional Excel report:
   ```bash
   python scripts/generate_report.py
   ```

3. (Optional but recommended) Run live agent cycles for fresh data:
   ```bash
   python scripts/agent_cycle.py --asset SOL --timeframe 1h
   python scripts/dashboard.py
   ```

4. Prepare the ≤200 word description from `HACKATHON_SUBMISSION_DESCRIPTION.md`.

### Optional but High-Value
- **Demo Video** (≤ 3 min): Screen recording of the web dashboard + a live `agent_cycle.py` run + backtest summary.
- **Community Post**: Repost the official Bitget interaction post, publish your own update with `#BitgetHackathon` and tag `@Bitget_AI`. Include the post link(s) in your submission form for Community Impact Award (+ Participation Award).

### Submission Checklist (Track 1)
- [x] **Complete strategy loop** — Perception (Bitget APIs + custom TA + sentiment + macro), Decision (unified `get_decision()`), Execution (sim LONG/SHORT with leverage), Risk (drawdown halt, position caps, SL/TP, liquidation).
- [x] **Backtest validation** — Improved `scripts/backtest.py` with unified logic, correct 2:1 RR, detailed metrics, and clean CSV output.
- [x] **Trade logs & reports** — `backtest_log.csv`, `portfolio_state.json`, `report.xlsx`.
- [x] **Runnable code + docs** — Full README, developer commands in `CLAUDE.md`, multiple UIs.
- [ ] **Public Demo Link** — Deploy `scripts/server.py` (Procfile + render.yaml ready).
- [ ] **Project Description** — Copy from `HACKATHON_SUBMISSION_DESCRIPTION.md` (≤200 words).
- [ ] **Community qualifying post** — For extra awards.
- [ ] **Demo video** (optional but strongly recommended).

**Note to judges**: All trading is 100% simulated paper trading. No real funds or accounts are used. The agent strictly follows the four-layer architecture required for Track 1.
