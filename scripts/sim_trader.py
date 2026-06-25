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

load_dotenv_if_exists()  # Load .env for Bitget keys (read-only recommended for testing)

LOG_FILE = "backtest_log.csv"
STATE_FILE = "portfolio_state.json"
INITIAL_CAPITAL = 1000.0

FEE_RATE = 0.0005  # 0.05% per side (~0.1% round-trip) - realistic for Bitget; applied on closes for simplicity

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
                # Ensure all required keys exist
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
    # Track peak balance
    if state["balance"] + sum(p["amount_usdt"] for p in state["open_positions"]) > state["peak_balance"]:
        state["peak_balance"] = state["balance"] + sum(p["amount_usdt"] for p in state["open_positions"])
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def log_trade(row):
    write_header = not os.path.exists(LOG_FILE)
    # Filter row to ensure only valid fields are written
    filtered_row = {k: row.get(k, "") for k in FIELDNAMES}
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(filtered_row)

def update_logged_trade(timestamp, exit_price, pnl_usdt, pnl_pct, status):
    """Update a trade's exit details in the CSV log."""
    if not os.path.exists(LOG_FILE):
        return
    rows = []
    updated = False
    with open(LOG_FILE, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["timestamp"] == timestamp and r["status"] == "OPEN":
                r["exit_price"] = str(round(exit_price, 2))
                r["pnl_usdt"] = str(round(pnl_usdt, 2))
                r["pnl_pct"] = str(round(pnl_pct, 2))
                r["status"] = status
                updated = True
            rows.append(r)
    
    if updated:
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

def check_risk_rules(state, action, amount_usdt):
    # Rule 1: Max drawdown
    total_val = state["balance"] + sum(p["amount_usdt"] for p in state["open_positions"])
    drawdown = (state["peak_balance"] - total_val) / state["peak_balance"] if state["peak_balance"] > 0 else 0.0
    if drawdown >= 0.10:
        return False, f"Max drawdown rule violated ({drawdown:.1%} >= 10.0%). Trading halted."

    # Rule 2: Max concurrent positions
    if action in ("BUY", "STRONG_BUY", "LONG", "SHORT") and len(state["open_positions"]) >= 3:
        return False, "Max open positions (3) reached. Cannot open new trades."

    return True, ""

def execute_trade(args):
    state = load_portfolio()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Clean action name
    action = args.action.upper()
    asset = args.asset.upper()
    leverage = getattr(args, "leverage", 3)

    if action in ("BUY", "STRONG_BUY", "LONG", "SHORT"):
        # Determine actual position direction
        direction = "LONG" if action in ("BUY", "STRONG_BUY", "LONG") else "SHORT"

        # Run risk check
        allowed, msg = check_risk_rules(state, action, args.amount_usdt)
        if not allowed:
            print(f"❌ TRADE BLOCKED: {msg}")
            return False

        # Apply position sizing cap (max 20% of capital per position)
        total_val = state["balance"] + sum(p["amount_usdt"] for p in state["open_positions"])
        max_position = total_val * 0.20
        size = min(args.amount_usdt, max_position)
        if size < args.amount_usdt:
            print(f"⚠️  Position size reduced from ${args.amount_usdt:.2f} to ${size:.2f} USDT (max 20% limit)")

        if size > state["balance"]:
            print(f"❌ TRADE BLOCKED: Insufficient balance (${state['balance']:.2f} USDT). Required: ${size:.2f}")
            return False

        # Entry fee (realism)
        fee = size * FEE_RATE
        state["balance"] -= fee

        # Calculate liquidation price
        # Long: entry * (1 - 1/leverage)
        # Short: entry * (1 + 1/leverage)
        entry_p = round(args.entry_price, 2)
        if direction == "LONG":
            liq_p = round(entry_p * (1.0 - 1.0 / leverage), 2)
        else:
            liq_p = round(entry_p * (1.0 + 1.0 / leverage), 2)

        trade = {
            "timestamp": ts,
            "asset": asset,
            "action": f"{direction} ({leverage}x)",
            "amount_usdt": round(size, 2),
            "entry_price": entry_p,
            "stop_loss": round(args.stop_loss, 2),
            "take_profit": round(args.take_profit, 2),
            "leverage": leverage,
            "liquidation_price": liq_p,
            "signal_score": args.signal_score,
            "confidence": args.confidence,
            "reasoning": args.reasoning,
            "exit_price": "",
            "pnl_usdt": "",
            "pnl_pct": "",
            "status": "OPEN"
        }

        state["open_positions"].append(trade)
        state["balance"] -= size
        state["total_trades"] += 1
        save_portfolio(state)
        log_trade(trade)

        print(f"✅ SIM {direction} EXECUTED | Size: ${size:.2f} USDT | Leverage: {leverage}x | Entry: ${args.entry_price:.2f} | SL: ${args.stop_loss:.2f} | TP: ${args.take_profit:.2f} | Liq Price: ${liq_p:.2f}")
        return True

    elif action in ("SELL", "STRONG_SELL", "CLOSE_LONG", "CLOSE_SHORT"):
        # Close positions for the asset matching direction
        closed_any = False
        open_pos = []
        
        # Decide which directions to close
        target_directions = []
        if action == "CLOSE_LONG":
            target_directions = ["LONG"]
        elif action == "CLOSE_SHORT":
            target_directions = ["SHORT"]
        else: # SELL or STRONG_SELL: closes LONG positions by default (backward compatible), or SHORT if specified
            # In our new futures reverse system, a SELL should close LONG. If none, we close SHORT if we wanted to (but default to LONG).
            target_directions = ["LONG", "SHORT"]

        for p in state["open_positions"]:
            p_action = p["action"]
            is_match = False
            
            if p["asset"] == asset:
                if "LONG" in p_action and "LONG" in target_directions:
                    is_match = True
                    direction = "LONG"
                elif "SHORT" in p_action and "SHORT" in target_directions:
                    is_match = True
                    direction = "SHORT"

            if is_match:
                # Close it out at current price
                entry = p["entry_price"]
                exit_p = args.entry_price
                p_lev = p.get("leverage", 1)
                
                # PnL math
                if direction == "LONG":
                    pnl_pct = (exit_p - entry) / entry * p_lev * 100.0
                else:
                    pnl_pct = (entry - exit_p) / entry * p_lev * 100.0
                
                pnl_pct = max(-100.0, pnl_pct)  # Cap loss at -100% (liquidation/total loss)
                pnl_usdt = p["amount_usdt"] * (pnl_pct / 100.0)

                # Apply trading fees (realism for backtest/hackathon reporting)
                fee = p["amount_usdt"] * FEE_RATE
                pnl_usdt -= fee
                
                # Update portfolio
                state["balance"] += p["amount_usdt"] + pnl_usdt
                state["realized_pnl"] += pnl_usdt
                if pnl_usdt > 0:
                    state["winning_trades"] += 1
                
                # Update CSV log
                update_logged_trade(p["timestamp"], exit_p, pnl_usdt, pnl_pct, "CLOSED")
                closed_any = True
                print(f"✅ SIM CLOSE {direction} EXECUTED | Asset: {p['asset']} | Entry: ${entry:.2f} | Exit: ${exit_p:.2f} | PnL: ${pnl_usdt:+.2f} ({pnl_pct:+.2f}%)")
            else:
                open_pos.append(p)
        
        if closed_any:
            state["open_positions"] = open_pos
            save_portfolio(state)
        else:
            print(f"ℹ️  No matching open positions found for {asset} to close.")
        return closed_any

def update_positions(args):
    """Scan open positions and check if SL/TP/Liquidation triggers at the current price."""
    state = load_portfolio()
    current_price = args.current_price
    asset = args.asset.upper()

    open_pos = []
    closed_any = False

    for p in state["open_positions"]:
        if p["asset"] == asset:
            p_action = p["action"]
            p_lev = p.get("leverage", 1)
            liq_p = p.get("liquidation_price", 0.0)
            
            direction = "LONG" if "LONG" in p_action else "SHORT"
            
            # SL/TP/Liq checks
            if direction == "LONG":
                hit_tp = current_price >= p["take_profit"]
                hit_sl = current_price <= p["stop_loss"]
                hit_liq = current_price <= liq_p
            else:  # SHORT
                hit_tp = current_price <= p["take_profit"]
                hit_sl = current_price >= p["stop_loss"]
                hit_liq = current_price >= liq_p if liq_p > 0 else False

            if hit_tp or hit_sl or hit_liq:
                if hit_liq:
                    trigger = "LIQUIDATION 💀"
                    exit_price = liq_p
                    pnl_pct = -100.0
                    pnl_usdt = -p["amount_usdt"]
                else:
                    trigger = "TAKE PROFIT 🎯" if hit_tp else "STOP LOSS 🛡️"
                    exit_price = p["take_profit"] if hit_tp else p["stop_loss"]
                    
                    if direction == "LONG":
                        pnl_pct = (exit_price - p["entry_price"]) / p["entry_price"] * p_lev * 100.0
                    else:
                        pnl_pct = (p["entry_price"] - exit_price) / p["entry_price"] * p_lev * 100.0
                        
                    pnl_pct = max(-100.0, pnl_pct)
                    pnl_usdt = p["amount_usdt"] * (pnl_pct / 100.0)

                # Apply trading fees
                fee = p["amount_usdt"] * FEE_RATE
                pnl_usdt -= fee

                state["balance"] += p["amount_usdt"] + pnl_usdt
                state["realized_pnl"] += pnl_usdt
                if pnl_usdt > 0:
                    state["winning_trades"] += 1

                update_logged_trade(p["timestamp"], exit_price, pnl_usdt, pnl_pct, "CLOSED")
                closed_any = True
                print(f"🔔 {trigger} TRIGGERED | Asset: {asset} | Entry: ${p['entry_price']:.2f} | Exit: ${exit_price:.2f} | PnL: ${pnl_usdt:+.2f} ({pnl_pct:+.2f}%)")
            else:
                open_pos.append(p)
        else:
            open_pos.append(p)

    if closed_any:
        state["open_positions"] = open_pos
        save_portfolio(state)
    return closed_any

def show_status():
    state = load_portfolio()
    total_val = state["balance"] + sum(p["amount_usdt"] for p in state["open_positions"])
    drawdown = (state["peak_balance"] - total_val) / state["peak_balance"] if state["peak_balance"] > 0 else 0.0
    win_rate = (state["winning_trades"] / state["total_trades"] * 100) if state["total_trades"] > 0 else 0.0

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
    trade_parser.add_argument("--action", required=True, choices=[
        "BUY", "SELL", "STRONG_BUY", "STRONG_SELL",
        "LONG", "SHORT", "CLOSE_LONG", "CLOSE_SHORT"
    ])
    trade_parser.add_argument("--asset", required=True)
    trade_parser.add_argument("--amount_usdt", type=float, required=True)
    trade_parser.add_argument("--entry_price", type=float, required=True)
    trade_parser.add_argument("--stop_loss", type=float, required=True)
    trade_parser.add_argument("--take_profit", type=float, required=True)
    trade_parser.add_argument("--leverage", type=int, default=3)
    trade_parser.add_argument("--signal_score", type=float, default=0.0)
    trade_parser.add_argument("--confidence", default="MEDIUM")
    trade_parser.add_argument("--reasoning", default="")

    # Update subcommand
    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("--asset", required=True)
    update_parser.add_argument("--current_price", type=float, required=True)

    # Status subcommand
    subparsers.add_parser("status")

    args = parser.parse_args()

    if args.command == "trade":
        execute_trade(args)
    elif args.command == "update":
        update_positions(args)
    elif args.command == "status":
        show_status()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
