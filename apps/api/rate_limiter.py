"""
Rate Limiter for AI Generation & Regeneration Endpoints.

Implements an in-memory sliding-window log rate limiter.
Tracks timestamps of requests per client key (IP address and API key).
Returns HTTP 429 Too Many Requests when the limit is exceeded.
"""

import time
from collections import defaultdict, deque
from fastapi import Header, HTTPException, Request, status


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter.
    Limits requests to `max_requests` within `window_seconds`.
    """

    def __init__(self, max_requests: int = 15, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # key -> deque of timestamps
        self._history: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, client_key: str) -> tuple[bool, int]:
        """
        Checks if the request is allowed for client_key.
        Returns:
            (allowed: bool, retry_after: int)
        """
        now = time.time()
        cutoff = now - self.window_seconds
        timestamps = self._history[client_key]

        # Evict timestamps outside the sliding window
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        if len(timestamps) >= self.max_requests:
            oldest = timestamps[0]
            retry_after = max(1, int(oldest + self.window_seconds - now))
            return False, retry_after

        timestamps.append(now)
        return True, 0

    def reset(self) -> None:
        """Clears all stored rate limit history (useful for test isolation)."""
        self._history.clear()


# Default limiter: 15 requests per 60 seconds (1 minute) for regenerations
regeneration_limiter = SlidingWindowRateLimiter(max_requests=15, window_seconds=60)


def check_regeneration_rate_limit(
    request: Request,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> None:
    """
    FastAPI dependency that enforces rate limiting on regeneration endpoints.
    Identifies clients by X-API-Key or client IP address.
    """
    client_ip = request.client.host if request.client else "unknown"
    client_key = f"{x_api_key}:{client_ip}" if x_api_key else client_ip

    allowed, retry_after = regeneration_limiter.is_allowed(client_key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Slow down. Too many requests in 1 minute. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
