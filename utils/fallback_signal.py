import json
import logging
from datetime import datetime
from typing import Any, Dict

def generate_fallback_signal(symbol: str, price: float) -> Dict[str, Any]:
    """Generate a minimal yet useful signal payload when live data fails.
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT').
        price: Fallback price to include.
    Returns:
        A dict representing a simplified signal structure.
    """
    now_iso = datetime.utcnow().isoformat() + 'Z'
    signal = {
        "symbol": symbol.upper(),
        "price": price,
        "aggregate_score": 0.0,
        "decision": "HOLD",
        "confidence": "LOW",
        "technicals": {
            "rsi": 50,
            "ema_cross": "neutral",
            "macd_hist": 0
        },
        "fear_greed": {"value": 50, "label": "Neutral", "score": 0},
        "news": {"score": 0},
        "macro": {"score": 0},
        "onchain": {"score": 0.5},
        "generated_at": now_iso,
        "fallback": True,
    }
    logging.info(f"[fallback_signal] Generated fallback signal for {symbol} at {price}")
    return signal

def serialize_fallback_signal(signal: Dict[str, Any]) -> str:
    """Serialize the fallback signal to a JSON string for API responses."""
    try:
        return json.dumps(signal, default=str)
    except Exception as e:
        logging.error(f"[fallback_signal] Serialization error: {e}")
        return json.dumps({"error": "fallback serialization failed"})
