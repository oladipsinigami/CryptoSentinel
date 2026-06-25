#!/usr/bin/env python3
"""
Dashboard Server — CryptoSentinel AI Trading Agent
Serves the web dashboard static assets and provides JSON API endpoints
for portfolio state and trade logs.
"""

import http.server
import socketserver
import json
import os
import csv
import subprocess
import sys
import math
import re
import concurrent.futures
import time
from typing import List, Optional, Tuple
# Ensure utils package can be imported by adding project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from urllib.parse import parse_qs
from datetime import datetime, timezone
import logging
from utils.fallback_signal import generate_fallback_signal
from utils import symbol_extraction_logger as selog
from utils.price_validator import validate_price
from utils.price_fallback import get_fallback_price
from utils.price_cache_manager import set_price_cache
from utils.error_handler import handle_errors, ErrorHandlerContext

def clean_nan_values(data):
    """Recursively replace float NaN/Inf with None so JSON serialization is valid in standard JS."""
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(x) for x in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
    return data

PORT = int(os.environ.get("PORT", 8000))

def get_workspace_dir():
    """Determine the project root (workspace) directory.
    Works when the server is launched from the top-level 'scripts' directory.
    Checks if a sibling 'web' folder exists in the parent directory; if so, returns the parent as the workspace.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)
    # If the parent directory contains the 'web' folder, it's the project root
    if os.path.isdir(os.path.join(parent, "web")):
        return parent
    # Fallback to script_dir (covers cases where server resides directly in the project root)
    return script_dir

WORKSPACE_DIR = get_workspace_dir()
WEB_DIR = os.path.join(WORKSPACE_DIR, "web")
STATE_FILE = os.path.join(WORKSPACE_DIR, "portfolio_state.json")
LOG_FILE = os.path.join(WORKSPACE_DIR, "backtest_log.csv")
SCAN_FILE = os.path.join(WORKSPACE_DIR, "market_scan.json")
NL_LOG = os.path.join(WORKSPACE_DIR, "web_nl.log")  # simple audit of web commands

try:
    # Add utils and scripts directories for custom imports
    sys.path.insert(0, os.path.join(WORKSPACE_DIR, "utils"))
    sys.path.insert(1, os.path.join(WORKSPACE_DIR, "scripts"))
    import fetch_signals as fs
    from bitget_skill_hub_client import BitgetSkillHubClient
    from strategy_framework import StrategySelector
    _PERCEPTION_AVAILABLE = True
    _skill_hub = BitgetSkillHubClient(verbose=False)
except Exception as _e:
    _PERCEPTION_AVAILABLE = False
    fs = None
    _skill_hub = None
    _import_err = str(_e)


def _get_python_executable():
    """Return the best python executable to use for child scripts.
    Prefers the exact interpreter running the server (most reliable across shells).
    Falls back to common launcher names.
    This fixes 'py: command not found' in Git Bash / WSL / other bash-on-Windows environments.
    """
    # 1. Best: the interpreter that is currently running this server process
    if sys.executable and os.path.isfile(sys.executable):
        try:
            # Quick sanity check
            res = subprocess.run([sys.executable, "--version"], capture_output=True, timeout=3)
            if res.returncode == 0:
                return sys.executable
        except Exception:
            pass

    # 2. Common names (works in most terminals)
    if sys.platform.startswith("win"):
        candidates = ["py", "python", "python3", "python.exe"]
    else:
        candidates = ["python3", "python"]

    for cand in candidates:
        try:
            res = subprocess.run([cand, "--version"], capture_output=True, timeout=4)
            if res.returncode == 0:
                return cand
        except Exception:
            continue

    # 3. Last resort — let the OS figure it out
    return "python"


def _run_py_script(args, description=""):
    """Run a python script robustly (handles py/python/python3 differences on Windows shells)."""
    python_cmd = _get_python_executable()
    cmd = [python_cmd] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=WORKSPACE_DIR,
            timeout=120  # generous for scans/candles
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out (still running in background if applicable)."
    except Exception as e:
        return False, "", str(e)


# Simple TTL cache for slow-changing perception data (fear&greed, news, macro, onchain, LS)
# These don't change every second, so caching dramatically reduces latency for repeated NL queries.
_PERCEPTION_CACHE = {}
_CACHE_TTL = 90  # seconds

def _get_cached(key, fetch_func):
    now = time.time()
    if key in _PERCEPTION_CACHE:
        ts, val = _PERCEPTION_CACHE[key]
        if now - ts < _CACHE_TTL:
            return val
    val = fetch_func()
    _PERCEPTION_CACHE[key] = (now, val)
    return val


# =============================================================================
# RICH PERCEPTION HELPERS - so the chat can actually "give signals" and reason
# =============================================================================

def _get_live_signals(symbol="BTCUSDT", style=None, strategies=None):
    """Return a rich, human-readable signal summary using direct imports + MCP.
    This is what powers "give me signals", "analyze BTC", etc.
    Very defensive so it almost always returns something useful.

    Parameters
    ----------
    strategies : list[str] | None
        Optional list of strategy IDs (keys of STRATEGY_ID_TO_NAME).  When
        provided, the StrategySelector is restricted to those strategies and
        uses unanimous-confirmation mode.  When *None*, the existing
        weighted-average over all 24 strategies is used.
    """
    sym = symbol.upper().replace("USDT", "") + "USDT"

    # If direct perception modules aren't available (wrong python env, missing pandas, etc.)
    # fall back to running the existing fetch script (which the user could run manually).
    if not _PERCEPTION_AVAILABLE or fs is None:
        print(f"[NL] Perception not available for {sym}, falling back to subprocess fetch_signals")
        ok, out, err = _run_py_script(["scripts/fetch_signals.py", "--asset", sym.replace("USDT",""), "--timeframe", "1h"])
        if ok and out:
            # Try to extract the JSON part from the output
            try:
                # The script prints JSON at the end
                lines = out.strip().splitlines()
                json_lines = [l for l in lines if l.strip().startswith("{") or '"aggregate_score"' in l]
                if json_lines:
                    # crude: take from first { to end
                    start = out.find("{")
                    if start != -1:
                        js = out[start:].strip()
                        # may have trailing text, cut at last }
                        end = js.rfind("}")
                        if end != -1:
                            js = js[:end+1]
                        data = json.loads(js)
                        return data, f"**{sym}** signals (via script fallback):\nAggregate: {data.get('aggregate_score')}\nDecision: {data.get('decision')}\n(Full details in latest_signals.json)"
            except Exception as parse_e:
                print(f"[NL] Fallback parse error: {parse_e}")
            return None, out[-800:] or "Fetched via script. Check latest_signals.json"
        return None, f"Could not fetch signals (subprocess failed: {err[:150] if err else 'no output'}). Try running `python scripts/fetch_signals.py --asset SOL` manually."

    try:
        # ── Run all independent I/O calls in parallel ──────────────────────────
        # This reduces total latency from the sequential sum (~15-30s) down to
        # approximately the slowest single call (~3-4s).
        def _fetch_ticker():      return fs.get_bitget_market_data(sym) or {}
        def _fetch_candles():     return fs.get_bitget_candles(sym, granularity="1h", limit=100) or []
        def _fetch_fg():          return _get_cached('fear_greed', lambda: fs.get_fear_greed() or {"value": 50, "label": "Neutral", "score": 0})
        def _fetch_news():        return _get_cached('news', lambda: fs.get_rss_sentiment() or {"score": 0})
        def _fetch_macro():       return _get_cached('macro', lambda: fs.get_global_macro() or {"score": 0})
        def _fetch_onchain():     return _get_cached('onchain', lambda: fs.get_onchain_signals() or {"score": 0.5})
        def _fetch_ohlcv():       return fs.get_bitget_ohlcv_df(sym, "1h", 100)
        def _fetch_ls():
            if not _skill_hub:
                return None
            def _do_ls():
                try:
                    return _skill_hub.derivatives_sentiment(sym, "long_short", "4h")
                except Exception as _e:
                    print(f"[NL] derivatives_sentiment extra failed: {_e}")
                    return None
            return _get_cached(f'ls_{sym}', _do_ls)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            f_ticker  = pool.submit(_fetch_ticker)
            f_candles = pool.submit(_fetch_candles)
            f_fg      = pool.submit(_fetch_fg)
            f_news    = pool.submit(_fetch_news)
            f_macro   = pool.submit(_fetch_macro)
            f_onchain = pool.submit(_fetch_onchain)
            f_ohlcv   = pool.submit(_fetch_ohlcv)
            f_ls      = pool.submit(_fetch_ls)

        # Collect results with per-call timeouts to guarantee the NL endpoint never hangs too long.
        # If a slow call times out, we fall back to safe defaults so the user gets a response quickly.
        try:
            ticker  = f_ticker.result(timeout=10)
        except concurrent.futures.TimeoutError:
            print("[NL] ticker fetch timed out, using empty")
            ticker = {}
        try:
            closes  = f_candles.result(timeout=10)
        except concurrent.futures.TimeoutError:
            print("[NL] candles fetch timed out, using empty")
            closes = []
        try:
            fg      = f_fg.result(timeout=10)
        except concurrent.futures.TimeoutError:
            print("[NL] fg fetch timed out, using default")
            fg = {"value": 50, "label": "Neutral", "score": 0}
        try:
            news    = f_news.result(timeout=10)
        except concurrent.futures.TimeoutError:
            print("[NL] news fetch timed out, using default")
            news = {"score": 0}
        try:
            macro   = f_macro.result(timeout=10)
        except concurrent.futures.TimeoutError:
            print("[NL] macro fetch timed out, using default")
            macro = {"score": 0}
        try:
            onchain = f_onchain.result(timeout=10)
        except concurrent.futures.TimeoutError:
            print("[NL] onchain fetch timed out, using default")
            onchain = {"score": 0.5}
        try:
            df_ohlcv = f_ohlcv.result(timeout=10)
        except concurrent.futures.TimeoutError:
            print("[NL] ohlcv fetch timed out, using empty df")
            try:
                import pandas as pd
                df_ohlcv = pd.DataFrame()
            except Exception:
                df_ohlcv = None
        try:
            ls_result = f_ls.result(timeout=10)
        except concurrent.futures.TimeoutError:
            print("[NL] ls fetch timed out, using None")
            ls_result = None

        # ── Price resolution ───────────────────────────────────────────────────
        raw_price = ticker.get("price", None)
        price = validate_price(sym, raw_price)
        if price is None:
            s_upper = sym.upper()
            is_major = any(coin in s_upper for coin in ["BTC", "ETH", "SOL"])
            if is_major:
                raise ValueError(f"Could not get reliable price data for {s_upper} right now")
            price = get_fallback_price(sym)
        else:
            set_price_cache(sym, price)

        # ── Technicals from candles ────────────────────────────────────────────
        tech = fs.compute_signals(closes) if len(closes) >= 30 else {"score": 0, "rsi": 50, "ema_cross": "neutral", "macd_hist": 0}

        # ── Build decision ─────────────────────────────────────────────────────
        raw = (tech.get("score", 0) * 1.3 + news.get("score", 0)*0.8 +
               fg.get("score", 0)*0.9 + macro.get("score", 0)*0.7 + onchain.get("score", 0)*0.6)
        norm = max(-10.0, min(10.0, raw))
        decision, conf = fs.get_decision(norm)

        # ── Strategy Intelligence Layer ────────────────────────────────────────
        strategy_intelligence = {}
        strategy_note = ""
        try:
            if df_ohlcv is not None and not df_ohlcv.empty:
                # Build StrategySelector — use requested subset when specified
                confirmation_mode = "unanimous" if strategies and len(strategies) > 1 else "weighted"
                selector = StrategySelector(strategy_ids=strategies or None)
                strategy_intelligence = selector.select_best_trade(
                    df_ohlcv, style=style, confirmation_mode=confirmation_mode
                )
                if strategy_intelligence.get("strategy") and strategy_intelligence.get("strategy") != "None":
                    strat_label = strategy_intelligence['strategy']
                    strategy_note = (
                        f"**Strategy Layer**: {strat_label} "
                        f"({strategy_intelligence['decision']} - {strategy_intelligence['confidence']}) "
                        f"| Regime: {strategy_intelligence['regime']}"
                    )
                    if strategies:
                        # B3 FIX: show the actual strategy names requested by the user
                        from strategy_framework import STRATEGY_ID_TO_NAME
                        human_names = [STRATEGY_ID_TO_NAME.get(s, s) for s in strategies]
                        strategy_note += (
                            f" | Mode: Unanimous\n"
                            f"**Active Strategies**: {', '.join(human_names)}"
                        )
        except Exception as e:
            print(f"[NL] Strategy Selector error: {e}")

        # ── L/S ratio note from parallel result ───────────────────────────────
        mcp_note = ""
        if ls_result and isinstance(ls_result, dict):
            ratio = ls_result.get("longShortRatio") or ls_result.get("ratio") or ls_result.get("long_short_ratio")
            if ratio is None and isinstance(ls_result.get("list"), list) and ls_result["list"]:
                ratio = ls_result["list"][0].get("longShortRatio")
            if ratio:
                mcp_note = f" | L/S ratio (MCP): {float(ratio):.2f}"

        # Formatted response the chat can show
        lines = [
            f"**{sym} @ ${price:,.2f}** (24h: {ticker.get('change_24h', 0):+.2f}%)",
            f"Decision: **{decision}** ({conf}) | Aggregate: **{norm:+.2f}**",
            f"Technicals: RSI {tech.get('rsi', 50):.1f} ({tech.get('ema_cross', 'neutral')}) | Tech score {tech.get('score', 0):+.1f}",
            f"Fear & Greed: {fg.get('value', 50)} ({fg.get('label', 'Neutral')}) {fg.get('score', 0):+.1f}{mcp_note}",
            f"News: {news.get('score', 0):+.2f} | Macro: {macro.get('score', 0):+.1f} | On-chain: {onchain.get('score', 0):+.1f}",
        ]
        if strategy_note:
            lines.append(strategy_note)

        return {
            "symbol": sym,
            "price": price,
            "aggregate_score": round(norm, 2),
            "decision": decision,
            "confidence": conf,
            "technicals": tech,
            "fear_greed": fg,
            "news": news,
            "macro": macro,
            "onchain": onchain,
            "strategy_intelligence": strategy_intelligence,
        }, "\n".join(lines)

    except Exception as e:
        print(f"[NL] _get_live_signals error for {sym}: {e}")
        if isinstance(e, ValueError) and "reliable price data" in str(e):
            raise e
            
        s_upper = sym.upper()
        is_major = any(coin in s_upper for coin in ["BTC", "ETH", "SOL"])
        
        # Last ditch: return basic ticker info
        try:
            ticker = fs.get_bitget_market_data(sym) if fs else None
            price = ticker["price"] if ticker else None
            price = validate_price(sym, price)
            if price is None:
                raise ValueError("No valid price available")
            return {"symbol": sym, "price": price}, f"Basic data for {sym}: ${price:,.2f} (full perception failed: {str(e)[:80]})"
        except Exception as last_e:
            if is_major:
                raise ValueError(f"Could not get reliable price data for {s_upper} right now")
            # Generate fallback signal using safe fallback price
            fallback_price = get_fallback_price(sym)
            fallback_signal = generate_fallback_signal(sym, fallback_price)
            fallback_msg = f"[Fallback] Unable to fetch full live signals for {sym}: {e}. Using minimal data."
            return fallback_signal, fallback_msg


def _get_market_overview():
    """High-level view + top opportunities (uses scan if available)."""
    if os.path.exists(SCAN_FILE):
        try:
            with open(SCAN_FILE) as f:
                scan = json.load(f)
            if scan:
                top = sorted(scan, key=lambda x: abs(x.get("aggregate_score", 0)), reverse=True)[:5]
                lines = ["**Current Market Scan (top conviction):**"]
                for t in top:
                    lines.append(f"• {t['symbol']}: {t['aggregate_score']:+.2f} → {t.get('decision','?')} (vol ${t.get('volume_24h',0)/1e6:.1f}M)")
                return {"scan": top}, "\n".join(lines)
        except Exception:
            pass

    # Fallback to single BTC view
    data, txt = _get_live_signals("BTCUSDT")
    return data, "Market overview (BTC as proxy):\n" + (txt or "No data")


# Full coin name → ticker mapping for natural language queries
COIN_NAME_MAP = {
    "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL", "RIPPLE": "XRP",
    "DOGECOIN": "DOGE", "AVALANCHE": "AVAX", "CHAINLINK": "LINK", "CARDANO": "ADA",
    "POLKADOT": "DOT", "POLYGON": "MATIC", "BINANCE": "BNB", "LITECOIN": "LTC",
    "COSMOS": "ATOM", "NEAR": "NEAR", "SUI": "SUI", "APTOS": "APT",
    "OPTIMISM": "OP", "ARBITRUM": "ARB", "UNISWAP": "UNI", "AAVE": "AAVE",
    "PEPE": "PEPE", "SHIBA": "SHIB", "SHIBAINUE": "SHIB", "TRON": "TRX",
    "STELLAR": "XLM", "MONERO": "XMR", "FILECOIN": "FIL", "HEDERA": "HBAR",
    "HYPE": "HYPE", "HYPERLIQUID": "HYPE"
}

# ---------------------------------------------------------------------------
# STRATEGY_KEYWORD_MAP
# Maps natural-language phrases (lower-case) to canonical strategy IDs.
# IDs must be keys in strategy_framework.STRATEGY_ID_TO_NAME.
# Order matters: longer / more-specific phrases should come first.
# ---------------------------------------------------------------------------
STRATEGY_KEYWORD_MAP: List[Tuple[str, str]] = [
    # Trend Following
    ("exponential moving average", "EMACross"),
    ("ema cross",                  "EMACross"),
    ("ema",                        "EMACross"),
    ("simple moving average",      "SMACross"),
    ("sma cross",                  "SMACross"),
    ("sma",                        "SMACross"),
    ("ma cross",                   "SMACross"),
    ("supertrend",                 "Supertrend"),
    ("trendline",                  "Supertrend"),
    ("trend line",                 "Supertrend"),
    ("adx trend",                  "ADXTrend"),
    ("adx",                        "ADXTrend"),
    ("directional index",          "ADXTrend"),
    # Momentum
    ("moving average convergence divergence", "MACDMomentum"),
    ("macd",                       "MACDMomentum"),
    ("relative strength index",    "RSIMomentum"),
    ("rsi momentum",               "RSIMomentum"),
    ("stochastic",                 "StochasticMomentum"),
    ("stoch",                      "StochasticMomentum"),
    ("rate of change",             "ROCMomentum"),
    ("roc",                        "ROCMomentum"),
    # Mean Reversion
    ("bollinger band reversion",   "BollingerReversion"),
    ("bollinger reversion",        "BollingerReversion"),
    ("mean reversion",             "BollingerReversion"),
    ("rsi reversion",              "RSIReversion"),
    ("z-score reversion",          "ZScoreReversion"),
    ("zscore",                     "ZScoreReversion"),
    ("z score",                    "ZScoreReversion"),
    # Breakout
    ("donchian",                   "DonchianBreakout"),
    ("channel breakout",           "DonchianBreakout"),
    ("atr breakout",               "ATRBreakout"),
    ("range breakout",             "RangeBreakout"),
    ("consolidation breakout",     "RangeBreakout"),
    # Volatility
    ("bollinger squeeze",          "BollingerSqueeze"),
    ("squeeze",                    "BollingerSqueeze"),
    ("keltner",                    "KeltnerExpansion"),
    ("atr expansion",              "ATRExpansion"),
    ("volatility expansion",       "ATRExpansion"),
    # Volume
    ("on balance volume",          "OBVVolume"),
    ("obv",                        "OBVVolume"),
    ("vwap",                       "VWAPCross"),
    ("volume weighted",            "VWAPCross"),
    ("volume spike",               "VolumeSpike"),
    # Smart Money Concepts
    ("order block",                "OrderBlocks"),
    ("fair value gap",             "FairValueGap"),
    ("fvg",                        "FairValueGap"),
    ("break of structure",         "BOSCHOCH"),
    ("choch",                      "BOSCHOCH"),
    ("bos",                        "BOSCHOCH"),
    ("liquidity sweep",            "LiquiditySweep"),
    ("liquidity",                  "LiquiditySweep"),
]


def _extract_strategies(text: str) -> List[str]:
    """Scan *text* for strategy keyword mentions and return a deduplicated
    list of strategy IDs.  Returns an empty list if no strategies are found.
    """
    t = text.lower()
    found: List[str] = []
    seen: set = set()
    for phrase, sid in STRATEGY_KEYWORD_MAP:
        if phrase in t and sid not in seen:
            found.append(sid)
            seen.add(sid)
    if found:
        print(f"[NL] Detected strategy IDs from text: {found}")
    return found


def _detect_trade_style(text: str) -> Optional[str]:
    """Detect trading style (scalping, swing, day_trading) from user query."""
    t = text.lower()
    if any(w in t for w in ["scalping", "scalp", "quick trade", "quick scalp", "fast trade"]):
        return "scalping"
    if any(w in t for w in ["swing", "swing trade", "swing trading", "position"]):
        return "swing"
    if any(w in t for w in ["day trade", "day trading", "intraday"]):
        return "day_trading"
    return None

@handle_errors(default_return=None)
def _extract_symbol(text: str) -> Optional[str]:
    """Extract a trading symbol from user text, validating against Bitget symbols.
    Uses the new symbol_registry module for dynamic validation and caching.
    Supports: tickers (BTC, ETH), full names (ethereum, solana), slash pairs (BTC/USDT).
    """
    from utils import symbol_registry as sr
    from utils.symbol_registry import normalize_symbol
    # Extract candidates
    if not text:
        return None
        
    # Quick check: if the input is directly a symbol format like "sol", "sol/usdt"
    direct_norm = normalize_symbol(text)
    if direct_norm and sr.is_valid_symbol(direct_norm):
        selog.log_extraction_attempt(text, [text], direct_norm)
        return direct_norm
        
    # Logging will be performed after final symbol determination
    t = text.upper()

    # Check full coin names first (e.g. "ethereum", "solana", "chainlink")
    for coin_name, ticker in COIN_NAME_MAP.items():
        # Match as a whole word, case-insensitive (already upper)
        if re.search(r'\b' + coin_name + r'\b', t):
            sym = ticker + "USDT"
            if sr.is_valid_symbol(sym):
                selog.log_extraction_attempt(text, [coin_name], sym)
                return sym
    
    STOP_WORDS = {
        "USD", "USDT", "USDC", "THE", "AND", "FOR", "ON", "TO", "IN", "IS", "AT", "OF", "A", "AN",
        "WITH", "LEVERAGE", "GIVE", "SIGNAL", "SIGNALS", "GET", "ME", "ANALYZE", "TRADE",
        "SOMETHING", "BIG", "COMING", "DETAILED", "BREAKDOWN", "INCLUDING", "FEAR", "GREED",
        "STRATEGY", "LAYER", "BREAK", "DOWN", "DETAIL", "FULL", "ANALYSIS", "LONG", "SHORT",
        "BUY", "SELL", "HOLD", "MARKET", "SENTIMENT", "RATIO", "RATIOS", "WARNING", "WARNINGS",
        "LOOK", "MY", "OPEN", "POSITIONS", "RISK", "SUGGEST", "WHAT", "SHOULD", "DO", "NEXT",
        "RESET", "ENTIRE", "PORTFOLIO", "CLEAN", "SLATE", "HOW", "AM", "I", "DOING", "OUR",
        "WE", "US", "YOU", "YOUR", "HE", "SHE", "IT", "THEY", "THIS", "THAT", "THESE", "THOSE",
        "SCALP", "SCALPING", "SWING", "POSITION", "DAY", "INTRADAY", "TRADE", "TRADING", "COINS", "COIN"
    }

    MAJOR_COINS = {
        "BTC", "ETH", "SOL", "XRP", "DOGE", "AVAX", "LINK", "ADA", "DOT", "MATIC", "BNB", 
        "LTC", "ATOM", "NEAR", "SUI", "APT", "OP", "ARB"
    }

    keyword_candidates = []
    other_candidates = []
    # Keyword pattern captures explicit mentions like "symbol BTC" or "coin ETH"
    keyword_pattern = r'(?:ON|FOR|ABOUT|SYMBOL|COIN|TICKER|ANALYZE|TRADE|SIGNAL[S]?|SCALP[ING]?|SWING)\s+(?:[A-Z]{2,8}\s+)?([A-Z]{2,8})'
    for m in re.findall(keyword_pattern, t):
        base = m.strip()
        if 2 <= len(base) <= 8 and base not in STOP_WORDS:
            keyword_candidates.append(base)
    # Suffixes like "BTC-USDT" or "ETHUSD"
    suffix_pattern = r'\b([A-Z]{2,8})[/-]?(USD|USDT|USDC)?\b'
    for m in re.findall(suffix_pattern, t):
        base = m[0] if isinstance(m, (list, tuple)) else m
        base = base.strip()
        if 2 <= len(base) <= 8 and base not in STOP_WORDS:
            other_candidates.append(base)
    # Fallback generic capital words
    if not keyword_candidates and not other_candidates:
        for m in re.findall(r'\b([A-Z]{2,8})\b', t):
            base = m.strip()
            if 2 <= len(base) <= 8 and base not in STOP_WORDS:
                other_candidates.append(base)
    
    candidates = keyword_candidates + other_candidates
    # Deduplicate while preserving order
    seen = set()
    candidates = [c for c in candidates if not (c in seen or seen.add(c))]
    
    # Sort candidates putting major priority coins first
    priority_candidates = [c for c in candidates if c in MAJOR_COINS]
    regular_candidates = [c for c in candidates if c not in MAJOR_COINS]
    final_candidates = priority_candidates + regular_candidates
    
    for base in final_candidates:
        base_upper = base.upper()
        if base_upper in ("BEST", "TOP", "STRONGEST"):
            selog.log_extraction_attempt(text, final_candidates, "BEST")
            return "BEST"
        sym = normalize_symbol(base_upper)
        if sym and sr.is_valid_symbol(sym):
            selog.log_extraction_attempt(text, final_candidates, sym)
            return sym
            
    selog.log_extraction_attempt(text, final_candidates, None)
    return None


def _parse_trade_intent(text: str) -> dict:  # noqa: C901
    """Parse intent, extracting action, style, symbol, use_best, and basic fields.
    Action is:
      - "close": for exiting positions
      - "execute_trade": for actual paper trading executions (replaces "trade")
      - "scan_best": for dynamic scans of the best opportunities
      - "signal": for market analysis / signal retrieval (default)
    """
    t = text.lower()
    style = _detect_trade_style(text)
    
    # 1. Determine action and side
    action = "signal"
    side = None
    
    # ── Detect scan-only intent first (BEFORE general trade-action detection) ──
    # Phrases like "best trades right now" are informational, not execution requests.
    SCAN_ONLY_PHRASES = [
        "right now", "today", "best trades", "top trades", "what should i",
        "what should I", "which coin", "which coins", "any good", "opportunities",
    ]
    is_scan_only_query = any(p in t for p in SCAN_ONLY_PHRASES)

    if any(w in t for w in ["close", "exit", "liquidate", "flatten"]):
        action = "close"
    # Detect trade/execute style requests (e.g. "scalp trade", "take a scalp trade", etc.)
    elif any(w in t for w in ["scalping trade", "scalp trade", "take a scalp", "take a scalping", "open a scalp", "open a scalping", "execute a scalp", "execute a scalping"]):
        action = "execute_trade"
        if any(w in t for w in ["long", "buy", "bullish"]):
            side = "LONG"
        elif any(w in t for w in ["short", "sell", "bearish"]):
            side = "SHORT"
    else:
        # Check if the user is asking for information, analysis, or signals
        # (e.g. "give me a signal", "what is", "analyze", "show me")
        is_info_seeking = any(w in t for w in ["give", "get", "show", "analyze", "analysis", "what", "outlook", "signal", "signals", "how", "explain"])
        
        has_trade_action = any(w in t for w in ["trade", "buy", "sell", "long", "short", "execute", "place", "open", "take"])
        
        # is_scan_only_query prevents informational phrases like "best trades right now"
        # from being classified as execution requests
        if has_trade_action and not is_info_seeking and not is_scan_only_query:
            action = "execute_trade"
            if any(w in t for w in ["long", "buy", "bullish"]):
                side = "LONG"
            elif any(w in t for w in ["short", "sell", "bearish"]):
                side = "SHORT"
        elif "trade for me" in t or "execute trade" in t:
            action = "execute_trade"
            
    # 2. Extract symbol
    symbol = _extract_symbol(text)
    
    # 3. Determine if we should scan best opportunities autonomously
    use_best = False
    if any(kw in t for kw in ["or other coins", "best", "strongest", "most profitable", "autonomous", "the best one", "best coin"]):
        use_best = True
    # Only treat "top" as scan trigger when used as an adjective ("top coin", "top opportunity").
    # Avoid matching "top" inside words that appear in portfolio/help phrases.
    if re.search(r'\btop\b', t) and not is_scan_only_query:
        use_best = True
        
    # If a style is requested but NO symbol was explicitly mentioned, trigger a best scan
    if style and not symbol:
        use_best = True
        
    # If "or other coins" is mentioned, prioritize best/autonomous scan
    if "or other coins" in t:
        use_best = True
        
    # If symbol extracted is BEST, set use_best to True
    if symbol == "BEST":
        use_best = True
        symbol = None
        
    # Normalize action for BEST/autonomous scan mode
    if use_best and action not in ("close", "execute_trade"):
        action = "scan_best"
        
    # Extract amount
    amount = None
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:usdt|usd|\$|dollars)', t)
    if m:
        amount = float(m.group(1))

    # Extract leverage
    leverage = None
    m_lev = re.search(r'\b(?:leverage\s*(?:of\s*)?|lev\s*|x\s*)?(\d+)\s*x\b|\b(?:leverage\s*(?:of\s*)?|lev\s*:?)\s*(\d+)\b', t)
    if m_lev:
        lev_val = int(m_lev.group(1) or m_lev.group(2))
        leverage = max(1, min(10, lev_val))
        
    # Extract explicitly-mentioned strategies
    strategies = _extract_strategies(text)

    # ── B7: detect if an unknown coin was mentioned ──────────────────────────
    # We flag this so handle_nl_command can warn the user.
    symbol_warning = ""
    if symbol is None and not use_best:
        # Heuristic: look for standalone uppercase 2-8 char words that aren't
        # strategy/trading keywords — they might be coin names we didn't recognise.
        _non_coin_words = {
            "EMA", "SMA", "RSI", "MACD", "ADX", "ATR", "OBV", "VWAP", "ROC",
            "BOS", "FVG", "SMC", "TP", "SL", "USDT", "USD", "LONG", "SHORT",
            "BUY", "SELL", "HOLD", "BEST", "TOP", "SIGNAL", "TRADE", "HELP",
        }
        _candidates = re.findall(r'\b([A-Z][A-Z0-9]{1,7})\b', text)
        _mystery = [c for c in _candidates if c not in _non_coin_words]
        if _mystery:
            symbol_warning = f"\n\n⚠️ '{_mystery[0]}' is not a recognised symbol on Bitget — analysis defaulted to BTC."

    return {
        "action": action,
        "side": side,
        "style": style,
        "symbol": symbol if not use_best else None,
        "use_best": use_best,
        "amount": amount,
        "leverage": leverage,
        "strategies": strategies,
        "symbol_warning": symbol_warning,
        "original_text": text
    }


def _execute_intelligent_trade(intent: dict, user_text: str, resolved_prices: Optional[dict] = None):
    """Execute a trade based on parsed intent. Uses full agent_cycle when possible
    for risk rules, or targeted trade when user specified a coin.
    """
    intent_action = str(intent.get("action")).upper()
    if intent_action == "CLOSE" or intent_action == "CLOSE_TRADE":
        # Close everything or specific
        sym = intent.get("symbol", "").replace("USDT", "")
        if sym and sym != "BEST":
            ok, out, err = _run_py_script(["scripts/sim_trader.py", "update", "--asset", sym, "--current_price", "0"], "close trigger")
            return f"Attempted to close positions in {sym}. Check dashboard."
        else:
            # Best effort: run update on common assets
            for s in ["BTC", "ETH", "SOL"]:
                _run_py_script(["scripts/sim_trader.py", "update", "--asset", s, "--current_price", "0"])
            return "Closed / updated open positions across major assets."

    # Full autonomous if user said "trade for me", "best", or no specific coin
    if intent.get("symbol") == "BEST" or intent.get("action") == "AUTONOMOUS" or "best" in user_text.lower() or intent.get("use_best"):
        lev = intent.get("leverage") or 3
        ok, out, err = _run_py_script(["scripts/agent_cycle.py", "--scan", "--leverage", str(lev)], "Autonomous trade the best")
        msg = "🧠 Executed full autonomous multi-coin cycle (scanned, ranked, traded top conviction under risk rules).\n"
        if ok:
            # Parse lines from output, omitting only the ASCII dashboard box lines
            exec_lines = []
            if out:
                for line in out.splitlines():
                    l_strip = line.strip()
                    if not l_strip:
                        continue
                    # Skip separators or ASCII art dashboard box borders/lines
                    if any(c in l_strip for c in "║═╔╗╚╝╠╣╦╩╬█"):
                        continue
                    exec_lines.append(l_strip)
            if exec_lines:
                msg += "\n" + "\n".join(exec_lines)
            else:
                msg += "\nNo logs were returned from the trade cycle."
        else:
            msg += f"\nSubprocess error: {err[:200]}"
        return msg

    # Targeted trade for a specific symbol
    symbol = intent.get("symbol") or "BTCUSDT"
    amount = intent.get("amount") or 100.0

    if resolved_prices:
        # B5 FIX: user's explicitly-stated side (LONG/SHORT) always wins over
        # the strategy-layer direction. Strategy direction is only used as a
        # fallback when the user didn't specify a side.
        user_side = intent.get("side")
        strat_direction = resolved_prices.get("direction", "LONG")
        side = user_side if user_side else strat_direction
        price = resolved_prices.get("entry_price")
        sl = resolved_prices.get("stop_loss")
        tp = resolved_prices.get("take_profit")
        lev = intent.get("leverage") or resolved_prices.get("suggested_leverage") or 3
    else:
        side = intent.get("side") or "LONG"
        lev = intent.get("leverage") or 3
        # Get current price
        ticker = fs.get_bitget_market_data(symbol) if fs else {}
        price = float(ticker.get("price", 60000.0)) if ticker else 60000.0

        # Dynamic SL/TP using the project's logic (simplified)
        chg = ticker.get("change_24h", 0) if ticker else 0
        sl_pct = 0.02
        if "BTC" in symbol: sl_pct = 0.015 if abs(chg)<2 else 0.03
        elif "ETH" in symbol: sl_pct = 0.02
        else: sl_pct = 0.04

        if side == "LONG":
            sl = round(price * (1 - sl_pct), 2)
            tp = round(price * (1 + sl_pct * 2), 2)
        else:
            sl = round(price * (1 + sl_pct), 2)
            tp = round(price * (1 - sl_pct * 2), 2)

    action = "LONG" if side == "LONG" else "SHORT"

    ok, out, err = _run_py_script([
        "scripts/sim_trader.py", "trade",
        "--action", action,
        "--asset", symbol.replace("USDT", ""),
        "--amount_usdt", str(round(amount, 2)),
        "--entry_price", str(price),
        "--stop_loss", str(sl),
        "--take_profit", str(tp),
        "--leverage", str(lev),
        "--signal_score", "0",
        "--confidence", "MEDIUM",
        "--reasoning", f"Chat command: {user_text[:80]}"
    ], f"Targeted {action} {symbol}")

    if ok:
        # B6 FIX: round SL/TP to avoid ugly float precision in the confirmation message
        sl_fmt = f"${float(sl):,.4f}" if float(sl) < 1 else (f"${float(sl):,.2f}" if float(sl) < 1000 else f"${float(sl):,.0f}")
        tp_fmt = f"${float(tp):,.4f}" if float(tp) < 1 else (f"${float(tp):,.2f}" if float(tp) < 1000 else f"${float(tp):,.0f}")
        return f"✅ Executed {action} {symbol} ${amount:.0f} @ ${price:,.2f} | SL {sl_fmt} TP {tp_fmt} ({lev}x)\nReason: {user_text}"
    else:
        return f"Trade attempt failed: {err[:150] or 'see logs'}"


def _generate_formatted_signal(sym, style=None, strategies=None):
    """
    Helper function to unify signal generation and formatting so both signal-only
    and trade execution paths display consistent, premium metrics.
    Returns: (dict_of_signal_data, formatted_string_message)

    Parameters
    ----------
    strategies : list[str] | None
        Optional strategy IDs to restrict the StrategySelector to.
    """
    try:
        data, msg = _get_live_signals(sym, style=style, strategies=strategies)
    except Exception as e:
        if "Could not get reliable price data" in str(e):
            coin_base = sym.replace("USDT", "")
            return None, f"I'm having trouble getting accurate live data for {coin_base} right now. Please try again in a moment or try BTC/ETH."
        raise e
        
    if not data:
        return None, "Unable to generate signal."
        
    # Determine direction (LONG / SHORT)
    strategy = data.get("strategy_intelligence", {}) or {}
    strat_decision = strategy.get("decision", "")
    if strat_decision:
        strat_dec_upper = str(strat_decision).upper()
        if "BUY" in strat_dec_upper or "LONG" in strat_dec_upper:
            direction = "LONG"
        elif "SELL" in strat_dec_upper or "SHORT" in strat_dec_upper:
            direction = "SHORT"
        else:
            direction = "LONG" if data.get("aggregate_score", 0.0) >= 0 else "SHORT"
    else:
        decision_upper = str(data.get("decision", "HOLD")).upper()
        if "BUY" in decision_upper or "LONG" in decision_upper:
            direction = "LONG"
        elif "SELL" in decision_upper or "SHORT" in decision_upper:
            direction = "SHORT"
        else:
            direction = "LONG" if data.get("aggregate_score", 0.0) >= 0 else "SHORT"

    entry_val = data.get("price")
    strat_name = strategy.get("strategy")
    strat_used = strat_name if (strat_name and strat_name != "None") else "Trend Following"

    # Get reasoning bullets
    reason_str = strategy.get("reasoning", "")
    if not reason_str:
        tech_data = data.get("technicals", {}) or {}
        fg_data = data.get("fear_greed", {}) or {}
        rsi = tech_data.get("rsi", 50)
        ema_cross = tech_data.get("ema_cross", "neutral")
        fg_val = fg_data.get("value", 50)
        
        reasons = []
        if direction == "LONG":
            if ema_cross == "bullish":
                reasons.append("Price above 200 EMA")
            else:
                reasons.append("Bullish technical structure")
            if rsi < 45:
                reasons.append("Bullish momentum")
            else:
                reasons.append("Buying pressure")
        else:
            if ema_cross == "bearish":
                reasons.append("Price below 200 EMA")
            else:
                reasons.append("Bearish technical structure")
            if rsi > 55:
                reasons.append("Bearish momentum")
            else:
                reasons.append("Selling pressure")
        reasons.append(f"Fear & Greed = {fg_val}")
        
        if style == "scalping":
            # Short-term enhancements
            reasons = [r + " (1h short-term)" if "EMA" in r or "structure" in r.lower() or "pressure" in r.lower() else r for r in reasons]
            reasons.insert(0, "Shorter-term 1h momentum alignment")
        elif style == "swing":
            reasons.insert(0, "Swing trend structure alignment")
            
        reason_display = "\n".join([f"• {r}" for r in reasons])
    else:
        parts = re.split(r'(?:\n|•|\*|;|\. )+', reason_str)
        bullets = [p.strip() for p in parts if p.strip()]
        if not bullets:
            bullets = [reason_str]
            
        if style == "scalping":
            bullets = [b + " (short-term)" if "EMA" in b or "Trend" in b or "momentum" in b.lower() or "breakout" in b.lower() else b for b in bullets]
            bullets.insert(0, "Shorter-term 1h momentum alignment")
        elif style == "swing":
            bullets.insert(0, "Swing trend structure alignment")
            
        reason_display = "\n".join([f"• {b}" for b in bullets])

    # TP/SL Percentages logic based on asset change & style
    chg = float(data.get("change_24h_pct", 0.0) or 0.0)
    strat_entry = strategy.get("entry_price")
    strat_sl = strategy.get("stop_loss")
    strat_tp = strategy.get("take_profit")
    
    sl_percent = 0.02
    if "BTC" in sym.upper():
        sl_percent = 0.015 if abs(chg) < 2.0 else 0.03
    elif "ETH" in sym.upper():
        sl_percent = 0.02
    else:
        sl_percent = 0.04
        
    # Adjust stop percentage based on style
    if style == "scalping":
        sl_percent *= 0.5
    elif style == "swing":
        sl_percent *= 1.5
        
    tp_percent = sl_percent * 2.0

    # Formatting prices or percentages
    entry_price = None
    if strat_entry and float(strat_entry) > 0:
        entry_price = float(strat_entry)
    elif entry_val and float(entry_val) > 0:
        entry_price = float(entry_val)

    if entry_price is not None:
        if entry_price >= 1000:
            entry_display = f"{entry_price:,.0f}"
        elif entry_price >= 1:
            entry_display = f"{entry_price:,.2f}"
        else:
            entry_display = f"{entry_price:,.4f}"
            
        if strat_entry and strat_sl and strat_tp:
            tp_price = float(strat_tp)
            sl_price = float(strat_sl)
        else:
            if direction == "SHORT":
                tp_price = entry_price * (1.0 - tp_percent)
                sl_price = entry_price * (1.0 + sl_percent)
            else:
                tp_price = entry_price * (1.0 + tp_percent)
                sl_price = entry_price * (1.0 - sl_percent)
                
        if tp_price >= 1000:
            tp_display = f"{tp_price:,.0f}"
        elif tp_price >= 1:
            tp_display = f"{tp_price:,.2f}"
        else:
            tp_display = f"{tp_price:,.4f}"
            
        if sl_price >= 1000:
            sl_display = f"{sl_price:,.0f}"
        elif sl_price >= 1:
            sl_display = f"{sl_price:,.2f}"
        else:
            sl_display = f"{sl_price:,.4f}"
    else:
        entry_display = "Current Price"
        if direction == "SHORT":
            tp_display = f"-{tp_percent * 100:.1f}%"
            sl_display = f"+{sl_percent * 100:.1f}%"
        else:
            tp_display = f"+{tp_percent * 100:.1f}%"
            sl_display = f"-{sl_percent * 100:.1f}%"
            
        price_val = entry_val or 1.0
        if direction == "SHORT":
            tp_price = price_val * (1.0 - tp_percent)
            sl_price = price_val * (1.0 + sl_percent)
        else:
            tp_price = price_val * (1.0 + tp_percent)
            sl_price = price_val * (1.0 - sl_percent)
        entry_price = price_val
            
        if tp_display.endswith(".0%"):
            tp_display = tp_display.replace(".0%", "%")
        if sl_display.endswith(".0%"):
            sl_display = sl_display.replace(".0%", "%")

    # Confidence & Risk Level
    conf_str = str(data.get("confidence", "LOW")).upper()
    if "HIGH" in conf_str:
        confidence_display = "82%"
        risk_level = "Medium"
    elif "MEDIUM" in conf_str:
        confidence_display = "65%"
        risk_level = "Medium"
    else:
        confidence_display = "35%"
        risk_level = "High"

    suggested_leverage = 10 if style == "scalping" else (3 if style == "swing" else 5)

    try:
        from scripts.llm_signal_reasoner import generate_signal_report
    except ModuleNotFoundError:
        from llm_signal_reasoner import generate_signal_report
    
    sentiment_data = {
        "fear_greed": data.get("fear_greed", {}),
        "news": data.get("news", {}),
        "macro": data.get("macro", {}),
        "onchain": data.get("onchain", {})
    }
    regime_data = strategy.get("regime", "")
    
    full_message = generate_signal_report(
        sym, 
        data.get("price"), 
        data.get("technicals", {}), 
        sentiment_data, 
        regime_data, 
        strategy
    )

    data["resolved_prices"] = {
        "direction": direction,
        "entry_price": entry_price,
        "take_profit": tp_price,
        "stop_loss": sl_price,
        "suggested_leverage": suggested_leverage
    }
    
    return data, full_message


def handle_nl_command(command_text: str):
    """
    Natural language interface using the improved _parse_trade_intent parser.
    """
    text = (command_text or "").strip()
    if not text:
        return {"ok": True, "message": "Please type something. Try 'Give me a signal on BTC'.", "action": "noop"}

    # Audit log
    try:
        with open(NL_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {command_text}\n")
    except Exception:
        pass

    # Parse intent
    intent = _parse_trade_intent(text)
    action = intent["action"]
    style = intent["style"]
    symbol = intent["symbol"]
    use_best = intent["use_best"]
    side = intent["side"]
    leverage = intent["leverage"]
    strategies = intent.get("strategies") or []
    tlower = text.lower()

    print(f"[NL] PARSED INTENT: {intent}")

    # B8 FIX: Check help BEFORE action routing so it isn't consumed by signal fallback
    if tlower in ("help", "?") or "what can you" in tlower or "capabilities" in tlower or tlower.startswith("help "):
        return {
            "ok": True,
            "message": (
                "Here's what I can do:\n"
                "\u2022 'give me signals on BTC' or 'analyze ETH' \u2192 live signals (technicals + sentiment + fear&greed)\n"
                "\u2022 'long BTC 100 usdt 3x' / 'short ETH 5x' \u2192 paper trade execution\n"
                "\u2022 'trade for me' / 'scan the market' \u2192 autonomous scan + best opportunity\n"
                "\u2022 'go long SOL using supertrend and MACD 4x' \u2192 specific strategy combination (unanimous mode)\n"
                "\u2022 'close my positions' / 'exit BTC' \u2192 close open trades\n"
                "\u2022 'portfolio' / 'show portfolio' \u2192 balance, PnL, open positions\n"
                "\u2022 'run a backtest' \u2192 historical strategy performance\n"
                "\u2022 'reset the portfolio' \u2192 start fresh with $1000\n\n"
                "Speak naturally \u2014 I understand symbols, amounts, leverage, styles (scalping/swing) and 24 strategy names."
            ),
            "action": "help"
        }

    # 1. CLOSE action
    if action == "close":
        result = _execute_intelligent_trade(intent, text)
        return {"ok": True, "message": result, "action": "close"}

    # 2. SCAN_BEST action
    if action == "scan_best":
        # B1 FIX: if the phrase is clearly informational/scan-only, skip straight to overview
        # regardless of other words (e.g. "best trades right now", "top opportunities today")
        _scan_phrases = ["right now", "today", "best trades", "top trades", "opportunities",
                         "any good", "which coin", "which coins", "what should i"]
        force_overview = any(p in tlower for p in _scan_phrases)
        is_execution = (
            not force_overview and
            any(w in tlower for w in ["trade for me", "execute", "place", "buy", "sell", "long", "short"])
            and not any(w in tlower for w in ["give me", "get me", "show me", "what is", "analyze", "analysis"])
        )
        if is_execution:
            if style == "scalping" and leverage is None:
                leverage = 10
                intent["leverage"] = 10
            if leverage is None:
                return {
                    "ok": False,
                    "message": "⚠️ Leverage was not specified. What leverage would you like to use? Please specify the leverage (e.g. 3x, 5x, 10x) to complete this trade.",
                    "action": "prompt_leverage"
                }
            result = _execute_intelligent_trade(intent, text)
            return {"ok": True, "message": result, "action": "scan_trade"}
        else:
            # Simple overview / scan overview
            data, msg = _get_market_overview()
            return {"ok": True, "message": msg, "action": "overview", "data": data}

    # 3. execute_trade action
    if action == "execute_trade":
        if style == "scalping" and leverage is None:
            leverage = 10
            intent["leverage"] = 10
            
        if leverage is None:
            return {
                "ok": False,
                "message": "Please specify leverage (e.g. 3x, 5x, 10x) to execute this trade. Example: 'long BTC 3x'",
                "action": "prompt_leverage"
            }
            
        if use_best:
            result = _execute_intelligent_trade(intent, text)
            return {"ok": True, "message": result, "action": "scan_trade"}
        else:
            sym = symbol if symbol else "BTCUSDT"
            # B7 FIX: if the user mentioned a coin that wasn't found in the symbol registry,
            # warn them clearly instead of silently defaulting to BTC.
            if not symbol:
                sym_warn = f"\u26a0\ufe0f No recognised coin was found in your message \u2014 defaulting to **{sym}**.\n\n"
            else:
                sym_warn = ""
            # 1. Generate signal first (with strategy filter if requested)
            data, sig_msg = _generate_formatted_signal(sym, style=style, strategies=strategies or None)
            if not data:
                return {
                    "ok": False,
                    "message": sig_msg,
                    "action": "signals"
                }
            # B4 FIX: if strategy layer says HOLD but user explicitly stated a direction,
            # warn them but still execute. If neither the strategy nor user has a clear
            # directional view, block the trade and explain why.
            strat_intel = data.get("strategy_intelligence", {})
            strat_decision = strat_intel.get("decision", "")
            is_strat_hold = "HOLD" in str(strat_decision).upper()
            user_has_side = bool(intent.get("side"))

            if is_strat_hold and not user_has_side:
                # No user direction AND strategy says HOLD → refuse trade
                hold_reason = strat_intel.get("reasoning", strat_decision)
                return {
                    "ok": False,
                    "message": (
                        f"{sig_msg}\n\n"
                        f"\u26a0\ufe0f **Trade blocked — strategy signals HOLD.**\n"
                        f"Reason: {hold_reason[:200]}\n"
                        "No position was opened. Specify a direction ('long' or 'short') to override, "
                        "or wait for a clearer signal."
                    ),
                    "action": "hold_blocked"
                }

            hold_override_note = ""
            if is_strat_hold and user_has_side:
                # User explicitly gave direction — execute but warn
                hold_override_note = (
                    f"\n\n\u26a0\ufe0f Strategy layer signalled HOLD (no confirmation from {strategies or 'all strategies'}), "
                    f"but executing per your explicit {intent['side']} instruction."
                )

            # 2. Execute trade using signal resolved prices
            trade_confirm = _execute_intelligent_trade(intent, text, resolved_prices=data.get("resolved_prices"))

            combined_message = f"{sym_warn}{sig_msg}\n\n--------------------------------------\n\n{trade_confirm}{hold_override_note}"
            
            state = {}
            try:
                with open(STATE_FILE) as f:
                    state = json.load(f)
            except Exception:
                pass
                
            return {
                "ok": True,
                "message": combined_message,
                "action": "trade",
                "state": state
            }

    # === KEYWORD-TRIGGERED HANDLERS (must run BEFORE the generic signal dispatch) ===
    # These handle words like 'portfolio', 'help', 'scan', 'reset', 'backtest' that
    # would otherwise be silently consumed by the signal action below.

    # B2 FIX: portfolio — expanded keyword list + moved before signal dispatch
    if any(kw in tlower for kw in [
        "portfolio", "balance", "pnl", "status", "how am i", "how are we",
        "open position", "my position", "my money", "my trades", "my balance",
        "current balance", "what are my", "show portfolio", "view portfolio",
        "show my portfolio", "check portfolio", "my portfolio",
    ]):
        try:
            with open(STATE_FILE) as f:
                st = json.load(f)
            total = st.get("balance", 0) + sum(p.get("amount_usdt", 0) for p in st.get("open_positions", []))
            msg = (f"**Portfolio**: ${st.get('balance', 0):,.2f} USDT | Total value ~${total:,.2f}\n"
                   f"Realized PnL: ${st.get('realized_pnl', 0):+,.2f} | Trades: {st.get('total_trades', 0)} "
                   f"(Win rate ~{ (st.get('winning_trades',0)/max(1,st.get('total_trades',1))*100):.0f}%)\n"
                   f"Open positions: {len(st.get('open_positions', []))}")
            return {"ok": True, "message": msg, "action": "status", "state": st}
        except Exception as e:
            return {"ok": True, "message": f"Could not read portfolio: {e}", "action": "status"}

    # Backtest
    if "backtest" in tlower or "test the strategy" in tlower:
        ok1, o1, _ = _run_py_script(["scripts/backtest.py"])
        ok2, o2, _ = _run_py_script(["scripts/generate_report.py"])
        return {
            "ok": ok1 and ok2,
            "message": "📊 Backtest + Excel report generated with current logic (fees, dynamic sizing, trend filter). Check report.xlsx and the equity chart on the dashboard.",
            "action": "backtest"
        }

    # B1 FIX: scan / top movers — now also catches 'best trades right now', 'opportunities'
    if ("scan" in tlower or "top conviction" in tlower or "top movers" in tlower
            or "top coins" in tlower or "best trades" in tlower
            or "opportunities" in tlower or "right now" in tlower
            or "today" in tlower) and "trade for me" not in tlower and action != "execute_trade":
        data, msg = _get_market_overview()
        return {"ok": True, "message": msg, "action": "overview", "data": data}

    # Reset
    if "reset" in tlower or "start over" in tlower or "clean" in tlower:
        try:
            initial = {"balance": 1000.0, "peak_balance": 1000.0, "open_positions": [],
                       "total_trades": 0, "winning_trades": 0, "realized_pnl": 0.0}
            with open(STATE_FILE, "w") as f: json.dump(initial, f, indent=2)
            return {"ok": True, "message": "🔄 Portfolio reset to $1000 clean slate.", "action": "reset"}
        except Exception as e:
            return {"ok": False, "message": f"Reset error: {e}", "action": "reset"}

    # 4. SIGNAL action (default analysis)
    if action == "signal":
        sym = symbol if symbol else "BTCUSDT"
        print(f"[NL] SIGNAL INTENT DETECTED → fetching for {sym} (style: {style}, strategies: {strategies})")
        data, msg = _generate_formatted_signal(sym, style=style, strategies=strategies or None)
        return {"ok": data is not None, "message": msg, "action": "signals", "signals": data}

    # === Smart fallback: try to be maximally helpful ===
    # If unclear, give current signals + offer to trade
    data, sigtxt = _get_live_signals("BTCUSDT")
    extra = "\n\nI didn't fully understand that. Try 'give me a signal on BTC', 'trade for me', or 'close everything'."
    return {
        "ok": True,
        "message": (sigtxt or "Here's the current market pulse:") + extra,
        "action": "fallback",
        "signals": data
    }

class DashboardAPIHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def translate_path(self, path):
        # Strip query params
        path = path.split('?')[0].split('#')[0]
        
        # If it is an API route, do not map to filesystem
        if path.startswith("/api/"):
            return path
            
        # Map root path to index.html
        if path == "/":
            return os.path.join(WEB_DIR, "index.html")
            
        # Serve static assets from the web folder
        return os.path.join(WEB_DIR, path.lstrip('/'))

    def do_GET(self):
        # Strip query parameters
        path_clean = self.path.split('?')[0].split('#')[0]

        if path_clean == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        elif path_clean == "/api/state":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            state = {
                "balance": 1000.0, 
                "peak_balance": 1000.0, 
                "open_positions": [], 
                "total_trades": 0, 
                "winning_trades": 0, 
                "realized_pnl": 0.0
            }
            if os.path.exists(STATE_FILE):
                try:
                    with open(STATE_FILE) as f:
                        state = json.load(f)
                except Exception as e:
                    print(f"Error reading state file: {e}")
            self.wfile.write(json.dumps(clean_nan_values(state)).encode())
            
        elif path_clean == "/api/logs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            trades = []
            if os.path.exists(LOG_FILE):
                try:
                    with open(LOG_FILE, "r") as f:
                        reader = csv.DictReader(f)
                        trades = list(reader)
                except Exception as e:
                    print(f"Error reading log file: {e}")
            self.wfile.write(json.dumps(clean_nan_values(trades)).encode())

        elif path_clean == "/api/scan":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            scan = []
            if os.path.exists(SCAN_FILE):
                try:
                    with open(SCAN_FILE) as f:
                        scan = json.load(f)
                except Exception as e:
                    print(f"Error reading scan file: {e}")
            self.wfile.write(json.dumps(clean_nan_values(scan)).encode())

        elif path_clean == "/api/signals":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # Parse ?symbol=BTCUSDT from query string
            from urllib.parse import urlparse, parse_qs as _pqs
            parsed = urlparse(self.path)
            qs = _pqs(parsed.query)
            sym = qs.get("symbol", ["BTCUSDT"])[0]
            data, msg = _get_live_signals(sym)
            result = {"symbol": sym, "message": msg, "data": data}
            self.wfile.write(json.dumps(clean_nan_values(result), default=str).encode())
            
        else:
            # Normal file serving
            file_path = self.translate_path(self.path)
            if not os.path.exists(file_path):
                # Fallback to index.html for SPA-style routing or missing files
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        path_clean = self.path.split('?')[0].split('#')[0]
        
        if path_clean == "/api/nl" or path_clean == "/api/command":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                payload = json.loads(body) if body else {}
                command = payload.get("command", "") or payload.get("text", "")
            except Exception as e:
                command = ""
                print(f"[NL] Failed to parse POST body: {e}")

            print(f"[NL] === /api/nl called with: {command[:120]} ===")
            result = handle_nl_command(command)
            print(f"[NL] === Response action={result.get('action')} ok={result.get('ok')} ===")

            # After a state-changing action, we can optionally embed the latest state
            if result.get("action") in ("scan_trade", "scan_only", "reset", "backtest", "refresh", "trade", "close"):
                try:
                    with open(STATE_FILE) as f:
                        result["state"] = json.load(f)
                except Exception:
                    result["state"] = None
                if result.get("action") in ("scan_trade", "scan_only") and os.path.exists(SCAN_FILE):
                    try:
                        with open(SCAN_FILE) as f:
                            result["scan_preview"] = json.load(f)[:5]
                    except Exception:
                        pass

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(clean_nan_values(result), default=str).encode())
            return

        # Default: method not allowed for other POSTs
        self.send_response(405)
        self.end_headers()
        self.wfile.write(b"Method Not Allowed")

    def do_OPTIONS(self):
        """Handle CORS preflight requests so browsers can POST to /api/nl."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

def run_server():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    handler = DashboardAPIHandler

    host = "0.0.0.0"
    print(f"[OK] CryptoSentinel Dashboard Server starting...")
    print(f"[*] Listening on http://{host}:{PORT}")
    print(f"[*] Workspace: {WORKSPACE_DIR}")
    print(f"[*] Serving web assets from: {WEB_DIR}")
    print(f"[*] Endpoints: /  |  /api/state  |  /api/logs  |  /api/nl (POST)  |  /health")
    print(f"[*] NEW: Full AI natural language interface is now available directly on the website!")
    
    with socketserver.ThreadingTCPServer((host, PORT), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dashboard server.")

if __name__ == "__main__":
    run_server()
