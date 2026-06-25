#!/usr/bin/env python3
"""
Backtest Engine Script — CryptoSentinel AI Trading Agent
Loads historical candle data, replays market history candle by candle,
computes technical signals, runs decision logic, and simulates trades.

This backtester is intentionally more conservative than the live agent_cycle:
- Uses additional EMA-50 trend filter for entries (live agent does not).
- Uses ATR-based dynamic stop distances (live uses 24h volatility tiers).
- Decision logic is now fully unified with fetch_signals.get_decision().
- TP is set to true 2:1 R:R (fixed from previous 0.5:1 bug).

Purpose: Generate credible, auditable backtest records for hackathon submission
while stress-testing the core perception + risk rules on historical data.
"""

import argparse
import json
import csv
import os
import sys
from datetime import datetime, timezone
import fetch_signals as fs
import pandas as pd
from strategy_framework import StrategySelector

# Project root for consistent file output
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if not os.path.isdir(os.path.join(ROOT_DIR, "web")):
    ROOT_DIR = os.getcwd()

# Configure standard output to use UTF-8 if possible to allow pretty boxes elsewhere
try:
    if sys.platform.startswith('win'):
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

STATE_FILE = os.path.join(ROOT_DIR, "portfolio_state.json")
LOG_FILE = os.path.join(ROOT_DIR, "backtest_log.csv")

FEE_RATE = 0.0005  # 0.05% per side for realistic reporting (applied on exits)

FIELDNAMES = [
    "timestamp", "asset", "action", "amount_usdt", "entry_price",
    "stop_loss", "take_profit", "signal_score", "confidence",
    "reasoning", "exit_price", "pnl_usdt", "pnl_pct", "status"
]

def load_historical_data(filepath):
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return None
    
    with open(filepath) as f:
        data = json.load(f)
    
    symbol = data.get("symbol", "SOLUSDT")
    candles = data.get("candles", [])
    candles.sort(key=lambda x: x["open_time"])
    return symbol, candles

