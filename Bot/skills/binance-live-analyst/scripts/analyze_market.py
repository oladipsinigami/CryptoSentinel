#!/usr/bin/env python3
"""
Market Analysis Engine
Performs trend analysis, SMC detection, volume analysis,
support/resistance identification, and confidence scoring
on OHLCV data from Binance.

Usage:
    python analyze_market.py --symbol SOLUSDT --interval 1h < market_data.json
    python analyze_market.py --symbol SOLUSDT --interval 1h --data-file market_data.json
"""

import argparse
import json
import sys
import math
from typing import Optional


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────

def load_data(data_file: Optional[str]) -> dict:
    if data_file:
        with open(data_file) as f:
            return json.load(f)
    return json.load(sys.stdin)


def extract_candles(data: dict) -> list[dict]:
    if data.get("error"):
        raise RuntimeError(f"Data fetch error: {data['error']}")
    candles = data.get("candles")
    if not candles or len(candles) < 20:
        raise RuntimeError("Insufficient candle data (need at least 20 candles)")
    return candles


# ─────────────────────────────────────────────
# MATH UTILITIES
# ─────────────────────────────────────────────

def atr(candles: list[dict], period: int = 14) -> float:
    """Average True Range."""
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    recent = trs[-period:]
    return sum(recent) / len(recent) if recent else 0.0


def ema(values: list[float], period: int) -> list[float]:
    """Exponential Moving Average."""
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    result = [sum(values[:period]) / period]
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def rolling_avg_volume(candles: list[dict], period: int = 20) -> float:
    vols = [c["volume"] for c in candles[-period:]]
    return sum(vols) / len(vols) if vols else 0.0


# ─────────────────────────────────────────────
# TREND ANALYSIS
# ─────────────────────────────────────────────

def find_swings(candles: list[dict], lookback: int = 3) -> tuple[list, list]:
    """Identify swing highs and swing lows."""
    highs, lows = [], []
    for i in range(lookback, len(candles) - lookback):
        h = candles[i]["high"]
        l = candles[i]["low"]
        if all(h >= candles[i + j]["high"] for j in range(-lookback, lookback + 1) if j != 0):
            highs.append((i, h, candles[i]["open_time"]))
        if all(l <= candles[i + j]["low"] for j in range(-lookback, lookback + 1) if j != 0):
            lows.append((i, l, candles[i]["open_time"]))
    return highs, lows


def determine_trend(candles: list[dict]) -> dict:
    """Determine market trend from swing structure."""
    highs, lows = find_swings(candles, lookback=3)

    if len(highs) < 2 or len(lows) < 2:
        return {"direction": "sideways", "description": "Insufficient swing points for structure analysis", "score": 0}

    recent_highs = highs[-3:]
    recent_lows = lows[-3:]

    # Check for HH/HL (bullish)
    hh = all(recent_highs[i][1] < recent_highs[i + 1][1] for i in range(len(recent_highs) - 1))
    hl = all(recent_lows[i][1] < recent_lows[i + 1][1] for i in range(len(recent_lows) - 1))

    # Check for LH/LL (bearish)
    lh = all(recent_highs[i][1] > recent_highs[i + 1][1] for i in range(len(recent_highs) - 1))
    ll = all(recent_lows[i][1] > recent_lows[i + 1][1] for i in range(len(recent_lows) - 1))

    if hh and hl:
        return {
            "direction": "bullish",
            "description": f"Higher Highs ({recent_highs[-1][1]:.4f}) and Higher Lows ({recent_lows[-1][1]:.4f}) — bullish structure intact",
            "last_high": recent_highs[-1][1],
            "last_low": recent_lows[-1][1],
            "score": 20
        }
    elif lh and ll:
        return {
            "direction": "bearish",
            "description": f"Lower Highs ({recent_highs[-1][1]:.4f}) and Lower Lows ({recent_lows[-1][1]:.4f}) — bearish structure intact",
            "last_high": recent_highs[-1][1],
            "last_low": recent_lows[-1][1],
            "score": 20
        }
    elif hh and ll:
        return {"direction": "sideways", "description": "Mixed structure — HH but LL: expanding range, no clear bias", "score": 0}
    else:
        return {"direction": "sideways", "description": "No consistent swing structure — ranging or transitional market", "score": 0}


