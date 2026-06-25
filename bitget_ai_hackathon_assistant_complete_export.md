# Bitget AI Hackathon Assistant - Complete Project Export

## 1. Project Overview
CryptoSentinel AI is a fully autonomous, production-grade cryptocurrency trading agent framework designed for Track 1 (Trading Agent) of the Bitget AI Base Camp Hackathon S1. It implements a complete closed-loop trading architecture:
1. **Perception**: Dynamic ingestion of real-time market data (USDT spot pairs) directly from the Bitget API, technical indicator calculations, RSS feed keyword sentiment analysis, Fear & Greed index values, and macro parameters.
2. **Decision**: A unified intelligence engine that synthesizes inputs into actionable signals (`BUY`, `SELL`, or `HOLD`) using technical filters and market regime recognition. It leverages a multi-strategy framework (24 quantitative strategies across 7 categories).
3. **Execution**: Simulated paper-trading accounts that track entry, exits, fees, and leverage (LONG/SHORT) without utilizing real capital.
4. **Risk Management**: Rigorous automated controls including position size caps (max 20% of capital), limit of 3 concurrent positions, automatic Stop Loss (SL) and Take Profit (TP) bounds, and a 10% maximum trailing drawdown halt.

### Current Status
- **Working**:
  - Live technical signal fetching and multi-coin scanning (`--scan`) from Bitget Spot APIs.
  - Multi-Strategy Intelligence Layer featuring 24 strategies (Trend, Momentum, Mean Reversion, Breakouts, Volatility, Volume, Smart Money Concepts) and a Market Regime Detector.
  - Paper trading execution engine with realistic fees (0.05% per side) and futures-style leverage (default 3x) in `sim_trader.py`.
  - Chronological backtester (`backtest.py`) with 2:1 RR and performance tracking for individual strategies.
  - Premium glassmorphic Web UI dashboard (`server.py` + Chart.js frontend) and CLI terminal view (`dashboard.py`).
  - Interactive Natural Language REPL chat (`natural_language_interface.py`) for typing instructions.
  - Full alignment client (`bitget_skill_hub_client.py`) connecting to the official Bitget MCP server at `https://datahub.noxiaohao.com/mcp`.
  - Excel KPI reporting (`generate_report.py`).
- **In Progress / Aspirational**:
  - Exposing the AI's Qwen/Claude decision-making layer with real LLM credentials (runs on rule-based fallbacks locally if API keys are missing).
  - Production deployment (configured for Render via `render.yaml` and `Procfile`).

---

## 2. Tech Stack
- **Frontend**: Single-Page Application (SPA) using React 18, Tailwind CSS, Framer Motion, p5.js, and Chart.js (via CDN loaders in `index.html` for clean, zero-config distribution).
- **Backend/Server**: Python 3.8+ built-in `http.server` hosting a REST API and serving static web assets. Supports concurrent ThreadPool execution for low-latency parallel requests.
- **LLM/Models**: Designed to interface with Alibaba Cloud Qwen (for reasoning/playbook strategy generation) or Claude. Includes standard rule-based fallbacks for offline reliability.
- **Key Python Libraries**: `pandas`, `numpy`, `openpyxl` (for Excel reports), `urllib` (no external `requests` or `aiohttp` required for zero-install compliance).
- **Bitget API Integration**:
  - Direct REST queries to Bitget Spot Tickers & Candles (`spot/market/tickers`, `spot/market/candles`).
  - MCP Client (`bitget_skill_hub_client.py`) connecting via SSE (Server-Sent Events) to the official Bitget Skill Hub server (`https://datahub.noxiaohao.com/mcp`) supporting tools: `sentiment_index`, `derivatives_sentiment`, `crypto_market`, `news_feed`, and `tradfi_news`.
  - CLI automation wrapper (`bgc` via `npx bitget-client`) support.

---

## 3. Project Structure
```
Bot/
├── .env.bitget.example
├── .gitignore
├── BITGET_MCP_SKILLS_SETUP.md
├── BUG_REPORT.md
├── CLAUDE.md
├── CRYPTO_SENTINEL_AI_DEVELOPER_TECHNICAL_REPORT.md
├── CRYPTO_SENTINEL_AI_DEVELOPMENT_REPORT.md
├── HACKATHON_PROJECT_HISTORY_AND_PROGRESS.md
├── HACKATHON_SUBMISSION_DESCRIPTION.md
├── Procfile
├── README.md
├── requirements.txt
├── render.yaml
├── backtest_log.csv
├── portfolio_state.json
├── market_scan.json
├── latest_signals.json
├── scripts/
│   ├── agent_cycle.py
│   ├── auto_runner.py
│   ├── backtest.py
│   ├── bitget_hub_alignment.py
│   ├── bitget_skill_hub_client.py
│   ├── dashboard.py
│   ├── fetch_btc_data.py
│   ├── fetch_signals.py
│   ├── generate_report.py
│   ├── generate_test_data.py
│   ├── kline_indicators.py
│   ├── kline_indicator_utils.py
│   ├── mcp_client.py
│   ├── natural_language_interface.py
│   ├── server.py
│   ├── sim_trader.py
│   └── strategy_framework.py
├── utils/
│   ├── __init__.py
│   ├── bad_words.py
│   ├── cleanup_report_generator.py
│   ├── demo_watchdog.py
│   ├── error_handler.py
│   ├── fallback_signal.py
│   ├── price_cache_manager.py
│   ├── price_fallback.py
│   ├── price_validator.py
│   ├── symbol_cache.json
│   ├── symbol_extraction_logger.py
│   └── symbol_registry.py
└── web/
    ├── index.html
    ├── style.css
    └── components/
        ├── App.js
        ├── ArtGenerator.js
        ├── BlurText.js
        ├── Capabilities.js
        ├── Dashboard.js
        ├── FadingVideo.js
        ├── Hero.js
        └── Navbar.js
```

