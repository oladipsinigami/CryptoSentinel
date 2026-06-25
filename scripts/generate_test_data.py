#!/usr/bin/env python3
"""
Generate a realistic 7-day synthetic BTC/USDT dataset (200 x 1h candles).
Simulates a real market cycle: consolidation -> dip -> recovery -> uptrend.
Used for backtesting when live API is unavailable.
"""
import json
import math
import random
from datetime import datetime, timezone, timedelta

random.seed(42)

# Market simulation: 200 hourly candles
# Based on realistic BTC price action mid-2026
START_PRICE = 63500.0
NUM_CANDLES = 200

# Define market phases (index ranges and price targets)
PHASES = [
    # (start_idx, end_idx, target_price, volatility_mult)
    (0,   30,  61800.0, 1.0),   # Phase 1: Gradual selloff/consolidation
    (30,  55,  59200.0, 1.5),   # Phase 2: Sharp drop (fear)
    (55,  80,  60500.0, 1.2),   # Phase 3: Dead cat bounce
    (80,  110, 58800.0, 1.3),   # Phase 4: Retest lows (FUD)
    (110, 140, 62000.0, 1.0),   # Phase 5: Recovery / accumulation
    (140, 170, 65500.0, 0.9),   # Phase 6: Uptrend begins
    (170, 200, 68800.0, 0.8),   # Phase 7: Bullish trend continuation
]

def get_phase_target(i):
    for (s, e, target, vol) in PHASES:
        if s <= i < e:
            progress = (i - s) / (e - s)
            return target, vol, progress
    return PHASES[-1][2], PHASES[-1][3], 1.0

def generate_candles():
    candles = []
    base_time = datetime(2026, 5, 30, 0, 0, 0, tzinfo=timezone.utc)
    price = START_PRICE

    for i in range(NUM_CANDLES):
        target, vol_mult, progress = get_phase_target(i)
        
        # Smoothly drift toward phase target
        mean_return = (target - price) / price * 0.15  # Gradual mean reversion
        
        # Hourly volatility: ~0.4% base, scaled by phase
        hourly_vol = 0.004 * vol_mult
        
        # Random walk with drift
        rand_return = random.gauss(mean_return, hourly_vol)
        close = price * (1 + rand_return)
        
        # Generate OHLC from close
        candle_range = abs(random.gauss(0, hourly_vol * 0.8)) * price
        open_price = price + random.gauss(0, hourly_vol * 0.3) * price
        high = max(open_price, close) + abs(random.gauss(0, candle_range * 0.5))
        low  = min(open_price, close) - abs(random.gauss(0, candle_range * 0.5))
        
        # Volume: higher during volatile phases
        base_vol = random.uniform(800, 2000)
        volume = base_vol * vol_mult * (1.5 if abs(rand_return) > hourly_vol else 1.0)
        
        ts = (base_time + timedelta(hours=i)).isoformat()
        candles.append({
            "open_time": ts,
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": round(volume, 3)
        })
        
        price = close

    return candles

candles = generate_candles()
out = {
    "symbol": "BTCUSDT",
    "interval": "1h",
    "source": "synthetic_market_simulation",
    "note": "Realistic synthetic BTC data - full market cycle (selloff -> recovery -> uptrend)",
    "candles": candles
}

with open("btc_7d.json", "w") as f:
    json.dump(out, f, indent=2)

closes = [c["close"] for c in candles]
print(f"[OK] Generated {len(candles)} synthetic BTC candles")
print(f"Range: {candles[0]['open_time']} -> {candles[-1]['open_time']}")
print(f"Price: ${closes[0]:,.2f} -> ${closes[-1]:,.2f}")
print(f"Min: ${min(closes):,.2f}  Max: ${max(closes):,.2f}")
print(f"Saved to btc_7d.json")