def detect_bos_choch(candles: list[dict], highs: list, lows: list) -> list[dict]:
    """Detect Break of Structure and Change of Character events."""
    events = []
    closes = [c["close"] for c in candles]

    if len(highs) >= 2 and len(lows) >= 2:
        last_high = highs[-1][1]
        prev_high = highs[-2][1]
        last_low = lows[-1][1]
        prev_low = lows[-2][1]
        current_close = closes[-1]

        # BOS Bullish: current close breaks above last swing high (trend continuation up)
        if current_close > last_high and last_high > prev_high:
            events.append({
                "type": "BOS",
                "direction": "bullish",
                "level": last_high,
                "description": f"Bullish BOS — close above prior swing high at {last_high:.4f}"
            })

        # BOS Bearish: current close breaks below last swing low (trend continuation down)
        if current_close < last_low and last_low < prev_low:
            events.append({
                "type": "BOS",
                "direction": "bearish",
                "level": last_low,
                "description": f"Bearish BOS — close below prior swing low at {last_low:.4f}"
            })

        # CHoCH Bullish: in downtrend, price breaks above a LH
        if current_close > last_high and last_high < prev_high:
            events.append({
                "type": "CHoCH",
                "direction": "bullish",
                "level": last_high,
                "description": f"Bullish CHoCH — break above lower high at {last_high:.4f}: potential trend reversal"
            })

        # CHoCH Bearish: in uptrend, price breaks below a HL
        if current_close < last_low and last_low > prev_low:
            events.append({
                "type": "CHoCH",
                "direction": "bearish",
                "level": last_low,
                "description": f"Bearish CHoCH — break below higher low at {last_low:.4f}: potential trend reversal"
            })

    return events


# ─────────────────────────────────────────────
# SMC FEATURE DETECTION
# ─────────────────────────────────────────────

def detect_order_blocks(candles: list[dict], lookback: int = 30) -> list[dict]:
    """Detect order blocks: last opposing candle before an impulse move."""
    obs = []
    recent = candles[-lookback:]

    for i in range(2, len(recent) - 2):
        c = recent[i]
        next_c = recent[i + 1]
        after_c = recent[i + 2]

        # Bullish OB: bearish candle followed by strong bullish impulse (2 up candles)
        if (c["close"] < c["open"] and
                next_c["close"] > next_c["open"] and
                after_c["close"] > after_c["open"] and
                after_c["close"] - next_c["open"] > (after_c["high"] - after_c["low"]) * 0.4):
            obs.append({
                "type": "bullish_ob",
                "top": c["open"],
                "bottom": c["close"],
                "time": c["open_time"],
                "description": f"Bullish Order Block: ${c['close']:.4f}–${c['open']:.4f}"
            })

        # Bearish OB: bullish candle followed by strong bearish impulse
        if (c["close"] > c["open"] and
                next_c["close"] < next_c["open"] and
                after_c["close"] < after_c["open"] and
                next_c["open"] - after_c["close"] > (after_c["high"] - after_c["low"]) * 0.4):
            obs.append({
                "type": "bearish_ob",
                "top": c["close"],
                "bottom": c["open"],
                "time": c["open_time"],
                "description": f"Bearish Order Block: ${c['open']:.4f}–${c['close']:.4f}"
            })

    return obs[-3:]  # Return most recent 3 OBs


