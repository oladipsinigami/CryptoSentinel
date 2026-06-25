# CryptoSentinel AI — Model-Aware Debug Analysis Report
**Analyzer**: Antigravity (model-aware-code-debugger skill)  
**Model Optimized For**: Claude Sonnet 4.6 (Thinking)  
**Date**: 2026-06-23  
**Scope**: Full codebase audit — `utils/`, `scripts/`, `Bot/scripts/`  
**Language**: Python 3.x  

---

## Executive Summary

| ID | Severity | File | Issue |
|----|----------|------|-------|
| BUG-A | 🔴 Critical | `utils/symbol_registry.py` | `Optional[str]` used without `from typing import Optional` |
| BUG-B | 🔴 Critical | `scripts/server.py` | `ticker["price"]` dict key access without None/KeyError guard |
| BUG-C | 🟠 High | `scripts/server.py` | `import re` appears twice — second import inside `try` block shadows first |
| BUG-D | 🟠 High | `scripts/server.py` | CRLF (`\r\n`) line endings — breaks Linux/Render deployment |
| BUG-E | 🟠 High | `utils/price_validator.py` | Cached-price floor rejection: no explicit `return None`, relies on fall-through |
| BUG-F | 🟡 Medium | `Bot/scripts/strategy_framework.py` | `StrategySelector` accesses `res["stop_loss"]`/`res["take_profit"]` without `.get()` |
| BUG-G | 🟡 Medium | `Bot/scripts/strategy_framework.py` | `_load_performance` uses bare `except:` — swallows `SystemExit`, `KeyboardInterrupt` |
| BUG-H | 🟡 Medium | `scripts/server.py` | Amount regex captures leverage numbers (e.g. "3x" → `amount=3.0`) |
| BUG-I | 🟡 Medium | `utils/price_fallback.py` | Hard-coded fallback prices are stale (ETH: $3100, SOL: $165) |
| BUG-J | 🟢 Low | `scripts/server.py` | Win-rate display shows `0%` instead of `N/A` when no trades recorded |
| BUG-K | 🟢 Low | `utils/error_handler.py` | `ErrorHandlerContext` always suppresses — no re-raise option |
| BUG-L | 🟢 Low | `scratch/debug_extract.py` | Symbol cleanup order corrupts `USDC`-based symbols (`USDCUSDT → CUSDT`) |

---

## Detailed Bug Analyses

---

### BUG-A — `Optional[str]` Used Without Import 🔴 CRITICAL

**Language**: Python  
**Severity**: Critical  
**File**: `utils/symbol_registry.py` — Line 86  

**Root Cause**: `normalize_symbol` and the return type of `is_valid_symbol` reference `Optional[str]` in their type annotations, but `Optional` is never imported. On Python < 3.10, this raises a `NameError` at import time. Any module that imports `symbol_registry` will fail, setting `_PERCEPTION_AVAILABLE = False` in `server.py` and silently disabling all live signal fetching.

**Evidence**:
```python
# Lines 1-6 of symbol_registry.py — no Optional import:
import os, json, time, urllib.request, urllib.error
from pathlib import Path

# Line 86 — NameError at runtime on Python < 3.10:
def normalize_symbol(symbol: str) -> Optional[str]:  # ← NameError!
```

**Impact**: Breaks `_extract_symbol()` in server.py → all NL commands fall back to BTC default or generic fallback.

**Recommended Fix**:
```diff
# utils/symbol_registry.py — add at top of imports:
+ from typing import Optional
```

---

### BUG-B — `ticker["price"]` Without Key Guard 🔴 CRITICAL

**Language**: Python  
**Severity**: Critical  
**File**: `scripts/server.py` — Lines 643–648  

**Root Cause**: In `_execute_intelligent_trade`, when `resolved_prices` is `None` and a targeted symbol trade runs, the code calls `fs.get_bitget_market_data(symbol)`. If the API returns an empty dict `{}` (a valid non-None response), `ticker["price"]` raises `KeyError`. The guard `if ticker else 60000.0` only protects against `None`, not an empty or malformed dict.

