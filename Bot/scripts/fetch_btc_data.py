#!/usr/bin/env python3
"""Fetch 7-day BTC hourly candles from Bitget for backtesting."""
import urllib.request
import json
from datetime import datetime, timezone

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

symbol = "BTCUSDT"
url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity=1h&limit=200"
data = fetch(url)
candles_raw = data.get("data", [])
candles_raw.reverse()  # oldest first

candles = []
for c in candles_raw:
    ts = datetime.fromtimestamp(int(c[0])/1000, tz=timezone.utc).isoformat()
    candles.append({
        "open_time": ts,
        "open": c[1],
        "high": c[2],
        "low": c[3],
        "close": c[4],
        "volume": c[5]
    })

out = {"symbol": symbol, "interval": "1h", "candles": candles}
with open("btc_7d.json", "w") as f:
    json.dump(out, f)

print(f"[OK] Fetched {len(candles)} candles for {symbol}. Saved to btc_7d.json")
print(f"Range: {candles[0]['open_time']} -> {candles[-1]['open_time']}")
closes = [float(c["close"]) for c in candles]
print(f"Price range: ${min(closes):,.2f} - ${max(closes):,.2f}")
