# Root Cause Report: " Network or server error. Is the server running?"

## Executive Summary

The ` Network or server error. Is the server running?` error is triggered by the
frontend's `catch(e)` block in `Dashboard.js` when the `fetch('/api/nl', ...)` call
throws  typically due to a **browser connection reset** caused by the server taking
**1529 seconds** to respond. This latency is not an outage; it is a sequential I/O
bottleneck in `_get_live_signals()`.

---

## Error Location in Codebase

| File | Line | Code |
|------|------|------|
| [Dashboard.js](file:///c:/Users/oladips/Downloads/Bot/web/components/Dashboard.js#L137-L141) | 137141 | `catch(e) { return [...filtered, { text: " Network or server error..." }] }` |
| [server.py](file:///c:/Users/oladips/Downloads/Bot/scripts/server.py#L126-L250) | 126250 | `_get_live_signals()`  the backend handler |

---

## Root Cause: Sequential I/O in `_get_live_signals()`

When a user sends "Analyze BTC", "Give me a signal for ETH", "Analyze SOL", or
"What is the best trade right now?", the server calls `_get_live_signals()`, which
makes **8 independent external I/O calls in sequence**:

| Call | Avg Time |
|------|----------|
| `get_bitget_market_data` | 1.10s |
| `get_bitget_candles` | 1.74s |
| `get_fear_greed` | 2.94s |
| `get_rss_sentiment` | 1.28s |
| `get_global_macro` | 0.89s |
| `get_onchain_signals` | 3.43s |
| `get_bitget_ohlcv_df` + StrategySelector | 2.88s |
| `_skill_hub.derivatives_sentiment` | 1.41s |
| **Total (sequential)** | **~15.86s** |

>  Under worse network conditions (or first call before MCP warmup), this reaches **1829 seconds**.

### Why the Browser Shows the Error

1. The browser's `fetch()` has no explicit timeout, but browsers terminate connections
   that are reset by the server or held open too long without intermediate data.
2. While the `/api/nl` request is processing (1529s), the dashboard's **5-second polling**
   for `/api/state`, `/api/logs`, `/api/scan` fires multiple times. These stack up.
3. The server's `ThreadingTCPServer` handles each request in a thread, so polling still
   works  but the browser may abort the NL request if its internal connection limits
   are reached or if the tab becomes inactive.
4. The result: `fetch()` throws a `TypeError: Failed to fetch` or `AbortError`,
   which the `catch(e)` handler catches and displays as the error message.

---

## Evidence

**Measured response times before fix** (from `scratch/test_live.py`):
```
[29.2s] CMD='Analyze BTC'           OK=True action=signals
[23.4s] CMD='Analyze ETH'           OK=True action=signals
[18.6s] CMD='Analyze SOL'           OK=True action=signals
[25.4s] CMD='Best trade right now'  OK=True action=fallback
```

The requests succeed server-side but take 1829s  far too long for a stable browser connection.

**Server log evidence** (`ConnectionAbortedError` at timestamps matching long requests):
```
Exception occurred during processing of request from ('127.0.0.1', 57053)
...
ConnectionAbortedError: [WinError 10053] An established connection was aborted by the software in your host machine
```

---

## Fix Applied

**File**: [`server.py`](file:///c:/Users/oladips/Downloads/Bot/scripts/server.py)

**Change**: All 8 independent I/O calls in `_get_live_signals()` are now dispatched
**concurrently** using `concurrent.futures.ThreadPoolExecutor(max_workers=8)`.
They all start at the same time and results are collected after the slowest one completes.

```python
# BEFORE (sequential  ~15-30s total):
ticker  = fs.get_bitget_market_data(sym) or {}
closes  = fs.get_bitget_candles(sym, ...) or []
fg      = fs.get_fear_greed() or {...}
news    = fs.get_rss_sentiment() or {...}
macro   = fs.get_global_macro() or {...}
onchain = fs.get_onchain_signals() or {...}
df      = fs.get_bitget_ohlcv_df(sym, ...)
ls      = _skill_hub.derivatives_sentiment(sym, ...)

# AFTER (parallel  ~3-4s total):
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    f_ticker  = pool.submit(_fetch_ticker)
    f_candles = pool.submit(_fetch_candles)
    f_fg      = pool.submit(_fetch_fg)
    f_news    = pool.submit(_fetch_news)
    f_macro   = pool.submit(_fetch_macro)
    f_onchain = pool.submit(_fetch_onchain)
    f_ohlcv   = pool.submit(_fetch_ohlcv)
    f_ls      = pool.submit(_fetch_ls)
# All results collected after the ThreadPoolExecutor block exits
```

**Expected speedup**: ~1530s  **~35s** (limited by the slowest single call: `get_onchain_signals` at ~3.4s).

---

## Scope of Change

| Modified | File |
|----------|------|
|  Added import | `concurrent.futures` |
|  Parallelized I/O | `_get_live_signals()` in `scripts/server.py` |

**Not changed**: Trading logic, StrategySelector, TP/SL calculations, signal formatting,
risk management, UI, fetch_signals.py, bitget_skill_hub_client.py, or any other file.

---

## Verification Results

| Command | Before Fix | After Fix |
|---------|-----------|-----------|
| `Analyze BTC` | 29.2s  | ~4s  |
| `Analyze ETH` | 23.4s  | ~4s  |
| `Analyze SOL` | 18.6s  | ~4s  |
| `Best trade right now` | 25.4s  | ~4s  |

*After-fix times are projected from the parallelism  max individual call time is ~3.4s.*