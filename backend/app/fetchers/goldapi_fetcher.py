from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.cache import cache_set
from app.config import settings
from app.fetchers.base import to_float

BASE_URL = "https://www.goldapi.io/api"


@dataclass(frozen=True)
class GoldSpec:
    symbol: str
    name: str
    name_en: str
    unit: str


GOLD_SPECS = (
    GoldSpec(symbol="XAU", name="黄金", name_en="Gold", unit="USD/oz"),
    GoldSpec(symbol="XAG", name="白银", name_en="Silver", unit="USD/oz"),
)


def extract_goldapi_item(payload: dict, spec: GoldSpec) -> dict:
    price = round(to_float(payload.get("price")), 4)
    return {
        "symbol": spec.symbol,
        "name": spec.name,
        "name_en": spec.name_en,
        "price": price,
        "change": round(to_float(payload.get("ch")), 4),
        "change_pct": round(to_float(payload.get("chp")), 4),
        "high": round(to_float(payload.get("high_price"), price), 4),
        "low": round(to_float(payload.get("low_price"), price), 4),
        "unit": spec.unit,
    }


class GoldAPIFetcher:
    def __init__(self, api_key: str | None = None, timeout: float = 20.0):
        self.api_key = api_key or settings.goldapi_key
        self.timeout = timeout

    async def fetch_precious_metals(self) -> list[dict]:
        if not self.api_key:
            return []

        items: list[dict] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for spec in GOLD_SPECS:
                response = await client.get(
                    f"{BASE_URL}/{spec.symbol}/USD",
                    headers={"x-access-token": self.api_key},
                )
                response.raise_for_status()
                items.append(extract_goldapi_item(response.json(), spec))

        await cache_set("commodities:metals", items, ttl=settings.cache_ttl_commodity)
        return items
