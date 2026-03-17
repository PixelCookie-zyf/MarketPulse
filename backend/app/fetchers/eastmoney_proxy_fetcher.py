from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings
from app.fetchers.base import to_float

USER_AGENT = "Mozilla/5.0 (MarketPulse)"
_EASTMONEY_PRICE_SCALE = 100.0


@dataclass(frozen=True)
class ProxyIndexSpec:
    upstream_code: str
    symbol: str
    name: str
    region: str


PROXY_REGIONAL_INDEX_SPECS = (
    ProxyIndexSpec(upstream_code="HSI", symbol="HSI", name="恒生指数", region="hk"),
    ProxyIndexSpec(upstream_code="N225", symbol="N225", name="日经225", region="jp"),
    ProxyIndexSpec(upstream_code="KS11", symbol="KOSPI", name="韩国KOSPI", region="kr"),
)

US_GLOBAL_INDEX_SYMBOLS = frozenset({"IXIC", "SPX", "DJI"})
REGIONAL_GLOBAL_INDEX_SYMBOLS = frozenset(spec.symbol for spec in PROXY_REGIONAL_INDEX_SPECS)
GLOBAL_INDEX_SYMBOLS = US_GLOBAL_INDEX_SYMBOLS | REGIONAL_GLOBAL_INDEX_SYMBOLS


def is_global_index_symbol(symbol: str) -> bool:
    return symbol in GLOBAL_INDEX_SYMBOLS


def extract_proxy_global_index_item(row: dict, spec: ProxyIndexSpec) -> dict:
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
        "sparkline": [],
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


class EastmoneyProxyFetcher:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(settings.eastmoney_proxy_base_url)

    async def fetch_regional_global_indices(self) -> dict[str, list[dict]]:
        groups = {spec.region: [] for spec in PROXY_REGIONAL_INDEX_SPECS}
        if not self.enabled:
            return groups

        payload = await self._get_json("/global-indices/spot")
        rows = payload.get("data", {}).get("diff") or []
        spec_by_code = {spec.upstream_code: spec for spec in PROXY_REGIONAL_INDEX_SPECS}
        for row in rows:
            spec = spec_by_code.get(str(row.get("f12", "")).strip())
            if spec is None:
                continue
            groups[spec.region].append(extract_proxy_global_index_item(row, spec))
        return groups

    async def fetch_global_index_chart(self, symbol: str, period: str) -> list[dict]:
        if not self.enabled or symbol not in GLOBAL_INDEX_SYMBOLS:
            return []

        endpoint = "/global-futures/kline" if symbol in US_GLOBAL_INDEX_SYMBOLS else "/global-indices/kline"
        payload = await self._get_json(endpoint, params={"symbol": symbol, "period": period})
        return extract_proxy_chart_items(payload)

    async def _get_json(self, path: str, params: dict[str, str] | None = None) -> dict:
        base_url = settings.eastmoney_proxy_base_url.rstrip("/")
        headers = {"User-Agent": USER_AGENT}
        if settings.eastmoney_proxy_token:
            headers["X-Proxy-Token"] = settings.eastmoney_proxy_token

        async with httpx.AsyncClient(timeout=self.timeout, headers=headers, trust_env=False) as client:
            response = await client.get(f"{base_url}{path}", params=params)
            response.raise_for_status()
            return response.json()
