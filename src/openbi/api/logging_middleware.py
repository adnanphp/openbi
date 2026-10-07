"""Structured JSON logging middleware.

Every HTTP request is logged as a single JSON line with:
  - timestamp
  - level
  - request_id (UUID, also returned in X-Request-ID response header)
  - method, path, status, duration_ms
  - client_ip

The output is stdout in JSON Lines format — the standard input format
for log aggregation systems (Loki, CloudWatch Logs, Cloud Logging).
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def configure_root_logger() -> None:
    """Send all logs to stdout as JSON Lines."""
    root = logging.getLogger()
    if root.handlers:
        return  # already configured

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request as one JSON line to stdout."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        response: Response
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            self._log(
                level="ERROR",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status=500,
                duration_ms=duration_ms,
                client_ip=self._client_ip(request),
                error=str(exc),
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        self._log(
            level="INFO",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            client_ip=self._client_ip(request),
        )

        response.headers["X-Request-ID"] = request_id
        return response

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    @staticmethod
    def _log(**fields) -> None:
        fields["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(json.dumps(fields), flush=True)
