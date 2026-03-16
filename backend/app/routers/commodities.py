from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache import cache_get
from app import scheduler

router = APIRouter(prefix="/api/v1", tags=["commodities"])


@router.get("/commodities")
async def get_commodities() -> dict:
    combined = await cache_get("commodities:all")
    if not combined:
        await scheduler.ensure_market_data(include={"commodities"})
        combined = await cache_get("commodities:all")

    if combined is None:
        combined = (await cache_get("commodities:metals") or []) + (await cache_get("commodities:stooq") or [])

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": combined,
    }
