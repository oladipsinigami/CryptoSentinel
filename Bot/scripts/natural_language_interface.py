#!/usr/bin/env python3
"""
Natural Language Interface for CryptoSentinel AI

Type plain English instructions like:
- "analyze the market and take trade where it's most profitable based on your strategy"
- "scan for the best opportunities and trade the top ones"
- "run a backtest on BTC data"
- "show the current dashboard and results"
- "reset the portfolio"

It will interpret the instruction and run the appropriate scripts / logic.
This makes the agent "natural language-driven" as encouraged in the hackathon examples.

For the full hackathon experience, you can also connect this via Bitget Agent Hub MCP Server
so you can say the same thing inside Claude Code / Cursor.

Run with: py scripts/natural_language_interface.py
"""

import subprocess
import sys
import os
import json

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Support for directly using Bitget MCP Server as active tools and Skill Hub skills
sys.path.insert(0, os.path.dirname(__file__))
try:
    from mcp_client import BitgetMCPClient
    MCP_AVAILABLE = True
except:
    MCP_AVAILABLE = False


def _resolve_python_for_shell():
    """Return a python command string that works even in Git Bash / WSL on Windows.
    Used for the shell=True run_cmd calls in the terminal NL interface.
    """
    if sys.executable and os.path.isfile(sys.executable):
        # Quote if path has spaces
        if " " in sys.executable:
            return f'"{sys.executable}"'
        return sys.executable

    if sys.platform.startswith("win"):
        # Try common ones that may work in the current shell
        for c in ["python", "python3", "py"]:
            try:
                subprocess.run([c, "--version"], capture_output=True, timeout=3)
                return c
            except Exception:
                continue
    else:
        for c in ["python3", "python"]:
            try:
                subprocess.run([c, "--version"], capture_output=True, timeout=3)
                return c
            except Exception:
                continue
    return "python"

def get_mcp_client():
    if not MCP_AVAILABLE:
        print("MCP client not available (mcp_client.py missing).")
        return None
    client = BitgetMCPClient()
    client.start()
    init = client.initialize()
    if init:
        print("MCP connection initialized - directly using bitget-mcp-server as active tools.")
        tools = client.list_tools()
        if tools and 'result' in tools:
            print("Active MCP tools available (the ones Skill Hub skills use):", [t['name'] for t in tools['result'].get('tools', [])[:5]])
    return client

