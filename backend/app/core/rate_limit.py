"""In-memory sliding-window limiter used for login abuse protection.

Limitation (documented): state lives in one process. With several API workers
each worker keeps its own counters; a shared store would be needed then.
"""
import time
from collections import defaultdict, deque
from threading import Lock

from app.core.exceptions import RateLimitedError


class SlidingWindowRateLimiter:
    def __init__(self, max_failures: int, window_seconds: int) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        bucket = self._failures[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        return bucket

    def ensure_allowed(self, key: str) -> None:
        with self._lock:
            if len(self._prune(key, time.monotonic())) >= self.max_failures:
                raise RateLimitedError("Too many failed attempts. Try again in a few minutes.")

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, now).append(now)

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._failures.clear()
            else:
                self._failures.pop(key, None)
