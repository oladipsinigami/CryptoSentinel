#!/usr/bin/env python3
"""
Fetch Signals Script — Bitget Trading Agent Skill
Collects all perception layer data and outputs a unified signal summary.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

def fetch_url(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BitgetTradingAgent/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return None


def get_fear_greed():
    data = fetch_url("https://api.alternative.me/fng/?limit=1")
    if data and data.get("data"):
        value = int(data["data"][0]["value"])
        label = data["data"][0]["value_classification"]
        # Contrarian scoring
        if value <= 25:   score = +2
        elif value <= 45: score = +1
        elif value <= 55: score = 0
        elif value <= 75: score = -1
        else:             score = -2
        return {"value": value, "label": label, "score": score}
    return {"value": 50, "label": "Neutral", "score": 0}


def get_btc_price():
    data = fetch_url("https://api.bitget.com/api/v2/spot/market/tickers?symbol=BTCUSDT")
    if data and data.get("data"):
        ticker = data["data"][0]
        return {
            "price": float(ticker.get("lastPr", 0)),
            "change_24h": float(ticker.get("change24h", 0)),
            "volume_24h": float(ticker.get("baseVolume", 0))
        }
    # Fallback to CoinGecko
    data = fetch_url("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true")
    if data and data.get("bitcoin"):
        return {
            "price": data["bitcoin"]["usd"],
            "change_24h": data["bitcoin"].get("usd_24h_change", 0),
            "volume_24h": 0
        }
    return {"price": 0, "change_24h": 0, "volume_24h": 0}


def get_global_macro():
    data = fetch_url("https://api.coingecko.com/api/v3/global")
    if data and data.get("data"):
        btc_dom = data["data"].get("market_cap_percentage", {}).get("btc", 50)
        mkt_cap_change = data["data"].get("market_cap_change_percentage_24h_usd", 0)
        # BTC dominance >55 = risk-off (bearish for alts, neutral for BTC)
        dom_score = 0 if btc_dom > 55 else +1
        trend_score = +1 if mkt_cap_change > 2 else (-1 if mkt_cap_change < -2 else 0)
        return {
            "btc_dominance": round(btc_dom, 1),
            "mkt_cap_change_24h": round(mkt_cap_change, 2),
            "score": dom_score + trend_score
        }
    return {"btc_dominance": 50.0, "mkt_cap_change_24h": 0.0, "score": 0}


def compute_signal_score(fear_greed, price_data, macro):
    """Compute aggregate signal score from -10 to +10."""
    scores = {}

    # Macro score (weight: 1.5)
    scores["macro"] = macro["score"] * 1.5

    # Fear & greed (weight: 1.0)
    scores["sentiment"] = fear_greed["score"] * 1.0

    # Price momentum (weight: 2.0)
    change = price_data["change_24h"]
    if change > 5:      mom = +2
    elif change > 2:    mom = +1
    elif change > -2:   mom = 0
    elif change > -5:   mom = -1
    else:               mom = -2
    scores["momentum"] = mom * 2.0

    raw = sum(scores.values())
    # Normalize to [-10, +10]
    normalized = max(-10, min(10, raw))
    return normalized, scores


def get_decision(score):
    if score >= 6:    return "STRONG BUY",  "HIGH"
    elif score >= 3:  return "BUY",          "MEDIUM"
    elif score >= -3: return "HOLD",         "LOW"
    elif score >= -6: return "SELL",         "MEDIUM"
    else:             return "STRONG SELL",  "HIGH"


def main():
    print("[*] Fetching market signals...\n")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    fear_greed = get_fear_greed()
    price_data  = get_btc_price()
    macro       = get_global_macro()

    score, breakdown = compute_signal_score(fear_greed, price_data, macro)
    decision, confidence = get_decision(score)

    output = {
        "timestamp": ts,
        "asset": "BTC/USDT",
        "price": price_data["price"],
        "change_24h_pct": price_data["change_24h"],
        "fear_greed": fear_greed,
        "macro": macro,
        "score_breakdown": breakdown,
        "aggregate_score": round(score, 2),
        "decision": decision,
        "confidence": confidence
    }

    print(json.dumps(output, indent=2))

    # Save to file for other scripts to consume
    with open("latest_signals.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[OK] Signals saved to latest_signals.json")
    print(f"\n>>> DECISION: {decision} (score: {score:+.1f}, confidence: {confidence})")


if __name__ == "__main__":
    main()
