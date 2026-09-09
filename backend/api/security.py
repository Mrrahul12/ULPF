"""Lightweight API security and request metrics for the ULPF service."""

import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import DefaultDict, Deque


class RateLimitExceeded(Exception):
    """Raised when a client exceeds the configured request limit."""


class RateLimiter:
    """Thread-safe fixed-window request limiter keyed by client identifier."""

    def __init__(self, limit: int = 100, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, client_id: str) -> None:
        """Record a request or raise RateLimitExceeded."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            requests = self._requests[client_id]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= self.limit:
                raise RateLimitExceeded()
            requests.append(now)

    def reset(self) -> None:
        """Clear tracked requests, primarily for tests and local operation."""
        with self._lock:
            self._requests.clear()


class RequestMetrics:
    """Simple process-local counters suitable for a first deployment."""

    def __init__(self):
        self._lock = Lock()
        self.total_requests = 0
        self.successful_parses = 0
        self.rejected_requests = 0
        self.failed_parses = 0

    def record_request(self) -> None:
        with self._lock:
            self.total_requests += 1

    def record_success(self) -> None:
        with self._lock:
            self.successful_parses += 1

    def record_rejection(self) -> None:
        with self._lock:
            self.rejected_requests += 1

    def record_failure(self) -> None:
        with self._lock:
            self.failed_parses += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "total_requests": self.total_requests,
                "successful_parses": self.successful_parses,
                "rejected_requests": self.rejected_requests,
                "failed_parses": self.failed_parses,
            }


def configured_api_key() -> str | None:
    """Read the optional API key from the environment."""
    value = os.getenv("ULPF_API_KEY", "").strip()
    return value or None


def configured_rate_limit() -> tuple[int, int]:
    """Read rate limit and window settings with safe defaults."""
    try:
        limit = max(1, int(os.getenv("ULPF_RATE_LIMIT", "100")))
        window = max(1, int(os.getenv("ULPF_RATE_WINDOW_SECONDS", "60")))
    except ValueError:
        return 100, 60
    return limit, window
