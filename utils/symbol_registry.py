import os
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

CACHE_FILE = Path(__file__).with_name('symbol_cache.json')
CACHE_TTL = 24 * 60 * 60  # 24 hours

# Hardcoded fallback list of common Bitget USDT futures symbols.
# Used when the API is unreachable so that the bot still works offline.
_FALLBACK_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
    "BNBUSDT", "LTCUSDT", "UNIUSDT", "AAVEUSDT", "ATOMUSDT",
    "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT",
    "PEPEUSDT", "SHIBUSDT", "FILUSDT", "TRXUSDT", "TONUSDT",
    "WLDUSDT", "SEIUSDT", "TIAUSDT", "INJUSDT", "RUNEUSDT",
    "FETUSDT", "RENDERUSDT", "WIFUSDT", "JUPUSDT", "ENAUSDT",
    "ONDOUSDT", "PENGUUSDT", "STXUSDT", "IMXUSDT", "GRTUSDT",
    "SANDUSDT", "MANAUSDT", "AXSUSDT", "FTMUSDT", "ALGOUSDT",
    "HYPEUSDT",
]


def _fetch_symbols_from_bitget() -> list:
    """Fetch the list of USDT-M futures symbols from Bitget public API (v2).
    Returns a list of symbol strings (e.g., 'BTCUSDT').
    """
    # Bitget v2 mix endpoint for futures contracts
    url = "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CryptoSentinel/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
        data = json.loads(body)
        # v2 response: {"code":"00000","data":[{"symbol":"BTCUSDT",...}, ...]}
        tickers = data.get("data", [])
        symbols = [
            item.get("symbol", "")
            for item in tickers
            if isinstance(item, dict) and item.get("symbol", "").endswith("USDT")
        ]
        return symbols if symbols else _FALLBACK_SYMBOLS
    except Exception as e:
        print(f"[symbol_registry] Failed to fetch symbols from Bitget API: {e}")
        return _FALLBACK_SYMBOLS


def _load_cache() -> dict:
    if CACHE_FILE.is_file():
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(symbols: list):
    cache = {
        "timestamp": int(time.time()),
        "symbols": symbols,
    }
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"[symbol_registry] Failed to write cache: {e}")


def get_symbols() -> list:
    """Return cached symbols if fresh, otherwise fetch from Bitget and cache."""
    cache = _load_cache()
    ts = cache.get('timestamp', 0)
    now = int(time.time())
    if now - ts < CACHE_TTL and cache.get('symbols'):
        return cache['symbols']
    symbols = _fetch_symbols_from_bitget()
    if symbols:
        _save_cache(symbols)
    return symbols or _FALLBACK_SYMBOLS


def normalize_symbol(symbol: str) -> Optional[str]:
    """Ensure symbol (e.g. SOL, SOLUSDT, sol, sol/usdt) resolves to standard USDT pair.
    E.g., 'sol' -> 'SOLUSDT', 'SOL/USDT' -> 'SOLUSDT', 'SOL-USDT' -> 'SOLUSDT'.
    """
    if not symbol:
        return None
    s = symbol.strip().upper()
    s = s.replace('/', '').replace('-', '').replace('_', '')
    if not s.endswith('USDT'):
        if s.endswith('USDC'):
            s = s[:-4]
        elif s.endswith('USD'):
            s = s[:-3]
        s = s + 'USDT'
    return s


def is_valid_symbol(sym: str) -> bool:
    """Check if a symbol (e.g., 'BTCUSDT') exists in the known list.
    Normalizes the input using normalize_symbol.
    """
    normalized = normalize_symbol(sym)
    if not normalized:
        return False
    return normalized in get_symbols()
