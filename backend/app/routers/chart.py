from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.cache import cache_get, cache_set
from app.fetchers.akshare_fetcher import AKShareFetcher
from app.fetchers.eastmoney_proxy_fetcher import EastmoneyProxyFetcher, is_commodity_symbol, is_global_index_symbol

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
    data: list[dict] = []

    if symbol.startswith("sh") or symbol.startswith("sz"):
        # A-share index
        if period == "5d":
            data = await fetcher.fetch_index_daily_history(symbol, days=5)
        else:
            data = await fetcher.fetch_index_intraday(symbol)
    elif is_global_index_symbol(symbol):
        data = await fetcher.fetch_global_index_chart(symbol, period)
    elif is_commodity_symbol(symbol):
        # Commodity chart via Cloudflare proxy (USD-denominated kline)
        proxy = EastmoneyProxyFetcher()
        data = await proxy.fetch_commodity_chart(symbol, period)

    ttl = 300 if period == "1d" else 1800
    if data:
        await cache_set(cache_key, data, ttl=ttl)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "period": period,
        "data": data,
    }
