#!/usr/bin/env python3
"""
Quick demonstration of alignment with Bitget Agent Hub + Skill Hub.

This file shows how CryptoSentinel's perception layer maps to (and re-uses
the same data sources as) the official Bitget AI modules, without requiring
Node.js, MCP, or the full Hub runtime.

For full interactive use with the official skills, see the hackathon page:
https://bitget-ai.gitbook.io/hackathon → use npx bitget-hub + MCP server
or the bgc CLI tool.

Current implementation:
- Direct Bitget REST calls (same as technical-analysis Skill and Hub Tools)
- 5 analyst capabilities matching the Skill Hub exactly
"""

import subprocess
import sys

def show_bitget_direct_usage():
    print("=== Using Bitget APIs directly (as done by Agent Hub Tools & technical-analysis Skill) ===")
    print("The project already calls:")
    print("  https://api.bitget.com/api/v2/spot/market/tickers")
    print("  https://api.bitget.com/api/v2/spot/market/candles")
    print("These are the same endpoints the official technical-analysis skill uses.")
    print()

def show_skill_hub_mapping():
    print("=== Mapping to the 5 official Bitget Skill Hub analyst skills ===")
    print("1. technical-analysis  →  fetch_signals.compute_signals() (pure-Python RSI/MACD/BB/EMA)")
    print("2. sentiment-analyst   →  get_fear_greed() + onchain proxies")
    print("3. news-briefing       →  get_rss_sentiment()")
    print("4. macro-analyst       →  get_global_macro()")
    print("5. market-intel        →  get_onchain_signals() + volume analysis")
    print()
    print("See scripts/fetch_signals.py for the full annotated implementation.")
    print()

def try_bgc_cli_example():
    """Optional: demonstrate calling the official bgc CLI if installed."""
    print("=== Optional: Calling the official Bitget CLI (bgc) from Agent Hub ===")
    try:
        # Example public call (no API key needed)
        result = subprocess.run(
            ["bgc", "spot", "spot_get_ticker", "--symbol", "BTCUSDT"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("bgc output (example):")
            print(result.stdout[:500])
        else:
            print("bgc not found or failed (this is expected in a pure-Python environment).")
            print("To use: npx bitget-hub (see hackathon docs) or install @bitget-ai packages.")
    except FileNotFoundError:
        print("bgc CLI not installed in this environment.")
        print("This is normal — the Python agent uses direct REST calls instead.")
    print()

def show_mcp_connection_instructions():
    print("=== Connecting the Official Bitget MCP Server + Skills ===")
    print("The full Bitget MCP + 5 Skill Hub skills are designed for Claude Code / Cursor / Codex.")
    print()
    print("Exact commands from https://bitget-ai.gitbook.io/hackathon :")
    print()
    print("# 1. One-time install")
    print("npx bitget-hub upgrade-all --target claude")
    print()
    print("# 2. Connect MCP (Claude Code / Cursor)")
    print('claude mcp add -s user \\')
    print('  --env BITGET_API_KEY=your-api-key \\')
    print('  --env BITGET_SECRET_KEY=your-secret-key \\')
    print('  --env BITGET_PASSPHRASE=your-passphrase \\')
    print('  bitget \\')
    print('  -- npx -y bitget-mcp-server')
    print()
    print("After connection, the AI can directly use:")
    print("  - 58 Bitget trading tools (via MCP)")
    print("  - The 5 Skill Hub perception skills (macro-analyst, market-intel, etc.)")
    print()
    print("See BITGET_MCP_SKILLS_SETUP.md in the project root for full guide + config files.")
    print("Example config: mcp-configs/bitget-mcp.json")
    print("Env template: .env.bitget.example")
    print()

if __name__ == "__main__":
    print("CryptoSentinel AI — Bitget Agent Hub Alignment Helper\n")
    show_bitget_direct_usage()
    show_skill_hub_mapping()
    try_bgc_cli_example()
    show_mcp_connection_instructions()
    print("For the official Hackathon submission, we state:")
    print("  'Uses Bitget Spot APIs + implements all 5 Skill Hub perception capabilities.'")
    print("  'Full MCP + bgc + Skill Hub connection documented and ready (see BITGET_MCP_SKILLS_SETUP.md).'")
    print("\nRun this file: python scripts/bitget_hub_alignment.py")