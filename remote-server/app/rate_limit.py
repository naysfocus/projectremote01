from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.dependencies import client_ip


@dataclass(frozen=True, slots=True)
class Limit:
    count: int
    window_seconds: int


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Small single-process limiter suitable for the current one-worker deployment."""

    def __init__(self, app, rules: dict[str, Limit]):  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.rules = rules
        self.events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        rule_key = f"{request.method.upper()} {request.url.path}"
        rule = self.rules.get(rule_key) or self.rules.get(request.url.path)
        if rule is None:
            return await call_next(request)

        now = time.monotonic()
        key = (client_ip(request), rule_key)
        with self.lock:
            bucket = self.events[key]
            cutoff = now - rule.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= rule.count:
                retry_after = max(1, int(rule.window_seconds - (now - bucket[0])))
                return JSONResponse(
                    status_code=429,
                    content={"ok": False, "error": "rate_limited", "retry_after": retry_after},
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)
        return await call_next(request)
