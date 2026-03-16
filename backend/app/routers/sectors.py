from datetime import datetime, timezone

from fastapi import APIRouter

from app.cache import cache_get

router = APIRouter(prefix="/api/v1", tags=["sectors"])


@router.get("/sectors/cn")
async def get_cn_sectors() -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": await cache_get("sectors:cn") or [],
    }