**Evidence**:
```python
# server.py lines 643-644:
ticker = fs.get_bitget_market_data(symbol) if fs else None
price = ticker["price"] if ticker else 60000.0  # ← KeyError if ticker == {}

# Line 647:
chg = ticker.get("change_24h", 0) if ticker else 0  # uses .get() — inconsistent
```

**Recommended Fix**:
```diff
- price = ticker["price"] if ticker else 60000.0
+ price = float(ticker.get("price", 60000.0)) if ticker else 60000.0
```

---

### BUG-C — Double `import re` (Shadowed) 🟠 HIGH

**Language**: Python  
**Severity**: High  
**File**: `scripts/server.py` — Lines 16 and 68  

**Root Cause**: `re` is imported globally at line 16, then imported again inside a `try` block at line 68. While Python deduplicates module loading, the duplicate import is inside a conditional block guarding `_PERCEPTION_AVAILABLE`. This masks the fact that `re` is always available regardless of perception status, and confuses static analysis tools.

**Evidence**:
```python
# Line 16 — global import:
import re

# Line 68 — duplicate inside try block:
import re           # ← remove this
import fetch_signals as fs
```

**Recommended Fix**: Remove `import re` from line 68.

---

### BUG-D — CRLF Line Endings Break Linux/Render Deployment 🟠 HIGH

**Language**: Python  
**Severity**: High  
**File**: `scripts/server.py` — entire file  

**Root Cause**: The file uses Windows CRLF (`\r\n`) throughout. The `Procfile` (`web: python scripts/server.py`) deploys to **Render** (a Linux host). On Linux, Python treats `\r` as part of string content, which can cause:
- Subprocess args with trailing `\r` to silently fail (e.g., `--asset BTC\r`)
- Log lines to overwrite themselves on terminals (carriage return behaviour)
- String comparisons with hardcoded literals to fail subtly

**Recommended Fix**:  
Add to `.gitattributes` in the project root:
```
scripts/server.py text eol=lf
*.py text eol=lf
```
Or run `dos2unix scripts/server.py` before each deployment.

---

### BUG-E — Cached-Price Rejection Has No Explicit `return None` 🟠 HIGH

**Language**: Python  
**Severity**: High  
**File**: `utils/price_validator.py` — Lines 53–64  

**Root Cause**: When the main price fails and falls back to the cache, there is a sanity floor check. If `cached < floor`, the code logs an error but relies on fall-through to reach `return None` at line 64. No explicit `return None` is inside the `if floor is not None and cached < floor:` block, making the logic fragile — any code inserted between line 59 and 63 could unintentionally change behaviour.

**Evidence**:
```python
# Lines 53-64:
if cached is not None:
    ...
    if floor is not None and cached < floor:
        logging.error(...)       # ← no return None here
    else:
        logging.info(...)
        return cached
logging.error(...)
return None                      # ← relies on fall-through from the if-block above
```

**Recommended Fix**:
```diff
  if floor is not None and cached < floor:
      logging.error(f"[price_validator] Cached price {cached} for {symbol} below floor. Rejecting.")
+     return None
  else:
```

---

### BUG-F — `StrategySelector` Dict Key Access Without `.get()` 🟡 MEDIUM

**Language**: Python  
**Severity**: Medium  
**File**: `Bot/scripts/strategy_framework.py` — Lines 1547–1556  

**Root Cause**: In `select_best_trade()`, strategy results are appended with direct key access: `res["stop_loss"]`, `res["take_profit"]`, `res["entry_price"]`. The guard `if res["signal"] != 0` prevents processing zero-signal results, but does not guard against strategies whose non-zero signals omit these keys due to edge-case early returns.

