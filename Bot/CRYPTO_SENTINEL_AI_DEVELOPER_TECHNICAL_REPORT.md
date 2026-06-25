# CryptoSentinel AI — Developer Technical Report

**Project:** CryptoSentinel AI — Autonomous Crypto Trading Agent for Bitget AI Hackathon S1 (Track 1)  
**Date:** June 11, 2026  
**Author Perspective:** Developer / Technical Lead (compiled from direct code inspection, commit-like history, and session logs)  
**Primary Goal:** Complete, auditable, Bitget-aligned autonomous trading agent with full perception→decision→execution→risk loop, usable via code, CLI, and web natural language interface. All in simulation (paper trading only).

This report details **everything built**, **how the code was written** (design decisions, patterns, iterations), **tools and libraries used**, and the evolution from initial scripts to the current integrated system. It serves as the authoritative technical companion to:

- `HACKATHON_PROJECT_HISTORY_AND_PROGRESS.md` (exhaustive chronological timeline)
- `CRYPTO_SENTINEL_AI_DEVELOPMENT_REPORT.md` (narrative reporter-style summary)

All information is derived from live inspection of the workspace on 2026-06-11.

---

## 1. Project Goals & Constraints (Developer View)

**Core Requirements (from hackathon gitbook analysis):**
- Full closed loop (perception, decision, execution, risk).
- Validated via backtest or sim trading with transparent records.
- Public demo that "actually runs".
- ≤200 word description covering problem + loop + Bitget modules used.
- Strong preference for using Bitget's own infrastructure (Agent Hub tools, 5 Skill Hub skills, MCP Server, CLI/bgc).

**Developer Constraints & Non-Functionals:**
- Simulation-only (no real API keys for trading, no real money).
- Windows/PowerShell primary environment (frequent `py` / Python discovery issues, Git Bash vs cmd).
- Minimal new dependencies (pure Python where possible; pandas/numpy only for official indicators).
- Hackathon timeline (iterative, evidence-driven development).
- Reproducibility and auditability (logs, reports, JSON state as "DB").
- Bitget alignment must be **real** (direct endpoint usage + official libraries/MCP clients), not just "inspired by".

**Success Metrics (internal):**
- Bot becomes "productive" (more trades on edges without blowing risk).
- Supports "a lot of coins" with autonomous selection.
- Natural language control ("analyze the market and take trade where it's most profitable based on your strategy").
- Credible "we use Bitget's Skill Hub MCP and official kline library" story.
- Public demo + fresh records ready for submission.

---

## 2. High-Level Architecture

The system is a classic **closed-loop agent** with strong separation of concerns and multiple interfaces (CLI scripts, subprocess orchestration, web API + chat).

```
Perception (fetch_signals.py + MCP clients + kline lib)
    ↓ (aggregate score -10..+10, decision, rich context)
Decision (get_decision + filters in agent_cycle / backtest)
    ↓ 
Execution (sim_trader.py — paper LONG/SHORT with leverage)
    ↓ (with SL/TP updates, fees, reversals)
Risk (enforced in sim_trader, agent_cycle, backtest)
    ↓
Observability (portfolio_state.json, backtest_log.csv, market_scan.json, dashboard, web UI)
    ↓
Interfaces:
  - Direct scripts (`python scripts/xxx.py`)
  - Orchestration (`agent_cycle.py --scan`)
  - NL REPL (`natural_language_interface.py`)
  - Web Dashboard + AI Chat (`server.py` + web/)
```

**Key Design Patterns Used:**
- **Subprocess isolation** for agent_cycle and NL interface (run `py scripts/xxx.py` via Popen/subprocess.run with capture). Reasons: clean separation, reuse of existing CLI entrypoints, Windows compatibility, easy to swap with real execution later.
- **File-based state** (JSON + CSV as lightweight "database"). No external DB — simple, auditable, works in deployed container.
- **Graceful degradation / fallbacks everywhere** (MCP → direct API, official indicators → pure Python, robust Python executable finder).
- **Direct imports for hot paths** (in server.py for web NL chat — import fetch_signals + BitgetSkillHubClient so "give me signals" is fast and rich, no subprocess overhead for read-only queries).
- **Robust cross-shell launcher** (`_get_python_executable` / similar in multiple files): prefers `sys.executable`, then common names. Critical for Windows (Git Bash, VSCode terminals, Store aliases).
- **MCP protocol implementation** (custom, no official SDK): JSON-RPC 2.0 over HTTP/SSE for the datahub MCP; stdio JSON-RPC for the trading `bitget-mcp-server`.

**Deployment Model:** Simple Python HTTP server (http.server + custom handler). Declarative via render.yaml/Procfile for free-tier hosting.

---

## 3. Detailed Code Implementation by Module

### 3.1 Perception Layer — `scripts/fetch_signals.py`

