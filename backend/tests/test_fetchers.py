import math

import pandas as pd

from app.fetchers.akshare_fetcher import (
    AKShareFetcher,
    EM_GLOBAL_INDEX_FUTURES,
    match_em_commodity_spec,
    normalize_index_row,
    normalize_sector_row,
    normalize_ths_sector_row,
)
from app.fetchers.base import build_sparkline, to_float
from app.fetchers.eastmoney_proxy_fetcher import ProxyIndexSpec, extract_proxy_global_index_item
from app.fetchers.alphavantage_fetcher import (
    AVCommoditySpec,
    AVQuoteSpec,
    extract_commodity_item,
    extract_global_quote_item,
    is_rate_limited_response,
)
from app.fetchers.goldapi_fetcher import GOLD_SPECS, GoldSpec, extract_goldapi_item
from app.fetchers.stooq_fetcher import (
    STQ_COMMODITY_SPECS,
    STQ_HK_INDEX_SPECS,
    STQ_US_INDEX_SPECS,
    StooqCommoditySpec,
    StooqIndexSpec,
    extract_stooq_commodity_item,
    extract_stooq_hk_index_item,
    extract_stooq_index_item,
)
from app.scheduler import _refresh_combined_commodities, build_job_specs, refresh_cn_indices


def test_extract_global_quote_item_maps_etf_quote_to_index_shape():
    payload = {
        "01. symbol": "QQQ",
        "03. high": "603.5999",
        "04. low": "592.5700",
        "05. price": "593.7200",
        "06. volume": "63145490",
        "09. change": "-3.5400",
        "10. change percent": "-0.5927%",
    }

    result = extract_global_quote_item(
        payload,
        AVQuoteSpec(source_symbol="QQQ", market_symbol="IXIC", name="纳斯达克"),
    )

    assert result == {
        "symbol": "IXIC",
        "name": "纳斯达克",
        "value": 593.72,
        "change": -3.54,
        "change_pct": -0.5927,
        "high": 603.5999,
        "low": 592.57,
        "volume": 63145490.0,
        "sparkline": [],
    }


def test_extract_commodity_item_uses_latest_and_previous_values():
    payload = {
        "data": [
            {"date": "2026-01-01", "value": "12986.60681818182"},
            {"date": "2025-12-01", "value": "11790.96409090909"},
        ]
    }

    result = extract_commodity_item(
        payload,
        AVCommoditySpec(symbol="COPPER", function="COPPER", name="铜", name_en="Copper", unit="USD/ton"),
    )

    assert result == {
        "symbol": "COPPER",
        "name": "铜",
        "name_en": "Copper",
        "price": 12986.6068,
        "change": 1195.6427,
        "change_pct": 10.14,
        "high": 12986.6068,
        "low": 12986.6068,
        "unit": "USD/ton",
    }


def test_rate_limit_detection_matches_information_payload():
    assert is_rate_limited_response(
        {
            "Information": "Thank you for using Alpha Vantage! Please consider spreading out your free API requests more sparingly."
        }
    )


def test_extract_goldapi_item_maps_quote_fields():
    payload = {
        "price": 5013.745,
        "ch": -5.43,
        "chp": -0.11,
        "high_price": 5036.255,
        "low_price": 4967.61,
    }

    result = extract_goldapi_item(payload, GoldSpec(symbol="XAU", name="黄金", name_en="Gold", unit="USD/oz"))

    assert result == {
        "symbol": "XAU",
        "name": "黄金",
        "name_en": "Gold",
        "price": 5013.745,
        "change": -5.43,
        "change_pct": -0.11,
        "high": 5036.255,
        "low": 4967.61,
        "unit": "USD/oz",
    }


def test_normalize_akshare_rows():
    index = normalize_index_row(
        {
            "代码": "sh000001",
            "名称": "上证指数",
            "最新价": 3050.12,
            "涨跌额": 10.5,
            "涨跌幅": 0.35,
            "最高": 3060.0,
            "最低": 3038.0,
            "成交量": 123456789,
        }
    )
    sector = normalize_sector_row(
        {
            "板块名称": "半导体",
            "涨跌幅": 3.25,
            "总市值": 12500000000,
            "领涨股票": "中芯国际",
        }
    )

    assert index["symbol"] == "sh000001"
    assert index["volume"] == 123456789.0
    assert sector["leading_stock"] == "中芯国际"
    assert sector["change_pct"] == 3.25


