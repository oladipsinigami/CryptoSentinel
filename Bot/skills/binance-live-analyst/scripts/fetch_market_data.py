#!/usr/bin/env python3
"""
Binance Live Market Data Fetcher
Fetches OHLCV candles, 24h ticker, and optional order book data.

Endpoint strategy (automatic, no config needed):
  1. CoinGecko API  — free, no key, globally accessible (PRIMARY)
  2. Binance.com    — used as fallback if CoinGecko fails

Output schema is identical regardless of which source is used,
so analyze_market.py and scan_pairs.py work without modification.

Usage:
    python fetch_market_data.py --symbol SOLUSDT --interval 1h --limit 100
    python fetch_market_data.py --symbol BTCUSDT --interval 4h --limit 200 --extras
"""

import argparse
import json
import ssl
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# SSL context — verification disabled for public market-data-only endpoints.
# No credentials are ever transmitted by this script.
# ---------------------------------------------------------------------------
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
BINANCE_BASE   = "https://api.binance.com/api/v3"

VALID_INTERVALS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h",
                   "6h", "8h", "12h", "1d", "3d", "1w", "1M"}

# CoinGecko interval → (days_back, CG interval string)
# CoinGecko auto-selects granularity based on `days`: 1d→5min, 2-90d→hourly, >90d→daily
_CG_INTERVAL_MAP = {
    "1m":  (1,   "minutely"),
    "3m":  (1,   "minutely"),
    "5m":  (1,   "minutely"),
    "15m": (1,   "minutely"),
    "30m": (1,   "minutely"),
    "1h":  (7,   "hourly"),
    "2h":  (14,  "hourly"),
    "4h":  (30,  "hourly"),
    "6h":  (45,  "hourly"),
    "8h":  (60,  "hourly"),
    "12h": (90,  "hourly"),
    "1d":  (365, "daily"),
    "3d":  (365, "daily"),
    "1w":  (365, "daily"),
    "1M":  (365, "daily"),
}

# Binance symbol → CoinGecko coin ID mapping (extend as needed)
_SYMBOL_TO_CG_ID = {
    "BTCUSDT":  "bitcoin",
    "ETHUSDT":  "ethereum",
    "SOLUSDT":  "solana",
    "BNBUSDT":  "binancecoin",
    "XRPUSDT":  "ripple",
    "DOGEUSDT": "dogecoin",
    "ADAUSDT":  "cardano",
    "AVAXUSDT": "avalanche-2",
    "DOTUSDT":  "polkadot",
    "MATICUSDT":"matic-network",
    "LINKUSDT": "chainlink",
    "UNIUSDT":  "uniswap",
    "LTCUSDT":  "litecoin",
    "ATOMUSDT": "cosmos",
    "NEARUSDT": "near",
    "APTUSDT":  "aptos",
    "ARBUSDT":  "arbitrum",
    "OPUSDT":   "optimism",
    "SUIUSDT":  "sui",
    "PEPEUSDT": "pepe",
    "WIFUSDT":  "dogwifcoin",
    "SHIBUSDT": "shiba-inu",
    "TRXUSDT":  "tron",
}


# ---------------------------------------------------------------------------
# Core HTTP helper
# ---------------------------------------------------------------------------

