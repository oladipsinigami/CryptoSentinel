from .price_cache_manager import get_cached_price, set_price_cache
import logging

DEFAULT_FALLBACK_PRICES = {
    "BTCUSDT": 98000.0,
    "ETHUSDT": 3100.0,
    "SOLUSDT": 165.0,
}

def get_fallback_price(symbol: str) -> float:
    """Return a fallback price for the given symbol.
    Tries cached price first, then a hard‑coded default.
    """
    symbol = symbol.upper()
    cached = get_cached_price(symbol)
    if cached is not None:
        logging.info(f"[price_fallback] Using cached fallback price for {symbol}: {cached}")
        return cached
    fallback = DEFAULT_FALLBACK_PRICES.get(symbol)
    if fallback is not None:
        logging.info(f"[price_fallback] Using hard‑coded fallback for {symbol}: {fallback}")
        return fallback
    # generic fallback if unknown symbol
    generic = 100.0
    logging.warning(f"[price_fallback] No specific fallback for {symbol}, using generic {generic}")
    return generic
