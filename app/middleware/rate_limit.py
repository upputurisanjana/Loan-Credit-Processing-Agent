"""
app/middleware/rate_limit.py — lightweight sliding-window rate limiter.

No external dependencies — uses a simple in-process deque per client IP.

Configuration (via environment variables):
    RATE_LIMIT_REQUESTS  — max requests per window (default: 10)
    RATE_LIMIT_WINDOW    — window size in seconds (default: 60)

POST /applications is the expensive endpoint (3 LLM calls).
All routes share the same per-IP counter to prevent amplification via
other endpoints.

For production, replace with a Redis-backed limiter (e.g. slowapi + Redis)
to share state across multiple workers.
"""

import logging
import os
import time
from collections import defaultdict, deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

log = logging.getLogger(__name__)

_RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "10"))
_RATE_LIMIT_WINDOW   = int(os.environ.get("RATE_LIMIT_WINDOW",   "60"))

# client_ip → deque of request timestamps (float seconds)
_request_log: dict[str, deque] = defaultdict(deque)


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For if present."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter.

    Returns HTTP 429 with Retry-After header when a client exceeds
    RATE_LIMIT_REQUESTS within RATE_LIMIT_WINDOW seconds.

    Only applies to state-mutating endpoints (POST/PUT/PATCH).
    GET requests are not counted — they are cheap reads.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only limit write operations
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        client_ip = _get_client_ip(request)
        now = time.monotonic()
        window_start = now - _RATE_LIMIT_WINDOW

        timestamps = _request_log[client_ip]

        # Evict timestamps outside the current window
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        if len(timestamps) >= _RATE_LIMIT_REQUESTS:
            oldest = timestamps[0]
            retry_after = int(_RATE_LIMIT_WINDOW - (now - oldest)) + 1
            log.warning(
                "rate_limit: ip=%s exceeded %d requests in %ds — returning 429",
                client_ip, _RATE_LIMIT_REQUESTS, _RATE_LIMIT_WINDOW,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded: max {_RATE_LIMIT_REQUESTS} "
                        f"requests per {_RATE_LIMIT_WINDOW}s. "
                        f"Retry after {retry_after}s."
                    )
                },
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
        return await call_next(request)
