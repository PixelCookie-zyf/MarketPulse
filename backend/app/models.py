from __future__ import annotations

from pydantic import BaseModel, Field


class CommodityItem(BaseModel):
    symbol: str
    name: str
    name_en: str
    price: float
    change: float
    change_pct: float
    high: float
    low: float
    unit: str


class IndexItem(BaseModel):
    symbol: str
    name: str
    value: float
    change: float
    change_pct: float
    high: float | None = None
    low: float | None = None
    volume: float | None = None
    sparkline: list[float] = Field(default_factory=list)


class IndexGroups(BaseModel):
    us: list[IndexItem] = Field(default_factory=list)
    jp: list[IndexItem] = Field(default_factory=list)
    kr: list[IndexItem] = Field(default_factory=list)
    hk: list[IndexItem] = Field(default_factory=list)
    cn: list[IndexItem] = Field(default_factory=list)


class SectorItem(BaseModel):
    name: str
    change_pct: float
    turnover: float | None = None
    leading_stock: str | None = None


class OverviewResponse(BaseModel):
    timestamp: str
    commodities: list[CommodityItem] = Field(default_factory=list)
    indices: IndexGroups = Field(default_factory=IndexGroups)
    sectors: list[SectorItem] = Field(default_factory=list)
