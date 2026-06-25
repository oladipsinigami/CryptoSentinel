#!/usr/bin/env python3
"""
Sim Trader Script — Bitget Trading Agent Skill
Executes simulated (paper) trades and maintains a trade log.
No real funds are used or at risk.
"""

import argparse
import csv
import json
import os
from datetime import datetime, timezone

LOG_FILE = "backtest_log.csv"
STATE_FILE = "portfolio_state.json"
INITIAL_CAPITAL = 1000.0

FIELDNAMES = [
    "timestamp", "asset", "action", "amount_usdt", "entry_price",
    "stop_loss", "take_profit", "signal_score", "confidence",
    "reasoning", "exit_price", "pnl_usdt", "pnl_pct", "status"
]


def load_portfolio():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "balance": INITIAL_CAPITAL,
        "peak_balance": INITIAL_CAPITAL,
        "open_positions": [],
        "total_trades": 0,
        "winning_trades": 0,
        "realized_pnl": 0.0
    }


def save_portfolio(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def log_trade(row):
    write_header = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def execute_trade(args):
    state = load_portfolio()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Risk check: max positions
    if len(state["open_positions"]) >= 3 and args.action in ("BUY", "STRONG_BUY"):
        print(f"❌ TRADE BLOCKED: Max open positions (3) reached. Action: HOLD")
        return

    # Risk check: max drawdown
    drawdown = (state["peak_balance"] - state["balance"]) / state["peak_balance"]
    if drawdown >= 0.10:
        print(f"❌ TRADE BLOCKED: Max drawdown ({drawdown:.1%}) exceeded 10%. Trading halted.")
        return

    # Risk check: balance
    if args.amount_usdt > state["balance"]:
        args.amount_usdt = state["balance"] * 0.20
        print(f"⚠️  Position size reduced to {args.amount_usdt:.2f} USDT (balance constraint)")

    trade = {
        "timestamp": ts,
        "asset": args.asset,
        "action": args.action,
        "amount_usdt": round(args.amount_usdt, 2),
        "entry_price": args.entry_price,
        "stop_loss": args.stop_loss,
        "take_profit": args.take_profit,
        "signal_score": getattr(args, "signal_score", "N/A"),
        "confidence": getattr(args, "confidence", "MEDIUM"),
        "reasoning": getattr(args, "reasoning", ""),
        "exit_price": "",
        "pnl_usdt": "",
        "pnl_pct": "",
        "status": "OPEN"
    }

    state["open_positions"].append(trade)
    state["balance"] -= args.amount_usdt
    state["total_trades"] += 1
    save_portfolio(state)
    log_trade(trade)

    print(f"""
✅ SIM TRADE EXECUTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Asset:       {args.asset}
Action:      {args.action}
Amount:      ${args.amount_usdt:.2f} USDT
Entry:       ${args.entry_price:,.2f}
Stop Loss:   ${args.stop_loss:,.2f}
Take Profit: ${args.take_profit:,.2f}
Balance:     ${state['balance']:.2f} USDT remaining
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


def show_status():
    state = load_portfolio()
    drawdown = (state["peak_balance"] - state["balance"]) / state["peak_balance"]
    win_rate = (state["winning_trades"] / state["total_trades"] * 100) if state["total_trades"] > 0 else 0

    print(f"""
╔══════════════════════════════════════╗
║       PORTFOLIO STATUS               ║
╠══════════════════════════════════════╣
║ Balance:        ${state['balance']:>10.2f} USDT    ║
║ Peak Balance:   ${state['peak_balance']:>10.2f} USDT    ║
║ Drawdown:       {drawdown:>10.1%}          ║
║ Realized PnL:   ${state['realized_pnl']:>+10.2f} USDT   ║
║ Total Trades:   {state['total_trades']:>10}          ║
║ Win Rate:       {win_rate:>10.1f}%          ║
║ Open Positions: {len(state['open_positions']):>10}          ║
╚══════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(description="Bitget Sim Trader")
    subparsers = parser.add_subparsers(dest="command")

    # Trade subcommand
    trade_parser = subparsers.add_parser("trade")
    trade_parser.add_argument("--action", required=True, choices=["BUY", "SELL", "STRONG_BUY", "STRONG_SELL"])
    trade_parser.add_argument("--asset", required=True)
    trade_parser.add_argument("--amount_usdt", type=float, required=True)
    trade_parser.add_argument("--entry_price", type=float, required=True)
    trade_parser.add_argument("--stop_loss", type=float, required=True)
    trade_parser.add_argument("--take_profit", type=float, required=True)
    trade_parser.add_argument("--signal_score", type=float, default=0.0)
    trade_parser.add_argument("--confidence", default="MEDIUM")
    trade_parser.add_argument("--reasoning", default="")

    # Status subcommand
    subparsers.add_parser("status")

    args = parser.parse_args()

    if args.command == "trade":
        execute_trade(args)
    elif args.command == "status":
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
