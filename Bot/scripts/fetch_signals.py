#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch Signals Script — CryptoSentinel AI Trading Agent
Collects market data, computes technical indicators, RSS news sentiment,
and macro metrics to generate a unified perception signal.

Perception Layer — Official Bitget AI Integration:
  Uses the SAME tools as the official Bitget Skill Hub skills:

  1. technical-analysis skill:
     -> Calls Bitget REST API: GET /api/v2/spot/market/candles (same URL, same format)
     -> Uses official kline_indicators.py (downloaded from Bitget Agent Hub GitHub)

  2. sentiment-analyst skill:
     -> Calls: sentiment_index() + derivatives_sentiment() on datahub.noxiaohao.com/mcp

  3. news-briefing skill:
     -> Calls: news_feed() on datahub.noxiaohao.com/mcp

  4. macro-analyst + market-intel skills:
     -> Calls: crypto_market() + tradfi_news() on datahub.noxiaohao.com/mcp

  All MCP calls go through BitgetSkillHubClient (bitget_skill_hub_client.py),
  which targets the same market-data MCP server referenced in every Skill Hub SKILL.md:
  <!-- MCP Server: https://datahub.noxiaohao.com/mcp -->
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
import argparse
import json
import urllib.request
import urllib.error
import re
import os
import subprocess
from datetime import datetime, timezone

# ─── Project root for consistent file paths ─────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)  # one level up from scripts/
if not os.path.isdir(os.path.join(ROOT_DIR, "web")):
    ROOT_DIR = os.getcwd()  # fallback if structure differs

# ─── Official Bitget Skill Hub MCP Client ────────────────────────────────────
# BitgetSkillHubClient calls the same market-data MCP server used by all 5
# Skill Hub SKILL.md files: <!-- MCP Server: https://datahub.noxiaohao.com/mcp -->
# It initializes a session via MCP Streamable HTTP (SSE protocol) and calls
# tools: sentiment_index, derivatives_sentiment, crypto_market, news_feed, tradfi_news
sys.path.insert(0, SCRIPT_DIR)
try:
    from bitget_skill_hub_client import BitgetSkillHubClient, _score_from_perception
    _SKILL_HUB_AVAILABLE = True
    _skill_hub_client = BitgetSkillHubClient(verbose=False)
except ImportError:
    _SKILL_HUB_AVAILABLE = False
    _skill_hub_client = None

try:
    import pandas as pd
    import numpy as np
    from kline_indicator_utils import IndicatorManager  # type: ignore
    _OFFICIAL_INDICATORS_AVAILABLE = True
except (ImportError, Exception):
    _OFFICIAL_INDICATORS_AVAILABLE = False

try:
    from strategy_framework import StrategySelector
    _STRATEGY_FRAMEWORK_AVAILABLE = True
except ImportError:
    _STRATEGY_FRAMEWORK_AVAILABLE = False

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
                if key and key not in os.environ:  # don't override already-set env vars
                    os.environ[key] = value
    except Exception:
        pass  # fail silently for safety

# Load local .env for convenience during testing (keys never committed thanks to .gitignore)
load_dotenv_if_exists()

def fetch_url(url, timeout=2):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None

def get_fear_greed():
    """
    sentiment-analyst skill equivalent.
    First tries the official Bitget Skill Hub MCP server (sentiment_index tool).
    Falls back to direct alternative.me API.
    """
    # --- Try official Bitget Skill Hub MCP server first ---
    if _SKILL_HUB_AVAILABLE and _skill_hub_client:
        result = _skill_hub_client.sentiment_index("current")
        if result:
            try:
                # Response shape varies: try multiple known fields
                value = None
                if isinstance(result, dict):
                    # Direct value field
                    value = result.get("value")
                    # Nested in data array (alternative.me format)
                    if value is None and "data" in result:
                        d = result["data"]
                        if isinstance(d, list) and d:
                            value = d[0].get("value")
                    # Already a score
                    if value is None:
                        value = result.get("score")
                if value is not None:
                    v = float(value)
                    if v <= 25:
                        score = +2.0
                        label = "Extreme Fear"
                    elif v <= 45:
                        score = +1.0
                        label = "Fear"
                    elif v <= 55:
                        score = 0.0
                        label = "Neutral"
                    elif v <= 75:
                        score = -1.0
                        label = "Greed"
                    else:
                        score = -2.0
                        label = "Extreme Greed"
                    return {"value": int(v), "label": label, "score": score,
                            "source": "bitget_skill_hub"}
            except Exception:
                pass

    # --- Fallback: direct alternative.me API ---
    data = fetch_url("https://api.alternative.me/fng/?limit=1")
    if data and data.get("data"):
        value = int(data["data"][0]["value"])
        if value <= 25:
            score = +2.0
            label = "Extreme Fear"
        elif value <= 45:
            score = +1.0
            label = "Fear"
        elif value <= 55:
            score = 0.0
            label = "Neutral"
        elif value <= 75:
            score = -1.0
            label = "Greed"
        else:
            score = -2.0
            label = "Extreme Greed"
        return {"value": value, "label": label, "score": score,
                "source": "alternative_me_direct"}
    return {"value": 50, "label": "Neutral", "score": 0.0, "source": "fallback"}