**How it was written:**
- Started as basic Bitget ticker/candle fetcher + pure-Python TA (calculate_ema, calculate_rsi, calculate_macd, calculate_bollinger_bands, get_bitget_candles).
- Iteratively enhanced for productivity and Bitget alignment.
- Added `load_dotenv_if_exists` (simple, no deps).
- Major rewrite for MCP + official indicators (see below).

**Key Code Patterns:**
- Conditional imports at module level with fallbacks:
  ```python
  try:
      from bitget_skill_hub_client import ...
      _SKILL_HUB_AVAILABLE = True
      _skill_hub_client = BitgetSkillHubClient(verbose=False)
  except ImportError:
      ...
  ```
- Perception functions (`get_fear_greed`, `get_global_macro`, etc.) always try official MCP first, then fallback, mapping responses flexibly (handles multiple shapes: direct fields, `data[]`, etc.).
- `compute_signals(closes)`:
  - If `_OFFICIAL_INDICATORS_AVAILABLE`: build minimal DF, call `IndicatorManager.calculate_multiple(config)`, extract values (e.g. `results["RSI"].values["RSI_14"].iloc[-1]`).
  - Else: pure-Python path.
- `scan_market()`: pre-fetches globals once (rate-limit friendly), filters Bitget tickers by volume, full perception per coin, rank by `abs(aggregate_score)`.
- Aggregation with boosting: `technicals * 1.3 + ...` + regime logic.
- `get_decision(score)`: relaxed bands for activity (STRONG at |4.0|, BUY at 1.5).

**Bitget Integration Details:**
- Exact public endpoints: `https://api.bitget.com/api/v2/spot/market/tickers`, `/candles?symbol=...&granularity=1h&limit=...`
- No auth for market data.

**Tools/Libraries:** `urllib.request` (no requests), `json`, `re` (for RSS), conditional `pandas`/`numpy`.

### 3.2 Official Bitget Indicators Integration

**Files:** `scripts/kline_indicators.py`, `scripts/kline_indicator_utils.py` (placed/copied from Agent Hub GitHub reference in the technical-analysis skill).

**How implemented:**
- Added to `requirements.txt` with comments referencing the exact path in the skill package.
- In fetch_signals: try/except around `import pandas as pd, numpy as np, from kline_indicator_utils import IndicatorManager`
- Usage inside `compute_signals`:
  ```python
  df = pd.DataFrame({'close': closes, ...})
  manager = IndicatorManager(show_indicators=False)
  config = {"RSI": {"period": 14}, "MACD": {...}, ...}
  results = manager.calculate_multiple(config, df)
  # Extract: results["RSI"].values["RSI_14"].iloc[-1], results["MACD"].values["HIST"]...
  ```
- Scoring logic kept identical between official and pure-Python paths for consistency.
- Fallback on any error (print + pure-Python).

**Why this way:** Matches the "technical-analysis" Skill exactly. Increases package size slightly (~2MB) but acceptable. Pure-Python path preserves zero-dep deploys.

### 3.3 MCP Clients (The "Proper Integration" Core)

#### 3.3.1 `scripts/bitget_skill_hub_client.py` (HTTP — Skill Hub Data MCP)
**How written:**
- Implements MCP Streamable HTTP transport from scratch (no SDK).
- `BitgetSkillHubClient`:
  - `_initialize()`: POST JSON-RPC "initialize", capture `mcp-session-id` header.
  - `_call(tool_name, arguments)`: POST with session header, parse SSE "data: {...}".
  - `_parse_sse()`: splits lines, looks for `data:`, JSON decodes `result.content[].text` or raw.
  - Re-init on 4xx session expiry.
- Exposed methods exactly matching Skill Hub usage: `sentiment_index(action)`, `derivatives_sentiment(symbol, action, period)`, `crypto_market(action)`, `news_feed(...)`, `tradfi_news(...)`.
- `get_full_perception()` convenience + `_score_from_perception()` helper.
- CLI: `--test`, `--list-tools`, direct perception fetch.
- Verbose mode for debugging.

**Key decisions:**
- Timeout = 20s.
- User-Agent with hackathon branding.
- Resilient response parsing (multiple shapes from the server).
- Pure stdlib (`urllib.request`, `json`).

**Usage in fetch_signals:** First-try in all four non-technical perception functions. Source tagged `"bitget_skill_hub"`.

#### 3.3.2 `scripts/mcp_client.py` (stdio — Trading MCP)
**How written:**
- `BitgetMCPClient` class using `subprocess.Popen` with `npx --yes bitget-mcp-server`, shell=True (Windows PATH).
- Threaded read loop for stdout JSON-RPC responses.
- `initialize()`, `list_tools()`, `call_tool(name, arguments)` with message IDs and response queue.
- Protocol: 2024-11-05.