def detect_fvg(candles: list[dict], lookback: int = 40) -> list[dict]:
    """Detect Fair Value Gaps (3-candle imbalance)."""
    fvgs = []
    recent = candles[-lookback:]

    for i in range(1, len(recent) - 1):
        prev = recent[i - 1]
        curr = recent[i]
        nxt = recent[i + 1]

        # Bullish FVG: gap between candle[i-1] high and candle[i+1] low
        if nxt["low"] > prev["high"]:
            gap_size = nxt["low"] - prev["high"]
            fvgs.append({
                "type": "bullish_fvg",
                "top": nxt["low"],
                "bottom": prev["high"],
                "size": round(gap_size, 6),
                "time": curr["open_time"],
                "description": f"Bullish FVG (unfilled): ${prev['high']:.4f}–${nxt['low']:.4f}"
            })

        # Bearish FVG: gap between candle[i-1] low and candle[i+1] high
        if nxt["high"] < prev["low"]:
            gap_size = prev["low"] - nxt["high"]
            fvgs.append({
                "type": "bearish_fvg",
                "top": prev["low"],
                "bottom": nxt["high"],
                "size": round(gap_size, 6),
                "time": curr["open_time"],
                "description": f"Bearish FVG (unfilled): ${nxt['high']:.4f}–${prev['low']:.4f}"
            })

    return fvgs[-4:]  # Return most recent 4 FVGs


def detect_liquidity_sweep(candles: list[dict], highs: list, lows: list) -> list[dict]:
    """Detect if recent candles swept a liquidity zone then reversed."""
    events = []
    if len(candles) < 3:
        return events

    last = candles[-1]
    prev = candles[-2]

    # Check sweep of recent lows (bullish sweep)
    if lows:
        recent_low = lows[-1][1]
        if prev["low"] < recent_low and last["close"] > recent_low:
            events.append({
                "type": "liquidity_sweep",
                "direction": "bullish",
                "level": recent_low,
                "description": f"Bullish liquidity sweep — wick below ${recent_low:.4f} then closed above: stop hunt confirmed"
            })

    # Check sweep of recent highs (bearish sweep)
    if highs:
        recent_high = highs[-1][1]
        if prev["high"] > recent_high and last["close"] < recent_high:
            events.append({
                "type": "liquidity_sweep",
                "direction": "bearish",
                "level": recent_high,
                "description": f"Bearish liquidity sweep — wick above ${recent_high:.4f} then closed below: stop hunt confirmed"
            })

    return events


def detect_supply_demand(candles: list[dict], lookback: int = 50) -> list[dict]:
    """Identify supply and demand zones from strong impulse origins."""
    zones = []
    recent = candles[-lookback:]

    for i in range(2, len(recent) - 3):
        c = recent[i]
        body_size = abs(c["close"] - c["open"])
        avg_body = sum(abs(x["close"] - x["open"]) for x in recent[max(0, i-10):i]) / 10

        # Strong bullish impulse origin → demand zone
        if c["close"] > c["open"] and body_size > avg_body * 1.8:
            zones.append({
                "type": "demand",
                "top": max(c["open"], c["close"]),
                "bottom": min(c["open"], c["close"]),
                "description": f"Demand Zone: ${min(c['open'], c['close']):.4f}–${max(c['open'], c['close']):.4f}"
            })

        # Strong bearish impulse origin → supply zone
        if c["close"] < c["open"] and body_size > avg_body * 1.8:
            zones.append({
                "type": "supply",
                "top": max(c["open"], c["close"]),
                "bottom": min(c["open"], c["close"]),
                "description": f"Supply Zone: ${min(c['open'], c['close']):.4f}–${max(c['open'], c['close']):.4f}"
            })

    return zones[-4:]


# ─────────────────────────────────────────────
# SUPPORT & RESISTANCE
# ─────────────────────────────────────────────

def find_support_resistance(candles: list[dict], highs: list, lows: list, current_price: float) -> dict:
    """Identify key support and resistance levels relative to current price."""
    all_high_prices = sorted([h[1] for h in highs], reverse=True)
    all_low_prices = sorted([l[1] for l in lows])

    resistances = [h for h in all_high_prices if h > current_price][:3]
    supports = [l for l in all_low_prices if l < current_price][:3]

    # Add psychological levels (round numbers)
    magnitude = 10 ** math.floor(math.log10(current_price))
    psych_above = [round(current_price / magnitude + i) * magnitude for i in range(1, 4)]
    psych_below = [round(current_price / magnitude - i) * magnitude for i in range(1, 4)]

    return {
        "resistance_levels": sorted(resistances),
        "support_levels": sorted(supports, reverse=True),
        "nearest_resistance": resistances[0] if resistances else None,
        "nearest_support": supports[0] if supports else None,
        "psychological_above": psych_above,
        "psychological_below": psych_below,
    }


