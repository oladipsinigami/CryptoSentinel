#!/usr/bin/env python3
"""
Multi-Pair Binance Scanner
Scans multiple Binance pairs in parallel, scores each by confidence,
and returns a ranked list of trade opportunities.

Usage:
    python scan_pairs.py --pairs BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
    python scan_pairs.py --pairs BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT --interval 4h --min-confidence 75
"""

import argparse
import json
import sys
import os
import subprocess
import concurrent.futures
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT",
    "BNBUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT"
]


def analyze_pair(symbol: str, interval: str) -> dict:
    """Fetch + analyze a single pair. Returns analysis result dict."""
    try:
        # Run fetch
        fetch_proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "fetch_market_data.py"),
             "--symbol", symbol, "--interval", interval, "--limit", "100"],
            capture_output=True, text=True, timeout=20
        )
        if fetch_proc.returncode != 0:
            return {"symbol": symbol, "error": f"Fetch failed: {fetch_proc.stderr.strip()}", "confidence": 0}

        fetch_data = fetch_proc.stdout

        # Run analysis
        analyze_proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "analyze_market.py"),
             "--symbol", symbol, "--interval", interval],
            input=fetch_data, capture_output=True, text=True, timeout=15
        )
        if analyze_proc.returncode != 0:
            return {"symbol": symbol, "error": f"Analysis failed: {analyze_proc.stderr.strip()}", "confidence": 0}

        result = json.loads(analyze_proc.stdout)
        return result

    except subprocess.TimeoutExpired:
        return {"symbol": symbol, "error": "Timeout fetching/analyzing data", "confidence": 0}
    except json.JSONDecodeError as e:
        return {"symbol": symbol, "error": f"JSON parse error: {e}", "confidence": 0}
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "confidence": 0}


def format_scan_summary(results: list[dict], min_confidence: int) -> str:
    """Format ranked results as a concise text summary for the analyst."""
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📡 BINANCE PAIR SCAN — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]

    qualified = [r for r in results if r.get("analysis", {}).get("confidence", 0) >= min_confidence]
    not_qualified = [r for r in results if r.get("analysis", {}).get("confidence", 0) < min_confidence]
    errors = [r for r in results if r.get("error")]

    if qualified:
        lines.append(f"✅ {len(qualified)} PAIR(S) ABOVE {min_confidence}% CONFIDENCE THRESHOLD:")
        lines.append("")
        for i, r in enumerate(qualified, 1):
            a = r.get("analysis", {})
            conf = a.get("confidence", 0)
            bias = a.get("bias", "neutral").upper()
            price = r.get("current_price", "N/A")
            symbol = r.get("symbol", "?")
            change = r.get("ticker_summary", {}).get("price_change_pct", 0)
            vol = r.get("analysis", {}).get("volatility", "?")
            emoji = "🟢" if bias == "BULLISH" else "🔴" if bias == "BEARISH" else "🟡"
            lines.append(f"  #{i} {symbol} — {emoji} {bias} | Confidence: {conf}% | Price: ${price} ({change:+.2f}%) | Volatility: {vol}")
    else:
        lines.append(f"⛔ No pairs met the {min_confidence}% confidence threshold.")

    lines.append("")
    if not_qualified:
        lines.append(f"📊 BELOW THRESHOLD ({len(not_qualified)} pairs):")
        for r in not_qualified:
            if not r.get("error"):
                a = r.get("analysis", {})
                lines.append(f"  • {r.get('symbol','?')}: {a.get('confidence', 0)}% confidence | {a.get('bias','neutral').upper()}")

    if errors:
        lines.append("")
        lines.append(f"⚠️  ERRORS ({len(errors)} pairs):")
        for r in errors:
            lines.append(f"  • {r.get('symbol','?')}: {r.get('error','unknown error')}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scan multiple Binance pairs for opportunities")
    parser.add_argument("--pairs", default=",".join(DEFAULT_PAIRS[:6]),
                        help="Comma-separated list of pairs (e.g. BTCUSDT,ETHUSDT)")
    parser.add_argument("--interval", default="1h",
                        help="Candle interval (default: 1h)")
    parser.add_argument("--min-confidence", default=75, type=int, dest="min_confidence",
                        help="Minimum confidence to flag as opportunity (default: 75)")
    parser.add_argument("--top", default=3, type=int,
                        help="Number of top results to highlight (default: 3)")
    parser.add_argument("--format", default="json", choices=["json", "text"],
                        help="Output format: json or text summary")
    args = parser.parse_args()

    pairs = [p.strip().upper() for p in args.pairs.split(",") if p.strip()]
    if not pairs:
        print(json.dumps({"error": "No valid pairs provided"}))
        sys.exit(1)

    print(f"[SCAN] Analyzing {len(pairs)} pairs on {args.interval}...", file=sys.stderr)

    # Run all pairs in parallel (max 5 workers to be respectful of rate limits)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(analyze_pair, pair, args.interval): pair for pair in pairs}
        for future in concurrent.futures.as_completed(futures):
            pair = futures[future]
            try:
                result = future.result()
                results.append(result)
                conf = result.get("analysis", {}).get("confidence", result.get("confidence", 0))
                print(f"[SCAN] {pair}: {conf}% confidence", file=sys.stderr)
            except Exception as e:
                results.append({"symbol": pair, "error": str(e), "confidence": 0})

    # Sort by confidence descending
    results.sort(key=lambda r: r.get("analysis", {}).get("confidence", 0), reverse=True)

    # Output
    if args.format == "text":
        print(format_scan_summary(results, args.min_confidence))
    else:
        output = {
            "scan_time_utc": datetime.now(timezone.utc).isoformat(),
            "interval": args.interval,
            "pairs_scanned": len(pairs),
            "min_confidence_threshold": args.min_confidence,
            "results_ranked": results,
            "top_opportunities": [
                r for r in results[:args.top]
                if r.get("analysis", {}).get("confidence", 0) >= args.min_confidence
            ],
            "text_summary": format_scan_summary(results, args.min_confidence)
        }
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
