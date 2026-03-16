from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache import cache_get
from app.fetchers.base import default_index_groups

router = APIRouter(prefix="/api/v1", tags=["overview"])


def _empty_groups() -> dict[str, list]:
    return default_index_groups()


@router.get("/overview")
async def get_overview() -> dict:
    commodities = await cache_get("commodities:all")
    if commodities is None:
        commodities = (await cache_get("commodities:metals") or []) + (await cache_get("commodities:av") or [])

    groups = await cache_get("indices:groups")
    if groups is None:
        groups = _empty_groups()
        for key in groups:
            groups[key] = await cache_get(f"indices:{key}") or []

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commodities": commodities,
        "indices": groups,
        "sectors": await cache_get("sectors:cn") or [],
    }