# ─────────────────────────────────────────────
# VOLUME ANALYSIS
# ─────────────────────────────────────────────

def analyze_volume(candles: list[dict]) -> dict:
    """Analyze volume profile for trading pressure and anomalies."""
    recent = candles[-30:]
    avg_vol = rolling_avg_volume(candles, period=20)
    last_vol = candles[-1]["volume"]
    last_candle = candles[-1]

    # Volume spike detection
    is_spike = last_vol > avg_vol * 1.8
    spike_multiplier = round(last_vol / avg_vol, 2) if avg_vol > 0 else 1.0

    # Bull/bear volume ratio over last 20 candles
    bull_vol = sum(c["volume"] for c in recent if c["close"] >= c["open"])
    bear_vol = sum(c["volume"] for c in recent if c["close"] < c["open"])
    total_vol = bull_vol + bear_vol
    buy_pressure_pct = round(bull_vol / total_vol * 100, 1) if total_vol > 0 else 50.0

    # Volume trend (rising or falling)
    first_half = [c["volume"] for c in recent[:15]]
    second_half = [c["volume"] for c in recent[15:]]
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    vol_trend = "increasing" if avg_second > avg_first * 1.1 else "decreasing" if avg_second < avg_first * 0.9 else "stable"

    # Volume divergence: price up but volume down (or vice versa)
    price_direction = "up" if candles[-1]["close"] > candles[-10]["close"] else "down"
    divergence = (price_direction == "up" and vol_trend == "decreasing") or \
                 (price_direction == "down" and vol_trend == "increasing")

    # Taker buy ratio (if available)
    taker_buy = last_candle.get("taker_buy_vol", 0)
    taker_ratio = round(taker_buy / last_vol * 100, 1) if last_vol > 0 and taker_buy > 0 else None

    return {
        "avg_volume_20": round(avg_vol, 4),
        "last_candle_volume": round(last_vol, 4),
        "volume_spike": is_spike,
        "spike_multiplier": spike_multiplier,
        "buy_pressure_pct": buy_pressure_pct,
        "sell_pressure_pct": round(100 - buy_pressure_pct, 1),
        "volume_trend": vol_trend,
        "price_volume_divergence": divergence,
        "taker_buy_ratio": taker_ratio,
        "summary": _volume_summary(is_spike, spike_multiplier, buy_pressure_pct, divergence, vol_trend)
    }


def _volume_summary(spike, mult, buy_pct, divergence, trend):
    parts = []
    if spike:
        parts.append(f"Volume spike detected ({mult}x average) — potential institutional activity")
    if buy_pct >= 60:
        parts.append(f"Bullish volume pressure: {buy_pct}% buy volume over last 30 candles")
    elif buy_pct <= 40:
        parts.append(f"Bearish volume pressure: {100 - buy_pct}% sell volume over last 30 candles")
    if divergence:
        parts.append("Volume divergence detected — momentum may be weakening")
    if not parts:
        parts.append(f"Volume {trend}, no significant anomalies")
    return parts


# ─────────────────────────────────────────────
# CONFIDENCE SCORING
# ─────────────────────────────────────────────

