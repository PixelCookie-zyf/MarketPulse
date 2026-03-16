from __future__ import annotations

import asyncio
import csv
from dataclasses import dataclass
from io import StringIO

import httpx

from app.cache import cache_set
from app.config import settings
from app.fetchers.base import build_sparkline, to_float

QUOTE_URL = "https://stooq.com/q/l/"
HISTORY_URL = "https://stooq.com/q/d/l/"
USER_AGENT = "Mozilla/5.0 (MarketPulse)"


@dataclass(frozen=True)
class StooqIndexSpec:
    symbol: str
    market_symbol: str
    name: str


@dataclass(frozen=True)
class StooqCommoditySpec:
    symbol: str
    market_symbol: str
    name: str
    name_en: str
    unit: str


STQ_US_INDEX_SPECS = (
    StooqIndexSpec(symbol="^ndq", market_symbol="IXIC", name="纳斯达克"),
    StooqIndexSpec(symbol="^spx", market_symbol="SPX", name="标普500"),
    StooqIndexSpec(symbol="^dji", market_symbol="DJI", name="道琼斯"),
)

STQ_COMMODITY_SPECS = (
    StooqCommoditySpec(symbol="cl.f", market_symbol="WTI", name="原油", name_en="Crude Oil", unit="USD/bbl"),
    StooqCommoditySpec(symbol="cb.f", market_symbol="BRENT", name="布伦特原油", name_en="Brent Oil", unit="USD/bbl"),
    StooqCommoditySpec(symbol="ng.f", market_symbol="NATGAS", name="天然气", name_en="Natural Gas", unit="USD/MMBtu"),
    StooqCommoditySpec(symbol="hg.f", market_symbol="COPPER", name="铜", name_en="Copper", unit="USc/lb"),
    StooqCommoditySpec(symbol="zc.f", market_symbol="CORN", name="玉米", name_en="Corn", unit="USc/bu"),
    StooqCommoditySpec(symbol="zw.f", market_symbol="WHEAT", name="小麦", name_en="Wheat", unit="USc/bu"),
    StooqCommoditySpec(symbol="ct.f", market_symbol="COTTON", name="棉花", name_en="Cotton", unit="USc/lb"),
    StooqCommoditySpec(symbol="sb.f", market_symbol="SUGAR", name="糖", name_en="Sugar", unit="USc/lb"),
    StooqCommoditySpec(symbol="kc.f", market_symbol="COFFEE", name="咖啡", name_en="Coffee", unit="USc/lb"),
)


def extract_stooq_index_item(body: str, spec: StooqIndexSpec, *, sparkline: list[float]) -> dict | None:
    parsed = _parse_quote_fields(body)
    if parsed is None:
        return None

    current = round(to_float(parsed["close"]), 4)
    previous = sparkline[-2] if len(sparkline) >= 2 else current
    change = current - previous
    change_pct = (change / previous * 100) if previous else 0.0
    high = round(to_float(parsed["high"], default=current), 4)
    low = round(to_float(parsed["low"], default=current), 4)
    volume = to_float(parsed["volume"], default=0.0)

    return {
        "symbol": spec.market_symbol,
        "name": spec.name,
        "value": current,
        "change": round(change, 4),
        "change_pct": round(change_pct, 4),
        "high": high,
        "low": low,
        "volume": volume,
        "sparkline": sparkline,
    }


def extract_stooq_commodity_item(body: str, spec: StooqCommoditySpec) -> dict | None:
    parsed = _parse_quote_fields(body)
    if parsed is None:
        return None

    price = round(to_float(parsed["close"]), 4)
    opened = to_float(parsed["open"], default=price)
    change = price - opened
    change_pct = (change / opened * 100) if opened else 0.0
    high = round(to_float(parsed["high"], default=price), 4)
    low = round(to_float(parsed["low"], default=price), 4)

    return {
        "symbol": spec.market_symbol,
        "name": spec.name,
        "name_en": spec.name_en,
        "price": price,
        "change": round(change, 4),
        "change_pct": round(change_pct, 2),
        "high": high,
        "low": low,
        "unit": spec.unit,
    }


class StooqFetcher:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def fetch_us_indices(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": USER_AGENT}) as client:
            tasks = [self._fetch_index_item(client, spec) for spec in STQ_US_INDEX_SPECS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        items = [item for item in results if isinstance(item, dict)]
        await cache_set("indices:us", items, ttl=settings.cache_ttl_index)
        return items

    async def fetch_commodities(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": USER_AGENT}) as client:
            results = []
            for spec in STQ_COMMODITY_SPECS:
                try:
                    results.append(await self._fetch_commodity_item(client, spec))
                except Exception:
                    results.append(None)

        items = [item for item in results if isinstance(item, dict)]
        await cache_set("commodities:stooq", items, ttl=settings.cache_ttl_commodity)
        return items

    async def _fetch_index_item(self, client: httpx.AsyncClient, spec: StooqIndexSpec) -> dict | None:
        response = await self._get_with_retry(client, HISTORY_URL, {"s": spec.symbol, "i": "d"})
        lines = [line.strip() for line in response.text.splitlines() if line.strip()]
        if len(lines) < 3:
            return None

        sample = "\n".join([lines[0], *lines[-8:]])
        rows = list(csv.DictReader(StringIO(sample)))
        if not rows:
            return None

        closes = [row.get("Close", "") for row in rows]
        sparkline = build_sparkline(closes, limit=7)
        latest = rows[-1]
        body = ",".join(
            [
                latest.get("Date", ""),
                latest.get("Open", ""),
                latest.get("High", ""),
                latest.get("Low", ""),
                latest.get("Close", ""),
                latest.get("Volume", ""),
            ]
        )
        return extract_stooq_index_item(body, spec, sparkline=sparkline)

    async def _fetch_commodity_item(self, client: httpx.AsyncClient, spec: StooqCommoditySpec) -> dict | None:
        response = await self._get_with_retry(client, QUOTE_URL, {"s": spec.symbol, "i": "d"})
        body = _extract_quote_body(response.text, spec.symbol)
        if body is None:
            return None
        return extract_stooq_commodity_item(body, spec)

    async def _get_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, str],
        attempts: int = 2,
    ) -> httpx.Response:
        last_error: Exception | None = None
        for _ in range(attempts):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response
            except Exception as exc:  # pragma: no cover - exercised through live verification
                last_error = exc
                await asyncio.sleep(0.4)
        assert last_error is not None
        raise last_error


def _extract_quote_body(payload: str, expected_symbol: str) -> str | None:
    lines = [line.strip() for line in payload.splitlines() if line.strip()]
    if not lines:
        return None

    line = lines[0]
    prefix = f"{expected_symbol.upper()},"
    upper = line.upper()
    if not upper.startswith(prefix):
        return None

    body = line[len(prefix) :]
    if "N/D" in body:
        return None
    return body


def _parse_body_fields(body: str) -> list[str]:
    fields = [field.strip() for field in body.split(",")]
    while fields and fields[-1] == "":
        fields.pop()
    if any(field == "N/D" for field in fields):
        return []
    return fields


def _parse_quote_fields(body: str) -> dict[str, str] | None:
    fields = _parse_body_fields(body)
    if len(fields) < 5:
        return None

    if len(fields) >= 6 and fields[1].isdigit():
        _, _, opened, high, low, close, *rest = fields
    else:
        _, opened, high, low, close, *rest = fields

    volume = rest[0] if rest else ""
    return {
        "open": opened,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }
