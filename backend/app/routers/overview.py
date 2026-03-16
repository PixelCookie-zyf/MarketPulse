import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache import cache_get
from app.fetchers.base import default_index_groups
from app import scheduler

router = APIRouter(prefix="/api/v1", tags=["overview"])


def _empty_groups() -> dict[str, list]:
    return default_index_groups()


@router.get("/overview")
async def get_overview() -> dict:
    commodities = await scheduler.load_combined_commodities()
    groups = await cache_get("indices:groups")
    sectors = await cache_get("sectors:cn")

    has_indices = bool(groups) and any(groups.get(key) for key in _empty_groups())
    has_data = bool(commodities) or has_indices or bool(sectors)

    if not has_data:
        # Only block on first-ever request when cache is completely empty.
        await scheduler.ensure_market_data(include={"commodities", "indices", "sectors"})
        commodities = await scheduler.load_combined_commodities()
        groups = await cache_get("indices:groups")
        sectors = await cache_get("sectors:cn")
    elif not commodities or not has_indices or not sectors:
        # Some data exists — return it immediately and refresh missing parts in background.
        missing: set[str] = set()
        if not commodities:
            missing.add("commodities")
        if not has_indices:
            missing.add("indices")
        if not sectors:
            missing.add("sectors")
        asyncio.create_task(scheduler.ensure_market_data(include=missing))

    if groups is None:
        groups = _empty_groups()
        for key in groups:
            groups[key] = await cache_get(f"indices:{key}") or []

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commodities": commodities,
        "indices": groups,
        "sectors": sectors or [],
    }