**Why kept:** Complements the data MCP. Provides "direct use of bitget-mcp-server as active tools" for trading endpoints (even if primarily used for evidence in this sim project). Used in NL interface for "use mcp tool" commands.

### 3.4 Orchestration & Autonomy — `scripts/agent_cycle.py`

**How written:**
- `run_cmd(args)`: robust python launcher (prefers sys.executable, falls back).
- Two modes:
  - Single asset: perception → update positions → trend filter → execute (with reversal logic) → dashboard.
  - `--scan`: run fetch `--scan`, load `market_scan.json`, update top positions, select/trade top conviction (up to 2, risk checks, no duplicates).
- Dynamic `get_sl_pct(asset, change_24h)`.
- Sizing with strength bonus + vol penalty.
- Subprocess calls to `fetch_signals.py` and `sim_trader.py`.

**Design choice:** Subprocess + CLI reuse for isolation and to keep the "run the script" model consistent with the NL interface.

### 3.5 Execution & Risk — `scripts/sim_trader.py`

**Key implementations:**
- `FEE_RATE = 0.0005` applied on open (balance -= fee) and close (pnl -= fee).
- `check_risk_rules` (10% DD halt, max 3 positions).
- `execute_trade`: broad action aliases (BUY/STRONG_BUY/LONG etc.), direction normalization, liq price calc, full metadata storage.
- `update_positions`: direction-aware SL/TP/liq checks using high/low in backtest context; fee on trigger.
- Robust portfolio loading with key healing.
- CSV append + in-place update for closed trades.
- Status pretty-printer.

**Iterations:** Added fees, more aliases for compatibility with fetch_signals decisions (spaced "STRONG BUY" vs underscore), better close logic.

### 3.6 Backtesting — `scripts/backtest.py`

- Imports `fetch_signals as fs` for consistency.
- Candle replay with lookback for indicators.
- Uses high/low for realistic SL/TP hits.
- Propagated fees, dynamic sizing, trend filter from live code.
- Rich summary metrics (PF, win rate split by direction, etc.).

### 3.7 Web Layer & NL Chat

**Backend (`scripts/server.py`):**
- Custom `http.server.SimpleHTTPRequestHandler` subclass.
- `get_workspace_dir()` for running from scripts/ or root.
- GET: /health, /api/state (portfolio JSON), /api/logs (CSV trades), static from web/.
- POST /api/nl: calls `handle_nl_command` (rich intent parser + direct perception for signals + subprocess for heavy actions).
- Robust `_get_python_executable` + `_run_py_script` (the Windows fix).
- Direct import of perception stack at module load for fast chat responses.
- Audit log `web_nl.log`.

**NL Logic (in server.py + natural_language_interface.py):**
- Early "if 'signal' in tlower" for phrases like "Give me a signal on BTC".
- `_get_live_signals` (direct or subprocess fallback).
- `_parse_trade_intent` (regex + keyword for side/amount/lev/symbol/"best").
- `_execute_intelligent_trade` (targeted or full --scan autonomous).
- Many keyword groups + final safety-net that always surfaces BTC signals.

**Frontend (`web/`):**
- Vanilla JS + Chart.js (equity line, doughnut stats).
- Dynamic DOM updates for KPIs, tables, positions.
- `initAICommand()`: chat log, send on Enter, quick pills, fetch POST /api/nl, auto-refresh dashboard on mutating actions.
- Glassmorphic CSS (matches dark theme).

**Why this architecture:** Keep server dead simple (no FastAPI/Flask) for easy Render deploy. Chat re-uses the same interpreter as the terminal REPL.

### 3.8 Other Tools & Scripts

- `auto_runner.py`: daemon for periodic cycles (uses same launcher).
- `generate_report.py`: openpyxl for styled Excel (win/loss colors, KPIs).
- `dashboard.py`: Unicode box + color ANSI for terminal view.
- `bitget_hub_alignment.py`, `fetch_btc_data.py`, scratch/ files for support.
- `render.yaml` / `Procfile`: declarative hosting.

---

## 4. Tools, Libraries & Environment

**Core Language & Runtime:**
- Python 3 (3.8+ targeted; 3.14 dev evidence in pyc files).
- Heavy stdlib: subprocess, urllib.request, http.server/socketserver, json, csv, re, argparse, os, sys, datetime, threading/queue (for stdio MCP).
- No heavy web framework.

**Optional (for official path):**
- pandas >=2.0, numpy >=1.24 (only for kline indicators; conditional).

**Bitget / External:**
- Public Bitget REST v2 (tickers, candles) — no auth needed for market data.
- Custom MCP clients (no official Python SDK used; protocol implemented directly).
- `npx --yes bitget-mcp-server` and `bitget-client` (for evidence + trading tools path).
- RSS feeds (cointelegraph, coindesk) — parsed with regex.
- CoinGecko fallback.