def test_normalize_ths_sector_row():
    sector = normalize_ths_sector_row(
        {
            "板块": "半导体",
            "涨跌幅": 3.25,
            "总成交额": 12500000000,
            "领涨股": "中芯国际",
        }
    )

    assert sector == {
        "name": "半导体",
        "change_pct": 3.25,
        "turnover": 12500000000.0,
        "leading_stock": "中芯国际",
    }


def test_match_em_commodity_spec_handles_contract_suffixes():
    spec = match_em_commodity_spec("布伦特原油2708")

    assert spec is not None
    assert spec["symbol"] == "BRENT"


async def test_fetch_global_commodities_ignores_non_finite_contract_rows(monkeypatch):
    frame = pd.DataFrame(
        [
            {"名称": "COMEX黄金2504", "最新价": math.nan, "昨结": math.nan, "最高": math.nan, "最低": math.nan},
            {"名称": "COMEX黄金", "最新价": 5020.8, "昨结": 5002.2, "最高": 5049.4, "最低": 4994.8},
        ]
    )

    async def fake_cache_set(*args, **kwargs):
        return None

    monkeypatch.setattr("app.fetchers.akshare_fetcher.ak.futures_global_spot_em", lambda: frame)
    monkeypatch.setattr("app.fetchers.akshare_fetcher.cache_set", fake_cache_set)
    monkeypatch.setattr("app.fetchers.eastmoney_proxy_fetcher.settings", type("S", (), {"eastmoney_proxy_base_url": "", "eastmoney_proxy_token": ""})())

    items = await AKShareFetcher().fetch_global_commodities()

    assert items == [
        {
            "symbol": "XAU",
            "name": "黄金",
            "name_en": "Gold",
            "price": 5020.8,
            "change": 18.6,
            "change_pct": 0.37,
            "high": 5049.4,
            "low": 4994.8,
            "unit": "USD/oz",
        }
    ]


def test_build_sparkline_uses_recent_numeric_values():
    assert build_sparkline([1, 2, "3.5", None, 4, 5, 6], limit=4) == [3.5, 4.0, 5.0, 6.0]


def test_to_float_replaces_nan_with_default():
    assert to_float(float("nan"), default=0.0) == 0.0


def test_extract_proxy_global_index_item_keeps_sparkline():
    spec = ProxyIndexSpec(upstream_code="DJIA", symbol="DJI", name="道琼斯", region="us")

    result = extract_proxy_global_index_item(
        {"f2": "4234500", "f4": "12500", "f3": "29", "f15": "4240100", "f16": "4212200", "f6": "0"},
        spec,
        sparkline=[41980.0, 42110.0, 42345.0],
    )

    assert result == {
        "symbol": "DJI",
        "name": "道琼斯",
        "value": 42345.0,
        "change": 125.0,
        "change_pct": 0.29,
        "high": 42401.0,
        "low": 42122.0,
        "volume": 0.0,
        "sparkline": [41980.0, 42110.0, 42345.0],
    }


def test_global_index_futures_define_chart_codes():
    assert {spec["chart_code"] for spec in EM_GLOBAL_INDEX_FUTURES.values()} == {"NQ00Y", "ES00Y", "YM00Y"}


def test_extract_stooq_index_item_maps_quote_and_sparkline():
    result = extract_stooq_index_item(
        "2026-03-13,22425.71,22521.38,22069.24,22105.36,4681146300",
        StooqIndexSpec(symbol="^ndq", market_symbol="IXIC", name="纳斯达克"),
        sparkline=[21980.12, 22144.8, 22091.45, 22105.36],
    )

    assert result == {
        "symbol": "IXIC",
        "name": "纳斯达克",
        "value": 22105.36,
        "change": 13.91,
        "change_pct": 0.063,
        "high": 22521.38,
        "low": 22069.24,
        "volume": 4681146300.0,
        "sparkline": [21980.12, 22144.8, 22091.45, 22105.36],
    }


