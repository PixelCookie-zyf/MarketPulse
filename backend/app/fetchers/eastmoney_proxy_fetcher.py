from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from app.config import settings
from app.fetchers.base import build_sparkline, to_float

USER_AGENT = "Mozilla/5.0 (MarketPulse)"
_EASTMONEY_PRICE_SCALE = 100.0


@dataclass(frozen=True)
class ProxyIndexSpec:
    upstream_code: str
    symbol: str
    name: str
    region: str


PROXY_US_INDEX_SPECS = (
    ProxyIndexSpec(upstream_code="DJIA", symbol="DJI", name="道琼斯", region="us"),
    ProxyIndexSpec(upstream_code="SPX", symbol="SPX", name="标普500", region="us"),
    ProxyIndexSpec(upstream_code="NDX", symbol="IXIC", name="纳斯达克", region="us"),
)

PROXY_REGIONAL_INDEX_SPECS = (
    ProxyIndexSpec(upstream_code="HSI", symbol="HSI", name="恒生指数", region="hk"),
    ProxyIndexSpec(upstream_code="N225", symbol="N225", name="日经225", region="jp"),
    ProxyIndexSpec(upstream_code="KS11", symbol="KOSPI", name="韩国KOSPI", region="kr"),
)

PROXY_GLOBAL_INDEX_SPECS = (*PROXY_US_INDEX_SPECS, *PROXY_REGIONAL_INDEX_SPECS)
US_GLOBAL_INDEX_SYMBOLS = frozenset({"IXIC", "SPX", "DJI"})
REGIONAL_GLOBAL_INDEX_SYMBOLS = frozenset(spec.symbol for spec in PROXY_REGIONAL_INDEX_SPECS)
GLOBAL_INDEX_SYMBOLS = US_GLOBAL_INDEX_SYMBOLS | REGIONAL_GLOBAL_INDEX_SYMBOLS


def is_global_index_symbol(symbol: str) -> bool:
    return symbol in GLOBAL_INDEX_SYMBOLS


def is_commodity_symbol(symbol: str) -> bool:
    return symbol in PROXY_COMMODITY_SYMBOLS


def extract_proxy_global_index_item(
    row: dict,
    spec: ProxyIndexSpec,
    *,
    sparkline: list[float] | None = None,
) -> dict:
    price = round(to_float(row.get("f2")) / _EASTMONEY_PRICE_SCALE, 4)
    change = round(to_float(row.get("f4")) / _EASTMONEY_PRICE_SCALE, 4)
    change_pct = round(to_float(row.get("f3")) / _EASTMONEY_PRICE_SCALE, 4)
    high = round(to_float(row.get("f15")) / _EASTMONEY_PRICE_SCALE, 4)
    low = round(to_float(row.get("f16")) / _EASTMONEY_PRICE_SCALE, 4)
    volume = to_float(row.get("f6"))
    return {
        "symbol": spec.symbol,
        "name": spec.name,
        "value": price,
        "change": change,
        "change_pct": change_pct,
        "high": high,
        "low": low,
        "volume": volume,
        "sparkline": sparkline or [],
    }


def extract_proxy_chart_items(payload: dict) -> list[dict]:
    rows = payload.get("data", {}).get("klines") or []
    items: list[dict] = []
    for row in rows:
        parts = str(row).split(",")
        if len(parts) < 6:
            continue
        items.append(
            {
                "time": parts[0],
                "price": round(to_float(parts[2]), 4),
                "volume": to_float(parts[5]),
            }
        )
    return items


# Commodity name mapping: futsseapi "name" → our spec
PROXY_COMMODITY_MAP = {
    "COMEX黄金": {"symbol": "XAU", "name": "黄金", "name_en": "Gold", "unit": "USD/oz"},
    "COMEX白银": {"symbol": "XAG", "name": "白银", "name_en": "Silver", "unit": "USD/oz"},
    "布伦特原油": {"symbol": "BRENT", "name": "布伦特原油", "name_en": "Brent Oil", "unit": "USD/bbl"},
    "COMEX铜": {"symbol": "COPPER", "name": "铜", "name_en": "Copper", "unit": "USD/lb"},
}

PROXY_COMMODITY_PRIORITY = ["XAU", "XAG", "BRENT", "COPPER"]
PROXY_COMMODITY_SYMBOLS = frozenset(spec["symbol"] for spec in PROXY_COMMODITY_MAP.values())