def run_cmd(cmd, description=""):
    print(f"\n[Running] {description or cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print("⚠️  Warnings/Errors:", result.stderr.strip()[:500])
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to run command: {e}")
        return False

def show_current_state():
    """Quick view of the bot's current results."""
    if os.path.exists("portfolio_state.json"):
        with open("portfolio_state.json") as f:
            state = json.load(f)
        print("\n=== Current Bot State (Portfolio) ===")
        print(f"Balance: ${state.get('balance', 0):,.2f}")
        print(f"Realized PnL: ${state.get('realized_pnl', 0):+,.2f}")
        print(f"Total Trades: {state.get('total_trades', 0)} | Win Rate: {(state.get('winning_trades',0)/max(1,state.get('total_trades',1))*100):.1f}%")
        print(f"Open Positions: {len(state.get('open_positions', []))}")
    if os.path.exists("market_scan.json"):
        with open("market_scan.json") as f:
            scan = json.load(f)
        print("\n=== Latest Market Scan (Top Conviction Coins) ===")
        for i, item in enumerate(scan[:5], 1):
            print(f"{i}. {item['symbol']}: score={item['aggregate_score']:+.2f} → {item['decision']} ({item['confidence']}) | vol=${item.get('volume_24h',0)/1e6:.1f}M")

def interpret_and_run(user_input: str):
    text = user_input.lower().strip()

    if not text:
        return

    if any(word in text for word in ["exit", "quit", "stop", "bye"]):
        print("Goodbye! The agent is ready whenever you are.")
        sys.exit(0)

    # Support for directly using MCP as active tools and Skill Hub skills
    if "use mcp tool" in text or "call mcp" in text:
        client = get_mcp_client()
        if client:
            # Example: parse tool name
            parts = user_input.split()
            tool_name = parts[3] if len(parts) > 3 else "crypto_market"
            args = {"symbol": "BTCUSDT"}
            result = client.call_tool(tool_name, args)
            print(f"MCP tool {tool_name} result (active tool from bitget-mcp-server):", result)
            client.close()
        return

    if "use " in text and " skill" in text:
        client = get_mcp_client()
        if client:
            # Map to MCP tools the skill uses (per hackathon docs)
            skill = user_input.lower().split("use ")[1].split(" skill")[0].strip()
            tool_map = {
                "technical-analysis": "crypto_market",
                "sentiment-analyst": "sentiment_index",
                "news-briefing": "news_feed",
                "macro-analyst": "macro_indicators",
                "market-intel": "defi_analytics"  # or appropriate on-chain tool
            }
            tool = tool_map.get(skill, "crypto_market")
            result = client.call_tool(tool, {"symbol": "BTCUSDT"})
            print(f"Using {skill} skill via MCP tool {tool} (directly using the skill's underlying active MCP tool):", result)
            client.close()
        return

    if any(phrase in text for phrase in ["analyze the market", "scan the market", "scan for", "most profitable", "best opportunities", "take trade", "autonomous", "pick the best", "trade where it's most profitable"]):
        # Leverage extraction
        import re
        m_lev = re.search(r'\b(?:leverage\s*(?:of\s*)?|lev\s*|x\s*)?(\d+)\s*x\b|\b(?:leverage\s*(?:of\s*)?|lev\s*:?)\s*(\d+)\b', text)
        if m_lev:
            lev_val = int(m_lev.group(1) or m_lev.group(2))
            lev = max(1, min(10, lev_val))
        else:
            print("⚠️ Leverage was not specified. What leverage would you like to use? Please specify the leverage (e.g. 3x, 5x, 10x) to complete this trade.")
            return

        print("🧠 Interpreting: Analyze many coins and autonomously trade the most profitable ones based on the full strategy (perception + decision + risk).")
        # This triggers the multi-coin scanner + autonomous selector
        # To directly use MCP: we can call MCP tools for perception data here
        client = get_mcp_client()
        if client:
            print("Using MCP server for perception data (active tools)...")
            # Example: call a perception tool the skills use
            mcp_data = client.call_tool("crypto_market", {"symbol": "BTCUSDT"})
            print("MCP perception data sample:", str(mcp_data)[:300])
            client.close()
        py = _resolve_python_for_shell()
        success = run_cmd(f"{py} scripts/agent_cycle.py --scan --leverage {lev}", "Multi-coin scan + autonomous trade selection (using MCP-enhanced perception where possible)")
        if success:
            show_current_state()
        return

    if "backtest" in text or "run backtest" in text or "test the strategy" in text:
        print("📊 Interpreting: Run a full backtest with the current improved strategy (trend filter + fees + dynamic sizing).")
        py = _resolve_python_for_shell()
        run_cmd(f"{py} scripts/backtest.py --data btc_7d.json --capital 1000", "Backtest on recent BTC data")
        run_cmd(f"{py} scripts/generate_report.py", "Generate Excel report")
        show_current_state()
        return

    if any(word in text for word in ["dashboard", "show results", "status", "portfolio", "how are we doing", "current state"]):
        print("📈 Interpreting: Show current bot results.")
        py = _resolve_python_for_shell()
        run_cmd(f"{py} scripts/dashboard.py", "CLI Dashboard")
        return

    if "reset" in text or "start over" in text or "clean portfolio" in text:
        print("🔄 Interpreting: Reset simulated portfolio to clean $1000 for fresh testing.")
        py = _resolve_python_for_shell()
        run_cmd(f'{py} -c "import json; initial={{\"balance\":1000.0,\"peak_balance\":1000.0,\"open_positions\":[],\"total_trades\":0,\"winning_trades\":0,\"realized_pnl\":0.0}}; open(\"portfolio_state.json\",\"w\").write(json.dumps(initial,indent=2)); print(\"Portfolio reset to $1000\")"', "Reset portfolio")
        return

    if "scan" in text or "analyze coins" in text or "look at the market" in text:
        print("🔍 Interpreting: Just analyze/scan many coins and show the ranking (no auto-trade).")
        py = _resolve_python_for_shell()
        run_cmd(f"{py} scripts/fetch_signals.py --scan", "Multi-coin market scan")
        if os.path.exists("market_scan.json"):
            with open("market_scan.json") as f:
                scan = json.load(f)
            print("\nTop 5 by conviction (the bot would trade these):")
            for i, r in enumerate(scan[:5], 1):
                print(f"  {i}. {r['symbol']}: {r['aggregate_score']:+.2f} → {r['decision']} ({r['confidence']})")
        return

    if "help" in text:
        print("""
Available natural language commands (examples):
- "analyze the market and take trade where it's most profitable based on your strategy"
- "scan for the best opportunities and trade autonomously"
- "run a backtest"
- "show dashboard" or "how are we doing"
- "reset the portfolio"
- "just scan the market" (analysis only, no trades)
        """)
        return

    print("🤔 I understood you want to do something with the market/bot, but I'm not 100% sure.")
    print("Try one of these:")
    print('  "analyze the market and take the most profitable trade"')
    print('  "run a backtest"')
    print('  "show the current results"')
    print('  "reset everything"')

def main():
    print("=" * 60)
    print("🤖 CryptoSentinel AI — Natural Language Interface")
    print("=" * 60)
    print("Talk to your trading bot in plain English.")
    print("It will run the right scripts and show you the results.")
    print()
    print('Example: "analyze the market and take trade where it\'s most profitable based on your strategy"')
    print("Type 'help' for examples, 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            interpret_and_run(user_input)
            print("\n" + "-" * 40)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()
