from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import httpx

from app.cache import cache_set
from app.config import settings
from app.fetchers.base import to_float

BASE_URL = "https://www.alphavantage.co/query"


@dataclass(frozen=True)
class AVQuoteSpec:
    source_symbol: str
    market_symbol: str
    name: str


@dataclass(frozen=True)
class AVCommoditySpec:
    symbol: str
    function: str
    name: str
    name_en: str
    unit: str
    interval: str = "monthly"


US_INDEX_SPECS = (
    AVQuoteSpec(source_symbol="QQQ", market_symbol="IXIC", name="纳斯达克"),
    AVQuoteSpec(source_symbol="SPY", market_symbol="SPX", name="标普500"),
    AVQuoteSpec(source_symbol="DIA", market_symbol="DJI", name="道琼斯"),
)

JP_KR_INDEX_SPECS = (
    AVQuoteSpec(source_symbol="EWJ", market_symbol="N225", name="日经225"),
    AVQuoteSpec(source_symbol="EWY", market_symbol="KOSPI", name="韩国KOSPI"),
)

COMMODITY_SPECS = (
    AVCommoditySpec(symbol="COPPER", function="COPPER", name="铜", name_en="Copper", unit="USD/ton", interval="monthly"),
)

_rate_limit_lock = asyncio.Lock()
_last_request_monotonic = 0.0


def is_rate_limited_response(payload: dict) -> bool:
    message = " ".join(str(payload.get(key, "")) for key in ("Information", "Note"))
    lowered = message.lower()
    return "alpha vantage" in lowered and (
        "rate limit" in lowered or "spreading out your free api requests" in lowered
    )


def extract_global_quote_item(payload: dict, spec: AVQuoteSpec) -> dict | None:
    if not payload:
        return None

    return {
        "symbol": spec.market_symbol,
        "name": spec.name,
        "value": round(to_float(payload.get("05. price")), 4),
        "change": round(to_float(payload.get("09. change")), 4),
        "change_pct": round(to_float(str(payload.get("10. change percent", "0")).replace("%", "")), 4),
        "high": round(to_float(payload.get("03. high")), 4),
        "low": round(to_float(payload.get("04. low")), 4),
        "volume": to_float(payload.get("06. volume")),
        "sparkline": [],
    }


def extract_commodity_item(payload: dict, spec: AVCommoditySpec) -> dict | None:
    entries = payload.get("data") or []
    if not entries:
        return None

    latest = entries[0]
    current = to_float(latest.get("value"))
    previous = to_float(entries[1].get("value"), current) if len(entries) > 1 else current
    change = current - previous
    change_pct = (change / previous * 100) if previous else 0.0
    price = round(current, 4)

    return {
        "symbol": spec.symbol,
        "name": spec.name,
        "name_en": spec.name_en,
        "price": price,
        "change": round(change, 4),
        "change_pct": round(change_pct, 2),
        "high": price,
        "low": price,
        "unit": spec.unit,
    }


class AlphaVantageFetcher:
    def __init__(self, api_key: str | None = None, timeout: float = 20.0):
        self.api_key = api_key or settings.alphavantage_key
        self.timeout = timeout

    async def fetch_us_indices(self) -> list[dict]:
        items = await self._fetch_quotes(US_INDEX_SPECS)
        await cache_set("indices:us", items, ttl=settings.cache_ttl_index)
        return items

    async def fetch_jpkr_indices(self) -> tuple[list[dict], list[dict]]:
        items = await self._fetch_quotes(JP_KR_INDEX_SPECS)
        jp = [item for item in items if item["symbol"] == "N225"]
        kr = [item for item in items if item["symbol"] == "KOSPI"]
        await cache_set("indices:jp", jp, ttl=settings.cache_ttl_index)
        await cache_set("indices:kr", kr, ttl=settings.cache_ttl_index)
        return jp, kr

    async def fetch_commodities(self) -> list[dict]:
        items: list[dict] = []
        for spec in COMMODITY_SPECS:
            payload = await self._request(
                {
                    "function": spec.function,
                    "interval": spec.interval,
                    "apikey": self.api_key,
                }
            )
            if not payload or is_rate_limited_response(payload):
                continue

            item = extract_commodity_item(payload, spec)
            if item is not None:
                items.append(item)

        await cache_set("commodities:av", items, ttl=settings.cache_ttl_commodity)
        return items

    async def _fetch_quotes(self, specs: tuple[AVQuoteSpec, ...]) -> list[dict]:
        items: list[dict] = []
        for spec in specs:
            payload = await self._request(
                {
                    "function": "GLOBAL_QUOTE",
                    "symbol": spec.source_symbol,
                    "apikey": self.api_key,
                }
            )
            if not payload or is_rate_limited_response(payload):
                continue

            item = extract_global_quote_item(payload.get("Global Quote", {}), spec)
            if item is not None:
                items.append(item)
        return items

    async def _request(self, params: dict[str, str]) -> dict:
        if not self.api_key:
            return {}

        payload = await self._perform_request(params)
        if is_rate_limited_response(payload):
            await asyncio.sleep(5)
            payload = await self._perform_request(params)
        return payload

    async def _perform_request(self, params: dict[str, str]) -> dict:
        await self._throttle()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(BASE_URL, params=params)
            response.raise_for_status()
            return response.json()

    async def _throttle(self) -> None:
        global _last_request_monotonic

        async with _rate_limit_lock:
            now = time.monotonic()
            remaining = 1.1 - (now - _last_request_monotonic)
            if remaining > 0:
                await asyncio.sleep(remaining)
            _last_request_monotonic = time.monotonic()
