# CryptoSentinel AI — Bug Report
**Date**: 2026-06-17 | **Severity Scale**: CRITICAL / HIGH / MEDIUM / LOW  
**Source**: 59-prompt automated end-to-end audit

---

## Bug Summary

| ID | Severity | Status | Description |
|----|----------|--------|-------------|
| BUG-001 | CRITICAL | FIXED | Signal intent too narrow — "analyze X" falls through to fallback |
| BUG-002 | CRITICAL | FIXED | "trade" keyword hijacks info queries with leverage prompt |
| BUG-003 | HIGH | FIXED | Full coin names (ethereum, solana, chainlink) not recognized |
| BUG-004 | HIGH | FIXED | "top conviction signals" extracts BESTUSDT @ $100 fallback |
| BUG-005 | MEDIUM | FIXED | "open positions" / "my position" routes to leverage prompt not status |

---

## Detailed Bug Descriptions

---

### BUG-001 — Signal Intent Too Narrow (CRITICAL) ✅ FIXED

**Affected Tests**: P1-01, P1-04, P1-05, P1-06, P1-07, P1-08, P1-10, P2-04, P2-10, P2-11, P3-02, P3-03, P3-04, P5-01, P5-06  
**Failure rate**: 15/59 tests (25.4%)

**Description**:  
The signal routing block in `handle_nl_command()` only detected the literal words "signal" or "signals". Any other analysis-seeking query fell through to `fallback`. The fallback response does return BTC data, but with the wrong `action` label and a confusing "I didn't fully understand that" message appended.

**Failed inputs**:
- `"Analyze BTC"` → fallback (expected: signals)
- `"Should I long BTC?"` → fallback
- `"What's your BTC outlook?"` → fallback
- `"Analyze Ethereum"` → fallback + wrong coin
- `"Give me a full analysis of BTCUSDT with entry, TP, SL..."` → fallback
- `"Give me a deep ETH analysis with Bollinger Bands, RSI"` → fallback

**Root Cause** (server.py line ~494 before fix):
```python
if "signal" in tlower or "signals" in tlower:
```
This was a single two-word check. No other analysis intent keywords were included.

**Fix Applied**:
```python
_SIGNAL_KEYWORDS = [
    "signal", "signals", "analyze", "analysis", "analyse", "outlook",
    "breakdown", "setup for", "deep", "entry", "stop loss", "take profit",
    "target price", "should i buy", "should i long", "should i short",
    "where should i enter", "where enter", "would you buy", "what's your",
    "your outlook", "explain", "current setup", "full analysis"
]
if any(kw in tlower for kw in _SIGNAL_KEYWORDS):
```

---

### BUG-002 — "trade" Keyword Hijacks Info Queries (CRITICAL) ✅ FIXED

**Affected Tests**: P1-12, P1-13, P2-01, P2-03, P2-05, P2-06, P3-11, P4-02, P4-07, P4-11, P5-02  
**Failure rate**: 11/59 tests (18.6%)

**Description**:  
The TRADE routing block used an overly broad keyword list that included bare words like `"trade"`, `"buy"`, `"sell"`, `"position"`. Any sentence containing these common words was routed to the leverage-execution pipeline, which then immediately returned an error asking the user for leverage amount.

This is the most demo-breaking bug. A hackathon judge asking "Best trade right now?" gets told:
> ⚠️ Leverage was not specified. What leverage would you like to use?

**Failed inputs**:
- `"Best trade right now"` — contains "trade" → prompt_leverage
- `"What should I buy today?"` — contains "buy" → prompt_leverage  
- `"Would you buy Bitcoin here?"` — contains "buy" → prompt_leverage
- `"Give me a safe trade."` — contains "trade" → prompt_leverage
- `"Find a good trade"` — contains "trade" → prompt_leverage
- `"What are my open positions?"` — contains "position" → prompt_leverage
- `"I'm new to crypto. What trade would you take today?"` — contains "trade" → prompt_leverage

**Root Cause** (server.py ~line 566 before fix):
```python
if any(kw in tlower for kw in [
    "trade for me", "trade", "make a trade", "go long", "go short", "buy", "sell",
    "long the", "short the", "take the", "execute", "position"
]):
```
Single common words like `"trade"`, `"buy"`, `"sell"`, `"position"` are in almost every natural language trading query.

**Fix Applied**: Replaced with precise, action-specific phrases:
```python
_TRADE_PHRASES = [
    "trade for me", "make a trade", "go long", "go short",
    "long the", "short the", "execute a trade", "take a trade",
    "place a trade", "enter a trade", "open a long", "open a short",
    "long btc", "long eth", "long sol", "short btc", "short eth", "short sol",
    "trade btc", "trade eth", "trade sol", "trade xrp", "trade doge"
]
```

