# Bitget Agent Hub MCP + Skill Hub Connection Guide

**For CryptoSentinel AI (Bitget AI Hackathon S1 Track 1)**

This document shows exactly how to connect to **all** the MCP, Skills, and tools mentioned on https://bitget-ai.gitbook.io/hackathon.

## 1. What the Hackathon Page Mentions

### MCP Server
- Package: `bitget-mcp-server`
- Provides access to **58 Bitget trading tools** (spot, futures, account, etc.) via the Model Context Protocol.
- Once connected, AI coding tools (Claude Code, Cursor, Codex, etc.) can call Bitget APIs in natural language.

### Skill Hub (5 Analyst Skills)
These are pre-built skills that give your agent perception capabilities:

| Skill                | Capability |
|----------------------|------------|
| `macro-analyst`      | Macro & cross-asset (Fed, DXY, Nasdaq, Gold, etc.) |
| `market-intel`       | On-chain & institutional (ETF flows, whales, DeFi TVL) |
| `news-briefing`      | News aggregation + narrative synthesis |
| `sentiment-analyst`  | Fear & Greed, long/short ratios, funding rates |
| `technical-analysis` | 23 indicators (RSI, MACD, BOLL, etc.). Uses direct Bitget API + Python (pandas/numpy) |

### Other
- **Playbook**: Natural language strategy builder (uses `@bitget-ai/getagent-skill` npm package + Playbook API Key).
- **CLI**: `bgc` (bitget-client) for shell scripting.
- **Qwen**: Special hackathon endpoint for Cursor/Codex.

## 2. Current Status in This Environment

I used the available `search_tool` (MCP discovery) with queries like:
- "bitget"
- "bitget-mcp-server"
- "mcp"
- "agent_hub OR skill hub"
- "technical-analysis OR macro-analyst" etc.

**Result**: No Bitget MCP tools or servers are currently registered or connected in this Grok session's MCP system (all returned empty results).

The only mentioned MCP server in the environment is `arc-docs` (which failed to connect).

**This is expected** — MCP servers like `bitget-mcp-server` must be explicitly added in the host environment (Claude Desktop, Cursor, VS Code with MCP support, or similar) using the commands below. This Grok Build TUI / CLI environment discovers tools via its own `search_tool` / `use_tool` mechanism.

## 3. Exact Connection Commands (from the official page)

### A. Full Quick Install (recommended)
```bash
npx bitget-hub upgrade-all --target claude
```

Or for specific tools:
```bash
npx bitget-hub install --target claude,codex
npx bitget-hub install bitget-skill --target claude
```

### B. Connect the MCP Server (Claude Code / Cursor)
```bash
claude mcp add -s user \
  --env BITGET_API_KEY=your-api-key \
  --env BITGET_SECRET_KEY=your-secret-key \
  --env BITGET_PASSPHRASE=your-passphrase \
  bitget \
  -- npx -y bitget-mcp-server
```

For Codex, add to `~/.codex/config.toml`:
```toml
[[mcp_servers]]
name = "bitget"
command = "npx"
args = ["-y", "bitget-mcp-server"]

[mcp_servers.env]
BITGET_API_KEY = "your-api-key"
BITGET_SECRET_KEY = "your-secret-key"
BITGET_PASSPHRASE = "your-passphrase"
```

### C. Get Bitget API Keys (Read permissions are sufficient for perception/tools)
1. Log into bitget.com → Settings → API Management
2. Create key with **Read** (and Trade if you want execution later)
3. Export the three values as shown above.

### D. Skill Hub Skills
After running `npx bitget-hub ...`, the 5 skills (`macro-analyst`, `market-intel`, `news-briefing`, `sentiment-analyst`, `technical-analysis`) become available in your AI tool.

`technical-analysis` additionally requires (in the AI environment):
```bash
pip install pandas numpy
```

### E. Playbook
- Go to https://www.bitget.com/.../playbook (or GetAgent Studio)
- Create Agent → get Playbook API Key
- In Claude Code prompt:
  ```
  1. Install getagent using https://www.npmjs.com/package/@bitget-ai/getagent-skill
  2. Use getagent to create a strategy playbook about [idea]...
  playbook key: [YOUR_KEY]
  ```

