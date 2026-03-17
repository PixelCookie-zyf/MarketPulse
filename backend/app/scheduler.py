from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.cache import cache_get, cache_set
from app.config import settings
from app.fetchers.akshare_fetcher import AKShareFetcher
from app.fetchers.alphavantage_fetcher import AlphaVantageFetcher
from app.fetchers.base import default_index_groups
from app.fetchers.goldapi_fetcher import GoldAPIFetcher
from app.fetchers.stooq_fetcher import StooqFetcher

_scheduler: AsyncIOScheduler | None = None
_refresh_lock = asyncio.Lock()

# Cache TTLs — must be LONGER than the scheduler interval for the same data,
# so the cache never expires between scheduled refreshes.
_INDEX_GROUP_TTL = 7200       # 2 hours (global indices refresh every 1h)
_COMMODITY_ALL_TTL = 7200     # 2 hours (stooq commodities refresh every 1h)

COMBINED_COMMODITY_SYMBOLS = (
    "XAU",
    "XAG",
    "WTI",
    "BRENT",
    "NATGAS",
    "COPPER",
    "CORN",
    "WHEAT",
    "COTTON",
    "SUGAR",
    "COFFEE",
)
STABLE_COMMODITY_CACHE_KEY = "commodities:em"


def build_job_specs() -> list[dict]:
    return [
        {"id": "cn_indices", "minutes": 1, "func": refresh_cn_indices},
        {"id": "cn_sectors", "minutes": 3, "func": refresh_cn_sectors},
        {"id": "gold_metals", "minutes": 15, "func": refresh_gold_metals},
        {"id": "global_indices", "minutes": 5, "func": refresh_global_indices},
        {"id": "em_commodities", "minutes": 5, "func": refresh_em_commodities},
    ]


async def refresh_cn_indices() -> dict[str, list]:
    akshare = AKShareFetcher()
    cn = await akshare.fetch_cn_indices()
    groups = await _load_index_groups()
    groups["cn"] = cn
    await cache_set("indices:groups", groups, ttl=_INDEX_GROUP_TTL)
    return groups


async def refresh_cn_sectors() -> list[dict]:
    fetcher = AKShareFetcher()
    return await fetcher.fetch_cn_sectors()


async def refresh_gold_metals() -> list[dict]:
    fetcher = GoldAPIFetcher()
    metals = await fetcher.fetch_precious_metals()
    await _refresh_combined_commodities(metals=metals)
    return metals


async def refresh_global_indices() -> dict[str, list]:
    try:
        akshare = AKShareFetcher()
        result = await akshare.fetch_global_indices()
        groups = await _load_index_groups()
        # Only overwrite if we got actual data
        for key in ("us", "jp", "kr", "hk"):
            items = result.get(key, [])
            if items:
                groups[key] = items
        await cache_set("indices:groups", groups, ttl=_INDEX_GROUP_TTL)
        return groups
    except Exception as e:
        print(f"[Scheduler] refresh_global_indices error: {e}")
        return await _load_index_groups()


async def refresh_em_commodities() -> list[dict]:
    """Fetch commodities from Eastmoney (via AKShare) — works from China."""
    akshare = AKShareFetcher()
    commodities = await akshare.fetch_global_commodities()
    await _refresh_combined_commodities(stooq=commodities)
    return commodities


async def ensure_market_data(*, include: set[str] | None = None) -> None:
    requested = include or {"commodities", "indices", "sectors"}

    async with _refresh_lock:
        jobs: list = []

        if "commodities" in requested:
            commodities = await cache_get("commodities:all")
            if not commodities:
                jobs.extend((refresh_gold_metals(), refresh_em_commodities()))

        if "indices" in requested:
            groups = await cache_get("indices:groups")
            has_indices = bool(groups) and any(groups.get(key) for key in default_index_groups())
            if not has_indices:
                jobs.extend((refresh_cn_indices(), refresh_global_indices()))

        if "sectors" in requested:
            sectors = await cache_get("sectors:cn")
            if not sectors:
                jobs.append(refresh_cn_sectors())

        if jobs:
            await asyncio.gather(*jobs)


def start_scheduler() -> None:
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        return

    _scheduler = AsyncIOScheduler()
    for spec in build_job_specs():
        trigger_args = {key: value for key, value in spec.items() if key in {"minutes", "hours"}}
        _scheduler.add_job(spec["func"], "interval", id=spec["id"], replace_existing=True, **trigger_args)
    _scheduler.start()

    loop = asyncio.get_running_loop()
    loop.create_task(refresh_cn_indices())
    loop.create_task(refresh_cn_sectors())
    loop.create_task(refresh_gold_metals())
    loop.create_task(refresh_global_indices())
    loop.create_task(refresh_em_commodities())


def stop_scheduler() -> None:
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
    _scheduler = None


async def _load_index_groups() -> dict[str, list]:
    groups = await cache_get("indices:groups") or default_index_groups()
    return {key: groups.get(key, []) for key in default_index_groups()}


async def _refresh_combined_commodities(
    metals: list[dict] | None = None,
    stooq: list[dict] | None = None,
) -> None:
    metal_items = metals if metals is not None else (await cache_get("commodities:metals") or [])
    stooq_items = stooq if stooq is not None else (await cache_get(STABLE_COMMODITY_CACHE_KEY) or [])
    await cache_set("commodities:all", _merge_commodity_items(metal_items, stooq_items), ttl=_COMMODITY_ALL_TTL)


async def load_combined_commodities() -> list[dict]:
    combined = await cache_get("commodities:all")
    if combined is not None:
        return _sort_commodities(combined)

    metal_items = await cache_get("commodities:metals") or []
    stooq_items = await cache_get(STABLE_COMMODITY_CACHE_KEY) or []
    combined = _merge_commodity_items(metal_items, stooq_items)
    if combined:
        await cache_set("commodities:all", combined, ttl=_COMMODITY_ALL_TTL)
    return combined


def _merge_commodity_items(metals: list[dict], stooq: list[dict]) -> list[dict]:
    deduped: dict[str, dict] = {}
    for item in [*metals, *stooq]:
        symbol = item.get("symbol")
        if symbol:
            deduped[str(symbol)] = item
    return _sort_commodities(list(deduped.values()))


def _sort_commodities(items: list[dict]) -> list[dict]:
    order = {symbol: index for index, symbol in enumerate(COMBINED_COMMODITY_SYMBOLS)}
    return sorted(items, key=lambda item: (order.get(str(item.get("symbol")), len(order)), str(item.get("symbol", ""))))
