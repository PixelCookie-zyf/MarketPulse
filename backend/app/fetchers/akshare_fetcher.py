from __future__ import annotations

import asyncio

import akshare as ak

from app.cache import cache_set
from app.config import settings
from app.fetchers.base import build_sparkline, to_float

CN_INDEX_CODES = ("sh000001", "sh000300", "sz399001", "sz399006", "sh000688")

# 东方财富全球指数 → 我们的标准 symbol 映射
EM_GLOBAL_INDEX_MAP = {
    "纳斯达克": {"symbol": "IXIC", "name": "纳斯达克"},
    "标普500": {"symbol": "SPX", "name": "标普500"},
    "道琼斯": {"symbol": "DJI", "name": "道琼斯"},
    "日经225": {"symbol": "N225", "name": "日经225"},
    "韩国KOSPI": {"symbol": "KOSPI", "name": "韩国KOSPI"},
    "恒生指数": {"symbol": "HSI", "name": "恒生指数"},
}

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
    "生猪当月连续": {"symbol": "PORK", "name": "生猪", "name_en": "Live Hogs", "unit": "CNY/t"},
}

# 优先展示的商品（按顺序）
COMMODITY_PRIORITY = ["XAU", "XAG", "WTI", "BRENT", "NATGAS", "COPPER", "PORK", "CORN", "WHEAT", "COTTON", "SUGAR", "COFFEE"]


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

    # Domestic futures that need Sina minute data for pricing
    SINA_DOMESTIC_SPECS = {
        "LH0": {"symbol": "PORK", "name": "生猪", "name_en": "Live Hogs", "unit": "CNY/t"},
    }

    async def _fetch_sina_domestic_commodities(self) -> list[dict]:
        """Fetch domestic commodity prices from Sina minute data."""
        items = []
        for sina_code, spec in self.SINA_DOMESTIC_SPECS.items():
            try:
                frame = await asyncio.to_thread(
                    ak.futures_zh_minute_sina, symbol=sina_code, period="1"
                )
                if frame.empty:
                    continue
                last = frame.iloc[-1]
                first_today = frame.iloc[0]
                price = to_float(last.get("close", 0))
                open_price = to_float(first_today.get("open", price))
                change = price - open_price
                change_pct = (change / open_price * 100) if open_price else 0
                items.append({
                    "symbol": spec["symbol"],
                    "name": spec["name"],
                    "name_en": spec["name_en"],
                    "price": round(price, 4),
                    "change": round(change, 4),
                    "change_pct": round(change_pct, 2),
                    "high": round(to_float(last.get("high", price)), 4),
                    "low": round(to_float(last.get("low", price)), 4),
                    "unit": spec["unit"],
                })
            except Exception as e:
                print(f"[AKShare] domestic commodity {sina_code} error: {e}")
        return items

    # Market symbol → Eastmoney Chinese name (for index_global_hist_em)
    SYM_TO_EM_NAME = {
        "IXIC": "纳斯达克", "SPX": "标普500", "DJI": "道琼斯",
        "N225": "日经225", "KOSPI": "韩国KOSPI", "HSI": "恒生指数",
    }

    async def fetch_global_indices(self) -> dict[str, list[dict]]:
        """Fetch global indices from Eastmoney (index_global_spot_em) with sparklines."""
        try:
            frame = await asyncio.to_thread(ak.index_global_spot_em)
        except Exception as e:
            print(f"[AKShare] fetch_global_indices error: {e}")
            return {"us": [], "jp": [], "kr": [], "hk": []}

        # Collect items (this part can't fail since frame is already loaded)
        all_items: list[dict] = []
        for _, row in frame.iterrows():
            name = str(row.get("名称", "")).strip()
            spec = EM_GLOBAL_INDEX_MAP.get(name)
            if spec is None:
                continue
            all_items.append({
                "symbol": spec["symbol"],
                "name": spec["name"],
                "value": round(to_float(row.get("最新价")), 4),
                "change": round(to_float(row.get("涨跌额")), 4),
                "change_pct": round(to_float(row.get("涨跌幅")), 4),
                "high": round(to_float(row.get("最新价")), 4),
                "low": round(to_float(row.get("最新价")), 4),
                "volume": 0,
                "sparkline": [],
            })

        # Sparklines: best-effort, failures don't affect main data
        try:
            sparkline_map = await self._fetch_global_sparklines([i["symbol"] for i in all_items])
            for item in all_items:
                item["sparkline"] = sparkline_map.get(item["symbol"], [])
        except Exception as e:
            print(f"[AKShare] sparkline fetch failed (non-fatal): {e}")

        # Group by region
        us, jp, kr, hk = [], [], [], []
        for item in all_items:
            sym = item["symbol"]
            if sym in ("IXIC", "SPX", "DJI"):
                us.append(item)
            elif sym == "N225":
                jp.append(item)
            elif sym == "KOSPI":
                kr.append(item)
            elif sym == "HSI":
                hk.append(item)

        result = {"us": us, "jp": jp, "kr": kr, "hk": hk}
        for key, items in result.items():
            await cache_set(f"indices:{key}", items, ttl=settings.cache_ttl_index)
        return result

    async def _fetch_global_sparklines(self, symbols: list[str]) -> dict[str, list[float]]:
        """Fetch 7-day sparkline data for global indices."""
        results: dict[str, list[float]] = {}
        tasks = [asyncio.to_thread(self._fetch_global_hist, sym) for sym in symbols]
        histories = await asyncio.gather(*tasks, return_exceptions=True)
        for sym, history in zip(symbols, histories):
            if isinstance(history, list) and history:
                results[sym] = history
        return results

    def _fetch_global_hist(self, symbol: str) -> list[float]:
        """Fetch recent daily closes for a global index from Eastmoney."""
        em_name = self.SYM_TO_EM_NAME.get(symbol)
        if not em_name:
            return []
        try:
            frame = ak.index_global_hist_em(symbol=em_name)
            if frame.empty:
                return []
            close_col = "最新价" if "最新价" in frame.columns else "收盘"
            closes = frame[close_col].tolist()
            return build_sparkline(closes, limit=7)
        except Exception as e:
            print(f"[AKShare] _fetch_global_hist error for {symbol}: {e}")
            return []

    async def fetch_global_index_chart(self, symbol: str, days: int = 5) -> list[dict]:
        """Fetch daily history for a global index from Eastmoney."""
        em_name = self.SYM_TO_EM_NAME.get(symbol)
        if not em_name:
            return []
        try:
            frame = await asyncio.to_thread(
                ak.index_global_hist_em, symbol=em_name
            )
            if frame.empty:
                return []
            recent = frame.tail(days)
            items = []
            for _, row in recent.iterrows():
                items.append({
                    "time": str(row.get("日期", "")),
                    "price": round(to_float(row.get("最新价", 0)), 4),
                    "volume": 0,
                })
            return items
        except Exception as e:
            print(f"[AKShare] fetch_global_index_chart error for {symbol}: {e}")
            return []

    async def fetch_global_commodities(self) -> list[dict]:
        """Fetch global commodity futures from Eastmoney + domestic from Sina."""
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
            # Add domestic commodities (pork etc.)
            domestic = await self._fetch_sina_domestic_commodities()
            seen_symbols = {item["symbol"] for item in items}
            for d in domestic:
                if d["symbol"] not in seen_symbols:
                    items.append(d)
            # Sort by priority
            order = {s: i for i, s in enumerate(COMMODITY_PRIORITY)}
            items.sort(key=lambda x: order.get(x["symbol"], 999))
            await cache_set("commodities:em", items, ttl=settings.cache_ttl_commodity)
            return items
        except Exception as e:
            print(f"[AKShare] fetch_global_commodities error: {e}")
            return []

    async def fetch_index_intraday(self, symbol: str) -> list[dict]:
        """Fetch 1-minute intraday data for A-share index from Sina.
        stock_zh_a_minute supports ~9 trading days of minute data.
        """
        try:
            frame = await asyncio.to_thread(
                ak.stock_zh_a_minute, symbol=symbol, period="1"
            )
            if frame.empty:
                return []
            # Get only the last trading day
            frame["day"] = frame["day"].astype(str)
            last_date = frame["day"].iloc[-1][:10]
            today_data = frame[frame["day"].str.startswith(last_date)]
            items = []
            for _, row in today_data.iterrows():
                items.append({
                    "time": str(row.get("day", ""))[11:16],  # HH:MM
                    "price": round(to_float(row.get("close", 0)), 4),
                    "volume": to_float(row.get("volume", 0)),
                })
            return items
        except Exception as e:
            print(f"[AKShare] fetch_index_intraday error for {symbol}: {e}")
            return []

    async def fetch_commodity_intraday(self, symbol: str) -> list[dict]:
        """Fetch commodity intraday data via futures_zh_minute_sina."""
        SYMBOL_TO_SINA = {
            "XAU": "AU0",       # 沪金
            "XAG": "AG0",       # 沪银
            "WTI": "SC0",       # 原油（上海国际能源）
            "COPPER": "CU0",    # 沪铜
            "BRENT": "SC0",     # 布伦特用SC0近似
            "NATGAS": "FU0",    # 燃料油近似天然气
            "PORK": "LH0",      # 生猪
        }
        sina_code = SYMBOL_TO_SINA.get(symbol)
        if not sina_code:
            return []
        try:
            frame = await asyncio.to_thread(
                ak.futures_zh_minute_sina, symbol=sina_code, period="1"
            )
            if frame.empty:
                return []
            frame["datetime"] = frame["datetime"].astype(str)
            last_date = frame["datetime"].iloc[-1][:10]
            today_data = frame[frame["datetime"].str.startswith(last_date)]
            items = []
            for _, row in today_data.iterrows():
                items.append({
                    "time": str(row.get("datetime", ""))[11:16],
                    "price": round(to_float(row.get("close", 0)), 4),
                    "volume": to_float(row.get("volume", 0)),
                })
            return items
        except Exception as e:
            print(f"[AKShare] fetch_commodity_intraday error for {symbol}: {e}")
            return []

    async def fetch_commodity_5d(self, symbol: str) -> list[dict]:
        """Fetch 5-day commodity chart using 15-min bars from Sina."""
        SYMBOL_TO_SINA = {
            "XAU": "AU0", "XAG": "AG0", "WTI": "SC0", "COPPER": "CU0",
            "BRENT": "SC0", "NATGAS": "FU0", "PORK": "LH0",
        }
        sina_code = SYMBOL_TO_SINA.get(symbol)
        if not sina_code:
            return []
        try:
            frame = await asyncio.to_thread(
                ak.futures_zh_minute_sina, symbol=sina_code, period="15"
            )
            if frame.empty:
                return []
            frame["datetime"] = frame["datetime"].astype(str)
            # Get last 5 trading days
            dates = frame["datetime"].str[:10].unique()
            recent_dates = dates[-5:] if len(dates) >= 5 else dates
            mask = frame["datetime"].str[:10].isin(recent_dates)
            recent_data = frame[mask]
            items = []
            for _, row in recent_data.iterrows():
                items.append({
                    "time": str(row.get("datetime", "")),
                    "price": round(to_float(row.get("close", 0)), 4),
                    "volume": to_float(row.get("volume", 0)),
                })
            return items
        except Exception as e:
            print(f"[AKShare] fetch_commodity_5d error for {symbol}: {e}")
            return []

    async def fetch_index_daily_history(self, symbol: str, days: int = 5) -> list[dict]:
        """Fetch 5-day chart using 15-min bars from Sina.
        stock_zh_a_minute with period=15 gives ~9 days of 15-min data.
        """
        try:
            frame = await asyncio.to_thread(
                ak.stock_zh_a_minute, symbol=symbol, period="15"
            )
            if frame.empty:
                # Fallback to daily
                frame = await asyncio.to_thread(ak.stock_zh_index_daily, symbol=symbol)
                if frame.empty:
                    return []
                recent = frame.tail(days)
                return [
                    {
                        "time": str(row.get("date", "")),
                        "price": round(to_float(row.get("close", 0)), 4),
                        "volume": to_float(row.get("volume", 0)),
                    }
                    for _, row in recent.iterrows()
                ]
            # Get last N days of 15-min bars
            frame["day"] = frame["day"].astype(str)
            dates = frame["day"].str[:10].unique()
            recent_dates = dates[-days:] if len(dates) >= days else dates
            mask = frame["day"].str[:10].isin(recent_dates)
            recent_data = frame[mask]
            items = []
            for _, row in recent_data.iterrows():
                items.append({
                    "time": str(row.get("day", "")),
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
