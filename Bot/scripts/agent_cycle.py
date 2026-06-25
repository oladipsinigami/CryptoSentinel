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
    # Prefer the python running this process
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
            # If it partially ran but had other error, still return what we have
            # (the caller checks returncode)
            pass

    # Final fallback
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
        # Step 1: Scan
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
        # Rank by conviction (abs score)
        ranked = sorted(scan, key=lambda x: abs(x["aggregate_score"]), reverse=True)
        print(f"✅ Scanned. Top conviction: {ranked[0]['symbol']} score={ranked[0]['aggregate_score']:+.2f} ({ranked[0]['decision']})")
        # Step 2: Global position update (for any open)
        print("\n[2/4] Updating any open positions...")
        # Update for top assets to be safe
        for cand in ranked[:5]:
            sym = cand["symbol"].replace("USDT","")
            res = run_cmd(["scripts/sim_trader.py", "update", "--asset", sym, "--current_price", str(cand["price"])])
            if res.returncode == 0 and res.stdout.strip():
                print(res.stdout.strip())
        portfolio = load_portfolio()
        # Step 3: Select and trade top profitable
        print("\n[3/4] Selecting and trading the most profitable opportunities (top by conviction, respecting risk)...")
        traded = 0
        for cand in ranked:
            if traded >= 2:  # limit to 2 new per cycle to be conservative
                break
            sym = cand["symbol"].replace("USDT", "")
            score = cand["aggregate_score"]
            dec = cand["decision"]
            conf = cand["confidence"]
            price = cand["price"]
            chg = cand.get("change_24h_pct", 0)
            if dec == "HOLD" or abs(score) < 1.5:
                continue
            # Check existing position for this asset
            open_for_this = [p for p in portfolio["open_positions"] if p["asset"] == sym]
            if open_for_this:
                continue
            if len(portfolio["open_positions"]) >= 3:
                print("ℹ️ Max positions reached. Skipping further selections.")
                break
            # Direction, stops, and reasoning - prefer strategy intelligence if available
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
                portfolio = load_portfolio()  # reload
            else:
                print(f"⚠️ Trade failed for {sym}: {res.stderr}")
        if traded == 0:
            print("ℹ️ No new high-conviction trades selected from scan (risk filters or no strong edges).")
        # Step 4: Dashboard
        print("\n[4/4] Rendering updated dashboard...")
        res = run_cmd(["scripts/dashboard.py"])
        if res.returncode == 0:
            print(res.stdout)
        return

    # Original single-asset path
    asset = args.asset.upper()
    symbol = f"{asset}USDT"

    print("====================================================")
    print(f"🚀 RUNNING AGENT CYCLE FOR {symbol} ({args.timeframe})")
    print("====================================================\n")

    # Step 1: Check and update existing positions with latest price if any
    # We fetch the current price first to do the update.
    # To get current price, we run the fetch_signals.py script
    print("[1/4] Running Perception Layer (Fetching latest signals)...")
    res = run_cmd(["scripts/fetch_signals.py", "--asset", asset, "--timeframe", args.timeframe])
    if res.returncode != 0:
        print(f"❌ Error fetching signals:\n{res.stderr}")
        sys.exit(1)
    
    # Load the generated signals
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
    
    # Generate reasoning snippet
    reasoning = (
        f"Signals score: {score:+.2f}. F&G: {signals['fear_greed']['value']} ({signals['fear_greed']['label']}). "
        f"RSI: {signals['technicals']['rsi']}, MACD Hist: {signals['technicals']['macd_hist']:+.4f}."
    )

    print(f"✅ Price fetched: ${current_price:,.2f} (24h change: {change_24h_pct:+.2f}%)")

    # Step 2: Update existing open positions first
    print("\n[2/4] Checking and updating open positions for SL/TP hits...")
    res = run_cmd(["scripts/sim_trader.py", "update", "--asset", asset, "--current_price", str(current_price)])
    if res.returncode == 0:
        if res.stdout.strip():
            print(res.stdout.strip())
        else:
            print("ℹ️  No open positions hit stop-loss or take-profit.")
    else:
        print(f"⚠️  Warning updating positions: {res.stderr}")

    # Reload portfolio state after updates
    portfolio = load_portfolio()
    balance = portfolio["balance"]
    
    # Check if there are open positions of this asset
    open_long_pos = [p for p in portfolio["open_positions"] if p["asset"] == asset and "LONG" in p["action"]]
    open_short_pos = [p for p in portfolio["open_positions"] if p["asset"] == asset and "SHORT" in p["action"]]

    # Step 3: Decision Engine & Execution Layer
    print("\n[3/4] Running Decision Engine & Execution Layer...")
    print(f"Recommended action from signals: {decision} (Confidence: {confidence}, Score: {score:+.2f})")

    # Conservative trend filter (aligns live cycle with safer backtest mode using EMA cross)
    # Prevents taking counter-trend positions that caused losses in downtrends.
    ema_cross = signals.get("technicals", {}).get("ema_cross", "neutral")
    if decision in ("BUY", "STRONG BUY") and ema_cross != "bullish":
        print("[FILTER] Trend filter: blocking LONG (price not above EMA trend)")
        decision = "HOLD"
    elif decision in ("SELL", "STRONG SELL") and ema_cross != "bearish":
        print("[FILTER] Trend filter: blocking SHORT (price not below EMA trend)")
        decision = "HOLD"

    leverage = args.leverage  # Leverage for Futures

    if decision in ("BUY", "STRONG BUY"):
        # Position reversal check: if holding SHORT, close it first
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
                # Reload portfolio state
                portfolio = load_portfolio()
                balance = portfolio["balance"]
            else:
                print(f"❌ Error closing SHORT position:\n{res.stderr}")

        # Now open LONG if not already holding one
        if open_long_pos and not open_short_pos:
            print(f"ℹ️  Already holding open LONG position for {symbol}. Blocking new LONG trade to manage exposure.")
        else:
            # Check strategy intelligence targets
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
            
            # Score-strength sizing (more aggressive on stronger signals) + vol dampening
            base_size = 0.05
            strength_bonus = min(0.15, abs(score) * 0.03)  # up to +15% for high |score|
            vol_penalty = min(0.10, abs(change_24h_pct) / 100.0 * 0.5)  # reduce in high vol
            size_pct = base_size + strength_bonus - vol_penalty
            
            if confidence == "HIGH":
                size_pct = max(size_pct, 0.15)
            elif confidence == "MEDIUM":
                size_pct = max(size_pct, 0.10)
            else:
                size_pct = max(size_pct, 0.05)
                
            size_pct = max(0.03, min(0.20, size_pct))  # hard bounds
            amount_usdt = balance * size_pct
            if amount_usdt < 10.0:
                amount_usdt = 10.0
                
            print(f"⚙️  Risk settings: LONG Volatility SL pct = {sl_pct:.1%}, Reward Ratio = 2.0x, Leverage = {leverage}x")
            print(f"💸 Sizing: {size_pct:.0%} of balance (${balance:.2f} USDT) = ${amount_usdt:.2f} USDT")
            
            # Execute LONG trade
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
        # Position reversal check: if holding LONG, close it first
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
                # Reload portfolio state
                portfolio = load_portfolio()
                balance = portfolio["balance"]
            else:
                print(f"❌ Error closing LONG position:\n{res.stderr}")

        # Now open SHORT if not already holding one
        if open_short_pos and not open_long_pos:
            print(f"ℹ️  Already holding open SHORT position for {symbol}. Blocking new SHORT trade to manage exposure.")
        else:
            # Check strategy intelligence targets
            strat_intel = signals.get("strategy_intelligence", {})
            if strat_intel and strat_intel.get("strategy") and strat_intel.get("strategy") != "None":
                sl_price = float(strat_intel.get("stop_loss", current_price * 1.02))
                tp_price = float(strat_intel.get("take_profit", current_price * 0.96))
                reasoning = f"Strategy: {strat_intel['strategy']} | {strat_intel['reasoning']}"
                sl_pct = abs(sl_price - current_price) / (current_price + 1e-10)
            else:
                sl_pct = get_sl_pct(asset, change_24h_pct)
                sl_price = current_price * (1.0 + sl_pct)  # Stop loss is ABOVE entry for SHORT
                tp_price = current_price * (1.0 - sl_pct * 2.0)  # Take profit is BELOW entry for SHORT
            
            # Score-strength sizing + vol dampening
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
                
            print(f"⚙️  Risk settings: SHORT Volatility SL pct = {sl_pct:.1%}, Reward Ratio = 2.0x, Leverage = {leverage}x")
            print(f"💸 Sizing: {size_pct:.0%} of balance (${balance:.2f} USDT) = ${amount_usdt:.2f} USDT")
            
            # Execute SHORT trade
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

    else:  # HOLD
        print("🟡 Decision is HOLD. No simulated trade executed.")

    # Step 4: Show updated dashboard
    print("\n[4/4] Rendering updated dashboard...")
    res = run_cmd(["scripts/dashboard.py"])
    if res.returncode == 0:
        print(res.stdout)
    else:
        print(f"❌ Error rendering dashboard:\n{res.stderr}")

if __name__ == "__main__":
    main()