---

## 4. Core Features Implemented
### A. Scalp Trading Signal Generation (`fetch_signals.py`)
Fetches OHLCV candle streams from Bitget. Computes pure-Python RSI, MACD, Bollinger Bands, and EMA crossovers. Merges these technicals with RSS news scoring, global Fear & Greed values, and derivatives sentiment indicators (Long/Short ratios, taker volume bias) fetched via the Bitget MCP. Operates in two modes: single-asset and multi-coin `--scan`. The scanner dynamically filters out stock-pegged tokens and leveraged tokens, selecting top crypto pairs based on volume and ranking them by conviction.

### B. Multi-Strategy Intelligence (`strategy_framework.py`)
Features 24 strategies across 7 categories:
1. **Trend Following**: EMA Cross, SMA Cross, Supertrend, ADX Trend.
2. **Momentum**: MACD, RSI, Stochastic, Rate of Change (ROC).
3. **Mean Reversion**: Bollinger Band Reversion, RSI Reversion, Z-Score Reversion.
4. **Breakout**: Donchian Channels, ATR Breakout, Range Consolidation Breakout.
5. **Volatility**: Bollinger Squeeze, ATR Volatility expansion, Keltner Channel Break.
6. **Volume**: OBV Trend, Chaikin Money Flow, Volume Spread Analysis (VSA).
7. **Smart Money Concepts**: Order Blocks, Fair Value Gaps (FVG), BOS & CHOCH setups.

An internal `MarketRegimeDetector` categorizes conditions (Bullish Trend, Bearish Trend, Ranging, High Volatility, Accumulation/Distribution) and weights strategies accordingly. A performance feedback loop dynamically adjusts individual strategy weights based on historical win rates.

### C. Signal Reasoning & Explanation
When generating decisions, the bot output is packed with clear, mathematical, and fundamental bullet-points:
- Current price, 24h change, and volume.
- Active strategy triggering (e.g., `"Order Blocks Reversal"`) with specific setup details.
- Technical parameters (exact RSI value, MACD histogram size, EMA orientation).
- Sentiment indices (Fear & Greed score and RSS bullish/bearish ratio).
- On-chain metrics (net flow, L/S ratio).

### D. Simulated Execution & Risk Control (`sim_trader.py`)
Manages the virtual account. Deducts transaction fees (0.05%) upon entries and exits. Supports futures leverage (e.g. 3x) and tracks liquidation parameters. Implements Stop Loss and Take Profit targets based on ATR-adjusted distance (2:1 reward-to-risk ratio). Employs position reversals (e.g., if shorting and a bullish signal fires, it immediately flattens the short and entries a long). Implements global safety checks (maximum 3 positions, 20% max allocation per trade, 10% max drawdown circuit breaker).

### E. Interactive Natural Language REPL (`natural_language_interface.py`)
Exposes a text prompt for chat-based interactions. The REPL parses English requests using regex keyword extraction and runs the corresponding Python logic. Phrases like `"analyze the market and trade where it's most profitable"` trigger the scanner, select top conviction pairs, apply risk calculations, and call the execution script, printing out the portfolio state update instantly.

---

## 5. Key Code Files

### A. Main Agent Logic: `scripts/agent_cycle.py`
This orchestrates the unified strategy execution cycle: fetches data, evaluates signals/regimes, updates SL/TP, resolves position reversals, applies risk checks, triggers executions, and updates the CLI dashboard.

```python
# [FULL CODE OF scripts/agent_cycle.py]
# File path: scripts/agent_cycle.py
```
*(Due to request size constraints, the complete code of this file is presented below in full)*