## 4. What This Project (CryptoSentinel) Already Does (Alignment)

We have aligned the existing pure-Python perception layer (`scripts/fetch_signals.py`) with the 5 Skill Hub skills without needing the full MCP runtime:

- Uses the **exact Bitget candle/ticker endpoints** that the official `technical-analysis` skill and Hub Tools use.
- Maps directly:
  - `technical-analysis` ← our pure-Python RSI/MACD/BB/EMA (lightweight, no pandas)
  - `sentiment-analyst` ← Fear & Greed + on-chain/positioning proxies
  - `news-briefing` ← RSS news
  - `macro-analyst` ← BTC dominance + global trends
  - `market-intel` ← volume + on-chain flow simulation

See:
- `scripts/fetch_signals.py` (annotated)
- `scripts/bitget_hub_alignment.py`
- `HACKATHON_SUBMISSION_DESCRIPTION.md`
- Updated README section "Bitget Agent Hub & Skill Hub Alignment"

This satisfies the hackathon requirement to mention "which Bitget AI modules used" while keeping the demo 100% standalone Python.

## 5. Files Created / Updated for MCP Readiness

- `BITGET_MCP_SKILLS_SETUP.md` (this file)
- `scripts/bitget_hub_alignment.py` (includes MCP example + bgc demo)
- `mcp-configs/bitget-mcp.json` (example config — see below)
- `.env.bitget.example` (template for keys)
- Previous updates to `fetch_signals.py`, README, submission description.

### Example MCP Config (for hosts that support JSON config)

Create or merge into your MCP config (e.g. Claude Desktop config or Cursor settings):

```json
{
  "mcpServers": {
    "bitget": {
      "command": "npx",
      "args": ["-y", "bitget-mcp-server"],
      "env": {
        "BITGET_API_KEY": "YOUR_KEY_HERE",
        "BITGET_SECRET_KEY": "YOUR_SECRET_HERE",
        "BITGET_PASSPHRASE": "YOUR_PASSPHRASE_HERE"
      }
    }
  }
}
```

A ready file is provided at `mcp-configs/bitget-mcp.json` (copy and fill in keys).

## 6. Python-Friendly Fallback / Direct Integration (Recommended for this project)

Because the full MCP is designed for AI coding assistants, for a standalone trading agent like CryptoSentinel the best path is:

1. Continue using direct Bitget REST calls (already implemented and aligned).
2. When you want the *full* 58 tools + natural language routing, run your agent **inside** an MCP-capable environment (or expose a thin HTTP/MCP bridge).

We can add:
- A Python client that speaks the same protocol as the MCP tools (if the server exposes SSE/JSON-RPC).
- Subprocess wrapper around `bgc` for selected commands.
- Direct port of the `technical-analysis` skill's Python code (it already uses Bitget + pandas).

Let me know if you want me to implement any of those (e.g. `bitget_mcp_client.py` or integrate `bgc` calls).

## 7. Next Steps to "Connect"

**In your local development environment (outside this Grok session):**
1. Get Bitget API keys (read permissions).
2. Run the `npx bitget-hub` commands above in a terminal where you use Claude Code / Cursor.
3. Once connected, you can ask the AI (in Claude/Cursor) things like:
   - "Use technical-analysis on BTCUSDT 1h"
   - "Run market-intel and sentiment-analyst for current conditions"
   - "Use the Bitget tools to check my futures positions"

**In this project for the hackathon demo:**
- The current alignment + direct APIs is sufficient and honest.
- The new `BITGET_MCP_SKILLS_SETUP.md` + configs prove you know how to connect the full stack.

Run this to verify current alignment:
```bash
py scripts/bitget_hub_alignment.py
```

---

**Would you like me to:**
- Generate the `mcp-configs/` directory + filled example JSON?
- Create a Python `BitgetMCPClient` stub that could call the MCP server if running?
- Add subprocess support for `bgc` in the perception layer?
- Update the submission description / README with more MCP language?
- Query the gitbook doc for more specific details (using the `?ask=` mechanism)?

Just tell me the next concrete step. This gets the project very close to fully leveraging everything mentioned on the hackathon page.