---

### BUG-003 — Full Coin Names Not Recognized (HIGH) ✅ FIXED

**Affected Tests**: P1-08, P1-10, P3-07, P3-08, P3-09, P3-10, P3-12, P3-13  
**Failure rate**: 8/59 tests (13.6%)

**Description**:  
The `_extract_symbol()` function only processed UPPERCASE tickers (BTC, ETH, SOL). It had no mapping from full English names to tickers. As a result:
- `"Analyze Ethereum"` → extracted BTCUSDT (defaulted to BTC, not ETH)
- `"solana"` → BTCUSDT (lowercase; regex required uppercase)
- `"ethereum"` → BTCUSDT
- `"dogecoin"` → BTCUSDT  
- `"What's your outlook on Chainlink?"` → BTCUSDT
- `"Give me a setup for Avalanche."` → BTCUSDT

**Root Cause**: The regex `r'\b([A-Z]{2,8})\b'` requires uppercase. The text is `.upper()`-ed at the start, but full names like "ETHEREUM" don't match any known ticker pattern, so the fallback BTCUSDT was returned.

**Fix Applied**: Added `COIN_NAME_MAP` dictionary (25 entries) checked before regex:
```python
COIN_NAME_MAP = {
    "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL", "RIPPLE": "XRP",
    "DOGECOIN": "DOGE", "AVALANCHE": "AVAX", "CHAINLINK": "LINK", "CARDANO": "ADA",
    "POLKADOT": "DOT", "POLYGON": "MATIC", ...
}
for coin_name, ticker in COIN_NAME_MAP.items():
    if re.search(r'\b' + coin_name + r'\b', t):
        sym = ticker + "USDT"
        if sr.is_valid_symbol(sym):
            return sym
```

---

### BUG-004 — "Top Conviction Signals" → BESTUSDT @ $100 (HIGH) ✅ FIXED

**Affected Tests**: P5-08  

**Description**:  
The query `"Scan the market and show top conviction signals"` contains the word "signal", so it hits the early signal routing block. The `_extract_symbol()` function then scans for symbols, finds "BEST" (from "best" in COIN_NAME_MAP or the short-circuit check), and returns "BESTUSDT" — a non-existent symbol. The fallback price of $100 is then used.

**Response was**:
```
BESTUSDT @ $100.00 (24h: +0.00%)
Decision: BUY (MEDIUM) | Aggregate: +2.10
```

**Fix Applied**: Added a `"top conviction"/"scan"` intent that routes to `_get_market_overview()` **before** the signal block, so it never reaches `_extract_symbol()`.

---

### BUG-005 — "Open Positions" Routes to Leverage Prompt (MEDIUM) ✅ FIXED

**Affected Test**: P4-11  
**Input**: `"What are my open positions?"`  
**Got**: `prompt_leverage` with `ok=False`

**Root Cause**: "position" was in the broad TRADE keyword list.  
**Fix Applied**: "what are my", "my position", "open position" added to STATUS keywords. Also removed "position" from TRADE phrases.

---

## Residual Known Issues (Not Fixed)

| ID | Issue | Severity | Notes |
|----|-------|----------|-------|
| BUG-006 | Lowercase-only ticker (`eth`, `btc`, `xrp`) falls to fallback | LOW | Requires routing fix: single lowercase coin should route to signals |
| BUG-007 | "what should I buy today?" gives no specific recommendation | LOW | Could route to overview to show top movers |
| BUG-008 | Some fallback responses include "I didn't fully understand that" even when data is correct | LOW | UX only — message cleanup |
| BUG-009 | Fear & Greed score sometimes shows "22 (Extreme Fear)" and "22 (Neutral)" for same value | LOW | Inconsistent label mapping in greed index thresholds |
| BUG-010 | Signal response time: 14-40s depending on coin | LOW | Expected for live API; could cache last result |

---

## Reproduction Steps for Critical Bugs (Pre-Fix)

```
# Bug 001 — Analyze not recognized as signal
POST http://localhost:8000/api/nl
{"command": "Analyze BTC"}
# Expected: {"action": "signals"}, Got: {"action": "fallback"}

# Bug 002 — trade hijacks info query
POST http://localhost:8000/api/nl
{"command": "Best trade right now"}
# Expected: market overview or BTC signal, Got: prompt_leverage with ok:false

# Bug 003 — Ethereum not extracted
POST http://localhost:8000/api/nl
{"command": "Analyze Ethereum"}
# Expected: {"symbol": "ETHUSDT"}, Got: {"symbol": "BTCUSDT"}

# Bug 004 — BESTUSDT
POST http://localhost:8000/api/nl
{"command": "Scan the market and show top conviction signals"}
# Got: {"symbol": "BESTUSDT", "price": 100.0}
```
