import logging
import functools
import traceback
from typing import Callable, Any


def handle_errors(default_return: Any = None):
    """Decorator to wrap functions with a try/except and log errors.
    Returns ``default_return`` if an exception occurs.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.error(f"[error_handler] Exception in {func.__name__}: {e}")
                logging.debug(traceback.format_exc())
                return default_return
        return wrapper
    return decorator


class ErrorHandlerContext:
    """Context manager for a block of code where errors are caught and logged.
    Usage::
        with ErrorHandlerContext(default={'ok': False, 'message': 'fallback'}):
            # risky code
    """
    def __init__(self, default: Any = None):
        self.default = default

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logging.error(f"[error_handler] Exception in block: {exc_val}")
            logging.debug(traceback.format_exception(exc_type, exc_val, exc_tb))
            return True  # suppress exception
        return False