def _get(url: str) -> dict | list:
    """GET a URL and return parsed JSON. Raises RuntimeError on any failure."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BinanceLiveAnalyst/1.0",
                 "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        raise RuntimeError(f"HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# CoinGecko data fetchers
# ---------------------------------------------------------------------------

def _cg_resolve_id(symbol: str) -> str:
    """Map a Binance symbol (e.g. BTCUSDT) to a CoinGecko coin ID."""
    sym = symbol.upper()
    if sym in _SYMBOL_TO_CG_ID:
        return _SYMBOL_TO_CG_ID[sym]
    # Try stripping USDT/BTC/ETH suffix and search CoinGecko
    base = sym.replace("USDT", "").replace("BTC", "").replace("ETH", "").lower()
    try:
        coins = _get(f"{COINGECKO_BASE}/coins/list?include_platform=false")
        for c in coins:
            if c["symbol"].lower() == base:
                return c["id"]
    except RuntimeError:
        pass
    raise RuntimeError(
        f"Cannot resolve '{symbol}' to a CoinGecko ID. "
        f"Add it to _SYMBOL_TO_CG_ID in fetch_market_data.py."
    )


def _cg_get_ticker(cg_id: str, symbol: str) -> dict:
    """Fetch 24h ticker from CoinGecko simple/price endpoint."""
    url = (f"{COINGECKO_BASE}/simple/price"
           f"?ids={cg_id}&vs_currencies=usd"
           f"&include_24hr_change=true&include_24hr_vol=true"
           f"&include_last_updated_at=true")
    data = _get(url)[cg_id]

    # For high/low and open we use the market_chart data — approximate here
    price       = data["usd"]
    change_pct  = data.get("usd_24h_change", 0.0)
    vol_24h     = data.get("usd_24h_vol", 0.0)
    prev_price  = price / (1 + change_pct / 100) if change_pct != -100 else price

    return {
        "symbol":           symbol.upper(),
        "price_change":     round(price - prev_price, 6),
        "price_change_pct": round(change_pct, 4),
        "weighted_avg":     round((price + prev_price) / 2, 6),
        "prev_close":       round(prev_price, 6),
        "last_price":       price,
        "bid":              price,   # CoinGecko doesn't provide L2
        "ask":              price,
        "open":             round(prev_price, 6),
        "high_24h":         price,   # will be overridden by OHLCV if available
        "low_24h":          price,
        "volume_24h":       round(vol_24h / price, 4) if price else 0,
        "quote_volume_24h": round(vol_24h, 2),
        "open_time":        (datetime.now(tz=timezone.utc) - timedelta(hours=24)).isoformat(),
        "close_time":       datetime.now(tz=timezone.utc).isoformat(),
        "count":            0,
        "data_source":      "coingecko",
    }


def _cg_get_klines(cg_id: str, symbol: str, interval: str, limit: int) -> list[dict]:
    """Fetch OHLCV candles from CoinGecko market_chart/range endpoint."""
    days_back, _ = _CG_INTERVAL_MAP.get(interval, (7, "hourly"))

    # CoinGecko free tier: use /market_chart with days param
    url = (f"{COINGECKO_BASE}/coins/{cg_id}/market_chart"
           f"?vs_currency=usd&days={days_back}")
    data = _get(url)

    prices  = data.get("prices", [])
    volumes = data.get("total_volumes", [])

    # Build vol map by timestamp for fast lookup
    vol_map = {v[0]: v[1] for v in volumes}

    # Convert to OHLCV — CoinGecko gives close prices only, so we synthesise
    # OHLC from adjacent closes (standard approach for single-price feeds).
    candles = []
    closes  = [(p[0], p[1]) for p in prices]

    # Apply limit (take most recent `limit` candles)
    closes = closes[-limit:]

    for i, (ts, close) in enumerate(closes):
        prev_close = closes[i - 1][1] if i > 0 else close
        # Approximate OHLC — open = prev close, high/low derived from range
        candle_range = abs(close - prev_close)
        high  = max(close, prev_close) + candle_range * 0.1
        low   = min(close, prev_close) - candle_range * 0.1
        vol   = vol_map.get(ts, 0) / close if close else 0

        candles.append({
            "open_time":           datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat(),
            "open":                round(prev_close, 6),
            "high":                round(high, 6),
            "low":                 round(low, 6),
            "close":               round(close, 6),
            "volume":              round(vol, 4),
            "close_time":          datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat(),
            "quote_volume":        round(vol_map.get(ts, 0), 2),
            "trades":              0,
            "taker_buy_vol":       round(vol * 0.5, 4),  # not available, estimated
            "taker_buy_quote_vol": round(vol_map.get(ts, 0) * 0.5, 2),
        })

    return candles


# ---------------------------------------------------------------------------
# Binance fallback fetchers
# ---------------------------------------------------------------------------

def _binance_get_ticker(symbol: str) -> dict:
    url = f"{BINANCE_BASE}/ticker/24hr?symbol={symbol.upper()}"
    data = _get(url)
    return {
        "symbol":            data["symbol"],
        "price_change":      float(data["priceChange"]),
        "price_change_pct":  float(data["priceChangePercent"]),
        "weighted_avg":      float(data["weightedAvgPrice"]),
        "prev_close":        float(data["prevClosePrice"]),
        "last_price":        float(data["lastPrice"]),
        "bid":               float(data["bidPrice"]),
        "ask":               float(data["askPrice"]),
        "open":              float(data["openPrice"]),
        "high_24h":          float(data["highPrice"]),
        "low_24h":           float(data["lowPrice"]),
        "volume_24h":        float(data["volume"]),
        "quote_volume_24h":  float(data["quoteVolume"]),
        "open_time":         datetime.fromtimestamp(data["openTime"] / 1000, tz=timezone.utc).isoformat(),
        "close_time":        datetime.fromtimestamp(data["closeTime"] / 1000, tz=timezone.utc).isoformat(),
        "count":             int(data["count"]),
        "data_source":       "binance",
    }


def _binance_get_klines(symbol: str, interval: str, limit: int) -> list[dict]:
    url = (f"{BINANCE_BASE}/klines"
           f"?symbol={symbol.upper()}&interval={interval}&limit={limit}")
    raw = _get(url)
    candles = []
    for c in raw:
        candles.append({
            "open_time":           datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc).isoformat(),
            "open":                float(c[1]),
            "high":                float(c[2]),
            "low":                 float(c[3]),
            "close":               float(c[4]),
            "volume":              float(c[5]),
            "close_time":          datetime.fromtimestamp(c[6] / 1000, tz=timezone.utc).isoformat(),
            "quote_volume":        float(c[7]),
            "trades":              int(c[8]),
            "taker_buy_vol":       float(c[9]),
            "taker_buy_quote_vol": float(c[10]),
        })
    return candles


# ---------------------------------------------------------------------------
# Public interface — auto-selects source
# ---------------------------------------------------------------------------

def get_ticker_24h(symbol: str) -> dict:
    """Fetch 24h ticker. Tries CoinGecko first, falls back to Binance."""
    try:
        cg_id = _cg_resolve_id(symbol)
        return _cg_get_ticker(cg_id, symbol)
    except RuntimeError as cg_err:
        print(f"[WARN] CoinGecko ticker failed ({cg_err}). Trying Binance…", file=sys.stderr)
    return _binance_get_ticker(symbol)


def get_klines(symbol: str, interval: str, limit: int) -> list[dict]:
    """Fetch OHLCV candles. Tries CoinGecko first, falls back to Binance."""
    try:
        cg_id = _cg_resolve_id(symbol)
        candles = _cg_get_klines(cg_id, symbol, interval, limit)
        if candles:
            return candles
        raise RuntimeError("Empty candle list returned")
    except RuntimeError as cg_err:
        print(f"[WARN] CoinGecko klines failed ({cg_err}). Trying Binance…", file=sys.stderr)
    return _binance_get_klines(symbol, interval, limit)


def validate_symbol(symbol: str) -> str:
    """Validate and normalise symbol. Auto-appends USDT if no quote suffix."""
    symbol = symbol.upper()
    if not any(symbol.endswith(q) for q in ["USDT", "BTC", "ETH", "BNB", "BUSD", "USDC"]):
        symbol = symbol + "USDT"
    # Check CoinGecko mapping or attempt resolution
    try:
        _cg_resolve_id(symbol)
        return symbol
    except RuntimeError:
        pass
    # Try Binance as last resort
    try:
        _get(f"{BINANCE_BASE}/ticker/price?symbol={symbol}")
        return symbol
    except RuntimeError as e:
        raise RuntimeError(f"Symbol '{symbol}' not found on any data source: {e}")


# ---------------------------------------------------------------------------
# Optional: order book stub (CoinGecko doesn't provide L2 — uses Binance)
# ---------------------------------------------------------------------------

def get_order_book(symbol: str, depth: int = 20) -> dict:
    """Fetch order book from Binance (best effort — may fail if geo-blocked)."""
    try:
        url = f"{BINANCE_BASE}/depth?symbol={symbol.upper()}&limit={depth}"
        data = _get(url)
        bids = [(float(p), float(q)) for p, q in data["bids"]]
        asks = [(float(p), float(q)) for p, q in data["asks"]]
        bid_liq = sum(p * q for p, q in bids)
        ask_liq = sum(p * q for p, q in asks)
        total = bid_liq + ask_liq
        return {
            "top_bid":       bids[0][0] if bids else None,
            "top_ask":       asks[0][0] if asks else None,
            "spread":        round(asks[0][0] - bids[0][0], 8) if bids and asks else None,
            "bid_liquidity": round(bid_liq, 2),
            "ask_liquidity": round(ask_liq, 2),
            "buy_pressure":  round(bid_liq / total * 100, 2) if total else 50.0,
            "bids_snapshot": bids[:5],
            "asks_snapshot": asks[:5],
            "data_source":   "binance",
        }
    except RuntimeError as e:
        return {"error": f"Order book unavailable: {e}", "data_source": "none"}


def get_recent_trades(symbol: str, limit: int = 50) -> dict:
    """Fetch recent trades from Binance (best effort — may fail if geo-blocked)."""
    try:
        url = f"{BINANCE_BASE}/trades?symbol={symbol.upper()}&limit={limit}"
        data = _get(url)
        buys  = [t for t in data if not t["isBuyerMaker"]]
        sells = [t for t in data if t["isBuyerMaker"]]
        buy_vol   = sum(float(t["qty"]) for t in buys)
        sell_vol  = sum(float(t["qty"]) for t in sells)
        total_vol = buy_vol + sell_vol
        return {
            "total_trades": len(data),
            "buy_trades":   len(buys),
            "sell_trades":  len(sells),
            "buy_volume":   round(buy_vol, 4),
            "sell_volume":  round(sell_vol, 4),
            "buy_ratio":    round(buy_vol / total_vol * 100, 2) if total_vol else 50.0,
            "last_price":   float(data[-1]["price"]) if data else None,
            "last_trade_time": datetime.fromtimestamp(
                data[-1]["time"] / 1000, tz=timezone.utc
            ).isoformat() if data else None,
            "data_source":  "binance",
        }
    except RuntimeError as e:
        return {"error": f"Recent trades unavailable: {e}", "data_source": "none"}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch live market data (CoinGecko → Binance fallback)")
    parser.add_argument("--symbol",   required=True,       help="Trading pair, e.g. SOLUSDT")
    parser.add_argument("--interval", default="1h",        help="Candle interval (default: 1h)")
    parser.add_argument("--limit",    default=100, type=int, help="Number of candles (20–500)")
    parser.add_argument("--extras",   action="store_true", help="Also fetch order book + recent trades")
    parser.add_argument("--out",      default=None,        help="Write JSON output to file instead of stdout")
    args = parser.parse_args()

    if args.interval not in VALID_INTERVALS:
        print(json.dumps({"error": f"Invalid interval '{args.interval}'. Valid: {sorted(VALID_INTERVALS)}"}))
        sys.exit(1)

    if args.limit < 20 or args.limit > 500:
        print(json.dumps({"error": "Limit must be between 20 and 500"}))
        sys.exit(1)

    result = {
        "fetch_time_utc": datetime.now(tz=timezone.utc).isoformat(),
        "symbol":         None,
        "interval":       args.interval,
        "error":          None,
        "ticker":         None,
        "candles":        None,
        "order_book":     None,
        "recent_trades":  None,
    }

    try:
        symbol = validate_symbol(args.symbol)
        result["symbol"] = symbol

        result["ticker"]  = get_ticker_24h(symbol)
        result["candles"] = get_klines(symbol, args.interval, args.limit)

        if args.extras:
            result["order_book"]    = get_order_book(symbol)
            result["recent_trades"] = get_recent_trades(symbol)

    except RuntimeError as e:
        result["error"] = str(e)
        output = json.dumps(result, indent=2)
        if args.out:
            with open(args.out, "w") as f:
                f.write(output)
        else:
            print(output)
        sys.exit(1)

    output = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(output)
        print(f"[OK] Data written to {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