```python
#!/usr/bin/env python3
"""
Agent Cycle Automation Script — CryptoSentinel AI Trading Agent
Executes a full perception → decision → execution → risk management cycle.
"""

import argparse
import json
import os
import sys
import subprocess

try:
    if sys.platform.startswith('win'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def load_dotenv_if_exists(filepath=".env"):
    """Very simple .env loader (no external deps). Only for local testing."""
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass

load_dotenv_if_exists()  # Load .env for Bitget keys during local testing (safe because of .gitignore)

# Project root for consistent file paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if not os.path.isdir(os.path.join(ROOT_DIR, "web")):
    ROOT_DIR = os.getcwd()

STATE_FILE = os.path.join(ROOT_DIR, "portfolio_state.json")
SIGNALS_FILE = os.path.join(ROOT_DIR, "latest_signals.json")
SCAN_FILE = os.path.join(ROOT_DIR, "market_scan.json")

def load_portfolio():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "balance": 1000.0,
        "peak_balance": 1000.0,
        "open_positions": [],
        "total_trades": 0,
        "winning_trades": 0,
        "realized_pnl": 0.0
    }

def get_sl_pct(asset, change_24h_pct):
    abs_change = abs(change_24h_pct)
    asset_upper = asset.upper()
    
    if "BTC" in asset_upper:
        if abs_change < 2.0:
            return 0.015  # 1.5%
        elif abs_change <= 5.0:
            return 0.020  # 2.0%
        else:
            return 0.030  # 3.0%
    elif "ETH" in asset_upper:
        if abs_change < 2.0:
            return 0.020  # 2.0%
        elif abs_change <= 5.0:
            return 0.025  # 2.5%
        else:
            return 0.040  # 4.0%
    else:  # Alts
        if abs_change < 2.0:
            return 0.030  # 3.0%
        elif abs_change <= 5.0:
            return 0.040  # 4.0%
        else:
            return 0.060  # 6.0%

def run_cmd(args):
    """Robust python launcher that works in PowerShell, CMD, Git Bash, WSL, etc.
    Prefers the current interpreter, then tries common names.
    """
    if sys.executable and os.path.isfile(sys.executable):
        candidates = [sys.executable]
    else:
        candidates = []

    if sys.platform.startswith("win"):
        candidates += ["py", "python", "python3"]
    else:
        candidates += ["python3", "python"]

    for python_cmd in candidates:
        try:
            full_args = [python_cmd] + args
            result = subprocess.run(full_args, capture_output=True, text=True, encoding="utf-8", cwd=ROOT_DIR)
            return result
        except FileNotFoundError:
            continue
        except Exception:
            pass

    full_args = ["python"] + args
    return subprocess.run(full_args, capture_output=True, text=True, encoding="utf-8", cwd=ROOT_DIR)

def main():
    parser = argparse.ArgumentParser(description="Run Full Agent Cycle")
    parser.add_argument("--asset", default="BTC", help="Asset symbol (BTC, ETH, SOL) - ignored if --scan")
    parser.add_argument("--timeframe", default="1h", choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d"], help="Timeframe / candle granularity")
    parser.add_argument("--scan", action="store_true", help="Scan many coins via fetch_signals --scan, rank by |score|, auto-trade the most profitable (highest conviction) up to risk limits. This lets the bot analyze dozens of coins and pick the best.")
    parser.add_argument("--leverage", type=int, default=3, help="Leverage for sim trading")
    args = parser.parse_args()

    if args.scan:
        print("====================================================")
        print("🚀 RUNNING AUTONOMOUS MULTI-COIN SCAN & TRADE CYCLE")
        print("====================================================\n")
        print("[1/4] Scanning market for best opportunities (analyzing many coins)...")
        res = run_cmd(["scripts/fetch_signals.py", "--scan"])
        if res.returncode != 0:
            print(f"❌ Scan failed:\n{res.stderr}")
            sys.exit(1)
        if not os.path.exists(SCAN_FILE):
            print("❌ market_scan.json not created.")
            sys.exit(1)
        with open(SCAN_FILE) as f:
            scan = json.load(f)
        if not scan:
            print("ℹ️ No strong opportunities found in scan.")
            return
        ranked = sorted(scan, key=lambda x: abs(x["aggregate_score"]), reverse=True)
        print(f"✅ Scanned. Top conviction: {ranked[0]['symbol']} score={ranked[0]['aggregate_score']:+.2f} ({ranked[0]['decision']})")
        print("\n[2/4] Updating any open positions...")
        for cand in ranked[:5]:
            sym = cand["symbol"].replace("USDT","")
            res = run_cmd(["scripts/sim_trader.py", "update", "--asset", sym, "--current_price", str(cand["price"])])
            if res.returncode == 0 and res.stdout.strip():
                print(res.stdout.strip())
        portfolio = load_portfolio()
        print("\n[3/4] Selecting and trading the most profitable opportunities (top by conviction, respecting risk)...")
        traded = 0
        for cand in ranked:
            if traded >= 2:
                break
            sym = cand["symbol"].replace("USDT", "")
            score = cand["aggregate_score"]
            dec = cand["decision"]
            conf = cand["confidence"]
            price = cand["price"]
            chg = cand.get("change_24h_pct", 0)
            if dec == "HOLD" or abs(score) < 1.5:
                continue
            open_for_this = [p for p in portfolio["open_positions"] if p["asset"] == sym]
            if open_for_this:
                continue
            if len(portfolio["open_positions"]) >= 3:
                print("ℹ️ Max positions reached. Skipping further selections.")
                break
            strat_intel = cand.get("strategy_intelligence", {})
            if strat_intel and strat_intel.get("strategy") and strat_intel.get("strategy") != "None":
                action = "LONG" if "BUY" in strat_intel["decision"] else "SHORT"
                sl = strat_intel["stop_loss"]
                tp = strat_intel["take_profit"]
                reasoning = f"Strategy: {strat_intel['strategy']} | {strat_intel['reasoning']}"
            else:
                action = "LONG" if score > 0 else "SHORT"
                sl_pct = get_sl_pct(sym, chg)
                if action == "LONG":
                    sl = price * (1 - sl_pct)
                    tp = price * (1 + sl_pct * 2)
                else:
                    sl = price * (1 + sl_pct)
                    tp = price * (1 - sl_pct * 2)
                reasoning = f"Multi-coin scan top pick: {dec} score {score:.2f}"
                
            size_pct = 0.12 if conf == "MEDIUM" else (0.20 if conf == "HIGH" else 0.08)
            amount = portfolio["balance"] * size_pct
            if amount < 10:
                continue
            trade_args = ["scripts/sim_trader.py", "trade",
                          "--action", action, "--asset", sym,
                          "--amount_usdt", str(round(amount,2)),
                          "--entry_price", str(price),
                          "--stop_loss", str(round(sl,2)),
                          "--take_profit", str(round(tp,2)),
                          "--leverage", str(args.leverage),
                          "--signal_score", str(score),
                          "--confidence", conf,
                          "--reasoning", reasoning]
            res = run_cmd(trade_args)
            if res.returncode == 0:
                print(res.stdout.strip())
                traded += 1
                portfolio = load_portfolio()
            else:
                print(f"⚠️ Trade failed for {sym}: {res.stderr}")
        if traded == 0:
            print("ℹ️ No new high-conviction trades selected from scan (risk filters or no strong edges).")
        print("\n[4/4] Rendering updated dashboard...")
        res = run_cmd(["scripts/dashboard.py"])
        if res.returncode == 0:
            print(res.stdout)
        return

    asset = args.asset.upper()
    symbol = f"{asset}USDT"

    print("====================================================")
    print(f"🚀 RUNNING AGENT CYCLE FOR {symbol} ({args.timeframe})")
    print("====================================================\n")

    print("[1/4] Running Perception Layer (Fetching latest signals)...")
    res = run_cmd(["scripts/fetch_signals.py", "--asset", asset, "--timeframe", args.timeframe])
    if res.returncode != 0:
        print(f"❌ Error fetching signals:\n{res.stderr}")
        sys.exit(1)
    
    if not os.path.exists(SIGNALS_FILE):
        print("❌ Error: latest_signals.json was not created.")
        sys.exit(1)
        
    with open(SIGNALS_FILE) as f:
        signals = json.load(f)
        
    current_price = float(signals["price"])
    change_24h_pct = float(signals["change_24h_pct"])
    decision = signals["decision"]
    confidence = signals["confidence"]
    score = float(signals["aggregate_score"])
    
    reasoning = (
        f"Signals score: {score:+.2f}. F&G: {signals['fear_greed']['value']} ({signals['fear_greed']['label']}). "
        f"RSI: {signals['technicals']['rsi']}, MACD Hist: {signals['technicals']['macd_hist']:+.4f}."
    )

    print(f"Base Price fetched: ${current_price:,.2f} (24h change: {change_24h_pct:+.2f}%)")

    print("\n[2/4] Checking and updating open positions for SL/TP hits...")
    res = run_cmd(["scripts/sim_trader.py", "update", "--asset", asset, "--current_price", str(current_price)])
    if res.returncode == 0:
        if res.stdout.strip():
            print(res.stdout.strip())
        else:
            print("ℹ️ No open positions hit stop-loss or take-profit.")
    else:
        print(f"⚠️ Warning updating positions: {res.stderr}")

    portfolio = load_portfolio()
    balance = portfolio["balance"]
    
    open_long_pos = [p for p in portfolio["open_positions"] if p["asset"] == asset and "LONG" in p["action"]]
    open_short_pos = [p for p in portfolio["open_positions"] if p["asset"] == asset and "SHORT" in p["action"]]

    print("\n[3/4] Running Decision Engine & Execution Layer...")
    print(f"Recommended action from signals: {decision} (Confidence: {confidence}, Score: {score:+.2f})")

    # EMA Cross conservative trend filter
    ema_cross = signals.get("technicals", {}).get("ema_cross", "neutral")
    if decision in ("BUY", "STRONG BUY") and ema_cross != "bullish":
        print("[FILTER] Trend filter: blocking LONG (price not above EMA trend)")
        decision = "HOLD"
    elif decision in ("SELL", "STRONG SELL") and ema_cross != "bearish":
        print("[FILTER] Trend filter: blocking SHORT (price not below EMA trend)")
        decision = "HOLD"

    leverage = args.leverage

    if decision in ("BUY", "STRONG BUY"):
        if open_short_pos:
            print(f"🔄 Reversal: Closing open SHORT position for {asset}...")
            close_args = [
                "scripts/sim_trader.py", "trade",
                "--action", "CLOSE_SHORT",
                "--asset", asset,
                "--amount_usdt", "0",
                "--entry_price", str(current_price),
                "--stop_loss", "0",
                "--take_profit", "0"
            ]
            res = run_cmd(close_args)
            if res.returncode == 0:
                print(res.stdout.strip())
                portfolio = load_portfolio()
                balance = portfolio["balance"]
            else:
                print(f"❌ Error closing SHORT position:\n{res.stderr}")

        if open_long_pos and not open_short_pos:
            print(f"ℹ️ Already holding open LONG position for {symbol}. Blocking new LONG trade to manage exposure.")
        else:
            strat_intel = signals.get("strategy_intelligence", {})
            if strat_intel and strat_intel.get("strategy") and strat_intel.get("strategy") != "None":
                sl_price = float(strat_intel.get("stop_loss", current_price * 0.98))
                tp_price = float(strat_intel.get("take_profit", current_price * 1.04))
                reasoning = f"Strategy: {strat_intel['strategy']} | {strat_intel['reasoning']}"
                sl_pct = abs(current_price - sl_price) / (current_price + 1e-10)
            else:
                sl_pct = get_sl_pct(asset, change_24h_pct)
                sl_price = current_price * (1.0 - sl_pct)
                tp_price = current_price * (1.0 + sl_pct * 2.0)
            
            base_size = 0.05
            strength_bonus = min(0.15, abs(score) * 0.03)
            vol_penalty = min(0.10, abs(change_24h_pct) / 100.0 * 0.5)
            size_pct = base_size + strength_bonus - vol_penalty
            
            if confidence == "HIGH":
                size_pct = max(size_pct, 0.15)
            elif confidence == "MEDIUM":
                size_pct = max(size_pct, 0.10)
            else:
                size_pct = max(size_pct, 0.05)
                
            size_pct = max(0.03, min(0.20, size_pct))
            amount_usdt = balance * size_pct
            if amount_usdt < 10.0:
                amount_usdt = 10.0
                
            print(f"⚙️ Risk settings: LONG Volatility SL pct = {sl_pct:.1%}, Reward Ratio = 2.0x, Leverage = {leverage}x")
            print(f"💸 Sizing: {size_pct:.0%} of balance (${balance:.2f} USDT) = ${amount_usdt:.2f} USDT")
            
            trade_args = [
                "scripts/sim_trader.py", "trade",
                "--action", "LONG",
                "--asset", asset,
                "--amount_usdt", str(round(amount_usdt, 2)),
                "--entry_price", str(current_price),
                "--stop_loss", str(round(sl_price, 2)),
                "--take_profit", str(round(tp_price, 2)),
                "--leverage", str(leverage),
                "--signal_score", str(score),
                "--confidence", confidence,
                "--reasoning", reasoning
            ]
            res = run_cmd(trade_args)
            if res.returncode == 0:
                print(res.stdout.strip())
            else:
                print(f"❌ Error executing LONG trade:\n{res.stderr}")

    elif decision in ("SELL", "STRONG SELL"):
        if open_long_pos:
            print(f"🔄 Reversal: Closing open LONG position for {asset}...")
            close_args = [
                "scripts/sim_trader.py", "trade",
                "--action", "CLOSE_LONG",
                "--asset", asset,
                "--amount_usdt", "0",
                "--entry_price", str(current_price),
                "--stop_loss", "0",
                "--take_profit", "0"
            ]
            res = run_cmd(close_args)
            if res.returncode == 0:
                print(res.stdout.strip())
                portfolio = load_portfolio()
                balance = portfolio["balance"]
            else:
                print(f"❌ Error closing LONG position:\n{res.stderr}")

        if open_short_pos and not open_long_pos:
            print(f"ℹ️ Already holding open SHORT position for {symbol}. Blocking new SHORT trade to manage exposure.")
        else:
            strat_intel = signals.get("strategy_intelligence", {})
            if strat_intel and strat_intel.get("strategy") and strat_intel.get("strategy") != "None":
                sl_price = float(strat_intel.get("stop_loss", current_price * 1.02))
                tp_price = float(strat_intel.get("take_profit", current_price * 0.96))
                reasoning = f"Strategy: {strat_intel['strategy']} | {strat_intel['reasoning']}"
                sl_pct = abs(sl_price - current_price) / (current_price + 1e-10)
            else:
                sl_pct = get_sl_pct(asset, change_24h_pct)
                sl_price = current_price * (1.0 + sl_pct)
                tp_price = current_price * (1.0 - sl_pct * 2.0)
            
            base_size = 0.05
            strength_bonus = min(0.15, abs(score) * 0.03)
            vol_penalty = min(0.10, abs(change_24h_pct) / 100.0 * 0.5)
            size_pct = base_size + strength_bonus - vol_penalty
            
            if confidence == "HIGH":
                size_pct = max(size_pct, 0.15)
            elif confidence == "MEDIUM":
                size_pct = max(size_pct, 0.10)
            else:
                size_pct = max(size_pct, 0.05)
                
            size_pct = max(0.03, min(0.20, size_pct))
            amount_usdt = balance * size_pct
            if amount_usdt < 10.0:
                amount_usdt = 10.0
                
            print(f"⚙️ Risk settings: SHORT Volatility SL pct = {sl_pct:.1%}, Reward Ratio = 2.0x, Leverage = {leverage}x")
            print(f"💸 Sizing: {size_pct:.0%} of balance (${balance:.2f} USDT) = ${amount_usdt:.2f} USDT")
            
            trade_args = [
                "scripts/sim_trader.py", "trade",
                "--action", "SHORT",
                "--asset", asset,
                "--amount_usdt", str(round(amount_usdt, 2)),
                "--entry_price", str(current_price),
                "--stop_loss", str(round(sl_price, 2)),
                "--take_profit", str(round(tp_price, 2)),
                "--leverage", str(leverage),
                "--signal_score", str(score),
                "--confidence", confidence,
                "--reasoning", reasoning
            ]
            res = run_cmd(trade_args)
            if res.returncode == 0:
                print(res.stdout.strip())
            else:
                print(f"❌ Error executing SHORT trade:\n{res.stderr}")

    else:
        print("🟡 Decision is HOLD. No simulated trade executed.")

    print("\n[4/4] Rendering updated dashboard...")
    res = run_cmd(["scripts/dashboard.py"])
    if res.returncode == 0:
        print(res.stdout)
    else:
        print(f"❌ Error rendering dashboard:\n{res.stderr}")

if __name__ == "__main__":
    main()
```

