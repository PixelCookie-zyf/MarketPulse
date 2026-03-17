from __future__ import annotations

import asyncio

import akshare as ak

from app.cache import cache_set
from app.config import settings
from app.fetchers.base import build_sparkline, to_float

CN_INDEX_CODES = ("sh000001", "sh000300", "sz399001", "sz399006", "sh000688")

# 东方财富全球期货 — 精确匹配名称（不带月份后缀的主力合约行）
EM_COMMODITY_MAP = {
    "COMEX黄金": {"symbol": "XAU", "name": "黄金", "name_en": "Gold", "unit": "USD/oz"},
    "COMEX白银": {"symbol": "XAG", "name": "白银", "name_en": "Silver", "unit": "USD/oz"},
    "COMEX铜": {"symbol": "COPPER", "name": "铜", "name_en": "Copper", "unit": "USD/lb"},
    "NYMEX原油": {"symbol": "WTI", "name": "原油", "name_en": "Crude Oil", "unit": "USD/bbl"},
    "布伦特原油": {"symbol": "BRENT", "name": "布伦特原油", "name_en": "Brent Oil", "unit": "USD/bbl"},
    "天然气": {"symbol": "NATGAS", "name": "天然气", "name_en": "Natural Gas", "unit": "USD/MMBtu"},
    "玉米当月连续": {"symbol": "CORN", "name": "玉米", "name_en": "Corn", "unit": "USc/bu"},
    "小麦当月连续": {"symbol": "WHEAT", "name": "小麦", "name_en": "Wheat", "unit": "USc/bu"},
    "棉花当月连续": {"symbol": "COTTON", "name": "棉花", "name_en": "Cotton", "unit": "USc/lb"},
    "糖11号当月连续": {"symbol": "SUGAR", "name": "糖", "name_en": "Sugar", "unit": "USc/lb"},
}

