from __future__ import annotations

import time
import random
import functools
import concurrent.futures as cf
from typing import Callable

from .logger import info, warn, error


def _sleep(backoff: float, jitter: bool = True) -> None:
    t = backoff * (0.5 + random.random() / 2) if jitter else backoff
    time.sleep(t)


def retry(max_tries: int = 3, base_delay: float = 1.0, max_delay: float = 5.0, jitter: bool = True, name: str = "op"):
    """Simple retry/backoff for sync functions."""

    def deco(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            tries = 0
            delay = base_delay
            while True:
                tries += 1
                try:
                    return fn(*args, **kwargs)
                except Exception as e:  # noqa: BLE001
                    if tries >= max_tries:
                        error(f"{name} failed", tries=tries, err=str(e))
                        raise
                    warn(f"{name} retry", tries=tries, err=str(e))
                    _sleep(min(delay, max_delay), jitter=jitter)
                    delay *= 2

        return wrapper

    return deco


def with_timeout(timeout_sec: float, name: str = "op"):
    """Timeout wrapper for sync functions using thread pool."""

    def deco(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with cf.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(fn, *args, **kwargs)
                try:
                    return fut.result(timeout=timeout_sec)
                except cf.TimeoutError:
                    fut.cancel()
                    raise TimeoutError(f"{name} timed out after {timeout_sec}s")

        return wrapper

    return deco