---

### B. Signal Generation Engine: `scripts/fetch_signals.py`
This calculates technical indicators, aggregates news/sentiment/macro data, queries the Bitget Skill Hub SSE server, and outputs the normalized perception signal.

*(Due to length constraints, the critical indicator math, multi-coin scanning filters, and integration logic are detailed below)*

```python
# Selected sections of scripts/fetch_signals.py
# File path: scripts/fetch_signals.py
```

```python
# Light weight, pure-Python technical indicator logic (no pandas/numpy dependencies)
def calculate_ema(prices, period):
    if len(prices) < period:
        return [prices[-1]] * len(prices)
    ema = []
    multiplier = 2 / (period + 1)
    sma = sum(prices[:period]) / period
    ema.append(sma)
    for i in range(period, len(prices)):
        val = (prices[i] - ema[-1]) * multiplier + ema[-1]
        ema.append(val)
    return [prices[0]] * (period - 1) + ema

def calculate_rsi(prices, period=14):
    if len(prices) <= period:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_macd(prices):
    if len(prices) < 26:
        return 0.0, 0.0, 0.0
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    signal_line = calculate_ema(macd_line, 9)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line[-1], signal_line[-1], histogram[-1]

# Crypto-only spot pair scanner
_EXCLUDED_PREFIXES = ("R",) # R-prefix tokenized stocks
_EXCLUDED_SUFFIXES = ("3LUSDT", "3SUSDT", "5LUSDT", "5SUSDT") # leveraged ETF tokens
_STABLECOIN_BASES = {"USDC", "TUSD", "DAI", "BUSD", "FDUSD", "USDP", "PYUSD"}

def is_real_crypto(symbol: str) -> bool:
    if not symbol.endswith("USDT"):
        return False
    base = symbol.replace("USDT", "")
    if not base:
        return False
    for prefix in _EXCLUDED_PREFIXES:
        if base.startswith(prefix) and len(base) > 1 and base[1:].isalpha() and base[1:].isupper():
            known_r_crypto = {"RNDR", "ROSE", "RSR", "REEF", "REQ", "RLC", "RUNE", "RVN", "RAY", "RENDER", "RON", "RPL"}
            if base not in known_r_crypto:
                return False
    for suffix in _EXCLUDED_SUFFIXES:
        if symbol.endswith(suffix):
            return False
    if base in _STABLECOIN_BASES:
        return False
    return True

def scan_market(top_n=20, min_volume_usdt=5000000):
    print(f"[*] Scanning top {top_n} high-volume USDT coins for opportunities...")
    all_tickers = get_bitget_all_tickers()
    fg = get_fear_greed()
    news = get_rss_sentiment()
    mac = get_global_macro()
    on = get_onchain_signals()
    # ... Ingests candidates, calculates indicators, selects top convictions ...
```

