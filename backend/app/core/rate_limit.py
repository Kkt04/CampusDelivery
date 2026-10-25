"""In-memory sliding-window limiter used for login and auth abuse protection.

Limitation (documented): state lives in one process. In a distributed multi-instance
production deployment, a shared store such as Redis is recommended.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import TYPE_CHECKING

from app.core.exceptions import RateLimitedError

if TYPE_CHECKING:
    from fastapi import Request


def resolve_client_ip(request: Request, trusted_proxies: list[str]) -> str:
    """Safely extract client IP respecting trusted reverse proxy configuration.

    Never blindly trusts arbitrary X-Forwarded-For headers from untrusted connections.
    """
    remote_ip = request.client.host if request.client else "unknown"
    if remote_ip in trusted_proxies:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            first_hop = forwarded.split(",")[0].strip()
            if first_hop:
                return first_hop
    return remote_ip


class SlidingWindowRateLimiter:
    def __init__(self, max_failures: int, window_seconds: int, max_tracked_keys: int = 5000) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.max_tracked_keys = max_tracked_keys
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        if key not in self._failures:
            return deque()
        bucket = self._failures[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if not bucket:
            self._failures.pop(key, None)
            return deque()
        return bucket

    def _cleanup_old_keys(self, now: float) -> None:
        if len(self._failures) > self.max_tracked_keys:
            expired = [k for k, b in list(self._failures.items()) if not b or now - b[-1] > self.window_seconds]
            for k in expired:
                self._failures.pop(k, None)

    def ensure_allowed(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            bucket = self._prune(key, now)
            if len(bucket) >= self.max_failures:
                oldest = bucket[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                raise RateLimitedError(
                    f"Too many failed attempts. Please retry in {retry_after} seconds.",
                    retry_after=retry_after,
                )

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._cleanup_old_keys(now)
            bucket = self._prune(key, now)
            bucket.append(now)
            self._failures[key] = bucket

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._failures.clear()
            else:
                self._failures.pop(key, None)

