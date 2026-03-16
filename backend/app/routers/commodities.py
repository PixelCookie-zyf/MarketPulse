from datetime import datetime, timezone

from fastapi import APIRouter

from app import scheduler

router = APIRouter(prefix="/api/v1", tags=["commodities"])


@router.get("/commodities")
async def get_commodities() -> dict:
    combined = await scheduler.load_combined_commodities()
    if not combined:
        await scheduler.ensure_market_data(include={"commodities"})
        combined = await scheduler.load_combined_commodities()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": combined,
    }
