import logging
import os
from datetime import datetime

# Use a dedicated named logger — never call logging.basicConfig() at import
# time because it hijacks the root logger for the entire application.
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOG_PATH = os.path.join(LOG_DIR, 'symbol_extraction.log')

_logger = logging.getLogger("symbol_extraction")
_logger.setLevel(logging.INFO)

# Only add handlers if none exist (prevents duplicates on re-import)
if not _logger.handlers:
    try:
        _fh = logging.FileHandler(LOG_PATH, encoding='utf-8')
        _fh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s'))
        _logger.addHandler(_fh)
    except Exception:
        pass  # File handler may fail in read-only environments


def log_extraction_attempt(raw_text: str, candidates: list, selected: str):
    """Log a symbol extraction attempt.
    Args:
        raw_text: Original user input.
        candidates: List of candidate symbols considered.
        selected: The final symbol chosen (or fallback).
    """
    try:
        _logger.info(
            f"Extraction attempt | input='{raw_text}' | candidates={candidates} | selected='{selected}'"
        )
    except Exception:
        # Fail-safe: never raise from logger
        pass
