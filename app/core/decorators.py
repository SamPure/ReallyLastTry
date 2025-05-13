import functools
import time
import random
import logging
from typing import Callable, TypeVar, Any
from app.core.constants import DEFAULT_MAX_RETRIES, DEFAULT_BACKOFF_BASE

T = TypeVar("T")


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: int = DEFAULT_BACKOFF_BASE,
    error_counter: Any = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if error_counter:
                        error_counter.inc()
                    if attempt < max_retries - 1:
                        sleep_time = backoff_base**attempt + random.random()
                        time.sleep(sleep_time)
            raise last_error

        return wrapper

    return decorator
