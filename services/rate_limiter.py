"""
rate_limiter.py
Simple in-memory per-user, per-endpoint rate limiter.

Note: This limiter is process-local. In multi-worker deployments, use a shared store.
"""

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Tuple


class RateLimiter:
    def __init__(self) -> None:
        # Structure: {(user_id, endpoint): deque[timestamps]}
        self._buckets: Dict[Tuple[int, str], Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, user_id: int, endpoint: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        key = (user_id, endpoint)
        with self._lock:
            bucket = self._buckets[key]
            # Drop timestamps outside the window
            cutoff = now - window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


# Global singleton for convenience
rate_limiter = RateLimiter()