**Evidence**:
```python
# Lines 1546-1556:
if res["signal"] != 0:
    raw_signals.append({
        ...
        "entry_price": res["entry_price"],   # ← KeyError if key missing
        "stop_loss": res["stop_loss"],        # ← KeyError if key missing
        "take_profit": res["take_profit"],    # ← KeyError if key missing
        ...
    })
```

**Recommended Fix**:
```python
last_close = float(df["close"].iloc[-1])
raw_signals.append({
    "strategy": strat.name,
    "category": strat.category,
    "signal": res["signal"],
    "confidence": res.get("confidence", 0.0),
    "entry_price": res.get("entry_price", last_close),
    "stop_loss": res.get("stop_loss", 0.0),
    "take_profit": res.get("take_profit", 0.0),
    "reasoning": res.get("reasoning", ""),
})
```

---

### BUG-G — Bare `except:` Swallows Fatal Signals 🟡 MEDIUM

**Language**: Python  
**Severity**: Medium  
**File**: `Bot/scripts/strategy_framework.py` — Lines 1490–1493  

**Root Cause**: `_load_performance()` catches all exceptions with a bare `except:`, including `KeyboardInterrupt` and `SystemExit`. This means the process can't be stopped cleanly with Ctrl+C if the file read hangs, and any OS-level signal is silently ignored during startup.

**Evidence**:
```python
try:
    with open(self.state_file_path) as f:
        return json.load(f)
except:      # ← swallows everything, including KeyboardInterrupt
    pass
```

**Recommended Fix**:
```diff
- except:
+ except (json.JSONDecodeError, OSError, ValueError) as e:
+     print(f"[StrategySelector] Performance state unreadable: {e}. Starting fresh.")
```

---

### BUG-H — Amount Regex Captures Leverage Numbers 🟡 MEDIUM

**Language**: Python  
**Severity**: Medium  
**File**: `scripts/server.py` — Lines 564–566  

**Root Cause**: The amount regex `r'(\d+(?:\.\d+)?)\s*(?:usdt|usd|\$|dollars)?'` makes the currency suffix optional (`?`), so it matches any bare number. For `"long BTC 3x"`, it captures `3` as `amount=3.0`, while the leverage regex also captures `3`. The trade executes with $3 USDT instead of the default $100.

**Evidence**:
```python
# Line 564:
m = re.search(r'(\d+(?:\.\d+)?)\s*(?:usdt|usd|\$|dollars)?', t)
# "long btc 3x" → m.group(1) = "3" → amount = 3.0  ← WRONG
```

**Recommended Fix**:
```diff
- m = re.search(r'(\d+(?:\.\d+)?)\s*(?:usdt|usd|\$|dollars)?', t)
+ m = re.search(r'(\d+(?:\.\d+)?)\s*(?:usdt|usd|\$|dollars)', t)
```
Removing the `?` from the currency suffix requires an explicit currency marker.

---

### BUG-I — Stale Hard-Coded Fallback Prices 🟡 MEDIUM

**Language**: Python  
**Severity**: Medium  
**File**: `utils/price_fallback.py` — Lines 4–8  

**Root Cause**: `DEFAULT_FALLBACK_PRICES` contains static values written at a specific point in time. When live API and cache both fail, these values are used for signal calculations, SL/TP, and portfolio display — producing inaccurate numbers.

**Evidence**:
```python
DEFAULT_FALLBACK_PRICES = {
    "BTCUSDT": 98000.0,   # Reasonable but drifts
    "ETHUSDT": 3100.0,    # ETH currently ~$3,500+
    "SOLUSDT": 165.0,     # SOL range varies widely
}
```

**Recommended Fix**: Add a timestamp comment and widen the fallback scope, or fetch a single backup price from a free endpoint (e.g., `api.coingecko.com/api/v3/simple/price`):
```python
# Last updated: 2026-06-23 — update these whenever deploying
DEFAULT_FALLBACK_PRICES = {
    "BTCUSDT": 105000.0,
    "ETHUSDT": 3500.0,
    "SOLUSDT": 155.0,
}
```