def _match_proxy_commodity_spec(name: str) -> dict | None:
    exact = PROXY_COMMODITY_MAP.get(name)
    if exact is not None:
        return exact
    for base_name, spec in PROXY_COMMODITY_MAP.items():
        if str(name).startswith(base_name):
            return spec
    return None


class EastmoneyProxyFetcher:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(settings.eastmoney_proxy_base_url)

    async def fetch_global_commodities(self) -> list[dict]:
        """Fetch commodity futures via Cloudflare proxy → futsseapi.eastmoney.com."""
        if not self.enabled:
            return []
        try:
            payload = await self._get_json("/global-commodities/spot")
        except Exception as e:
            print(f"[EastmoneyProxy] fetch_global_commodities error: {e}")
            return []

        rows = payload.get("list") or []
        items: list[dict] = []
        seen_symbols: set[str] = set()
        for row in rows:
            name = str(row.get("name", "")).strip()
            spec = _match_proxy_commodity_spec(name)
            if spec is None or spec["symbol"] in seen_symbols:
                continue
            price = to_float(row.get("p"))
            if not price or price == 0:
                continue
            seen_symbols.add(spec["symbol"])
            prev = to_float(row.get("zjsj"), default=price)
            change = to_float(row.get("zde"), default=price - prev)
            change_pct = to_float(row.get("zdf"), default=(change / prev * 100) if prev else 0.0)
            items.append({
                "symbol": spec["symbol"],
                "name": spec["name"],
                "name_en": spec["name_en"],
                "price": round(price, 4),
                "change": round(change, 4),
                "change_pct": round(change_pct, 2),
                "high": round(to_float(row.get("h"), default=price), 4),
                "low": round(to_float(row.get("l"), default=price), 4),
                "unit": spec["unit"],
            })
        order = {s: i for i, s in enumerate(PROXY_COMMODITY_PRIORITY)}
        items.sort(key=lambda x: order.get(x["symbol"], 999))
        return items

    async def fetch_global_indices(self) -> dict[str, list[dict]]:
        groups = {spec.region: [] for spec in PROXY_GLOBAL_INDEX_SPECS}
        if not self.enabled:
            return groups

        payload = await self._get_json("/global-indices/spot")
        rows = payload.get("data", {}).get("diff") or []
        spec_by_code = {spec.upstream_code: spec for spec in PROXY_GLOBAL_INDEX_SPECS}
        sparkline_map = await self.fetch_global_index_sparkline_map([spec.symbol for spec in PROXY_GLOBAL_INDEX_SPECS])
        for row in rows:
            spec = spec_by_code.get(str(row.get("f12", "")).strip())
            if spec is None:
                continue
            groups[spec.region].append(
                extract_proxy_global_index_item(row, spec, sparkline=sparkline_map.get(spec.symbol, []))
            )
        return groups

    async def fetch_global_index_chart(self, symbol: str, period: str) -> list[dict]:
        if not self.enabled or symbol not in GLOBAL_INDEX_SYMBOLS:
            return []

        payload = await self._get_json("/global-indices/kline", params={"symbol": symbol, "period": period})
        return extract_proxy_chart_items(payload)

    async def fetch_commodity_chart(self, symbol: str, period: str) -> list[dict]:
        """Fetch commodity kline via Cloudflare proxy (USD-denominated)."""
        if not self.enabled or symbol not in PROXY_COMMODITY_SYMBOLS:
            return []

        payload = await self._get_json("/global-commodities/kline", params={"symbol": symbol, "period": period})
        return extract_proxy_chart_items(payload)

    async def fetch_global_index_sparkline_map(self, symbols: list[str]) -> dict[str, list[float]]:
        tasks = [self.fetch_global_index_chart(symbol, "5d") for symbol in symbols]
        histories = await asyncio.gather(*tasks, return_exceptions=True)
        sparkline_map: dict[str, list[float]] = {}
        for symbol, history in zip(symbols, histories):
            if isinstance(history, list) and history:
                sparkline_map[symbol] = build_sparkline([item.get("price") for item in history], limit=7)
        return sparkline_map

    async def _get_json(self, path: str, params: dict[str, str] | None = None) -> dict:
        base_url = settings.eastmoney_proxy_base_url.rstrip("/")
        headers = {"User-Agent": USER_AGENT}
        if settings.eastmoney_proxy_token:
            headers["X-Proxy-Token"] = settings.eastmoney_proxy_token

        async with httpx.AsyncClient(timeout=self.timeout, headers=headers, trust_env=False) as client:
            response = await client.get(f"{base_url}{path}", params=params)
            response.raise_for_status()
            return response.json()
