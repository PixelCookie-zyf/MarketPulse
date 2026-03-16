from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import redis.asyncio as redis

from app.config import settings

_redis_client: redis.Redis | None = None
_memory_cache: dict[str, str] = {}
_backend_name = "uninitialized"


async def init_cache() -> None:
    global _redis_client, _backend_name

    if settings.cache_backend == "memory":
        _backend_name = "memory"
        return

    try:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await _redis_client.ping()
        _backend_name = "redis"
    except Exception:
        if settings.cache_backend == "redis":
            raise
        _redis_client = None
        _backend_name = "memory"


async def close_cache() -> None:
    global _redis_client, _memory_cache, _backend_name

    if _redis_client is not None:
        await _redis_client.aclose()
    _redis_client = None
    _memory_cache = {}
    _backend_name = "uninitialized"


def get_cache_backend_name() -> str:
    return _backend_name


async def cache_set(key: str, data: Any, ttl: int = 60) -> None:
    payload = json.dumps(data, ensure_ascii=False, default=_json_default)
    if _backend_name == "redis" and _redis_client is not None:
        await _redis_client.set(key, payload, ex=ttl)
        return

    _memory_cache[key] = payload


async def cache_get(key: str) -> Any | None:
    if _backend_name == "redis" and _redis_client is not None:
        raw = await _redis_client.get(key)
    else:
        raw = _memory_cache.get(key)

    if raw is None:
        return None
    return json.loads(raw)


def _json_default(value: Any) -> Any:
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")