---

### C. Execution Engine: `scripts/sim_trader.py`
This module tracks open positions, applies entry/exit fees, performs Stop Loss/Take Profit checks, and updates the local state.

```python
# [FULL CODE OF scripts/sim_trader.py]
# File path: scripts/sim_trader.py
```

*(Due to size constraints, the core logic is provided here)*

```python
#!/usr/bin/env python3
"""
Sim Trader Script — CryptoSentinel AI Trading Agent
Executes simulated (paper) trades, manages positions, checks SL/TP hits,
and applies risk management controls. No real funds are used.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

LOG_FILE = "backtest_log.csv"
STATE_FILE = "portfolio_state.json"
INITIAL_CAPITAL = 1000.0
FEE_RATE = 0.0005  # 0.05% per side (~0.1% round-trip)

FIELDNAMES = [
    "timestamp", "asset", "action", "amount_usdt", "entry_price",
    "stop_loss", "take_profit", "signal_score", "confidence",
    "reasoning", "exit_price", "pnl_usdt", "pnl_pct", "status"
]

def load_portfolio():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
                keys = ["balance", "peak_balance", "open_positions", "total_trades", "winning_trades", "realized_pnl"]
                for k in keys:
                    if k not in state:
                        if k == "open_positions": state[k] = []
                        elif k in ("total_trades", "winning_trades"): state[k] = 0
                        else: state[k] = INITIAL_CAPITAL if "balance" in k else 0.0
                return state
        except Exception:
            pass
    return {
        "balance": INITIAL_CAPITAL,
        "peak_balance": INITIAL_CAPITAL,
        "open_positions": [],
        "total_trades": 0,
        "winning_trades": 0,
        "realized_pnl": 0.0
    }

def save_portfolio(state):
    if state["balance"] + sum(p["amount_usdt"] for p in state["open_positions"]) > state["peak_balance"]:
        state["peak_balance"] = state["balance"] + sum(p["amount_usdt"] for p in state["open_positions"])
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def check_risk_rules(state, action, amount_usdt):
    total_val = state["balance"] + sum(p["amount_usdt"] for p in state["open_positions"])
    drawdown = (state["peak_balance"] - total_val) / state["peak_balance"] if state["peak_balance"] > 0 else 0.0
    if drawdown >= 0.10:
        return False, f"Max drawdown rule violated ({drawdown:.1%} >= 10.0%). Trading halted."
    if action in ("BUY", "STRONG_BUY", "LONG", "SHORT") and len(state["open_positions"]) >= 3:
        return False, "Max open positions (3) reached. Cannot open new trades."
    return True, ""

def execute_trade(args):
    state = load_portfolio()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    action = args.action.upper()
    asset = args.asset.upper()
    leverage = getattr(args, "leverage", 3)

    if action in ("BUY", "STRONG_BUY", "LONG", "SHORT"):
        direction = "LONG" if action in ("BUY", "STRONG_BUY", "LONG") else "SHORT"
        allowed, msg = check_risk_rules(state, action, args.amount_usdt)
        if not allowed:
            print(f"❌ TRADE BLOCKED: {msg}")
            return False

        total_val = state["balance"] + sum(p["amount_usdt"] for p in state["open_positions"])
        max_position = total_val * 0.20
        size = min(args.amount_usdt, max_position)
        
        if size > state["balance"]:
            print(f"❌ TRADE BLOCKED: Insufficient balance. Required: ${size:.2f}")
            return False

        fee = size * FEE_RATE
        state["balance"] -= fee

        entry_p = round(args.entry_price, 2)
        liq_p = round(entry_p * (1.0 - 1.0 / leverage), 2) if direction == "LONG" else round(entry_p * (1.0 + 1.0 / leverage), 2)

        trade = {
            "timestamp": ts, "asset": asset, "action": f"{direction} ({leverage}x)",
            "amount_usdt": round(size, 2), "entry_price": entry_p,
            "stop_loss": round(args.stop_loss, 2), "take_profit": round(args.take_profit, 2),
            "leverage": leverage, "liquidation_price": liq_p,
            "signal_score": args.signal_score, "confidence": args.confidence,
            "reasoning": args.reasoning, "exit_price": "", "pnl_usdt": "", "pnl_pct": "", "status": "OPEN"
        }
        state["open_positions"].append(trade)
        state["balance"] -= size
        state["total_trades"] += 1
        save_portfolio(state)
        # Log write helper call ...
```

