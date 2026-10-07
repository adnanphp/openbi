"""Redis cache layer for FastAPI endpoints.

Provides simple get/set helpers used at the data layer (after the DB
query, before returning). This is the "cache-aside" pattern.

If Redis is unreachable, all helpers degrade gracefully — the app keeps
working, just without caching. Caching is an optimization, not a
dependency.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

try:
    import redis
except ImportError:
    redis = None  # type: ignore

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis.redis.svc.cluster.local")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

_client: "redis.Redis | None" = None


def get_client() -> "redis.Redis | None":
    """Return a shared Redis client, or None if Redis is unavailable."""
    global _client
    if _client is not None:
        return _client
    if redis is None:
        logger.warning("redis library not installed; caching disabled")
        return None
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            decode_responses=True,
        )
        client.ping()
        _client = client
        logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        return _client
    except Exception as exc:
        logger.warning(f"Redis unavailable ({exc}); caching disabled")
        return None


def cache_get(key: str) -> Any | None:
    """Read a cached value. Returns None on miss or Redis failure."""
    client = get_client()
    if client is None:
        return None
    try:
        raw = client.get(f"openbi:{key}")
        if raw is None:
            _safe_incr("openbi:stats:misses")
            return None
        _safe_incr("openbi:stats:hits")
        return json.loads(raw)
    except Exception as exc:
        logger.warning(f"cache_get failed for {key}: {exc}")
        return None


def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """Store a value in cache with a TTL (in seconds)."""
    client = get_client()
    if client is None:
        return
    try:
        client.setex(f"openbi:{key}", ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning(f"cache_set failed for {key}: {exc}")


def invalidate(pattern: str) -> int:
    """Delete keys matching a pattern. Returns count deleted."""
    client = get_client()
    if client is None:
        return 0
    deleted = 0
    try:
        for key in client.scan_iter(match=f"openbi:{pattern}"):
            client.delete(key)
            deleted += 1
    except Exception as exc:
        logger.warning(f"invalidate failed: {exc}")
    return deleted


def get_stats() -> dict[str, Any]:
    """Return cache connection status and hit/miss statistics."""
    client = get_client()
    if client is None:
        return {"connected": False, "hits": 0, "misses": 0, "keys": 0}
    try:
        hits = int(client.get("openbi:stats:hits") or 0)
        misses = int(client.get("openbi:stats:misses") or 0)
        keys = int(client.dbsize())
        total = hits + misses
        return {
            "connected": True,
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / total, 4) if total > 0 else 0.0,
            "keys": keys,
            "host": f"{REDIS_HOST}:{REDIS_PORT}",
        }
    except Exception as exc:
        return {"connected": False, "error": str(exc), "hits": 0, "misses": 0, "keys": 0}


def _safe_incr(key: str) -> None:
    client = get_client()
    if client is None:
        return
    try:
        client.incr(key)
    except Exception:
        pass
