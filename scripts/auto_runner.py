#!/usr/bin/env python3
"""
Auto Runner Daemon — CryptoSentinel AI Trading Agent
Runs the agent cycle periodically at a set interval.
"""

import argparse
import sys
import os
import time
import subprocess
from datetime import datetime, timezone

try:
    if sys.platform.startswith('win'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

LOG_FILE = "auto_runner.log"

def log_message(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_cycle(asset, timeframe):
    # Robust launcher (same fix as other scripts for Git Bash / mixed shells on Windows)
    if sys.executable and os.path.isfile(sys.executable):
        python_cmd = sys.executable
    elif sys.platform.startswith("win"):
        python_cmd = "python"
    else:
        python_cmd = "python3"
    args = [python_cmd, "scripts/agent_cycle.py", "--asset", asset, "--timeframe", timeframe]
    
    log_message(f"Starting agent cycle for {asset} ({timeframe})...")
    
    # Run the cycle and capture stdout
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    
    if result.returncode == 0:
        log_message(f"Agent cycle for {asset} completed successfully.")
        # Print output to terminal and log file
        print(result.stdout)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(result.stdout + "\n")
    else:
        log_message(f"❌ Agent cycle for {asset} failed with exit code {result.returncode}!")
        log_message(f"Error output:\n{result.stderr}")

def main():
    parser = argparse.ArgumentParser(description="Autonomous Agent Auto-Runner Daemon")
    parser.add_argument("--asset", default="BTC", help="Asset symbol(s) to trade (e.g. BTC or BTC,ETH,SOL)")
    parser.add_argument("--timeframe", default="1h", choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d"], help="Timeframe / candle granularity")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds between cycles")
    parser.add_argument("--iterations", type=int, default=None, help="Limit number of runs (None for infinite)")
    args = parser.parse_args()

    assets = [a.strip().upper() for a in args.asset.split(",")]

    log_message("====================================================")
    log_message(f"🤖 STARTING CRYPTOSENTINEL DAEMON FOR {', '.join(assets)}")
    log_message(f"⏱️  Timeframe: {args.timeframe.upper()}")
    log_message(f"⏰ Interval: {args.interval} seconds")
    log_message(f"📝 Logging to {LOG_FILE}")
    log_message("====================================================\n")

    count = 0
    try:
        while True:
            count += 1
            if args.iterations and count > args.iterations:
                log_message("Reached specified iteration limit. Stopping daemon.")
                break
                
            for asset in assets:
                run_cycle(asset, args.timeframe)
                if len(assets) > 1:
                    time.sleep(2) # Avoid concurrent API/file writes
            
            # Wait for next interval
            log_message(f"Sleeping for {args.interval} seconds until next check...")
            time.sleep(args.interval)
            print()
            
    except KeyboardInterrupt:
        log_message("Daemon stopped by user keyboard interrupt (Ctrl+C).")
    except Exception as e:
        log_message(f"Fatal error in daemon loop: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