---

### D. Multi-Strategy Framework: `scripts/strategy_framework.py`
Implements the advanced quant layer with BOS/CHOCH setups, order blocks, FVG indicators, and regime transitions.

*(Due to the extensive size of the file (1600+ lines), the structural layout of the main class, regime detector, and a sample SMC strategy are shown here)*

```python
# Structural breakdown of scripts/strategy_framework.py
# File path: scripts/strategy_framework.py
```

```python
class MarketRegimeDetector:
    """Classifies market structure based on ATR, EMAs, and ADX."""
    def detect_regime(self, df: pd.DataFrame, atr: pd.Series) -> str:
        if len(df) < 50:
            return "Ranging"
        close = df['close']
        ema50 = get_ema(close, 50)
        ema200 = get_ema(close, 200)
        
        # Volatility index
        atr_pct = (atr / close) * 100
        high_vol = atr_pct.iloc[-1] > atr_pct.rolling(window=100).mean().iloc[-1] * 1.5
        
        # Trend index
        ema_dist = (ema50 - ema200) / ema200 * 100
        trending_bull = ema_dist.iloc[-1] > 1.5 and close.iloc[-1] > ema50.iloc[-1]
        trending_bear = ema_dist.iloc[-1] < -1.5 and close.iloc[-1] < ema50.iloc[-1]
        
        if high_vol:
            return "High Volatility"
        if trending_bull:
            return "Bullish Trend"
        if trending_bear:
            return "Bearish Trend"
        return "Ranging"

class OrderBlockStrategy(BaseStrategy):
    """Detects institutional supply/demand zones (Order Blocks) and entries on retracement."""
    def __init__(self):
        super().__init__("Order Blocks Reversal", "Smart Money Concepts")

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < 20:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
        # Checks structural highs/lows and validates order blocks ...
        # Returns entry, SL/TP and explanation
```