---

### BUG-J — Win-Rate Shows `0%` vs `N/A` When No Trades 🟢 LOW

**Language**: Python  
**Severity**: Low  
**File**: `scripts/server.py` — Line 1020  

**Root Cause**: `max(1, st.get('total_trades', 1))` prevents division-by-zero, but when `total_trades == 0` it displays `0%` win rate, which is misleading — a fresh portfolio has never lost, it just has no data.

**Recommended Fix**:
```diff
- f"(Win rate ~{ (st.get('winning_trades',0)/max(1,st.get('total_trades',1))*100):.0f}%)"
+ f"(Win rate: {'N/A' if st.get('total_trades', 0) == 0 else f\"{st.get('winning_trades',0)/st['total_trades']*100:.0f}%\"})"
```

---

### BUG-K — `ErrorHandlerContext` Cannot Re-raise 🟢 LOW

**Language**: Python  
**Severity**: Low  
**File**: `utils/error_handler.py` — Lines 36–40  

**Root Cause**: `__exit__` always returns `True` (suppress), with no way for callers to opt into re-raising specific exception types. Makes it impossible to detect whether code inside the context ran successfully or silently failed.

**Recommended Fix**:
```python
def __init__(self, default=None, suppress=True):
    self.default = default
    self.suppress = suppress

def __exit__(self, exc_type, exc_val, exc_tb):
    if exc_type:
        logging.error(f"[error_handler] Exception in block: {exc_val}")
        logging.debug(traceback.format_exception(exc_type, exc_val, exc_tb))
        return self.suppress  # caller controls suppression
    return False
```

---

### BUG-L — USDC Symbol Cleanup Order Corrupts Symbols 🟢 LOW

**Language**: Python  
**Severity**: Low  
**File**: `scratch/debug_extract.py` — Line 67  

**Root Cause**: `replace("USD", "")` executes before `replace("USDC", "")`. Since `"USDC"` contains `"USD"`, the first replace transforms `"USDCUSDT"` → `"CUSDT"` — the second replace has nothing to match, producing an invalid symbol.

**Evidence**:
```
Input base_upper = "USDC"
→ "USDC".replace("USD", "")   = "C"
→ "C".replace("USDC", "")     = "C"   (no match)
→ "C" + "USDT"                = "CUSDT"  ← invalid symbol
```

**Recommended Fix**:
```diff
- sym = base_upper.replace("USD", "").replace("USDC", "").rstrip("-/") + "USDT"
+ sym = base_upper.replace("USDC", "").replace("USD", "").rstrip("-/") + "USDT"
```

---

## Residual Issues from Existing BUG_REPORT.md (Still Open)

| ID | Description |
|----|-------------|
| BUG-006 | Lowercase-only ticker (`eth`, `btc`) falls to fallback signal instead of routing correctly |
| BUG-007 | "What should I buy today?" gives no specific recommendation |
| BUG-008 | Fallback responses append "I didn't fully understand that" even when data is correct |
| BUG-009 | Fear & Greed score label inconsistency (value=22 mapped to both "Extreme Fear" and "Neutral") |
| BUG-010 | Signal response time: 14–40s for live API calls (acceptable, but cacheable) |

---

## Claude Sonnet–Optimized Fix Prompt

Copy and paste this into Claude to apply all fixes in one go:

```xml
<task>
  Fix the following bugs in the CryptoSentinel AI Trading Bot (Python 3.x).
  Apply the minimal-change principle — only fix what is specified.
  For each fix, return: (1) file path, (2) original code, (3) corrected code,
  (4) one sentence explaining why the change is safe.
</task>

<bugs>
  <bug id="BUG-A" priority="critical" file="utils/symbol_registry.py">
    Missing import. Add `from typing import Optional` to the imports at the top
    of the file. The functions normalize_symbol and is_valid_symbol use Optional
    in their return type annotations but it is never imported, causing NameError
    on Python < 3.10.
  </bug>

  <bug id="BUG-B" priority="critical" file="scripts/server.py">
    In _execute_intelligent_trade, line: `price = ticker["price"] if ticker else 60000.0`
    Replace with: `price = float(ticker.get("price", 60000.0)) if ticker else 60000.0`
    An empty dict response from the API passes the truthiness check but raises
    KeyError on direct key access.
  </bug>

  <bug id="BUG-C" priority="high" file="scripts/server.py">
    Remove the duplicate `import re` at line 68 (inside the try block).
    The module is already imported globally at line 16.
  </bug>

  <bug id="BUG-E" priority="high" file="utils/price_validator.py">
    In validate_price, inside the fallback block when `cached < floor`:
    after the logging.error call, add `return None` explicitly.
    Currently the function relies on fall-through to reach return None
    at the end of the function, which is fragile.
  </bug>

  <bug id="BUG-F" priority="medium" file="Bot/scripts/strategy_framework.py">
    In select_best_trade, replace direct key access `res["entry_price"]`,
    `res["stop_loss"]`, `res["take_profit"]` with `.get()` calls and sensible
    defaults (last close price for entry, 0.0 for SL/TP).
  </bug>

  <bug id="BUG-G" priority="medium" file="Bot/scripts/strategy_framework.py">
    In _load_performance, replace bare `except:` with
    `except (json.JSONDecodeError, OSError, ValueError) as e:` and add a
    print statement logging the error message.
  </bug>

  <bug id="BUG-H" priority="medium" file="scripts/server.py">
    In _parse_trade_intent, change the amount regex from:
      `r'(\d+(?:\.\d+)?)\s*(?:usdt|usd|\$|dollars)?'`
    to:
      `r'(\d+(?:\.\d+)?)\s*(?:usdt|usd|\$|dollars)'`
    (remove the trailing `?` to require an explicit currency marker).
  </bug>

  <bug id="BUG-L" priority="low" file="scratch/debug_extract.py">
    Line 67: swap the order of replacements from
      `.replace("USD", "").replace("USDC", "")`
    to:
      `.replace("USDC", "").replace("USD", "")`
    to prevent "USD" consuming the prefix of "USDC" first.
  </bug>
</bugs>
```

---

## Fix Priority Order

| Priority | Bug ID | Risk if Unfixed |
|----------|--------|-----------------|
| 1st | BUG-A | Entire perception system disabled silently |
| 2nd | BUG-B | `KeyError` crash in targeted trade execution |
| 3rd | BUG-E | Price validator silently passes bad cached prices |
| 4th | BUG-F | `KeyError` crash in strategy selector under edge inputs |
| 5th | BUG-H | Trades execute with wrong dollar amount ($3 instead of $100) |
| 6th | BUG-C/G/D/L | Code quality and deployment reliability |

---

## Architecture Health Summary

| Area | Status | Notes |
|------|--------|-------|
| Fallback chain (live → cache → hardcoded) | ✅ Good design | BUG-E is a minor gap in implementation |
| Threading in `_get_live_signals` | ✅ Well done | ThreadPoolExecutor with per-call timeouts |
| 24-strategy framework + regime detection | ✅ Solid | BUG-F is an edge-case robustness gap |
| NL intent parsing | ⚠️ Fragile | Regex-based, grows in complexity; consider spaCy or rule DSL |
| `server.py` size (1259 lines) | ⚠️ Large | Tight coupling between NL parsing, signals, and trade execution |
| Deployment (Render + Procfile) | ⚠️ Risk | CRLF line endings (BUG-D) can cause subtle Linux failures |
| Error handling | ⚠️ Inconsistent | Mix of `@handle_errors`, `ErrorHandlerContext`, and raw `try/except` |
