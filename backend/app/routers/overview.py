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
    if not commodities and not has_indices and not sectors:
        await scheduler.ensure_market_data(include={"commodities", "indices", "sectors"})
        commodities = await scheduler.load_combined_commodities()
        groups = await cache_get("indices:groups")
        sectors = await cache_get("sectors:cn")

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