---

### E. Natural Language REPL Interface: `scripts/natural_language_interface.py`
Parses plain-English commands and translates them to CLI script executions.

```python
# [FULL CODE OF scripts/natural_language_interface.py]
# File path: scripts/natural_language_interface.py
```

*(See complete code shown in Section 5 section view of the transcript. It matches the CLI behavior and translates sentences directly into executing `scripts/agent_cycle.py --scan` or `scripts/backtest.py`)*

---

### F. REST API & Web server: `scripts/server.py`
Hosts the web portal API, executing parallel non-blocking routines to resolve tickers, sentiment index parameters, and active portfolios. Exposes GET endpoints (`/api/state`, `/api/logs`, `/api/scan`) and a POST endpoint (`/api/nl` for Chat prompt inputs).

*(Complete details are present in `scripts/server.py`)*

---

### G. Client SDK Integration: `scripts/bitget_skill_hub_client.py`
Connects directly to the official Bitget MCP server at `https://datahub.noxiaohao.com/mcp` using SSE streams and JSON-RPC payloads.

```python
# [FULL CODE OF scripts/bitget_skill_hub_client.py]
# File path: scripts/bitget_skill_hub_client.py
```

*(See complete client code shown in the transcript section. It includes `_parse_sse` and session initialization helper definitions)*

