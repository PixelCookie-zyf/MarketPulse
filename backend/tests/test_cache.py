import pytest

from app.cache import cache_get, cache_set, close_cache, get_cache_backend_name, init_cache


@pytest.mark.asyncio
async def test_memory_cache_round_trip():
    await init_cache()

    payload = {"symbol": "XAU", "price": 2650.3}
    await cache_set("commodities:test", payload, ttl=30)

    assert await cache_get("commodities:test") == payload
    assert get_cache_backend_name() == "memory"

    await close_cache()
