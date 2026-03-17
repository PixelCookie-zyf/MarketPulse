from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.cache import cache_get, cache_set
from app.fetchers.akshare_fetcher import AKShareFetcher

router = APIRouter(prefix="/api/v1", tags=["chart"])


@router.get("/chart/intraday")
async def get_intraday(
    symbol: str = Query(..., description="Symbol like sh000001, XAU, IXIC"),
    period: str = Query("1d", description="1d or 5d"),
) -> dict:
    cache_key = f"chart:{symbol}:{period}"
    cached = await cache_get(cache_key)
    if cached:
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "symbol": symbol, "period": period, "data": cached}

    fetcher = AKShareFetcher()

    if symbol.startswith("sh") or symbol.startswith("sz"):
        # A-share index
        if period == "5d":
            data = await fetcher.fetch_index_daily_history(symbol, days=5)
        else:
            data = await fetcher.fetch_index_intraday(symbol)
    else:
        # Commodity
        if period == "5d":
            data = await fetcher.fetch_commodity_5d(symbol)
        else:
            data = await fetcher.fetch_commodity_intraday(symbol)

    ttl = 300 if period == "1d" else 1800  # 5 min for intraday, 30 min for 5d
    if data:
        await cache_set(cache_key, data, ttl=ttl)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "period": period,
        "data": data,
    }
