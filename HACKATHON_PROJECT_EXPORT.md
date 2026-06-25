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

### B. Scalp Trading Signal Generator: `scripts/fetch_signals.py`
This is mapped to the 5 analyst-grade perception skills in the Bitget Skill Hub.

```python
# [SELECTED SOURCE CODE OF scripts/fetch_signals.py]
```
*(Please refer to the codebase for the complete 1000-line file; here is the core logic that parses tickers, indicators, news, and calls the StrategySelector)*

```python
def compute_signals(closes):
    if not closes or len(closes) < 30:
        return {
            "rsi": 50.0, "rsi_score": 0.0,
            "macd_hist": 0.0, "macd_score": 0.0,
            "bb_percent": 0.5, "bb_score": 0.0,
            "ema_cross": "neutral", "ema_score": 0.0,
            "score": 0.0
        }
    
    # Technical Indicators calculation
    rsi = calculate_rsi(closes)
    if rsi < 30:      rsi_score = +2.0  # Oversold (Bullish)
    elif rsi < 50:    rsi_score = +1.0
    elif rsi < 70:    rsi_score = -1.0
    else:             rsi_score = -2.0  # Overbought (Bearish)
    
    macd, signal, hist = calculate_macd(closes)
    macd_score = +2.0 if hist > 0 else -2.0
    
    sma, upper, lower = calculate_bollinger_bands(closes)
    latest_price = closes[-1]
    band_range = (upper - lower)
    bb_percent = (latest_price - lower) / band_range if band_range > 0 else 0.5
    if bb_percent < 0.2:    bb_score = +2.0
    elif bb_percent > 0.8:  bb_score = -2.0
    else:                   bb_score = 0.0
    
    ema9 = calculate_ema(closes, 9)[-1]
    ema21 = calculate_ema(closes, 21)[-1]
    if ema9 > ema21:
        ema_cross = "bullish"
        ema_score = +1.0
    else:
        ema_cross = "bearish"
        ema_score = -1.0
        
    avg_score = (rsi_score + macd_score + bb_score + ema_score) / 4.0
    return {
        "rsi": round(rsi, 2),
        "rsi_score": rsi_score,
        "macd_hist": round(hist, 4),
        "macd_score": macd_score,
        "bb_percent": round(bb_percent, 2),
        "bb_score": bb_score,
        "ema_cross": ema_cross,
        "ema_score": ema_score,
        "score": round(avg_score * 3.0, 2)
    }

def main():
    # ... parses args ...
    # fetch_signals loads df and runs:
    # technicals = compute_signals(closes)
    # fear_greed = get_fear_greed()
    # rss_news = get_rss_sentiment()
    # macro = get_global_macro()
    # onchain = get_onchain_signals()
    # base_score = technicals.score * 1.3 + rss_news.score * 0.8 + ...
    # normalized_score = max(-10.0, min(10.0, raw_score))
    # decision, confidence = get_decision(normalized_score)
```

---

### C. Client SDK Client: `scripts/bitget_skill_hub_client.py`
Establishes connection loops to call specific tools from the official Bitget MCP server at `https://datahub.noxiaohao.com/mcp` using the MCP Streamable HTTP SSE transport layer.

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.error
import time

MCP_SERVER_URL = "https://datahub.noxiaohao.com/mcp"
TIMEOUT = 2

class BitgetSkillHubClient:
    def __init__(self, server_url: str = MCP_SERVER_URL, verbose: bool = False):
        self.server_url = server_url
        self.verbose = verbose
        self._session_id = None
        self._request_id = 0

    def _initialize(self) -> bool:
        payload = {
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "CryptoSentinel-AI", "version": "1.0"}
            }
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.server_url, data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": "CryptoSentinel-AI/1.0",
            }, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                session_id = resp.headers.get("mcp-session-id")
                if session_id:
                    self._session_id = session_id
                    return True
                return False
        except Exception:
            return False

    def _call(self, tool_name: str, arguments: dict):
        if not self._session_id:
            if not self._initialize():
                return None
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0", "id": self._request_id, "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.server_url, data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": "CryptoSentinel-AI/1.0",
                "mcp-session-id": self._session_id,
            }, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return self._parse_sse(raw, tool_name)
        except Exception:
            return None

    def _parse_sse(self, raw: str, tool_name: str):
        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                data = json.loads(data_str)
                if "result" in data:
                    result = data["result"]
                    if isinstance(result, dict) and "content" in result:
                        for item in result["content"]:
                            if item.get("type") == "text":
                                text = item["text"]
                                try:
                                    return json.loads(text)
                                except json.JSONDecodeError:
                                    return {"raw": text}
                    return result
            except json.JSONDecodeError:
                continue
        return None

    def sentiment_index(self, action: str = "current"):
        return self._call("sentiment_index", {"action": action})

    def derivatives_sentiment(self, symbol: str = "BTCUSDT", action: str = "long_short", period: str = "4h"):
        return self._call("derivatives_sentiment", {"action": action, "symbol": symbol, "period": period})

    def crypto_market(self, action: str = "global"):
        return self._call("crypto_market", {"action": action})

    def news_feed(self, keyword: str = "", limit: int = 10):
        args = {"action": "latest", "feeds": "cointelegraph,coindesk", "limit": limit}
        if keyword: args["keyword"] = keyword
        return self._call("news_feed", args)
