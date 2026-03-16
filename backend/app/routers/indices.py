from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache import cache_get
from app.fetchers.base import default_index_groups
from app import scheduler

router = APIRouter(prefix="/api/v1", tags=["indices"])


def _empty_groups() -> dict[str, list]:
    return default_index_groups()


@router.get("/indices/global")
async def get_global_indices() -> dict:
    groups = await _load_groups()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {key: groups.get(key, []) for key in ("us", "jp", "kr", "hk")},
    }


@router.get("/indices/cn")
async def get_cn_indices() -> dict:
    groups = await _load_groups()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": groups.get("cn", []),
    }


async def _load_groups() -> dict[str, list]:
    groups = await cache_get("indices:groups")
    if groups is not None and any(groups.get(key) for key in _empty_groups()):
        return groups

    await scheduler.ensure_market_data(include={"indices"})
    groups = await cache_get("indices:groups")
    if groups is not None:
        return groups

    defaults = _empty_groups()
    for key in defaults:
        defaults[key] = await cache_get(f"indices:{key}") or []
    return defaults
