#!/usr/bin/env python3
"""
Dashboard Script — CryptoSentinel AI Trading Agent
Renders a beautiful, styled terminal dashboard showing current portfolio status,
open positions, recent trade history, and active market signals.
"""

import json
import os
import csv
import sys

try:
    if sys.platform.startswith('win'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

STATE_FILE = "portfolio_state.json"
SIGNALS_FILE = "latest_signals.json"
LOG_FILE = "backtest_log.csv"

def get_color_pnl(val, width=9):
    raw = f"+${val:.2f}" if val > 0 else (f"-${abs(val):.2f}" if val < 0 else f"${val:.2f}")
    padded = f"{raw:<{width}}"
    if val > 0:
        return f"\033[92m{padded}\033[0m"
    elif val < 0:
        return f"\033[91m{padded}\033[0m"
    return padded

def get_color_pct(val, width=7):
    raw = f"+{val:.2f}%" if val > 0 else (f"{val:.2f}%" if val < 0 else f"{val:.2f}%")
    padded = f"{raw:<{width}}"
    if val > 0:
        return f"\033[92m{padded}\033[0m"
    elif val < 0:
        return f"\033[91m{padded}\033[0m"
    return padded

def render_bar(score):
    # Normalize score from [-10, +10] to [0, 10] bars
    num_bars = int((score + 10) / 2)
    num_bars = max(0, min(10, num_bars))
    filled = "█" * num_bars
    empty = "░" * (10 - num_bars)
    
    # Color code
    if score >= 3.0:
        color = "\033[92m" # Green
    elif score <= -3.0:
        color = "\033[91m" # Red
    else:
        color = "\033[93m" # Yellow
        
    return f"{color}{filled}{empty}\033[0m"

def render_decision_badge(decision):
    if "STRONG BUY" in decision:
        return f"\033[1;92m{decision:^11}\033[0m 🟢"
    elif "BUY" in decision:
        return f"\033[92m{decision:^11}\033[0m 🟢"
    elif "STRONG SELL" in decision:
        return f"\033[1;91m{decision:^11}\033[0m 🔴"
    elif "SELL" in decision:
        return f"\033[91m{decision:^11}\033[0m 🔴"
    return f"\033[93m{decision:^11}\033[0m 🟡"

def main():
    # Load state
    state = {
        "balance": 1000.0, "peak_balance": 1000.0, "open_positions": [],
        "total_trades": 0, "winning_trades": 0, "realized_pnl": 0.0
    }
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state.update(json.load(f))
        except Exception:
            pass

    # Load latest signals
    signals = None
    if os.path.exists(SIGNALS_FILE):
        try:
            with open(SIGNALS_FILE) as f:
                signals = json.load(f)
        except Exception:
            pass

    # Load recent trades from CSV
    recent_trades = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                reader = csv.DictReader(f)
                closed_trades = [r for r in reader if r.get("status") == "CLOSED"]
                recent_trades = closed_trades[-5:] # last 5 closed trades
                recent_trades.reverse() # newest first
        except Exception:
            pass

    # Calculate metrics
    total_val = state["balance"] + sum(p["amount_usdt"] for p in state["open_positions"])
    drawdown = (state["peak_balance"] - total_val) / state["peak_balance"] if state["peak_balance"] > 0 else 0.0
    win_rate = (state["winning_trades"] / state["total_trades"] * 100) if state["total_trades"] > 0 else 0.0

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║             🏆 CRYPTO SENTINEL TRADING DASHBOARD             ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    
    if signals:
        tf = signals.get('timeframe', '1h').upper()
        asset_tf = f"{signals['asset']} ({tf})"
        price_str = f"${signals['price']:,.2f}"
        pct_str = get_color_pct(signals['change_24h_pct'], width=8)
        print(f"║  Asset: {asset_tf:<12} | Price: {price_str:<11} | 24h: {pct_str}    ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print("║  SIGNAL BREAKDOWN                                            ║")
        print(f"║  Fear & Greed Sentiment:  {render_bar(signals['fear_greed']['score'])}  {signals['fear_greed']['score']:+4.1f} ({signals['fear_greed']['label']}) ║")
        print(f"║  Technical Indicators:    {render_bar(signals['technicals']['score'])}  {signals['technicals']['score']:+4.1f} (RSI: {signals['technicals']['rsi']})       ║")
        print(f"║  On-Chain Flows:          {render_bar(signals['onchain']['score'])}  {signals['onchain']['score']:+4.1f}                       ║")
        print(f"║  Macro Outlook:           {render_bar(signals['macro']['score'])}  {signals['macro']['score']:+4.1f}                       ║")
        print(f"║  News Sentiment:          {render_bar(signals['news_sentiment']['score'])}  {signals['news_sentiment']['score']:+4.1f}                       ║")
        print("║  ──────────────────────────────────────────────────────────  ║")
        print(f"║  Aggregate score: {signals['aggregate_score']:+4.1f} / 10.0   →  DECISION: {render_decision_badge(signals['decision']):<30} ║")
    else:
        print("║  No recent signal signals found. Run fetch_signals.py first. ║")
        
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  PORTFOLIO OVERVIEW                                          ║")
    balance_str = f"${state['balance']:.2f}"
    pnl_str = get_color_pnl(state['realized_pnl'], width=10)
    print(f"║  Wallet Balance: {balance_str:<15} | Realized PnL: {pnl_str}  ║")
    print(f"║  Total Valuation: ${total_val:<8.2f} USDT | Max Drawdown: {drawdown:>6.1%}            ║")
    print(f"║  Total Trades: {state['total_trades']:<13} | Win Rate: {win_rate:>10.1f}%             ║")
    
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  OPEN POSITIONS                                              ║")
    if state["open_positions"]:
        for p in state["open_positions"]:
            action_str = p.get("action", "LONG")
            liq_p = p.get("liquidation_price", 0.0)
            print(f"║  🟢 {p['asset']:<5} {action_str:<9} | Ent: ${p['entry_price']:<5.0f} | Mar: ${p['amount_usdt']:<3.0f} | Liq: ${liq_p:<5.0f} ║")
    else:
        print("║  No active positions.                                        ║")
        
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  RECENT TRADES                                               ║")
    if recent_trades:
        for t in recent_trades:
            pnl_val = float(t['pnl_usdt']) if t['pnl_usdt'] else 0.0
            pnl_str = get_color_pnl(pnl_val, width=10)
            asset_clean = t['asset'].replace("USDT", "")
            action_clean = t['action']
            print(f"║  {t['timestamp'][:19]} | {asset_clean:<6} | {action_clean:<11} | PnL: {pnl_str} ║")
    else:
        print("║  No trade log data found.                                    ║")
        
    print("╚══════════════════════════════════════════════════════════════╝")

if __name__ == "__main__":
    main()