```

---

### D. Frontend Layout: `web/index.html`
Exposes the glassmorphic trading client dashboard, Chart.js equity line tracking, and interactive AI agent control.

```html
<!-- [SELECTED SECTIONS OF web/index.html] -->
```

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="CryptoSentinel AI - Autonomous Deep-Market Exploration and Neural Trading framework.">
    <title>CryptoSentinel AI — Premium Trading Portal</title>
    <!-- Imports Google Fonts Barlow / Outfit / Instrument Serif, FontAwesome, Chart.js, React CDN, Tailwind -->
    <style>
        .liquid-glass {
            background: rgba(255,255,255,0.015);
            backdrop-filter: blur(8px);
            box-shadow: inset 0 1px 1px rgba(255,255,255,0.1);
        }
        body { background-color: #000; color: #fff; font-family: 'Inter', sans-serif; }
    </style>
</head>
<body>
    <div id="root"></div>
    <!-- Babel React rendering scripts -->
    <script type="text/babel" src="components/Navbar.js"></script>
    <script type="text/babel" src="components/Dashboard.js"></script>
    <script type="text/babel" src="components/App.js"></script>
</body>
</html>
```

---

## 6. System Prompts & Agent Instructions
The agent evaluates decisions against strict mathematical and fundamental bounds:
- **Perception Bounds**: Technical factors (e.g. RSI, MACD) are weighted heavily (*1.3 multiplier) relative to sentiment factors.
- **Trend Filter**: Prevents taking counter-trend positions. LONG signals are blocked if price is below EMA-50. SHORT signals are blocked if price is above EMA-50.
- **Drawdown Circuit Breaker**: Trading operations are halted if trailing drawdown exceeds 10% from the peak balance.
- **Leverage Rules**: Liquidation thresholds are monitored closely:
  $$\text{Liquidation Price (Long)} = \text{Entry Price} \times \left(1 - \frac{1}{\text{Leverage}}\right)$$
  $$\text{Liquidation Price (Short)} = \text{Entry Price} \times \left(1 + \frac{1}{\text{Leverage}}\right)$$

---

## 7. How to Run Locally

### 1. Installation
Install the project dependencies (Python 3.8+):
```bash
pip install -r requirements.txt
```

### 2. Backtest Replay
Replay weeks of Solana hourly candlesticks to audit strategy profitability:
```bash
python scripts/backtest.py --data sol_data.json --capital 1000
```
This runs the chronological simulator, records details in `backtest_log.csv`, and resets `portfolio_state.json`.

### 3. Launch Web Server
Launch the HTTP server and API backend:
```bash
python scripts/server.py
```
Open **[http://localhost:8000](http://localhost:8000)**. Scroll to the bottom panel to access the **Command the AI Agent** prompt. 

### 4. Interactive CLI Prompt
Run the terminal REPL chat to input instructions:
```bash
python scripts/natural_language_interface.py
```
Try commands like:
- `analyze the market and trade where it's most profitable based on your strategy`
- `run a backtest`
- `show dashboard`
- `reset portfolio`

---

## 8. Current Issues, TODOs & Known Limitations
1. **API Rate Limiting**: Sending frequent candle requests to public Bitget endpoints will cause temporary IP bans. Add a local sqlite cache or implement token bucket rate limiters.
2. **Read-Only / Simulation**: The order routing system is 100% paper trading. Integrating API keys with HMAC signing headers is required for live execution.
3. **Threading Race Conditions**: Writing portfolio states to `portfolio_state.json` from the web server thread pool can cause write conflicts if multiple commands occur simultaneously. Introduce a thread lock or move state storage to SQLite.

---

## 9. Additional Context for Grok
- **Decoupled Strategy Design**: The 24 strategies in `strategy_framework.py` return a standard signal format. You can add a new strategy by subclassing `BaseStrategy` and appending it to the `StrategySelector` list.
- **Bitget SDK SSE Client**: The SSE connection client (`bitget_skill_hub_client.py`) handles real-time payloads. If running locally with the official `bitget-mcp-server` configured in Cursor/Claude, this enables true agentic tool-use.
- **Glassmorphic Aesthetic UI**: The Web Portal dashboard uses Tailwind and Framer Motion, presenting the win-rate, profit factor, equity curves, active scanner tables, and logs. Focus on maintaining these styling structures during edits.