---

## 6. System Prompts & Agent Instructions
The agent uses a strict four-layer architecture script checklist. System instructions guide the reasoning output format:
```
You are the CryptoSentinel AI autonomous agent.
Your core priority is Risk Management:
1. Validate price feeds using the cache manager and verify price sanity bounds.
2. Filter tokenized stock assets (starting with prefix 'R' unless Rose/Rndr etc) and ETF multipliers.
3. Check overall trailing portfolio drawdown; halt immediately if equity drops 10% below peak.
4. Keep position sizes strictly scaled to conviction scores (5% to 20%).
5. Ensure a strict 2:1 Reward-to-Risk ratio on all entries.
6. When formatting signals, present technical reasons first, followed by macro context and sentiment values.
```

The underlying prompts used by the natural language translator to map queries are defined dynamically in `server.py` and `natural_language_interface.py` through regex mappings.

---

## 7. How to Run Locally

### 1. Prerequisites & Installation
Ensure Python 3.8+ is installed on the system. Install the required dependencies:
```bash
pip install -r requirements.txt
```
*(Requires: `pandas`, `numpy`, `openpyxl`)*

### 2. Running a Historical Backtest
Evaluate strategy performance against historical hourly Solana candlestick data:
```bash
python scripts/backtest.py --data sol_data.json --capital 1000
```
This runs the chronological backtester, updating strategy metrics, and saves results to `backtest_log.csv` and `portfolio_state.json`.

### 3. Fetching Live Signals
Fetch current technical metrics, macro indicators, and sentiment scores:
```bash
python scripts/fetch_signals.py --asset BTC
```
To scan the entire market for top-volume assets:
```bash
python scripts/fetch_signals.py --scan
```

### 4. Running the Autonomous Cycle
To run a single-asset iteration:
```bash
python scripts/agent_cycle.py --asset SOL --leverage 3
```
To scan the market, rank by conviction, check risk criteria, and autonomously execute trades:
```bash
python scripts/agent_cycle.py --scan --leverage 3
```

### 5. Starting the Interactive Web Portal
Launch the server:
```bash
python scripts/server.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser. This displays the Chart.js equity curve, win-rate metrics, open positions, history log, and provides the **Command the AI Agent** chat prompt at the bottom of the portal.

### 6. Starting the CLI Chat Interface
To type commands directly in the shell terminal:
```bash
python scripts/natural_language_interface.py
```

### 7. Exporting Reports
Convert the trade logs into a styled spreadsheet:
```bash
python scripts/generate_report.py
```
This generates `report.xlsx`.

---

## 8. Current Issues, TODOs & Known Limitations
1. **API Rate Limiting**: The public Bitget API restricts candle fetch frequency. The ThreadPoolExecutor in the web server can trigger limits if the client spams queries. Implement progressive backoff or local caching.
2. **Missing Live Trading Auth**: Sim execution only. Futures order creation is simulated. A future step is connecting HMAC signature routines to spot/futures endpoints using API keys.
3. **No Database Persistence**: State is persisted in `portfolio_state.json` and `backtest_log.csv`. In multi-threaded environments, file write conflicts can occur. Needs sqlite or postgres integration.
4. **Mock Fallback Dependency**: If network issues disconnect the client from Bitget, mock prices are injected to maintain web UI uptime. Needs better fallback handlers.

---

## 9. Additional Context for Grok
- **Decoupled Architecture**: The project separates data fetching (`fetch_signals.py`), strategy evaluation (`strategy_framework.py`), execution logic (`sim_trader.py`), and orchestration. This makes it trivial to replace simulated trading with live Bitget orders by modifying only `sim_trader.py`.
- **Glassmorphism Design**: The frontend (`web/index.html` and `web/components/`) was styled for maximum aesthetic appeal. It uses vibrant dark layouts, glass borders, responsive Chart.js layouts, and micro-animations.
- **Why SSE for MCP**: The SSE client (`bitget_skill_hub_client.py`) bypasses the need for running an external Node/MCP daemon locally, making deployment on cloud platforms (e.g. Render, Heroku) robust and straightforward.
- **Next Development Goals**:
  1. Add a SQLite database for transaction logging.
  2. Implement an automated hyperparameter grid search in `scratch/optimize_strategy.py` to optimize weights for the 24 strategies.
  3. Integrate the Alibaba Cloud Qwen reasoning layer directly into `fetch_signals.py` to generate the trade rationale in natural language.
