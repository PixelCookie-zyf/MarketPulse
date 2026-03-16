from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache import cache_get
from app import scheduler

router = APIRouter(prefix="/api/v1", tags=["sectors"])


@router.get("/sectors/cn")
async def get_cn_sectors() -> dict:
    sectors = await cache_get("sectors:cn")
    if not sectors:
        await scheduler.ensure_market_data(include={"sectors"})
        sectors = await cache_get("sectors:cn")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": sectors or [],
    }