def test_extract_stooq_hk_index_item_maps_quote_and_sparkline():
    result = extract_stooq_hk_index_item(
        "2026-03-13,18588.63,18620.50,18388.10,18456.23,0",
        sparkline=[18720.0, 18690.0, 18580.0, 18456.23],
    )

    assert STQ_HK_INDEX_SPECS == (StooqIndexSpec(symbol="^hsi", market_symbol="HSI", name="恒生指数"),)
    assert result == {
        "symbol": "HSI",
        "name": "恒生指数",
        "value": 18456.23,
        "change": -132.4,
        "change_pct": -0.71,
        "high": 18620.5,
        "low": 18388.1,
        "volume": 0.0,
        "sparkline": [18720.0, 18690.0, 18580.0, 18456.23],
    }


def test_extract_stooq_commodity_item_maps_quote_fields():
    result = extract_stooq_commodity_item(
        "2026-03-16,73.84,75.26,72.4,74.28,",
        StooqCommoditySpec(symbol="cb.f", market_symbol="BRENT", name="布伦特原油", name_en="Brent Oil", unit="USD/bbl"),
    )

    assert result == {
        "symbol": "BRENT",
        "name": "布伦特原油",
        "name_en": "Brent Oil",
        "price": 74.28,
        "change": 0.44,
        "change_pct": 0.6,
        "high": 75.26,
        "low": 72.4,
        "unit": "USD/bbl",
    }


def test_stooq_specs_cover_expanded_dashboard_symbols():
    assert {spec.market_symbol for spec in STQ_US_INDEX_SPECS} == {"IXIC", "SPX", "DJI"}
    assert {spec.symbol for spec in GOLD_SPECS} | {spec.market_symbol for spec in STQ_COMMODITY_SPECS} == {
        "XAU",
        "XAG",
        "BRENT",
        "COPPER",
    }


def test_scheduler_job_specs_reflect_free_tier_limits():
    specs = {spec["id"]: spec for spec in build_job_specs()}

    assert specs["cn_indices"]["minutes"] == 1
    assert specs["cn_sectors"]["minutes"] == 3
    assert specs["gold_metals"]["minutes"] == 15
    assert specs["global_indices"]["minutes"] == 5
    assert specs["em_commodities"]["minutes"] == 5


async def test_refresh_cn_indices_preserves_existing_global_groups(monkeypatch):
    async def fake_fetch_cn_indices(self):
        return [{"symbol": "sh000001", "name": "上证指数"}]

    async def fake_load_index_groups():
        return {"us": [], "jp": [], "kr": [], "hk": [{"symbol": "HSI", "name": "恒生指数"}], "cn": []}

    async def fake_cache_set(*args, **kwargs):
        return None

    monkeypatch.setattr("app.fetchers.akshare_fetcher.AKShareFetcher.fetch_cn_indices", fake_fetch_cn_indices)
    monkeypatch.setattr("app.scheduler.cache_set", fake_cache_set)
    monkeypatch.setattr("app.scheduler._load_index_groups", fake_load_index_groups)

    groups = await refresh_cn_indices()

    assert groups["cn"] == [{"symbol": "sh000001", "name": "上证指数"}]
    assert groups["hk"] == [{"symbol": "HSI", "name": "恒生指数"}]


async def test_refresh_combined_commodities_keeps_dashboard_order(monkeypatch):
    cached = {}

    async def fake_cache_set(key, data, ttl=60):
        cached[key] = data

    monkeypatch.setattr("app.scheduler.cache_set", fake_cache_set)

    await _refresh_combined_commodities(
        metals=[
            {"symbol": "XAG", "name": "白银"},
            {"symbol": "XAU", "name": "黄金"},
        ],
        stooq=[
            {"symbol": "BRENT", "name": "布伦特原油"},
            {"symbol": "COPPER", "name": "铜"},
        ],
    )

    assert [item["symbol"] for item in cached["commodities:all"]] == [
        "XAU",
        "XAG",
        "BRENT",
        "COPPER",
    ]
