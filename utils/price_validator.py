import logging
from typing import Optional

# Simple price validator that ensures a price is a positive float.
# If the price is missing or non‑numeric, it attempts to retrieve a cached
# fallback from the price_cache_manager. If that also fails, returns None.

from .price_cache_manager import get_cached_price

MIN_PRICE_FLOORS = {
    "BTCUSDT": 10000.0,
    "BTC": 10000.0,
    "ETHUSDT": 200.0,
    "ETH": 200.0,
    "SOLUSDT": 2.0,
    "SOL": 2.0,
}

def validate_price(symbol: str, price: Optional[float]) -> Optional[float]:
    """Validate a raw price value.

    Args:
        symbol: Upper‑case trading symbol (e.g., 'BTCUSDT').
        price: Raw price value from API (may be None or invalid).

    Returns:
        A valid price (float) or a cached fallback, or None if unavailable.
    """
    sym_upper = symbol.upper()
    try:
        if price is None:
            raise ValueError("Price is None")
        # Coerce to float and ensure positive
        price_f = float(price)
        if price_f <= 0:
            raise ValueError("Non‑positive price")
            
        # Check price floor sanity
        floor = MIN_PRICE_FLOORS.get(sym_upper)
        if floor is None:
            base = sym_upper.replace("USDT", "")
            floor = MIN_PRICE_FLOORS.get(base)
            
        if floor is not None and price_f < floor:
            logging.error(f"[SANITY FAILURE] Price sanity check failed for {symbol}: {price_f} is below floor limit of {floor}!")
            raise ValueError(f"Price {price_f} is below floor limit of {floor}")
            
        return price_f
    except Exception as e:
        logging.warning(f"[price_validator] Invalid price for {symbol}: {e}. Attempting fallback.")
        # Try cached price
        cached = get_cached_price(symbol)
        if cached is not None:
            floor = MIN_PRICE_FLOORS.get(sym_upper)
            if floor is None:
                base = sym_upper.replace("USDT", "")
                floor = MIN_PRICE_FLOORS.get(base)
            if floor is not None and cached < floor:
                logging.error(f"[price_validator] Cached price {cached} for {symbol} is below floor limit of {floor}. Rejecting cache.")
                return None  # explicit early exit — do not fall through
            else:
                logging.info(f"[price_validator] Using cached price for {symbol}: {cached}")
                return cached
        logging.error(f"[price_validator] No valid price available for {symbol}.")
        return None