def calculate_confidence(trend: dict, smc_events: list, sweep_events: list,
                          volume: dict, sr: dict, fvgs: list) -> tuple[int, list]:
    """Score the setup 0–100 and return reasons."""
    score = 0
    reasons = []

    # HTF trend structure (20 pts)
    if trend["direction"] in ("bullish", "bearish"):
        score += trend["score"]
        reasons.append(f"Trend structure confirmed: {trend['direction'].upper()} ({trend['score']}pts)")

    # SMC confluences (20 pts for 3+)
    total_smc = len(smc_events) + len(fvgs)
    if total_smc >= 3:
        score += 20
        reasons.append(f"3+ SMC features detected (OBs + FVGs) (20pts)")
    elif total_smc >= 1:
        score += 10
        reasons.append(f"{total_smc} SMC feature(s) detected (10pts)")

    # Liquidity sweep as trigger (15 pts)
    if sweep_events:
        score += 15
        reasons.append(f"Liquidity sweep confirmed as entry trigger (15pts)")

    # Volume confirmation (15 pts)
    if volume["volume_spike"] or volume["buy_pressure_pct"] >= 62 or volume["buy_pressure_pct"] <= 38:
        score += 15
        reasons.append(f"Volume confirms directional pressure (15pts)")
    elif not volume["price_volume_divergence"]:
        score += 8
        reasons.append(f"Volume aligned with price (no divergence) (8pts)")

    # Clear structural levels (10 pts)
    if sr["nearest_resistance"] and sr["nearest_support"]:
        score += 10
        reasons.append(f"Clear support (${sr['nearest_support']:.4f}) and resistance (${sr['nearest_resistance']:.4f}) identified (10pts)")

    return min(score, 100), reasons


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Analyze Binance market data for trading signals")
    parser.add_argument("--symbol",    required=True)
    parser.add_argument("--interval",  default="1h")
    parser.add_argument("--data-file", default=None, dest="data_file")
    args = parser.parse_args()

    try:
        raw = load_data(args.data_file)
        candles = extract_candles(raw)
    except (RuntimeError, KeyError, json.JSONDecodeError) as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    ticker = raw.get("ticker", {})
    current_price = ticker.get("last_price") or candles[-1]["close"]

    # Run all analyses
    trend = determine_trend(candles)
    highs, lows = find_swings(candles)
    bos_choch = detect_bos_choch(candles, highs, lows)
    obs = detect_order_blocks(candles)
    fvgs = detect_fvg(candles)
    sweeps = detect_liquidity_sweep(candles, highs, lows)
    supply_demand = detect_supply_demand(candles)
    sr = find_support_resistance(candles, highs, lows, current_price)
    volume = analyze_volume(candles)
    atr_val = atr(candles)

    all_smc = bos_choch + obs + sweeps + supply_demand
    confidence, conf_reasons = calculate_confidence(trend, all_smc, sweeps, volume, sr, fvgs)

    # Determine overall bias
    if trend["direction"] == "bullish" and confidence >= 50:
        bias = "bullish"
    elif trend["direction"] == "bearish" and confidence >= 50:
        bias = "bearish"
    else:
        bias = "neutral"

    # Volatility classification
    price_range_pct = ((ticker.get("high_24h", current_price) - ticker.get("low_24h", current_price)) /
                       current_price * 100) if ticker else 0
    if price_range_pct > 8:
        volatility = "high"
    elif price_range_pct > 3:
        volatility = "medium"
    else:
        volatility = "low"

    output = {
        "symbol": args.symbol.upper(),
        "interval": args.interval,
        "fetch_time_utc": raw.get("fetch_time_utc"),
        "current_price": current_price,
        "ticker_summary": {
            "price_change_pct": ticker.get("price_change_pct"),
            "high_24h": ticker.get("high_24h"),
            "low_24h": ticker.get("low_24h"),
            "volume_24h": ticker.get("volume_24h"),
        },
        "analysis": {
            "bias": bias,
            "confidence": confidence,
            "confidence_reasons": conf_reasons,
            "trend": trend,
            "bos_choch_events": bos_choch,
            "order_blocks": obs,
            "fair_value_gaps": fvgs,
            "liquidity_sweeps": sweeps,
            "supply_demand_zones": supply_demand,
            "support_resistance": sr,
            "volume": volume,
            "atr_14": round(atr_val, 6),
            "volatility": volatility,
            "price_range_24h_pct": round(price_range_pct, 2),
        },
        "trade_recommendation": {
            "should_trade": confidence >= 75,
            "direction": bias if confidence >= 75 else "none",
            "note": "Confidence meets 75% threshold — full signal warranted" if confidence >= 75
                    else f"Confidence {confidence}% below 75% threshold — NO TRADE"
        }
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
