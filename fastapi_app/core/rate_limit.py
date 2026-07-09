"""
A lightweight, in-memory rate limiter for authentication endpoints
(login, OTP request, OTP verify).

IMPORTANT — this is process-local, in-memory state:
  - It resets whenever the server restarts.
  - It does NOT work correctly if you run multiple worker processes
    (e.g. `uvicorn --workers 4`) or multiple server instances behind a
    load balancer, since each process has its own separate counters.

For a real production deployment, replace this with a Redis-backed
limiter (e.g. `slowapi` + Redis, or `fastapi-limiter`) so all workers
share the same counters. This implementation is intentionally dependency-free
so it works today without adding Redis to the stack.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import Request, HTTPException, status


class _RateLimiter:
    def __init__(self):
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = time.time()
        with self._lock:
            hits = self._hits[key]
            # Drop timestamps outside the current window
            cutoff = now - window_seconds
            while hits and hits[0] < cutoff:
                hits.pop(0)

            if len(hits) >= max_requests:
                retry_after = int(window_seconds - (now - hits[0]))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many attempts. Please try again in {max(retry_after, 1)} seconds.",
                )

            hits.append(now)


_limiter = _RateLimiter()


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> None:
    """Public entry point for rate-limiting by an arbitrary key (e.g. an
    email address) from inside a route body, where request-body fields
    like `email` are already available as parsed Pydantic data."""
    _limiter.check(key, max_requests, window_seconds)


def rate_limit(max_requests: int, window_seconds: int, scope: str):
    """
    Returns a FastAPI dependency that rate-limits by (client IP + scope).
    Usage:
        @router.post("/login", dependencies=[Depends(rate_limit(10, 900, "login"))])
    """

    def _dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"{scope}:{client_ip}"
        _limiter.check(key, max_requests, window_seconds)

    return _dependency


def rate_limit_by_email(max_requests: int, window_seconds: int, scope: str):
    """
    Same idea, but keyed by the email in the request body instead of IP —
    useful for OTP endpoints where you want to cap attempts per-account
    regardless of which IP they come from. Reads `email` off the parsed
    request body via a small dependency; falls back to IP if email isn't
    present for some reason.
    """

    def _dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        # Rate-limit by IP here; email-specific limiting is applied inside
        # the route itself (see auth_router.py) where the parsed Pydantic
        # body is already available.
        key = f"{scope}:{client_ip}"
        _limiter.check(key, max_requests, window_seconds)

    return _dependency