# 优先展示的商品（按顺序）
COMMODITY_PRIORITY = ["XAU", "XAG", "WTI", "BRENT", "NATGAS", "COPPER", "CORN", "WHEAT", "COTTON", "SUGAR", "COFFEE"]


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
            sparkline_map = await self._fetch_cn_sparkline_map()
            items = []
            for row in rows:
                item = normalize_index_row(row)
                item["sparkline"] = sparkline_map.get(item["symbol"], [])
                items.append(item)
            await cache_set("indices:cn", items, ttl=settings.cache_ttl_index)
            return items
        except Exception:
            return []

    async def fetch_cn_sectors(self) -> list[dict]:
        try:
            frame = await asyncio.to_thread(ak.stock_board_industry_summary_ths)
            items = [normalize_ths_sector_row(row) for row in frame.to_dict(orient="records")]
            items.sort(key=lambda item: item["change_pct"], reverse=True)
            await cache_set("sectors:cn", items, ttl=settings.cache_ttl_sector)
            return items
        except Exception:
            try:
                frame = await asyncio.to_thread(ak.stock_board_industry_name_em)
                items = [normalize_sector_row(row) for row in frame.to_dict(orient="records")]
                items.sort(key=lambda item: item["change_pct"], reverse=True)
                await cache_set("sectors:cn", items, ttl=settings.cache_ttl_sector)
                return items
            except Exception:
                return []

    async def _fetch_cn_sparkline_map(self) -> dict[str, list[float]]:
        results: dict[str, list[float]] = {}
        tasks = [asyncio.to_thread(self._fetch_cn_history, code) for code in CN_INDEX_CODES]
        histories = await asyncio.gather(*tasks, return_exceptions=True)
        for code, history in zip(CN_INDEX_CODES, histories):
            if isinstance(history, list) and history:
                results[code] = history
        return results

    async def fetch_global_commodities(self) -> list[dict]:
        """Fetch global commodity futures from Eastmoney via AKShare."""
        try:
            frame = await asyncio.to_thread(ak.futures_global_spot_em)
            items = []
            seen_symbols = set()
            for _, row in frame.iterrows():
                name = str(row.get("名称", "")).strip()
                # Exact match on the map keys (these are the main contract rows)
                spec = EM_COMMODITY_MAP.get(name)
                if spec is None or spec["symbol"] in seen_symbols:
                    continue
                price = to_float(row.get("最新价"))
                if not price or price == 0:
                    continue
                seen_symbols.add(spec["symbol"])
                prev = to_float(row.get("昨结"), default=price)
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0.0
                items.append({
                    "symbol": spec["symbol"],
                    "name": spec["name"],
                    "name_en": spec["name_en"],
                    "price": round(price, 4),
                    "change": round(change, 4),
                    "change_pct": round(change_pct, 2),
                    "high": round(to_float(row.get("最高"), default=price), 4),
                    "low": round(to_float(row.get("最低"), default=price), 4),
                    "unit": spec["unit"],
                })
            # Sort by priority
            order = {s: i for i, s in enumerate(COMMODITY_PRIORITY)}
            items.sort(key=lambda x: order.get(x["symbol"], 999))
            await cache_set("commodities:em", items, ttl=settings.cache_ttl_commodity)
            return items
        except Exception as e:
            print(f"[AKShare] fetch_global_commodities error: {e}")
            return []

    async def fetch_index_intraday(self, symbol: str) -> list[dict]:
        """Fetch recent daily data as intraday proxy for A-share index.
        Uses stock_zh_index_daily (Sina source) which is reliable from China.
        For 1d view, returns the last trading day's OHLC as a single-point chart.
        Falls back to daily history as a line chart.
        """
        try:
            frame = await asyncio.to_thread(ak.stock_zh_index_daily, symbol=symbol)
            if frame.empty:
                return []
            # Get last trading day's data — use last 1 row for "today"
            last_row = frame.iloc[-1]
            date_str = str(last_row.get("date", ""))
            # For intraday simulation, create points from open→high→low→close
            o = to_float(last_row.get("open"))
            h = to_float(last_row.get("high"))
            l = to_float(last_row.get("low"))
            c = to_float(last_row.get("close"))
            vol = to_float(last_row.get("volume", 0))
            items = [
                {"time": f"{date_str} 09:30", "price": round(o, 4), "volume": vol / 4},
                {"time": f"{date_str} 10:30", "price": round(h, 4), "volume": vol / 4},
                {"time": f"{date_str} 13:30", "price": round(l, 4), "volume": vol / 4},
                {"time": f"{date_str} 15:00", "price": round(c, 4), "volume": vol / 4},
            ]
            return items
        except Exception as e:
            print(f"[AKShare] fetch_index_intraday error for {symbol}: {e}")
            return []

    async def fetch_commodity_intraday(self, symbol: str) -> list[dict]:
        """Fetch commodity intraday data. Returns empty if not supported."""
        # Commodity intraday not reliably available from China servers.
        # Return empty — the chart will show "暂无分时数据".
        return []

    async def fetch_index_daily_history(self, symbol: str, days: int = 5) -> list[dict]:
        """Fetch recent daily close prices for 5-day chart.
        Uses stock_zh_index_daily (Sina source) — always works from China.
        """
        try:
            frame = await asyncio.to_thread(ak.stock_zh_index_daily, symbol=symbol)
            if frame.empty:
                return []
            recent = frame.tail(days)
            items = []
            for _, row in recent.iterrows():
                items.append({
                    "time": str(row.get("date", "")),
                    "price": round(to_float(row.get("close", 0)), 4),
                    "volume": to_float(row.get("volume", 0)),
                })
            return items
        except Exception as e:
            print(f"[AKShare] fetch_index_daily_history error for {symbol}: {e}")
            return []

    def _fetch_cn_history(self, symbol: str) -> list[float]:
        try:
            frame = ak.stock_zh_index_daily(symbol=symbol)
            close_column = "close" if "close" in frame.columns else "收盘"
            return build_sparkline(frame[close_column].tolist(), limit=7)
        except Exception:
            return []
