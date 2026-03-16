from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.cache import cache_get, cache_set
from app.fetchers.akshare_fetcher import AKShareFetcher
from app.fetchers.alphavantage_fetcher import AlphaVantageFetcher
from app.fetchers.base import default_index_groups
from app.fetchers.goldapi_fetcher import GoldAPIFetcher

_scheduler: AsyncIOScheduler | None = None


def build_job_specs() -> list[dict]:
    return [
        {"id": "cn_indices", "minutes": 1, "func": refresh_cn_indices},
        {"id": "cn_sectors", "minutes": 3, "func": refresh_cn_sectors},
        {"id": "gold_metals", "minutes": 15, "func": refresh_gold_metals},
        {"id": "alpha_indices", "hours": 12, "func": refresh_alpha_indices},
        {"id": "alpha_commodities", "hours": 12, "func": refresh_alpha_commodities},
    ]


async def refresh_cn_indices() -> dict[str, list]:
    fetcher = AKShareFetcher()
    cn, hk = await asyncio.gather(fetcher.fetch_cn_indices(), fetcher.fetch_hk_index())
    groups = await _load_index_groups()
    groups["cn"] = cn
    groups["hk"] = hk
    await cache_set("indices:groups", groups)
    return groups


async def refresh_cn_sectors() -> list[dict]:
    fetcher = AKShareFetcher()
    return await fetcher.fetch_cn_sectors()


async def refresh_gold_metals() -> list[dict]:
    fetcher = GoldAPIFetcher()
    metals = await fetcher.fetch_precious_metals()
    await _refresh_combined_commodities(metals=metals)
    return metals


async def refresh_alpha_indices() -> dict[str, list]:
    fetcher = AlphaVantageFetcher()
    us, jpkr = await asyncio.gather(fetcher.fetch_us_indices(), fetcher.fetch_jpkr_indices())
    jp, kr = jpkr
    groups = await _load_index_groups()
    groups["us"] = us
    groups["jp"] = jp
    groups["kr"] = kr
    await cache_set("indices:groups", groups)
    return groups


async def refresh_alpha_commodities() -> list[dict]:
    fetcher = AlphaVantageFetcher()
    commodities = await fetcher.fetch_commodities()
    await _refresh_combined_commodities(av=commodities)
    return commodities


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
    loop.create_task(refresh_alpha_indices())
    loop.create_task(refresh_alpha_commodities())


def stop_scheduler() -> None:
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
    _scheduler = None


async def _load_index_groups() -> dict[str, list]:
    groups = await cache_get("indices:groups") or default_index_groups()
    return {key: groups.get(key, []) for key in default_index_groups()}


async def _refresh_combined_commodities(metals: list[dict] | None = None, av: list[dict] | None = None) -> None:
    metal_items = metals if metals is not None else (await cache_get("commodities:metals") or [])
    av_items = av if av is not None else (await cache_get("commodities:av") or [])
    await cache_set("commodities:all", metal_items + av_items)