**Web / Frontend:**
- Pure HTML + CSS (glassmorphic, custom properties).
- Vanilla JS + CDN: Chart.js (charts), Font Awesome (icons), Google Fonts.
- Some pages use React via CDN (sentinel_landing.html etc.) for marketing/demo.

**Dev & Ops Tools:**
- Git (implied; history tracked via conversation + files).
- PowerShell / cmd / Git Bash (primary Windows dev env — drove the launcher robustness).
- Render.com (free Python web service) for public demo.
- Manual backtest/report runs for fresh artifacts before claims.
- `.gitignore`, simple .env loader.

**Documentation & Alignment Tools:**
- Extensive .md files (history, setup guides, submission text).
- Inline docstrings + comments referencing Skill Hub SKILL.md and Agent Hub paths.

**Testing Approach:**
- Iterative: reset → run perception/scan/cycle → view dashboard → analyze logs/metrics → adjust.
- Cross-validated live vs backtest.
- Subprocess + file outputs for easy inspection.

---

## 5. Evolution, Decisions & Lessons

**Major Iterations:**
- Strict thresholds → relaxed + boosted for productivity.
- Single-asset → full multi-coin autonomous (`--scan` everywhere).
- Pure custom TA → official kline lib (with fallback).
- Basic perception → MCP-first (datahub) + direct trading MCP readiness.
- CLI-only → full web + embedded NL chat.
- Naive Python launch → robust executable finder (Windows survival).

**Notable Design Trade-offs:**
- Subprocess vs direct import: subprocess for orchestration (isolation, CLI reuse); direct in server for chat responsiveness.
- Rich MCP client vs official SDK: implemented protocol ourselves for zero extra deps and full control.
- File state vs real DB: sufficient for sim + hackathon; highly auditable.
- Always fallbacks: demo must "just work" even if MCP or pandas missing.

**Windows-Specific Engineering:**
- Multiple launcher helpers.
- UTF-8 reconfigure guards.
- shell=True for npx in Popen/subprocess.
- Advice to users: disable Store aliases, use full paths if needed.

**Known Current Limitations (as of 2026-06-11):**
- Web NL chat signals path ("Give me a signal on BTC") has had reliability issues for the user (trigger not firing consistently in their runs); further refinement paused at user's request ("leave it for now").
- MCP calls can return None (server reachability / response shape); fallbacks active.
- Some "R" prefixed symbols in scans (Bitget special/tokenized listings).
- Server is single-threaded (long scans block briefly).

---

## 6. Current Codebase Snapshot & How to Explore

**Key Live Artifacts (June 11):**
- `portfolio_state.json`: balance ~$785, realized +$56, 2 open leveraged LONGs from scans.
- `latest_signals.json`: BTC HOLD +0.15 with MCP Fear&Greed source.
- `market_scan.json`: multiple entries, currently low conviction.

**To Run as Developer:**
```powershell
# Perception / scan
python scripts/fetch_signals.py --scan
python scripts/fetch_signals.py --asset BTC

# Autonomous cycle
python scripts/agent_cycle.py --scan

# Web + chat (the main interface)
python scripts/server.py   # then http://localhost:8000
```

**Inspection Commands:**
- Grep for "MCP", "bitget_skill_hub", "IndicatorManager", "signal" in scripts/.
- Read docstrings in fetch_signals.py (top alignment comments are excellent).
- Watch server terminal for [NL] prints when using web chat.

---

## 7. Summary of Developer Effort

**What Was Built:**
- ~15-20 core Python modules + supporting docs.
- Two custom MCP protocol clients.
- Official Bitget indicator integration.
- Multi-interface system (scripts, REPL, web + chat).
- Full risk realism (fees everywhere, dynamic everything).
- Deployment-ready public demo.

**Code Volume & Style:**
- Clean, well-commented, defensive Python.
- Consistent patterns (robust launchers, fallbacks, source tagging).
- Zero unnecessary abstractions — pragmatic for hackathon + sim.

**Tools Used (full list):**
- Python 3 + stdlib (dominant).
- pandas/numpy (conditional).
- Bitget public REST + custom MCP.
- npx / node for MCP evidence.
- Chart.js + vanilla web stack.
- openpyxl (reports).
- Render (hosting).
- PowerShell + mixed shells.

This represents a complete, production-minded implementation done iteratively under real user feedback and hackathon constraints.

**References (in repo):**
- All files listed in the history MD.
- `requirements.txt`, `render.yaml`, `CLAUDE.md` (dev commands).
- Inline comments and the two companion reports.

For diffs or specific function deep-dives, provide the exact file + question. The workspace contains the full, working result of this effort. 

(Report generated 2026-06-11 from direct file reads and session context. All claims verifiable in the code.)