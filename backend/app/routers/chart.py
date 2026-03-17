from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.cache import cache_get, cache_set
from app.fetchers.akshare_fetcher import AKShareFetcher, EM_GLOBAL_INDEX_MAP

router = APIRouter(prefix="/api/v1", tags=["chart"])

# Known global index symbols
GLOBAL_INDEX_SYMBOLS = {spec["symbol"] for spec in EM_GLOBAL_INDEX_MAP.values()}


def _classify_symbol(symbol: str) -> str:
    if symbol.startswith("sh") or symbol.startswith("sz"):
        return "cn_index"
    if symbol in GLOBAL_INDEX_SYMBOLS:
        return "global_index"
    return "commodity"


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
    data: list[dict] = []
    kind = _classify_symbol(symbol)

    if kind == "cn_index":
        if period == "5d":
            data = await fetcher.fetch_index_daily_history(symbol, days=5)
        else:
            data = await fetcher.fetch_index_intraday(symbol)

    elif kind == "global_index":
        days = 5 if period == "5d" else 1
        data = await fetcher.fetch_global_index_chart(symbol, days=days)

    else:  # commodity
        if period == "5d":
            data = await fetcher.fetch_commodity_5d(symbol)
        else:
            data = await fetcher.fetch_commodity_intraday(symbol)

    ttl = 300 if period == "1d" else 1800
    if data:
        await cache_set(cache_key, data, ttl=ttl)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "period": period,
        "data": data,
    }
