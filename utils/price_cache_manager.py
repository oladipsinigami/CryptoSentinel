import time
from threading import Lock

# In‑memory cache for recent prices
_price_cache = {}
_cache_lock = Lock()
CACHE_TTL = 60  # seconds – keep recent price for a minute

def _now():
    return int(time.time())

def get_cached_price(symbol: str):
    """Return cached price if fresh, otherwise None.
    Args:
        symbol: Uppercase symbol like 'BTCUSDT'.
    """
    with _cache_lock:
        entry = _price_cache.get(symbol)
        if entry and (_now() - entry['timestamp'] < CACHE_TTL):
            return entry['price']
    return None

def set_price_cache(symbol: str, price: float):
    """Store price in cache with current timestamp.
    Args:
        symbol: Uppercase symbol.
        price: Numeric price.
    """
    with _cache_lock:
        _price_cache[symbol] = {'price': price, 'timestamp': _now()}