def get_coingecko_market_data(asset="bitcoin"):
    asset_lower = asset.lower()
    if "btc" in asset_lower:
        cg_id = "bitcoin"
    elif "eth" in asset_lower:
        cg_id = "ethereum"
    elif "sol" in asset_lower:
        cg_id = "solana"
    elif "xrp" in asset_lower:
        cg_id = "ripple"
    elif "doge" in asset_lower:
        cg_id = "dogecoin"
    elif "trx" in asset_lower:
        cg_id = "tron"
    else:
        cg_id = asset_lower.replace("usdt", "")
        
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true"
    data = fetch_url(url)
    if data and data.get(cg_id):
        return {
            "price": data[cg_id]["usd"],
            "change_24h": data[cg_id].get("usd_24h_change", 0.0),
            "volume_24h": data[cg_id].get("usd_24h_vol", 0.0)
        }
    return None

def _is_price_sane(symbol: str, price: float) -> bool:
    if price is None or price <= 0:
        return False
    s = symbol.upper()
    if "BTC" in s and price < 10000.0:
        return False
    if "ETH" in s and price < 200.0:
        return False
    if "SOL" in s and price < 2.0:
        return False
    return True

def get_bitget_market_data(symbol="BTCUSDT", use_bgc=False):
    """Fetch ticker data.
    - use_bgc=True: Actually call the official Bitget CLI (bgc via npx bitget-client) for maximum Bitget integration.
    - Default: Direct public Bitget API.
    - Validates price sanity and falls back to CoinGecko.
    """
    print(f"[get_bitget_market_data] Requesting symbol: {symbol}")
    
    ticker_res = None
    
    # 1. Fetch from Bitget
    if use_bgc:
        try:
            cmd = [
                "npx", "--yes", "bitget-client",
                "spot", "spot_get_ticker",
                "--symbol", symbol,
                "--pretty"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, shell=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                ticker_data = data.get("data", [])
                if isinstance(ticker_data, list) and len(ticker_data) > 0:
                    ticker = ticker_data[0]
                elif isinstance(ticker_data, dict):
                    ticker = ticker_data
                else:
                    ticker = {}
                ticker_res = {
                    "price": float(ticker.get("lastPr", 0.0)),
                    "change_24h": float(ticker.get("change24h", 0.0)) * 100.0,
                    "volume_24h": float(ticker.get("baseVolume", 0.0))
                }
            else:
                print(f"[bgc] Non-zero exit for ticker {symbol}. stderr: {result.stderr[:300]}")
        except Exception as e:
            print(f"[bgc] Failed to call official bitget-client for ticker {symbol} ({type(e).__name__}).")

    if not ticker_res:
        url = f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={symbol}"
        data = fetch_url(url)
        if data and data.get("data"):
            ticker = data["data"][0]
            ticker_res = {
                "price": float(ticker.get("lastPr", 0.0)),
                "change_24h": float(ticker.get("change24h", 0.0)) * 100.0,
                "volume_24h": float(ticker.get("baseVolume", 0.0))
            }

    # 2. Price Sanity Check
    if ticker_res and _is_price_sane(symbol, ticker_res.get("price")):
        print(f"[get_bitget_market_data] Sanity check passed for {symbol} | Price: {ticker_res['price']}")
        return ticker_res

    # 3. Fallback / Retry with CoinGecko
    bad_price = ticker_res.get("price") if ticker_res else "None"
    print(f"[SANITY FAILURE] Price sanity check failed for {symbol}: price={bad_price}. Attempting CoinGecko fallback...")
    
    cg_res = get_coingecko_market_data(symbol)
    if cg_res and _is_price_sane(symbol, cg_res.get("price")):
        print(f"[get_bitget_market_data] CoinGecko fallback check passed for {symbol} | Price: {cg_res['price']}")
        return cg_res

    print(f"[get_bitget_market_data] All data sources failed or returned bad prices for {symbol}.")
    return None

def get_bitget_authenticated_balance():
    """
    Optional: Fetch real account balance if BITGET keys are set in environment.
    This can be used to "sync" your sim portfolio with a Bitget sub-account
    or the simulated account provided by Agent Hub (the hackathon 'free funding').
    
    Requires: BITGET_API_KEY, BITGET_SECRET_KEY, BITGET_PASSPHRASE in env.
    Currently returns None (placeholder) because full authenticated calls
    need proper HMAC signing (see Agent Hub docs for examples or use bgc CLI).
    """
    api_key = os.environ.get("BITGET_API_KEY")
    if not api_key:
        return None
    
    # Placeholder: In a full implementation you would sign the request
    # and call account endpoints (e.g. /api/v2/spot/account/assets).
    # For now we just note that keys are detected for "free funding" test mode.
    print("[TEST] Bitget API keys detected in environment — you can extend this to sync real/sim account balances.")
    return {"note": "API keys present — add signing logic for full balance fetch from Bitget simulated sub-account"}

def get_global_macro():
    """
    macro-analyst skill equivalent.
    First tries the official Bitget Skill Hub MCP server (crypto_market tool).
    Falls back to direct CoinGecko API.
    """
    # --- Try official Bitget Skill Hub MCP server (crypto_market global) ---
    if _SKILL_HUB_AVAILABLE and _skill_hub_client:
        result = _skill_hub_client.crypto_market("global")
        if result and isinstance(result, dict):
            try:
                btc_dom = result.get("bitcoin_dominance_percentage") or result.get("btc_dominance") or 50.0
                mkt_change = result.get("market_cap_change_percentage_24h_usd") or \
                             result.get("market_cap_change_24h") or 0.0
                # Handle nested data
                if "data" in result:
                    d = result["data"]
                    if isinstance(d, dict):
                        btc_dom = d.get("market_cap_percentage", {}).get("btc", btc_dom)
                        mkt_change = d.get("market_cap_change_percentage_24h_usd", mkt_change)
                dom_score = 0.0 if float(btc_dom) > 55.0 else +1.0
                trend_score = +1.0 if float(mkt_change) > 2.0 else (-1.0 if float(mkt_change) < -2.0 else 0.0)
                return {
                    "btc_dominance": round(float(btc_dom), 1),
                    "mkt_cap_change_24h": round(float(mkt_change), 2),
                    "score": dom_score + trend_score,
                    "source": "bitget_skill_hub"
                }
            except Exception:
                pass

    # --- Fallback: direct CoinGecko API ---
    data = fetch_url("https://api.coingecko.com/api/v3/global")
    if data and data.get("data"):
        btc_dom = data["data"].get("market_cap_percentage", {}).get("btc", 50.0)
        mkt_cap_change = data["data"].get("market_cap_change_percentage_24h_usd", 0.0)
        dom_score = 0.0 if btc_dom > 55.0 else +1.0
        trend_score = +1.0 if mkt_cap_change > 2.0 else (-1.0 if mkt_cap_change < -2.0 else 0.0)
        return {
            "btc_dominance": round(btc_dom, 1),
            "mkt_cap_change_24h": round(mkt_cap_change, 2),
            "score": dom_score + trend_score,
            "source": "coingecko_direct"
        }
    return {"btc_dominance": 50.0, "mkt_cap_change_24h": 0.0, "score": 0.0, "source": "fallback"}

def get_rss_sentiment():
    """
    news-briefing skill equivalent.
    First tries the official Bitget Skill Hub MCP server (news_feed tool).
    Falls back to direct RSS scraping.
    """
    # --- Try official Bitget Skill Hub MCP server (news_feed tool) ---
    if _SKILL_HUB_AVAILABLE and _skill_hub_client:
        result = _skill_hub_client.news_feed(
            action="latest",
            feeds="cointelegraph,coindesk,decrypt,blockworks",
            limit=20
        )
        if result:
            try:
                bullish_kw = ["etf", "approval", "surge", "rally", "adopt", "gain", "bullish", "ath", "high", "upgrade"]
                bearish_kw = ["hack", "ban", "crash", "sec", "lawsuit", "fraud", "dump", "bearish", "decline", "fall"]
                # Extract titles from various response formats
                titles = []
                if isinstance(result, list):
                    for item in result:
                        if isinstance(item, dict):
                            titles.append(item.get("title", "") + " " + item.get("summary", ""))
                elif isinstance(result, dict):
                    items = result.get("items") or result.get("articles") or result.get("data") or []
                    for item in (items if isinstance(items, list) else []):
                        titles.append(str(item.get("title", "")) + " " + str(item.get("summary", "")))
                if titles:
                    bull = sum(1 for t in titles if any(w in t.lower() for w in bullish_kw))
                    bear = sum(1 for t in titles if any(w in t.lower() for w in bearish_kw))
                    total = bull + bear
                    score = (bull - bear) / total * 2.0 if total > 0 else 0.0
                    return {
                        "score": round(score, 2),
                        "bullish_count": bull,
                        "bearish_count": bear,
                        "total": len(titles),
                        "source": "bitget_skill_hub"
                    }
            except Exception:
                pass

    # --- Fallback: direct RSS scraping ---
    feeds = [
        "https://cointelegraph.com/rss",
        "https://coindesk.com/arc/outboundfeeds/rss/"
    ]
    bullish_keywords = ["etf", "approval", "surge", "rally", "adopt", "gain", "bullish", "ath", "high", "upgrade"]
    bearish_keywords = ["hack", "ban", "crash", "sec", "lawsuit", "fraud", "dump", "bearish", "decline", "fall", "liquidation"]
    titles = []
    for url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode('utf-8', errors='ignore')
                titles.extend(re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', html))
                titles.extend(re.findall(r'<title>(.*?)</title>', html))
        except Exception:
            continue
    if not titles:
        return {"score": 0.0, "bullish_count": 0, "bearish_count": 0, "total": 0, "source": "fallback"}
    bull_cnt = sum(1 for t in titles if any(w in t.lower() for w in bullish_keywords))
    bear_cnt = sum(1 for t in titles if any(w in t.lower() for w in bearish_keywords))
    total = bull_cnt + bear_cnt
    score = (bull_cnt - bear_cnt) / total * 2.0 if total > 0 else 0.0
    return {
        "score": round(score, 2),
        "bullish_count": bull_cnt,
        "bearish_count": bear_cnt,
        "total": len(titles),
        "source": "rss_direct"
    }

# --- Technical Indicator Calculations (Pure Python) ---
# This section implements core technical analysis aligned with the official
# Bitget Agent Hub "technical-analysis" Skill (one of the 5 Skill Hub analyst skills).
# Our implementation uses lightweight pure-Python (no pandas/numpy dependency)
# while computing the same key indicators the skill provides (RSI, MACD, Bollinger, EMA).
# It fetches directly from the same Bitget candle endpoint used by the skill.

def calculate_ema(prices, period):
    if len(prices) < period:
        return [prices[-1]] * len(prices)
    ema = []
    multiplier = 2 / (period + 1)
    sma = sum(prices[:period]) / period
    ema.append(sma)
    for i in range(period, len(prices)):
        val = (prices[i] - ema[-1]) * multiplier + ema[-1]
        ema.append(val)
    return [prices[0]] * (period - 1) + ema

def calculate_rsi(prices, period=14):
    if len(prices) <= period:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_macd(prices):
    if len(prices) < 26:
        return 0.0, 0.0, 0.0
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    signal_line = calculate_ema(macd_line, 9)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line[-1], signal_line[-1], histogram[-1]

def calculate_bollinger_bands(prices, period=20, num_std=2):
    if len(prices) < period:
        return prices[-1], prices[-1], prices[-1]
    sma = sum(prices[-period:]) / period
    variance = sum((x - sma) ** 2 for x in prices[-period:]) / period
    std_dev = variance ** 0.5
    upper = sma + num_std * std_dev
    lower = sma - num_std * std_dev
    return sma, upper, lower

def get_bitget_candles(symbol="BTCUSDT", granularity="1h", limit=100):
    url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}"
    data = fetch_url(url)
    if data and data.get("data"):
        # Bitget returns: [ts, open, high, low, close, volume, ...]
        closes = []
        for candle in data["data"]:
            closes.append(float(candle[4]))
        closes.reverse()  # Bitget might return newest first, reverse to historical order (oldest to newest)
        if closes:
            latest_price = closes[-1]
            if not _is_price_sane(symbol, latest_price):
                print(f"[SANITY FAILURE] get_bitget_candles price sanity check failed for {symbol}: price={latest_price} below floor limit!")
                return []
        return closes
    return []

def get_bitget_ohlcv_df(symbol="BTCUSDT", granularity="1h", limit=100):
    url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}"
    data = fetch_url(url)
    if data and data.get("data"):
        raw_candles = list(reversed(data["data"]))
        df = pd.DataFrame(raw_candles, columns=["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "extra"])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        if not df.empty:
            latest_price = float(df["close"].iloc[-1])
            if not _is_price_sane(symbol, latest_price):
                print(f"[SANITY FAILURE] get_bitget_ohlcv_df price sanity check failed for {symbol}: price={latest_price} below floor limit!")
                return pd.DataFrame()
        return df
    return pd.DataFrame()

def compute_signals(closes):
    if not closes or len(closes) < 30:
        return {
            "rsi": 50.0, "rsi_score": 0.0,
            "macd_hist": 0.0, "macd_score": 0.0,
            "bb_percent": 0.5, "bb_score": 0.0,
            "ema_cross": "neutral", "ema_score": 0.0,
            "score": 0.0
        }
    
    if _OFFICIAL_INDICATORS_AVAILABLE:
        try:
            df = pd.DataFrame({
                'open': closes,
                'high': closes,
                'low': closes,
                'close': closes,
                'volume': [100.0] * len(closes)
            })
            
            manager = IndicatorManager(show_indicators=False)
            config = {
                "RSI": {"period": 14},
                "MACD": {"fast": 12, "slow": 26, "signal": 9},
                "BOLL": {"period": 20, "std_dev": 2},
                "EMA": [{"period": 9}, {"period": 21}]
            }
            results = manager.calculate_multiple(config, df)
            
            # Extract RSI
            rsi_val = float(results["RSI"].values["RSI_14"].iloc[-1])
            # Extract MACD Hist
            macd_hist = float(results["MACD"].values["HIST"].iloc[-1])
            # Extract BOLL Upper, Middle, Lower
            boll_upper = float(results["BOLL"].values["UPPER"].iloc[-1])
            boll_middle = float(results["BOLL"].values["MIDDLE"].iloc[-1])
            boll_lower = float(results["BOLL"].values["LOWER"].iloc[-1])
            # Extract EMA9 & EMA21
            ema9_val = float(results["EMA_9"].values["EMA_9"].iloc[-1])
            ema21_val = float(results["EMA_21"].values["EMA_21"].iloc[-1])
            
            # 1. RSI Score
            if rsi_val < 30:      rsi_score = +2.0  # Oversold (Bullish)
            elif rsi_val < 50:    rsi_score = +1.0
            elif rsi_val < 70:    rsi_score = -1.0
            else:                 rsi_score = -2.0  # Overbought (Bearish)
            
            # 2. MACD Score
            macd_score = +2.0 if macd_hist > 0 else -2.0
            
            # 3. Bollinger Bands Score
            latest_price = closes[-1]
            band_range = (boll_upper - boll_lower)
            bb_percent = (latest_price - boll_lower) / band_range if band_range > 0 else 0.5
            if bb_percent < 0.2:    bb_score = +2.0  # Near lower band (oversold)
            elif bb_percent > 0.8:  bb_score = -2.0  # Near upper band (overbought)
            else:                   bb_score = 0.0
            
            # 4. EMA Cross
            if ema9_val > ema21_val:
                ema_cross = "bullish"
                ema_score = +1.0
            else:
                ema_cross = "bearish"
                ema_score = -1.0
                
            avg_score = (rsi_score + macd_score + bb_score + ema_score) / 4.0
            return {
                "rsi": round(rsi_val, 2),
                "rsi_score": rsi_score,
                "macd_hist": round(macd_hist, 4),
                "macd_score": macd_score,
                "bb_percent": round(bb_percent, 2),
                "bb_score": bb_score,
                "ema_cross": ema_cross,
                "ema_score": ema_score,
                "score": round(avg_score * 3.0, 2)  # Scale to match weight of technicals
            }
        except Exception as e:
            print(f"[IndicatorManager Error] {e}. Falling back to pure-Python technicals.")

    # 1. RSI (Fallback)
    rsi = calculate_rsi(closes)
    if rsi < 30:      rsi_score = +2.0  # Oversold (Bullish)
    elif rsi < 50:    rsi_score = +1.0
    elif rsi < 70:    rsi_score = -1.0
    else:             rsi_score = -2.0  # Overbought (Bearish)
    
    # 2. MACD (Fallback)
    macd, signal, hist = calculate_macd(closes)
    macd_score = +2.0 if hist > 0 else -2.0
    
    # 3. Bollinger Bands (Fallback)
    sma, upper, lower = calculate_bollinger_bands(closes)
    latest_price = closes[-1]
    band_range = (upper - lower)
    bb_percent = (latest_price - lower) / band_range if band_range > 0 else 0.5
    if bb_percent < 0.2:    bb_score = +2.0  # Near lower band (oversold)
    elif bb_percent > 0.8:  bb_score = -2.0  # Near upper band (overbought)
    else:                   bb_score = 0.0
    
    # 4. EMA Cross (Fallback)
    ema9 = calculate_ema(closes, 9)[-1]
    ema21 = calculate_ema(closes, 21)[-1]
    if ema9 > ema21:
        ema_cross = "bullish"
        ema_score = +1.0
    else:
        ema_cross = "bearish"
        ema_score = -1.0
        
    avg_score = (rsi_score + macd_score + bb_score + ema_score) / 4.0
    return {
        "rsi": round(rsi, 2),
        "rsi_score": rsi_score,
        "macd_hist": round(hist, 4),
        "macd_score": macd_score,
        "bb_percent": round(bb_percent, 2),
        "bb_score": bb_score,
        "ema_cross": ema_cross,
        "ema_score": ema_score,
        "score": round(avg_score * 3.0, 2)  # Scale to match weight of technicals
    }

def get_onchain_signals():
    """
    market-intel skill equivalent.
    First tries the official Bitget Skill Hub MCP server for real derivatives
    sentiment (long/short ratio, taker buy/sell pressure, funding rates).
    Falls back to a stable proxy value.
    """
    # --- Try official Bitget Skill Hub MCP server (derivatives_sentiment) ---
    if _SKILL_HUB_AVAILABLE and _skill_hub_client:
        ls_data = _skill_hub_client.derivatives_sentiment("BTCUSDT", "long_short", "4h")
        tr_data = _skill_hub_client.derivatives_sentiment("BTCUSDT", "taker_ratio", "4h")
        score = 0.0
        meta = {"source": "bitget_skill_hub"}
        got_data = False

        if ls_data and isinstance(ls_data, dict):
            ratio = ls_data.get("longShortRatio") or ls_data.get("ratio") or ls_data.get("long_short_ratio")
            # Also try nested list
            if ratio is None and isinstance(ls_data.get("list"), list) and ls_data["list"]:
                ratio = ls_data["list"][0].get("longShortRatio")
            if ratio is not None:
                r = float(ratio)
                meta["long_short_ratio"] = round(r, 4)
                if r > 2.0:    score -= 1.0
                elif r > 1.5:  score -= 0.5
                elif r < 0.5:  score += 1.0
                elif r < 0.75: score += 0.5
                got_data = True

        if tr_data and isinstance(tr_data, dict):
            buy_ratio = tr_data.get("buyRatio") or tr_data.get("takerBuyRatio")
            if buy_ratio is None and isinstance(tr_data.get("list"), list) and tr_data["list"]:
                buy_ratio = tr_data["list"][0].get("buySellRatio") or tr_data["list"][0].get("buyRatio")
            if buy_ratio is not None:
                br = float(buy_ratio)
                meta["taker_buy_ratio"] = round(br, 4)
                score += (br - 0.5) * 2.0   # maps 0->-1, 0.5->0, 1->+1
                got_data = True

        if got_data:
            meta["score"] = round(max(-2.0, min(2.0, score)), 3)
            meta["exchange_net_flow_btc"] = -15.0   # directional proxy
            meta["whale_transactions_24h"] = 25
            return meta

    # --- Fallback: stable mild-bullish proxy ---
    return {
        "exchange_net_flow_btc": -15.0,
        "whale_transactions_24h": 25,
        "score": +0.5,
        "source": "fallback_proxy"
    }

def get_decision(score):
    # Further relaxed for productivity: more trades on decent edges, still risk-aware.
    # Combined with score-strength sizing and regime logic below.
    if score >= 4.0:    return "STRONG BUY",  "HIGH"
    elif score >= 1.5:  return "BUY",          "MEDIUM"
    elif score >= -1.0: return "HOLD",         "LOW"
    elif score >= -4.0: return "SELL",         "MEDIUM"
    else:               return "STRONG SELL",  "HIGH"


# ─── Crypto-only filter for scan ────────────────────────────────────────────
# Bitget lists tokenized stocks (RSPY, RMU, RSNDK, RNVDA, etc.) alongside real
# crypto. These R-prefix symbols have high volume but are NOT crypto. We must
# filter them out so the scan focuses on real crypto for the hackathon.
_EXCLUDED_PREFIXES = ("R",)  # Tokenized stock prefix on Bitget
_EXCLUDED_SUFFIXES = ("3LUSDT", "3SUSDT", "5LUSDT", "5SUSDT")  # Leveraged tokens
_STABLECOIN_BASES = {"USDC", "TUSD", "DAI", "BUSD", "FDUSD", "USDP", "PYUSD"}

def is_real_crypto(symbol: str) -> bool:
    """Return True only for genuine crypto pairs, not tokenized stocks or leveraged tokens."""
    if not symbol.endswith("USDT"):
        return False
    base = symbol.replace("USDT", "")
    if not base:
        return False
    # Exclude R-prefix tokenized stocks (RSPY, RMU, RSNDK, RTSLA, RNVDA, etc.)
    for prefix in _EXCLUDED_PREFIXES:
        if base.startswith(prefix) and len(base) > 1 and base[1:].isalpha() and base[1:].isupper():
            # Additional check: real crypto starting with R (RENDER, ROSE, RSR, RNDR)
            # These have mixed case or are well-known. Tokenized stocks are ALL CAPS
            # and typically 3-5 chars matching ticker symbols (SPY, MU, SNDK, NVDA)
            known_r_crypto = {"RNDR", "ROSE", "RSR", "REEF", "REQ", "RLC", "RUNE", "RVN", "RAY", "RENDER", "RON", "RPL"}
            if base not in known_r_crypto:
                return False
    # Exclude leveraged tokens
    for suffix in _EXCLUDED_SUFFIXES:
        if symbol.endswith(suffix):
            return False
    # Exclude stablecoin bases
    if base in _STABLECOIN_BASES:
        return False
    return True


def get_bitget_all_tickers():
    """Fetch all spot tickers from Bitget to discover tradable coins."""
    url = "https://api.bitget.com/api/v2/spot/market/tickers"
    data = fetch_url(url)
    if data and data.get("data"):
        return data["data"]
    return []


def scan_market(top_n=20, min_volume_usdt=5000000):
    """
    Scan top volume USDT pairs, compute full perception for each,
    rank by |aggregate_score| (highest conviction first).
    Returns list of dicts for the bot to select from.
    This enables the bot to analyze many coins and pick the 'profitable' ones.
    """
    print(f"[*] Scanning top {top_n} high-volume USDT coins for opportunities...")
    all_tickers = get_bitget_all_tickers()
    
    # Pre-fetch global sentiment and macro signals once to optimize performance and rate limits
    fg = get_fear_greed()
    news = get_rss_sentiment()
    mac = get_global_macro()
    on = get_onchain_signals()
    
    if not all_tickers:
        print("⚠️ Could not fetch tickers, falling back to default list.")
        default = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "PEPEUSDT", "WIFUSDT"]
        results = []
        for sym in default:
            try:
                # Quick ticker - prefer official bgc CLI for Bitget integration
                ticker = get_bitget_market_data(sym, use_bgc=True)
                if not ticker:
                    continue
                # Full signal (re-uses main logic but without saving)
                # For simplicity, call compute for candles
                closes = get_bitget_candles(sym, granularity="1h")
                if len(closes) < 30:
                    continue
                tech = compute_signals(closes)
                raw = (tech["score"] * 1.3 + news["score"]*0.8 + fg["score"]*0.9 + mac["score"]*0.7 + on["score"]*0.6)
                norm = max(-10.0, min(10.0, raw))
                dec, conf = get_decision(norm)
                results.append({
                    "symbol": sym,
                    "price": ticker["price"],
                    "change_24h_pct": round(ticker["change_24h"], 2),
                    "volume_24h": ticker.get("volume_24h", 0),
                    "aggregate_score": round(norm, 2),
                    "decision": dec,
                    "confidence": conf,
                    "technicals_score": tech["score"],
                })
            except:
                continue
        ranked = sorted(results, key=lambda x: abs(x["aggregate_score"]), reverse=True)
        return ranked[:top_n]

    # Filter USDT pairs with decent volume — CRYPTO ONLY (no tokenized stocks)
    usdt_tickers = []
    for t in all_tickers:
        sym = t.get("symbol", "")
        if not is_real_crypto(sym):
            continue
        vol = float(t.get("quoteVolume", 0) or 0)  # USDT volume
        if vol >= min_volume_usdt:
            usdt_tickers.append({
                "symbol": sym,
                "price": float(t.get("lastPr", 0)),
                "change_24h": float(t.get("change24h", 0)) * 100,
                "volume_24h": vol,
            })

    # Sort by volume, take top
    usdt_tickers.sort(key=lambda x: x["volume_24h"], reverse=True)
    candidates = usdt_tickers[:top_n * 2]  # oversample

    results = []
    for t in candidates[:top_n]:
        sym = t["symbol"]
        try:
            closes = get_bitget_candles(sym, granularity="1h", limit=100)
            if len(closes) < 30:
                continue
            df = get_bitget_ohlcv_df(sym, granularity="1h", limit=100)
            tech = compute_signals(closes)
            raw = (tech["score"] * 1.3 + news["score"]*0.8 + fg["score"]*0.9 + mac["score"]*0.7 + on["score"]*0.6)
            norm = max(-10.0, min(10.0, raw))
            dec, conf = get_decision(norm)
            
            # Run Strategy Intelligence Layer
            strategy_intelligence = {}
            if _STRATEGY_FRAMEWORK_AVAILABLE and not df.empty:
                try:
                    selector = StrategySelector()
                    strategy_intelligence = selector.select_best_trade(df)
                except Exception as se:
                    pass

            results.append({
                "symbol": sym,
                "price": t["price"],
                "change_24h_pct": round(t["change_24h"], 2),
                "volume_24h": t["volume_24h"],
                "aggregate_score": round(norm, 2),
                "decision": dec,
                "confidence": conf,
                "technicals_score": tech["score"],
                "strategy_intelligence": strategy_intelligence
            })
        except Exception as e:
            continue

    # Rank by conviction (abs score), highest first
    ranked = sorted(results, key=lambda x: abs(x["aggregate_score"]), reverse=True)
    if ranked:
        print(f"[*] Scanned {len(ranked)} coins. Top conviction: {ranked[0]['symbol']} @ {ranked[0]['aggregate_score']:+.2f} ({ranked[0]['decision']})")
    return ranked


def main():
    parser = argparse.ArgumentParser(description="CryptoSentinel Perception Signal Aggregator")
    parser.add_argument("--asset", default="BTC", help="Asset symbol (BTC, ETH, SOL)")
    parser.add_argument("--timeframe", default="1h", choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d"], help="Timeframe / candle granularity")
    parser.add_argument("--scan", action="store_true", help="Scan many coins, rank by conviction, save market_scan.json. Bot can then pick the most profitable.")
    args = parser.parse_args()

    if args.scan:
        ranked = scan_market(top_n=15)
        scan_path = os.path.join(ROOT_DIR, "market_scan.json")
        with open(scan_path, "w") as f:
            json.dump(ranked, f, indent=2)
        print(f"\n[OK] Market scan complete. Saved top {len(ranked)} to {scan_path}")
        print("Top 5 by conviction:")
        for r in ranked[:5]:
            print(f"  {r['symbol']}: score={r['aggregate_score']:+.2f} {r['decision']}({r['confidence']}) vol=${r['volume_24h']/1e6:.1f}M")
        return

    symbol = f"{args.asset.upper()}USDT"
    print(f"[*] Aggregating perception signals for {symbol} ({args.timeframe})...")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Fetch price and 24h ticker data
    ticker = get_bitget_market_data(symbol)
    if not ticker:
        ticker = get_coingecko_market_data(args.asset)
    if not ticker:
        # Hard fallback
        ticker = {"price": 60000.0, "change_24h": 0.0, "volume_24h": 1000.0}

    # Free funding / test mode support
    get_bitget_authenticated_balance()  # Will print note if BITGET keys are in env (for simulated sub-account testing)

    # Map timeframe to Bitget granularity format
    timeframe_map = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d"
    }
    bitget_granularity = timeframe_map.get(args.timeframe, "1h")

    # Fetch candles & calculate technical indicators
    df = get_bitget_ohlcv_df(symbol, granularity=bitget_granularity)
    if df.empty:
        # Mock candles for local fallback testing if API fails
        import random
        base_p = ticker["price"]
        closes = [base_p * (1 + random.uniform(-0.02, 0.02)) for _ in range(100)]
        closes.append(base_p)
        dates = pd.date_range(end=datetime.now(timezone.utc), periods=101, freq="h")
        df = pd.DataFrame({
            "open": pd.Series(closes).shift(1).fillna(base_p),
            "high": pd.Series(closes) * 1.005,
            "low": pd.Series(closes) * 0.995,
            "close": pd.Series(closes),
            "volume": [random.uniform(100, 1000) for _ in range(101)]
        }, index=dates)
        closes = df["close"].tolist()
    else:
        closes = df["close"].tolist()
        
    technicals = compute_signals(closes)
    
    # Fear & greed and RSS news sentiment
    # These map to official Bitget Skill Hub skills:
    # - get_fear_greed() + onchain proxies → sentiment-analyst skill
    # - rss_news → news-briefing skill
    # - macro → macro-analyst skill
    # - onchain → market-intel skill
    fear_greed = get_fear_greed()
    rss_news = get_rss_sentiment()
    macro = get_global_macro()
    onchain = get_onchain_signals()

    # Aggregate Perception Score computation - technicals heavily weighted for productivity
    # (real data edge) + regime-aware boosts.
    # technicals.score scaled to ~4.0 weight
    # others ~1.0-2.0
    base_score = (
        technicals["score"] * 1.3 +   # boost technicals (core edge)
        rss_news["score"] * 0.8 +
        fear_greed["score"] * 0.9 +
        macro["score"] * 0.7 +
        onchain["score"] * 0.6
    )

    # Regime / mean-reversion boost for productivity in high-fear or extreme regimes
    # If fear extreme + technical oversold -> extra bullish bias (mean-reversion)
    # If strong macro disagreement -> dampen
    regime_boost = 0.0
    if fear_greed["score"] >= 1.5 and technicals["rsi"] < 35:
        regime_boost += 1.2   # mean-reversion in fear
    if fear_greed["score"] <= -1.5 and technicals["rsi"] > 65:
        regime_boost -= 1.2   # mean-reversion in greed
    if macro["score"] * base_score < -1.0:  # strong disagreement
        regime_boost *= 0.5   # dampen

    raw_score = base_score + regime_boost
    
    # Normalize score to [-10, +10]
    normalized_score = max(-10.0, min(10.0, raw_score))
    decision, confidence = get_decision(normalized_score)

    # Run the Strategy Intelligence Layer
    strategy_intelligence = {}
    if _STRATEGY_FRAMEWORK_AVAILABLE:
        try:
            selector = StrategySelector()
            strategy_intelligence = selector.select_best_trade(df)
        except Exception as se:
            strategy_intelligence = {"error": str(se)}

    try:
        from scripts.llm_signal_reasoner import generate_signal_report
    except ModuleNotFoundError:
        from llm_signal_reasoner import generate_signal_report
    sentiment_data = {
        "fear_greed": fear_greed,
        "news": rss_news,
        "macro": macro,
        "onchain": onchain
    }
    regime_data = strategy_intelligence.get("regime", "")
    signal_report = generate_signal_report(symbol, ticker["price"], technicals, sentiment_data, regime_data, strategy_intelligence)

    output = {
        "timestamp": ts,
        "asset": symbol,
        "timeframe": args.timeframe,
        "price": ticker["price"],
        "change_24h_pct": round(ticker["change_24h"], 2),
        "fear_greed": fear_greed,
        "news_sentiment": rss_news,
        "macro": macro,
        "onchain": onchain,
        "technicals": technicals,
        "strategy_intelligence": strategy_intelligence,
        "aggregate_score": round(normalized_score, 2),
        "decision": decision,
        "confidence": confidence,
        "signal_report": signal_report
    }

    print(json.dumps(output, indent=2))

    # Save to file (always to project root for consistency with server)
    signals_path = os.path.join(ROOT_DIR, "latest_signals.json")
    with open(signals_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[OK] Signals saved to {signals_path}")
    print("\n========================================")
    print("RESTORED CLEAN SIGNAL REPORT:")
    print("========================================")
    print(signal_report)
    print("========================================")
    print(f"\n>>> DECISION: {decision} (score: {normalized_score:+.1f}, confidence: {confidence})")

if __name__ == "__main__":
    main()
