import time
import logging
from functools import wraps
from typing import Callable, Any, Type, Tuple, Optional

logger = logging.getLogger(__name__)

def retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    tries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
) -> Callable:
    """
    Retry calling the decorated function using an exponential backoff.

    Args:
        exceptions: The exception(s) to check. May be a tuple of exceptions to check.
        tries: Number of times to try (not retry) before giving up.
        delay: Initial delay between retries in seconds.
        backoff: Backoff multiplier e.g. value of 2 will double the delay each retry.
    """
    def deco_retry(f: Callable) -> Callable:
        @wraps(f)
        def f_retry(*args: Any, **kwargs: Any) -> Any:
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    msg = f"{e}, Retrying in {mdelay} seconds..."
                    logger.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry

def fallback(
    fallback_func: Callable,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Fallback to a provided function if the decorated function raises an exception.

    Args:
        fallback_func: The function to call if an exception is raised. Must accept the same args/kwargs.
        exceptions: The exception(s) to check. May be a tuple of exceptions to check.
    """
    def deco_fallback(f: Callable) -> Callable:
        @wraps(f)
        def f_fallback(*args: Any, **kwargs: Any) -> Any:
            try:
                return f(*args, **kwargs)
            except exceptions as e:
                logger.warning(f"Exception {e} caught, falling back to {fallback_func.__name__}")
                return fallback_func(*args, **kwargs)
        return f_fallback
    return deco_fallback
