from __future__ import annotations

import asyncio

import akshare as ak

from app.cache import cache_set
from app.config import settings
from app.fetchers.base import to_float

CN_INDEX_CODES = ("sh000001", "sh000300", "sz399001", "sz399006", "sh000688")


def normalize_index_row(row: dict) -> dict:
    return {
        "symbol": str(row.get("代码", "")),
        "name": str(row.get("名称", "")),
        "value": round(to_float(row.get("最新价")), 4),
        "change": round(to_float(row.get("涨跌额")), 4),
        "change_pct": round(to_float(row.get("涨跌幅")), 4),
        "high": round(to_float(row.get("最高")), 4),
        "low": round(to_float(row.get("最低")), 4),
        "volume": to_float(row.get("成交量")),
        "sparkline": [],
    }


def normalize_sector_row(row: dict) -> dict:
    return {
        "name": str(row.get("板块名称", "")),
        "change_pct": round(to_float(row.get("涨跌幅")), 4),
        "turnover": to_float(row.get("总市值")),
        "leading_stock": str(row.get("领涨股票", "") or ""),
    }


def normalize_ths_sector_row(row: dict) -> dict:
    return {
        "name": str(row.get("板块", "")),
        "change_pct": round(to_float(row.get("涨跌幅")), 4),
        "turnover": to_float(row.get("总成交额")),
        "leading_stock": str(row.get("领涨股", "") or ""),
    }


class AKShareFetcher:
    async def fetch_cn_indices(self) -> list[dict]:
        try:
            frame = await asyncio.to_thread(ak.stock_zh_index_spot_sina)
            rows = frame[frame["代码"].isin(CN_INDEX_CODES)].to_dict(orient="records")
            items = [normalize_index_row(row) for row in rows]
            await cache_set("indices:cn", items, ttl=settings.cache_ttl_index)
            return items
        except Exception:
            return []

    async def fetch_hk_index(self) -> list[dict]:
        try:
            frame = await asyncio.to_thread(ak.index_global_spot_em)
            rows = frame[frame["名称"].astype(str).str.contains("恒生", na=False)].to_dict(orient="records")
            items = [
                {
                    "symbol": str(row.get("代码") or row.get("名称") or "HSI"),
                    "name": "恒生指数",
                    "value": round(to_float(row.get("最新价")), 4),
                    "change": round(to_float(row.get("涨跌额")), 4),
                    "change_pct": round(to_float(row.get("涨跌幅")), 4),
                    "high": round(to_float(row.get("最高")), 4),
                    "low": round(to_float(row.get("最低")), 4),
                    "volume": to_float(row.get("成交量")),
                    "sparkline": [],
                }
                for row in rows[:1]
            ]
            await cache_set("indices:hk", items, ttl=settings.cache_ttl_index)
            return items
        except Exception:
            return []

    async def fetch_cn_sectors(self) -> list[dict]:
        try:
            frame = await asyncio.to_thread(ak.stock_board_industry_name_em)
            items = [normalize_sector_row(row) for row in frame.to_dict(orient="records")]
            items.sort(key=lambda item: item["change_pct"], reverse=True)
            await cache_set("sectors:cn", items, ttl=settings.cache_ttl_sector)
            return items
        except Exception:
            try:
                frame = await asyncio.to_thread(ak.stock_board_industry_summary_ths)
                items = [normalize_ths_sector_row(row) for row in frame.to_dict(orient="records")]
                items.sort(key=lambda item: item["change_pct"], reverse=True)
                await cache_set("sectors:cn", items, ttl=settings.cache_ttl_sector)
                return items
            except Exception:
                return []