def run_backtest(filepath, initial_capital=1000.0, use_trend_filter=True):
    print(f"[*] Starting backtest on {filepath}...")
    
    loaded = load_historical_data(filepath)
    if not loaded:
        return
        
    symbol, candles = loaded
    if not candles:
        print("[ERROR] No candle data loaded.")
        return
        
    print(f"[*] Loaded {len(candles)} candles for {symbol}.")
    
    # Determine safe starting index for signals + EMA50 trend filter
    # Minimum for technicals ~30, EMA50 needs 55. Use 55 when possible.
    min_lookback = 55
    if len(candles) < min_lookback:
        min_lookback = max(30, len(candles) // 2)
        print(f"[!] Small dataset ({len(candles)} candles). Using reduced lookback of {min_lookback}.")
        print("    Note: EMA-50 trend filter will be limited or disabled for very small files.")
    
    print(f"[*] Starting replay from candle index {min_lookback} (for signal stability).")
    mode = "with EMA50 trend filter (conservative)" if use_trend_filter else "without trend filter (closer to live agent)"
    print(f"[*] Backtest mode: {mode} + ATR stops.")
    
    # Portfolio State
    balance = initial_capital
    peak_balance = initial_capital
    max_drawdown = 0.0
    open_positions = []
    closed_trades = []
    total_trades = 0
    winning_trades = 0
    realized_pnl = 0.0
    long_trades = 0
    short_trades = 0

    # Instantiate the Multi-Strategy Intelligence Layer
    perf_file = os.path.join(ROOT_DIR, "strategy_performance.json")
    selector = StrategySelector(state_file_path=perf_file)

    # Reset performance metrics for clean/reproducible backtest run
    for s in selector.strategies:
        selector.performance[s.name] = {
            "wins": 0,
            "losses": 0,
            "pnl": 0.0,
            "total_trades": 0
        }
    selector.save_performance()

    # Replay loop
    for i in range(min_lookback, len(candles)):
        candle = candles[i]
        high = float(candle["high"])
        low = float(candle["low"])
        close = float(candle["close"])
        timestamp = candle["open_time"]
        
        # 1. Update/check open positions for SL/TP/Liquidation hits first
        still_open = []
        leverage = 3
        for pos in open_positions:
            direction = "LONG" if "SHORT" not in pos["action"] else "SHORT"
            liq_p = pos.get("liquidation_price", 0.0)
            
            if direction == "LONG":
                hit_tp = high >= pos["take_profit"]
                hit_sl = low <= pos["stop_loss"]
                hit_liq = low <= liq_p
            else: # SHORT
                hit_tp = low <= pos["take_profit"]
                hit_sl = high >= pos["stop_loss"]
                hit_liq = high >= liq_p if liq_p > 0 else False
                
            if hit_tp or hit_sl or hit_liq:
                if hit_liq:
                    exit_price = liq_p
                    trigger = "LIQUIDATION 💀"
                    pnl_pct = -100.0
                else:
                    if hit_tp and not hit_sl:
                        exit_price = pos["take_profit"]
                        trigger = "TAKE PROFIT 🎯"
                    else:
                        exit_price = pos["stop_loss"]
                        trigger = "STOP LOSS 🛡️"
                    
                    if direction == "LONG":
                        pnl_pct = (exit_price - pos["entry_price"]) / pos["entry_price"] * leverage * 100.0
                    else:
                        pnl_pct = (pos["entry_price"] - exit_price) / pos["entry_price"] * leverage * 100.0
                        
                pnl_pct = max(-100.0, pnl_pct)
                pnl_usdt = pos["amount_usdt"] * (pnl_pct / 100.0)

                # Apply fees for realism
                fee = pos["amount_usdt"] * FEE_RATE
                pnl_usdt -= fee
                
                balance += pos["amount_usdt"] + pnl_usdt
                realized_pnl += pnl_usdt
                if pnl_usdt > 0:
                    winning_trades += 1
                
                pos["exit_price"] = round(exit_price, 2)
                pos["pnl_usdt"] = round(pnl_usdt, 2)
                pos["pnl_pct"] = round(pnl_pct, 2)
                pos["status"] = "CLOSED"
                closed_trades.append(pos)
                
                print(f"[{timestamp}] [ALERT] {trigger} | {pos['action']} | Entry: ${pos['entry_price']:.2f} | Exit: ${exit_price:.2f} | PnL: ${pnl_usdt:+.2f} ({pnl_pct:+.2f}%)")
                
                # Update strategy performance
                if "strategy" in pos:
                    selector.record_trade_result(pos["strategy"], pnl_usdt)
            else:
                still_open.append(pos)
        open_positions = still_open

        has_long = any("LONG" in p["action"] for p in open_positions)
        has_short = any("SHORT" in p["action"] for p in open_positions)

        # Update peak balance and track max drawdown (for final report)
        current_equity = balance + sum(p["amount_usdt"] for p in open_positions)
        if current_equity > peak_balance:
            peak_balance = current_equity

        dd = (peak_balance - current_equity) / peak_balance if peak_balance > 0 else 0.0
        if dd > max_drawdown:
            max_drawdown = dd

        # Check hard drawdown halt rule
        if dd >= 0.10:
            print(f"[{timestamp}] [HALTED] Max drawdown threshold exceeded ({dd:.1%} >= 10.0%)")
            break

        # Convert rolling slice to DataFrame for StrategySelector
        df_slice = pd.DataFrame(candles[max(0, i-99):i+1])
        df_slice['open'] = df_slice['open'].astype(float)
        df_slice['high'] = df_slice['high'].astype(float)
        df_slice['low'] = df_slice['low'].astype(float)
        df_slice['close'] = df_slice['close'].astype(float)
        df_slice['volume'] = df_slice['volume'].astype(float)
        df_slice.index = pd.to_datetime(df_slice['open_time'])

        best_trade = selector.select_best_trade(df_slice)
        decision = best_trade["decision"]
        confidence = best_trade["confidence"]
        strategy_name = best_trade["strategy"]
        score = best_trade["score"]
        reasoning = best_trade["reasoning"]
        stop_loss = best_trade.get("stop_loss", 0.0)
        take_profit = best_trade.get("take_profit", 0.0)

        # Calculate EMA-50 trend filter if enabled (for conservative exit/entry alignment)
        if use_trend_filter:
            all_closes_50 = [float(c["close"]) for c in candles[max(0, i-54):i+1]]
            if len(all_closes_50) >= 50:
                ema50 = fs.calculate_ema(all_closes_50, 50)[-1]
                price_above_ema50 = close > ema50
            else:
                price_above_ema50 = True
        else:
            price_above_ema50 = True

        # 3. Decision Execution — Reversals and Long/Short Support
        if use_trend_filter and has_short and price_above_ema50:
            still_open = []
            for pos in open_positions:
                if "SHORT" in pos["action"]:
                    exit_p = close
                    pnl_pct = (pos["entry_price"] - exit_p) / pos["entry_price"] * leverage * 100.0
                    pnl_pct = max(-100.0, pnl_pct)
                    pnl_usdt = pos["amount_usdt"] * (pnl_pct / 100.0)

                    # Apply fees
                    fee = pos["amount_usdt"] * FEE_RATE
                    pnl_usdt -= fee

                    balance += pos["amount_usdt"] + pnl_usdt
                    realized_pnl += pnl_usdt
                    if pnl_usdt > 0:
                        winning_trades += 1
                    pos["exit_price"] = round(exit_p, 2)
                    pos["pnl_usdt"] = round(pnl_usdt, 2)
                    pos["pnl_pct"] = round(pnl_pct, 2)
                    pos["status"] = "CLOSED"
                    closed_trades.append(pos)
                    print(f"[{timestamp}] [CLOSE SHORT] Trend Reversal | Entry: ${pos['entry_price']:.2f} | Exit: ${exit_p:.2f} | PnL: ${pnl_usdt:+.2f} ({pnl_pct:+.2f}%)")
                    
                    if "strategy" in pos:
                        selector.record_trade_result(pos["strategy"], pnl_usdt)
                else:
                    still_open.append(pos)
            open_positions = still_open
            has_short = False
            current_equity = balance + sum(p["amount_usdt"] for p in open_positions)

        if use_trend_filter and has_long and not price_above_ema50:
            still_open = []
            for pos in open_positions:
                if "SHORT" not in pos["action"]:
                    exit_p = close
                    pnl_pct = (exit_p - pos["entry_price"]) / pos["entry_price"] * leverage * 100.0
                    pnl_pct = max(-100.0, pnl_pct)
                    pnl_usdt = pos["amount_usdt"] * (pnl_pct / 100.0)

                    # Apply fees
                    fee = pos["amount_usdt"] * FEE_RATE
                    pnl_usdt -= fee

                    balance += pos["amount_usdt"] + pnl_usdt
                    realized_pnl += pnl_usdt
                    if pnl_usdt > 0:
                        winning_trades += 1
                    pos["exit_price"] = round(exit_p, 2)
                    pos["pnl_usdt"] = round(pnl_usdt, 2)
                    pos["pnl_pct"] = round(pnl_pct, 2)
                    pos["status"] = "CLOSED"
                    closed_trades.append(pos)
                    print(f"[{timestamp}] [CLOSE LONG] Trend Reversal | Entry: ${pos['entry_price']:.2f} | Exit: ${exit_p:.2f} | PnL: ${pnl_usdt:+.2f} ({pnl_pct:+.2f}%)")
                    
                    if "strategy" in pos:
                        selector.record_trade_result(pos["strategy"], pnl_usdt)
                else:
                    still_open.append(pos)
            open_positions = still_open
            has_long = False
            current_equity = balance + sum(p["amount_usdt"] for p in open_positions)

        # Open positions based on signals
        if decision in ("BUY", "STRONG BUY"):
            if price_above_ema50 and not has_long and len(open_positions) < 3:
                max_size = current_equity * 0.20
                base_pct = 0.08
                strength_bonus = min(0.12, abs(score) * 0.025)
                size_pct = min(0.20, base_pct + strength_bonus)
                size = min(current_equity * size_pct, max_size)

                if balance >= size and size > 10:
                    # Entry fee
                    fee = size * FEE_RATE
                    balance -= fee

                    entry_p = close
                    sl_val = stop_loss
                    tp_val = take_profit
                    liq_p = round(entry_p * (1.0 - 1.0 / leverage), 2)

                    pos = {
                        "timestamp": timestamp,
                        "asset": symbol,
                        "action": f"LONG ({leverage}x)",
                        "amount_usdt": round(size, 2),
                        "entry_price": round(entry_p, 2),
                        "stop_loss": sl_val,
                        "take_profit": tp_val,
                        "liquidation_price": liq_p,
                        "signal_score": round(score, 2),
                        "confidence": confidence,
                        "strategy": strategy_name,
                        "reasoning": f"[{strategy_name} | LONG] {reasoning}",
                        "exit_price": "",
                        "pnl_usdt": "",
                        "pnl_pct": "",
                        "status": "OPEN"
                    }
                    open_positions.append(pos)
                    balance -= size
                    total_trades += 1
                    long_trades += 1
                    print(f"[{timestamp}] [LONG | {strategy_name}] Entry:${entry_p:.2f} SL:${sl_val:.2f} TP:${tp_val:.2f} Score:{score:+.2f}")

        elif decision in ("SELL", "STRONG SELL"):
            if not price_above_ema50 and not has_short and len(open_positions) < 3:
                max_size = current_equity * 0.20
                base_pct = 0.08
                strength_bonus = min(0.12, abs(score) * 0.025)
                size_pct = min(0.20, base_pct + strength_bonus)
                size = min(current_equity * size_pct, max_size)

                if balance >= size and size > 10:
                    # Entry fee
                    fee = size * FEE_RATE
                    balance -= fee

                    entry_p = close
                    sl_val = stop_loss
                    tp_val = take_profit
                    liq_p = round(entry_p * (1.0 + 1.0 / leverage), 2)

                    pos = {
                        "timestamp": timestamp,
                        "asset": symbol,
                        "action": f"SHORT ({leverage}x)",
                        "amount_usdt": round(size, 2),
                        "entry_price": round(entry_p, 2),
                        "stop_loss": sl_val,
                        "take_profit": tp_val,
                        "liquidation_price": liq_p,
                        "signal_score": round(score, 2),
                        "confidence": confidence,
                        "strategy": strategy_name,
                        "reasoning": f"[{strategy_name} | SHORT] {reasoning}",
                        "exit_price": "",
                        "pnl_usdt": "",
                        "pnl_pct": "",
                        "status": "OPEN"
                    }
                    open_positions.append(pos)
                    balance -= size
                    total_trades += 1
                    short_trades += 1
                    print(f"[{timestamp}] [SHORT | {strategy_name}] Entry:${entry_p:.2f} SL:${sl_val:.2f} TP:${tp_val:.2f} Score:{score:+.2f}")

    # Finalize remaining open positions at final close price
    if open_positions:
        print("\n[*] Closing remaining open positions at backtest end...")
        final_close = float(candles[-1]["close"])
        final_ts = candles[-1]["open_time"]
        for pos in open_positions:
            direction = "LONG" if "SHORT" not in pos["action"] else "SHORT"
            if direction == "LONG":
                pnl_pct = (final_close - pos["entry_price"]) / pos["entry_price"] * leverage * 100.0
            else:
                pnl_pct = (pos["entry_price"] - final_close) / pos["entry_price"] * leverage * 100.0
            
            pnl_pct = max(-100.0, pnl_pct)
            pnl_usdt = pos["amount_usdt"] * (pnl_pct / 100.0)

            # Apply fees
            fee = pos["amount_usdt"] * FEE_RATE
            pnl_usdt -= fee
            
            balance += pos["amount_usdt"] + pnl_usdt
            realized_pnl += pnl_usdt
            if pnl_usdt > 0:
                winning_trades += 1
                
            pos["exit_price"] = round(final_close, 2)
            pos["pnl_usdt"] = round(pnl_usdt, 2)
            pos["pnl_pct"] = round(pnl_pct, 2)
            pos["status"] = "CLOSED"
            closed_trades.append(pos)
            print(f"[{final_ts}] [CLOSED] Entry: ${pos['entry_price']:.2f} | Exit: ${final_close:.2f} | PnL: ${pnl_usdt:+.2f} ({pnl_pct:+.2f}%)")
            
            if "strategy" in pos:
                selector.record_trade_result(pos["strategy"], pnl_usdt)
        open_positions = []

    # Calculate metrics
    final_equity = balance
    net_profit = final_equity - initial_capital
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    # Additional hackathon-friendly metrics from closed trades
    avg_pnl = (realized_pnl / total_trades) if total_trades > 0 else 0.0
    gross_profit = sum(t.get("pnl_usdt", 0) for t in closed_trades if float(t.get("pnl_usdt", 0) or 0) > 0)
    gross_loss = abs(sum(t.get("pnl_usdt", 0) for t in closed_trades if float(t.get("pnl_usdt", 0) or 0) < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0.0)
    max_dd_pct = max_drawdown * 100

    # Save portfolio state (always clean at end of backtest)
    state = {
        "balance": round(final_equity, 2),
        "peak_balance": round(peak_balance, 2),
        "open_positions": [],
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "realized_pnl": round(realized_pnl, 2)
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    # Save all closed trades to backtest_log.csv (clean, auditable log for submission)
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for t in closed_trades:
            filtered_t = {k: t.get(k, "") for k in FIELDNAMES}
            writer.writerow(filtered_t)

    # Professional summary (good for judges / report)
    print("\n" + "="*48)
    print("        BACKTEST RESULTS SUMMARY")
    print("="*48)
    print(f"Symbol:              {symbol}")
    print(f"Initial Capital:     ${initial_capital:.2f} USDT")
    print(f"Final Capital:       ${final_equity:.2f} USDT")
    print(f"Net Profit:          ${net_profit:+.2f} USDT ({net_profit/initial_capital*100:+.2f}%)")
    print(f"Peak Balance:        ${peak_balance:.2f} USDT")
    print(f"Max Drawdown:        {max_dd_pct:.1f}%")
    print(f"Total Trades:        {total_trades}  (LONG: {long_trades}, SHORT: {short_trades})")
    print(f"Win Rate:            {win_rate:.1f}%  ({winning_trades}/{total_trades})")
    print(f"Realized PnL:        ${realized_pnl:+.2f} USDT")
    print(f"Avg PnL per Trade:   ${avg_pnl:+.2f}")
    if gross_loss > 0:
        print(f"Profit Factor:       {profit_factor:.2f}  (gross wins / gross losses)")
    else:
        print(f"Profit Factor:       N/A (no losing trades)")
    print("="*48)

    print("\n" + "="*48)
    print("     STRATEGY INTELLIGENCE PERFORMANCE")
    print("="*48)
    active_strats = {k: v for k, v in selector.performance.items() if v.get("total_trades", 0) > 0}
    if active_strats:
        print(f"{'Strategy Name':<30} | {'Trades':<6} | {'Win Rate':<8} | {'PnL (USDT)':<10}")
        print("-" * 62)
        for name, perf in sorted(active_strats.items(), key=lambda x: x[1]["pnl"], reverse=True):
            wr = (perf["wins"] / perf["total_trades"] * 100) if perf["total_trades"] > 0 else 0.0
            print(f"{name:<30} | {perf['total_trades']:<6} | {wr:.1f}%   | ${perf['pnl']:+.2f}")
    else:
        print("No strategy intelligence trades were recorded during this run.")
    print("="*48)

    print(f"Trade log saved to   {LOG_FILE}")
    print(f"Portfolio state      {STATE_FILE}")
    print("Note: Decision logic + 2:1 RR now unified with live agent_cycle/sim_trader.")
    print("="*48 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Backtest on Historical Candles")
    parser.add_argument("--data", default="sol_data.json", help="Path to historical candles JSON file")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital in USDT")
    parser.add_argument("--no-trend-filter", action="store_true",
                        help="Disable EMA50 trend filter (closer to live agent_cycle behavior, may increase trade count on small datasets)")
    args = parser.parse_args()
    
    # Resolve data file path: try as-is, then relative to ROOT_DIR
    data_path = args.data
    if not os.path.exists(data_path):
        data_path = os.path.join(ROOT_DIR, args.data)
    if not os.path.exists(data_path):
        data_path = os.path.join(SCRIPT_DIR, args.data)
    
    use_trend_filter = not args.no_trend_filter
    run_backtest(data_path, args.capital, use_trend_filter=use_trend_filter)
